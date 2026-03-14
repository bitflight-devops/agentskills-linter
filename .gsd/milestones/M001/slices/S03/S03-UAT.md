# S03: Refreshable schema ingestion and brownfield migration — UAT

**Milestone:** M001
**Written:** 2026-03-14

## UAT Type

- UAT mode: **artifact-driven** (the slice delivers a refresh script and test suite; verification is automated via pytest)
- Why this mode is sufficient: S03 delivers operational tooling (refresh script) and test coverage (72 tests). The verification checks defined in the slice plan are automated and pass. No human-only scenarios exist in this slice.

## Preconditions

- Python 3.12+ available as `python3`
- `uv` package manager installed
- Project dependencies installed: `uv sync`
- Working directory: project root (`/home/ubuntulinuxqa2/repos/agentskills-linter`)

## Smoke Test

```bash
python3 scripts/refresh_schemas.py --dry-run
# Expected: exits 0, prints proposed changes for all 4 providers
```

## Test Cases

### 1. Dry-run shows schema changes without writing

1. Run `python3 scripts/refresh_schemas.py --dry-run`
2. **Expected:** Exit code 0, output shows 4 providers with proposed v2.json files, no files written to disk
3. Verify: `ls packages/skilllint/schemas/*/v2.json` returns "No such file or directory"

### 2. Version bumping creates valid schemas

1. Run `python3 scripts/refresh_schemas.py --bump`
2. **Expected:** Exit code 0, v2.json files created for all 4 providers
3. Verify: Each v2.json has valid JSON with provenance.authority_url, provenance.last_verified matching today

### 3. Provider-specific refresh

1. Run `python3 scripts/refresh_schemas.py --provider claude_code --dry-run`
2. **Expected:** Only claude_code shown in output
3. Run `python3 scripts/refresh_schemas.py --provider nonexistent`
4. **Expected:** Exit code 1, error message lists available providers

### 4. Verbose mode shows constraint_scope preservation

1. Run `python3 scripts/refresh_schemas.py --dry-run --verbose`
2. **Expected:** Output includes "constraint_scope fields: N → N (preserved)" for each provider

### 5. Brownfield loader eliminated

1. Run `grep -r "_schema_loader" packages/skilllint/ --include="*.py" | grep -v __pycache__`
2. **Expected:** Returns only a comment in `schemas/__init__.py`

### 6. Backwards-compatible alias works

1. Run `uv run python -c "from skilllint.schemas import load_bundled_schema; print('OK')"`
2. **Expected:** Prints "OK" without error

### 7. Multi-provider schema loading works

1. Run `uv run python -c "from skilllint.schemas import get_provider_ids; print(get_provider_ids())"`
2. **Expected:** Shows ['agentskills_io', 'claude_code', 'codex', 'cursor']

### 8. Refresh tests pass

1. Run `cd packages/skilllint && uv run python -m pytest tests/test_schema_refresh.py -v`
2. **Expected:** 20 tests passed

### 9. Bundled schema tests pass

1. Run `cd packages/skilllint && uv run python -m pytest tests/test_bundled_schema.py -v`
2. **Expected:** 24 tests passed (parametrized across 4 providers)

### 10. Full test suite has no regressions

1. Run `cd packages/skilllint && uv run python -m pytest tests/ -q`
2. **Expected:** All tests pass (639 passed, 1 skipped)

## Edge Cases

### Invalid provider name

1. Run `python3 scripts/refresh_schemas.py --provider invalid_provider_name`
2. **Expected:** Exit code 1, structured error: "error: provider 'invalid_provider_name' not found. Available: [...]"

### Corrupted schema JSON (would be caught by validation)

1. Manually corrupt a schema file (e.g., add invalid JSON)
2. Run `python3 scripts/refresh_schemas.py --bump`
3. **Expected:** Exit code 1, error mentions parse error and line number

## Failure Signals

- Exit code 1 from refresh script → validation error (invalid schema JSON or missing provenance fields)
- Exit code 2 from refresh script → write failure (permission issue or disk full)
- Test failures in `test_schema_refresh.py` → refresh contract violated (version bump incorrect, provenance missing, dry-run unsafe)
- Test failures in `test_bundled_schema.py` → importlib.resources loading broken for one or more providers

## Requirements Proved By This UAT

No requirements tracked — `.gsd/REQUIREMENTS.md` does not exist. This slice operates in legacy compatibility mode.

## Not Proven By This UAT

- S04 (end-to-end packaged integration proof) — the installed-runtime loading of refreshed artifacts through the real CLI is not yet proven; this is S04's responsibility

## Notes for Tester

- The refresh script's `--bump` flag actually writes files. Use `--dry-run` (the default) to inspect changes without side effects.
- The script uses today's date for `last_verified` timestamps — this is intentional for a refresh operation.
- The grep for `_schema_loader` will return one line: a comment in `schemas/__init__.py`. This is expected and acceptable.
