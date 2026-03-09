# Phase 2: Platform Adapters - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Define a `PlatformAdapter` Protocol and ship bundled adapters for Claude Code, Cursor, and Codex. Enable the validator to route file validation through the correct platform-specific schema and rule set. Introduce a shared agentskills.io rule series (AS-codes) that fires across all platforms. Windsurf and other platforms are v2 scope.

</domain>

<decisions>
## Implementation Decisions

### Adapter Protocol design
- Use `typing.Protocol` (structural subtyping) — third-party adapters do NOT import from skilllint to be compatible
- Each adapter has a string ID (e.g., `claude_code`, `cursor`, `codex`)
- Adapter's responsibilities: provide schema for each file type, declare path patterns for auto-detection, declare applicable rule codes
- Core validator owns all rule execution — adapters are data providers, not logic owners
- Adapter exposes `applicable_rules()` returning a set of rule code prefixes or explicit codes — core filters checks accordingly
- Bundled adapters registered in `pyproject.toml` via `skilllint.adapters` entry_points group
- Third-party adapters install via the same entry_points mechanism — no core modification needed

### Rule code series
- New **AS-series** codes for agentskills.io spec violations (AS001, AS002, AS003, …)
  - AS-series fires on ANY SKILL.md regardless of platform adapter
  - Examples: AS001 = name format, AS002 = description length/quality, AS003 = directory name mismatch
- SK/PR/HK codes remain Claude Code-specific
- Each platform adapter declares which code series it activates
- This separation means third-party adapters can reference AS codes without depending on SK codes

### Shared agentskills.io validation (AS-series)
All platforms that have SKILL.md files get these checks:
- `name`: 1–64 chars, lowercase alphanumeric + hyphens, no leading/trailing/consecutive hyphens, must match parent directory name
- `description`: 1–1024 chars, non-empty, should be trigger-oriented (description quality check)
- Directory structure: `SKILL.md` required, `scripts/`, `references/`, `assets/` optional
- Progressive disclosure: warn if `SKILL.md` body exceeds 500 lines (move detail to references/)
- Test case detection: identify if `eval_queries.json` or equivalent test fixtures exist alongside the skill

Reference: https://agentskills.io/specification.md — researcher should also check https://agentskills.io/skill-creation/optimizing-descriptions.md and https://agentskills.io/skill-creation/evaluating-skills.md for AS-series rule completeness

### Platform detection
- Each adapter **declares its own path patterns** (glob patterns) — not hardcoded in core
- CLI matches a file against all registered adapter patterns; all matching adapters run their checks
- `--platform` flag overrides auto-detection when ambiguous or wrong
- **Multi-adapter files**: when a file matches multiple adapters, run AS-series rules once, then each matching adapter's platform-specific checks; report violations grouped by adapter
- Layered validation model:
  - AS-series rules = cross-platform baseline (agentskills.io spec)
  - Platform-specific rules = only fire when that adapter matches the file

### Layered frontmatter reality
- Cursor reads SKILL.md files from `.claude/`, `.agents/`, and `.cursor/` directories — same file may be valid for both Claude Code and Cursor
- Cursor uses agentskills.io frontmatter fields (`name`, `description`, `license`, `metadata`, `compatibility`, `allowed-tools`) but NOT Claude Code-specific fields (e.g., plugin-specific extensions)
- Adapter declares which frontmatter fields are valid for it — fields outside AS-spec and not in adapter's declared fields produce platform-specific warnings, not AS-series errors
- Researcher should verify exact Cursor and Codex field lists from their official docs

### Claude Code adapter
- Validates: `plugin.json`, `SKILL.md` (under `.claude/`), `agents/*.md`, `commands/*.md`, `hooks.json`
- Path patterns: `.claude/**/*.md`, `plugin.json`, `hooks.json`, `agents/**/*.md`, `commands/**/*.md`
- Runs existing SK/PR/HK rule series in addition to AS-series
- Reference for Claude Code-specific validation matrix: `/home/ubuntulinuxqa2/repos/claude-plugins-official/plugins/` (skill-creator and plugin-dev plugins contain Claude Code-specific validation rules)

### Cursor adapter
- Validates: `.mdc` rule files, SKILL.md in `.cursor/` directory
- Path patterns: `**/*.mdc`, `.cursor/**/*.md`, `.agents/skills/**/*.md`
- Schema content: researcher verifies complete `.mdc` frontmatter field list from Cursor docs before planning (known fields: `description`, `globs`, `alwaysApply`)
- Runs AS-series for SKILL.md files; Cursor-specific schema checks for `.mdc` files

