---
task: "9"
title: "MCPConfigValidator Implementation"
status: not-started
agent: "@python-cli-architect"
dependencies: ["1", "2", "3", "5"]
priority: 3
complexity: m
---

## Task 6: LSPConfig Pydantic Models

**Status**: NOT STARTED
**Agent**: @python-cli-architect
**Dependencies**: Task 2
**Priority**: 2
**Complexity**: M
**Accuracy Risk**: High

#### Context

Need Pydantic models to validate .lsp.json language server configuration with extensive optional fields.

#### Objective

Create type-safe Pydantic models for LSP server configuration validation with comprehensive field validation.

#### Required Inputs

- Architecture spec: ./architect-plugin-linter.md lines 224-265 (LSPConfig schema)
- Official docs: <https://docs.anthropic.com/en/docs/claude-code/plugins.md#lsp-servers> (cite)
- Example .lsp.json files from codebase

#### Requirements

1. Create `LSPTransport` StrEnum with values: STDIO, SOCKET
2. Create `LSPServer` Pydantic model with 12 fields per architecture spec
3. Create `LSPConfig` Pydantic model with lspServers dict
4. Add field validators for:
   - Command non-empty string
   - extensionToLanguage non-empty dict
   - Extension keys start with dot (e.g., ".py")
   - Language values are lowercase identifiers
   - Timeouts are positive integers
   - maxRestarts is positive integer

#### Constraints

- MUST cite official schema URL in model docstrings
- MUST use Field(default_factory) for all list/dict fields
- MUST validate extension format (.py not py or *.py)
- MUST enforce lowercase language identifiers
- Timeout validation MUST check positive not just non-negative

#### Expected Outputs

- Modified file: `plugins/plugin-creator/scripts/plugin_validator.py` (new models section)
- 3 new models (LSPTransport enum, LSPServer, LSPConfig)
- Field validators for extension format, language format, timeouts
- Docstrings with schema source citation

#### Acceptance Criteria

1. LSPServer model has all 12 fields with correct types
2. extensionToLanguage field validated for dot-prefix extensions
3. Language identifiers validated for lowercase
4. Timeout values validated for positive integers
5. Transport enum restricts to stdio/socket only
6. Empty extensionToLanguage dict rejected with error

#### Verification Steps

1. Create valid .lsp.json, parse with LSPConfig.model_validate()
2. Create invalid config with extension "py" (no dot), verify error
3. Create invalid config with language "Python" (not lowercase), verify error
4. Create invalid config with negative timeout, verify error
5. Run `mypy --strict` on modified file
6. Verify Pydantic errors reference correct field names

#### CoVe Checks

**Accuracy Risk**: High (complex schema with many optional fields)

- Key claims to verify:
  - All 12 LSPServer fields match official schema
  - Required vs optional fields correct
  - Default values match schema specification
  - Validation rules match official requirements

- Verification questions:
  1. Is extensionToLanguage required or optional?
  2. Are timeout fields in milliseconds or seconds?
  3. Does transport default to stdio in official schema?
  4. Are there additional optional fields not in architecture spec?

- Evidence to collect:
  - Fetch official schema: `WebFetch("https://docs.anthropic.com/en/docs/claude-code/plugins.md")`
  - Cross-reference all 12 fields with official documentation
  - Check example .lsp.json files for actual usage patterns

- Revision rule:
  - If official schema has additional fields, add them with Optional types
  - If field requirements differ, follow official schema
  - Document any schema ambiguities in code comments

**Can Parallelize With**: Task 4 (HookConfig), Task 5 (MCPConfig), Task 7 (Agent enums)
**Reason**: Independent schema models
**Handoff**: Provide model code, verification outputs, official schema comparison
