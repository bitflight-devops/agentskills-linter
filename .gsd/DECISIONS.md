# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| D001 | M001 | arch | Provider contract packaging | Keep provider schemas as versioned bundled artifacts under `packages/skilllint/schemas/<provider>/vN.json` | Matches current brownfield packaging pattern and preserves `importlib.resources` runtime loading while enabling evolution | Yes — if a manifest-based loader replaces per-provider versioned files later |
| D002 | M001 | convention | Rule authority metadata | Normalize rule/schema provenance into structured metadata rather than freeform source strings only | Downstream CLI output, tests, and refresh tooling need machine-readable authority tracing | No |
| D003 | M001 | scope | Final proof shape | Include an explicit integration slice proving refresh → bundled resource load → CLI validation end-to-end | Milestone crosses repo tooling, packaged resources, and runtime CLI boundaries; contract proof alone would be insufficient | No |
| D004 | M001 | arch | Adapter constraint_scopes method | Added constraint_scopes() to PlatformAdapter protocol returning set of constraint_scope values from provider schema | Enables future provider-specific rule filtering; AS-series rules are cross-platform (shared), but future provider-specific rules need scope filtering | Yes — can be extended to pass scope context to individual rules |
| D005 | M001 | convention | AS-series rule authority | All AS001-AS006 rules have authority metadata pointing to agentskills.io specification sections | Provides traceability from violation output back to authoritative source; enables downstream tooling to surface provenance | No |
| D006 | M001 | test | CLI integration test invocation | Use `skilllint.plugin_validator` module path instead of `skilllint` for subprocess CLI tests | Package has no `__main__.py`; the CLI entry point is through plugin_validator module | Yes — if `__main__.py` is added later |
| D007 | M001 | test | Provider ID alignment testing | Test that adapter IDs are subset of `get_provider_ids()` rather than exact equality | `agentskills_io` is a base schema directory with no corresponding adapter | No |
| D008 | S04 | test | E2E wheel build fixture scope | Use module-scoped fixture for wheel build with idempotent check for existing wheel | Avoids rebuilding wheel for each test; parallel test execution can race on dist directory | Yes — could use session scope if tests share wheel across modules |
| D009 | S04 | test | Subprocess isolation for installed package tests | Clear PYTHONPATH environment variable in subprocess runs | Ensures tests use installed package, not repo checkout; dev environment has PYTHONPATH pointing to packages/ | No |
