# Registry Schema Examples

Companion to [design-rule-provenance-registry.md](./design-rule-provenance-registry.md). Contains concrete JSON examples for each claim type using real rule data from the provenance audit.

## Claim type: enum_set

An enumerated set of valid values. The assertion is "this set of strings is the complete list of valid X."

### HK002.valid_event_types

```json
{
  "rule_code": "HK002",
  "claim_name": "valid_event_types",
  "description": "The set of recognized hook event type names that can appear as top-level keys in hooks.json",
  "claim_type": "enum_set",

  "authority": {
    "vendor_file": ".claude/vendor/claude_code/plugins/plugin-dev/skills/hook-development/SKILL.md",
    "anchor_selector": "#hook-input-and-output",
    "authority_url": "https://docs.anthropic.com/en/docs/claude-code/hooks"
  },

  "extraction": {
    "prompt_template": "The following markdown section describes Claude Code hook events. List every event type name mentioned in this section. Return as a JSON array of strings, with exact casing as shown in the source. Include only event type names (e.g., SessionStart, PreToolUse), not field names or other identifiers.\n\nSection:\n{{section}}",
    "output_schema": {
      "type": "array",
      "items": { "type": "string" }
    },
    "post_processing": "sort"
  },

  "assertion_location": {
    "file": "packages/skilllint/schemas/claude_code/v1.json",
    "symbol": "$.enums.valid_event_types.values",
    "source_type": "schema_json_enum"
  },

  "x-audited": {
    "date": "2026-03-23",
    "source": ".claude/vendor/claude_code/plugins/plugin-dev/skills/hook-development/SKILL.md"
  }
}
```

### HK003.valid_hook_types

```json
{
  "rule_code": "HK003",
  "claim_name": "valid_hook_types",
  "description": "The set of recognized hook type values for the type field in hook entries",
  "claim_type": "enum_set",

  "authority": {
    "vendor_file": ".claude/vendor/claude_code/plugins/plugin-dev/skills/hook-development/SKILL.md",
    "anchor_selector": "#hook-types",
    "authority_url": "https://docs.anthropic.com/en/docs/claude-code/hooks"
  },

  "extraction": {
    "prompt_template": "The following markdown section describes Claude Code hook types. List every valid hook type value that can appear in the \"type\" field of a hook entry. Return as a JSON array of lowercase strings.\n\nSection:\n{{section}}",
    "output_schema": {
      "type": "array",
      "items": { "type": "string" }
    },
    "post_processing": "sort"
  },

  "assertion_location": {
    "file": "packages/skilllint/schemas/claude_code/v1.json",
    "symbol": "$.enums.valid_hook_types.values",
    "source_type": "schema_json_enum"
  },

  "x-audited": {
    "date": "2026-03-23",
    "source": ".claude/vendor/claude_code/plugins/plugin-dev/skills/hook-development/SKILL.md"
  }
}
```

### FM007.tool_field_names

```json
{
  "rule_code": "FM007",
  "claim_name": "tool_field_names",
  "description": "Frontmatter field names that accept tool specifications and should be comma-separated strings, not YAML arrays",
  "claim_type": "enum_set",

  "authority": {
    "vendor_file": ".claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/SKILL.md",
    "anchor_selector": "#frontmatter-fields",
    "authority_url": "https://docs.anthropic.com/en/docs/claude-code/plugins"
  },

  "extraction": {
    "prompt_template": "The following markdown section describes frontmatter fields for Claude Code plugins. List every field name that accepts tool names or tool patterns as its value. Return as a JSON array of strings with exact field name casing.\n\nSection:\n{{section}}",
    "output_schema": {
      "type": "array",
      "items": { "type": "string" }
    },
    "post_processing": "sort"
  },

  "assertion_location": {
    "file": "packages/skilllint/schemas/claude_code/v1.json",
    "symbol": "$.enums.tool_field_names.values",
    "source_type": "schema_json_enum"
  },

  "x-audited": {
    "date": "2026-03-23",
    "source": ".claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/SKILL.md"
  }
}
```

## Claim type: scalar

A single value constraint. The assertion is "this field has this specific limit/value."

### AS001.max_name_length

```json
{
  "rule_code": "AS001",
  "claim_name": "max_name_length",
  "description": "Maximum character length for skill names",
  "claim_type": "scalar",

  "authority": {
    "vendor_file": "packages/skilllint/schemas/agentskills_io/v1.json",
    "anchor_selector": null,
    "authority_url": "https://agentskills.io/specification"
  },

  "extraction": {
    "prompt_template": "The following JSON schema defines the 'name' field for skills. What is the maxLength value for the name field? Return as a JSON object: {\"max_name_length\": <integer>}\n\nSchema:\n{{section}}",
    "output_schema": {
      "type": "object",
      "properties": {
        "max_name_length": { "type": "integer" }
      }
    },
    "post_processing": null
  },

  "assertion_location": {
    "file": "packages/skilllint/schemas/agentskills_io/v1.json",
    "symbol": "$.properties.name.maxLength",
    "source_type": "schema_json_field"
  },

  "x-audited": {
    "date": "2026-03-23",
    "source": "packages/skilllint/schemas/agentskills_io/v1.json"
  }
}
```

