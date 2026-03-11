# Schema Audit — 2026-03-10

Auditor: Claude Code (claude-sonnet-4-6)
Date: 2026-03-10
Scope: All bundled JSON schema files in packages/skilllint/schemas/

---

## Schema 1: Cursor `.mdc` — `packages/skilllint/schemas/cursor/v1.json` (`file_types.mdc`)

### Source Consulted

- Primary: `.planning/research/cursor-mdc-schema-correction.md` (HIGH confidence, sourced from
  official Cursor docs at `cursor.com/docs/context/rules`, captured 2026-03-10)

### Official Spec Summary

Three frontmatter fields are documented for `.mdc` rule files:

| Field         | Type                        | Required? | Notes |
|---------------|-----------------------------|-----------|-------|
| `description` | string                      | No        | Required only for "Apply Intelligently" rule type |
| `globs`       | string or array of strings  | No        | Controls auto-attach behavior |
| `alwaysApply` | boolean                     | No        | When true, rule injects into every context |

No other frontmatter fields are documented. The `type` field appears in community examples but is
absent from all official Cursor docs.

### Comparison

| Field               | Official spec                          | Schema              | Match? |
|---------------------|----------------------------------------|---------------------|--------|
| `required` array    | empty (no field required universally)  | `[]`                | PASS |
| `description` type  | string                                 | string, minLength 1 | PASS |
| `globs` type        | string or array of strings             | oneOf [string, array] | PASS |
| `alwaysApply` type  | boolean                                | boolean             | PASS |
| `additionalProperties` | not documented beyond three fields  | false               | PASS |

### Result: PASS

The schema was corrected from an earlier version that had `"required": ["description"]`; the
current version correctly uses `"required": []`.

---

## Schema 2: Cursor `skill_md` — `packages/skilllint/schemas/cursor/v1.json` (`file_types.skill_md`)

### Source Consulted

- `.planning/phases/02-platform-adapters/02-RESEARCH.md` — agentskills.io open standard section
  (HIGH confidence)

### Comparison

| Field                  | Official spec                     | Schema               | Match? |
|------------------------|-----------------------------------|----------------------|--------|
| `name` required        | Yes                               | Yes                  | PASS |
| `description` required | Yes                               | Yes                  | PASS |
| `name` maxLength       | 64 chars                          | maxLength: 64        | PASS |
| `description` maxLength| 1024 chars                        | maxLength: 1024      | PASS |
| `additionalProperties` | permitted (extensible)            | true                 | PASS |
| `name` pattern         | lowercase alphanumeric + hyphens  | NOT in schema        | NOTE — delegated to AS001 |
| `description` HTML     | no `<` or `>`                     | NOT in schema        | NOTE — delegated to AS004 |

### Result: PASS (pattern/HTML constraints intentionally delegated to AS-series rules)

---

## Schema 3: Codex `.rules` — `packages/skilllint/schemas/codex/v1.json` (`file_types.prefix_rule`)

### Source Consulted

- `https://developers.openai.com/codex/rules/` (fetched 2026-03-10)

### Official Spec Summary

prefix_rule() function accepts:

| Field           | Required? |
|-----------------|-----------|
| `pattern`       | Yes       |
| `decision`      | No — allow/prompt/forbidden |
| `justification` | No        |
| `match`         | No        |
| `not_match`     | No        |

### Comparison

| Aspect               | Official spec         | Schema                        | Match? |
|----------------------|-----------------------|-------------------------------|--------|
| `known_fields` list  | all five fields       | identical list                | PASS |
| `valid_decisions`    | allow/prompt/forbidden | identical list               | PASS |
| `required_fields`    | pattern               | ["pattern"]                   | PASS |
| `x-experimental` flag | format is stable in current docs | true (flag set)  | LOW — see note |

### Note on `x-experimental` flag

Current OpenAI docs document the `.rules` format without experimental caveats. The flag was set
based on earlier docs. Verify whether the Codex adapter emits user-facing warnings based on this
flag — if yes, the warning is inaccurate.

### Result: CONDITIONAL PASS

Field lists accurate. `x-experimental` flag may be stale — impact depends on adapter behavior.

---

## Schema 4: Codex `agents_md` — `packages/skilllint/schemas/codex/v1.json` (`file_types.agents_md`)

### Source Consulted

- `https://developers.openai.com/codex/guides/agents-md/` (fetched 2026-03-10)

### Official Spec

AGENTS.md is plain Markdown — no YAML frontmatter schema. Validation is existence + non-empty.

### Result: PASS

The `x-non-empty: true` sentinel is the correct representation.

---

## Schema 5: Codex `skill_md` — `packages/skilllint/schemas/codex/v1.json` (`file_types.skill_md`)

Identical to Schema 2. **Result: PASS**

---

## Schema 6: Claude Code `plugin` — `packages/skilllint/schemas/claude_code/v1.json` (`file_types.plugin`)

### Source Consulted

- `https://code.claude.com/docs/en/plugins-reference.md` (fetched 2026-03-10)

