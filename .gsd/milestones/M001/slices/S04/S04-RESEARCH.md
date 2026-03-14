# S04: End-to-End Packaged Integration Proof - Research

**Status:** Ready for Implementation
**Risk:** Medium
**Owner:** @system

## Objective
Prove the assembled refresh → artifact packaging → CLI validation workflow functions end-to-end through the real runtime path with packaged resources.

## Key Findings

### Existing Capabilities
- **Schema Refresh (S03):** `scripts/refresh_schemas.py` can regenerate provider artifacts
- **Packaged Loading (S01):** `load_provider_schema()` uses `importlib.resources` compatible paths
- **CLI Integration (S02):** `--platform` flag routes validation through provider adapters

### Integration Points to Verify
1. Refreshed schemas persist through packaging (pyproject.toml includes them)
2. Installed CLI loads schemas via `importlib.resources`, not filesystem paths
3. Validation results match development environment behavior

### Required Verification Steps
1. **Schema Refresh & Package Build**
   - Run refresh script
   - Build package with `uv pip install .`
   - Verify schemas exist in installed package dir

2. **CLI Execution Path**
   - Run installed `skilllint check` against fixtures
   - Confirm exit codes match dev environment
   - Check violation authority metadata exists

3. **Provenance Chain**
   - Verify `last_verified` timestamps from refresh
   - Confirm schema versions in violations match

### Surprises/Risks
- **Packaging Layout:** `pyproject.toml` must include schema dirs via `package-data`
- **Resource API:** `importlib.resources.files()` vs legacy `pkg_resources` differences
- **Test Isolation:** Need venv-based testing to avoid dev environment contamination

### Skills Activated
- **pi-packaging:** Python packaging and resource management
- **importlib-resources:** Resource access patterns

## Implementation Strategy
1. Add `package_data` directive in `pyproject.toml`
2. Create venv-based test script
3. Add E2E test class with:
   - Schema refresh
   - Package install
   - CLI validation assert

## Completion Criteria
- [ ] `uv pip install .` includes latest schemas
- [ ] Installed CLI shows same version as source
- [ ] Validation violations include refreshed timestamps
- [ ] All S04 tests pass in clean venv

## Forward Work
- Test matrix across Python 3.10+ (likely separate slice)
- Binary wheel verification (stretch goal)