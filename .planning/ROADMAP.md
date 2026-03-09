# Roadmap: skilllint

## Overview

skilllint starts as a PEP 723 monolith and becomes a fully packaged Python linter for AI agent plugins, skills, and agents — shipping as a CLI, LSP server, VS Code extension, MCP server, and Claude Code .plugin. The dependency graph is strict: packaging must precede adapters, adapters must precede LSP/MCP, LSP must precede the VS Code extension, and MCP must precede the .plugin bundle. Each phase delivers a coherent, independently verifiable capability before the next begins.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Package Structure** - Migrate PEP 723 scripts to an installable Python package distributable as a .whl (completed 2026-03-03)
- [ ] **Phase 2: Platform Adapters** - Pluggable PlatformAdapter architecture with Claude Code, Cursor, and Codex adapters
- [ ] **Phase 3: Fix Mode, Config, and Validator Correctness** - --fix flag, config file support, validator bug fixes, and SAM tooling
- [ ] **Phase 4: LSP Server** - Language server with diagnostics, code actions, hover, and completions driven by the validation engine
- [ ] **Phase 5: VS Code Extension** - TypeScript extension shell that spawns the LSP server and surfaces diagnostics in the editor
- [ ] **Phase 6: MCP Server** - FastMCP server exposing validate, query, scaffold, and list_rules tools for AI self-validation
- [ ] **Phase 7: Claude Code .plugin** - Bundle MCP server + skill + agent into an installable Claude Code .plugin artifact

## Phase Details

### Phase 1: Package Structure
**Goal**: skilllint is an installable Python package that ships as a .whl with bundled schema snapshots and named CLI entry points
**Depends on**: Nothing (first phase)
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04, PKG-05
**Success Criteria** (what must be TRUE):
  1. `uv add skilllint` installs the package and `skilllint --help` runs without error
  2. `skilllint`, `agentlint`, `pluginlint`, and `skillint` all invoke the same binary and produce identical output
  3. `uv build` produces a `.whl` that contains bundled schema JSON files accessible via `importlib.resources.files()`
  4. Existing pre-commit hook users are not broken — hooks run from the packaged entry point and all existing tests pass
  5. `uv run plugin_validator.py` either still works or the migration path is documented and enforced
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Merge feature/initial-packaging into main; verify 521 tests pass
- [ ] 01-02-PLAN.md — Add pluginlint entry point, exclude tests from wheel, create bundled schema directory
- [ ] 01-03-PLAN.md — Add .pre-commit-hooks.yaml, update conftest.py to package imports, document PEP 723 migration

