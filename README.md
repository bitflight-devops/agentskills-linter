# skilllint

[![PyPI version](https://img.shields.io/pypi/v/skilllint.svg)](https://pypi.org/project/skilllint/)
[![Python versions](https://img.shields.io/pypi/pyversions/skilllint.svg)](https://pypi.org/project/skilllint/)
[![License](https://img.shields.io/pypi/l/skilllint.svg)](https://github.com/bitflight-devops/agentskills-linter/blob/main/LICENSE)
[![CI](https://github.com/bitflight-devops/agentskills-linter/actions/workflows/test.yml/badge.svg)](https://github.com/bitflight-devops/agentskills-linter/actions/workflows/test.yml)

Static analysis linter for AI agent plugins, skills, and agents — for Claude Code, Cursor, Codex, and any [agentskills.io](https://agentskills.io)-compatible platform.

---

## What it does

`skilllint` validates the structure and content of AI agent files: plugins, skills, agents, and commands. It catches broken references, missing frontmatter, oversized skills, invalid hook configurations, and more — before they cause silent failures at runtime.

```
$ skilllint plugins/my-plugin

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
skilllint plugins/my-plugin

# Validate a single skill file
skilllint plugins/my-plugin/skills/my-skill/SKILL.md

# Validate everything and show a summary
skilllint --show-summary plugins/

# Auto-fix issues where possible
skilllint --fix plugins/my-plugin

# Count tokens in any markdown file
skilllint --tokens-only .claude/CLAUDE.md
```

Exit codes: `0` = all checks passed · `1` = validation errors · `2` = usage error

---

## Pre-commit hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/bitflight-devops/agentskills-linter
    rev: v0.1.0
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
skilllint --platform claude-code plugins/my-plugin
```

---

## What gets validated

| Code | Category | Description |
|---|---|---|
| FM001–FM010 | Frontmatter | Required fields, valid values, schema compliance |
| SK001–SK009 | Skill | Description quality, token limits, complexity, internal links |
| PL001–PL005 | Plugin | Structure, registration, subprocess safety |
| HK001–HK005 | Hook | Script existence, configuration validity |
| NR001–NR002 | Namespace refs | Cross-plugin skill/agent/command references |
| PR001–PR005 | Registration | Plugin manifest correctness |

---

## CLI reference

```
Usage: skilllint [OPTIONS] [PATHS]...

Options:
  --check            Validate only, don't auto-fix
  --fix              Auto-fix issues where possible
  --verbose, -v      Show detailed output including info messages
  --no-color         Disable colour output for CI
  --tokens-only      Output only the integer token count
  --show-progress    Show per-file PASSED/FAILED status
  --show-summary     Show validation summary panel at the end
  --filter TEXT      Glob pattern to match files within a directory
  --filter-type TEXT Shortcut: skills | agents | commands
  --platform TEXT    Restrict to a specific platform adapter
  --help             Show this message and exit
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

- [GitHub repository](https://github.com/bitflight-devops/agentskills-linter)
- [Issue tracker](https://github.com/bitflight-devops/agentskills-linter/issues)
- [PyPI](https://pypi.org/project/skilllint/)
- [agentskills.io](https://agentskills.io)

---

## License

MIT
