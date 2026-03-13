# Research Findings: agentskills-skilllint
Date: 2026-03-13

## 1. Existing Solutions

No skilllint-specific plugin or skill exists anywhere in the project — not in `.claude/skills/`, `.claude/commands/`, or the installed plugin cache at `/root/.claude/plugins/cache/`. The only validation-adjacent capability is the `schema-drift-auditor` agent, which does cross-referencing of vendor docs against schema definitions — complementary to, but distinct from, a skilllint guide.

Structural templates are available from 13 vendor plugins in `.claude/vendor/claude_code/plugins/`. The standard layout is:

```
plugin-name/
  .claude-plugin/plugin.json
  skills/<skill-name>/SKILL.md
  skills/<skill-name>/references/  (optional, loaded on demand)
```

The `plugins/agentskills-skilllint/` target directory does not exist and must be created from scratch. No argument-driven skill exists in the project; the vendor plugin `claude-opus-4-5-migration` provides the closest reference for skills with a `references/` subdirectory.

Key pattern: `plugin.json` requires only `name`. All other fields (`version`, `description`, `author`, `keywords`) are strongly recommended metadata. Component path fields (`skills`, `agents`, etc.) are omitted when the default directory layout is used — auto-discovery handles them.

## 2. Recommended Features

**context: fork** — Do NOT use. The skill needs conversation context to understand what the user is working on (e.g., which plugin path is relevant, what error they saw). Inline context is the correct choice for a guide/reference skill.

**disable-model-invocation** — Do NOT set. Per `discuss-CONTEXT.md`, the skill must auto-activate when Claude encounters linting errors, rule violations, or plugin validation topics. Setting this would make the skill invisible to Claude unless the user explicitly types `/skilllint`.

**allowed-tools** — The research is split: research-2 recommends omitting it (inherits parent tools, avoids restriction); research-3 recommends `Read, Grep, Glob, Bash(skilllint:*, uv run skilllint:*)`. The task spec requires `allowed-tools="Read, Bash, Glob, Grep"`. This is the value to use — it explicitly grants the four needed tools without relying on parent inheritance.

**argument-hint** — Use `[rule-id|path]`. The `$ARGUMENTS` substitution enables three invocation modes: no args (full guide), rule ID (explain that rule from catalog), path (run lint on that path).

**references/ subdirectory** — Yes, one file: `references/rule-catalog.md`. The full catalog is ~780 lines and would exceed the SK006 warning threshold (4400 tokens) if inlined. Progressive disclosure: SKILL.md contains the workflow guide and a rule-series overview; the catalog is loaded on demand.

**Dynamic context injection (`!` backtick)** — Selective use: a version/install check at skill activation (`!command -v skilllint ...`) is appropriate. Do NOT use it for scan output — scan targets depend on user context and cannot be parameterized at load time.

**`skilllint rule <id>` subcommand** — Does NOT exist. The CLI is a single command with options. The skill must tell agents to look up rules in `references/rule-catalog.md`, and use `skilllint --verbose <path>` for detailed output.

## 3. Architecture Patterns

**Minimal plugin structure** (no agents, no commands, no hooks initially):

```
plugins/agentskills-skilllint/
├── .claude-plugin/
│   └── plugin.json
└── skills/
    └── skilllint/
        ├── SKILL.md
        └── references/
            └── rule-catalog.md
```