### Codex adapter
- Validates: SKILL.md (under `.agents/skills/`), `AGENTS.md`, `.rules` files
- Path patterns: `.agents/skills/**/*.md`, `AGENTS.md`, `**/*.rules`, `.codex/**`
- Codex skill format = agentskills.io standard (same `name`/`description` frontmatter as Claude Code) — AS-series applies
- `AGENTS.md`: plain markdown, no strict schema — check presence and non-empty content
- `.rules` files: validate known Starlark `prefix_rule()` fields (`pattern`, `decision`, `justification`, `match`, `not_match`); note format is experimental and may change
- Schema source: https://developers.openai.com/codex/skills.md, https://developers.openai.com/codex/rules.md, https://developers.openai.com/codex/multi-agent.md

### Bundled schema snapshots
- Phase 1 established `load_bundled_schema("claude_code", "v1")` pattern via `importlib.resources.files()`
- Phase 2 adds `skilllint.schemas.cursor` and `skilllint.schemas.codex` namespace packages with `v1.json` snapshots
- v1.json is a Phase 2 deliverable with real field definitions (not stubs)
- Schema update tooling is v2 scope

### Phase 2 validation depth
- Schema validation: required fields present, types correct, no unknown fields
- AS-series shared rules: name/description/structure per agentskills.io spec
- Platform-specific field validation per adapter
- NO full SK/PR rule execution for Cursor/Codex adapters in Phase 2 — that is Phase 3+
- .rules (Starlark) and agents/*.toml (Codex agent roles) validated for structure only

### Claude's Discretion
- Exact AS rule code numbering beyond AS001-AS003
- Internal adapter registry implementation detail (lazy vs eager loading)
- Error message wording for AS-series violations
- Whether adapter path patterns use fnmatch or pathlib glob semantics

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `load_bundled_schema(platform, version)` in `skilllint/__init__.py`: accesses `skilllint.schemas.{platform}/{version}.json` via `importlib.resources.files()` — adapter can call this to load its schema
- `skilllint/schemas/claude_code/__init__.py` + `v1.json`: namespace package pattern to replicate for `cursor` and `codex`
- `skilllint/schemas/__init__.py`: top-level schemas namespace — add new platform subpackages here
- Existing validators in `plugin_validator.py`: Claude Code-specific; Phase 2 wraps these behind the Claude Code adapter

### Established Patterns
- Entry_points discovery: pattern from pyproject.toml `[project.entry-points]` — same mechanism used for CLI aliases; extend for `skilllint.adapters`
- `importlib.resources.files()`: runtime schema access pattern — no filesystem paths, works in wheel
- Namespace packages with `__init__.py` markers: established in Phase 1 for schemas

### Integration Points
- `plugin_validator.py` CLI (`app`): needs to accept `--platform` flag and route to adapter
- `conftest.py` test fixtures: existing fixture patterns for validation tests — adapter tests follow same structure
- Pre-commit hook: must pass file paths through adapter detection; `--platform` may be needed for pre-commit config

### Reference Repositories
- `/home/ubuntulinuxqa2/repos/claude-plugins-official/plugins/`: official Claude Code plugins with platform-specific validation rules — use as reference for Claude Code adapter rule matrix
- `/home/ubuntulinuxqa2/repos/vercel-plugin/hooks/posttooluse-validate.mjs` + `patterns.mjs`: path pattern matching approach — adapters declaring path patterns mirrors this design

</code_context>

<specifics>
## Specific Ideas

- "Adapter is a Protocol, not ABC — third-party adapters don't need to import from skilllint"
- "AS-series codes have clear provenance: AS = agentskills.io spec, SK = Claude Code-specific"
- "Cursor reads .claude/ skills but only validates agentskills.io frontmatter — not Claude Code extensions. Same file, different validation layer depending on adapter."
- "Validate all matching adapters when file matches multiple — report grouped by adapter"
- "Researcher should read agentskills.io/specification.md, /skill-creation/optimizing-descriptions.md, /skill-creation/evaluating-skills.md, /skill-creation/using-scripts.md, /client-implementation/adding-skills-support.md for complete AS-series rule derivation"
- "Codex .rules files use Starlark — validate known prefix_rule() fields but note format is experimental"

</specifics>

<deferred>
## Deferred Ideas

- Windsurf adapter — v2 scope (ADPT-V2-01)
- Roo Code, Amp/Sourcegraph Cody, generic agentskills.io adapters — v2 scope
- Schema update tooling (automated snapshot refresh) — v2 scope (REG-V2-01)
- Full SK/PR rule validation for Cursor/Codex files — Phase 3+
- `agents/*.toml` deep validation for Codex agent roles — not in Phase 2
- MCP server wrapping for holistic_lint.py — v2 scope (MCP-V2-01)
- agentskills.io specification updates (user noted spec may need updating) — separate task outside this phase

</deferred>

---

*Phase: 02-platform-adapters*
*Context gathered: 2026-03-09*
