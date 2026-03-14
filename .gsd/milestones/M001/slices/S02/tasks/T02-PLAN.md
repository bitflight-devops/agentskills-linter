---
estimated_steps: 4
estimated_files: 1
---

# T02: Integration tests proving provider-specific validation on real fixtures

**Slice:** S02 — Provider-aware CLI validation on real fixtures
**Milestone:** M001

## Description

Write integration tests that exercise the provider-aware validation path from T01 against real fixture files. Tests must prove that different `--platform` values produce different, provider-specific results and that authority provenance is surfaced in violation output.

## Steps

1. Create `packages/skilllint/tests/test_provider_validation.py` with tests covering: (a) `validate_file()` with `platform_override='claude_code'` vs `'cursor'` produces different violation sets on shared fixtures, (b) violation dicts contain `authority` field when rule has authority metadata, (c) constraint_scope filtering restricts checks appropriately per provider.
2. Add subprocess-based CLI integration tests: run `skilllint check --platform claude-code` and `--platform cursor` on fixture dirs and assert exit codes and output differences.
3. Add a test verifying `get_provider_ids()` matches available adapters to ensure schema/adapter alignment.
4. Run the full test suite to confirm no regressions.

## Must-Haves

- [x] Tests for provider-specific validation routing (at least claude_code, cursor, codex)
- [x] Tests for authority provenance in violation output
- [x] Tests for constraint_scope-based rule filtering
- [x] All tests pass

## Verification

- `cd packages/skilllint && python -m pytest tests/test_provider_validation.py -v` — all pass
- `cd packages/skilllint && python -m pytest tests/ -x` — no regressions

## Inputs

- T01's wired validation path (adapters, authority, constraint_scope filtering)
- Existing fixtures in `packages/skilllint/tests/fixtures/{claude_code,cursor,codex}/`

## Observability Impact

Tests in this file verify the provider-aware validation path works end-to-end:

- **Test signals to verify:**
  - `validate_file()` with different `platform_override` values produces different violation sets
  - Violation dicts contain `authority` field with `origin` and `reference` keys
  - `constraint_scopes()` returns expected values per adapter
  - CLI subprocess runs with `--platform` flag exit correctly

- **Failure visibility:** Tests will fail fast if provider routing is broken — assertions compare actual violation sets between providers. Authority missing from violations will cause explicit assertion failures.

- **Inspection during debugging:**
  - Run `pytest tests/test_provider_validation.py -v -s` to see print output
  - Use `--log-cli-level=DEBUG` to see constraint_scopes filtering logs
  - JSON output fixtures in tests show expected authority structure

## Expected Output

- `packages/skilllint/tests/test_provider_validation.py` — integration test file proving provider-aware validation works
