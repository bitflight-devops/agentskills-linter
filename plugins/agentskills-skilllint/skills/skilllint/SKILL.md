---
name: skilllint
description: 'Guide for using the skilllint CLI to validate, lint, and fix Claude Code plugins, skills, agents, and commands. Use when encountering FM, SK, AS, PL, HK, LK, PD rule violations, when asked to lint or validate a plugin, or when asked how to install or check the version of skilllint.'
argument-hint: '[rule-id | path]'
---

# skilllint Guide

Arguments received: `$ARGUMENTS`

## Argument Routing

- **No arguments** → Run full workflow guide below
- **Rule ID** (e.g. `FM004`, `SK006`, `AS002`) → Look up that rule in [rule-catalog.md](./references/rule-catalog.md) and explain what it means, what causes it, and how to fix it
- **A path** (e.g. `./plugins/my-plugin`) → Run `skilllint <path>` and interpret the output

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

### Validate a plugin, skill, or directory

```bash
# Validate a whole plugin directory
skilllint ./plugins/my-plugin

# Validate a single skill file
skilllint ./plugins/my-plugin/skills/my-skill/SKILL.md

# Validate with detailed per-file output
skilllint --show-progress --show-summary ./plugins/my-plugin

# Validate and see info-level messages (not just warnings/errors)
skilllint --verbose ./plugins/my-plugin
```

### Filter to specific file types

```bash
# Only validate skills
skilllint --filter-type skills ./plugins/my-plugin

# Only validate agents
skilllint --filter-type agents ./plugins/my-plugin

# Only validate commands
skilllint --filter-type commands ./plugins/my-plugin

# Custom glob filter
skilllint --filter '**/skills/*/SKILL.md' ./plugins/my-plugin
```

### Validate only (no auto-fix)

```bash
skilllint --check ./plugins/my-plugin
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
skills/my-skill/SKILL.md:1  warning  Skill is approaching token limit (3800/4000)  [SK006]
```

Severity levels:
- **error** — must fix before the skill/plugin works correctly
- **warning** — should fix; may cause degraded behavior
- **info** — informational; no action required

**To understand any rule ID**, check [rule-catalog.md](./references/rule-catalog.md) or run:
```bash
skilllint --verbose <path>
```
The `--verbose` flag includes explanatory text for each violation.

---

## Auto-Fixing Issues

Many frontmatter errors can be fixed automatically:

```bash
# Auto-fix in place
skilllint --fix ./plugins/my-plugin

# Preview what would be fixed (validate-only first, then fix)
skilllint --check ./plugins/my-plugin
skilllint --fix ./plugins/my-plugin
```

**Auto-fixable rules:** FM004, FM007, FM008, FM009, FM010/SK001–SK003, SL001

**Not auto-fixable:** SK006, SK007 (token size — requires manual refactoring), PD series, AS series, LK series, most PL/PR/HK rules.

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

### SK006 / SK007 — Skill exceeds token limit

Move large reference content to a `references/` subdirectory and link to it:
```markdown
For the full rule catalog, see [rule-catalog.md](./references/rule-catalog.md)
```

### AS002 — Name/directory mismatch

The `name:` frontmatter field must match the directory name:
```
skills/my-skill/SKILL.md  →  name: my-skill
```

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

# Check latest available on PyPI
pip index versions skilllint 2>/dev/null | head -1
# or
uv tool install skilllint --dry-run 2>&1 | grep skilllint
```

---

## Workflow: Scan → Identify → Explain → Fix

1. **Scan**: `skilllint --show-summary --show-progress <path>`
2. **Identify** rule IDs in the output (e.g. `[FM004]`, `[SK006]`)
3. **Explain**: Look up the rule ID in [rule-catalog.md](./references/rule-catalog.md)
4. **Fix auto-fixable**: `skilllint --fix <path>`
5. **Fix manual issues**: Apply the patterns above based on rule ID
6. **Verify**: `skilllint --check <path>` — should exit 0 with no errors

---

## Platform-Specific Validation

```bash
# Validate only for Claude Code rules
skilllint --platform claude-code ./plugins/my-plugin

# Validate only for Cursor rules
skilllint --platform cursor ./plugins/my-plugin

# Validate only for Codex rules
skilllint --platform codex ./plugins/my-plugin
```

---

## Token Count

```bash
# Get token count for a skill (integer only, for scripting)
skilllint --tokens-only ./plugins/my-plugin/skills/my-skill/SKILL.md
```

SK006 fires at ~3800 tokens (warning); SK007 fires at ~4000 tokens (error).

---

For the full rule catalog with all rule IDs, descriptions, severity, and auto-fix flags, see [rule-catalog.md](./references/rule-catalog.md).
