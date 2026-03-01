---
task: "8"
title: "HookConfigValidator Implementation"
status: not-started
agent: "@python-cli-architect"
dependencies: ["1", "2", "3", "4"]
priority: 3
complexity: l
---

## Task 5: MCPConfig Pydantic Models

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: Task 2
**Priority**: 2
**Complexity**: S
**Accuracy Risk**: High

#### Context

Need Pydantic models to validate .mcp.json server configuration structure against MCP protocol specification.

#### Objective

Create type-safe Pydantic models for MCP server configuration validation.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 196-222 (MCPConfig schema)
- Official docs: <https://modelcontextprotocol.io/docs/server> (cite as comment)
- Example .mcp.json files from codebase

#### Requirements

1. Create `MCPServer` Pydantic model with fields: command (required), args, env, cwd
2. Create `MCPConfig` Pydantic model with mcpServers dict structure
3. Add field validators for:
   - Command non-empty string validation
   - Args is list of strings (not single string)
   - Env is dict[str, str] validation
   - CWD path existence check (warning only)

#### Constraints

- MUST cite official schema URL in model docstrings
- MUST use Field(default_factory=list) for args and Field(default_factory=dict) for env
- MUST NOT execute commands during validation
- CWD validation MUST be warning not error (path may not exist at validation time)

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (new models section)
- 2 new Pydantic models defined
- Field validators for command, args, env, cwd
- Docstrings with schema source citation

#### Acceptance Criteria

1. MCPServer model enforces command as required string
2. Args field validates as list not string
3. Env field validates as string→string dict
4. CWD validation produces warning not error when path missing
5. Empty command string rejected with error
6. Model passes Pydantic schema validation

#### Verification Steps

1. Create valid .mcp.json, parse with MCPConfig.model_validate()
2. Create invalid config with args as string, verify validation error
3. Create invalid config with empty command, verify error
4. Run `mypy --strict` on modified file
5. Test CWD path check produces warning not error

#### CoVe Checks

**Accuracy Risk**: High (schema compliance critical)

- Key claims to verify:
  - Required vs optional fields match official schema
  - Field types match MCP specification
  - Validation rules match schema requirements

- Verification questions:
  1. Is command field required or optional in official spec?
  2. Are args and env truly optional with empty defaults?
  3. Does official schema specify CWD validation behavior?

- Evidence to collect:
  - Fetch official schema: `WebFetch("https://modelcontextprotocol.io/docs/server")`
  - Cross-reference field requirements
  - Test with real .mcp.json from codebase if available

- Revision rule:
  - If official schema differs from architecture spec, follow official schema
  - Document validation behavior in docstrings

**Can Parallelize With**: Task 4 (HookConfig), Task 6 (LSPConfig), Task 7 (Agent enums)
**Reason**: Independent schema models for different config files
**Handoff**: Provide model code, verification outputs, schema cross-reference
