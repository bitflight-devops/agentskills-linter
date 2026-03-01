---
task: "17"
title: "LSPConfigValidator Tests"
status: not-started
agent: "@python-pytest-architect"
dependencies: ["10"]
priority: 4
complexity: m
---

## Task 13: Dead Code Removal

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: None
**Priority**: 3
**Complexity**: S
**Accuracy Risk**: Low

#### Context

Lines 904-911 in NamespaceReferenceValidator contain unreachable nested skill reference resolution code due to early return on line 903.

#### Objective

Remove dead code after verifying unreachability with coverage analysis.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 1149-1165 (Dead code removal)
- Current implementation: plugin_validator.py lines 904-911
- Test coverage report from existing test suite

#### Requirements

1. Run test suite with coverage enabled
2. Verify lines 904-911 have 0% coverage
3. Review git history to understand original purpose
4. Remove lines 904-911 after verification
5. Document removal in commit message with coverage evidence

#### Constraints

- MUST verify 0% coverage before removal (don't remove if ever executed)
- MUST document original purpose in commit message
- MUST run all tests after removal to ensure no breakage
- MUST NOT remove any other code in the same method

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (lines 904-911 removed)
- Coverage report showing 0% coverage on removed lines
- Git commit message documenting removal with evidence
- Test suite passing after removal

#### Acceptance Criteria

1. Coverage report confirms 0% coverage on lines 904-911
2. Lines 904-911 deleted from file
3. All existing tests pass after removal
4. No linting or type errors introduced
5. Commit message documents coverage evidence

#### Verification Steps

1. Run `pytest plugins/plugin-creator/tests/ --cov=plugin_validator --cov-report=term-missing`
2. Verify lines 904-911 not in coverage report (0% coverage)
3. Delete lines 904-911
4. Run test suite: `pytest plugins/plugin-creator/tests/ -v`
5. Run `mypy --strict` and `ruff check`
6. Review git diff to confirm only dead code removed

**Can Parallelize With**: All tasks (independent cleanup)
**Reason**: Dead code removal doesn't affect functionality
**Handoff**: Provide coverage report, git diff, test results
