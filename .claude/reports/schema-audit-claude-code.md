# Schema Audit: Claude Code Platform Schema v1

**Schema under audit**: `packages/skilllint/schemas/claude_code/v1.json`
**Audit date**: 2026-03-10

## Sources Consulted

1. `packages/skilllint/schemas/claude_code/v1.json` — the schema under audit
2. `.claude/vendor/claude_code/plugins/README.md` — plugin system overview and structure
3. `.claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/SKILL.md` — authoritative plugin structure reference
4. `.claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/references/manifest-reference.md` — complete `plugin.json` field reference
5. `.claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/references/component-patterns.md` — component organization patterns
6. `.claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/examples/minimal-plugin.md` — minimal plugin example
7. `.claude/vendor/claude_code/plugins/plugin-dev/skills/plugin-structure/examples/advanced-plugin.md` — full enterprise plugin example
8. Real `plugin.json` files sampled: `agent-sdk-dev`, `feature-dev`, `explanatory-output-style`

---

## Schema Structure Note

The schema uses a custom flat metadata format rather than standard JSON Schema:

```json
"file_types": {
  "plugin": {
    "required_fields": ["name", "version", "description"],
    "optional_fields": ["author", "skills", "agents", "commands", "hooks"]
  }
}
```

This format cannot validate field types, object shapes, format constraints, or disallow unknown properties. All findings concern the accuracy of `required_fields` / `optional_fields` lists relative to vendor documentation, and missing documented fields.

---

## Findings

### PLUGIN section

**1. `version` incorrectly listed as required**

- Schema says: `"required_fields": ["name", "version", "description"]`
- Docs say (`manifest-reference.md`, "version" section): `"Default": "0.1.0" if not specified`. The minimal-plugin.md example shows only `{ "name": "hello-world" }` — the docs state: "Only the required `name` field".
- **Verdict**: FAIL — `version` is not required for plugin; it has a documented default of `"0.1.0"`.

**2. `description` incorrectly listed as required**

- Schema says: `"required_fields": ["name", "version", "description"]`
- Docs say (`manifest-reference.md`, "Minimal vs. Complete Examples"): `{ "name": "hello-world" }` is the "Bare minimum for a working plugin." `description` appears under "Recommended Metadata", not required fields.
- **Verdict**: FAIL — `description` is not required for plugin; it is recommended metadata only.

**3. `skills` listed as optional field — phantom field**

- Schema says: `"optional_fields": ["author", "skills", "agents", "commands", "hooks"]`
- Docs say (`manifest-reference.md`, "Component Path Fields"): Component path fields are `commands`, `agents`, `hooks`, and `mcpServers`. There is no `skills` field in `plugin.json`. Skills are auto-discovered from the `skills/` directory and are not enumerated in the manifest.
- **Verdict**: FAIL — `skills` is a phantom field with no documentation backing. It does not exist in `plugin.json`.

**4. `mcpServers` missing from optional_fields**

- Schema says: `"optional_fields": ["author", "skills", "agents", "commands", "hooks"]`
- Docs say (`manifest-reference.md`, "mcpServers" section): `mcpServers` is a documented optional component path field in `plugin.json`. The advanced-plugin.md example uses `"mcpServers": "./.mcp.json"`.
- **Verdict**: FAIL — `mcpServers` is a documented optional field absent from the schema.

**5. `homepage`, `repository`, `license`, `keywords` missing from optional_fields**

- Schema says: Four fields not listed.
- Docs say (`manifest-reference.md`, "Metadata Fields" section): `homepage`, `repository`, `license`, and `keywords` are all documented optional fields with full type and format specifications.
- **Verdict**: FAIL — four documented optional fields are absent from the schema.

**6. `author` type is undocumented in schema**

- Docs say (`manifest-reference.md`, "author" section): `author` is either an Object (`name` required, `email`/`url` optional) OR a plain string in npm-style format.
- **Verdict**: OBSERVATION — the custom schema format carries no type information; this is a structural limitation.

---

### SKILL section

**7. `version` listed as required — ambiguous**

- Docs: `version` appears in all documented SKILL.md examples but no statement explicitly says it is required or has a default for skills.
- **Verdict**: AMBIGUOUS — marking it required is defensible but unconfirmed by docs.

**8. `triggers`, `tools`, `permissions`, `dependencies` listed as optional — phantom fields**

