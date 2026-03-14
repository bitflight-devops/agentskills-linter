# S01: Provider schema contracts and authority metadata

**Milestone:** M001
**Parent:** M001-ROADMAP.md
**Phase:** complete

## What Happened

Slice S01 implemented structured provenance metadata and rule authority tracking across all provider schemas. The slice consolidated two tasks that established the contract boundary for downstream slices.

**T01** added provenance metadata to all three provider schemas (claude_code, cursor, codex) with `authority_url`, `last_verified`, and `provider_id` fields. Each schema field received a `constraint_scope` annotation ("shared" or "provider_specific") to distinguish base AgentSkills rules from provider overlays. The `load_provider_schema()` utility was implemented using `importlib.resources.files()` for package-safe loading, along with `get_provider_ids()` for provider discovery.

**T02** added the `RuleAuthority` dataclass with `origin` and `reference` fields, extended `RuleEntry` with an optional `authority` field, and updated the `skilllint_rule()` decorator to accept `authority` as an optional kwarg. Contract tests (15 total) were written to lock the metadata shape as a boundary for S02 and S03.

## Verification

All contract tests pass:
```
cd packages/skilllint && python -m pytest tests/test_provider_contracts.py -v
# 15 passed in 1.98s
```

Observability surfaces verified:
- `get_provider_ids()` returns `['claude_code', 'codex', 'cursor']`
- `load_provider_schema('claude_code')['provenance']` returns structured dict with authority_url, last_verified, provider_id
- Invalid provider raises `FileNotFoundError` with available providers listed
- `RuleEntry` accepts optional `authority: RuleAuthority | None` field
- `skilllint_rule` decorator converts `authority: dict` kwarg to `RuleAuthority` dataclass

## Requirements Advanced

No `.gsd/REQUIREMENTS.md` exists — the roadmap operates in legacy compatibility mode.

## Requirements Validated

No `.gsd/REQUIREMENTS.md` exists.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

- No rules currently have `authority` set — the field exists but is not yet populated on any rules. S02 will wire provider-aware validation that uses these authority fields.
- The constraint_scope classification is manual; no automated way to detect shared vs provider-specific fields exists yet.

## Follow-ups

- S02 should populate authority metadata on existing AS-series rules as part of provider-aware validation
- S03 should build refresh tooling that can update provenance metadata automatically

## Files Created/Modified

- `packages/skilllint/schemas/__init__.py` — Added `load_provider_schema()` and `get_provider_ids()` using importlib.resources
- `packages/skilllint/schemas/claude_code/v1.json` — Added provenance object and constraint_scope to all fields
- `packages/skilllint/schemas/cursor/v1.json` — Added provenance object and constraint_scope to all properties
- `packages/skilllint/schemas/codex/v1.json` — Added provenance object and constraint_scope to all fields
- `packages/skilllint/rule_registry.py` — Added `RuleAuthority` dataclass, extended `RuleEntry` with authority field, updated decorator
- `packages/skilllint/tests/test_provider_contracts.py` — New test file with 15 contract tests

## Forward Intelligence

### What the next slice should know
- The schema loading utilities use `importlib.resources.files("skilllint.schemas")` which works when the package is installed via pip
- Provenance metadata is at the top level of each provider schema, not nested under individual fields
- Constraint_scope values: "shared" for name, description, version, license, homepage, repository, keywords; "provider_specific" for everything else (model, color, tools, globs, etc.)
- The decorator converts dict authority to RuleAuthority dataclass — S02 can use this to register rules with structured authority

### What's fragile
- The constraint_scope classification is manual — if new fields are added to schemas, they need to be classified manually
- No validation that authority_url is a valid URL or that last_verified is a valid date

### Authoritative diagnostics
- `load_provider_schema(provider)['provenance']` — returns the authoritative provenance dict
- `get_provider_ids()` — returns the list of available providers, useful for discovery
- The test file `test_provider_contracts.py` defines the contract — any breaking change to provenance/authority structure will fail these tests

### What assumptions changed
- Initially assumed rule authority would use freeform strings — now uses structured RuleAuthority dataclass for type safety
- Initially thought importlib.resources might not work in all environments — fallback provider list added just in case, but primary path uses importlib.resources.files()
