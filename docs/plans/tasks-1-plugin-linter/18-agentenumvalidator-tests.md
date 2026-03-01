---
task: "18"
title: "AgentEnumValidator Tests"
status: not-started
agent: "@python-pytest-architect"
dependencies: ["11"]
priority: 4
complexity: m
---

## Task 14: Report Counting Fix

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: None
**Priority**: 3
**Complexity**: S
**Accuracy Risk**: Low

#### Context

ConsoleReporter.summarize() (lines 2681-2709) counts ValidationResult objects instead of unique files, showing inflated counts in summary.

#### Objective

Change report summary to count unique files validated instead of validator runs.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 836-893 (Report generation fix)
- Current implementation: plugin_validator.py lines 2681-2709
- Reporter protocol: plugin_validator.py lines 2561-2592

#### Requirements

1. Change report() method to accept results as dict[Path, ValidationResult]
2. Update summarize() to count unique paths not ValidationResult objects
3. Change summary message from "X validators passed" to "X files validated"
4. Group issues by file path in report output
5. Update all reporter implementations (ConsoleReporter, CIReporter, SummaryReporter)
6. Update caller sites to pass dict[Path, ValidationResult] instead of list[tuple[Path, ValidationResult]]

#### Constraints

- MUST preserve all error/warning information (no data loss)
- MUST maintain backward compatibility with Rich output format
- MUST update all 3 reporter classes consistently
- Summary statistics MUST show file counts not validator counts

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (lines 2561-2807 region)
- Updated Reporter protocol signature
- Updated all 3 reporter implementations
- Updated caller sites to pass dict structure
- Updated tests to match new signature

#### Acceptance Criteria

1. Reporter protocol signature changed to dict[Path, ValidationResult]
2. Summary shows "Validated X files" not "Passed X validators"
3. Issues grouped by file path in output
4. Single file with 7 validators shows "1 file" not "7 files"
5. All reporter implementations updated consistently
6. Existing report format preserved (only counts changed)

#### Verification Steps

1. Validate single SKILL.md file, verify summary shows "1 file"
2. Validate plugin directory with 5 files, verify summary shows "5 files"
3. Verify error grouping by file path in output
4. Run existing reporter tests, update expectations as needed
5. Run `mypy --strict` on modified file
6. Verify no regression in error/warning display

**Can Parallelize With**: All tasks (independent UX fix)
**Reason**: Report formatting doesn't affect validation logic
**Handoff**: Provide file diff, before/after output samples, test updates
