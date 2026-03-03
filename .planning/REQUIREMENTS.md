# Requirements: skilllint

**Defined:** 2026-03-02
**Core Value:** An AI agent or developer who creates a plugin/skill/agent gets instant, actionable feedback — in their editor, in CI, and from the AI itself — before their work ever ships broken.

## v1 Requirements

### Packaging and Distribution

- [x] **PKG-01**: Package is structured as an installable Python package (`packages/skilllint/`) with `pyproject.toml` and hatchling build backend — replacing PEP 723 standalone scripts
- [x] **PKG-02**: Package installs via `uv add skilllint` or `pip install skilllint` and is distributable as a `.whl`
- [x] **PKG-03**: CLI entry points `skilllint`, `agentlint`, `pluginlint`, `skillint` all invoke the same binary
- [x] **PKG-04**: Platform schema snapshots (JSON files) are bundled inside the wheel and accessed via `importlib.resources.files()` at runtime
- [ ] **PKG-05**: PEP 723 → package migration is atomic — pre-commit hook users are not broken; existing `uv run plugin_validator.py` workflow is preserved or explicitly migrated

### Platform Adapters

- [ ] **ADPT-01**: `PlatformAdapter` Protocol defines the interface for platform-specific schema and rule sets
- [ ] **ADPT-02**: Adapters register via Python entry_points (`skilllint.adapters`) so third-party adapters can be installed without modifying the core package
- [ ] **ADPT-03**: Claude Code adapter — validates plugin.json, SKILL.md, agents/*.md, commands/*.md, hooks.json against Claude Code schemas
- [ ] **ADPT-04**: Cursor adapter — validates `.mdc` rule files and Cursor-specific configuration
- [ ] **ADPT-05**: Codex / OpenAI adapter — validates OpenAI Codex agent format files

### Fix Mode and Configuration

- [ ] **CFG-01**: `--fix` flag auto-applies safe fixes (e.g., array format, multiline → single-line) and reports-only for unsafe violations
- [ ] **CFG-02**: `[tool.skilllint]` section in `pyproject.toml` (or `linter.toml`) supports enabling/disabling individual rules by code
- [ ] **CFG-03**: Per-file or per-directory rule overrides in config (e.g., ignore SK006 for templates/)
- [ ] **CFG-04**: Token complexity thresholds (SK006/SK007) are configurable per-project rather than hardcoded (resolves issue #5)

### Core Validator Bug Fixes and Coverage (from GitHub issues)

- [ ] **VAL-01**: Report summary counts unique files, not validator invocations — "Total files: 1" for 1 file validated by 4 validators (resolves issue #3, sub-issue 1)
- [ ] **VAL-02**: SK005 (missing trigger phrases) fires only on SKILL files, not COMMAND or AGENT files (resolves issue #3, sub-issue 2)
- [ ] **VAL-03**: SK004 (description too short) fires on SKILL and AGENT files but not COMMAND files (resolves issue #3, sub-issue 2)
- [ ] **VAL-04**: `FileType` enum includes HOOK_SCRIPT and HOOK_CONFIG variants; `detect_file_type()` recognizes `.js` files in `hooks/` directories and `hooks.json` files (resolves issue #3, sub-issue 3)
- [ ] **VAL-05**: `HookValidator` class validates hook files using HK001+ error code series (valid JSON, valid event types, valid matcher patterns) (resolves issue #3, sub-issue 3)
- [ ] **VAL-06**: Dead nested skill resolution code removed from `_resolve_skill_reference` (lines 904–911) and related error message strings updated (resolves issue #3, sub-issue 4)
- [ ] **VAL-07**: PR003 and PR004 test coverage added to `test_plugin_registration_validator.py` (resolves issue #6)
- [ ] **VAL-08**: Dead code removed: triplicated regex patterns, unused `skipped` list, unused `sum()` call, HK005 incorrectly treated as error (resolves issue #7)
- [ ] **VAL-09**: Pre-commit integration runs only on changed files by default; template files (e.g., `commands/development/templates/*.md`) excluded from FM003 false positives (resolves issue #4)

### LSP Server

- [ ] **LSP-01**: LSP server (`skilllint.lsp.server`) imports `ValidationEngine` directly — no subprocess spawning
- [ ] **LSP-02**: Diagnostics surfaced as editor warnings/errors using incremental document sync (not full sync) for keypress-level responsiveness
- [ ] **LSP-03**: Code actions expose auto-fixable violations as quick-fix actions in the editor
- [ ] **LSP-04**: Hover on rule codes (e.g., SK001) shows rule description, rationale, and fix hint
- [ ] **LSP-05**: Schema-aware completions for frontmatter field names and valid values driven by active platform adapter
- [ ] **LSP-06**: LSP server tested with pytest-lsp end-to-end test suite

### VS Code Extension

- [ ] **VSCE-01**: TypeScript extension shell spawns Python LSP server (`python -m skilllint.lsp.server`) via stdio; zero validation logic in TypeScript
- [ ] **VSCE-02**: Violations appear in VS Code Problems panel (diagnostics panel integration)
- [ ] **VSCE-03**: Status bar indicator shows active platform adapter name and violation count
- [ ] **VSCE-04**: Platform adapter selector UI lets user switch active adapter (Claude Code / Cursor / Codex)
- [ ] **VSCE-05**: Extension published to VS Code Marketplace as `.vsix`

### MCP Server

- [ ] **MCP-01**: FastMCP 3.x server (`skilllint.mcp.server`) with stderr-only logging — no stdout output that could corrupt JSON-RPC channel
- [ ] **MCP-02**: `validate_plugin`, `validate_skill`, `validate_agent` tools — AI can validate its own generated output and receive structured results
- [ ] **MCP-03**: `query_schema` tool — AI can query what fields are valid for a given platform and file type
- [ ] **MCP-04**: `scaffold_plugin`, `scaffold_skill`, `scaffold_agent` tools — AI can generate correct skeleton files for a given platform
- [ ] **MCP-05**: `list_rules` tool — AI can list all active rules with descriptions and severity
- [ ] **MCP-06**: All MCP tool descriptions are static strings (no f-strings, no dynamic content) to prevent prompt injection

### Claude Code .plugin Distribution

- [ ] **PLUGIN-01**: Claude Code `.plugin` bundle (plugin.json + MCP server + skill + agent) installable as a `.plugin` file into Claude Code
- [ ] **PLUGIN-02**: `skilllint` SKILL.md teaches Claude how to use skilllint effectively (when to validate, how to interpret results, how to fix violations)
- [ ] **PLUGIN-03**: `skilllint` agent validates plugins/skills/agents before presenting them to the user
- [ ] **PLUGIN-04**: Claude Code hooks (PostToolUse on Write/Edit) trigger validation on `.md` and `plugin.json` files within the scope of the active plugin/skill directory
- [ ] **PLUGIN-05**: Package also distributed as a `.skill` file for portability

### SAM Tooling (issue #11)

- [ ] **SAM-01**: Python validator replaces `validate-task-file.sh` for task format validation, using the shared `task_format.py` module and supporting YAML frontmatter

## v2 Requirements

### Extended Platform Support

- **ADPT-V2-01**: Windsurf adapter
- **ADPT-V2-02**: Roo Code adapter
- **ADPT-V2-03**: Amp / Sourcegraph Cody adapter
- **ADPT-V2-04**: Generic agentskills.io standard adapter

### Extended LSP Features

- **LSP-V2-01**: YAML frontmatter completions in Markdown (confirmed ecosystem gap — no established pattern as of 2026-03)
- **LSP-V2-02**: Conflict resolution with redhat.vscode-yaml for frontmatter range ownership

### Extended MCP Features

- **MCP-V2-01**: `holistic-linting` MCP server wrapping `holistic_lint.py` with `lint_files`, `list_lint_errors`, `auto_fix` tools (from issue #10)

### Registry and Schema Sync

- **REG-V2-01**: Schema update tooling — automated process for updating bundled schema snapshots when platforms release new versions

## Out of Scope

| Feature | Reason |
|---------|--------|
| Live schema fetching at lint time | Bundled snapshots chosen for offline/sandbox reliability; live fetch adds fragility |
| Speed/performance as design goal (Rust rewrite) | Python + uv run is sufficient for current scale |
| Mobile or web UI | CLI + LSP + VS Code covers target surfaces |
| Generic agent installer (.skill → any platform) | Claude Code .plugin installs into Claude Code only; cross-platform install deferred to v2 |
| Real-time collaboration or shared config | Single-developer tool scope for v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PKG-01 | Phase 1: Package Structure | Complete (01-01) |
| PKG-02 | Phase 1: Package Structure | Complete (01-01) |
| PKG-03 | Phase 1: Package Structure | Complete |
| PKG-04 | Phase 1: Package Structure | Complete |
| PKG-05 | Phase 1: Package Structure | Pending |
| ADPT-01 | Phase 2: Platform Adapters | Pending |
| ADPT-02 | Phase 2: Platform Adapters | Pending |
| ADPT-03 | Phase 2: Platform Adapters | Pending |
| ADPT-04 | Phase 2: Platform Adapters | Pending |
| ADPT-05 | Phase 2: Platform Adapters | Pending |
| CFG-01 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| CFG-02 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| CFG-03 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| CFG-04 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| VAL-01 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| VAL-02 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| VAL-03 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| VAL-04 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| VAL-05 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| VAL-06 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| VAL-07 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| VAL-08 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| VAL-09 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| SAM-01 | Phase 3: Fix Mode, Config, and Validator Correctness | Pending |
| LSP-01 | Phase 4: LSP Server | Pending |
| LSP-02 | Phase 4: LSP Server | Pending |
| LSP-03 | Phase 4: LSP Server | Pending |
| LSP-04 | Phase 4: LSP Server | Pending |
| LSP-05 | Phase 4: LSP Server | Pending |
| LSP-06 | Phase 4: LSP Server | Pending |
| VSCE-01 | Phase 5: VS Code Extension | Pending |
| VSCE-02 | Phase 5: VS Code Extension | Pending |
| VSCE-03 | Phase 5: VS Code Extension | Pending |
| VSCE-04 | Phase 5: VS Code Extension | Pending |
| VSCE-05 | Phase 5: VS Code Extension | Pending |
| MCP-01 | Phase 6: MCP Server | Pending |
| MCP-02 | Phase 6: MCP Server | Pending |
| MCP-03 | Phase 6: MCP Server | Pending |
| MCP-04 | Phase 6: MCP Server | Pending |
| MCP-05 | Phase 6: MCP Server | Pending |
| MCP-06 | Phase 6: MCP Server | Pending |
| PLUGIN-01 | Phase 7: Claude Code .plugin | Pending |
| PLUGIN-02 | Phase 7: Claude Code .plugin | Pending |
| PLUGIN-03 | Phase 7: Claude Code .plugin | Pending |
| PLUGIN-04 | Phase 7: Claude Code .plugin | Pending |
| PLUGIN-05 | Phase 7: Claude Code .plugin | Pending |

**Coverage:**
- v1 requirements: 46 total
- Mapped to phases: 46
- Unmapped: 0

---
*Requirements defined: 2026-03-02*
*Last updated: 2026-03-02 — traceability expanded to explicit per-requirement rows after roadmap creation*
