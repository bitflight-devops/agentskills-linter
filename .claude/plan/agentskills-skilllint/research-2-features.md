# Research: Claude Code Skill Features for skilllint Guide

Date: 2026-03-13

## Summary

This document analyzes which Claude Code skill features are appropriate for a "skilllint guide" skill, based on the authoritative skill specification (claude-skills-overview-2026), the existing project context (discuss-CONTEXT.md), and the actual skilllint CLI capabilities.

---

## Question 1: Should this use `context: fork` or inline instructions?

**Recommendation: Do NOT use `context: fork`. Use inline (main context) instructions.**

### Rationale

- `context: fork` runs the skill in an isolated subagent that does NOT have access to the user's conversation history. The skilllint guide needs conversation context -- when a user says "I got an FM004 error," the skill needs to see what they were working on and what plugin path is relevant.
- The skill is primarily a knowledge/reference resource with some CLI execution. It does not perform a complex isolated task that benefits from a fresh context.
- Per the specification: "Use `context: fork` only when the skill includes explicit instructions and a clear task." A guide/reference skill provides guidelines and context-sensitive help, not a single discrete task.
- The existing `mmap-processor` skill in this project also uses inline context (no `context: fork`), which is the right pattern for instructional/knowledge skills.

### When fork WOULD be appropriate

If the skill needed to perform a full automated linting pass (scan a directory, collect results, produce a report), a forked `general-purpose` agent would make sense. But the discuss-CONTEXT.md makes clear this is a guide, not an automated scanner.

---

## Question 2: Should `disable-model-invocation` be set?

**Recommendation: Do NOT set `disable-model-invocation: true`. Leave it at the default (false).**

### Rationale

- Per discuss-CONTEXT.md: "Invocation: user-invoked (slash command `/skilllint`) AND model-invoked (when linting topics come up)."
- The skill should activate automatically when Claude encounters linting errors, when a user asks about skilllint rules, or when plugin validation is being discussed. This is the core value -- Claude should know about this tool without the user needing to explicitly invoke it.
- `disable-model-invocation: true` would remove the skill description from Claude's context entirely (per the specification table), meaning Claude would never know this tool exists unless the user types `/skilllint`.
- This skill has no side effects (it guides usage, it does not deploy or modify infrastructure), so there is no safety reason to restrict auto-invocation.

### Impact on context budget

With `disable-model-invocation: false`, the skill's description (up to 1024 chars) is always loaded into the `<available_skills>` block (2% of context window). This is a small cost and worthwhile for discoverability.

---

## Question 3: What `allowed-tools` are appropriate?

**Recommendation: Do NOT specify `allowed-tools`. Let the skill inherit the parent agent's tool capabilities.**

### Rationale

- Per the specification: "When an `allowed-tools` field is not specified, the skill inherits the tool capabilities of the parent agent. This is a common pattern for skills that need to use tools from the parent agent."
- The skill is an inline knowledge skill, not a forked agent. It loads into the main conversation context. The orchestrator/main agent already has access to Read, Bash, Grep, Glob, Edit, Write, etc. Specifying `allowed-tools` would actually RESTRICT the agent to only those tools (the field is both a pre-approval and a scoping mechanism).
- The skill needs Claude to be able to:
  - Run `skilllint` via Bash (to scan, check versions, etc.)
  - Read files (to look at linting output, SKILL.md files being linted)
  - Edit files (to apply manual fixes based on rule guidance)
  - Search files (Grep/Glob to find files to lint)
- Restricting to a subset would break the natural workflow. The user might ask Claude to fix a violation, which requires Edit/Write -- tools that would need to be explicitly listed if `allowed-tools` were set.

### Exception case

If the skill were `context: fork`, we would need `allowed-tools: Read, Bash, Grep, Glob, Edit, Write` to grant those tools to the subagent. Since we are not forking, this is unnecessary.

---

## Question 4: Should the skill use `argument-hint`?

**Recommendation: YES. Use `argument-hint: "[rule-id | path]"`.**

### Rationale

- Per discuss-CONTEXT.md: "Argument support: YES -- `skilllint <rule-id>` should explain a specific rule; no args = full guide."
- The `argument-hint` field provides autocomplete guidance in the `/` menu. When the user starts typing `/skilllint`, they see `[rule-id | path]` as a hint, making it clear the skill accepts arguments.
- The skill content should use `<$ARGUMENTS>` for argument substitution. When invoked as `/skilllint FM004`, the `<$ARGUMENTS>` placeholder resolves to `FM004`, and the skill instructions can branch: "If a rule ID is provided, explain that specific rule and how to fix it."

### Implementation pattern

```yaml
---
argument-hint: "[rule-id | path]"
---

# skilllint Guide

<$ARGUMENTS>

If a rule ID was provided above (e.g., FM004, SK006, HK001), explain that rule...
If a path was provided, show how to run skilllint on that path...
If no arguments, show the full usage guide...
```

---

## Question 5: Is a `references/` subdirectory appropriate for a rule catalog?

**Recommendation: YES, use `references/` for the full rule catalog, but keep it to a single file.**

### Rationale

- The skilllint tool validates across multiple rule series: FM (frontmatter), SK (skill structure/tokens), HK (hooks), PL (plugin), NR (namespace references), AS (agentskills standard). Based on the test files, there are at least 25+ distinct rule codes.
- Putting the full catalog inline in SKILL.md would bloat the skill body. The skill specification encourages progressive disclosure: "Supporting files can also live at the skill root. Reference them from SKILL.md so Claude knows what each file contains and when to load it."
- SKILL.md should contain: the guide workflow (install, scan, interpret output, fix), a compact rule-series overview, and a pointer to `references/rule-catalog.md` for the detailed per-rule explanations.
- A single `references/rule-catalog.md` is sufficient. There is no need for one file per series -- the catalog is a lookup table, not a set of independent documents.

