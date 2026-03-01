---
task: "23"
title: "Pre-Commit Config Update"
status: not-started
agent: "@python-cli-architect"
dependencies: ["3"]
priority: 5
complexity: s
---

## Task 18: AgentEnumValidator Tests

**Status**: NOT STARTED
**Agent**: @python-pytest-architect
**Dependencies**: Task 11
**Priority**: 4
**Complexity**: M
**Accuracy Risk**: Low

#### Context

AgentEnumValidator needs comprehensive test coverage for enum validation and suggestion quality.

#### Objective

Create complete test suite for AgentEnumValidator achieving 90%+ coverage.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 983-995 (AgentEnumValidator test requirements)
- Completed Task 11: AgentEnumValidator implementation
- Test pattern: plugins/plugin-creator/tests/test_frontmatter_validator.py

#### Requirements

1. Create test_agent_enum_validator.py with pytest test class
2. Test valid agent enum combinations (parametrized)
3. Test invalid model values → AG001 with suggestions
4. Test invalid permissionMode values → AG002 with suggestions
5. Test invalid memory values → AG003 with suggestions
6. Test missing required fields → AG004, AG005
7. Test invalid maxTurns → AG006
8. Test invalid color values → AG007 (warning)
9. Test disallowedTools validation → AG008 (warning)
10. Test tools/disallowedTools conflict → AG009
11. Test hooks reference validation → AG010
12. Parametrize valid enum combination tests
13. Verify suggestion quality for invalid enum values
14. Achieve 90%+ coverage

#### Constraints

- MUST verify enum value suggestions are accurate
- MUST test all valid enum combinations
- MUST test file type filtering (only runs on AGENT files)
- MUST achieve minimum 90% coverage

#### Expected Outputs

- New file: `plugins/plugin-creator/tests/test_agent_enum_validator.py` (~250 lines)
- Test fixtures for valid/invalid agent frontmatter
- Parametrized tests for enum combinations
- Coverage report showing 90%+ for AgentEnumValidator

#### Acceptance Criteria

1. Test file created with all required test cases
2. All 10 error codes (AG001-AG010) have dedicated tests
3. Enum value suggestions tested and verified accurate
4. Valid enum combinations tested via parametrize
5. File type filtering tested (validator skips non-agent files)
6. Coverage ≥90% for AgentEnumValidator class
7. All tests pass

#### Verification Steps

1. Run tests: `pytest plugins/plugin-creator/tests/test_agent_enum_validator.py -v`
2. Check coverage: `pytest --cov=plugin_validator --cov-report=term-missing`
3. Verify AG001 suggests valid model values
4. Verify validator doesn't run on skill files
5. Run `mypy tests/test_agent_enum_validator.py --strict`

**Can Parallelize With**: Task 15 (HookConfig tests), Task 16 (MCPConfig tests), Task 17 (LSPConfig tests)
**Reason**: Independent test files
**Handoff**: Provide test file, coverage report, suggestion verification
