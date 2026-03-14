---
estimated_steps: 4
estimated_files: 2
---

# T02: Add structured authority to RuleEntry and write contract tests

**Slice:** S01 — Provider schema contracts and authority metadata
**Milestone:** M001

## Description

Extend `RuleEntry` with a structured `authority` field replacing freeform-only provenance, and write `test_provider_contracts.py` to lock the metadata shape of both provider schemas and rule authority as a contract boundary for S02 and S03.

## Steps

1. Add `RuleAuthority` dataclass to `rule_registry.py` with fields `origin: str` (e.g. "agent-skills.io", "anthropic.com") and `reference: str | None` (URL or doc path). Add `authority: RuleAuthority | None = None` field to `RuleEntry`.
2. Update `skilllint_rule()` decorator to accept optional `authority: dict | None` kwarg and convert it to `RuleAuthority` when present.
3. Write `packages/skilllint/tests/test_provider_contracts.py` with parametrized tests:
   - `test_provider_schema_has_provenance(provider)` — loads each schema, asserts `provenance` has required keys
   - `test_provider_schema_constraint_scopes(provider)` — asserts all field entries have valid `constraint_scope`
   - `test_rule_entry_authority_structured()` — creates a RuleEntry with authority, asserts fields accessible
   - `test_load_provider_schema_all_providers()` — calls `load_provider_schema` for each provider, asserts success
4. Run `pytest tests/test_provider_contracts.py -v` and confirm all pass.

## Must-Haves

- [ ] `RuleAuthority` dataclass exists with `origin` and `reference` fields
- [ ] `RuleEntry.authority` field exists and is optional
- [ ] `skilllint_rule` decorator accepts `authority` kwarg
- [ ] `test_provider_contracts.py` has ≥4 test cases covering schema provenance, constraint scope, rule authority, and loader

## Verification

- `cd packages/skilllint && python -m pytest tests/test_provider_contracts.py -v` — all tests pass
- `ruff check packages/skilllint/rule_registry.py` — no lint errors

## Inputs

- `packages/skilllint/schemas/__init__.py` — T01's `load_provider_schema` and `get_provider_ids`
- `packages/skilllint/rule_registry.py` — existing RuleEntry without authority
- T01's augmented schema files with provenance and constraint_scope

## Expected Output

- `packages/skilllint/rule_registry.py` — extended with `RuleAuthority` and updated `RuleEntry`
- `packages/skilllint/tests/test_provider_contracts.py` — new test file locking contract shape

## Observability Impact

**Signals added:**
- `RuleEntry.authority` field exposes structured origin/reference for any decorated rule
- `RuleAuthority` dataclass provides typed access via `.origin` and `.reference` attributes

**Inspection surface:**
- `get_rule("SK001").authority` returns `RuleAuthority` or `None`
- `load_provider_schema(p)['provenance']` returns dict with `authority_url`, `last_verified`, `provider_id`

**Failure visibility:**
- Missing provenance keys → contract test fails immediately with specific key missing
- Invalid constraint_scope → contract test fails listing invalid value
- Rule authority not structured → test fails showing expected vs actual shape

**Diagnostic check:**
```python
from skilllint.rule_registry import get_rule, RuleAuthority
from skilllint.schemas import load_provider_schema

# Check rule authority structure
rule = get_rule("SK001")
if rule and rule.authority:
    print(f"origin={rule.authority.origin}, ref={rule.authority.reference}")

# Check schema provenance structure
schema = load_provider_schema("claude_code")
print(schema["provenance"])  # {authority_url, last_verified, provider_id}
```
