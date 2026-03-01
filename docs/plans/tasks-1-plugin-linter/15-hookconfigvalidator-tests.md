---
task: "15"
title: "HookConfigValidator Tests"
status: not-started
agent: "@python-pytest-architect"
dependencies: ["8"]
priority: 4
complexity: l
---

## Task 11: AgentEnumValidator Implementation

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: Task 1, Task 2, Task 7
**Priority**: 3
**Complexity**: M
**Accuracy Risk**: Medium

#### Context

Need validator class to check agent enum fields (model, permissionMode, memory) against enhanced AgentFrontmatter model and generate AG001-AG010 error codes.

#### Objective

Implement AgentEnumValidator class to validate agent-specific enum fields and required fields.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 530-580 (AgentEnumValidator spec)
- Completed Task 7: Agent enum models available
- Validator protocol: plugin_validator.py lines 249-286
- FrontmatterValidator pattern: plugin_validator.py lines 1243-1600

#### Requirements

1. Implement Validator protocol (validate, can_fix, fix methods)
2. Parse agent frontmatter (reuse extract_frontmatter utility)
3. Validate against AgentFrontmatter Pydantic model
4. Generate AG001 for invalid model values
5. Generate AG002 for invalid permissionMode values
6. Generate AG003 for invalid memory values
7. Generate AG004/AG005 for missing required fields
8. Validate maxTurns is positive → AG006
9. Provide enum value suggestions for invalid values
10. Implement can_fix() to return False

#### Constraints

- MUST reuse existing extract_frontmatter() utility function
- MUST NOT auto-fix enum values (would be guessing intent)
- MUST suggest valid enum values in error messages
- MUST only run on FileType.AGENT files

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (new validator class)
- AgentEnumValidator class with ~100 lines of implementation
- Error handling for AG001-AG010 codes
- Enum value suggestions in error messages

#### Acceptance Criteria

1. Validator implements all 3 protocol methods
2. Invalid model "gpt-4" produces AG001 error with suggestions
3. Invalid permissionMode produces AG002 error
4. Invalid memory value produces AG003 error
5. Missing name field produces AG004 error
6. Missing description field produces AG005 error
7. maxTurns=0 produces AG006 error
8. Error messages include list of valid enum values
9. can_fix() returns False
10. Only validates files with FileType.AGENT

#### Verification Steps

1. Create test agent with model="gpt-4", verify AG001 suggests valid values
2. Create test agent with permissionMode="admin", verify AG002
3. Create test agent with missing name field, verify AG004
4. Create test agent with maxTurns=-1, verify AG006
5. Run validator on skill file, verify no errors (wrong file type)
6. Run `mypy --strict` on validator class
7. Verify error messages list all valid enum values

**Can Parallelize With**: Task 8 (HookConfig), Task 9 (MCPConfig), Task 10 (LSPConfig)
**Reason**: Independent validators
**Handoff**: Provide validator code, manual test outputs, enum suggestion verification
