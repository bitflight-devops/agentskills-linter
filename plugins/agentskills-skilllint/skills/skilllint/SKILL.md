---
name: skilllint
description: 'Guide for using the skilllint CLI to validate, lint, and fix Claude Code plugins, skills, agents, and commands. Use when encountering FM, SK, AS, LK, PD, PL, HK, NR, SL, TC, PR, CU, CX rule violations, when asked to lint or validate a plugin, or when asked how to install or check the version of skilllint.'
argument-hint: '[rule-id | path]'
---

# skilllint Guide

Arguments received: `$ARGUMENTS`

## Argument Routing

- **No arguments** → Run full workflow guide below
- **Rule ID** (e.g. `AS001`, `AS005`, `FM004`) → Run `skilllint rule <ID>` for AS rules; for others look up in [rule-catalog.md](./references/rule-catalog.md)
- **A path** (e.g. `./plugins/my-plugin`) → Run `skilllint check <path>` and interpret the output

---

## Installation

Install `skilllint` once using whichever package manager is available:

```bash
# With uv (recommended — fastest, isolated tool environment)
uv tool install skilllint

# With pipx (isolated tool environment)
pipx install skilllint

# With pip (installs into current Python environment)
pip install skilllint
```

**Verify installation:**
```bash
skilllint --version
```

---

## Running skilllint

`skilllint` uses subcommands. The three commands are: `check`, `rule`, and `rules`.

### Validate a plugin, skill, or directory

```bash
# Validate a whole plugin directory
skilllint check ./plugins/my-plugin

# Validate a single skill file
skilllint check ./plugins/my-plugin/skills/my-skill/SKILL.md

# Validate with detailed per-file output
skilllint check --show-progress --show-summary ./plugins/my-plugin

# Validate and see detailed messages including explanations
skilllint check --verbose ./plugins/my-plugin
```

### Filter to specific file types

```bash
# Only validate skills
skilllint check --filter-type skills ./plugins/my-plugin

# Only validate agents
skilllint check --filter-type agents ./plugins/my-plugin

# Only validate commands
skilllint check --filter-type commands ./plugins/my-plugin

# Custom glob filter
skilllint check --filter '**/skills/*/SKILL.md' ./plugins/my-plugin
```

### Validate only (no auto-fix)

```bash
skilllint check --check ./plugins/my-plugin
```

---

## Reading skilllint Output

Each violation is reported as:

```
<FILE>:<LINE>  <SEVERITY>  <MESSAGE>  [RULE-ID]
```

Example:
```
skills/my-skill/SKILL.md:3  error  Description uses YAML multiline block scalar (>-); use a single-line string  [FM004]
skills/my-skill/SKILL.md:5  error  allowed-tools must be a comma-separated string, not a YAML array  [FM007]
skills/my-skill/SKILL.md:1  warning  SKILL.md body exceeds token threshold  [AS005]
```

Severity levels:
- **error** — must fix before the skill/plugin works correctly
- **warning** — should fix; may cause degraded behavior
- **info** — informational; no action required

**To look up any rule ID:**

```bash
# For AS001–AS006 (the rule documentation system)
skilllint rule AS001
skilllint rule AS005

# List all documented rules
skilllint rules

# Filter by severity or category
skilllint rules --severity error
skilllint rules --category skill
```

For FM, SK, LK, PD, PL, HK, NR, SL, TC, PR, CU, CX rule IDs, use [rule-catalog.md](./references/rule-catalog.md) — these are emitted by `skilllint check --verbose` but not yet in the `rule` documentation system.

---

## Auto-Fixing Issues

Many frontmatter errors can be fixed automatically:

```bash
# Auto-fix in place
skilllint check --fix ./plugins/my-plugin

# Preview what would be fixed (validate-only first, then fix)
skilllint check --check ./plugins/my-plugin
skilllint check --fix ./plugins/my-plugin
```

> **Note:** `--check` and `--fix` are mutually exclusive. Passing both flags at the same time is an error.

**Auto-fixable rules:** FM004, FM007, FM008, FM009, FM010/AS002, SK001, SK002, SK003, SL001

**Not auto-fixable:** AS005 (token size — requires manual refactoring), PD series, AS006, LK series, most PL/HK rules.

---

## Common Fix Patterns

### FM004 — YAML multiline block scalar in description

```yaml
# Wrong
description: >-
  This is a long description
  that spans multiple lines

# Correct — single-line string
description: 'This is a long description that spans multiple lines.'
```

### FM007 / FM008 — allowed-tools or other fields as YAML array

```yaml
# Wrong
allowed-tools:
  - Read
  - Bash
  - Glob

# Correct — comma-separated string
allowed-tools: 'Read, Bash, Glob'
```

### FM009 — Unquoted colon in description

```yaml
# Wrong
description: Validate files: plugins, skills, and agents

# Correct — quote the value
description: 'Validate files: plugins, skills, and agents'
```

### AS005 — Skill exceeds token limit

Move large reference content to a `references/` subdirectory and link to it:
```markdown
For the full rule catalog, see [rule-catalog.md](./references/rule-catalog.md)
```
Token thresholds are defined by `TOKEN_WARNING_THRESHOLD` (warning) and `TOKEN_ERROR_THRESHOLD` (error) in the skilllint source. Run `skilllint rules` to see current threshold values. Body text only — frontmatter is excluded from the count.

### AS002 / FM010 — Name/directory mismatch

The `name:` frontmatter field must match the directory name:
```
skills/my-skill/SKILL.md  →  name: my-skill
```

### AS004 — Unquoted colons in description

If the `description:` contains unquoted colons like `Examples: Context:`,
YAML parsing will fail. Quote the string to fix.

---

## Checking for Updates

```bash
# With uv
uv tool upgrade skilllint

# With pipx
pipx upgrade skilllint

# With pip
pip install --upgrade skilllint

# Check current version
skilllint --version
```

---

## Workflow: Scan → Identify → Explain → Fix

1. **Scan**: `skilllint check --show-summary --show-progress <path>`
2. **Identify** rule IDs in the output (e.g. `[FM004]`, `[AS005]`, `[AS002]`)
3. **Explain**: `skilllint rule <ID>` for AS rules; [rule-catalog.md](./references/rule-catalog.md) for others
4. **Fix auto-fixable**: `skilllint check --fix <path>`
5. **Fix manual issues**: Apply the patterns above based on rule ID
6. **Verify**: `skilllint check --check <path>` — should exit 0 with no errors

---

## Platform-Specific Validation

```bash
# Validate only for a specific platform
skilllint check --platform agentskills ./plugins/my-plugin

# List rules for a specific platform
skilllint rules --platform agentskills
```

---

## Token Count

```bash
# Get token count for a skill (integer only, for scripting)
skilllint check --tokens-only ./plugins/my-plugin/skills/my-skill/SKILL.md
```

AS005 fires when body token count exceeds `TOKEN_WARNING_THRESHOLD` (warning) or `TOKEN_ERROR_THRESHOLD` (error) — frontmatter excluded. Run `skilllint rules` to see current values.

---

For the full rule catalog with all rule IDs, descriptions, severity, and auto-fix flags, see [rule-catalog.md](./references/rule-catalog.md).
