"""Parametrized rule fixture tests.

Each fixture directory discovered under tests/fixtures/providers/ becomes one
test case.  The test copies the fixture to a temporary directory, runs any
declared setup command, invokes the skilllint scanner, and asserts:

- Failing fixtures: produce exactly the expected number of the declared rule
  violation and no violations for any OTHER rule (some info-level codes are
  always emitted regardless of fixture content and are unconditionally exempt).
- Passing fixtures: produce zero violations of any kind (exempt codes still
  excluded from the assertion).

Scope and strategy
------------------
This module is a black-box integration harness.  It does not test individual
validator functions — those live in their dedicated test_*.py modules.  Instead
it validates that the fixture files themselves accurately represent the rule
behaviours they claim to demonstrate, giving us executable documentation and
a regression guard against fixture rot.

Test isolation: every test gets its own tmp_path copy of the fixture tree so
that setup commands (chmod, etc.) never mutate the committed fixture files.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from skilllint.plugin_validator import ValidationIssue, ValidationResult, validate_single_path
from skilllint.scan_runtime import _discover_validatable_paths, _load_plugin_json

# ---------------------------------------------------------------------------
# fixture_loader import
#
# fixture_loader.py lives in packages/skilllint/tests/ alongside the test
# files.  That directory has no __init__.py so it is not a package and
# relative imports do not work.  pytest adds the directory of each test file
# to sys.path in its default "prepend" importmode, making `fixture_loader`
# importable as a top-level name at runtime.  However the static type checker
# (ty) does not search that path, so we load it via importlib to silence the
# false-positive unresolved-import diagnostic while keeping full runtime
# functionality.
# ---------------------------------------------------------------------------

_fixture_loader_spec = importlib.util.spec_from_file_location(
    "fixture_loader", Path(__file__).parent / "fixture_loader.py"
)
assert _fixture_loader_spec is not None
assert _fixture_loader_spec.loader is not None
_fixture_loader_mod = importlib.util.module_from_spec(_fixture_loader_spec)
# Register before exec_module so @dataclass can resolve cls.__module__ via
# sys.modules (required on Python 3.14).
sys.modules.setdefault("fixture_loader", _fixture_loader_mod)
_fixture_loader_spec.loader.exec_module(_fixture_loader_mod)  # type: ignore[union-attr]

FixtureCase = _fixture_loader_mod.FixtureCase
discover_fixtures = _fixture_loader_mod.discover_fixtures

# ---------------------------------------------------------------------------
# Module-level fixture discovery
# ---------------------------------------------------------------------------

ALL_FIXTURES: list[FixtureCase] = discover_fixtures()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Issue codes that are always exempt from the "no unexpected violations" check.
# These are emitted unconditionally by the scanner regardless of fixture content:
#
#   TC001 — info-level token count, emitted for every .md file scanned.
#   PL001 — info emitted when nested Claude CLI sessions prevent plugin
#            structure validation.  This is an environment constraint, not a
#            fixture content issue, so it must never cause a fixture test to
#            fail.
_ALWAYS_EXEMPT: frozenset[str] = frozenset({"TC001", "PL001"})


def _collect_issues(fixture_dir: Path) -> list[ValidationIssue]:
    """Scan fixture_dir the same way the CLI does and return all issues.

    Replicates the CLI expansion step: calls _discover_validatable_paths to
    resolve the directory into individual file / plugin-root paths, then calls
    validate_single_path on each one.  This is required because
    validate_single_path raises typer.Exit(2) when passed a bare directory it
    cannot classify as a known file type.

    Args:
        fixture_dir: Absolute path to the copied fixture directory.

    Returns:
        Flat list of all ValidationIssue objects (errors + warnings + info)
        produced across all discovered paths.
    """
    expanded = _discover_validatable_paths(fixture_dir)
    issues: list[ValidationIssue] = []
    for path in expanded:
        file_results = validate_single_path(path, check=True, fix=False, verbose=False)
        for validator_pairs in file_results.values():
            for _validator_name, result in validator_pairs:
                if isinstance(result, ValidationResult):
                    issues.extend(result.errors)
                    issues.extend(result.warnings)
                    issues.extend(result.info)
    return issues


def _fixture_id(case: FixtureCase) -> str:
    """Generate a readable pytest node ID.

    Format: ``{RULE_ID}-{kind}-{variant-name}``
    Example: ``FM002-failing-unclosed-brace``

    Args:
        case: The fixture case to generate an ID for.

    Returns:
        Hyphen-separated string safe for pytest node IDs.
    """
    return f"{case.rule_id}-{case.kind}-{case.name}"


# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

_IS_WINDOWS = sys.platform == "win32"


def _needs_git(case: FixtureCase) -> bool:
    """Return True if this fixture requires git infrastructure (PR003/PR004)."""
    return case.rule_id.upper() in {"PR003", "PR004"}


def _git_available() -> bool:
    """Return True if git is available on PATH."""
    return shutil.which("git") is not None


# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_plugin_json_cache() -> None:
    """Clear the @functools.cache on _load_plugin_json between tests.

    The scanner caches plugin.json reads keyed by plugin_root Path.  Without
    clearing this cache, AS008 fixtures sharing the same tmp_path prefix can
    return stale data from a previous test's tmp directory.

    Tests:  cache isolation
    How:    call cache_clear() before every test via autouse=True
    Why:    tmp_path directories are unique per test but the cache key is the
            Path object — different paths, so normally safe.  We clear anyway
            as a defensive measure against future refactors that reuse paths.
    """
    _load_plugin_json.cache_clear()


@pytest.fixture
def prepared_fixture(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    """Copy a fixture tree to tmp_path and run any declared setup command.

    Tests:  fixture isolation and setup
    How:    shutil.copytree into a unique tmp_path sub-directory, then run
            case.setup as a shell command in that directory if set.
    Why:    setup commands (chmod, symlink creation) must not mutate committed
            fixture files — tests must be independently repeatable.

    Args:
        request: pytest request object carrying the FixtureCase via indirect param.
        tmp_path: pytest-provided unique temporary directory.

    Returns:
        Absolute path to the copied, set-up fixture directory.
    """
    case: FixtureCase = request.param
    dest = tmp_path / case.rule_id / case.kind / case.name
    shutil.copytree(case.path, dest)

    if case.setup:
        subprocess.run(case.setup, shell=True, cwd=str(dest), check=True)

    return dest


# ---------------------------------------------------------------------------
# Parametrized test
# ---------------------------------------------------------------------------


def _make_params() -> tuple[list[tuple[FixtureCase, FixtureCase]], list[str]]:
    """Build parametrize args and IDs from ALL_FIXTURES.

    Returns:
        Tuple of (param_pairs, ids) where param_pairs is a list of
        (case, case) tuples (indirect fixture receives first element,
        direct case receives second) and ids is the list of node ID strings.
    """
    params = [(c, c) for c in ALL_FIXTURES]
    ids = [_fixture_id(c) for c in ALL_FIXTURES]
    return params, ids


_PARAMS, _IDS = _make_params()


@pytest.mark.skipif(not ALL_FIXTURES, reason="No fixture cases discovered — fixtures/providers/ is empty")
@pytest.mark.parametrize(("prepared_fixture", "case"), _PARAMS, ids=_IDS, indirect=["prepared_fixture"])
def test_rule_fixture(prepared_fixture: Path, case: FixtureCase) -> None:
    """Each fixture directory must produce exactly its declared violation count.

    Tests:  rule validator correctness against canonical fixture trees
    How:
        1. Copy fixture tree to tmp_path (via prepared_fixture fixture).
        2. Run any declared setup command (chmod, etc.).
        3. Expand the fixture directory to individual paths via
           _discover_validatable_paths (mirrors the CLI expansion step).
        4. Invoke validate_single_path on each discovered path.
        5. Assert violation counts match fixture.toml declarations.
    Why:    Fixtures are executable documentation — they must accurately
            represent the rule behaviour they claim to demonstrate, and must
            not silently drift as validators evolve.

    Skip conditions:
        - Tier-5 fixtures on Windows (POSIX permissions / symlinks not supported).
        - Git-dependent fixtures (PR003/PR004) when git is not on PATH.

    Args:
        prepared_fixture: Path to the copied, set-up fixture directory.
        case: The FixtureCase metadata from fixture.toml.
    """
    # --- Skip conditions ---
    if case.tier >= 5 and _IS_WINDOWS:
        pytest.skip(f"Tier-5 fixture {case.rule_id}/{case.name} requires POSIX filesystem semantics")

    if _needs_git(case) and not _git_available():
        pytest.skip(f"Fixture {case.rule_id}/{case.name} requires git on PATH")

    # --- Act ---
    issues = _collect_issues(prepared_fixture)

    # --- Assert ---
    if case.kind == "passing":
        # Passing fixtures must produce ZERO violations.
        # Always-exempt codes (TC001, PL001) are excluded — they fire
        # unconditionally regardless of fixture content.
        real_issues = [i for i in issues if i.code not in _ALWAYS_EXEMPT]
        assert not real_issues, (
            f"Passing fixture {case.rule_id}/{case.name} produced unexpected violations:\n"
            + "\n".join(f"  [{i.code}] {i.field}: {i.message}" for i in real_issues)
        )
    else:
        # Failing fixtures must produce exactly the declared count of the target rule.
        matching = [i for i in issues if i.code == case.rule_id]
        assert len(matching) == case.expected_count, (
            f"Expected {case.expected_count} {case.rule_id} violation(s) in "
            f"fixture {case.rule_id}/{case.name}, got {len(matching)}.\n"
            "All issues found:\n" + "\n".join(f"  [{i.code}] {i.field}: {i.message}" for i in issues)
        )

        # Failing fixtures must NOT produce violations for OTHER rules.
        # Always-exempt codes fire unconditionally — exclude them.
        # allowed_collateral codes are declared in fixture.toml for violations
        # that are structural consequences of the trigger rule (e.g. broken YAML
        # prevents field extraction, causing name/description validators to fire).
        exempt = _ALWAYS_EXEMPT | set(case.allowed_collateral)
        unexpected = [i for i in issues if i.code != case.rule_id and i.code not in exempt]
        assert not unexpected, (
            f"Fixture {case.rule_id}/{case.name} triggered unexpected rule violations "
            f"(fixture content should be valid except for {case.rule_id}):\n"
            + "\n".join(f"  [{i.code}] {i.field}: {i.message}" for i in unexpected)
        )
