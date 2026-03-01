---
task: "12"
title: "DescriptionValidator File-Type Awareness"
status: not-started
agent: "@python-cli-architect"
dependencies: ["1", "3"]
priority: 3
complexity: s
---

## Priority 2: Validators and Bug Fixes (Depends on P0, P1)

## Task 8: HookConfigValidator Implementation

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: Task 1, Task 2, Task 3, Task 4
**Priority**: 3
**Complexity**: L
**Accuracy Risk**: Medium

#### Context

Need validator class to check hooks.json files against HookConfig Pydantic model and generate HK001-HK010 error codes.

#### Objective

Implement HookConfigValidator class following Validator protocol to validate hooks.json structure and content.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 360-420 (HookConfigValidator spec)
- Completed Task 4: HookConfig Pydantic models available
- Validator protocol: plugin_validator.py lines 249-286

#### Requirements

1. Implement Validator protocol (validate, can_fix, fix methods)
2. Parse JSON with syntax error handling → HK001
3. Validate against HookConfig Pydantic model
4. Convert Pydantic validation errors to ValidationIssue with HK error codes
5. Validate regex patterns in matcher fields → HK005
6. Check timeout values are positive → HK006
7. Validate hook type discriminators → HK003, HK004
8. Suggest similar event names for unknown events → HK002
9. Implement can_fix() to return False (no auto-fix for JSON)

#### Constraints

- MUST NOT execute regex patterns (compile only for validation)
- MUST provide clear error messages with suggestions
- MUST handle malformed JSON gracefully (catch exceptions)
- MUST link to ERROR_CODES.md in ValidationIssue.docs_url

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (new validator class)
- HookConfigValidator class with ~150 lines of implementation
- Error handling for all HK001-HK010 error codes
- Fuzzy matching suggestions for unknown event types

#### Acceptance Criteria

1. Validator implements all 3 protocol methods
2. Invalid JSON produces HK001 error with line number
3. Unknown event types produce HK002 with "did you mean" suggestions
4. Invalid hook types produce HK003 error
5. Type field mismatches produce HK004 error
6. Invalid regex produces HK005 error with regex compilation message
7. Negative timeouts produce HK006 error
8. can_fix() returns False
9. All ValidationIssue objects have docs_url set

#### Verification Steps

1. Create test hooks.json with JSON syntax error, verify HK001
2. Create test with unknown event "SessionStartup", verify HK002 suggests "SessionStart"
3. Create test with type=command but no command field, verify HK004
4. Create test with invalid regex `[`, verify HK005
5. Create test with timeout=-1, verify HK006
6. Run `mypy --strict` on validator class
7. Verify all error paths covered (will be checked by Task 15 tests)

**Can Parallelize With**: Task 9 (MCPConfigValidator), Task 10 (LSPConfigValidator), Task 11 (AgentEnumValidator)
**Reason**: Validators are independent, operate on different file types
**Handoff**: Provide validator code, manual test outputs, error code coverage verification