Note: For AS001, the `maxLength` claim has direct provenance through the schema JSON (the schema itself is the authority, fetched by `fetch_spec_schema.py`). The regex pattern and consecutive-hyphen constraints are classified as opinions because they have no vendor source (see opinion catalog).

## Claim type: field_set

A set of field definitions with structural properties. The assertion is "these fields exist with these attributes."

### PA001.restricted_agent_fields

```json
{
  "rule_code": "PA001",
  "claim_name": "restricted_agent_fields",
  "description": "Frontmatter fields that are restricted for plugin sub-agents (permissionMode, hooks, mcpServers)",
  "claim_type": "field_set",

  "authority": {
    "vendor_file": ".claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/references/manifest-reference.md",
    "anchor_selector": "#agents",
    "authority_url": "https://docs.anthropic.com/en/docs/claude-code/sub-agents"
  },

  "extraction": {
    "prompt_template": "The following markdown section describes plugin agent configuration. List every frontmatter field that is explicitly described as restricted, prohibited, or not supported for sub-agents. Return as a JSON array of field name strings.\n\nSection:\n{{section}}",
    "output_schema": {
      "type": "array",
      "items": { "type": "string" }
    },
    "post_processing": "sort"
  },

  "assertion_location": {
    "file": "packages/skilllint/schemas/claude_code/v1.json",
    "symbol": "$.file_types.agent.restricted_fields",
    "source_type": "schema_json_field"
  },

  "x-audited": {
    "date": "2026-03-23",
    "source": ".claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/references/manifest-reference.md"
  }
}
```

## Opinion catalog entries

These go in `opinion-catalog.json`, not in the provenance registry.

### FM004 -- multiline YAML detection

```json
{
  "rule_code": "FM004",
  "description": "Detects multiline YAML syntax indicators (|, >, |-, >-, |+, >+) in the description field",
  "rationale": "No vendor schema restricts multiline syntax. Claude Code runtime accepts block scalars. This is a style preference to encourage single-line descriptions for portability.",
  "constraint": "regex r\"description:\\s*[|>][-+]?\\s*\\n\" applied to raw frontmatter text",
  "references": [
    "Code comment at plugin_validator.py:454-456: FM004 -- multiline YAML accepted by Claude Code runtime"
  ]
}
```

### AS007 -- wildcard tool detection

```json
{
  "rule_code": "AS007",
  "description": "Detects wildcard patterns (containing *) in the tools frontmatter field",
  "rationale": "No schema or vendor doc defines wildcard validation for tool names. This is a safety recommendation to discourage overly broad tool permissions.",
  "constraint": "\"*\" in tool_name for each tool name string",
  "references": []
}
```

### AS001.name_pattern (partial opinion)

```json
{
  "rule_code": "AS001",
  "description": "Skill name must match ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ with no consecutive hyphens",
  "rationale": "The maxLength=64 constraint is schema-backed (see provenance registry AS001.max_name_length). The regex pattern and consecutive-hyphen rule have no vendor source. They enforce a stricter convention than the spec requires.",
  "constraint": "_NAME_RE = re.compile(r\"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$\"), _CONSECUTIVE_HYPHENS_RE = re.compile(r\"--\")",
  "references": [
    "Schema maxLength=64 in agentskills_io/v1.json, cursor/v1.json, codex/v1.json (backed -- see provenance registry)"
  ]
}
```

### FM007.disallowed_tools_field (partial opinion)

```json
{
  "rule_code": "FM007",
  "description": "The field name disallowedTools is checked as a tool-accepting field that should use CSV format",
  "rationale": "The tools and allowed-tools fields appear in schema JSON. disallowedTools does not appear in any schema file. Including it in the check set is a lint opinion based on naming convention, not vendor documentation.",
  "constraint": "disallowedTools in the hardcoded set {\"tools\", \"disallowedTools\", \"allowed-tools\"}",
  "references": [
    "agentskills_io/v1.json: allowed-tools typed as string",
    "claude_code/v1.json: tools and allowed-tools fields defined (no type specified)"
  ]
}
```

## Full registry example