- Schema says: `"optional_fields": ["author", "triggers", "tools", "permissions", "dependencies"]`
- Docs say: None of `triggers`, `tools`, `permissions`, or `dependencies` appear in any documented SKILL.md frontmatter example or specification. The plugin-structure SKILL.md itself uses only `name`, `description`, `version`.
- **Verdict**: FAIL — four listed optional skill fields have no documentation backing.

---

### AGENT section

**9. `name` incorrectly listed as required**

- Schema says: `"required_fields": ["name", "version", "description"]`
- Docs say (`SKILL.md`, "Agents" section, "File format"): Agent frontmatter contains `description` and `capabilities`. No `name` field is shown. Agents are identified by their filename.
- **Verdict**: FAIL — `name` is not a documented agent frontmatter field. Identity comes from the filename.

**10. `version` listed as required for agent — no documentation backing**

- Docs: No agent frontmatter example includes a `version` field. The documented format is `description` + `capabilities`.
- **Verdict**: FAIL — `version` is not a documented agent frontmatter field.

**11. `capabilities` missing from optional_fields**

- Schema says: `"optional_fields": ["author", "tools", "permissions", "model"]`
- Docs say (`SKILL.md`, "Agents" section): `capabilities` is an explicitly listed field in the documented agent frontmatter format and in the advanced-plugin.md example.
- **Verdict**: FAIL — `capabilities` is a documented agent frontmatter field absent from the schema.

**12. `tools`, `permissions`, `model` in optional_fields — no documentation backing**

- Docs: None of `tools`, `permissions`, or `model` appear in any documented agent frontmatter example.
- **Verdict**: FAIL — three listed optional agent fields have no documentation backing.

---

### COMMAND section

**13. `version` listed as required — no documentation backing**

- Schema says: `"required_fields": ["name", "version"]`
- Docs say (`SKILL.md`, "Commands" section): Command frontmatter contains `name` and `description`. No `version` field appears in any command example.
- **Verdict**: FAIL — `version` is not a documented command frontmatter field.

**14. `description` listed as optional — should be required**

- Schema says: `"required_fields": ["name", "version"]`, `"optional_fields": ["description", "author"]`
- Docs: Every command example includes `description`. The minimal-plugin.md command shows `description: "Prints a friendly greeting message"`. The canonical format shows `name` + `description`.
- **Verdict**: FAIL — `description` is used in all documented command examples but listed as optional; the undocumented `version` is listed as required instead.

---

## Summary of All Findings

| # | Section | Field | Schema | Docs | Verdict |
|---|---------|-------|--------|------|---------|
| 1 | plugin | `version` | required | optional (default `"0.1.0"`) | FAIL |
| 2 | plugin | `description` | required | recommended, not required | FAIL |
| 3 | plugin | `skills` | optional | not a plugin.json field | FAIL |
| 4 | plugin | `mcpServers` | absent | documented optional field | FAIL |
| 5 | plugin | `homepage`, `repository`, `license`, `keywords` | absent | all documented optional fields | FAIL |
| 6 | plugin | `author` type | no type | object or string | OBSERVATION |
| 7 | skill | `version` | required | in all examples, not explicitly required | AMBIGUOUS |
| 8 | skill | `triggers`, `tools`, `permissions`, `dependencies` | optional | no documentation backing | FAIL |
| 9 | agent | `name` | required | not a frontmatter field | FAIL |
| 10 | agent | `version` | required | not a documented agent field | FAIL |
| 11 | agent | `capabilities` | absent | documented optional frontmatter field | FAIL |
| 12 | agent | `tools`, `permissions`, `model` | optional | no documentation backing | FAIL |
| 13 | command | `version` | required | not a documented command field | FAIL |
| 14 | command | `description` | optional | used in all examples, canonical format | FAIL |

---

## Summary Verdict

**FAIL**

13 distinct failures against vendor documentation:

- Two sections (plugin, agent) have required fields that are either not required per docs or not valid fields at all
- One phantom field (`skills` in plugin) exists with no documentation backing
- Multiple documented fields absent: `mcpServers`, `homepage`, `repository`, `license`, `keywords` (plugin); `capabilities` (agent)
- Multiple undocumented fields listed as valid optionals across skill and agent sections
- Command section inverts required/optional status of `description` vs. `version`
- The schema format is structurally incapable of enforcing the type, format, and shape constraints that the vendor documentation specifies

The schema as written would both reject valid minimally-specified plugins (demands `version` and `description` as required) and pass invalid structures (lists non-existent fields as valid, cannot check types).
