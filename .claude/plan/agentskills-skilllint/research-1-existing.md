# Research: Existing Plugin/Skill Structures in agentskills-linter

Date: 2026-03-13

## 1. Plugin/Skill Directories That Exist in the Repo

### Project-Level Skills (`.claude/skills/`)

One skill exists:

- **`.claude/skills/mmap-processor/SKILL.md`** -- Enforces memory-mapped file I/O for large file processing in Python. Standard skill format with frontmatter (`name`, `description`) and markdown body. No references/ subdirectory. Approximately 50 lines.

### Project-Level Agents (`.claude/agents/`)

13 agents exist, all at the project root `.claude/agents/` level:

- `schema-drift-auditor.md` -- Reads `.drift-pending.json`, cross-references vendor doc changes against schema `x-audited.source` fields. This is the closest thing to a "linting/validation" agent in the repo. Uses frontmatter fields: `name`, `description`, `tools`, `color`.
- 12 `gsd-*` agents -- Part of the "Get Shit Done" workflow system (planner, executor, verifier, debugger, etc.)

### Project-Level Commands (`.claude/commands/`)

- `commands/gsd/` -- 30+ GSD workflow commands (add-phase, execute-phase, verify-work, etc.)
- No skilllint-related commands exist.

### Vendor Plugins (`.claude/vendor/claude_code/plugins/`)

13 vendor plugins exist as reference examples. These are NOT project plugins but local clones of official Anthropic plugin examples. Key patterns observed:

| Plugin | Components | Pattern |
|--------|-----------|---------|
| `code-review` | commands/ only | Minimal plugin.json (name, description, version, author) |
| `hookify` | commands/ + skills/ + agents/ + hooks/ + core/ | Full-featured plugin with Python hook handlers |
| `plugin-dev` | commands/ + skills/ (7 skills) + agents/ | Multi-skill plugin for plugin development |
| `feature-dev` | commands/ + agents/ (3 agents) | Agent-heavy plugin |
| `commit-commands` | commands/ only | Simple command-only plugin |
| `claude-opus-4-5-migration` | skills/ with references/ | Skill with reference documents |
| `explanatory-output-style` | hooks/ only | Hook-only plugin |

### Vendor Skills from Other Platforms (`.claude/vendor/`)

The repo contains vendor documentation clones for multiple platforms (gemini_cli, codex, kilocode, kimi, opencode) used for schema auditing. These contain their own skills but are reference material, not project capabilities.

### External Installed Plugins (`/root/.claude/plugins/cache/`)

Two plugin sets are installed at the user level:

- `jamie-bitflight-skills/plugin-creator/8.5.1/` -- The plugin-creator plugin (provides skills like `claude-skills-overview-2026`, `claude-plugins-reference-2026`, `hooks-guide`, etc.)
- `jamie-bitflight-skills/python3-development/4.0.2/` -- Python development skills (python3-development, ty, hatchling, pre-commit, etc.)

No skilllint-specific plugin exists in any installed plugin cache.

## 2. Existing Skills About skilllint, Linting, or Validation

**None found.** Specifically:

- No skill in `.claude/skills/` mentions skilllint, linting, or validation
- No command in `.claude/commands/` relates to skilllint
- No installed plugin in `/root/.claude/plugins/cache/` references skilllint or agentskills-linter
- The `schema-drift-auditor` agent is related (it audits schema drift from vendor docs) but does not use `skilllint` -- it is a manual cross-referencing agent

The only validation-adjacent capability is `schema-drift-auditor.md`, which detects whether vendor documentation changes affect schema field definitions. This is complementary to but distinct from what a skilllint guide skill would do.

## 3. Patterns Used in Existing Plugins/Skills

### Frontmatter Pattern (from `mmap-processor` and `schema-drift-auditor`)

Project-level skills use minimal frontmatter:
```yaml
---
name: <kebab-case-name>
description: <single-line description with trigger keywords>
---
```

Agents add `tools` and `color` fields.

### Vendor Plugin Structure Pattern

The standard layout observed across all vendor plugins:
```
plugin-name/
  .claude-plugin/
    plugin.json          # name, version, description, author
  commands/              # Markdown command files
  skills/
    skill-name/
      SKILL.md           # Frontmatter + instructions
      references/        # Supporting docs (loaded on demand)
  agents/                # Subagent definitions
  hooks/                 # Hook config + handlers
  scripts/               # Executable utilities
```

### plugin.json Pattern

Minimal required fields observed in all vendor plugins:
```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "description": "Brief description",
  "author": { "name": "...", "email": "..." }
}
```

No vendor plugin uses custom path overrides (no `"skills": "./custom/"` etc.) -- they all rely on default directory conventions.

### Reference Document Pattern

Skills with supporting material use a `references/` subdirectory:
- `claude-opus-4-5-migration/skills/.../references/effort.md` and `prompt-snippets.md`
- `plugin-dev/skills/agent-development/references/` (3 files)
- `plugin-dev/skills/command-development/references/` (7 files)

References are linked from SKILL.md and loaded on demand by Claude.

## 4. Gaps to Fill

### Primary Gap: No skilllint Guide Skill

There is no skill anywhere in the project that:
- Teaches Claude how to use the `skilllint` CLI
- Explains rule IDs (FM-series, SK-series, AS-series)
- Shows the scan-identify-fix workflow
- Documents installation via uv/pipx/pip
- Covers version checking and upgrades

This is the exact gap the `agentskills-skilllint` plugin is intended to fill per `discuss-CONTEXT.md`.

### Secondary Gaps

1. **No plugin structure at `plugins/` in repo root** -- The plan in `discuss-CONTEXT.md` specifies `plugins/agentskills-skilllint/` as the target location. This directory does not exist yet and needs to be created from scratch.

2. **No existing rule catalog** -- The plan calls for a `references/` file with the full rule catalog. This content needs to be authored (or generated from `skilllint rule --list` output).

3. **No argument-driven skill examples in project** -- The `mmap-processor` skill does not use arguments. The planned skill needs `argument-hint` frontmatter and `$ARGUMENTS` substitution for rule ID lookups. Vendor plugins (e.g., `plugin-dev` skills) provide reference patterns for this.

### What Already Exists and Can Be Leveraged

- The `discuss-CONTEXT.md` plan file provides clear scope decisions
- The vendor plugin examples in `.claude/vendor/claude_code/plugins/` provide structural templates
- The `claude-skills-overview-2026` and `claude-plugins-reference-2026` skills (installed plugins) provide authoritative schema references for validation
- The `skilllint` package itself lives at `packages/skilllint/` and can be queried for rule definitions

## Summary

| Category | Status |
|----------|--------|
| Plugin directory (`plugins/agentskills-skilllint/`) | Does not exist -- needs creation |
| SKILL.md | Does not exist -- needs creation |
| plugin.json | Does not exist -- needs creation |
| Rule catalog reference | Does not exist -- needs creation |
| Structural templates | Available via vendor plugins |
| Schema references | Available via installed plugin-creator skills |
| Scope/requirements | Documented in `discuss-CONTEXT.md` |
