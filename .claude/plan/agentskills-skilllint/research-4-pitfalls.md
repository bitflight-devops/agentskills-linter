# skilllint — Rule IDs, Pitfalls, and Reference

## PyPI Package

- **Package name:** `skilllint`
- **Install:** `pip install skilllint` / `pipx install skilllint` / `uv tool install skilllint`
- **Entry points (all identical):** `skilllint`, `agentlint`, `pluginlint`, `skillint`

## Version Check

```
skilllint --version
```

Typer auto-generates `--version` from the package metadata. There is no `skilllint rule <id>` subcommand — the CLI has a single command (`main`) registered via `app.command()(main)`. All flags are options on that single command.

## CLI Flags

```
skilllint [PATHS]...
  --check          Validate only, don't auto-fix
  --fix            Auto-fix issues where possible
  --verbose / -v   Show detailed output including info messages
  --no-color       Disable color output for CI
  --tokens-only    Output only the integer token count (programmatic use)
  --show-progress  Show per-file PASSED/FAILED status
  --show-summary   Show validation summary panel at end
  --filter GLOB    Glob pattern to match files within a directory
  --filter-type    Shortcut: skills | agents | commands
  --platform       Restrict to a specific adapter: claude-code | cursor | codex
```

`--check` and `--fix` are mutually exclusive.

## Auto-Fixable Rules

The `--fix` flag is supported. Validators that return `can_fix() -> True` and implement `fix()`:

| Validator | Rules Fixed |
|---|---|
| `FrontmatterValidator` | FM004, FM007, FM008, FM009 (and related frontmatter normalization) |
| `NameFormatValidator` | SK001 (uppercase), SK002 (underscores), SK003 (bad hyphens), FM010 |
| `SymlinkTargetValidator` | SL001 (trailing whitespace in symlink targets) |

`ProgressiveDisclosureValidator` explicitly raises `NotImplementedError` in its `fix()` — PD001/PD002/PD003 are **not** auto-fixable.

---

## All Rule IDs

### FM Series — Frontmatter (FM001–FM010)

