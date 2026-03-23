"""Dynamic fixture loader for rule validation tests.

Discovers fixture directories under
tests/fixtures/providers/{platform}/{failing-examples,passing-examples}/{rule-id}/,
reads fixture.toml metadata, and yields FixtureCase objects for parametrized pytest
tests.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "providers"

_KIND_DIRS = {"failing-examples", "passing-examples"}
_KIND_MAP = {"failing-examples": "failing", "passing-examples": "passing"}


@dataclass
class FixtureCase:
    """A single pass/fail test case for a rule.

    Attributes:
        rule_id: The rule identifier (e.g. "FM002").
        name: Variant name within the fixture (e.g. "unclosed-brace").
        path: Absolute path to the scannable directory for this variant.
        expected_count: Expected violation count (0 for passing, >=1 for failing).
        kind: "failing" or "passing".
        tier: Fixture tier (1-5) — describes infrastructure requirements.
        setup: Optional shell command to run in the variant directory before scanning.
        allowed_collateral: Rule codes that are acceptable co-violations for this
            variant.  Used when a trigger rule causes other validators to fire as
            a structural consequence (e.g. broken YAML prevents field extraction,
            causing name/description validators to also report missing fields).
    """

    rule_id: str
    name: str
    path: Path
    expected_count: int
    kind: str
    tier: int
    setup: str | None = None
    allowed_collateral: list[str] = field(default_factory=list)


def _cases_from_rule_dir(rule_dir: Path, default_kind: str, rule_id_filter: str | None) -> list[FixtureCase]:
    """Load FixtureCase objects from a single rule fixture directory.

    Args:
        rule_dir: Directory containing fixture.toml and variant sub-directories.
        default_kind: "failing" or "passing" inferred from the parent kind dir.
        rule_id_filter: If set, skip rule dirs whose name does not match
            (case-insensitive).

    Returns:
        List of FixtureCase objects for all valid variants found on disk.
    """
    if rule_id_filter and rule_dir.name.upper() != rule_id_filter.upper():
        return []

    toml_path = rule_dir / "fixture.toml"
    if not toml_path.exists():
        return []

    with toml_path.open("rb") as fh:
        meta = tomllib.load(fh)

    fixture_meta = meta.get("fixture", {})
    rid = fixture_meta.get("rule_id", rule_dir.name)
    tier = fixture_meta.get("tier", 1)

    cases: list[FixtureCase] = []
    for variant in meta.get("variants", []):
        variant_name = variant["name"]
        variant_dir = rule_dir / variant_name
        if not variant_dir.is_dir():
            continue
        cases.append(
            FixtureCase(
                rule_id=rid,
                name=variant_name,
                path=variant_dir,
                expected_count=variant["expected_count"],
                kind=variant.get("kind", default_kind),
                tier=tier,
                setup=variant.get("setup"),
                allowed_collateral=list(variant.get("allowed_collateral", [])),
            )
        )
    return cases


def _cases_from_kind_dir(kind_dir: Path, rule_id_filter: str | None) -> list[FixtureCase]:
    """Enumerate all rule directories within one kind directory.

    Args:
        kind_dir: A ``failing-examples`` or ``passing-examples`` directory.
        rule_id_filter: Forwarded to _cases_from_rule_dir.

    Returns:
        Flat list of FixtureCase objects across all rule directories.
    """
    kind = _KIND_MAP[kind_dir.name]
    cases: list[FixtureCase] = []
    for rule_dir in sorted(kind_dir.iterdir()):
        if rule_dir.is_dir():
            cases.extend(_cases_from_rule_dir(rule_dir, kind, rule_id_filter))
    return cases


def discover_fixtures(rule_id: str | None = None) -> list[FixtureCase]:
    """Discover all fixture cases, optionally filtered by rule_id.

    Walks the providers tree:
      fixtures/providers/{platform}/{failing-examples,passing-examples}/{rule-id}/

    Each rule-id directory must contain a fixture.toml with [[variants]] entries.
    Variants whose directory does not exist on disk are silently skipped.

    Args:
        rule_id: If provided, only return cases matching this rule ID
            (case-insensitive).

    Returns:
        List of FixtureCase objects, sorted by platform / kind / rule / variant name.
    """
    if not FIXTURES_ROOT.exists():
        return []

    cases: list[FixtureCase] = []
    for platform_dir in sorted(FIXTURES_ROOT.iterdir()):
        if not platform_dir.is_dir():
            continue
        for kind_dir in sorted(platform_dir.iterdir()):
            if kind_dir.is_dir() and kind_dir.name in _KIND_DIRS:
                cases.extend(_cases_from_kind_dir(kind_dir, rule_id))
    return cases
