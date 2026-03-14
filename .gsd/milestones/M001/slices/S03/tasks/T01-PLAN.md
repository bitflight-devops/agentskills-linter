---
estimated_steps: 5
estimated_files: 4
---

# T01: Build schema refresh script and consolidate brownfield loader

**Slice:** S03 — Refreshable schema ingestion and brownfield migration
**Milestone:** M001

## Description

Create the schema refresh script that can regenerate versioned provider schemas with provenance metadata, and eliminate the duplicate `_schema_loader.py` so all code uses the canonical `schemas/__init__.py` loader.

## Steps

1. Create `scripts/refresh_schemas.py` that: reads each provider's current latest schema, bumps the version (v1→v2), updates `provenance.last_verified` to current timestamp, preserves all constraint_scope annotations, writes the new versioned file. Support `--bump` (write), `--dry-run` (show diff), `--provider` (single provider).
2. Find all imports of `_schema_loader` across the codebase: `grep -rn "_schema_loader" packages/skilllint/ --include="*.py"`. Replace each with the equivalent `load_provider_schema()` call from `schemas.__init__`.
3. Delete `packages/skilllint/_schema_loader.py`.
4. Update `schemas/__init__.py` if needed to support discovering the latest version (highest vN) for a provider, so the refresh script and loaders stay in sync.
5. Run existing tests to confirm no regressions: `cd packages/skilllint && python -m pytest tests/ -x -q`.

## Must-Haves

- [ ] `scripts/refresh_schemas.py` exists with `--bump`, `--dry-run`, `--provider` flags
- [ ] Refresh generates schemas with valid provenance (authority_url, last_verified, provider_id)
- [ ] `_schema_loader.py` deleted and no code references it
- [ ] Existing tests pass unchanged

## Verification

- `python scripts/refresh_schemas.py --dry-run` exits 0 and prints proposed changes
- `grep -r "_schema_loader" packages/skilllint/ --include="*.py" | grep -v __pycache__` returns empty
- `cd packages/skilllint && python -m pytest tests/ -x -q` passes

## Inputs

- `packages/skilllint/schemas/__init__.py` — canonical loader from S01
- `packages/skilllint/_schema_loader.py` — duplicate loader to eliminate
- `packages/skilllint/schemas/*/v1.json` — current provider schemas with provenance shape
- `scripts/fetch_platform_docs.py` — reference for existing scraping patterns

## Expected Output

- `scripts/refresh_schemas.py` — new schema refresh/regeneration script
- `packages/skilllint/_schema_loader.py` — deleted
- Any files that imported `_schema_loader` — updated to use `schemas.__init__`

## Observability Impact

- **Signals added:** Refresh script emits per-provider progress to stderr (provider_id, version bump, timestamp). Structured error messages for invalid provider ID or malformed schema JSON.
- **How future agent inspects:** Run `python scripts/refresh_schemas.py --dry-run --verbose` to see proposed changes and constraint_scope preservation status. Run with `--provider <name>` to scope to single provider.
- **Failure state visibility:** Exit code 1 = provider not found or schema validation error (with file path and error message). Exit code 2 = file write failure. STDERR contains structured error with actionable message.
