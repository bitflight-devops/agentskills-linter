# skilllint Rule Catalog

Complete reference for all rule IDs emitted by `skilllint`. Use `skilllint check --verbose <path>` to see explanatory text alongside each violation.

---

## FM — Frontmatter Rules

Validate YAML frontmatter in SKILL.md, agent .md, and command .md files.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| FM001 | error | no | Frontmatter block is missing entirely |
| FM002 | error | no | Frontmatter is not valid YAML |
| FM003 | error | no | Required frontmatter field is missing (e.g. `name` per agentskills spec) |
| FM004 | error | **yes** | `description` uses a YAML multiline block scalar (`` >- ``, `` \| ``, `` \|- ``); Claude Code skill indexer reads this as literal `>-`. Use a single-line string. |
| FM005 | error | no | `name` field contains invalid characters (must be lowercase letters, numbers, hyphens only; max 64 chars) |
| FM006 | error | no | `description` exceeds 1024 characters |
| FM007 | error | **yes** | `allowed-tools` is a YAML array instead of a comma-separated string |
| FM008 | error | **yes** | Another field that requires a comma-separated string is specified as a YAML array |
| FM009 | error | **yes** | Unquoted colon in `description` or other string field causes YAML parse failure |
| FM010 | error | **yes** | `name` field does not match the directory name (same as AS002; FM010 is the frontmatter-level check) |

**Common FM fix:** Run `skilllint check --fix <path>` — FM004, FM007, FM008, FM009, FM010 are all auto-fixable.

---

## SK — Skill Quality Rules

Validate skill name, description quality, and token budget.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| SK001 | error | **yes** | Skill name is not lowercase kebab-case |
| SK002 | error | **yes** | Skill name contains underscores (use hyphens) |
| SK003 | error | **yes** | Skill name has leading/trailing/consecutive hyphens, or name field is empty |
| SK004 | warning | no | Skill description is very short (< 20 chars); may not trigger auto-invocation |
| SK005 | warning | no | Skill description lacks trigger phrases ("Use when...", keywords); Claude may not auto-invoke |
| SK006 | warning | no | (Legacy) Skill is approaching token limit; see AS005 for current thresholds |
| SK007 | error | no | (Legacy) Skill exceeds token limit; see AS005 for current thresholds |
| SK008 | info | no | Skill has no `argument-hint` but appears to accept arguments based on `$ARGUMENTS` usage |
| SK009 | info | no | Token count report (informational; always emitted with `--verbose`) |

**Token limit fix (AS005):** Move large sections to `skills/<name>/references/<file>.md` and add a link from SKILL.md. Thresholds are `TOKEN_WARNING_THRESHOLD` (warning) and `TOKEN_ERROR_THRESHOLD` (error) — body text only, frontmatter excluded. Run `skilllint rules` to see current values.

---

## AS — AgentSkills Open Standard Rules

Cross-platform compliance with the [agentskills.io](https://agentskills.io) specification.
Use `skilllint check --filter <ID> --verbose <path>` to see detailed output for any AS rule.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| AS001 | error | no | Invalid skill name format — must be lowercase alphanumeric with hyphens, 1–64 chars, no consecutive hyphens, start/end with letter or digit |
| AS002 | error | **yes** | Skill `name` field does not match the parent directory name |
| AS003 | error | no | `description` field is missing or empty |
| AS004 | error | no | `description` contains HTML tags (not allowed) |
| AS005 | warning | no | SKILL.md body exceeds token threshold (`TOKEN_WARNING_THRESHOLD` warning, `TOKEN_ERROR_THRESHOLD` error — body only, frontmatter excluded); split or move content to `references/` |
| AS006 | info | no | No evaluation queries file found (optional but recommended) |

**Full detail:** Use `skilllint check --filter <ID> --verbose <path>` (e.g. `skilllint check --filter AS001 --verbose <path>`) to see detailed output for any AS rule.

---

## LK — Internal Link Rules

Validate internal markdown links in SKILL.md and agent files.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| LK001 | error | no | Internal link target file does not exist on disk |
| LK002 | warning | no | Internal link target exists but the anchor fragment (#section) does not match any heading |

**LK001 fix:** Verify the linked file path is correct. Links in `skills/<name>/SKILL.md` are relative to the skill directory, not the plugin root.

---

## PD — Progressive Disclosure Rules

Validate the `references/` directory structure for progressive disclosure.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| PD001 | warning | no | Large skill (approaching AS005 threshold) has no `references/` directory; consider adding one |
| PD002 | warning | no | `references/` directory exists but is not linked from SKILL.md |
| PD003 | info | no | Files in `references/` are never referenced in SKILL.md |

---

## PL — Plugin Manifest Rules

Validate `plugin.json` structure.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| PL001 | error | no | `plugin.json` is missing |
| PL002 | error | no | `plugin.json` is not valid JSON |
| PL003 | error | no | Required `name` field is missing from `plugin.json` |
| PL004 | error | no | A path in `plugin.json` does not start with `./` |
| PL005 | error | no | Referenced file in `plugin.json` does not exist |

---

## HK — Hook Rules

Validate `hooks.json` and inline hook configurations.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| HK001 | error | no | `hooks.json` is not valid JSON |
| HK002 | error | no | Hook event name is not a recognized Claude Code event |
| HK003 | error | no | Hook `type` is not one of: `command`, `prompt`, `agent` |
| HK004 | warning | no | Hook script path does not exist on disk |
| HK005 | warning | no | Hook script is not executable (`chmod +x` required) |

---

## NR — Namespace Reference Rules

Validate namespace-qualified skill references (e.g. `plugin-name:skill-name`).

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| NR001 | warning | no | Namespace reference uses a plugin name that is not installed |
| NR002 | warning | no | Namespace reference uses a skill name not found in the referenced plugin |

---

## SL — Symlink Rules

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| SL001 | warning | **yes** | Symlink target has trailing whitespace or newline characters |

---

## TC — Token Count

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| TC001 | info | no | Token count report for a file (always shown with `--verbose`; use `--tokens-only` for integer output) |

---

## Cursor-Specific Rules

These only fire when `--platform cursor` is used.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| cursor-mdc-frontmatter | error | no | Cursor `.mdc` file frontmatter is invalid |
| cursor-mdc-glob | warning | no | Cursor `.mdc` `globs` field is missing or empty |

---

## Quick Reference: Auto-Fixable Rules

Run `skilllint check --fix <path>` to automatically fix:

- **FM004** — multiline block scalar in description
- **FM007** — allowed-tools as YAML array
- **FM008** — other comma-separated fields as YAML array
- **FM009** — unquoted colon in string field
- **FM010 / AS002** — name/directory mismatch
- **SK001** — skill name contains uppercase characters (lowercased)
- **SK002** — skill name contains underscores (replaced with hyphens)
- **SK003** — skill name has leading/trailing/consecutive hyphens (normalized)
- **SL001** — symlink outside plugin directory

All other rules (including AS005 token size, PD, LK, HK series) require manual fixes.
