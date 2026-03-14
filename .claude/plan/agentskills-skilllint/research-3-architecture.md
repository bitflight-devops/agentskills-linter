# Research 3: Architecture Patterns for agentskills-skilllint Plugin

## 1. Directory Layout

Based on the plugin-creator plugin structure and Claude Code plugin conventions:

```
plugins/agentskills-skilllint/
├── .claude-plugin/
│   └── plugin.json              # Required: plugin manifest
├── skills/
│   └── skilllint/
│       ├── SKILL.md             # Primary skill: guides agents through skilllint CLI
│       └── references/
│           └── rule-catalog.md  # Complete rule ID catalog (FM/SK/LN/ST/AG/PJ series)
├── scripts/                     # Optional: hook scripts if needed later
└── LICENSE
```

Rationale:
- Single skill (`skilllint`) keeps things focused. The plugin wraps one CLI tool.
- `references/rule-catalog.md` holds the full error code explanations so the SKILL.md body stays lean (progressive disclosure).
- No `agents/` directory needed — this is a skill-only plugin.
- No `commands/` directory — skills supersede commands in the unified system.

## 2. plugin.json Fields

```json
{
  "name": "agentskills-skilllint",
  "version": "0.1.0",
  "description": "Guide AI agents through using the skilllint CLI to validate, lint, and auto-fix Claude Code plugins, skills, agents, and commands. Use when checking plugin quality, resolving frontmatter violations, or understanding linting rules.",
  "author": {
    "name": "Jamie Nelson",
    "url": "https://github.com/bitflight-devops"
  },
  "homepage": "https://github.com/bitflight-devops/skilllint",
  "repository": "https://github.com/bitflight-devops/skilllint",
  "license": "MIT",
  "keywords": [
    "skilllint",
    "linter",
    "validation",
    "claude-code",
    "plugin",
    "skill",
    "agent",
    "frontmatter"
  ]
}
```

Required fields per plugin schema (source: `claude-plugins-reference-2026`):
- `name` (string, kebab-case) — REQUIRED, only strictly required field
- `version` (string, semver) — metadata, strongly recommended
- `description` (string) — metadata, strongly recommended for discovery

Optional metadata used above: `author`, `homepage`, `repository`, `license`, `keywords`.

Component path fields NOT needed:
- `skills` — omitted because `skills/` at plugin root is auto-discovered
- `agents` — no agents in this plugin
- `commands` — no legacy commands
- `hooks` — no hooks initially
- `mcpServers` — not applicable
- `lspServers` — not applicable

## 3. SKILL.md Structure

### Frontmatter

```yaml
---
name: skilllint
description: Run the skilllint CLI to validate, lint, and auto-fix Claude Code plugins, skills, agents, and commands. Use when checking plugin quality, resolving frontmatter violations (FM001-FM010), skill naming issues (SK001-SK007), or understanding what a lint error means. Pass a path or rule ID as argument.
argument-hint: <path-or-rule-id>
allowed-tools: Read, Grep, Glob, Bash(skilllint:*, uv run skilllint:*)
user-invocable: true
---
```

Field choices explained:

| Field | Value | Rationale |
|-------|-------|-----------|
| `name` | `skilllint` | Matches directory name; required per agentskills.io spec |
| `description` | (see above) | Includes both what it does AND trigger keywords (frontmatter, violations, FM/SK codes). Single-line, no multiline YAML indicators (per known indexer bug). Under 1024 chars. |
| `argument-hint` | `<path-or-rule-id>` | Indicates the skill accepts either a file/dir path to lint OR a rule ID to explain |
| `allowed-tools` | `Read, Grep, Glob, Bash(skilllint:*, uv run skilllint:*)` | Scoped Bash access to only skilllint commands. Read/Grep/Glob for file inspection. |
| `user-invocable` | `true` (default) | Users should be able to invoke `/skilllint path/to/plugin` directly |

Fields deliberately omitted:
- `model` — inherit from parent; no need for specific model
- `context` — NOT forked; skill needs conversation context to understand what the user wants linted
- `agent` — not applicable without `context: fork`
- `disable-model-invocation` — leave false; Claude should auto-invoke when user mentions linting/validation
- `hooks` — not needed initially; could add PostToolUse lint hook later

### Body Structure

The SKILL.md body should follow a workflow-guidance pattern (similar to `plugin-creator:lint`):

```markdown
# skilllint

<target>$ARGUMENTS</target>

## Workflow

### 1. Determine intent from arguments

- If `<target/>` is a rule ID (matches pattern `FM\d{3}`, `SK\d{3}`, etc.): read [references/rule-catalog.md](./references/rule-catalog.md) and explain that rule.
- If `<target/>` is a path: proceed to validation.
- If `<target/>` is empty: ask what to lint, or scan current directory.

### 2. Run validation

```bash
skilllint <target/> --show-summary --show-progress
```

If not installed or command fails, try:
```bash
uv run skilllint <target/> --show-summary --show-progress
```

### 3. Interpret results

For each violation reported, read its explanation from [references/rule-catalog.md](./references/rule-catalog.md).

### 4. Fix (if requested)

```bash
skilllint check --fix <target/>
```

Auto-fixable rules: FM004, FM007, FM008, FM009. For non-auto-fixable rules, provide manual fix guidance from the rule catalog.

## Installation

skilllint is available via: `uv tool install skilllint`, `pipx install skilllint`, or `pip install skilllint`.

## Reference Files

- [references/rule-catalog.md](./references/rule-catalog.md) — Complete rule ID catalog with explanations, examples, and fix guidance
```

