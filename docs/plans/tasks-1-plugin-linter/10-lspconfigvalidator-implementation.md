---
task: "10"
title: "LSPConfigValidator Implementation"
status: not-started
agent: "@python-cli-architect"
dependencies: ["1", "2", "3", "6"]
priority: 3
complexity: m
---

## Task 7: AgentFrontmatter Enum Models

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: Task 2
**Priority**: 2
**Complexity**: S
**Accuracy Risk**: High

#### Context

Existing AgentFrontmatter model (lines 1167-1235) lacks enum validation for model, permissionMode, and memory fields. Need to add enum types for strict validation.

#### Objective

Enhance AgentFrontmatter Pydantic model with enum validation for agent-specific fields.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 267-312 (Agent enum schema)
- Official docs: <https://docs.anthropic.com/en/docs/claude-code/sub-agents.md> (cite)
- Current AgentFrontmatter model: plugin_validator.py lines 1167-1235

#### Requirements

1. Create `AgentModel` StrEnum with values: SONNET, OPUS, HAIKU, INHERIT
2. Create `AgentPermissionMode` StrEnum with 6 permission mode values
3. Create `AgentMemory` StrEnum with values: USER, PROJECT, LOCAL
4. Modify AgentFrontmatter model to use these enum types
5. Change `model: str | None` to `model: AgentModel | None`
6. Change `permissionMode: str | None` to `permissionMode: AgentPermissionMode | None`
7. Add `memory: AgentMemory | None` field if not present

#### Constraints

- MUST cite official schema URL in enum docstrings
- MUST preserve all existing AgentFrontmatter fields unchanged
- MUST use exact enum value casing from official docs
- MUST NOT break existing agent frontmatter parsing

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (lines 1167-1235 region)
- 3 new StrEnum classes added
- AgentFrontmatter model fields updated to use enums
- Docstrings cite official schema URL

#### Acceptance Criteria

1. AgentModel enum contains exactly 4 values (sonnet, opus, haiku, inherit)
2. AgentPermissionMode enum contains all 6 permission modes
3. AgentMemory enum contains 3 memory scope values
4. AgentFrontmatter.model field type is `AgentModel | None`
5. Existing agent files still validate correctly
6. Invalid enum values rejected with Pydantic validation error

#### Verification Steps

1. Parse existing agent .md files from codebase, verify no validation errors
2. Create test agent with invalid model value "gpt-4", verify rejection
3. Create test agent with invalid permissionMode, verify error suggests valid values
4. Run `mypy --strict` on modified file
5. Verify backward compatibility with existing tests

#### CoVe Checks

**Accuracy Risk**: High (must match official agent schema exactly)

- Key claims to verify:
  - All enum values match official documentation exactly
  - Enum value casing is correct (lowercase vs camelCase)
  - No valid enum values are missing

- Verification questions:
  1. Are model values lowercase or capitalized in official schema?
  2. Is permissionMode camelCase or snake_case in official schema?
  3. Are there additional permission modes beyond the 6 listed?
  4. Is memory field actually supported in current Claude Code version?

- Evidence to collect:
  - Fetch official agent schema: `WebFetch("https://docs.anthropic.com/en/docs/claude-code/sub-agents.md")`
  - Cross-reference all enum values with official list
  - Test with actual agent files from this repository
  - Check Claude Code version compatibility

- Revision rule:
  - If official schema has different enum values, update to match official
  - If memory field is not in official schema, mark as experimental in docstring
  - Document any version-specific enum values

**Can Parallelize With**: Task 4 (HookConfig), Task 5 (MCPConfig), Task 6 (LSPConfig)
**Reason**: Independent schema enhancements
**Handoff**: Provide model diff, verification outputs, official schema comparison
