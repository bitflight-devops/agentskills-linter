---
task: "13"
title: "Dead Code Removal"
status: not-started
agent: "@python-cli-architect"
priority: 3
complexity: s
---

## Task 9: MCPConfigValidator Implementation

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: Task 1, Task 2, Task 3, Task 5
**Priority**: 3
**Complexity**: M
**Accuracy Risk**: Medium

#### Context

Need validator class to check .mcp.json files against MCPConfig Pydantic model and generate MC001-MC010 error codes.

#### Objective

Implement MCPConfigValidator class following Validator protocol to validate MCP server configurations.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 422-473 (MCPConfigValidator spec)
- Completed Task 5: MCPConfig Pydantic models available
- Validator protocol: plugin_validator.py lines 249-286

#### Requirements

1. Implement Validator protocol (validate, can_fix, fix methods)
2. Parse JSON with syntax error handling → MC001
3. Validate against MCPConfig Pydantic model
4. Check command field non-empty → MC003
5. Check command exists in PATH using shutil.which() → MC004 (warning)
6. Validate args is list not string → MC005
7. Validate env values are strings → MC006
8. Check CWD path exists → MC007 (warning)
9. Implement can_fix() to return False

#### Constraints

- MUST NOT execute commands during validation
- MUST use shutil.which() for command existence check (no subprocess)
- MC004 and MC007 MUST be warnings not errors (paths may not exist at validation time)
- MUST handle permission errors when checking path existence

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (new validator class)
- MCPConfigValidator class with ~100 lines of implementation
- Error handling for MC001-MC010 codes
- Warning-level issues for MC004 and MC007

#### Acceptance Criteria

1. Validator implements all 3 protocol methods
2. Invalid JSON produces MC001 error
3. Missing command field produces MC002 error
4. Empty command string produces MC003 error
5. Command not in PATH produces MC004 warning
6. Args as string produces MC005 error
7. Non-string env values produce MC006 error
8. Non-existent CWD produces MC007 warning
9. can_fix() returns False
10. Severity correctly set (error vs warning)

#### Verification Steps

1. Create test .mcp.json with JSON syntax error, verify MC001
2. Create test with missing command field, verify MC002
3. Create test with command="/nonexistent/binary", verify MC004 warning
4. Create test with args="--flag" (string not list), verify MC005
5. Create test with env values as integers, verify MC006
6. Run `mypy --strict` on validator class
7. Verify warning vs error severity correctly assigned

**Can Parallelize With**: Task 8 (HookConfigValidator), Task 10 (LSPConfigValidator), Task 11 (AgentEnumValidator)
**Reason**: Independent validators for different config types
**Handoff**: Provide validator code, manual test outputs, severity verification
