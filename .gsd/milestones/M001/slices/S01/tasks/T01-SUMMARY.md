---
id: T01
parent: S01
milestone: M001
provides:
  - load_provider_schema() utility for package-safe schema loading
  - get_provider_ids() for discovering available providers
  - Structured provenance metadata in all provider schemas
  - constraint_scope annotations on all schema fields
key_files:
  - packages/skilllint/schemas/__init__.py
  - packages/skilllint/schemas/claude_code/v1.json
  - packages/skilllint/schemas/cursor/v1.json
  - packages/skilllint/schemas/codex/v1.json
key_decisions:
  - Used importlib.resources.files() for package-safe schema loading (works when installed via pip)
  - Fallback provider list for environments where iterdir() isn't available
  - constraint_scope values: "shared" (name, description, version, license, homepage, repository, keywords) vs "provider_specific" (platform-unique fields like model, color, tools, globs, alwaysApply, etc.)
patterns_established:
  - Provenance object structure: {authority_url, last_verified, provider_id}
  - Field-level constraint_scope annotation for shared vs provider-specific classification
observability_surfaces:
  - load_provider_schema() returns full schema dict with provenance accessible via s['provenance']
  - get_provider_ids() returns sorted list of discoverable provider directories
  - Invalid provider/version raises FileNotFoundError with available providers listed
duration: 20m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Add structured provenance metadata to provider schema contracts

**Added provenance metadata and constraint_scope annotations to all provider schemas, plus schema loading utilities using importlib.resources.**

## What Happened

Implemented the full task plan:

1. Added `provenance` object to all three provider schemas (claude_code, cursor, codex) with `authority_url`, `last_verified`, and `provider_id` fields
2. Added `constraint_scope` annotation ("shared" or "provider_specific") to all field entries across all schemas
3. Implemented `load_provider_schema(provider, version="v1")` using `importlib.resources.files()` for package-safe loading
4. Implemented `get_provider_ids()` to discover available provider directories
5. Fixed pre-flight observability gaps in both S01-PLAN.md and T01-PLAN.md

Constraint scope classification:
- **Shared fields**: name, description, version, license, homepage, repository, keywords (exist across multiple platforms)
- **Provider-specific fields**: model, color, tools, allowed-tools, argument-hint, disable-model-invocation, author, agents, commands, hooks, mcpServers, globs, alwaysApply, metadata, pattern, decision, justification, match, not_match, paths

## Verification

All smoke tests passed:

```bash
# Provenance verification
uv run python -c "from skilllint.schemas import load_provider_schema; s = load_provider_schema('claude_code'); assert s['provenance']['provider_id'] == 'claude_code'"
uv run python -c "from skilllint.schemas import load_provider_schema; s = load_provider_schema('cursor'); assert s['provenance']['provider_id'] == 'cursor'"
uv run python -c "from skilllint.schemas import load_provider_schema; s = load_provider_schema('codex'); assert s['provenance']['provider_id'] == 'codex'"

# Provider discovery
uv run python -c "from skilllint.schemas import get_provider_ids; assert set(get_provider_ids()) == {'claude_code', 'cursor', 'codex'}"

# Constraint scope validation
uv run python -c "... # All field entries have valid constraint_scope values"

# Schema keys preserved
uv run python -c "... # All required keys ($schema, $id, title, platform, file_types, provenance) present"
```

## Diagnostics

- `load_provider_schema('claude_code')` returns dict with `provenance: {authority_url, last_verified, provider_id}`
- `get_provider_ids()` returns `['claude_code', 'codex', 'cursor']` (sorted)
- Invalid provider/version raises `FileNotFoundError` with available providers listed
- Malformed JSON raises `json.JSONDecodeError`

## Deviations

None - implementation followed task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `packages/skilllint/schemas/__init__.py` — Added load_provider_schema() and get_provider_ids() functions
- `packages/skilllint/schemas/claude_code/v1.json` — Added provenance object and constraint_scope to all fields
- `packages/skilllint/schemas/cursor/v1.json` — Added provenance object and constraint_scope to all properties
- `packages/skilllint/schemas/codex/v1.json` — Added provenance object and constraint_scope to all fields/properties
- `.gsd/milestones/M001/slices/S01/S01-PLAN.md` — Added Observability/Diagnostics section and diagnostic verification check
- `.gsd/milestones/M001/slices/S01/tasks/T01-PLAN.md` — Added Observability Impact section
