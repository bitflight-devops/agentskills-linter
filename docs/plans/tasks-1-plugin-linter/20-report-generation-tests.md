---
task: "20"
title: "Report Generation Tests"
status: not-started
agent: "@python-pytest-architect"
dependencies: ["14"]
priority: 4
complexity: m
---

## Priority 3: Testing (Depends on P0-P2)

## Task 15: HookConfigValidator Tests

**Status**: NOT STARTED
**Agent**: @python-pytest-architect
**Dependencies**: Task 8
**Priority**: 4
**Complexity**: L
**Accuracy Risk**: Low

#### Context

HookConfigValidator needs comprehensive test coverage for all 15 event types and 10 error codes with parametrized tests.

#### Objective

Create complete test suite for HookConfigValidator achieving 90%+ coverage.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 925-948 (HookConfigValidator test requirements)
- Completed Task 8: HookConfigValidator implementation
- Test pattern: plugins/plugin-creator/tests/test_frontmatter_validator.py

#### Requirements

1. Create test_hook_config_validator.py with pytest test class
2. Test valid hooks.json with all 15 event types (parametrized)
3. Test invalid JSON syntax → HK001
4. Test unknown event types → HK002 with fuzzy matching suggestions
5. Test invalid hook types → HK003
6. Test type field mismatches → HK004
7. Test invalid regex patterns → HK005
8. Test invalid timeouts → HK006
9. Test missing required fields → HK007
10. Test empty hooks arrays → HK008
11. Test invalid model values → HK009
12. Test invalid type field values → HK010
13. Add fixtures for valid/invalid hooks.json templates
14. Use pytest.mark.parametrize for event type tests
15. Achieve 90%+ line and branch coverage

#### Constraints

- MUST follow pytest testing standards from architecture spec
- MUST use typed fixtures with return type hints
- MUST use pytest-mock not unittest.mock
- MUST use AAA (Arrange-Act-Assert) pattern with comments
- MUST achieve minimum 90% coverage

#### Expected Outputs

- New file: `plugins/plugin-creator/tests/test_hook_config_validator.py` (~300 lines)
- Test fixtures for valid/invalid hooks.json
- Parametrized tests for all 15 event types
- Individual tests for each error code HK001-HK010
- Coverage report showing 90%+ for HookConfigValidator

#### Acceptance Criteria

1. Test file created with all required test cases
2. All 15 event types tested via parametrize
3. All 10 error codes (HK001-HK010) have dedicated tests
4. Fuzzy matching suggestions tested for unknown events
5. Coverage ≥90% line and branch for HookConfigValidator
6. All tests pass: `pytest plugins/plugin-creator/tests/test_hook_config_validator.py -v`
7. Type hints on all fixtures and test functions

#### Verification Steps

1. Run tests: `pytest plugins/plugin-creator/tests/test_hook_config_validator.py -v`
2. Check coverage: `pytest --cov=plugin_validator --cov-report=term-missing`
3. Verify coverage ≥90% for HookConfigValidator class
4. Run `mypy tests/test_hook_config_validator.py --strict`
5. Verify parametrized tests run 15 times (one per event type)

**Can Parallelize With**: Task 16 (MCPConfig tests), Task 17 (LSPConfig tests), Task 18 (AgentEnum tests)
**Reason**: Independent test files for different validators
**Handoff**: Provide test file, coverage report, pytest output