### Token budget consideration

- SKILL.md content only loads when the skill is activated (not at startup). The references/ files load on demand when Claude reads them. This two-tier approach keeps the initial activation cost low.
- Per the specification, if SKILL.md body exceeds 4400 tokens, the plugin assessor flags SK006 (warning); if it exceeds 8800 tokens, it flags SK007 (error). Keeping the detailed catalog in references/ avoids this.

### Discovered rule codes (from test files)

| Series | Codes Found | Category |
|--------|-------------|----------|
| FM | FM001, FM002, FM003, FM004, FM007, FM008, FM009, FM010 | Frontmatter validation |
| SK | SK001, SK002, SK003, SK006, SK007, SK009 | Skill structure/tokens |
| HK | HK001, HK002, HK003, HK004, HK005 | Hook validation |
| PL | PL002, PL003 | Plugin manifest |
| NR | NR001 | Namespace references |
| AS | AS001, AS002, AS003, AS004, AS005, AS006 | AgentSkills standard |

Note: The actual rule registry in the source code may contain additional rules not exercised in tests. The rule catalog should be generated from the source, not hardcoded.

---

## Question 6: Should we use dynamic context injection (`!`command``) to show live skilllint output?

**Recommendation: YES, but selectively -- use it for version checking only, not for full scan output.**

### Good use case: Version check

```markdown
Current installed version:
!`skilllint --version 2>/dev/null || echo "not installed"`
```

This runs at skill activation time (preprocessing), so Claude immediately knows whether skilllint is installed and what version is available. This enables the skill to give contextual advice ("you have version X, consider upgrading" vs "skilllint is not installed, here is how to install it").

### Bad use case: Full scan output

Do NOT use dynamic injection for `!`skilllint .``. Reasons:
- The scan target depends on user context (what directory? what files?). Dynamic injection runs before Claude sees the prompt, so there is no way to parameterize it.
- Scan output can be very large (hundreds of violations), which would bloat the skill content injected into context.
- The skill should instruct Claude to run `skilllint` as a Bash command, not pre-run it.

### Implementation

```yaml
---
name: skilllint
description: Guide for using the skilllint CLI to validate Claude Code plugins, skills, and agents. Use when discussing linting, plugin validation, rule violations, or skilllint installation.
argument-hint: "[rule-id | path]"
---

skilllint status: !`command -v skilllint >/dev/null 2>&1 && skilllint --version 2>/dev/null || echo "NOT INSTALLED"`

# skilllint Guide
...
```

---

## Proposed Skill Structure

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

### Proposed SKILL.md frontmatter

```yaml
---
name: skilllint
description: Guide for using the skilllint CLI to validate Claude Code plugins, skills, and agents. Explains rule violations (FM/SK/HK/PL/NR/AS series), fix workflows, installation via uv/pipx/pip, and version management. Use when discussing linting errors, plugin validation, or skilllint commands.
argument-hint: "[rule-id | path]"
---
```

### Frontmatter field decisions (summary)

| Field | Value | Reason |
|-------|-------|--------|
| `name` | `skilllint` | Matches directory name, creates `/skilllint` command |
| `description` | (see above) | Includes trigger keywords for auto-invocation |
| `argument-hint` | `[rule-id \| path]` | Shows users can pass a rule ID or file path |
| `context` | (omitted = inline) | Needs conversation context, not isolated |
| `agent` | (omitted) | Not applicable without `context: fork` |
| `disable-model-invocation` | (omitted = false) | Should auto-activate on linting topics |
| `user-invocable` | (omitted = true) | Users should be able to invoke directly |
| `allowed-tools` | (omitted) | Inherits parent tools; no restriction needed |
| `model` | (omitted) | Inherits session model |
| `hooks` | (omitted) | No lifecycle hooks needed |

---

## Additional Design Notes

### No `skilllint rule` subcommand exists yet

The current CLI (`skilllint --help`) has no `rule` subcommand. The discuss-CONTEXT.md mentions `skilllint rule <rule-id>` but this does not exist in the current codebase. The skill should document the actual CLI interface:
- `skilllint <path>` -- validate a plugin/skill/agent
- `skilllint check --fix <path>` -- auto-fix where possible
- `skilllint check <path>` -- validate only
- `skilllint --filter-type skills|agents|commands <path>` -- filter by file type
- `skilllint --platform claude-code|cursor|codex <path>` -- platform-specific validation

The rule catalog in `references/rule-catalog.md` serves the "explain a rule" function until a `rule` subcommand is implemented.

### Installation instructions should cover three methods

1. `uv tool install skilllint` / `uv tool upgrade skilllint`
2. `pipx install skilllint` / `pipx upgrade skilllint`
3. `pip install skilllint` / `pip install --upgrade skilllint`

### The `<$ARGUMENTS>` branching pattern

The skill body should handle three invocation patterns:
1. `/skilllint` (no args) -- show full usage guide
2. `/skilllint FM004` (rule ID) -- explain that specific rule, show fix
3. `/skilllint ./path/to/plugin` (path) -- show how to run skilllint on that path

---

## Sources

- Skill specification: `claude-skills-overview-2026` (loaded via plugin-creator skill)
- Plugin specification: `claude-plugins-reference-2026` (loaded via plugin-creator skill)
- Project context: `/home/user/agentskills-linter/.claude/plan/agentskills-skilllint/discuss-CONTEXT.md`
- CLI help: `skilllint --help` output
- Rule codes: extracted from test files in `/home/user/agentskills-linter/packages/skilllint/tests/`