**plugin.json** — Include `name`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`. Omit path override fields (`skills`, `agents`, etc.) — auto-discovery handles them. No `agents` array is needed.

**SKILL.md frontmatter** — Single-line description (multiline YAML indicators are an FM004 violation). Include trigger keywords for auto-invocation. Use `argument-hint` for slash-command UX.

**SKILL.md body structure** — Argument routing first (`$ARGUMENTS`), then: installation, running skilllint, reading output, looking up rules (via catalog), fixing issues, version management. Keep body under 4400 tokens (SK006 threshold).

**rule-catalog.md** — One file covering all series: FM, SK, AS, LK, PD, PL, PR, HK, NR, SL, CM, TC. Each entry: rule ID, severity, what it checks, auto-fixable (yes/no). This is the authoritative lookup table the agent reads when explaining a specific violation.

**Version comparison with plugin-creator:lint** — The closest precedent. Key difference: plugin-creator:lint uses dynamic injection (`!` backtick) to run its validator at load time and dump results inline. The agentskills-skilllint skill does NOT do this — agents run `skilllint` via Bash because: (1) the scan target is unknown at load time, (2) scan output can be large, (3) dual-mode (path vs. rule ID) requires interactive routing.

## 4. Pitfalls & Requirements

**PyPI package name:** `skilllint`. Entry points: `skilllint`, `agentlint`, `pluginlint`, `skillint` (all identical).

**Version check command:** `skilllint --version` (Typer auto-generates from package metadata).

**No `rule` subcommand:** The CLI is a single command. Use `references/rule-catalog.md` for rule lookups.

**Auto-fixable rules:**
- FM004, FM007, FM008, FM009 — frontmatter normalization (`FrontmatterValidator`)
- SK001, SK002, SK003, FM010 — name format (`NameFormatValidator`)
- SL001 — symlink trailing whitespace (`SymlinkTargetValidator`)
- NOT fixable: PD001, PD002, PD003, all AS series, all HK series (except indirectly)

**Token thresholds:** SK006/AS005 warning at 4400 tokens; SK007/AS005 error at 8800 tokens. Keep SKILL.md body under 4400 tokens.

**YAML multiline bug (FM004):** Never use `>-` or `|-` in frontmatter. Description must be a single plain string on one line.

**FM009 colon trap:** If a description contains a colon followed by a space (e.g., "Use this skill: it does X"), it must be quoted in YAML.

**SK005 trigger phrase requirement:** The `description` field must include at least one of: "use when", "use this", "use on", "used when", "used by", "when ", "trigger", "activate", "load this", "load when", "invoke". Without it, Claude cannot determine when to auto-invoke the skill.

**Rule suppression mechanism:** Via `.claude-plugin/validator.json` with an `ignore` map of path prefixes to rule code arrays.

**Complete rule series inventory:**

| Series | Codes | Auto-fixable |
|--------|-------|-------------|
| FM | FM001–FM010 | FM004, FM007, FM008, FM009, FM010 |
| SK | SK001–SK009 | SK001, SK002, SK003 |
| AS | AS001–AS006 | None |
| LK | LK001–LK002 | None |
| PD | PD001–PD003 | None |
| PL | PL001–PL005 | None |
| PR | PR001–PR005 | None |
| HK | HK001–HK005 | None |
| NR | NR001–NR002 | None |
| SL | SL001 | SL001 |
| CM | CM001 | Reserved |
| TC | TC001 | N/A (info only) |

## Synthesis

**Key insights:**

1. The plugin fills a genuine gap — nothing guides agents through skilllint usage anywhere in the project. This is the primary value proposition.

2. The `skilllint rule <id>` CLI subcommand assumed in `discuss-CONTEXT.md` does not exist. The design must route rule-ID arguments to `references/rule-catalog.md` instead. This actually produces a better UX (agents can read the catalog without running a command that doesn't exist).

3. Research-2 and research-3 diverge on `allowed-tools`. The task spec resolves the ambiguity: use `allowed-tools="Read, Bash, Glob, Grep"`. This explicitly grants the four tools needed without restricting Edit/Write — but since this is an inline (non-forked) skill, the parent agent retains all its own tools regardless.

4. The dynamic version-check injection (`!command -v skilllint ...`) is a genuinely useful feature for contextual advice ("not installed" vs. "installed, version X"). Include it.

5. The SKILL.md body must stay under 4400 tokens to avoid SK006 violations — ironic for a linter guide skill to fail its own linter. The `references/` approach is essential, not optional.

6. The FM004 pitfall (multiline YAML in frontmatter) is the single most common agent mistake — the SKILL.md description field itself is a live demonstration of correct practice.

**Recommended approach:**

Build a focused three-file plugin:
- `plugin.json` — full metadata, no path overrides, no agents array
- `SKILL.md` — argument-routing header, workflow guide body (~40-60 lines), reference to catalog
- `references/rule-catalog.md` — complete rule catalog organized by series, each entry with severity, auto-fixable flag, example violation, and fix

The SKILL.md body uses `$ARGUMENTS` routing: rule ID → read catalog and explain; path → run `skilllint <path>`; empty → full guide. The version/install check runs at load time via `!` injection. The `references/rule-catalog.md` serves as both the rule-explanation backend (for rule-ID invocations) and the fix-guidance reference (for the fixing workflow).