Key design decisions:
- Uses `$ARGUMENTS` substitution (same pattern as `plugin-creator:lint`)
- Dynamic context injection (`!` backtick) is NOT used here because skilllint output changes per invocation — the agent runs it via Bash instead.
- Progressive disclosure: rule catalog lives in references/, loaded only when agent needs to explain a specific rule.

## 4. References: Rule Catalog

Yes, a `references/rule-catalog.md` is strongly recommended. Rationale:

1. **Token efficiency**: The full rule catalog from the plugin-creator's ERROR_CODES.md is ~780 lines. Putting this in SKILL.md would blow past the SK006 warning threshold (4000 tokens). In `references/`, it loads on demand.

2. **Content**: The catalog should contain all rule series with their:
   - Rule ID and name
   - Severity (ERROR/WARNING/INFO)
   - Whether auto-fixable
   - What triggers it
   - Example of violation and fix
   - For FM-series: exact YAML before/after

3. **Source**: Generate from skilllint's own internal rule definitions rather than copying from plugin-creator's ERROR_CODES.md. This keeps it in sync with the actual tool version.

4. **Size concern**: If the catalog exceeds ~10k words, add grep search patterns in SKILL.md so the agent can find specific rules without loading the full file:
   ```markdown
   For specific rule details, grep `references/rule-catalog.md` for the rule ID (e.g., `FM004`).
   ```

## 5. Marketplace JSON

A `marketplace.json` is NOT needed at this stage. Reasons:

- `marketplace.json` goes in `.claude-plugin/marketplace.json` and is for repositories that host MULTIPLE plugins for distribution as a catalog.
- This plugin lives inside the skilllint repo alongside the tool it wraps.
- For initial distribution, users install via `--plugin-dir` or by adding the repo as a marketplace source.
- A marketplace.json becomes relevant when:
  - The repo hosts multiple plugins (currently just one)
  - There is a need for version pinning via `ref`/`sha` fields
  - Enterprise teams need managed marketplace restrictions

If a marketplace is desired later, the minimal structure would be:

```json
{
  "name": "skilllint",
  "owner": {
    "name": "Jamie Nelson",
    "email": "jamie@bitflight.io"
  },
  "plugins": [
    {
      "name": "agentskills-skilllint",
      "source": "./plugins/agentskills-skilllint",
      "description": "Guide agents through skilllint CLI validation",
      "version": "0.1.0"
    }
  ]
}
```

This would live at the repo root, not inside the plugin directory.

## 6. Comparison with plugin-creator:lint

The `plugin-creator:lint` skill is the closest architectural precedent. Key differences:

| Aspect | plugin-creator:lint | agentskills-skilllint:skilllint |
|--------|--------------------|---------------------------------|
| Tool invoked | `plugin_validator.py` (Python script) | `skilllint` (installed CLI binary) |
| Dynamic injection | Uses `!` backtick to run validator at load time | Does NOT use dynamic injection; agent runs CLI via Bash |
| Error codes ref | `@${CLAUDE_PLUGIN_ROOT}/references/ERROR_CODES.md` (loaded via `@` syntax) | `references/rule-catalog.md` (agent reads on demand) |
| Arguments | Single path only | Path OR rule ID (dual-mode) |
| Body size | 3 lines (minimal) | ~40-60 lines (workflow guidance) |
| Fix support | Not guided | Explicit `--fix` workflow with auto-fixable rule list |

The plugin-creator:lint skill is extremely minimal (3 lines) because it relies on dynamic injection to run the validator and dump results. Our skill is more structured because:
1. skilllint is a standalone CLI, not a script in the plugin
2. We want to guide through the full scan-interpret-fix workflow
3. We support dual-mode (path linting vs. rule explanation)

## 7. Version Synchronization

The plugin version in `plugin.json` should track the skilllint package version from `pyproject.toml`. Since skilllint uses `hatch-vcs` (git tag-based versioning), the plugin version should be updated when skilllint releases change the rule set or CLI interface.

Recommendation: Start at `0.1.0` for the plugin and bump independently of skilllint's version, since the plugin content (SKILL.md prose, rule catalog) can change without the tool changing and vice versa.

## 8. Open Questions (from mission.json backlog)

These were captured in the existing mission.json and remain relevant:

1. **Should the skill guide through creating new plugins from scratch?** — Recommendation: No. That is plugin-creator's domain. This skill focuses on validation/linting of existing artifacts.

2. **Should it link to agentskills.io for AS-series rules?** — Recommendation: Yes, but only as a reference link in rule-catalog.md, not as a dependency.

3. **Should version checking be a separate argument path?** — Recommendation: No separate path. Include `skilllint --version` as a diagnostic step in the troubleshooting section of SKILL.md.