Fired by `FrontmatterValidator` on SKILL.md, agents/*.md, and commands/*.md files.

| Code | Severity | What It Checks |
|---|---|---|
| FM001 | error | Missing required field (`name`, `description`) |
| FM002 | error | Invalid YAML syntax in frontmatter |
| FM003 | error | Frontmatter not closed with `---` |
| FM004 | error | Forbidden multiline indicator (`>-` or `\|-`) in frontmatter values |
| FM005 | error | Field type mismatch (expected string or bool, got something else) |
| FM006 | error | Invalid field value (e.g. `model` not in allowed enum) |
| FM007 | error | `allowed-tools` (or `tools`) field is a YAML array — must be a CSV string |
| FM008 | error | `skills` field is a YAML array — must be a CSV string |
| FM009 | info | Unquoted description value containing a colon (causes YAML parse ambiguity) |
| FM010 | error | `name` field does not match the required pattern (lowercase alphanumeric + hyphens) |

**FM004, FM007, FM008, FM009 are auto-fixable with `--fix`.**

### SK Series — Skill Quality (SK001–SK009)

Fired by `NameFormatValidator`, `DescriptionValidator`, and `ComplexityValidator`.

| Code | Severity | What It Checks |
|---|---|---|
| SK001 | error | `name` contains uppercase characters |
| SK002 | error | `name` contains underscores (use hyphens instead) |
| SK003 | error | `name` has leading, trailing, or consecutive hyphens |
| SK004 | error | `description` is too short (minimum 20 characters) |
| SK005 | warning | `description` missing trigger phrases (e.g. "use when", "trigger", "invoke") |
| SK006 | warning | SKILL.md body token count exceeds TOKEN_WARNING_THRESHOLD (4400 tokens) |
| SK007 | error | SKILL.md body token count exceeds TOKEN_ERROR_THRESHOLD (8800 tokens) — must split |
| SK008 | error | Skill directory name violates naming convention |
| SK009 | warning | Plugin uses manual skill selection (overrides auto-discovery) |

**SK001, SK002, SK003 are auto-fixable with `--fix`.**

### AS Series — agentskills.io Cross-Platform (AS001–AS006)

Fired by `check_skill_md()` / `run_as_series()` in `rules/as_series.py` on any SKILL.md, regardless of platform adapter. Applies to Claude Code, Cursor, and Codex adapters.

| Code | Severity | What It Checks |
|---|---|---|
| AS001 | error | `name` must be lowercase alphanumeric + hyphens, 1–64 chars, no consecutive hyphens |
| AS002 | error | `name` must equal the parent directory name |
| AS003 | error | `description` field must be present and non-empty |
| AS004 | error | `description` must not contain HTML tags (`<` or `>`) |
| AS005 | warning/error | SKILL.md body token count: warning at 4400, error at 8800 tokens |
| AS006 | info | No `eval_queries.json` (or `*eval*.json` / `*queries*.json`) found in skill directory |

**AS series rules are not auto-fixable.**

### LK Series — Internal Links (LK001–LK002)

Fired by `InternalLinkValidator` on markdown files.

| Code | Severity | What It Checks |
|---|---|---|
| LK001 | error | Broken internal link — referenced file does not exist |
| LK002 | warning | Relative link missing `./` prefix |

### PD Series — Progressive Disclosure (PD001–PD003)

Fired by `ProgressiveDisclosureValidator` on skill directories.

| Code | Severity | What It Checks |
|---|---|---|
| PD001 | warning | No `references/` directory found in skill |
| PD002 | warning | No `examples/` directory found in skill |
| PD003 | warning | No `scripts/` directory found in skill |

**Not auto-fixable.**

### PL Series — Plugin Manifest (PL001–PL005)

Fired by `ClaudeCodeAdapter.validate()` and plugin structure checks.

| Code | Severity | What It Checks |
|---|---|---|
| PL001 | error | Missing `plugin.json` file |
| PL002 | error | Invalid JSON syntax in `plugin.json` |
| PL003 | error | Missing required field (e.g. `name`) in plugin manifest |
| PL004 | error | Component path does not start with `./` |
| PL005 | error | Referenced component file does not exist |

### PR Series — Plugin Registration (PR001–PR005)

Fired by `PluginRegistrationValidator`.

| Code | Severity | What It Checks |
|---|---|---|
| PR001 | warning | Capability (skill/agent/command) exists but is not registered in `plugin.json` |
| PR002 | error | Registered capability path does not exist |
| PR003 | warning | Plugin metadata fields (`repository`, `homepage`, `author`) not populated |
| PR004 | warning | Plugin metadata `repository` URL mismatches git remote URL |
| PR005 | error | Registered command path is a skill directory (contains SKILL.md) |

### HK Series — Hooks (HK001–HK005)

Fired by `HookValidator` on `hooks.json` files.

| Code | Severity | What It Checks |
|---|---|---|
| HK001 | error | Invalid `hooks.json` structure |
| HK002 | error | Invalid event type in `hooks.json` |
| HK003 | error | Invalid hook entry structure |
| HK004 | error | Hook script referenced in `hooks.json` but file not found |
| HK005 | warning | Hook script exists but is not executable |

### NR Series — Namespace References (NR001–NR002)

Fired by `NamespaceReferenceValidator`.

| Code | Severity | What It Checks |
|---|---|---|
| NR001 | error | Namespace reference target does not exist |
| NR002 | error | Namespace reference points outside the plugin directory |

### SL Series — Symlinks (SL001)

Fired by `SymlinkTargetValidator`.

| Code | Severity | What It Checks |
|---|---|---|
| SL001 | error | Symlink target has trailing whitespace or newlines |

**Auto-fixable with `--fix`.**

### CM Series — Commands (CM001)

| Code | Severity | What It Checks |
|---|---|---|
| CM001 | reserved | Command-specific validation (reserved for future use) |

### TC Series — Token Count (TC001)

| Code | Severity | What It Checks |
|---|---|---|
| TC001 | info | Token count report (total, frontmatter, body) — informational only |

### Cursor Adapter — Platform-Specific Codes

Fired by `CursorAdapter.validate()` on `.mdc` files only. These use string codes, not the FM/SK pattern:

| Code | Severity | What It Checks |
|---|---|---|
| `cursor-mdc-missing-required` | error | Required field missing from `.mdc` frontmatter |
| `cursor-mdc-unknown-field` | error | Unknown field in `.mdc` frontmatter when `additionalProperties` is false |

---

## Adapter Scope

| Adapter | Applicable Rule Series | File Patterns |
|---|---|---|
| `claude_code` | SK, PR, HK, AS | `.claude/**/*.md`, `plugin.json`, `hooks.json`, `agents/**/*.md`, `commands/**/*.md` |
| `cursor` | AS | `**/*.mdc`, `.cursor/skills/**/*.md`, `.claude/skills/**/*.md`, `.agents/skills/**/*.md` |
| `codex` | (see adapter) | (see adapter) |

---

## Common Agent Mistakes the Linter Catches

### FM004 — Multiline block scalars in frontmatter
Agents sometimes write descriptions using YAML block scalar syntax:
```yaml
description: >-
  This skill helps you do things.
