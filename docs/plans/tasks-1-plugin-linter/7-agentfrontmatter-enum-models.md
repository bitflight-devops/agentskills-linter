---
task: "7"
title: "AgentFrontmatter Enum Models"
status: not-started
agent: "@python-cli-architect"
dependencies: ["2"]
priority: 2
complexity: s
---

## Priority 1: Schema Models (Depends on P0)

## Task 4: HookConfig Pydantic Models

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: Task 2
**Priority**: 2
**Complexity**: M
**Accuracy Risk**: High

#### Context

Need Pydantic models to validate hooks.json structure against official Claude Code hook schema with 15 event types and 3 hook action types.

#### Objective

Create type-safe Pydantic models for hooks.json validation that enforce official schema constraints.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 135-194 (HookConfig schema)
- Official docs: <https://docs.anthropic.com/en/docs/claude-code/hooks.md> (cite as comment)
- Example hooks.json files from codebase

#### Requirements

1. Create `HookType` StrEnum with values: COMMAND, PROMPT, AGENT
2. Create `HookEventType` StrEnum with all 15 valid event names
3. Create `HookDefinition` Pydantic model with discriminated union for type field
4. Create `EventMatcher` Pydantic model with matcher and hooks list
5. Create `HookConfig` Pydantic model with hooks dict structure
6. Add field validators for:
   - Hook type field presence matching discriminator
   - Regex pattern validity in matcher field
   - Timeout positive integer validation

#### Constraints

- MUST cite official schema URL in model docstrings
- MUST use Pydantic 2.0+ discriminated unions for hook type
- MUST NOT execute regex patterns during validation (compile only)
- MUST preserve case-sensitivity of event names

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (new models section)
- 5 new Pydantic models defined
- Field validators for type matching and regex validation
- Docstrings with schema source citations

#### Acceptance Criteria

1. All 15 event types defined in HookEventType enum
2. HookDefinition validates type discriminator correctly
3. Invalid regex patterns rejected with clear error
4. Timeout validation rejects zero and negative values
5. Models pass Pydantic schema validation
6. Docstrings cite official docs URL

#### Verification Steps

1. Create valid hooks.json test case, parse with HookConfig.model_validate()
2. Create invalid hooks.json with bad event type, verify validation error
3. Create invalid regex pattern, verify compilation error caught
4. Run `mypy --strict` on modified file
5. Verify Pydantic error messages reference field names correctly

#### CoVe Checks

**Accuracy Risk**: High (schema compliance is critical)

- Key claims to verify:
  - All 15 event types match official documentation exactly
  - Hook type discriminator matches official schema
  - Field validators match official requirements

- Verification questions:
  1. Are all 15 event type names spelled and capitalized correctly?
  2. Does hook type discriminator allow all 3 action types?
  3. Are optional vs required fields correct per schema?

- Evidence to collect:
  - Fetch official schema: `WebFetch("https://docs.anthropic.com/en/docs/claude-code/hooks.md")`
  - Cross-reference event names with official list
  - Test with real hooks.json from codebase

- Revision rule:
  - If official schema differs from architecture spec, update models to match official schema
  - Document any discrepancies found

**Can Parallelize With**: Task 5 (MCPConfig models), Task 6 (LSPConfig models), Task 7 (Agent enum models)
**Reason**: Schema models are independent (different JSON files)
**Handoff**: Provide model code, verification test outputs, official schema cross-reference
