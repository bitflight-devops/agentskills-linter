# S03: Refreshable Schema Ingestion and Brownfield Migration - Research

## Current State Analysis

### Schema Generation Workflow
- Existing `scripts/fetch_platform_docs.py` scrapes provider docs but outputs unversioned schemas
- Manual process required to convert scraped data to versioned JSON schemas
- No automated version bump or provenance tracking in generation process

### Brownfield Dependencies
- `plugin_validator.py` still contains hardcoded schema references
- 23 direct filesystem accesses to schema paths in test files
- `packages/skilllint/schemas/` contains legacy non-versioned files

### Packaging Constraints
- `importlib.resources` requires __init__.py in schema directories
- PyPI packaging test reveals missing schema files in built distribution

## Key Gaps
1. No version-aware schema regeneration pipeline
2. Legacy code still accesses schemas via direct filesystem paths
3. Missing provenance preservation in refresh process
4. No schema diffing capability for change validation

## Proposed Approach

### Phase 1 - Refresh Automation
1. Extend `fetch_platform_docs.py` to:
   - Output versioned schemas using `v${N+1}` semver
   - Preserve existing constraint_scope annotations
   - Generate provenance metadata with current timestamp
2. Add schema validation step using JSON Schema meta-schema
3. Implement dry-run mode showing proposed changes

### Phase 2 - Brownfield Migration
1. Replace all direct schema accesses with `load_provider_schema()`
2. Add deprecation warnings for legacy schema paths
3. Create schema compatibility shim for tests

### Phase 3 - Packaging Verification
1. Add `conftest.py` hook to validate schema packaging
2. Implement install-local schema loading test
3. Verify resource loading in zip-safe mode

## Verification Strategy

| Verification Type       | Method                                          | Success Criteria                          |
|--------------------------|-------------------------------------------------|-------------------------------------------|
| Schema Refresh           | `python scripts/fetch_platform_docs.py --bump` | Generates v2 schemas with valid metadata  |
| Brownfield Compatibility | `pytest tests/legacy_schema_test.py`           | 100% pass rate with compatibility shim    |
| Packaging Integrity      | `pip install . && skilllint check --list-schemas` | Shows refreshed schema versions          |
| Provenance Preservation  | `jq .provenance packages/skilllint/schemas/claude_code/v2.json` | Contains authority_url and valid dates |

## Risks
1. **Provenance Drift**: Auto-generated schemas may lose manual constraint_scope annotations
   - Mitigation: Implement annotation inheritance system
2. **Test Coupling**: Legacy tests may rely on schema field positions
   - Mitigation: Add schema location abstraction layer
3. **Packaging Paths**: importlib.resources may fail with nested schema versions
   - Mitigation: Pre-test in zipapp distribution format

## Required Artifacts
1. Schema refresh workflow documentation
2. Brownfield migration checklist
3. Packaging verification test suite
4. Provenance comparison tool (old vs new schemas)

## Upstream Dependencies
- Provider documentation stability (Claude Code API docs)
- `importlib_resources` backport compatibility for Python <3.9

## First Principles Validation
