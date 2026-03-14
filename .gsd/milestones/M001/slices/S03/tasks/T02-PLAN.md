---
estimated_steps: 4
estimated_files: 3
---

# T02: Add refresh and packaging verification tests

**Slice:** S03 — Refreshable schema ingestion and brownfield migration
**Milestone:** M001

## Description

Add test coverage for the schema refresh roundtrip and verify multi-provider packaging integrity. This locks the refresh contract so future changes don't silently break schema generation or importlib.resources loading.

## Steps

1. Create `packages/skilllint/tests/test_schema_refresh.py` with tests: (a) refresh script generates valid JSON with all required provenance fields, (b) version bumping produces correct filename (vN+1), (c) dry-run mode doesn't write files, (d) constraint_scope annotations are preserved in refreshed output.
2. Extend `packages/skilllint/tests/test_bundled_schema.py` to test all providers returned by `get_provider_ids()` (currently only tests claude_code).
3. Run the full test suite: `cd packages/skilllint && python -m pytest tests/ -v`.
4. Verify no regressions in `test_provider_contracts.py` and `test_provider_validation.py`.

## Must-Haves

- [ ] `test_schema_refresh.py` covers refresh generation, version bump, dry-run, provenance preservation
- [ ] `test_bundled_schema.py` covers all providers, not just claude_code
- [ ] All existing tests continue to pass

## Verification

- `cd packages/skilllint && python -m pytest tests/test_schema_refresh.py tests/test_bundled_schema.py tests/test_provider_contracts.py -v` — all pass
- `cd packages/skilllint && python -m pytest tests/ -q` — no regressions

## Inputs

- `scripts/refresh_schemas.py` — from T01
- `packages/skilllint/schemas/__init__.py` — canonical loader
- `packages/skilllint/tests/test_bundled_schema.py` — existing tests to extend
- `packages/skilllint/tests/test_provider_contracts.py` — existing contract tests

## Expected Output

- `packages/skilllint/tests/test_schema_refresh.py` — new test file
- `packages/skilllint/tests/test_bundled_schema.py` — extended with multi-provider coverage

## Observability Impact

**Signals added:**
- Test failures now surface refresh contract violations: missing provenance fields, incorrect version bumping, dry-run safety, and constraint_scope loss.
- Multi-provider test coverage surfaces when a new provider schema fails to load via importlib.resources or lacks required provenance.

**How a future agent inspects:**
- Run `cd packages/skilllint && python -m pytest tests/test_schema_refresh.py -v` to see per-test refresh contract validation.
- Run `cd packages/skilllint && python -m pytest tests/test_bundled_schema.py -v` to verify all providers load correctly.

**Failure visibility:**
- `test_refresh_generates_valid_json` fails → refresh script produces malformed output.
- `test_version_bump_correct_filename` fails → version bumping logic is broken.
- `test_dry_run_no_write` fails → dry-run mode is writing files (safety violation).
- `test_constraint_scope_preserved` fails → refresh drops field-level annotations.
- Multi-provider parametrized tests fail → new provider schemas have missing/invalid structure.
