---
task: "22"
title: "ERROR_CODES.md Documentation"
status: not-started
agent: "@python-cli-architect"
dependencies: ["2", "8", "9", "10", "11"]
priority: 5
complexity: m
---

## Task 17: LSPConfigValidator Tests

**Status**: NOT STARTED
**Agent**: @python-pytest-architect
**Dependencies**: Task 10
**Priority**: 4
**Complexity**: M
**Accuracy Risk**: Low

#### Context

LSPConfigValidator needs comprehensive test coverage for extension format validation and all error codes.

#### Objective

Create complete test suite for LSPConfigValidator achieving 90%+ coverage.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 965-981 (LSPConfigValidator test requirements)
- Completed Task 10: LSPConfigValidator implementation
- Test pattern: plugins/plugin-creator/tests/test_frontmatter_validator.py

#### Requirements

1. Create test_lsp_config_validator.py with pytest test class
2. Test valid .lsp.json configurations
3. Test invalid JSON syntax → LS001
4. Test missing required fields → LS002, LS003
5. Test extension format validation → LS004 (parametrized for .py, .js, .ts vs py, *.py)
6. Test language identifier validation → LS005 (Python vs python)
7. Test invalid transport values → LS006
8. Test invalid timeout values → LS007
9. Test invalid maxRestarts values → LS008
10. Test empty extensionToLanguage → LS009
11. Test empty server name → LS010
12. Parametrize extension format tests (valid/invalid patterns)
13. Parametrize language identifier tests (valid/invalid casing)
14. Achieve 90%+ coverage

#### Constraints

- MUST test extension format strictly (.py not py or *.py)
- MUST verify lowercase language identifier enforcement
- MUST test positive integer validation for timeouts
- MUST achieve minimum 90% coverage

#### Expected Outputs

- New file: `plugins/plugin-creator/tests/test_lsp_config_validator.py` (~250 lines)
- Test fixtures for valid/invalid .lsp.json
- Parametrized tests for extension formats
- Coverage report showing 90%+ for LSPConfigValidator

#### Acceptance Criteria

1. Test file created with all required test cases
2. All 10 error codes (LS001-LS010) have dedicated tests
3. Extension format tests parametrized (valid: .py, .js, .ts; invalid: py, *.py)
4. Language identifier tests parametrized (valid: python, javascript; invalid: Python, JavaScript)
5. Coverage ≥90% for LSPConfigValidator class
6. All tests pass

#### Verification Steps

1. Run tests: `pytest plugins/plugin-creator/tests/test_lsp_config_validator.py -v`
2. Check coverage: `pytest --cov=plugin_validator --cov-report=term-missing`
3. Verify parametrized extension tests run multiple times
4. Verify LS004 suggests correct format (.py)
5. Run `mypy tests/test_lsp_config_validator.py --strict`

**Can Parallelize With**: Task 15 (HookConfig tests), Task 16 (MCPConfig tests), Task 18 (AgentEnum tests)
**Reason**: Independent test files
**Handoff**: Provide test file, coverage report, parametrize verification
