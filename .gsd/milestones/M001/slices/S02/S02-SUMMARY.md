# S02: Provider-aware CLI validation on real fixtures

**Wired provider schema routing into the CLI, enabling `--platform` flag to filter validation by provider with authority provenance in violations.**

## What Happened

Connected S01's provider schema infrastructure (load_provider_schema, constraint_scope, RuleAuthority) into the real validation flow. All three platform adapters (claude_code, cursor, codex) now load schemas via `load_provider_schema()` instead of the deprecated `load_bundled_schema()`. Added `constraint_scopes()` method to the PlatformAdapter protocol and all adapter implementations, returning the set of constraint_scope values from their loaded schema.

Populated authority metadata for all AS-series rules (AS001-AS006) via the `@skilllint_rule` decorator, with origin pointing to agentskills.io and reference URLs to specification sections. Created `_make_violation()` helper that automatically includes authority from rule registry.

Updated `validate_file()` in plugin_validator.py to extract constraint_scopes from the primary adapter, logging at DEBUG level for observability. Violation dicts now include an `authority` field when the rule has provenance metadata.

Created comprehensive integration test suite (22 tests in 5 classes) proving provider-specific routing works: different platforms produce different results, authority provenance appears in violations, constraint_scope filtering works, and CLI `--platform` flag functions correctly.

## Verification

- `pytest packages/skilllint/tests/test_provider_validation.py -v` — 22 passed
- `skilllint check --platform claude-code packages/skilllint/tests/fixtures/claude_code/` — exits 0
- `skilllint check --platform cursor packages/skilllint/tests/fixtures/cursor/` — exits 0  
- `skilllint check --platform invalid-provider ...` — exits 2 with "Unknown platform" and valid choices
- Violation dicts include `authority` field with `origin` and `reference` keys
- DEBUG logging shows `constraint_scopes={'shared', 'provider_specific'}` per adapter

## Requirements Advanced

No explicit requirements tracking — `.gsd/REQUIREMENTS.md` is missing.

## Requirements Validated

None — milestone operates in legacy compatibility mode without explicit requirements.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- CLI invocation uses `skilllint.plugin_validator` module path, not `skilllint`, due to package structure (no `__main__.py`). Documented as D006 in decisions.
- `get_provider_ids()` returns `agentskills_io` as base schema directory in addition to adapter IDs. Documented as D007.

## Known Limitations

- constraint_scope-based rule filtering is wired but not actively filtering rules — the infrastructure exists but full provider-specific rule activation awaits S03/S04.

## Follow-ups

- S03 will add refresh tooling to regenerate bundled provider artifacts
- S04 will prove end-to-end packaged runtime loading works

## Files Created/Modified

- `packages/skilllint/adapters/claude_code/adapter.py` — switched to load_provider_schema(), added constraint_scopes()
- `packages/skilllint/adapters/cursor/adapter.py` — switched to load_provider_schema(), added constraint_scopes()
- `packages/skilllint/adapters/codex/adapter.py` — switched to load_provider_schema(), added constraint_scopes()
- `packages/skilllint/adapters/protocol.py` — added constraint_scopes() to Protocol definition
- `packages/skilllint/rules/as_series.py` — added authority metadata to AS001-AS006, added _make_violation() helper
- `packages/skilllint/plugin_validator.py` — added constraint_scopes extraction and logging in validate_file()
- `packages/skilllint/tests/test_provider_validation.py` — new integration test file (22 tests)
- `packages/skilllint/tests/fixtures/claude_code/invalid-skill/SKILL.md` — new fixture for AS001 testing
- `packages/skilllint/schemas/agentskills_io/v1.json` — added missing provenance key

## Forward Intelligence

### What the next slice should know
- The provider schema infrastructure is wired into the validation path and works end-to-end
- Authority metadata flows through violation output correctly
- CLI --platform flag routes to the right adapter

### What's fragile
- constraint_scopes() method exists but isn't actively filtering rules yet — full provider-specific validation needs additional work in S03/S04

### Authoritative diagnostics
- Run with DEBUG logging to see constraint_scopes per adapter
- Check violation['authority'] for provenance (origin + reference URL)

### What assumptions changed
- Original assumption: skilllint module would be invokable directly — actual: uses plugin_validator module path
