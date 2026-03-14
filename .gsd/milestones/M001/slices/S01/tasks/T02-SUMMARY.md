---
id: T02
parent: S01
milestone: M001
provides:
  - RuleAuthority dataclass with origin and reference fields
  - RuleEntry.authority field for structured rule provenance
  - skilllint_rule decorator authority kwarg support
  - Contract tests locking metadata shape for S02/S03
key_files:
  - packages/skilllint/rule_registry.py
  - packages/skilllint/tests/test_provider_contracts.py
key_decisions:
  - Authority dict converted to RuleAuthority dataclass in decorator (not stored raw)
  - authority is optional on both decorator and RuleEntry (backwards compatible)
patterns_established:
  - RuleAuthority(origin: str, reference: str | None) for typed authority access
  - Contract tests in test_provider_contracts.py as boundary for downstream slices
observability_surfaces:
  - get_rule("SK001").authority returns RuleAuthority or None
  - load_provider_schema(p)["provenance"] returns dict with authority_url, last_verified, provider_id
duration: 20m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T02: Add structured authority to RuleEntry and write contract tests

**Added RuleAuthority dataclass, extended RuleEntry with optional authority field, updated decorator, and wrote 15 contract tests locking metadata shape for downstream slices.**

## What Happened

Fixed the observability gap in T02-PLAN.md first (pre-flight requirement), then implemented the full task:

1. Added `RuleAuthority` dataclass with `origin: str` and `reference: str | None` fields
2. Extended `RuleEntry` with `authority: RuleAuthority | None = None`
3. Updated `skilllint_rule()` decorator to accept `authority: dict | None` kwarg and convert to `RuleAuthority`
4. Wrote `test_provider_contracts.py` with 15 tests covering:
   - Schema provenance structure (3 parametrized tests)
   - Constraint scope validation (3 parametrized tests)
   - Schema loader functionality (3 tests)
   - RuleAuthority dataclass (2 tests)
   - RuleEntry authority integration (4 tests)

## Verification

- `uv run pytest packages/skilllint/tests/test_provider_contracts.py -v` — 15/15 passed
- `ruff check packages/skilllint/rule_registry.py` — no lint errors
- `uv run python -c "from skilllint.schemas import get_provider_ids; print(get_provider_ids())"` — returns `['claude_code', 'codex', 'cursor']`

## Diagnostics

- `get_rule("SK001").authority` returns `RuleAuthority` or `None`
- `load_provider_schema("claude_code")["provenance"]` returns `{authority_url, last_verified, provider_id}`
- Missing provenance keys fail contract tests immediately with specific key missing
- Invalid constraint_scope fails with provider/field/scope details

## Deviations

None — all steps executed as planned.

## Known Issues

None.

## Files Created/Modified

- `packages/skilllint/rule_registry.py` — Added RuleAuthority dataclass, extended RuleEntry, updated decorator
- `packages/skilllint/tests/test_provider_contracts.py` — New test file with 15 contract tests
- `.gsd/milestones/M001/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