```
The `>-` (or `|-`) indicator is forbidden. Use a plain single-line string:
```yaml
description: This skill helps you do things.
```
**Auto-fixable.**

### FM007 / FM008 — YAML arrays instead of CSV strings
Agents write `allowed-tools` or `skills` as YAML lists:
```yaml
allowed-tools:
  - Bash
  - Read
```
Must be a CSV string:
```yaml
allowed-tools: Bash, Read
```
**Auto-fixable.**

### FM009 — Unquoted colons in description
```yaml
description: Use this skill: it does X
```
The `: ` after "skill" is a YAML mapping indicator. Quote the value:
```yaml
description: "Use this skill: it does X"
```
**Auto-fixable.**

### AS001 / FM010 / SK001 / SK002 — Name format violations
- Uppercase letters in `name` (SK001): `name: MySkill` → `name: my-skill`
- Underscores (SK002): `name: my_skill` → `name: my-skill`
- `name` not matching directory (AS002): directory is `git-helper` but frontmatter says `name: git_helper`

### AS002 — Name/directory mismatch
The `name` field must exactly equal the parent directory name. Creating a skill in a directory `my-skill/` but writing `name: mySKill` will fail both AS001 and AS002.

### SK004 — Description too short
A one-word or very brief description like `description: Git tool` fails (minimum 20 characters).

### SK005 — No trigger phrase in description
The description must include at least one of: `use when`, `use this`, `use on`, `used when`, `used by`, `when `, `trigger`, `activate`, `load this`, `load when`, `invoke`. Without a trigger phrase the AI cannot determine when to invoke the skill.

### SK006 / SK007 / AS005 — Token bloat
SKILL.md body over 4400 tokens triggers SK006/AS005 warning. Over 8800 tokens is SK007/AS005 error — the skill must be split into sub-skills.

### PR001 — Unregistered capabilities
Creating a skill directory without adding it to `plugin.json`'s skills array triggers PR001. Auto-discovery does not replace explicit registration.

### HK004 / HK005 — Hook script issues
Referencing a hook script path that doesn't exist (HK004) or exists but lacks execute permission (HK005). On Windows/Linux discrepancy: a script checked in without `chmod +x` will pass on Windows but fail HK005 on Linux CI.

### AS006 — No eval_queries.json
Every skill should have an `eval_queries.json` (or a file matching `*eval*.json` / `*queries*.json`) in its directory for automated quality assessment. Absence fires AS006 (info severity).

---

## Suppressing Rules

Per-plugin suppression via `.claude-plugin/validator.json`:
```json
{
  "ignore": {
    "skills/my-skill": ["SK006", "PD001"]
  }
}
```
Keys are path prefixes relative to the plugin root. All files under that prefix have the listed codes suppressed.

---

## Token Thresholds (from `token_counter.py`)

- `TOKEN_WARNING_THRESHOLD` = 4400 tokens → SK006 / AS005 warning
- `TOKEN_ERROR_THRESHOLD` = 8800 tokens → SK007 / AS005 error

Encoding: `tiktoken` `cl100k_base`. Token counting covers only the body (frontmatter excluded).