### Phase 2: Platform Adapters
**Goal**: A pluggable PlatformAdapter architecture is in place with working adapters for Claude Code, Cursor, and Codex registered via Python entry_points
**Depends on**: Phase 1
**Requirements**: ADPT-01, ADPT-02, ADPT-03, ADPT-04, ADPT-05
**Success Criteria** (what must be TRUE):
  1. `PlatformAdapter` Protocol is defined and all three bundled adapters (Claude Code, Cursor, Codex) implement it without error
  2. Third-party adapters installed as separate packages are discovered automatically via `skilllint.adapters` entry_points — no code changes to core required
  3. `skilllint --platform claude-code` validates plugin.json, SKILL.md, agents/*.md, commands/*.md, and hooks.json against Claude Code schemas
  4. `skilllint --platform cursor` validates `.mdc` rule files; `skilllint --platform codex` validates OpenAI Codex agent format files
**Plans**: 5 plans

Plans:
- [x] 02-01-PLAN.md — Wave 0: test scaffolds and fixtures (TDD)
- [ ] 02-02-PLAN.md — PlatformAdapter Protocol + AS-series rules AS001-AS006
- [ ] 02-03-PLAN.md — Cursor and Codex schema namespace packages
- [ ] 02-04-PLAN.md — Three bundled adapters + entry_points registration
- [ ] 02-05-PLAN.md — CLI --platform flag + adapter dispatch

### Phase 3: Fix Mode, Config, and Validator Correctness
**Goal**: The CLI auto-fixes safe violations, respects per-project configuration, and all known validator bugs from GitHub issues #3–#7 and #11 are resolved
**Depends on**: Phase 2
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, VAL-01, VAL-02, VAL-03, VAL-04, VAL-05, VAL-06, VAL-07, VAL-08, VAL-09, SAM-01
**Success Criteria** (what must be TRUE):
  1. `skilllint --fix` auto-applies safe fixes (array format, multiline normalization) and leaves unsafe violations as report-only warnings
  2. A `[tool.skilllint]` section in `pyproject.toml` (or `linter.toml`) enables disabling individual rule codes and setting per-directory overrides — changes take effect without restarting the linter
  3. Validating one file with four validators reports "Total files: 1" (not 4); SK005 fires only on SKILL files; SK004 fires on SKILL and AGENT files but not COMMAND files
  4. Hook files (`.js` in `hooks/` and `hooks.json`) are detected, validated with HK001+ error codes, and pre-commit runs only on changed files with template directories excluded from FM003
  5. `python validator.py tasks/` validates task files using `task_format.py` and replaces the `validate-task-file.sh` shell script
**Plans**: TBD

### Phase 4: LSP Server
**Goal**: A pygls language server publishes diagnostics, exposes code actions for fixable violations, shows hover documentation for rule codes, and offers schema-aware completions — all driven by the ValidationEngine with no subprocess calls
**Depends on**: Phase 3
**Requirements**: LSP-01, LSP-02, LSP-03, LSP-04, LSP-05, LSP-06
**Success Criteria** (what must be TRUE):
  1. Opening a SKILL.md or plugin.json file in any LSP-compatible editor shows diagnostics (squiggles) within 200ms of the last keypress — diagnostics disappear immediately when the violation is fixed
  2. A quick-fix lightbulb appears on fixable violations; applying it corrects the file in-place using the same fix logic as `--fix`
  3. Hovering over a rule code (e.g., SK001) in any diagnostic shows the rule description, rationale, and fix hint inline
  4. Frontmatter field completions for the active platform adapter appear when editing supported files (Claude Code fields for claude-code adapter, Cursor fields for cursor adapter)
  5. The LSP server passes the pytest-lsp end-to-end test suite covering open, change, hover, code action, and completion scenarios
**Plans**: TBD

### Phase 5: VS Code Extension
**Goal**: A VS Code extension spawns the Python LSP server and surfaces diagnostics, quick fixes, status bar indicators, and a platform adapter selector in the editor
**Depends on**: Phase 4
**Requirements**: VSCE-01, VSCE-02, VSCE-03, VSCE-04, VSCE-05
**Success Criteria** (what must be TRUE):
  1. Installing the extension and opening a SKILL.md file shows violations as red/yellow squiggles and entries in the VS Code Problems panel — no manual server start required
  2. Applying a quick fix from the lightbulb or "Fix all" from the command palette corrects violations in the file
  3. The status bar shows the active platform adapter name and current violation count; clicking it switches adapters (Claude Code / Cursor / Codex)
  4. Extension settings (platform adapter, rule overrides) are configurable in the VS Code Settings UI and apply per-workspace
  5. The extension is publishable as a `.vsix` and listed on the VS Code Marketplace
**Plans**: TBD

### Phase 6: MCP Server
**Goal**: A FastMCP server exposes validate, query_schema, scaffold, and list_rules tools that AI agents can call to self-validate generated output and retrieve schema information
**Depends on**: Phase 3
**Requirements**: MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06
**Success Criteria** (what must be TRUE):
  1. `validate_skill`, `validate_agent`, and `validate_plugin` tools return structured JSON results that an AI agent can parse and act on — no prose error messages
  2. `query_schema` returns the valid field names and constraints for a given platform and file type; `list_rules` returns all active rules with codes, descriptions, and severity
  3. `scaffold_plugin`, `scaffold_skill`, and `scaffold_agent` return syntactically correct skeleton files for the requested platform that pass validation with zero violations
  4. The MCP server produces zero output on stdout — all logging goes to stderr; MCP Inspector verifies the server starts, lists tools, and handles tool calls without JSON-RPC corruption
  5. All tool descriptions are static strings with no dynamic content or user-input interpolation
**Plans**: TBD

### Phase 7: Claude Code .plugin
**Goal**: skilllint ships as a Claude Code .plugin bundle that installs the MCP server, a SKILL.md teaching document, and an agent that validates plugins/skills/agents before they are presented to the user
**Depends on**: Phase 6
**Requirements**: PLUGIN-01, PLUGIN-02, PLUGIN-03, PLUGIN-04, PLUGIN-05
**Success Criteria** (what must be TRUE):
  1. Installing the `.plugin` file into Claude Code activates the MCP server, SKILL.md, and agent without manual configuration
  2. After installation, Claude can call `validate_skill` and receive results that guide it to produce valid frontmatter in subsequent writes
  3. PostToolUse hooks on Write/Edit automatically trigger validation on `.md` and `plugin.json` files within active plugin/skill directories and surface violations inline
  4. The package is also distributable as a standalone `.skill` file that can be loaded independently of the full .plugin bundle
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Package Structure | 3/3 | Complete    | 2026-03-03 |
| 2. Platform Adapters | 2/5 | In Progress|  |
| 3. Fix Mode, Config, and Validator Correctness | 0/TBD | Not started | - |
| 4. LSP Server | 0/TBD | Not started | - |
| 5. VS Code Extension | 0/TBD | Not started | - |
| 6. MCP Server | 0/TBD | Not started | - |
| 7. Claude Code .plugin | 0/TBD | Not started | - |