A complete `provenance-registry.json` with all claims identified in the provenance audit:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "description": "Rule Provenance Registry -- maps lint rule claims to upstream authority sources",
  "version": "1",
  "claims": {
    "HK002.valid_event_types": {
      "rule_code": "HK002",
      "claim_name": "valid_event_types",
      "description": "The set of recognized hook event type names",
      "claim_type": "enum_set",
      "authority": {
        "vendor_file": ".claude/vendor/claude_code/plugins/plugin-dev/skills/hook-development/SKILL.md",
        "anchor_selector": "#hook-input-and-output",
        "authority_url": "https://docs.anthropic.com/en/docs/claude-code/hooks"
      },
      "extraction": {
        "prompt_template": "List every event type name mentioned in this section. Return as a JSON array of strings with exact casing.\n\n{{section}}",
        "output_schema": { "type": "array", "items": { "type": "string" } },
        "post_processing": "sort"
      },
      "assertion_location": {
        "file": "packages/skilllint/schemas/claude_code/v1.json",
        "symbol": "$.enums.valid_event_types.values",
        "source_type": "schema_json_enum"
      },
      "x-audited": { "date": "2026-03-23", "source": ".claude/vendor/claude_code/plugins/plugin-dev/skills/hook-development/SKILL.md" }
    },
    "HK003.valid_hook_types": {
      "rule_code": "HK003",
      "claim_name": "valid_hook_types",
      "description": "The set of recognized hook type values",
      "claim_type": "enum_set",
      "authority": {
        "vendor_file": ".claude/vendor/claude_code/plugins/plugin-dev/skills/hook-development/SKILL.md",
        "anchor_selector": "#hook-types",
        "authority_url": "https://docs.anthropic.com/en/docs/claude-code/hooks"
      },
      "extraction": {
        "prompt_template": "List every valid hook type value for the \"type\" field. Return as a JSON array of lowercase strings.\n\n{{section}}",
        "output_schema": { "type": "array", "items": { "type": "string" } },
        "post_processing": "sort"
      },
      "assertion_location": {
        "file": "packages/skilllint/schemas/claude_code/v1.json",
        "symbol": "$.enums.valid_hook_types.values",
        "source_type": "schema_json_enum"
      },
      "x-audited": { "date": "2026-03-23", "source": ".claude/vendor/claude_code/plugins/plugin-dev/skills/hook-development/SKILL.md" }
    },
    "FM007.tool_field_names": {
      "rule_code": "FM007",
      "claim_name": "tool_field_names",
      "description": "Frontmatter field names that accept tool specifications",
      "claim_type": "enum_set",
      "authority": {
        "vendor_file": ".claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/SKILL.md",
        "anchor_selector": "#frontmatter-fields",
        "authority_url": "https://docs.anthropic.com/en/docs/claude-code/plugins"
      },
      "extraction": {
        "prompt_template": "List every field name that accepts tool names or tool patterns as its value. Return as a JSON array of strings.\n\n{{section}}",
        "output_schema": { "type": "array", "items": { "type": "string" } },
        "post_processing": "sort"
      },
      "assertion_location": {
        "file": "packages/skilllint/schemas/claude_code/v1.json",
        "symbol": "$.enums.tool_field_names.values",
        "source_type": "schema_json_enum"
      },
      "x-audited": { "date": "2026-03-23", "source": ".claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/SKILL.md" }
    },
    "AS001.max_name_length": {
      "rule_code": "AS001",
      "claim_name": "max_name_length",
      "description": "Maximum character length for skill names",
      "claim_type": "scalar",
      "authority": {
        "vendor_file": "packages/skilllint/schemas/agentskills_io/v1.json",
        "anchor_selector": null,
        "authority_url": "https://agentskills.io/specification"
      },
      "extraction": {
        "prompt_template": "What is the maxLength value for the name field? Return as JSON: {\"max_name_length\": <integer>}\n\n{{section}}",
        "output_schema": { "type": "object", "properties": { "max_name_length": { "type": "integer" } } },
        "post_processing": null
      },
      "assertion_location": {
        "file": "packages/skilllint/schemas/agentskills_io/v1.json",
        "symbol": "$.properties.name.maxLength",
        "source_type": "schema_json_field"
      },
      "x-audited": { "date": "2026-03-23", "source": "packages/skilllint/schemas/agentskills_io/v1.json" }
    },
    "PA001.restricted_agent_fields": {
      "rule_code": "PA001",
      "claim_name": "restricted_agent_fields",
      "description": "Frontmatter fields restricted for plugin sub-agents",
      "claim_type": "field_set",
      "authority": {
        "vendor_file": ".claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/references/manifest-reference.md",
        "anchor_selector": "#agents",
        "authority_url": "https://docs.anthropic.com/en/docs/claude-code/sub-agents"
      },
      "extraction": {
        "prompt_template": "List every frontmatter field described as restricted or not supported for sub-agents. Return as a JSON array of field name strings.\n\n{{section}}",
        "output_schema": { "type": "array", "items": { "type": "string" } },
        "post_processing": "sort"
      },
      "assertion_location": {
        "file": "packages/skilllint/schemas/claude_code/v1.json",
        "symbol": "$.file_types.agent.restricted_fields",
        "source_type": "schema_json_field"
      },
      "x-audited": { "date": "2026-03-23", "source": ".claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/references/manifest-reference.md" }
    }
  }
}
```
