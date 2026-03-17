# Feature: Context-Aware Scan Discovery

## Problem Description

The scanner (`scan_runtime.py`) discovers validatable files using flat glob patterns (`**/agents/*.md`, `**/skills/*/SKILL.md`, etc.) without first identifying what kind of root directory it is scanning. This causes **false positives** when the glob patterns match files that are not actually validatable in their context.

### Concrete example

Running `skilllint check` against the `claude-plugins-official` repo flags files inside `skills/skill-creator/agents/` with FM003 (missing frontmatter). These are **skill-internal reference files** — markdown files that a skill uses as templates or documentation — not plugin-level agents. The `**/agents/*.md` glob matches them because it recurses into skill subdirectories.

### Root cause

The scanner has no concept of **scan context**. It treats every directory the same way: glob for patterns, validate whatever matches. But the correct set of validatable files depends on what kind of root the scanner is looking at:

- A **plugin** directory has specific conventions about where agents, commands, and skills live — and skill-internal files should never be treated as plugin agents.
- A **provider** directory (`.claude/`, `.cursor/`, `.gemini/`) has its own conventions about agent location.
- A **bare directory** (user points the tool at an arbitrary path) needs to detect which context applies before discovering files.

Without this detection step, the scanner cannot distinguish between a plugin agent at `agents/my-agent.md` and a skill-internal reference file at `skills/my-skill/agents/template.md`.

## Desired Outcomes

### 1. Scan context identification before file discovery

Before discovering files, the scanner must identify the scan context of the target directory. The context determines which discovery rules apply.

### 2. Plugin context: respect plugin structure

When scanning a plugin (directory containing `.claude-plugin/plugin.json`):

- **Manifest-driven discovery**: If `plugin.json` declares explicit paths (e.g., `agents`, `commands`, `skills` arrays or path fields), use exactly those paths. No globbing beyond what the manifest specifies.
- **Convention-driven discovery**: If `plugin.json` does not declare explicit paths, auto-discover using the same conventions Claude Code uses: `agents/`, `commands/`, `skills/` at the **plugin root only** — never recursing into `skills/*/` subdirectories for agent or command discovery.
- **Skill-internal files excluded**: Files inside `skills/<skill-name>/agents/` or `skills/<skill-name>/commands/` are never treated as plugin-level agents or commands. They belong to the skill and are validated (if at all) under skill-internal rules.

### 3. Provider context: respect provider conventions

When scanning a provider directory (`.claude/`, `.cursor/`, `.gemini/`, etc.):

- Agents come from `.<provider>/agents/**/*` only.
- No other files in that directory tree are treated as agents.
- Provider adapters already define `path_patterns()` — the scan context should leverage these.

### 4. Bare directory context: detect-then-scan

When the user points `skilllint` at an arbitrary directory:

- First check: does it contain `.claude-plugin/plugin.json`? If yes, apply plugin context rules.
- Second check: is it (or does it contain) a provider directory? If yes, apply provider context rules.
- Fallback: current behavior (glob-based discovery), but with the understanding that this is the least precise mode.

### 5. PA001 and other plugin-aware rules benefit automatically

Rules like PA001 (`check_pa001`) already scan `plugin_dir / "agents"` correctly (top-level only). But they are currently invoked on paths that shouldn't have been discovered in the first place. Context-aware discovery means these rules receive only correctly-scoped paths, reducing both false positives and wasted validation work.

### 6. No behavioral change for correctly-structured inputs

Users who already pass well-scoped paths (a single plugin directory, a single agent file) should see no change in behavior. The feature affects only the discovery phase when directories are expanded.

## Use Scenarios

### Scenario A: Scanning a plugin repository

```
skilllint check /path/to/my-plugin/
```

The directory contains `.claude-plugin/plugin.json`. The scanner enters plugin context. It discovers agents from `agents/*.md` at the plugin root, skills from `skills/*/SKILL.md`, and commands from `commands/*.md` — but does NOT recurse into `skills/*/agents/` for agent discovery.

**Current behavior**: `**/agents/*.md` matches `skills/skill-creator/agents/researcher.md` and flags it with FM003.

**Desired behavior**: `skills/skill-creator/agents/researcher.md` is not discovered as a validatable agent. No false positive.

### Scenario B: Scanning a provider directory

```
skilllint check /path/to/project/.claude/
```

The scanner enters provider context. Agents are discovered from `.claude/agents/**/*` only.

### Scenario C: Scanning a repository containing multiple plugins

```
skilllint check /path/to/monorepo/
```

The scanner finds multiple `.claude-plugin/plugin.json` files. Each plugin subtree gets its own plugin context. Files outside any plugin subtree use bare-directory rules.

### Scenario D: Scanning with `--filter-type`

```
skilllint check /path/to/my-plugin/ --filter-type agents
```

Current `FILTER_TYPE_MAP` maps `"agents"` to `**/agents/*.md`. In plugin context, this should be scoped to plugin-root agents only, not skill-internal agents.

### Scenario E: Manifest-driven plugin

```json
// .claude-plugin/plugin.json
{
  "agents": ["agents/main-agent.md", "agents/helper.md"],
  "skills": ["skills/code-review"]
}
```

The scanner uses exactly these paths. No globbing. If a file exists in `agents/` but is not listed in the manifest, it is not validated as a plugin agent.

## Ambiguities and Questions for Resolution

### Q1: What does "manifest-driven" mean concretely?

Does `plugin.json` currently have fields that declare explicit agent/command/skill paths? If not, is this a future schema addition, or should the scanner only use convention-driven discovery for now? Need to inspect the actual `plugin.json` schema to determine what fields are available.

### Q2: How should overlapping contexts be handled?

A provider directory (`.claude/`) might exist inside a plugin directory. Which context wins? Options:

- **Plugin context takes precedence** — the `.claude/` directory inside a plugin is part of the plugin, not a standalone provider directory.
- **Most specific context wins** — if the user points directly at `.claude/agents/`, use provider context; if they point at the plugin root, use plugin context.

### Q3: Should skill-internal files be validated at all?

The feature excludes `skills/*/agents/*.md` from plugin-agent discovery. But should these files be validated under a different ruleset (e.g., skill-internal frontmatter rules)? Or are they completely outside skilllint's scope?

### Q4: What about nested skills?

Can skills contain sub-skills (`skills/parent-skill/skills/child-skill/`)? If so, the recursion boundary needs to be clearly defined.

### Q5: How should `--filter` interact with scan context?

If a user passes `--filter "**/agents/*.md"` explicitly, should the scan context still restrict discovery? Options:

- **Explicit filter overrides context** — user knows what they want, respect it.
- **Context always applies** — even explicit filters are scoped by context rules.

The first option is more consistent with CLI tool conventions (explicit flags override defaults).

### Q6: Where does `_discover_validatable_paths` live after this change?

Currently in `scan_runtime.py`. The context detection logic could live there too, or it could be a separate module. The discovery function's signature and responsibilities will change — it needs to accept or determine the scan context.

### Q7: How do adapters relate to scan context?

Adapters define `path_patterns()` for provider-specific file discovery. Should scan context detection delegate to adapters for provider contexts, or should the scan context module be independent and adapters remain validation-only?
