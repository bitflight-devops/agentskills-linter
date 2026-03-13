# skilllint Rule Catalog

Complete reference for all rule IDs emitted by `skilllint`. Use `skilllint --verbose <path>` to see explanatory text alongside each violation.

---

## FM — Frontmatter Rules

Validate YAML frontmatter in SKILL.md, agent .md, and command .md files.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| FM001 | error | no | Frontmatter block is missing entirely |
| FM002 | error | no | Frontmatter is not valid YAML |
| FM003 | error | no | Required frontmatter field is missing (e.g. `name` per agentskills spec) |
| FM004 | error | **yes** | `description` uses a YAML multiline block scalar (`>-`, `|`, `|-`); Claude Code skill indexer reads this as literal `>-`. Use a single-line string. |
| FM005 | error | no | `name` field contains invalid characters (must be lowercase letters, numbers, hyphens only; max 64 chars) |
| FM006 | error | no | `description` exceeds 1024 characters |
| FM007 | error | **yes** | `allowed-tools` is a YAML array instead of a comma-separated string |
| FM008 | error | **yes** | Another field that requires a comma-separated string is specified as a YAML array |
| FM009 | error | **yes** | Unquoted colon in `description` or other string field causes YAML parse failure |
| FM010 | error | **yes** | `name` field does not match the directory name (same as AS002; FM010 is the frontmatter-level check) |

**Common FM fix:** Run `skilllint --fix <path>` — FM004, FM007, FM008, FM009, FM010 are all auto-fixable.

---

## SK — Skill Quality Rules

Validate skill name, description quality, and token budget.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| SK001 | warning | **yes** | Skill name is not lowercase kebab-case |
| SK002 | warning | **yes** | Skill name exceeds 64 characters |
| SK003 | warning | **yes** | Skill description is missing or empty |
| SK004 | warning | no | Skill description is very short (< 20 chars); may not trigger auto-invocation |
| SK005 | warning | no | Skill description lacks trigger phrases ("Use when...", keywords); Claude may not auto-invoke |
| SK006 | warning | no | Skill is approaching token limit (~3800 tokens); consider moving content to `references/` |
| SK007 | error | no | Skill exceeds token limit (~4000 tokens); must split or extract content to `references/` |
| SK008 | info | no | Skill has no `argument-hint` but appears to accept arguments based on `$ARGUMENTS` usage |
| SK009 | info | no | Token count report (informational; always emitted with `--verbose`) |

**SK006/SK007 fix:** Move large sections to `skills/<name>/references/<file>.md` and add a link from SKILL.md. Do not auto-fix — requires judgment about what to extract.

---

## AS — AgentSkills Open Standard Rules

Cross-platform compliance with the [agentskills.io](https://agentskills.io) specification. These fire regardless of `--platform`.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| AS001 | error | no | `name` field is missing (required by agentskills spec) |
| AS002 | error | **yes** | `name` field does not match the directory name |
| AS003 | warning | no | `description` field is missing (recommended by spec) |
| AS004 | warning | no | `allowed-tools` uses non-standard tool names not in the agentskills spec's approved list |
| AS005 | info | no | `compatibility` field is missing (optional but recommended for cross-agent portability) |
| AS006 | info | no | `metadata` field is missing (optional; for extended skill metadata) |

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
| PD001 | warning | no | Large skill (approaching SK006) has no `references/` directory; consider adding one |
| PD002 | warning | no | `references/` directory exists but is not linked from SKILL.md |
| PD003 | info | no | Files in `references/` are never referenced in SKILL.md |

---

## PL — Plugin Manifest Rules

Validate `plugin.json` structure.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| PL001 | error | no | `plugin.json` is missing or not valid JSON |
| PL002 | error | no | `name` field is missing from `plugin.json` |
| PL003 | error | no | `agents` field is a directory string instead of an array of file paths |
| PL004 | warning | no | A path in `plugin.json` uses `../` traversal (unsupported after plugin caching) |
| PL005 | warning | no | A path in `plugin.json` does not start with `./` |

---

## PR — Plugin Registration Rules

Validate that plugin components declared in `plugin.json` actually exist.

| Rule | Severity | Auto-fix | Description |
|------|----------|----------|-------------|
| PR001 | error | no | A skill path in `plugin.json` points to a directory that does not exist |
| PR002 | error | no | A skill directory exists but contains no `SKILL.md` file |
| PR003 | error | no | An agent file listed in `plugin.json` does not exist |
| PR004 | warning | no | A `commands` path in `plugin.json` does not exist |
| PR005 | info | no | `plugin.json` `skills` field is omitted; skills will still be auto-discovered from `skills/` |

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
| SL001 | warning | **yes** | Symlink target points outside the plugin directory (will break after plugin caching) |

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

Run `skilllint --fix <path>` to automatically fix:

- **FM004** — multiline block scalar in description
- **FM007** — allowed-tools as YAML array
- **FM008** — other comma-separated fields as YAML array
- **FM009** — unquoted colon in string field
- **FM010 / AS002** — name/directory mismatch
- **SK001** — skill name case/format
- **SK002** — skill name too long (truncated)
- **SK003** — missing description (adds placeholder)
- **SL001** — symlink outside plugin directory

All other rules require manual fixes.
