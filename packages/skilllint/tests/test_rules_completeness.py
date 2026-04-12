"""Completeness tests for the skilllint rule registry.

These tests assert that all expected rule series are registered and that the CLI
output is consistent with the registry.  They are designed to FAIL pre-migration
(before T3-T13 populate the remaining series) and PASS once all series modules
are fully populated and T14 completes.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from typer.testing import CliRunner

# MIN_REGISTERED_SERIES is re-exported by T1 from skilllint.rules._constants.
# Source: P038 architect spec section 8 -- 14 series total (AS + FM + PA existing,
# SK + LK + PD + PL + HK + NR + SL + TC + PR extracted, CU + CX adapter-backed).
from skilllint.rules import MIN_REGISTERED_SERIES

# The full expected set: every two-letter prefix that must appear in the registry
# once migration is complete.  CM001 is intentionally excluded (reserved, no logic).
# Source: P038 plan, section 'Critical invariants', invariant #8.
_EXPECTED_SERIES: frozenset[str] = frozenset({
    "AS",
    "FM",
    "PA",
    "SK",
    "LK",
    "PD",
    "PL",
    "HK",
    "NR",
    "SL",
    "TC",
    "PR",
    "CU",
    "CX",
})


def _registered_prefixes() -> set[str]:
    """Return the set of two-letter series prefixes currently in RULE_REGISTRY."""
    from skilllint.rule_registry import RULE_REGISTRY

    return {rule_id[:2] for rule_id in RULE_REGISTRY}


def _cli_series_from_output(output: str) -> set[str]:
    """Parse series prefixes from ``skilllint rules`` table output.

    The table rows have the form ``| SK001 | ...``.  Extract the two-letter prefix
    from each rule ID column.

    Args:
        output: Captured stdout from ``skilllint rules``.

    Returns:
        Set of two-letter series prefix strings found in the output.
    """
    # Match rule IDs like AS001, FM002, SK003 in the table
    matches = re.findall(r"\b([A-Z]{2})\d{3}\b", output)
    return set(matches)


def _readme_series_from_table() -> set[str]:
    """Parse series prefixes from the README 'What gets validated' table.

    Reads the project README and extracts two-letter codes from table rows
    in the 'What gets validated' section.

    Returns:
        Set of two-letter series prefix strings found in the README table.
    """
    readme = Path(__file__).parents[3] / "README.md"
    if not readme.exists():
        pytest.skip(f"README.md not found at {readme}")

    content = readme.read_text(encoding="utf-8")

    # Find the "What gets validated" section
    section_match = re.search(r"## What gets validated\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if section_match is None:
        pytest.skip("README.md does not contain a 'What gets validated' section")

    section = section_match.group(1)

    # Match rule codes like FM001-FM010, SK001-SK009, PA001 at the start of table cells
    matches = re.findall(r"\|\s*([A-Z]{2})\d{3}", section)
    return set(matches)


class TestRegisteredSeriesCount:
    """Assert the registered series prefix count meets MIN_REGISTERED_SERIES."""

    def test_registered_series_count_meets_minimum(self) -> None:
        """Registry must contain at least MIN_REGISTERED_SERIES distinct series.

        This test fails pre-migration (only AS, FM, PA registered = 3 series)
        and passes once T3-T13 complete and all 14 series are populated.
        """
        prefixes = _registered_prefixes()
        count = len(prefixes)
        assert count >= MIN_REGISTERED_SERIES, (
            f"RULE_REGISTRY has {count} distinct series prefixes but requires at least "
            f"{MIN_REGISTERED_SERIES}. Missing series: "
            f"{sorted(_EXPECTED_SERIES - prefixes)}. "
            f"Registered so far: {sorted(prefixes)}."
        )


class TestExpectedSeriesSubset:
    """Assert expected series set is a subset of registered prefixes."""

    def test_expected_series_subset_of_registered(self) -> None:
        """All 14 expected series prefixes must be present in RULE_REGISTRY.

        Expected: {AS, FM, PA, SK, LK, PD, PL, HK, NR, SL, TC, PR, CU, CX}.
        This test fails pre-migration (SK, LK, PD, PL, HK, NR, SL, TC, PR, CU, CX
        are not yet registered) and passes once all series tasks complete.
        """
        prefixes = _registered_prefixes()
        missing = _EXPECTED_SERIES - prefixes
        assert not missing, (
            f"Expected series prefixes not yet registered: {sorted(missing)}. "
            f"Registered prefixes: {sorted(prefixes)}. "
            f"Complete T3-T13 to populate all series."
        )


class TestCliOutputMatchesRegistry:
    """Assert 'skilllint rules' CLI output lists the same series as RULE_REGISTRY."""

    def test_cli_rules_output_matches_registry(self, cli_runner: CliRunner) -> None:
        """CLI 'skilllint rules' output must list exactly the series in RULE_REGISTRY.

        Verifies that every series visible in the registry is surfaced by the CLI,
        and that no extra series appear in CLI output that are not in the registry.

        This test fails pre-migration because RULE_REGISTRY only has 3 series
        while the full migration requires 14.
        """
        import skilllint.plugin_validator as plugin_validator

        result = cli_runner.invoke(plugin_validator.app, ["rules"])
        assert result.exit_code == 0, f"'skilllint rules' exited with code {result.exit_code}. Output: {result.stdout}"

        cli_series = _cli_series_from_output(result.stdout)
        registry_series = _registered_prefixes()

        # Every series in the registry must appear in CLI output
        missing_from_cli = registry_series - cli_series
        assert not missing_from_cli, (
            f"Series in RULE_REGISTRY but not in 'skilllint rules' output: "
            f"{sorted(missing_from_cli)}. CLI output series: {sorted(cli_series)}."
        )

        # Every series in CLI output must be in the registry
        extra_in_cli = cli_series - registry_series
        assert not extra_in_cli, (
            f"Series in 'skilllint rules' output but not in RULE_REGISTRY: "
            f"{sorted(extra_in_cli)}. Registry series: {sorted(registry_series)}."
        )

        # Final gate: the combined set must reach MIN_REGISTERED_SERIES
        assert len(cli_series) >= MIN_REGISTERED_SERIES, (
            f"'skilllint rules' shows {len(cli_series)} series; "
            f"requires at least {MIN_REGISTERED_SERIES}. "
            f"Shown: {sorted(cli_series)}."
        )


class TestReadmeTableMatchesRegistry:
    """Assert README 'What gets validated' table matches registered series."""

    def test_readme_table_matches_registered_series(self) -> None:
        """README 'What gets validated' table must list every registered series.

        Each series prefix present in RULE_REGISTRY must appear in the README
        table so documentation stays in sync with code.

        Pre-migration this test passes trivially for the 3 existing series.
        It becomes a meaningful guard during T14 (documentation sync) when
        all 14 series must be in both the registry and the README.
        """
        registry_series = _registered_prefixes()
        readme_series = _readme_series_from_table()

        missing_from_readme = registry_series - readme_series
        assert not missing_from_readme, (
            f"Series registered in RULE_REGISTRY but missing from README 'What gets validated' "
            f"table: {sorted(missing_from_readme)}. "
            f"README series: {sorted(readme_series)}. "
            f"Update README.md to document all registered series."
        )

    def test_readme_table_completeness_against_expected(self) -> None:
        """README table must eventually list all 14 expected series.

        This test fails until T14 updates the README to include all series.
        It is a documentation completeness gate, not a registry gate.
        """
        readme_series = _readme_series_from_table()
        missing = _EXPECTED_SERIES - readme_series
        assert not missing, (
            f"Expected series not yet in README 'What gets validated' table: "
            f"{sorted(missing)}. "
            f"README currently lists: {sorted(readme_series)}. "
            f"T14 must add documentation rows for these series."
        )
