---
task: "25"
title: "Performance Validation"
status: not-started
agent: "@python-cli-architect"
dependencies: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21"]
priority: 5
complexity: s
---

## Task 20: Report Generation Tests

**Status**: NOT STARTED
**Agent**: @python-pytest-architect
**Dependencies**: Task 14
**Priority**: 4
**Complexity**: M
**Accuracy Risk**: Low

#### Context

Report counting fix needs tests to verify file counts are accurate and grouping is correct.

#### Objective

Create test suite verifying report generation counts files not validators and groups issues correctly.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 1014-1027 (Report generation test requirements)
- Completed Task 14: Report counting fix
- Existing test pattern: plugins/plugin-creator/tests/test_cli.py

#### Requirements

1. Create test_report_generation.py with pytest test class
2. Test file count accuracy (not validator count)
3. Test issue grouping by file path
4. Test issue grouping by error code within file
5. Test summary statistics accuracy
6. Test error vs warning separation
7. Test ConsoleReporter output format
8. Test CIReporter output format
9. Test SummaryReporter output format
10. Verify single file with 7 validators shows "1 file"
11. Verify 5 files show "5 files" in summary
12. Capture and parse Rich console output

#### Constraints

- MUST capture Rich console output for verification
- MUST verify grouping structure matches spec
- MUST test all 3 reporter implementations
- MUST achieve 90%+ coverage of reporter classes

#### Expected Outputs

- New file: `plugins/plugin-creator/tests/test_report_generation.py` (~200 lines)
- Tests for all 3 reporter classes
- Console output capture and parsing tests
- Coverage report showing 90%+ for reporter classes

#### Acceptance Criteria

1. File count tests verify 1 file shows "1 file" not "7 validators"
2. Grouping tests verify issues grouped by file path
3. Summary statistics tests verify error/warning counts
4. All 3 reporter implementations tested
5. Coverage ≥90% for reporter classes
6. All tests pass

#### Verification Steps

1. Run tests: `pytest plugins/plugin-creator/tests/test_report_generation.py -v`
2. Check coverage: `pytest --cov=plugin_validator --cov-report=term-missing`
3. Manually verify output format matches specification
4. Test with actual validation runs to verify counts
5. Run `mypy tests/test_report_generation.py --strict`

**Can Parallelize With**: Task 19 (file type tests), Task 21 (description validator tests)
**Reason**: Independent test files
**Handoff**: Provide test file, coverage report, output format verification
