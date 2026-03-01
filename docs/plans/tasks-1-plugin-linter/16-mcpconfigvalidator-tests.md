---
task: "16"
title: "MCPConfigValidator Tests"
status: not-started
agent: "@python-pytest-architect"
dependencies: ["9"]
priority: 4
complexity: m
---

## Task 12: DescriptionValidator File-Type Awareness

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: Task 1, Task 3
**Priority**: 3
**Complexity**: S
**Accuracy Risk**: Low

#### Context

DescriptionValidator (lines 1790-1936) currently fires SK005 trigger phrase check on commands, causing false positives. Commands don't need trigger phrases since they're explicitly invoked.

#### Objective

Add file_type parameter to DescriptionValidator.validate() to skip SK005 check for commands.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 582-629 (DescriptionValidator modification)
- Current implementation: plugin_validator.py lines 1790-1936
- Completed Task 3: FileType detection available

#### Requirements

1. Add `file_type: FileType` parameter to validate() method signature
2. Skip SK005 check when `file_type == FileType.COMMAND`
3. Run SK005 check for FileType.SKILL and FileType.AGENT
4. Update method docstring to document file_type parameter behavior
5. Preserve existing SK004 length check for all file types
6. Update validator registration to pass file_type parameter

#### Constraints

- MUST NOT change SK004 behavior (length check applies to all types)
- MUST preserve can_fix() and fix() methods unchanged
- MUST maintain backward compatibility with existing tests
- FileType parameter MUST be positional (not keyword-only) for consistency

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (lines 1790-1936 region)
- Updated validate() method signature
- Conditional SK005 check based on file_type
- Updated docstring

#### Acceptance Criteria

1. Method signature includes `file_type: FileType` parameter
2. SK005 skipped when file_type is COMMAND
3. SK005 runs when file_type is SKILL or AGENT
4. SK004 runs for all file types
5. Existing tests still pass (verify with Task 21)
6. No linting errors introduced

#### Verification Steps

1. Create test command file, verify no SK005 error
2. Create test skill file, verify SK005 still fires
3. Create test agent file, verify SK005 still fires
4. Run existing description validator tests, verify all pass
5. Run `mypy --strict` on modified file
6. Verify validator registration calls pass file_type parameter

**Can Parallelize With**: Task 13 (dead code removal), Task 14 (report counting fix)
**Reason**: Independent bug fixes in different code sections
**Handoff**: Provide file diff, test verification outputs
