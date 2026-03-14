---
id: T02
parent: S03
milestone: M001
provides:
  - Schema refresh contract tests validating generation, version bump, dry-run safety, and constraint_scope preservation
  - Multi-provider packaging verification for all providers via importlib.resources
key_files:
  - packages/skilllint/tests/test_schema_refresh.py
  - packages/skilllint/tests/test_bundled_schema.py
key_decisions:
  - Used parametrized pytest tests (@pytest.mark.parametrize) to cover all providers dynamically via get_provider_ids()
  - Separated test concerns: TestSchemaFileImportlibAccess for importlib.resources access, TestLoadProviderSchema for loader function, TestBackwardsCompatibleAlias for legacy API
patterns_established:
  - Parametrized multi-provider tests discover providers at collection time, ensuring new providers are automatically covered
  - Schema refresh tests monkey-patch rs.SCHEMAS_DIR for filesystem isolation in tests that need temp directories
observability_surfaces:
  - Test failures surface refresh contract violations: missing provenance fields, incorrect version bumping, dry-run safety, constraint_scope loss
  - Multi-provider test failures surface importlib.resources loading issues for any provider
duration: 20m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T02: Add refresh and packaging verification tests

**Added comprehensive test coverage for schema refresh roundtrip and multi-provider packaging verification.**

## What Happened

Created `test_schema_refresh.py` with 20 tests covering:
- Valid JSON generation with all required provenance fields
- Version bumping produces correct vN+1 filename
- Dry-run mode doesn't write files (safety)
- constraint_scope annotations preserved in refreshed output
- Provider discovery functionality

Extended `test_bundled_schema.py` from 7 hardcoded claude_code tests to 24 parametrized tests covering all providers (claude_code, cursor, codex, agentskills_io) via `get_provider_ids()`.

Also added missing `## Observability Impact` section to T02-PLAN.md as pre-flight fix.

## Verification

- `cd packages/skilllint && uv run python -m pytest tests/test_schema_refresh.py tests/test_bundled_schema.py tests/test_provider_contracts.py -v` — **72 tests passed**
- `cd packages/skilllint && uv run python -m pytest tests/ -q` — **639 passed, 1 skipped, no regressions**

## Diagnostics

To inspect what this task built:
- `cd packages/skilllint && uv run python -m pytest tests/test_schema_refresh.py -v` — per-test refresh contract validation
- `cd packages/skilllint && uv run python -m pytest tests/test_bundled_schema.py -v` — multi-provider loading verification

## Deviations

None. All steps in task plan executed as specified.

## Known Issues

None.

## Files Created/Modified

- `packages/skilllint/tests/test_schema_refresh.py` — **created** — 20 tests for schema refresh contract
- `packages/skilllint/tests/test_bundled_schema.py` — **rewritten** — parametrized all providers (4 providers × 6 tests = 24 tests)
- `.gsd/milestones/M001/slices/S03/tasks/T02-PLAN.md` — **modified** — added missing Observability Impact section
