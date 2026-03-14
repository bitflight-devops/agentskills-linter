# S04: End-to-end packaged integration proof

**Goal:** Prove the assembled refresh → package build → installed CLI validation flow works through real runtime paths with `importlib.resources` loading.
**Demo:** A test installs `skilllint` into an isolated venv, runs `skilllint check --platform claude-code` against a fixture, and gets correct provider-specific violations with authority metadata — all from packaged resources.

## Must-Haves

- Schema JSON files are included in the built wheel (hatchling packaging verification)
- Installed CLI loads schemas via `importlib.resources`, not filesystem paths relative to repo checkout
- `skilllint check --platform <provider>` produces identical exit codes and violation structure from installed package as from dev environment
- Refresh → build → validate chain works end-to-end in a single test flow

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes
- Human/UAT required: no

## Verification

- `cd packages/skilllint && uv run python -m pytest tests/test_e2e_packaging.py -v` — all tests pass
- The test exercises: wheel build → venv install → CLI invocation → output validation

## Integration Closure

- Upstream surfaces consumed: `schemas/__init__.py` (load_provider_schema), `scripts/refresh_schemas.py`, `plugin_validator.py` CLI entry, adapter `constraint_scopes()`
- New wiring introduced in this slice: E2E test exercising the full chain; any packaging fixes needed to include schema artifacts
- What remains before the milestone is truly usable end-to-end: nothing — this is the final proof slice

## Tasks

- [x] **T01: Write E2E packaging integration test and fix any packaging gaps** `est:1h`
  - Why: This is the entire point of S04 — prove the installed package works end-to-end
  - Files: `packages/skilllint/tests/test_e2e_packaging.py`, `pyproject.toml` (if packaging fix needed)
  - Do: Write a test that (1) builds the wheel via `uv build`, (2) installs into a temp venv, (3) runs `skilllint check --platform claude-code` against the fixtures directory via subprocess, (4) asserts exit code and violation output contain authority metadata. Also verify schema JSON files exist in the installed package tree. If hatchling doesn't include `.json` files, add explicit `[tool.hatch.build.targets.wheel.force-include]` or similar config.
  - Verify: `cd packages/skilllint && uv run python -m pytest tests/test_e2e_packaging.py -v`
  - Done when: All E2E tests pass, proving refresh → build → install → CLI validation works with packaged resources

## Files Likely Touched

- `packages/skilllint/tests/test_e2e_packaging.py`
- `pyproject.toml` (only if packaging fix needed)

## Observability / Diagnostics

### Runtime Signals
- **Wheel contents listing**: `zipfile.ZipFile(wheel_path).namelist()` reveals exactly which files are packaged — test asserts schema JSON paths exist
- **Installed CLI subprocess output**: `subprocess.run(["skilllint", "check", ...], capture_output=True)` exposes exit code, stdout, stderr — test parses for expected violation structure
- **Schema file presence in installed venv**: `venv_path / "lib/pythonX.Y/site-packages/skilllint/schemas/<provider>/v1.json"` — direct filesystem check

### Inspection Surfaces
- **Test failure output**: Pytest assertion failures include the actual wheel contents or CLI output, making missing files or malformed output immediately visible
- **Subprocess stderr**: On CLI failure, stderr is printed in test output for root cause analysis

### Failure Visibility
- **Packaging failure**: `test_wheel_contains_schemas` lists all files in wheel, highlighting missing schemas
- **CLI execution failure**: `test_installed_cli_validates_fixtures` prints exit code, stdout, and stderr
- **Authority metadata missing**: `test_violation_authority_in_installed_output` shows actual violation JSON for diff

### Diagnostic Verification
- Test `test_wheel_contains_schemas` serves as a packaging diagnostic — if schemas are missing from wheel, this test fails with clear file listing
- Test `test_installed_cli_validates_fixtures` serves as CLI integration diagnostic — failures indicate runtime path issues
