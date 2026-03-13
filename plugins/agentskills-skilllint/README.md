# agentskills-skilllint

A Claude Code plugin providing a `/skilllint` skill that guides AI agents through using the `skilllint` CLI to validate, fix, and understand linting violations in Claude Code plugins, skills, agents, and commands.

## What It Does

The skill teaches Claude how to:

- **Install** `skilllint` via `uv`, `pipx`, or `pip`
- **Run** validation scans on plugins, skills, agents, and commands
- **Read** and interpret violation output (FM, SK, AS, PL, HK, LK, PD rule IDs)
- **Fix** auto-fixable violations with `skilllint --fix`
- **Understand** any rule ID by consulting the built-in rule catalog
- **Check for updates** and upgrade to the latest version

## Installation

Install this plugin from the repository:

```bash
claude plugin install agentskills-skilllint@agentskills-linter
```

Or load it for a single session:

```bash
claude --plugin-dir ./plugins/agentskills-skilllint
```

## Usage

### Invoke directly

```
/skilllint
```

Runs the full workflow guide: installation, scanning, reading output, fixing issues, checking versions.

### With a rule ID

```
/skilllint FM004
```

Explains what rule FM004 means, what causes it, and how to fix it.

### With a path

```
/skilllint ./plugins/my-plugin
```

Runs `skilllint` against the specified path and interprets the output.

### Model-invoked

Claude will automatically load this skill when you ask about linting plugins, fixing FM/SK/AS violations, or validating Claude Code skills.

## Skills

| Skill | Description |
|-------|-------------|
| `skilllint` | Full skilllint guide with argument routing, install instructions, workflow, and rule lookup |

## Rule Catalog

The skill includes a [full rule catalog](./skills/skilllint/references/rule-catalog.md) covering all rule series:

| Series | Domain |
|--------|--------|
| FM001–FM010 | YAML frontmatter validity |
| SK001–SK009 | Skill name, description, and token budget |
| AS001–AS006 | AgentSkills open standard cross-platform compliance |
| LK001–LK002 | Internal markdown links |
| PD001–PD003 | Progressive disclosure directory structure |
| PL001–PL005 | Plugin manifest (`plugin.json`) |
| PR001–PR005 | Plugin component registration |
| HK001–HK005 | hooks.json configuration |
| NR001–NR002 | Namespace references |
| SL001 | Symlink hygiene |
| TC001 | Token count reporting |

## skilllint Installation Reference

```bash
# uv (recommended)
uv tool install skilllint
uv tool upgrade skilllint

# pipx
pipx install skilllint
pipx upgrade skilllint

# pip
pip install skilllint
pip install --upgrade skilllint

# Check version
skilllint --version
```

## License

MIT
