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

**S04 complete (end-to-end packaged integration):** Delivered E2E test suite (`test_e2e_packaging.py`) with 10 tests proving the full refresh → build → install → CLI validation chain works with packaged resources. All tests pass.

**M001 milestone complete:** All four slices (S01-S04) finished. The versioned provider schema and rule authority pipeline is fully operational.
