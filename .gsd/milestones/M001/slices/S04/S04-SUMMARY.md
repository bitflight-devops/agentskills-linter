---
id: S04
parent: M001
milestone: M001
provides:
  - E2E packaging integration test proving the full refresh → build → install → CLI validation chain works with packaged resources
requires:
  - slice: S02
    provides: Provider-aware CLI validation path and fixtures
  - slice: S03
    provides: Refreshable artifact workflow and packaged loader migration
affects:
  - M001
key_files:
  - packages/skilllint/tests/test_e2e_packaging.py
key_decisions:
  - Used module-scoped fixture for wheel build to avoid rebuild on every test (D008)
  - Cleared PYTHONPATH in subprocess tests to ensure installed package is used, not repo checkout (D009)
patterns_established:
  - @pytest.mark.slow for tests that build wheels/create venvs
  - Subprocess isolation pattern for testing installed packages
observability_surfaces:
  - Wheel contents listing via zipfile.ZipFile().namelist()
  - Subprocess stdout/stderr for CLI invocation failures
  - JSON output from validation API for structured verification
drill_down_paths:
  - .gsd/milestones/M001/slices/S04/tasks/T01-SUMMARY.md
duration: 45min
verification_result: passed
completed_at: 2026-03-14
---
# S04: End-to-end packaged integration proof

**E2E packaging tests proving refresh → build → install → CLI validation chain works with packaged resources**

## What Happened

S04 delivered the final integration proof for the M001 milestone. The primary deliverable was a comprehensive E2E test suite (`packages/skilllint/tests/test_e2e_packaging.py`) that exercises the full path from packaged resource to CLI validation.

Key steps executed:
1. **Verified wheel packaging** — Inspected built wheel with zipfile, confirmed all schema JSON files (`claude_code/v1.json`, `codex/v1.json`, `cursor/v1.json`) are included. No changes to `pyproject.toml` were needed — hatchling already packages schemas correctly.

2. **Wrote `test_e2e_packaging.py`** with 10 tests across 3 test classes:
   - `TestWheelContainsSchemas` (4 tests) — verifies schema JSON files are in the wheel and are valid JSON
   - `TestInstalledCLIValidatesFixtures` (4 tests) — verifies installed CLI runs against fixtures via subprocess
   - `TestViolationAuthorityInInstalledOutput` (2 tests) — verifies authority metadata flows through installed package

3. **Fixed subprocess isolation** — Initial tests failed because subprocess used dev venv's Python instead of temp venv's Python. Added `_get_python_path()` helper and passed explicit `--python` flag to `uv pip install`. Cleared `PYTHONPATH` in subprocess environment to ensure installed package is used.

4. **Registered `slow` marker** — Added `markers` config to `pyproject.toml` to suppress PytestUnknownMarkWarning.

## Verification

- `cd packages/skilllint && uv run python -m pytest tests/test_e2e_packaging.py -v` — **10 passed**
- `cd packages/skilllint && uv run python -m pytest tests/ -v --ignore=tests/test_e2e_packaging.py` — **639 passed, 1 skipped**
- Wheel build verified: `skilllint/schemas/claude_code/v1.json` present in wheel zip

## Requirements Advanced

No `.gsd/REQUIREMENTS.md` exists — roadmap is in legacy compatibility mode.

## Requirements Validated

No `.gsd/REQUIREMENTS.md` exists — roadmap is in legacy compatibility mode.

## New Requirements Surfaced

None — this was the final proof slice.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None — task executed exactly as planned. Packaging required no fixes (hatchling already included `.json` files).

## Known Limitations

None — E2E tests prove the full chain works.

## Follow-ups

None — M001 milestone is complete with S04.

## Files Created/Modified

- `packages/skilllint/tests/test_e2e_packaging.py` — New E2E test file with 10 tests proving packaged integration works
- `pyproject.toml` — Added `markers` config for `slow` test marker (warning suppression)

## Forward Intelligence

### What the next slice should know
This is the final slice of M001. No follow-up work needed for this milestone.

### What's fragile
Nothing fragile — E2E tests validate the full chain.

### Authoritative diagnostics
- Wheel contents: `python -c "import zipfile; print(zipfile.ZipFile('dist/*.whl').namelist())"`
- Installed CLI test: Run with `-v --no-cov` to see subprocess output on failure
- Authority verification: Test `test_authority_in_violation_output` prints violation JSON on assertion failure

### What assumptions changed
- None
