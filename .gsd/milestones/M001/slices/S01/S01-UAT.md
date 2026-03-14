# S01: Provider schema contracts and authority metadata — UAT

**Milestone:** M001
**Written:** 2026-03-14

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: The slice delivers structured metadata (provenance, constraint_scope, RuleAuthority) and utility functions. Verification is fully automatable — we can assert the exact shape of loaded schemas and the presence of required fields without needing human judgment.

## Preconditions

- Python 3.14+ with uv installed
- skilllint package installed or available via `uv run`
- No additional servers or data seeding required

## Smoke Test

```bash
cd packages/skilllint && uv run python -c "from skilllint.schemas import get_provider_ids; print(get_provider_ids())"
```
**Expected:** Outputs `['claude_code', 'codex', 'cursor']`

## Test Cases

### 1. Load all provider schemas with provenance

1. Run: `uv run python -c "from skilllint.schemas import load_provider_schema; providers = ['claude_code', 'cursor', 'codex']; [print(f'{p}: {load_provider_schema(p)[\"provenance\"]}') for p in providers]"`
2. **Expected:** Each provider outputs a dict containing `authority_url`, `last_verified`, and `provider_id` matching the provider name

### 2. Verify constraint_scope classification

1. Run: `uv run python -c "
from skilllint.schemas import load_provider_schema
schema = load_provider_schema('claude_code')
shared = ['name', 'description', 'version', 'license', 'homepage', 'repository', 'keywords']
for ft, ft_def in schema.get('file_types', {}).items():
    for field, field_def in ft_def.get('fields', {}).items():
        scope = field_def.get('constraint_scope', 'MISSING')
        if field in shared:
            assert scope == 'shared', f'{field} should be shared'
        print(f'{ft}.{field}: {scope}')
"`
2. **Expected:** All shared fields annotated as "shared", provider-specific fields as "provider_specific"

### 3. Schema loader rejects invalid provider

1. Run: `uv run python -c "from skilllint.schemas import load_provider_schema; load_provider_schema('nonexistent')"`
2. **Expected:** Raises `FileNotFoundError` with message containing "Available providers"

### 4. RuleAuthority dataclass works

1. Run: `uv run python -c "
from skilllint.rule_registry import RuleAuthority, RuleEntry

# Test with authority
auth = RuleAuthority(origin='test-origin', reference='/rules/TEST')
print(f'origin: {auth.origin}, reference: {auth.reference}')

# Test without reference
auth2 = RuleAuthority(origin='anthropic.com')
print(f'reference is None: {auth2.reference is None}')

# Test RuleEntry with authority
def validator(fm): return []
entry = RuleEntry(id='TEST001', fn=validator, severity='error', category='test', platforms=['agentskills'], docstring='Test', authority=auth)
print(f'RuleEntry authority: {entry.authority.origin}')
"`
2. **Expected:** All assertions pass, outputs show origin, reference, and RuleEntry integration work

### 5. skilllint_rule decorator accepts authority

1. Run: `uv run python -c "
from skilllint.rule_registry import skilllint_rule, RULE_REGISTRY

@skilllint_rule('DECO_TEST_001', severity='info', category='test', authority={'origin': 'test', 'reference': '/test'})
def deco_test(frontmatter):
    return []

entry = RULE_REGISTRY.get('DECO_TEST_001')
print(f'Decorator authority origin: {entry.authority.origin}')
print(f'Decorator authority reference: {entry.authority.reference}')
"`
2. **Expected:** Outputs show the decorator converted the dict to RuleAuthority correctly

### 6. Contract tests pass

1. Run: `cd packages/skilllint && uv run pytest tests/test_provider_contracts.py -v`
2. **Expected:** 15 tests pass with no failures

## Edge Cases

### Invalid constraint_scope value

1. Manually add a field with `"constraint_scope": "invalid"` to any schema
2. Run: `uv run pytest packages/skilllint/tests/test_provider_contracts.py::TestProviderSchemaProvenance::test_provider_schema_constraint_scopes -v`
3. **Expected:** Test fails with clear error showing which provider/field has invalid scope

### Empty provenance field

1. Remove `authority_url` from a provider schema provenance section
2. Run: `uv run pytest packages/skilllint/tests/test_provider_contracts.py::TestProviderSchemaProvenance::test_provider_schema_has_provenance -v`
3. **Expected:** Test fails indicating which required key is missing

### Missing version file

1. Request a non-existent version: `uv run python -c "from skilllint.schemas import load_provider_schema; load_provider_schema('claude_code', 'v99')"`
2. **Expected:** Raises `FileNotFoundError` indicating version not found

## Failure Signals

- `FileNotFoundError` when loading valid provider → schema files missing or importlib.resources path broken
- Test failures in `test_provider_contracts.py` → contract boundary violated, downstream slices will break
- Empty provenance dict → provenance not added to schema files
- `AttributeError` on `entry.authority` → RuleEntry.authority field not implemented

## Requirements Proved By This UAT

No `.gsd/REQUIREMENTS.md` exists — requirements tracking is not active for this project.

## Not Proven By This UAT

- Provider-aware CLI validation (S02) — not yet wired into skilllint check command
- Schema refresh tooling (S03) — not yet implemented
- Packaged installation loading (S04) — not yet verified end-to-end
- Actual provider-specific validation results — requires S02 integration

## Notes for Tester

- The test file `test_provider_contracts.py` is the source of truth for the contract — if it passes, the contract is intact
- `importlib.resources.files()` is used for loading, which works when the package is installed via pip but may behave differently in dev mode
- The `authority` field on rules is optional and defaults to None for backwards compatibility
- All three providers (claude_code, cursor, codex) should have structurally identical provenance objects
