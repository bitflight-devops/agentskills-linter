# agentskills-linter

## Current State

`skilllint` is a linter for agent skill formats across multiple providers. The codebase currently mixes hardcoded validation limits, rule logic, provider-specific behavior, and documentation-derived constraints. Some rules now explicitly document provenance, but the structural constraint system is still split between Python constants, validator logic, and bundled schema snapshots.

## What The Project Is Becoming

The project is moving toward a schema-driven validation architecture:
- versioned provider schemas instead of ad hoc limits constants
- explicit provenance for every rule and constraint
- composition of base standards (for example `agentskills.io`) with provider-specific extensions (for example Claude Code)
- a clear split between schema-backed structural validation and semantic lint rules

## Immediate Focus

**S03 complete (refreshable schema ingestion):** Delivered schema refresh script with --bump/--dry-run/--provider/--verbose flags, eliminated duplicate _schema_loader.py brownfield loader, and added comprehensive test coverage (72 tests) for refresh roundtrip and multi-provider packaging.

**Next: S04** will prove end-to-end packaged integration: refresh → bundled artifact load → CLI validation through the real runtime path.