### Official Spec

From the official plugins-reference:

| Field          | Required? |
|----------------|-----------|
| `name`         | **Yes — the ONLY required field** |
| `version`      | No — optional metadata |
| `description`  | No — optional metadata |
| `author`       | No |
| `homepage`     | No |
| `repository`   | No |
| `license`      | No |
| `keywords`     | No |
| `commands`     | No |
| `agents`       | No |
| `skills`       | No |
| `hooks`        | No |
| `mcpServers`   | No |
| `outputStyles` | No |
| `lspServers`   | No |

### Current Schema

```json
{
  "required_fields": ["name", "version", "description"],
  "optional_fields": ["author", "skills", "agents", "commands", "hooks"]
}
```

### Discrepancies

| Aspect              | Official spec    | Schema                   | Match? |
|---------------------|------------------|--------------------------|--------|
| `name` required     | Yes              | Yes                      | PASS |
| `version` required  | **No**           | Yes (required_fields)    | **FAIL** |
| `description` required | **No**        | Yes (required_fields)    | **FAIL** |
| `homepage`          | Optional         | Missing                  | **FAIL** |
| `repository`        | Optional         | Missing                  | **FAIL** |
| `license`           | Optional         | Missing                  | **FAIL** |
| `keywords`          | Optional         | Missing                  | **FAIL** |
| `mcpServers`        | Optional         | Missing                  | **FAIL** |
| `outputStyles`      | Optional         | Missing                  | **FAIL** |
| `lspServers`        | Optional         | Missing                  | **FAIL** |

### Result: FAIL

`version` and `description` incorrectly required. Only `name` is required. Seven documented
optional fields absent from schema.

---

## Schema 7: Claude Code `skill`, `agent`, `command` — `packages/skilllint/schemas/claude_code/v1.json`

### Source Consulted

- `https://code.claude.com/docs/en/plugins-reference.md` (fetched 2026-03-10)

### Current Schema

```json
"skill":   { "required_fields": ["name", "version", "description"], ... },
"agent":   { "required_fields": ["name", "version", "description"], ... },
"command": { "required_fields": ["name", "version"], ... }
```

### Official Spec

SKILL.md files use agentskills.io format — `name` and `description` required, no `version` field
in the file itself. Agent Markdown files use name + description frontmatter. `version` belongs in
`plugin.json`, not in individual component files.

### Discrepancies

`version` incorrectly listed as required for skill, agent, and command file types.

### Result: FAIL (stub schema with inaccurate required_fields)

---

## Summary of All Discrepancies Requiring Action

| Schema | Discrepancy | Severity |
|--------|-------------|----------|
| cursor/v1.json mdc | All correct | PASS |
| cursor/v1.json skill_md | Pattern/HTML delegated to AS-series (intentional) | PASS |
| codex/v1.json prefix_rule | `x-experimental` flag may be stale | LOW |
| codex/v1.json agents_md | Correct | PASS |
| codex/v1.json skill_md | Correct | PASS |
| claude_code/v1.json plugin | `version` and `description` wrongly required; only `name` is required | **HIGH** |
| claude_code/v1.json plugin | Missing 7 optional fields: homepage, repository, license, keywords, mcpServers, outputStyles, lspServers | MEDIUM |
| claude_code/v1.json skill | `version` not a field in SKILL.md files | **HIGH** |
| claude_code/v1.json agent | `version` not a field in agent Markdown files | **HIGH** |
| claude_code/v1.json command | `version` not documented as required for command files | **HIGH** |

### Priority Action Items

1. **HIGH — `claude_code/v1.json` plugin.required_fields**: Remove `version` and `description`.
   Correct: `["name"]`.

2. **HIGH — `claude_code/v1.json` skill/agent/command.required_fields**: Remove `version` from
   all three. SKILL.md files: `name` and `description` required (agentskills.io). Agent files:
   `name` and `description`. Command files: no `version` field.

3. **MEDIUM — `claude_code/v1.json` plugin.optional_fields**: Add 7 missing fields: `homepage`,
   `repository`, `license`, `keywords`, `mcpServers`, `outputStyles`, `lspServers`.

4. **LOW — `codex/v1.json` prefix_rule `x-experimental`**: Verify whether the adapter emits
   user-facing warnings based on this flag. If yes, remove or suppress.

---

## Sources

| Source | URL / Path | Confidence |
|--------|-----------|------------|
| Cursor .mdc rules | `.planning/research/cursor-mdc-schema-correction.md` (from cursor.com/docs/context/rules) | HIGH |
| agentskills.io SKILL.md | `.planning/phases/02-platform-adapters/02-RESEARCH.md` | HIGH |
| Codex prefix_rule | https://developers.openai.com/codex/rules/ | MEDIUM (fetched 2026-03-10) |
| Codex AGENTS.md | https://developers.openai.com/codex/guides/agents-md/ | MEDIUM |
| Claude Code plugin.json | https://code.claude.com/docs/en/plugins-reference.md | HIGH |
