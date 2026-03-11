# skilllint

Static analysis linter for Claude Code plugins, skills, and agents.

## Installation

```bash
pip install skilllint
```

## Usage

```bash
skilllint path/to/plugin/
agentlint path/to/skill/SKILL.md
skillint path/to/plugin/plugin.json
```

## CLI entry points

All three commands are aliases for the same tool:

- `skilllint`
- `agentlint`
- `pluginlint`
- `skillint`

## Migration from PEP 723 scripts

Prior to v0.1, skilllint ran as a PEP 723 inline-dependency script:

```bash
# Old (deprecated) — no longer supported
uv run plugin_validator.py [files...]
```

With v0.1+, install the package and use the named CLI entry point:

```bash
# Install (choose one)
uv add skilllint          # add to project
uv tool install skilllint # install as global tool

# Run
skilllint [files...]      # primary entry point
agentlint [files...]      # alias
pluginlint [files...]     # alias
skillint [files...]       # alias
```

### Pre-commit hook migration

If you have a pre-commit hook referencing `plugin_validator.py`, update your
`.pre-commit-config.yaml` to use the published hook:

```yaml
repos:
  - repo: https://github.com/bitflight-devops/agentskills-linter
    rev: v0.1.0
    hooks:
      - id: skilllint
```
