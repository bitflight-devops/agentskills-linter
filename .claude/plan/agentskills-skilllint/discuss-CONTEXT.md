# Plugin Discussion: agentskills-skilllint
Date: 2026-03-13

## Scope Decisions
- Skill takes arguments: YES — rule IDs or paths can be passed as arguments
- Primary purpose: Guide Claude agents through using the skilllint CLI to lint Claude Code plugins/skills/agents
- Secondary purposes: Explain how to fix specific rule violations, check for new versions, install the tool

## UX Preferences
- Invocation: user-invoked (slash command `/skilllint`) AND model-invoked (when linting topics come up)
- Verbosity: balanced — show commands, explain what they do, give examples
- Argument support: YES — `skilllint <rule-id>` should explain a specific rule; no args = full guide

## Technical Choices
- Component: 1 skill with argument support (no agents or hooks needed)
- Installation section covers: uv, pipx, pip
- Version checking: cover `uv tool upgrade skilllint`, `pipx upgrade skilllint`, `pip install --upgrade skilllint`
- The `skilllint rule <rule-id>` pattern: document how to look up rule explanations in the CLI
- Fix workflow: scan → identify rule IDs → `skilllint rule <id>` for explanation → `skilllint check --fix` for auto-fixable issues
- Rule categories to cover: FM-series (frontmatter), SK-series (skill structure/tokens), AS-series (agentskills standard)
- Progressive disclosure: inline rule reference in the skill; separate references/ file for full rule catalog
- Plugin structure: single skill, no agents, no hooks
- Plugin location: plugins/agentskills-skilllint/

## User Requirements (from invocation)
- Skill takes arguments
- Guide through skilllint CLI usage
- Show how to address linting issues using `skilllint rule <rule id>`
- Show how to check for new versions
- Show usage with uv, pipx, pip
