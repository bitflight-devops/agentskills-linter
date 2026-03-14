# S01: Provider schema contracts and authority metadata

**Goal:** Provider contract artifacts and rule metadata expose structured, machine-readable provenance so downstream slices can route validation by provider and trace any rule or schema field back to its source authority.
**Demo:** `pytest` passes tests that load each provider schema, verify top-level authority metadata shape, distinguish shared vs provider-specific constraints, and confirm RuleEntry objects carry structured source authority.

## Must-Haves

- Each provider schema (`claude_code`, `cursor`, `codex`) has top-level `provenance` metadata with `authority_url`, `last_verified`, and `provider_id` fields.
- A `shared` vs `provider_specific` classification exists for schema constraints so downstream validation can distinguish base AgentSkills rules from provider overlays.
- `RuleEntry` carries a structured `authority` field (not just freeform `source` strings) with at minimum `origin` and `reference` sub-fields.
- Test file locks the metadata shape for both schema provenance and rule authority so S02/S03 can depend on it as a contract.

## Proof Level

- This slice proves: contract
- Real runtime required: no
- Human/UAT required: no

## Verification

- `cd packages/skilllint && python -m pytest tests/test_provider_contracts.py -v` — all tests pass
- Tests assert: each provider schema loads, has required provenance keys, classifies constraints as shared/provider_specific, and RuleEntry.authority is structured.
- Diagnostic check: `python3 -c "from skilllint.schemas import load_provider_schema, get_provider_ids; print(get_provider_ids())"` — returns list of available provider IDs, confirming loader discovery works

## Observability / Diagnostics

- Runtime signals: Schema load errors surface as `FileNotFoundError` (missing provider/version) or `json.JSONDecodeError` (malformed schema); provenance access returns structured dict
- Inspection surfaces: `get_provider_ids()` lists discoverable providers; `load_provider_schema(provider, version)` returns full schema dict with provenance accessible via `s['provenance']`
- Failure visibility: Invalid provider/version raises clear exception; missing provenance keys fail contract tests immediately
- Redaction constraints: None — schemas contain no secrets

## Integration Closure

- Upstream surfaces consumed: `packages/skilllint/schemas/<provider>/v1.json`, `packages/skilllint/rule_registry.py`
- New wiring introduced in this slice: provenance metadata in schema files, `authority` field on `RuleEntry`, schema loader utility for provenance access
- What remains before the milestone is truly usable end-to-end: S02 wires provider-aware CLI validation, S03 builds refresh tooling, S04 proves packaged loading

## Tasks

- [x] **T01: Add structured provenance metadata to provider schema contracts** `est:45m`
  - Why: Schema files lack top-level authority metadata; downstream slices need machine-readable provenance and shared-vs-provider classification to route validation.
  - Files: `packages/skilllint/schemas/claude_code/v1.json`, `packages/skilllint/schemas/cursor/v1.json`, `packages/skilllint/schemas/codex/v1.json`, `packages/skilllint/schemas/__init__.py`
  - Do: Add `provenance` object to each schema with `authority_url`, `last_verified`, `provider_id`. Add `constraint_scope` ("shared" | "provider_specific") to each field-level entry. Create `load_provider_schema(provider, version)` utility in `schemas/__init__.py` that returns parsed schema with provenance accessible. Ensure `importlib.resources` loading still works.
  - Verify: `python3 -c "from skilllint.schemas import load_provider_schema; s = load_provider_schema('claude_code', 'v1'); assert 'provenance' in s"`
  - Done when: All three provider schemas have provenance metadata and the loader returns it.

- [x] **T02: Add structured authority to RuleEntry and write contract tests** `est:45m`
  - Why: RuleEntry has no structured authority field, and no tests lock the metadata shape that S02/S03 depend on as a contract boundary.
  - Files: `packages/skilllint/rule_registry.py`, `packages/skilllint/tests/test_provider_contracts.py`
  - Do: Add `authority: RuleAuthority | None` dataclass field to `RuleEntry` with `origin` (str) and `reference` (str | None). Update `skilllint_rule` decorator to accept optional `authority` kwarg. Write `test_provider_contracts.py` with tests: (1) each provider schema has required provenance keys, (2) constraint_scope values are valid, (3) RuleEntry accepts and exposes authority metadata, (4) load_provider_schema returns valid data for all providers.
  - Verify: `cd packages/skilllint && python -m pytest tests/test_provider_contracts.py -v`
  - Done when: All contract tests pass, locking the metadata shape for downstream slices.

## Files Likely Touched

- `packages/skilllint/schemas/claude_code/v1.json`
- `packages/skilllint/schemas/cursor/v1.json`
- `packages/skilllint/schemas/codex/v1.json`
- `packages/skilllint/schemas/__init__.py`
- `packages/skilllint/rule_registry.py`
- `packages/skilllint/tests/test_provider_contracts.py`
