---
estimated_steps: 5
estimated_files: 5
---

# T01: Wire provider schema routing and authority into validation path

**Slice:** S02 — Provider-aware CLI validation on real fixtures
**Milestone:** M001

## Description

Connect S01's provider schema infrastructure (`load_provider_schema`, `constraint_scope`, `RuleAuthority`) into the real validation path. Currently, adapters use `load_bundled_schema` and ignore provider-specific constraint_scope metadata. AS-series rules lack authority metadata. Violation output doesn't surface provenance.

## Steps

1. Update each adapter (claude_code, cursor, codex) to call `load_provider_schema()` from `skilllint.schemas` and expose a `constraint_scopes()` method that returns the set of constraint_scope values from the loaded schema (shared vs provider_specific fields).
2. Add `authority={"origin": "...", "reference": "..."}` kwarg to existing `@skilllint_rule` decorators in `as_series.py` for rules that have a known source.
3. Update `validate_file()` in `plugin_validator.py` to pass provider constraint_scope context so AS-series rules can be filtered by provider relevance.
4. Update violation dict construction to include `authority` field (origin + reference) when the rule has authority metadata.
5. Verify existing test suite still passes after the wiring changes.

## Must-Haves

- [ ] Adapters use `load_provider_schema()` not just `load_bundled_schema()`
- [ ] AS-series rules have authority metadata populated
- [ ] Violation dicts include authority provenance when the rule provides it
- [ ] Constraint_scope filtering is available for per-provider rule selection
- [ ] Existing tests pass (`cd packages/skilllint && python -m pytest tests/ -x`)

## Verification

- `cd packages/skilllint && python -m pytest tests/ -x` — no regressions
- `python -c "from skilllint.schemas import load_provider_schema; s = load_provider_schema('claude_code'); print(s['provenance'])"` — proves schema loading works
- `python -c "from skilllint.rule_registry import list_rules; print([r.authority for r in list_rules() if r.authority])"` — shows rules with authority

## Observability Impact

- **Signals added:** `load_provider_schema()` calls logged at DEBUG; constraint_scope filtering emits rule counts at INFO.
- **Inspection:** Run `skilllint check --platform <provider> --verbose` to see filtered rules. Check `violation.authority` in JSON output for provenance.
- **Failure visibility:** Invalid provider IDs surface structured error with available options. Missing constraint_scope defaults to "shared" with warning log.
- **Agent inspection:** Future agents can verify wiring by checking `violation.authority` in test output or running `python -c "from skilllint.rule_registry import list_rules; print([r.authority for r in list_rules() if r.authority])"`.

## Inputs

- `packages/skilllint/schemas/__init__.py` — `load_provider_schema()` and `get_provider_ids()` from S01
- `packages/skilllint/rule_registry.py` — `RuleAuthority` dataclass and decorator support from S01
- `packages/skilllint/schemas/*/v1.json` — provider schemas with constraint_scope annotations from S01

## Expected Output

- Modified adapter files using `load_provider_schema()`
- `as_series.py` rules decorated with authority metadata
- `plugin_validator.py` passing authority/provenance through to violation output
