---
task: "4"
title: "HookConfig Pydantic Models"
status: not-started
agent: "@python-cli-architect"
dependencies: ["2"]
priority: 2
complexity: m
---

## Task 2: Error Code Constants Definition

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: None
**Priority**: 1
**Complexity**: S
**Accuracy Risk**: Low

#### Context

Error code constants (lines 71-109) currently define FM, SK, LK, PD, PL, NR series. Need to add 40 new constants for HK, MC, LS, AG series to support new validators.

#### Objective

Add 40 error code string constants to enable new validators to reference consistent error identifiers.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 700-763 (Error code registry)
- Current implementation: plugin_validator.py lines 71-109

#### Requirements

1. Add 10 constants: HK001 through HK010 for hook config errors
2. Add 10 constants: MC001 through MC010 for MCP config errors
3. Add 10 constants: LS001 through LS010 for LSP config errors
4. Add 10 constants: AG001 through AG010 for agent enum errors
5. Follow existing pattern: `HK001 = "HK001"`
6. Add comment block above each series with category name

#### Constraints

- MUST NOT modify existing error code constants
- MUST maintain alphabetical ordering by series (AG, HK, LS, MC)
- MUST NOT add error descriptions (those belong in ERROR_CODES.md)
- MUST use exact error code values from architecture spec

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (lines 71-109 region)
- 40 new string constants added
- Comment blocks added for each series

#### Acceptance Criteria

1. All 40 error codes defined as constants
2. Error codes match architecture spec exactly (HK001-HK010, MC001-MC010, LS001-LS010, AG001-AG010)
3. Constants follow existing pattern (uppercase variable = "UPPERCASE_STRING")
4. No duplicate error codes between old and new series

#### Verification Steps

1. Run `grep -E "^(HK|MC|LS|AG)[0-9]{3} = " plugins/plugin-creator/scripts/plugin_validator.py | wc -l` (should be 40)
2. Run `ruff check plugins/plugin-creator/scripts/plugin_validator.py`
3. Verify no duplicate constants with `sort < file | uniq -d`
4. Import constants in REPL: `from plugin_validator import HK001, MC001, LS001, AG001`

**Can Parallelize With**: Task 1 (enum), Task 3 (file detection)
**Reason**: String constants are independent additions
**Handoff**: Provide file diff showing 40 new constants, verification command outputs
