# S03: Refreshable schema ingestion and brownfield migration

**Goal:** Maintainers can refresh bundled provider schema artifacts through a supported script, and all brownfield code uses the single canonical loader.
**Demo:** `python scripts/refresh_schemas.py --bump` regenerates versioned schemas; `_schema_loader.py` is eliminated; all tests pass using `load_provider_schema()` from `schemas/__init__.py`.

## Must-Haves

- A schema refresh script that can bump schema versions with valid provenance metadata
- Elimination of the duplicate `_schema_loader.py` loader — single canonical path through `schemas/__init__.py`
- Refreshed schemas pass existing contract tests (`test_provider_contracts.py`)
- Packaging verification: refreshed schemas loadable via `importlib.resources`

## Proof Level

- This slice proves: operational (refresh workflow + brownfield consolidation)
- Real runtime required: yes (script execution, importlib.resources loading)
- Human/UAT required: no

## Observability / Diagnostics

- **Runtime signals:** Refresh script emits structured output to stderr for each provider processed (provider_id, old_version → new_version, provenance.last_verified timestamp). Exit code 0 = success, 1 = validation error, 2 = write failure.
- **Inspection surfaces:** `--dry-run` shows JSON diff of proposed changes without writing; `--verbose` flag includes per-field constraint_scope preservation status.
- **Failure visibility:** Invalid schema JSON returns structured error with file path, parse error, and line number. Missing provenance fields reported explicitly (e.g., `provenance.authority_url: required field missing`).
- **Redaction:** Provenance URLs and timestamps are public data; no secrets in schemas. No redaction required.

## Verification

- `python scripts/refresh_schemas.py --dry-run` shows proposed schema changes without writing
- `python scripts/refresh_schemas.py --bump` writes v2 schemas with valid provenance
- `cd packages/skilllint && python -m pytest tests/test_provider_contracts.py tests/test_bundled_schema.py tests/test_schema_refresh.py -v` — all pass
- `grep -r "_schema_loader" packages/skilllint/ --include="*.py" | grep -v __pycache__` — returns nothing (brownfield eliminated)
- `python scripts/refresh_schemas.py --provider nonexistent 2>&1` exits 1 and prints structured error: `error: provider 'nonexistent' not found. Available: [claude_code, cursor, codex, ...]`

## Integration Closure

- Upstream surfaces consumed: `schemas/__init__.py` (load_provider_schema, get_provider_ids), S01 provenance metadata shape, `scripts/fetch_platform_docs.py` (existing scraping logic)
- New wiring introduced: `scripts/refresh_schemas.py` refresh command, consolidated loader path
- What remains before milestone is truly usable end-to-end: S04 proves installed-runtime loading of refreshed artifacts through real CLI

## Tasks

- [x] **T01: Build schema refresh script and consolidate brownfield loader** `est:1h`
  - Why: No automated way to regenerate versioned schemas exists, and `_schema_loader.py` is a duplicate loader that must be eliminated for a single canonical path
  - Files: `scripts/refresh_schemas.py`, `packages/skilllint/_schema_loader.py`, `packages/skilllint/schemas/__init__.py`
  - Do: (1) Create `scripts/refresh_schemas.py` that reads current provider schemas, bumps version, updates provenance timestamps, writes new versioned files. Support `--bump`, `--dry-run`, and `--provider` flags. (2) Find all imports of `_schema_loader` and replace with `schemas.__init__` equivalents. (3) Delete `_schema_loader.py`.
  - Verify: `python scripts/refresh_schemas.py --dry-run` succeeds; `grep -r "_schema_loader" packages/skilllint/ --include="*.py" | grep -v __pycache__` returns empty
  - Done when: Refresh script generates valid versioned schemas and no code references `_schema_loader`

- [x] **T02: Add refresh and packaging verification tests** `est:45m`
  - Why: The refresh → load roundtrip and brownfield elimination need regression coverage
  - Files: `packages/skilllint/tests/test_schema_refresh.py`, `packages/skilllint/tests/test_bundled_schema.py`
  - Do: (1) Write `test_schema_refresh.py` testing: refresh script generates valid JSON with provenance, version bumping increments correctly, dry-run doesn't write files. (2) Extend `test_bundled_schema.py` to verify all providers (not just claude_code) load via importlib.resources. (3) Run full test suite to confirm no regressions.
  - Verify: `cd packages/skilllint && python -m pytest tests/test_schema_refresh.py tests/test_bundled_schema.py tests/test_provider_contracts.py -v` — all pass
  - Done when: Refresh roundtrip and multi-provider packaging are covered by passing tests

## Files Likely Touched

- `scripts/refresh_schemas.py`
- `packages/skilllint/_schema_loader.py`
- `packages/skilllint/schemas/__init__.py`
- `packages/skilllint/tests/test_schema_refresh.py`
- `packages/skilllint/tests/test_bundled_schema.py`
