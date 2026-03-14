# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| D001 | M001 | arch | Provider contract packaging | Keep provider schemas as versioned bundled artifacts under `packages/skilllint/schemas/<provider>/vN.json` | Matches current brownfield packaging pattern and preserves `importlib.resources` runtime loading while enabling evolution | Yes — if a manifest-based loader replaces per-provider versioned files later |
| D002 | M001 | convention | Rule authority metadata | Normalize rule/schema provenance into structured metadata rather than freeform source strings only | Downstream CLI output, tests, and refresh tooling need machine-readable authority tracing | No |
| D003 | M001 | scope | Final proof shape | Include an explicit integration slice proving refresh → bundled resource load → CLI validation end-to-end | Milestone crosses repo tooling, packaged resources, and runtime CLI boundaries; contract proof alone would be insufficient | No |
