# skilllint

[![PyPI version](https://img.shields.io/pypi/v/skilllint.svg)](https://pypi.org/project/skilllint/)
[![Python versions](https://img.shields.io/pypi/pyversions/skilllint.svg)](https://pypi.org/project/skilllint/)
[![License](https://img.shields.io/pypi/l/skilllint.svg)](https://github.com/bitflight-devops/skilllint/blob/main/LICENSE)
[![CI](https://github.com/bitflight-devops/skilllint/actions/workflows/test.yml/badge.svg)](https://github.com/bitflight-devops/skilllint/actions/workflows/test.yml)

Static analysis linter for AI agent plugins, skills, and agents — for Claude Code, Cursor, Codex, and any [agentskills.io](https://agentskills.io)-compatible platform.

---

## What it does

`skilllint` validates the structure and content of AI agent files: plugins, skills, agents, and commands. It catches broken references, missing frontmatter, oversized skills, invalid hook configurations, and more — before they cause silent failures at runtime.

```
$ skilllint check plugins/my-plugin

plugins/my-plugin/skills/my-skill/SKILL.md
  SK006  Token count 14823 exceeds recommended limit of 8192

plugins/my-plugin/agents/my-agent.md
  NR001  Namespace reference 'other-plugin:some-skill' — plugin directory not found

2 errors in 2 files
```

---

## Installation

```bash
pip install skilllint
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add skilllint          # add to a project
uv tool install skilllint # install as a global tool
```

**Requires Python 3.11–3.14.**

---

## Quick start

```bash
# Validate a plugin directory
skilllint check plugins/my-plugin

# Validate a single skill file
skilllint check plugins/my-plugin/skills/my-skill/SKILL.md

# Validate everything and show a summary
skilllint check --show-summary plugins/

# Auto-fix issues where possible
skilllint check --fix plugins/my-plugin

# Count tokens in any markdown file
skilllint check --tokens-only .claude/CLAUDE.md
```

Exit codes: `0` = all checks passed · `1` = validation errors · `2` = usage error

---

## Pre-commit hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/bitflight-devops/skilllint
    rev: v1.0.0
    hooks:
      - id: skilllint
```

---

## Platform support

`skilllint` ships with adapters for three platforms and supports third-party adapters via Python entry points:

| Platform | Adapter ID | Bundled |
|---|---|---|
| [Claude Code](https://claude.ai/code) | `claude-code` | ✓ |
| [Cursor](https://cursor.sh) | `cursor` | ✓ |
| [OpenAI Codex](https://platform.openai.com/docs/codex) | `codex` | ✓ |
| OpenCode, Gemini, and others | — | via entry points |

Restrict validation to one platform:

```bash
skilllint check --platform claude-code plugins/my-plugin
```

---

## What gets validated

| Code | Category | Description |
|---|---|---|
| FM001–FM010 | Frontmatter | Required fields, valid values, schema compliance |
| SK001–SK009 | Skill | Description quality, token limits, complexity, internal links |
| AS001–AS006 | AgentSkills | Cross-platform open standard compliance |
| LK001–LK002 | Links | Markdown link validity and broken reference detection |
| PD001–PD003 | Progressive disclosure | Directory structure for references/, examples/, scripts/ |
| PL001–PL005 | Plugin | Structure, manifest correctness, subprocess safety |
| HK001–HK005 | Hook | Script existence, configuration validity |
| NR001–NR002 | Namespace refs | Cross-plugin skill/agent/command references |
| SL001 | Symlinks | Symlink hygiene within plugin directory |
| TC001 | Token count | Token count reporting and threshold enforcement |

---

## CLI reference

```
Usage: skilllint [OPTIONS] COMMAND [ARGS]...

Commands:
  check   Validate Claude Code plugins, skills, agents, and commands.
  rule    Show documentation for a validation rule.
  rules   List all available validation rules.

Options:
  --help  Show this message and exit.
```

### check

```
Usage: skilllint check [OPTIONS] [PATHS]...

Arguments:
  paths              Paths to validate

Options:
  --check            Validate only, don't auto-fix
  --fix              Auto-fix issues where possible
  --verbose, -v      Show detailed output
  --no-color         Disable color
  --tokens-only      Output token count only
  --show-progress    Show per-file status
  --show-summary     Show summary panel
  --filter TEXT      Glob pattern to match files within a directory
  --filter-type TEXT Filter type (skills | agents | commands)
  --platform TEXT    Platform adapter
  --help             Show this message and exit
```

### rules

```
Usage: skilllint rules [OPTIONS]

Options:
  --platform, -p TEXT  Filter rules by platform
  --category, -c TEXT  Filter rules by category
  --severity, -s TEXT  Filter rules by severity (error, warning, info)
  --help               Show this message and exit
```

### rule

```
Usage: skilllint rule [OPTIONS] RULE_ID

Arguments:
  rule_id  Rule identifier (e.g., "SK001", "FM002", "AS001")  [required]

Options:
  --help   Show this message and exit
```

All four command names are aliases for the same tool:

```bash
skilllint   # primary
agentlint   # alias
pluginlint  # alias
skillint    # alias
```

---

## Third-party adapters

Register a custom platform adapter via Python entry points in your `pyproject.toml`:

```toml
[project.entry-points."skilllint.adapters"]
my-platform = "my_package.adapter:MyPlatformAdapter"
```

Your adapter must implement the `AdapterProtocol` interface from `skilllint.adapters.protocol`.

---

## Links

- [GitHub repository](https://github.com/bitflight-devops/skilllint)
- [Issue tracker](https://github.com/bitflight-devops/skilllint/issues)
- [PyPI](https://pypi.org/project/skilllint/)
- [agentskills.io](https://agentskills.io)

---

## License

MIT
