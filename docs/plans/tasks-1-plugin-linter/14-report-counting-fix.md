---
task: "14"
title: "Report Counting Fix"
status: not-started
agent: "@python-cli-architect"
priority: 3
complexity: s
---

## Task 10: LSPConfigValidator Implementation

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: Task 1, Task 2, Task 3, Task 6
**Priority**: 3
**Complexity**: M
**Accuracy Risk**: Medium

#### Context

Need validator class to check .lsp.json files against LSPConfig Pydantic model and generate LS001-LS010 error codes.

#### Objective

Implement LSPConfigValidator class following Validator protocol to validate LSP server configurations.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 475-528 (LSPConfigValidator spec)
- Completed Task 6: LSPConfig Pydantic models available
- Validator protocol: plugin_validator.py lines 249-286

#### Requirements

1. Implement Validator protocol (validate, can_fix, fix methods)
2. Parse JSON with syntax error handling → LS001
3. Validate against LSPConfig Pydantic model
4. Check required fields present → LS002, LS003
5. Validate extension keys start with dot → LS004
6. Validate language identifiers are lowercase → LS005
7. Validate transport enum → LS006
8. Validate timeout values positive → LS007
9. Validate maxRestarts positive → LS008
10. Check extensionToLanguage non-empty → LS009
11. Implement can_fix() to return False

#### Constraints

- MUST validate extension format strictly (.py not py or *.py)
- MUST enforce lowercase language identifiers
- MUST check timeout and maxRestarts are positive not just non-negative
- MUST handle empty extensionToLanguage dict as error not warning

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (new validator class)
- LSPConfigValidator class with ~120 lines of implementation
- Error handling for LS001-LS010 codes
- Clear error messages for extension format violations

#### Acceptance Criteria

1. Validator implements all 3 protocol methods
2. Invalid JSON produces LS001 error
3. Missing command field produces LS002 error
4. Missing extensionToLanguage field produces LS003 error
5. Extension "py" (no dot) produces LS004 error
6. Language "Python" (not lowercase) produces LS005 error
7. Invalid transport "tcp" produces LS006 error
8. Negative timeout produces LS007 error
9. Zero maxRestarts produces LS008 error
10. Empty extensionToLanguage dict produces LS009 error

#### Verification Steps

1. Create test .lsp.json with JSON syntax error, verify LS001
2. Create test with missing extensionToLanguage, verify LS003
3. Create test with extension format "py", verify LS004 suggests ".py"
4. Create test with language "Python", verify LS005 suggests "python"
5. Create test with transport="http", verify LS006
6. Create test with startupTimeout=0, verify LS007
7. Run `mypy --strict` on validator class

**Can Parallelize With**: Task 8 (HookConfig), Task 9 (MCPConfig), Task 11 (AgentEnum)
**Reason**: Independent validators
**Handoff**: Provide validator code, manual test outputs, error message verification
