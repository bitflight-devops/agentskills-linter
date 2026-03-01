---
task: "5"
title: "MCPConfig Pydantic Models"
status: not-started
agent: "@python-cli-architect"
dependencies: ["2"]
priority: 2
complexity: s
---

## Task 3: File Type Detection Enhancement

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: Task 1
**Priority**: 1
**Complexity**: M
**Accuracy Risk**: Medium

#### Context

FileType.detect_file_type() method (lines 147-165) needs enhancement to detect hooks.json, .mcp.json, .lsp.json config files and hook scripts in hooks/ directory.

#### Objective

Extend FileType.detect_file_type() to correctly classify all 7 plugin component types based on exact filename matches and path patterns.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 105-130 (Detection rules)
- Current implementation: plugin_validator.py lines 147-165
- Completed Task 1: New FileType enum values available

#### Requirements

1. Add exact filename match for `hooks.json` → `FileType.HOOK_CONFIG`
2. Add exact filename match for `.mcp.json` → `FileType.MCP_CONFIG`
3. Add exact filename match for `.lsp.json` → `FileType.LSP_CONFIG`
4. Add directory-based detection for `hooks/*.{js,py,sh}` → `FileType.HOOK_SCRIPT`
5. Maintain detection priority: exact filenames > special filenames > directory-based > UNKNOWN
6. Preserve existing detection logic for SKILL, AGENT, COMMAND, PLUGIN

#### Constraints

- MUST check exact filename matches before directory-based detection
- MUST NOT break existing file type detection for skills/agents/commands
- MUST handle both absolute and relative paths
- MUST NOT execute or read file contents during detection

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (lines 147-165 region)
- Enhanced detect_file_type() method with 4 new detection cases
- Docstring updated with detection priority order

#### Acceptance Criteria

1. `Path("hooks.json").detect_file_type()` returns `FileType.HOOK_CONFIG`
2. `Path(".mcp.json").detect_file_type()` returns `FileType.MCP_CONFIG`
3. `Path(".lsp.json").detect_file_type()` returns `FileType.LSP_CONFIG`
4. `Path("hooks/session-start.js").detect_file_type()` returns `FileType.HOOK_SCRIPT`
5. Existing file types still detected correctly (SKILL.md, agents/*.md, commands/*.md)
6. Detection is deterministic (same input always produces same output)

#### Verification Steps

1. Run unit tests (will be created in Task 19)
2. Manual verification:
   ```python
   from pathlib import Path
   from plugin_validator import FileType
   assert FileType.detect_file_type(Path("hooks.json")) == FileType.HOOK_CONFIG
   assert FileType.detect_file_type(Path(".mcp.json")) == FileType.MCP_CONFIG
   assert FileType.detect_file_type(Path(".lsp.json")) == FileType.LSP_CONFIG
   assert FileType.detect_file_type(Path("hooks/test.js")) == FileType.HOOK_SCRIPT
   ```
3. Run `mypy plugins/plugin-creator/scripts/plugin_validator.py --strict`

#### CoVe Checks

**Accuracy Risk**: Medium (path detection logic can have edge cases)

- Key claims to verify:
  - Detection priority order matches architecture spec
  - Existing file types still detected correctly

- Verification questions:
  1. Does `hooks.json` in subdirectory still match? (e.g., `plugins/test/hooks.json`)
  2. Does `.mcp.json` with path prefix match? (e.g., `./config/.mcp.json`)
  3. Do existing tests pass after changes?

- Evidence to collect:
  - Run existing test suite: `pytest plugins/plugin-creator/tests/test_cli.py -v`
  - Test with actual plugin directory structure

- Revision rule:
  - If existing file type detection breaks, revise to preserve original logic path
  - If edge cases found, document assumptions in docstring

**Can Parallelize With**: Task 2 (error codes)
**Reason**: Detection logic and error code constants are independent
**Handoff**: Provide file diff, manual verification outputs, test results
