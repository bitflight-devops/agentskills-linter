---
task: "3"
title: "File Type Detection Enhancement"
status: not-started
agent: "@python-cli-architect"
dependencies: ["1"]
priority: 1
complexity: m
---

## Priority 0: Foundation (No Dependencies)

## Task 1: FileType Enum Extension

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: None
**Priority**: 1
**Complexity**: S
**Accuracy Risk**: Low

#### Context

The FileType enum (lines 138-166 of plugin_validator.py) currently lacks variants for hook configs, MCP configs, LSP configs, and hook scripts. All subsequent file type detection and validator selection depends on this enum.

#### Objective

Add 4 new FileType enum values to enable detection of hook configurations, MCP server configs, LSP server configs, and hook script files.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 85-130 (FileType enum specification)
- Current implementation: plugin_validator.py lines 138-166

#### Requirements

1. Add `HOOK_CONFIG = "hook_config"` enum value
2. Add `MCP_CONFIG = "mcp_config"` enum value
3. Add `LSP_CONFIG = "lsp_config"` enum value
4. Add `HOOK_SCRIPT = "hook_script"` enum value
5. Maintain alphabetical ordering within enum definition
6. Preserve existing enum values unchanged

#### Constraints

- MUST NOT modify existing enum values (SKILL, AGENT, COMMAND, PLUGIN, UNKNOWN)
- MUST use StrEnum as base class (existing pattern)
- MUST NOT add any detection logic in this task (handled in Task 3)

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (lines 138-166 region)
- 4 new enum values added with string values
- Existing enum structure preserved

#### Acceptance Criteria

1. FileType enum contains 9 total values (5 existing + 4 new)
2. New values use StrEnum convention (lowercase with underscores)
3. Enum imports and class structure unchanged
4. No linting errors introduced (ruff, mypy)

#### Verification Steps

1. Run `ruff check plugins/plugin-creator/scripts/plugin_validator.py`
2. Run `mypy plugins/plugin-creator/scripts/plugin_validator.py --strict`
3. Import FileType in Python REPL and verify `len(FileType)` == 9
4. Verify `FileType.HOOK_CONFIG.value == "hook_config"`

**Can Parallelize With**: Task 2 (error code constants), Task 3 (file detection logic)
**Reason**: Enum definition and error codes are independent additions
**Handoff**: Provide file diff showing 4 new enum values, linting output showing no errors
