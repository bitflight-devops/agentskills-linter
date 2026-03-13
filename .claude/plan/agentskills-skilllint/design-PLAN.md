# Design Plan: agentskills-skilllint
Date: 2026-03-13

## Plugin Goal
A single-skill Claude Code plugin (`agentskills:skilllint`) that guides AI agents
through using the `skilllint` CLI to validate, fix, and understand linting
violations in Claude Code plugins, skills, agents, and commands.

## Architecture Decisions
- **No `context: fork`** — skill runs inline, needs conversation history and Bash calls
- **No `allowed-tools`** — inherits parent tools (Bash needed to run CLI commands)
- **No `disable-model-invocation`** — both user (/skilllint) and model can invoke
- **`argument-hint: "[rule-id | path]"`** — skill branches on $ARGUMENTS
- **`references/rule-catalog.md`** — progressive disclosure for 25+ rules (avoids SK006)
- **`skilllint rule <id>` does NOT exist** — use `--verbose` + inline catalog instead
- **Dynamic context injection** — only for version availability check at activation

## Files to Create

<task id="1" name="Create plugin.json">
  <file>plugins/agentskills-skilllint/.claude-plugin/plugin.json</file>
  <description>Plugin manifest with name, version, description, author, keywords</description>
  <verify>test -f plugins/agentskills-skilllint/.claude-plugin/plugin.json && python3 -c "import json; json.load(open('plugins/agentskills-skilllint/.claude-plugin/plugin.json'))"</verify>
  <done>File exists with valid JSON containing name="agentskills-skilllint"</done>
</task>

<task id="2" name="Create SKILL.md">
  <file>plugins/agentskills-skilllint/skills/skilllint/SKILL.md</file>
  <description>Main skill file with argument routing, install guide, workflow, version checking</description>
  <verify>test -f plugins/agentskills-skilllint/skills/skilllint/SKILL.md</verify>
  <done>SKILL.md exists with valid YAML frontmatter (name, description, argument-hint) and workflow content</done>
</task>

<task id="3" name="Create rule catalog">
  <file>plugins/agentskills-skilllint/skills/skilllint/references/rule-catalog.md</file>
  <description>Full rule catalog: FM, SK, AS, LK, PD, PL, PR, HK, NR, SL, TC series with severity and auto-fix flags</description>
  <verify>test -f plugins/agentskills-skilllint/skills/skilllint/references/rule-catalog.md</verify>
  <done>File exists with all rule series documented</done>
</task>
