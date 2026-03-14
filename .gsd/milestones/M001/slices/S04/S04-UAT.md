# S04: End-to-end packaged integration proof — UAT

**Milestone:** M001
**Written:** 2026-03-14

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All tests are automated pytest assertions. The test file `test_e2e_packaging.py` contains comprehensive assertions that verify wheel contents, CLI execution, and output structure. No human verification needed when all tests pass.

## Preconditions

- Python 3.14 with uv package manager installed
- Project dependencies installed (`cd packages/skilllint && uv sync`)
- No special server or data setup required

## Smoke Test

Quick check that the E2E test file exists and contains tests:
```bash
cd packages/skilllint && uv run python -m pytest tests/test_e2e_packaging.py --collect-only
```
**Expected:** 10 test items collected across 3 test classes.

## Test Cases

### 1. Wheel contains all provider schema files

1. Run: `cd packages/skilllint && uv run python -m pytest tests/test_e2e_packaging.py::TestWheelContainsSchemas -v`
2. **Expected:** All 4 tests pass:
   - `test_wheel_contains_all_provider_schemas` — verifies `claude_code/v1.json`, `codex/v1.json`, `cursor/v1.json` in wheel
   - `test_wheel_contains_claude_code_schema` — verifies specific provider schema present
   - `test_wheel_contains_schema_init_files` — verifies `__init__.py` files included
   - `test_wheel_schema_files_are_valid_json` — verifies schemas parse as JSON

### 2. Installed CLI runs check command successfully

1. Run: `cd packages/skilllint && uv run python -m pytest tests/test_e2e_packaging.py::TestInstalledCLIValidatesFixtures -v`
2. **Expected:** All 4 tests pass:
   - `test_installed_cli_runs_check` — CLI exits with code 0 for valid fixture
   - `test_installed_cli_validates_valid_fixture` — returns success output
   - `test_installed_cli_detects_invalid_fixture` — returns non-zero exit for invalid
   - `test_installed_cli_loads_schemas_from_package` — schema loading succeeds

### 3. Authority metadata flows through installed package

1. Run: `cd packages/skilllint && uv run python -m pytest tests/test_e2e_packaging.py::TestViolationAuthorityInInstalledOutput -v`
2. **Expected:** Both tests pass:
   - `test_authority_in_violation_output` — violation output contains authority/source fields
   - `test_schema_provenance_in_package` — schema metadata includes provenance

### 4. Full test suite passes

1. Run: `cd packages/skilllint && uv run python -m pytest tests/test_e2e_packaging.py -v`
2. **Expected:** 10 passed

### 5. Other tests still pass (regression check)

1. Run: `cd packages/skilllint && uv run python -m pytest tests/ -v --ignore=tests/test_e2e_packaging.py`
2. **Expected:** 639 passed, 1 skipped

## Edge Cases

### Empty wheel (packaging misconfiguration)

- **Test:** Manually check wheel contents
- **Command:** `python -c "import zipfile; print([f for f in zipfile.ZipFile('dist/skilllint-*.whl').namelist() if 'schema' in f])"`
- **Expected:** At least 3 schema JSON files listed (claude_code, codex, cursor)

### CLI output format mismatch

- **Test:** Run CLI directly in temp venv and inspect JSON output
- **Command:** After install, run `skilllint check --format json <fixture_path>`
- **Expected:** Valid JSON with `violations` array containing objects with `rule_id`, `message`, `source` fields

### PYTHONPATH interference

- **Test:** Run CLI with PYTHONPATH set to repo packages/
- **Command:** `PYTHONPATH=packages skilllint check --platform claude-code tests/fixtures/plugin-valid`
- **Expected:** Should still use installed package (test verifies isolation)

## Failure Signals

- **Wheel missing schemas:** `test_wheel_contains_*` tests fail with assertion showing actual wheel contents
- **CLI execution fails:** Subprocess tests print exit code, stdout, stderr on failure
- **Authority missing:** `test_authority_in_violation_output` shows actual violation JSON for diff
- **Import errors:** Test output shows Python traceback

## Requirements Proved By This UAT

No explicit requirements tracked — `.gsd/REQUIREMENTS.md` is absent.

This UAT proves the M001 success criteria:
- Schema JSON files are included in the built wheel ✓
- Installed CLI loads schemas via `importlib.resources` ✓
- `skilllint check --platform <provider>` produces correct exit codes and violation structure from installed package ✓
- Refresh → build → validate chain works end-to-end ✓

## Not Proven By This UAT

- None — S04 is the final proof slice covering the complete end-to-end path.

## Notes for Tester

- Tests are marked `@pytest.mark.slow` because they build wheels and create temp venvs. Expect ~6 seconds for full suite.
- Use `-v --no-cov` to see subprocess output clearly on failure.
- The tests verify installed package behavior by clearing PYTHONPATH in subprocess runs.
- All wheel building happens in module-scoped fixture — parallel test execution won't race on rebuild.
