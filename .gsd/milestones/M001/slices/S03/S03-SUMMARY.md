---
id: S03
parent: M001
milestone: M001
provides:
  - Schema refresh script with --bump, --dry-run, --provider, --verbose flags
  - Single canonical loader path via schemas/__init__.py
  - Comprehensive test coverage for refresh roundtrip and multi-provider packaging
requires:
  - slice: S01
    provides: Versioned artifact convention, provenance metadata shape
affects:
  - S04
key_files:
  - scripts/refresh_schemas.py
  - packages/skilllint/schemas/__init__.py
  - packages/skilllint/__init__.py
  - packages/skilllint/tests/test_schema_refresh.py
  - packages/skilllint/tests/test_bundled_schema.py
key_decisions:
  - Added load_bundled_schema as alias for load_provider_schema for backwards compatibility with existing brownfield code
  - Used parametrized pytest tests to cover all providers dynamically via get_provider_ids()
  - Schema refresh tests monkey-patch rs.SCHEMAS_DIR for filesystem isolation in tests that need temp directories
patterns_established:
  - Refresh script discovers providers dynamically from schema directory
  - Version bumping finds highest vN and increments to vN+1
  - Provenance validation requires authority_url, last_verified, provider_id
  - Multi-provider tests parametrized at collection time ensure new providers are automatically covered
observability_surfaces:
  - Refresh script emits per-provider progress to stderr with version bump and timestamp
  - Exit codes: 0=success, 1=validation error, 2=write failure
  - --dry-run shows JSON diff without writing; --verbose shows constraint_scope preservation count
drill_down_paths:
  - .gsd/milestones/M001/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S03/tasks/T02-SUMMARY.md
duration: 1h5m
verification_result: passed
completed_at: 2026-03-14
---

# S03: Refreshable schema ingestion and brownfield migration

**Maintainers can refresh bundled provider schema artifacts through a supported repo workflow, and all brownfield code uses the single canonical loader.**

## What Happened

This slice delivered two major capabilities:

1. **Schema Refresh Script** (`scripts/refresh_schemas.py`): A CLI tool that reads current provider schemas, bumps versions, updates provenance timestamps, and writes new versioned files. Supports `--bump` (write), `--dry-run` (default, show changes), `--provider NAME` (scope to single provider), and `--verbose` (show constraint_scope preservation).

2. **Brownfield Consolidation**: Eliminated the duplicate `_schema_loader.py` loader. All schema loading now flows through `schemas/__init__.py` with a backwards-compatible `load_bundled_schema` alias for existing code.

3. **Test Coverage**: Added comprehensive tests in `test_schema_refresh.py` (20 tests) covering valid JSON generation, version bumping, dry-run safety, and constraint_scope preservation. Extended `test_bundled_schema.py` from 7 hardcoded tests to 24 parametrized tests covering all providers.

## Verification

All slice-level verification checks passed:

- `python3 scripts/refresh_schemas.py --dry-run` shows proposed schema changes ✓
- `python3 scripts/refresh_schemas.py --provider nonexistent` exits 1 with structured error ✓
- `grep -r "_schema_loader" packages/skilllint/ --include="*.py" | grep -v __pycache__` returns only a comment ✓
- `cd packages/skilllint && uv run python -m pytest tests/test_schema_refresh.py tests/test_bundled_schema.py tests/test_provider_contracts.py -v` — **72 tests passed** ✓
- `python3 scripts/refresh_schemas.py --dry-run --verbose` shows constraint_scope preservation counts ✓

## Requirements Advanced

This slice operates in legacy compatibility mode — `.gsd/REQUIREMENTS.md` does not exist, so no requirements tracking applies.

## Requirements Validated

This slice operates in legacy compatibility mode — `.gsd/REQUIREMENTS.md` does not exist, so no requirements tracking applies.

## New Requirements Surfaced

None — this slice delivers operational tooling rather than new feature requirements.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

- The refresh script updates `last_verified` timestamps but does not fetch fresh constraints from upstream sources (this is a refresh mechanism, not a fetch mechanism)
- The script validates provenance structure but does not validate the semantic content of schema constraints

## Follow-ups

- S04 will prove installed-runtime loading of refreshed artifacts through the real CLI

## Files Created/Modified

- `scripts/refresh_schemas.py` — New schema refresh script with CLI flags (--bump, --dry-run, --provider, --verbose)
- `packages/skilllint/schemas/__init__.py` — Added `load_bundled_schema` alias for backwards compatibility
- `packages/skilllint/__init__.py` — Updated import from `_schema_loader` to `schemas`
- `packages/skilllint/_schema_loader.py` — **DELETED** — duplicate brownfield loader eliminated
- `packages/skilllint/tests/test_schema_refresh.py` — New test file with 20 tests for schema refresh contract
- `packages/skilllint/tests/test_bundled_schema.py` — Rewritten with parametrized tests for all providers (24 tests)
- `.gsd/milestones/M001/slices/S03/S03-PLAN.md` — Added Observability/Diagnostics section
- `.gsd/milestones/M001/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section
- `.gsd/milestones/M001/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section

## Forward Intelligence

### What the next slice should know

S03 provides the refresh tooling that S04 needs to prove end-to-end integration. The key integration point is `schemas/__init__.py` which exports `load_provider_schema()` (and its `load_bundled_schema` alias) — this is what the CLI and packaged runtime will use to load refreshed artifacts.

### What's fragile

The refresh script's version bumping relies on parsing `vN.json` filenames. If a provider's schema directory contains non-versioned files (e.g., `latest.json`), the `get_latest_version()` function may return unexpected results.

### Authoritative diagnostics

- `python3 scripts/refresh_schemas.py --dry-run --verbose` — shows all proposed changes including constraint_scope counts
- `uv run python -c "from skilllint.schemas import get_provider_ids; print(get_provider_ids())"` — verify provider discovery
- Test failures in `test_schema_refresh.py` surface specific contract violations (missing provenance fields, version bump errors)

### What assumptions changed

None — S03 followed the plan exactly with no major deviations from initial assumptions.
