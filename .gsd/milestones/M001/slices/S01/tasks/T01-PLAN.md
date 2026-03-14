---
estimated_steps: 5
estimated_files: 4
---

# T01: Add structured provenance metadata to provider schema contracts

**Slice:** S01 — Provider schema contracts and authority metadata
**Milestone:** M001

## Description

Add top-level `provenance` metadata to each provider schema JSON file (`claude_code`, `cursor`, `codex`) and annotate field-level constraints with `constraint_scope` to distinguish shared AgentSkills rules from provider-specific ones. Create a `load_provider_schema()` utility in the schemas package that returns parsed schema data with provenance accessible, using `importlib.resources` for package-safe loading.

## Steps

1. Add `provenance` object to `packages/skilllint/schemas/claude_code/v1.json` with keys: `authority_url` (str, docs URL), `last_verified` (ISO date str), `provider_id` (str matching directory name). Do the same for `cursor/v1.json` and `codex/v1.json` with appropriate provider-specific URLs.
2. Add `constraint_scope: "shared"` or `constraint_scope: "provider_specific"` to each field entry in `file_types.*.fields.*` across all three schemas. Fields like `name` and `description` that exist on all platforms are `"shared"`; platform-unique fields are `"provider_specific"`.
3. Implement `load_provider_schema(provider: str, version: str = "v1") -> dict` in `packages/skilllint/schemas/__init__.py` using `importlib.resources.files()` to load and parse the JSON. Return the full parsed dict.
4. Add `get_provider_ids() -> list[str]` that returns available provider directory names.
5. Verify with a quick smoke: `python3 -c "from skilllint.schemas import load_provider_schema; s = load_provider_schema('claude_code'); print(s['provenance'])"`.

## Must-Haves

- [ ] All three provider schemas contain a top-level `provenance` object with `authority_url`, `last_verified`, `provider_id`
- [ ] Field-level entries include `constraint_scope` with value `"shared"` or `"provider_specific"`
- [ ] `load_provider_schema()` loads via `importlib.resources` and returns parsed dict
- [ ] Existing schema keys (`$schema`, `$id`, `title`, `platform`, `file_types`) are preserved

## Verification

- `python3 -c "from skilllint.schemas import load_provider_schema; s = load_provider_schema('claude_code', 'v1'); assert 'provenance' in s; assert s['provenance']['provider_id'] == 'claude_code'"`
- Same smoke test for `cursor` and `codex`

## Inputs

- `packages/skilllint/schemas/claude_code/v1.json` — existing schema without provenance
- `packages/skilllint/schemas/cursor/v1.json` — existing schema
- `packages/skilllint/schemas/codex/v1.json` — existing schema
- `packages/skilllint/schemas/__init__.py` — currently a namespace-only init

## Expected Output

- `packages/skilllint/schemas/claude_code/v1.json` — augmented with provenance and constraint_scope
- `packages/skilllint/schemas/cursor/v1.json` — augmented
- `packages/skilllint/schemas/codex/v1.json` — augmented
- `packages/skilllint/schemas/__init__.py` — exports `load_provider_schema`, `get_provider_ids`

## Observability Impact

- Signals added/changed: `load_provider_schema()` returns parsed dict with top-level `provenance` key; `get_provider_ids()` returns list of discoverable provider directories
- How a future agent inspects this: `python3 -c "from skilllint.schemas import load_provider_schema, get_provider_ids; s = load_provider_schema('claude_code'); print(s['provenance'])"`
- Failure state exposed: Invalid provider/version raises `FileNotFoundError` with clear message; malformed JSON raises `json.JSONDecodeError`; missing provenance keys fail smoke test assertions
