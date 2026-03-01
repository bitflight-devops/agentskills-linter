---
task: "24"
title: "Integration Testing"
status: not-started
agent: "@python-pytest-architect"
dependencies: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21"]
priority: 5
complexity: m
---

## Task 19: File Type Detection Tests

**Status**: NOT STARTED
**Agent**: @python-pytest-architect
**Dependencies**: Task 3
**Priority**: 4
**Complexity**: S
**Accuracy Risk**: Low

#### Context

Enhanced FileType.detect_file_type() needs comprehensive tests for all 9 file types and edge cases.

#### Objective

Create complete test suite for file type detection achieving 100% coverage.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 996-1008 (File type detection test requirements)
- Completed Task 3: Enhanced detect_file_type() method

#### Requirements

1. Create test_file_type_detection.py with pytest test class
2. Test SKILL.md detection
3. Test agent file detection (agents/ directory)
4. Test command file detection (commands/ directory)
5. Test hooks.json exact match detection
6. Test .mcp.json exact match detection
7. Test .lsp.json exact match detection
8. Test hook script detection (hooks/*.js)
9. Test plugin.json detection
10. Test UNKNOWN fallback for unrecognized files
11. Test edge cases: nested directories, symlinks (if applicable), case sensitivity
12. Achieve 100% coverage of detect_file_type() method

#### Constraints

- MUST test detection priority order (exact filename > special > directory-based)
- MUST test both absolute and relative paths
- MUST verify deterministic behavior (same input → same output)
- MUST achieve 100% branch coverage

#### Expected Outputs

- New file: `plugins/plugin-creator/tests/test_file_type_detection.py` (~150 lines)
- Test cases for all 9 FileType enum values
- Edge case tests for path variations
- Coverage report showing 100% for detect_file_type()

#### Acceptance Criteria

1. All 9 FileType values have detection tests
2. Edge cases tested (nested paths, subdirectories)
3. Detection priority order verified
4. Coverage 100% for detect_file_type() method
5. All tests pass
6. No false positives or negatives

#### Verification Steps

1. Run tests: `pytest plugins/plugin-creator/tests/test_file_type_detection.py -v`
2. Check coverage: `pytest --cov=plugin_validator --cov-report=term-missing`
3. Verify 100% branch coverage for detect_file_type()
4. Test with real plugin directory structure
5. Run `mypy tests/test_file_type_detection.py --strict`

**Can Parallelize With**: Task 20 (report tests), Task 21 (description validator tests)
**Reason**: Independent test files
**Handoff**: Provide test file, coverage report showing 100%
