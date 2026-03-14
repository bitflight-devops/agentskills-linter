---
id: T02
parent: S02
milestone: M001
provides:
  - Integration tests proving provider-specific validation routing works
  - Tests for authority provenance in violation output
  - Tests for constraint_scope-based rule filtering
  - CLI subprocess integration tests for --platform flag
key_files:
  - packages/skilllint/tests/test_provider_validation.py
  - packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md
key_decisions:
  - D006: CLI integration tests use `skilllint.plugin_validator` module path (not `skilllint`) due to package structure
  - D007: Test for get_provider_ids() accounts for base `agentskills_io` schema directory that has no corresponding adapter
patterns_established:
  - Test fixture structure: invalid skills placed in subdirectory with SKILL.md filename to trigger AS-series rules
  - CLI tests use subprocess to verify actual process behavior with --platform flag
  - Authority provenance tested via violation dict inspection
observability_surfaces:
  - Run `pytest tests/test_provider_validation.py -v` to see all test outcomes
  - Use `--log-cli-level=DEBUG` to see constraint_scopes filtering logs during tests
duration: 1h
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T02: Integration tests proving provider-specific validation on real fixtures

**Created integration test suite proving provider-aware validation works with authority provenance.**

## What Happened

Created `packages/skilllint/tests/test_provider_validation.py` with 22 integration tests across 5 test classes:

1. **TestProviderValidationRouting**: Tests for provider-specific validation routing via `validate_file()` with `platform_override`
2. **TestAuthorityProvenance**: Tests for authority metadata in violation output (AS001-AS006)
3. **TestConstraintScopeFiltering**: Tests for `constraint_scopes()` method on all adapters
4. **TestProviderAdapterAlignment**: Tests verifying schema/adapter alignment
5. **TestCLIProviderIntegration**: Subprocess-based CLI tests for `--platform` flag

Added fixture `packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md` with invalid name to test AS001 violation detection.

Fixed test issues:
- AS-series rules only fire on files named `SKILL.md`, not on arbitrary `.md` files
- `get_provider_ids()` returns `agentskills_io` as a base schema directory in addition to adapter IDs
- CLI invocation uses `skilllint.plugin_validator` module path

## Verification

- `cd packages/skilllint && python -m pytest tests/test_provider_validation.py -v` — 22 passed
- `cd packages/skilllint && python -m pytest tests/ -x` — 524 passed, 1 skipped, 70.56% coverage
- `skilllint check --platform claude-code packages/skilllint/tests/fixtures/claude_code/` — exits 0
- `skilllint check --platform cursor packages/skilllint/tests/fixtures/cursor/` — exits 0
- `skilllint check --platform invalid-provider ...` — exits 2 with "Unknown platform" message

## Diagnostics

- Run `pytest tests/test_provider_validation.py -v -s` for verbose output with print statements
- Use `--log-cli-level=DEBUG` to see constraint_scopes filtering in action
- Check violation dicts via test output for authority field presence

## Deviations

- Task plan expected `skilllint` module invocation; actual is `skilllint.plugin_validator` due to package structure (no `__main__.py`)
- Added `agentskills_io` awareness to schema/adapter alignment tests

## Known Issues

None discovered during implementation.

## Files Created/Modified

- `packages/skilllint/tests/test_provider_validation.py` — new integration test file (22 tests)
- `packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md` — new fixture for AS001 testing
- `.gsd/milestones/M001/slices/S02/tasks/T02-PLAN.md` — added missing Observability Impact section
