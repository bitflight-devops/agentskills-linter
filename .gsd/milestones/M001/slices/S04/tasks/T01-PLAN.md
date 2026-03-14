---
estimated_steps: 5
estimated_files: 2
---

# T01: Write E2E packaging integration test and fix any packaging gaps

**Slice:** S04 — End-to-end packaged integration proof
**Milestone:** M001

## Description

Write an integration test that proves the full refresh → package → install → CLI validation chain works. The test builds a wheel, installs it into a temporary venv, and runs `skilllint check --platform <provider>` via subprocess against existing fixtures. Asserts that schema files are present in the installed package, exit codes are correct, and violation output includes authority metadata.

## Steps

1. Verify schema `.json` files are included in a built wheel (inspect wheel contents with `zipfile`). If missing, fix `pyproject.toml` hatch config to include them.
2. Write `test_e2e_packaging.py` with:
   - `test_wheel_contains_schemas()` — builds wheel, inspects zip for `skilllint/schemas/<provider>/v1.json`
   - `test_installed_cli_validates_fixtures()` — installs wheel in temp venv, runs `skilllint check --platform claude-code <fixture-dir>`, asserts exit code and output
   - `test_violation_authority_in_installed_output()` — parses CLI output for authority/provenance fields
3. Use `@pytest.mark.slow` or similar marker so these don't run on every `pytest` invocation (they build wheels)
4. Run the tests and fix any issues discovered
5. Run existing test suite to confirm no regressions

## Must-Haves

- [ ] Wheel contains `skilllint/schemas/claude_code/v1.json` (and other providers)
- [ ] Installed CLI runs `skilllint check --platform claude-code` successfully via subprocess
- [ ] CLI output from installed package contains authority metadata in violations
- [ ] Existing tests still pass

## Verification

- `cd packages/skilllint && uv run python -m pytest tests/test_e2e_packaging.py -v` — all new tests pass
- `cd packages/skilllint && uv run python -m pytest tests/ -v --ignore=tests/test_e2e_packaging.py` — existing tests pass

## Observability Impact

- Signals added/changed: Test output surfaces whether wheel packaging includes schemas correctly
- How a future agent inspects this: Run `test_e2e_packaging.py` — failures pinpoint whether it's a packaging, loading, or validation issue
- Failure state exposed: Wheel contents listing, subprocess stderr from CLI, missing schema paths

## Inputs

- `packages/skilllint/schemas/` — provider schema artifacts from S01
- `scripts/refresh_schemas.py` — refresh script from S03
- `packages/skilllint/tests/fixtures/claude_code/` — validation fixtures from S02
- `pyproject.toml` — current hatch build config

## Expected Output

- `packages/skilllint/tests/test_e2e_packaging.py` — new E2E test file proving installed-package validation works
- `pyproject.toml` — modified only if schema inclusion fix is needed
