---
id: T01
parent: S03
milestone: M001
provides:
  - Schema refresh script with --bump, --dry-run, --provider, --verbose flags
  - Backwards-compatible load_bundled_schema alias in schemas/__init__.py
  - Elimination of duplicate _schema_loader.py brownfield loader
key_files:
  - scripts/refresh_schemas.py
  - packages/skilllint/schemas/__init__.py
  - packages/skilllint/__init__.py
key_decisions:
  - Added load_bundled_schema as alias for load_provider_schema for backwards compatibility
patterns_established:
  - Refresh script discovers providers dynamically from schema directory
  - Version bumping finds highest vN and increments to vN+1
  - Provenance validation requires authority_url, last_verified, provider_id
observability_surfaces:
  - Refresh script emits per-provider progress to stderr with version bump and timestamp
  - Exit codes: 0=success, 1=validation error, 2=write failure
  - --dry-run shows JSON diff without writing; --verbose shows constraint_scope preservation
duration: 45min
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Build schema refresh script and consolidate brownfield loader

**Created schema refresh script and eliminated duplicate _schema_loader.py, consolidating all schema loading through schemas/__init__.py.**

## What Happened

1. **Created `scripts/refresh_schemas.py`** with full CLI support:
   - `--dry-run` (default): Shows proposed changes without writing
   - `--bump`: Writes new versioned schema files
   - `--provider NAME`: Scope to single provider
   - `--verbose`: Shows constraint_scope preservation count
   - Exit codes: 0=success, 1=validation error, 2=write failure

2. **Added `load_bundled_schema` alias** to `schemas/__init__.py` for backwards compatibility with the old `_schema_loader` API.

3. **Updated `packages/skilllint/__init__.py`** to import from `schemas` instead of `_schema_loader`.

4. **Deleted `packages/skilllint/_schema_loader.py`** - the duplicate brownfield loader is now eliminated.

5. **Added observability sections** to S03-PLAN.md and T01-PLAN.md (pre-flight fixes).

## Verification

All task-level verification checks passed:

- `python3 scripts/refresh_schemas.py --dry-run` exits 0 and prints proposed changes ✓
- `python3 scripts/refresh_schemas.py --provider nonexistent 2>&1` exits 1 with structured error ✓
- `grep -r "_schema_loader" packages/skilllint/ --include="*.py" | grep -v __pycache__` returns only a comment ✓
- `cd packages/skilllint && uv run python -m pytest tests/ -x -q` passes (592 passed, 1 skipped) ✓
- `uv run python -m pytest tests/test_bundled_schema.py tests/test_provider_contracts.py -v` passes (25 passed) ✓

Slice-level verification (partial - T02 will complete):
- `--dry-run` shows proposed changes ✓
- `--provider nonexistent` exits 1 with error ✓
- `_schema_loader` eliminated ✓
- `test_schema_refresh.py` not yet created (T02 responsibility)

## Diagnostics

To inspect what this task built:
- `python3 scripts/refresh_schemas.py --dry-run --verbose` - see all proposed schema changes
- `python3 scripts/refresh_schemas.py --provider claude_code --dry-run` - single provider inspection
- `uv run python -c "from skilllint.schemas import load_bundled_schema, get_provider_ids; print(get_provider_ids())"` - verify loader

## Deviations

None. The implementation followed the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `scripts/refresh_schemas.py` — New schema refresh script with CLI flags
- `packages/skilllint/schemas/__init__.py` — Added `load_bundled_schema` alias and export
- `packages/skilllint/__init__.py` — Updated import from `_schema_loader` to `schemas`
- `packages/skilllint/_schema_loader.py` — DELETED
- `.gsd/milestones/M001/slices/S03/S03-PLAN.md` — Added Observability/Diagnostics section
- `.gsd/milestones/M001/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section
