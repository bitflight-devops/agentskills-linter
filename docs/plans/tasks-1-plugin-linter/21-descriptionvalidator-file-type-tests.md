---
task: "21"
title: "DescriptionValidator File-Type Tests"
status: not-started
agent: "@python-pytest-architect"
dependencies: ["12"]
priority: 4
complexity: s
---

## Task 16: MCPConfigValidator Tests

**Status**: NOT STARTED
**Agent**: @python-pytest-architect
**Dependencies**: Task 9
**Priority**: 4
**Complexity**: M
**Accuracy Risk**: Low

#### Context

MCPConfigValidator needs comprehensive test coverage for all error codes and edge cases with mocked command existence checks.

#### Objective

Create complete test suite for MCPConfigValidator achieving 90%+ coverage.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 949-964 (MCPConfigValidator test requirements)
- Completed Task 9: MCPConfigValidator implementation
- Test pattern: plugins/plugin-creator/tests/test_frontmatter_validator.py

#### Requirements

1. Create test_mcp_config_validator.py with pytest test class
2. Test valid .mcp.json configurations
3. Test invalid JSON syntax → MC001
4. Test missing command field → MC002
5. Test empty command string → MC003
6. Test command not in PATH → MC004 (warning) with mocked shutil.which()
7. Test args as string not list → MC005
8. Test env with non-string values → MC006
9. Test non-existent CWD path → MC007 (warning)
10. Test empty server name → MC008
11. Test empty mcpServers dict → MC009
12. Test args with non-string elements → MC010
13. Mock shutil.which() for command existence tests
14. Mock Path.exists() for CWD validation tests
15. Achieve 90%+ coverage

#### Constraints

- MUST use pytest-mock for mocking (not unittest.mock)
- MUST verify warning vs error severity correctly assigned
- MUST test both existent and non-existent commands
- MUST achieve minimum 90% coverage

#### Expected Outputs

- New file: `plugins/plugin-creator/tests/test_mcp_config_validator.py` (~250 lines)
- Test fixtures for valid/invalid .mcp.json
- Mocked tests for command and path existence
- Coverage report showing 90%+ for MCPConfigValidator

#### Acceptance Criteria

1. Test file created with all required test cases
2. All 10 error codes (MC001-MC010) have dedicated tests
3. shutil.which() mocked for command existence tests
4. Path.exists() mocked for CWD tests
5. Warning severity verified for MC004 and MC007
6. Coverage ≥90% for MCPConfigValidator class
7. All tests pass with mocked dependencies

#### Verification Steps

1. Run tests: `pytest plugins/plugin-creator/tests/test_mcp_config_validator.py -v`
2. Check coverage: `pytest --cov=plugin_validator --cov-report=term-missing`
3. Verify MC004 produces warning not error
4. Verify MC007 produces warning not error
5. Run `mypy tests/test_mcp_config_validator.py --strict`

**Can Parallelize With**: Task 15 (HookConfig tests), Task 17 (LSPConfig tests), Task 18 (AgentEnum tests)
**Reason**: Independent test files
**Handoff**: Provide test file, coverage report, severity verification
