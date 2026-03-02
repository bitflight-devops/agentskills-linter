# Project Research Summary

**Project:** skilllint
**Domain:** Python linter for AI agent plugin/skill YAML frontmatter — CLI, LSP server, VS Code extension, MCP server, .whl distribution
**Researched:** 2026-03-02
**Confidence:** MEDIUM-HIGH

## Executive Summary

skilllint is a Python-based linter for AI agent plugin/skill frontmatter that must ship across four distinct surfaces: a CLI (already exists), an LSP server for editor integration, a VS Code extension that packages the LSP, and an MCP server for AI agent self-validation. The established pattern for this class of tool — exemplified by ruff's native server and microsoft/vscode-python-tools-extension-template — is a pure Python validation library at the core with thin protocol wrappers on top. The critical prerequisite is migrating the existing monolithic `plugin_validator.py` into a proper installable Python package (`skilllint/`) before any LSP or MCP work can begin. All three new surfaces import from `engine.py` directly; without a proper package structure, each surface must duplicate validation logic or shell out via subprocess, both of which are dead ends.

The recommended stack is well-established: `pygls 2.0.1` for the LSP server, `fastmcp 3.0.2` for the MCP server, `vscode-languageclient 9.x` + TypeScript for the VS Code extension shell, and `hatchling` + `importlib.resources` for Python wheel distribution with bundled schema snapshots. Each choice is the current industry standard with no meaningful alternatives for this use case. The architecture follows a strict layering rule: ValidationEngine is I/O-free library code; CLI, LSP server, and MCP server are each thin adapters that translate between the engine and their respective protocols.

The primary risks are implementation-order violations and protocol-specific traps. Building the LSP or MCP server before completing the package restructure is the most common mistake and the most expensive to recover from. The MCP server has a critical stdout corruption trap (any `print()` call corrupts the JSON-RPC channel). The LSP server has three independent correctness traps: wrong pygls import path (v1 vs v2), full document sync instead of incremental (causes stale diagnostics UX), and 0-based vs 1-based line number offsets (mispositioned squiggles). Each of these looks correct until editor integration testing, at which point recovery cost is high.

## Key Findings

### Recommended Stack

The new technology additions build directly on the existing Python 3.11+, uv, Pydantic 2.x, Typer, ruamel.yaml, tiktoken, Rich, and pytest stack. No existing dependencies require changes. The additions are:

- `pygls 2.0.1` (LSP server) + `lsprotocol 2025.0.0` (auto-installed) — the only actively maintained Python LSP framework; used by Microsoft's own Python tools extension template
- `fastmcp 3.0.2` (MCP server) — dominant Python MCP implementation, 1M downloads/day, GA since January 2026; `@mcp.tool` decorator keeps tool functions as plain callable Python
- `vscode-languageclient 9.0.1` (VS Code extension) — Microsoft's official npm package; the only supported VS Code LSP client API
- `esbuild` (VS Code extension bundler) — 50x faster than webpack for straightforward TypeScript; required for VS Code Web compatibility
- `hatchling` (build backend) + `importlib.resources` (runtime schema access) — correct Python packaging for non-Python data files (schemas) bundled in the wheel

**Core technologies:**
- `pygls 2.0.1`: Python LSP server framework — the reference implementation, v2.0 removes Pydantic dependency (no conflict with Pydantic 2.x)
- `fastmcp 3.0.2`: MCP server — cleaner than official SDK, `@mcp.tool` decorator on plain functions, Python 3.10+ compatible
- `vscode-languageclient 9.0.1`: VS Code LSP client — mandatory Microsoft package, no alternative
- `hatchling` + `importlib.resources`: wheel packaging with bundled schemas — `force-include` in pyproject.toml; `files("skilllint.schemas")` access at runtime
- `pytest-lsp`: end-to-end LSP test harness — spawns server as subprocess matching how VS Code does it

### Expected Features

**Must have (table stakes for v1):**

LSP:
- Publish diagnostics on open/change — core value; without this the LSP is useless
- Code actions for fixable diagnostics — lightbulb quick-fix; every comparable linter has this
- "Fix all" code action — batch fixing; users configure this immediately
- Hover on rule codes — inline documentation; eliminates context switching
- Configuration reload on file change — live config; otherwise server must restart on any config edit
- Server lifecycle (initialize/shutdown/exit) — protocol requirement; clients disconnect without it

VS Code Extension:
- Diagnostics in Problems panel + squiggly underlines — primary UX surface
- Quick fix lightbulb + fix on save (`source.fixAll.skilllint`) — table stakes for any VS Code linter
- Extension settings in Settings UI — per-workspace config needed for monorepos
- Status bar server indicator — debugging activation without it is frustrating
- Workspace trust declaration — VS Code rejects extensions that omit this

MCP Server:
- `validate_skill`, `validate_agent`, `validate_plugin` tools — core value proposition for AI consumers
- `query_schema` tool — AI agents need to know what fields are valid before authoring
- `list_rules` tool — AI agents need rule codes to explain violations
- Structured JSON output — AI agents cannot parse prose error messages

**Should have (competitive, v1.x):**
- LSP YAML frontmatter completions in Markdown files — highest complexity feature; no existing LSP fills this gap (confirmed open issues in vscode-yaml and Zed as of 2025)
- MCP `scaffold_skill/agent/command` tools — low complexity; AI agent avoids common frontmatter mistakes from scratch
- VS Code platform adapter selector in status bar — quick-switch between Claude Code / Cursor / Windsurf validation modes
- VS Code walkthrough for first-time users — low effort, high polish signal
- LSP inlay hints showing token count — maps to existing `ComplexityMetrics`; unique to this domain

**Defer (v2+):**
- VS Code rule documentation panel (WebviewPanel) — high UX effort; validate demand first
- LSP hover on frontmatter field names — requires field-level documentation strings not yet in `frontmatter_core.py`
- Platform-scoped MCP validation (`platform` parameter) — depends on mature adapter architecture
- Multi-platform LSP diagnostic messages — requires adapter-aware diagnostic text

**Anti-features to avoid:**
- Live schema fetching at lint time — breaks offline/sandbox environments; already rejected in PROJECT.md
- Generic Markdown prose linting — out of scope; write-good/markdownlint exist for this
- Real-time YAML frontmatter formatting — YAML round-trip is fragile; offer `--fix` only
- Persistent MCP session state — each validation is <1s; task tracking adds complexity with no benefit

### Architecture Approach

The architecture is strictly layered: `ValidationEngine` + `Validator` classes form a pure Python library with no I/O. CLI (`cli.py`), LSP server (`lsp/server.py`), and MCP server (`mcp/server.py`) are each thin wrappers that call the engine and translate results to their respective output formats. The VS Code extension is a TypeScript shell that spawns the Python LSP server over stdio. Platform adapters implement a `PlatformAdapter` Protocol, resolved by the engine and injected into validators — no platform logic lives inside validators.

**Major components:**
1. `ValidationEngine` (`engine.py`) — orchestrates validators per file type, aggregates `ValidationResult` objects; stateless, importable, no I/O
2. `Validator` classes (`validators/`) — one module per rule group; implement `validate()`, `can_fix()`, `fix()` protocol; stateless, platform-agnostic
3. `PlatformAdapter` (`platforms/`) — per-platform schema, scan patterns, docs URLs; bundled schema snapshots accessed via `importlib.resources.files()`
4. `pygls LanguageServer` (`lsp/server.py`) — translates LSP events to engine calls; incremental document sync; async with debounced lint runs
5. `FastMCP server` (`mcp/server.py`) — `@mcp.tool()` wrappers around engine functions; all logging to stderr; no stdout writes
6. VS Code Extension (TypeScript, `vscode-extension/`) — spawns Python LSP server via stdio; uses `vscode-languageclient`; no validation logic
7. Schema Snapshot Store (`skilllint/schemas/`) — JSON files inside the package, declared as package data, accessed via `importlib.resources`

### Critical Pitfalls

1. **stdout corruption in MCP STDIO server** — any `print()`, logging-to-stdout, or tiktoken download progress on stdout silently corrupts the JSON-RPC channel. Prevention: `logging.basicConfig(stream=sys.stderr)` before server starts; capture all linter output programmatically; pre-download tiktoken encodings.

2. **Package restructure must precede LSP/MCP work** — the existing monolith (`plugin_validator.py`) cannot be imported by LSP or MCP servers without dragging in CLI output side effects. Prevention: complete the package migration as a discrete phase with pre-commit integration tests before writing any LSP or MCP code.

3. **pygls v2 breaking import paths** — `LanguageServer` moved from `pygls.server` to `pygls.lsp.server`; the old module exists as a shim but fails at attribute lookup. Prevention: pin `pygls>=2.0` in pyproject.toml; use v2 import paths exclusively from day one.

4. **Full document sync produces stale diagnostics** — `TextDocumentSyncKind.Full` debounces updates; errors stay highlighted after fix; feels broken to users. Prevention: use `TextDocumentSyncKind.Incremental` from the start; use pygls workspace document management for in-memory state.

5. **0-based vs 1-based line number offset in LSP Positions** — existing validators report 1-based lines; LSP requires 0-based. Subtract 1 from all line numbers when building `Position` objects. Add a unit test with explicit offset assertion before any LSP integration testing.

6. **Wrong VS Code activation event scope** — `onLanguage:yaml` or `onLanguage:markdown` activates the extension for all YAML/Markdown files including irrelevant ones. Prevention: restrict `documentSelector` to specific file name patterns (`SKILL.md`, `AGENT.md`, `plugin.json`, etc.) before writing any LSP client code.

7. **MCP tool descriptions as prompt injection vectors** — descriptions are sent verbatim to the LLM; dynamic content (f-strings from user input) enables injection. Prevention: all `@mcp.tool` descriptions must be static strings; never interpolate user-provided content.

## Implications for Roadmap

Based on the combined research, the architecture's own build-order dependency graph directly dictates phase structure. The dependency constraint is hard: Phases 4, 5, 6, and 7 all import from `engine.py` — the package restructure (Phase 1) is a prerequisite for all of them. Phases 4 (LSP) and 6 (MCP) are independent of each other and can be parallelized after Phase 3.

### Phase 1: Package Structure and Distribution

**Rationale:** All downstream phases import from `engine.py`. Without a proper installable package, LSP and MCP servers must either duplicate validation logic or subprocess-shell to the CLI — both are documented dead ends. The PEP 723 monolith migration is also the highest-risk pitfall for existing pre-commit hook users; handling it first limits blast radius.

**Delivers:** `skilllint` Python package on PyPI; `skilllint` CLI entry point with `skilllint` and `skillint` aliases; pre-commit hook working from the packaged entry point; `uv build` producing a `.whl` with bundled schema snapshots; existing tests passing with proper package imports.

**Addresses features:** All CLI features (existing); establishes foundation for LSP, MCP, and VS Code features.

**Avoids pitfall:** Monolith-to-package migration breaking pre-commit (Pitfall 6); schema files outside the package directory (Anti-Pattern 3); `__file__`-relative resource paths broken in wheel installs.

**Research flag:** Standard patterns — this is well-documented Python packaging. No deeper research needed. Use hatchling `force-include` for schemas; `importlib.resources.files()` for runtime access.

### Phase 2: Platform Adapter Architecture

**Rationale:** Platform adapter architecture must be complete before platform-scoped LSP and MCP features. The adapter protocol also resolves the open/closed principle violation in the existing code (platform logic hardcoded in validators). Building it immediately after packaging ensures validators are refactored clean — before LSP and MCP add their own consumption patterns.

**Delivers:** `PlatformAdapter` Protocol definition; `ClaudeCodeAdapter` (migrated from existing logic); stub adapters for Cursor and Windsurf; bundled schema JSON snapshots per platform; adapter registry using `importlib.metadata.entry_points` for third-party extension (not global dict self-registration).

**Addresses features:** Foundational for multi-platform diagnostic messages, platform adapter selector in VS Code, platform-scoped MCP validation.

**Avoids pitfall:** Global adapter registry tight coupling (Pitfall 8); platform logic inline in validators (Anti-Pattern 5).

**Research flag:** Standard Protocol + entry_points pattern. The entry_points discovery mechanism is well-documented. No deeper research needed.

### Phase 3: Fix Mode and Configuration

**Rationale:** Fix mode (`--fix` flag, `can_fix()`, `fix()` protocol) is required by the LSP code actions feature — a v1 table stakes item. Configuration file parsing (`linter.toml` / `[tool.skilllint]` in pyproject.toml) is needed by the LSP configuration reload feature (also v1 table stakes). Both must be wired through the engine before LSP work begins.

**Delivers:** `--fix` flag wired through `ValidationEngine`; safe vs. unsafe fix labeling; config file parsing with live-reload support; all validators implementing `can_fix()` and `fix()` methods.

**Addresses features:** LSP code actions, "Fix all" code action, fix on save in VS Code extension.

**Avoids pitfall:** None of the major pitfalls are specific to this phase; this phase eliminates risk in Phase 4 by ensuring LSP code actions have a clean API to call.

**Research flag:** Standard patterns. No deeper research needed.

### Phase 4: LSP Server

**Rationale:** LSP server is the first new protocol surface. It depends on Phases 1-3 (package structure, platform adapters, fix mode). Phase 4 and Phase 6 (MCP) are independent and can be parallelized, but LSP should come first because it is higher complexity and the VS Code extension (Phase 5) is blocked on it.

**Delivers:** `pygls LanguageServer` subclass with incremental document sync; `textDocument/publishDiagnostics` on open/change; `textDocument/codeAction` for fixable violations; "Fix all" code action; `textDocument/hover` for rule code documentation; `workspace/didChangeWatchedFiles` for config reload; server lifecycle (initialize/shutdown/exit); `pytest-lsp` integration tests.

**Stack:** `pygls 2.0.1`, `lsprotocol 2025.0.0`, `pytest-lsp`

**Addresses features:** All LSP v1 table stakes features.

**Avoids pitfalls:** pygls v2 import paths (use `from pygls.lsp.server import LanguageServer`); incremental sync (set `TextDocumentSyncKind.Incremental`); 0-based line numbers (helper function with explicit unit test); debounced lint runs (200ms idle before triggering for files >2KB frontmatter); tiktoken singleton (initialize encoding once at server startup).

**Research flag:** LSP server patterns are well-documented via official pygls docs and the microsoft/vscode-python-tools-extension-template. The YAML frontmatter completions feature (differentiator) is genuinely novel — no ecosystem solution exists. Treat completions as a Phase 4.x follow-on, not Phase 4 scope.

### Phase 5: VS Code Extension

**Rationale:** The VS Code extension is a thin TypeScript shell that spawns the Phase 4 LSP server. It has no validation logic. It is strictly dependent on Phase 4. Building it as its own phase focuses the work on TypeScript project setup, Python process spawning, bundling, and marketplace publication — not on LSP features.

**Delivers:** TypeScript extension project scaffolded from `microsoft/vscode-python-tools-extension-template`; `vscode-languageclient` spawning `python -m skilllint.lsp.server` over stdio; diagnostics in Problems panel and squiggles in editor; quick fix lightbulb and fix on save; extension settings in Settings UI; status bar server indicator; workspace trust declaration; `.vsix` packaging via `@vscode/vsce`; VS Code Marketplace listing.

**Stack:** `vscode-languageclient 9.0.1`, `@types/vscode`, `esbuild`, `@vscode/vsce`

**Addresses features:** All VS Code Extension v1 table stakes.

**Avoids pitfalls:** Wrong activation event scope (restrict `documentSelector` to skill/agent/plugin file patterns before writing any client code); VSIX version collision (automate version bump in CI before VSIX generation); async Python process spawn (use `vscode-languageclient`'s lazy start patterns).

**Research flag:** Well-documented pattern. Follow `microsoft/vscode-python-tools-extension-template` exactly for project structure and Python process spawning. No deeper research needed.

### Phase 6: MCP Server

**Rationale:** MCP server is independent of Phases 4 and 5 and can be parallelized with them after Phase 3. It is sequenced here because it depends on Phase 2 (platform adapters) and Phase 3 (fix mode) being complete for full feature coverage. The MCP server is also the lower-complexity new surface — all tools are thin wrappers over `engine.py` functions.

**Delivers:** `FastMCP` server with `validate_skill`, `validate_agent`, `validate_plugin`, `query_schema`, `list_rules` tools; all tools returning structured JSON; all logging redirected to stderr; path traversal protection on tool arguments; static tool descriptions (no f-strings); MCP Inspector verified before integration.

**Stack:** `fastmcp 3.0.2`

**Addresses features:** All MCP Server v1 table stakes.

**Avoids pitfalls:** stdout corruption (stderr-only logging enforced from day one, tested with MCP Inspector); prompt injection via tool descriptions (static strings only, code-reviewed before ship); path traversal (allowed root validation on all path arguments); tiktoken pre-download (suppress progress output via `TIKTOKEN_CACHE_DIR`).

**Research flag:** FastMCP tool wrapping is well-documented. The security considerations (prompt injection, path traversal) are not standard onboarding content — review Simon Willison's MCP prompt injection analysis before finalizing tool descriptions and input validation.

### Phase 7: Claude Code .plugin

**Rationale:** The `.plugin` packaging format bundles the MCP server, skill definition, and agent definition into a Claude Code distributable. It depends on Phase 6 (MCP server is deployable) and on the MCP server being addressable via `uvx skilllint-mcp` or `uv run -m skilllint.mcp`. This is the final distribution artifact.

**Delivers:** `plugin.json` and `marketplace.json` for Claude Code plugin registry; `skilllint-mcp` console script entry point; verified end-to-end install via `uv tool install skilllint`; Claude Code plugin activates MCP server correctly.

**Addresses features:** Claude Code .plugin distribution.

**Research flag:** Claude Code .plugin format is less documented than PyPI and VS Code Marketplace. May need a focused research pass on the `.plugin` YAML frontmatter spec and marketplace submission process before this phase executes.

### Phase Ordering Rationale

- Phase 1 (package structure) is a hard prerequisite for all other phases — without it, nothing can import from `engine.py`
- Phase 2 (platform adapters) must precede any platform-scoped features in Phases 4 and 6; also resolves the open/closed violation before LSP/MCP consumption patterns are added
- Phase 3 (fix mode + config) must precede Phase 4 (LSP) because LSP code actions require `can_fix()` / `fix()` APIs
- Phase 4 (LSP) and Phase 6 (MCP) are independent after Phase 3; can be parallelized with separate agents
- Phase 5 (VS Code extension) is strictly after Phase 4 — it only spawns the LSP server
- Phase 7 (.plugin) is strictly after Phase 6 — it packages the MCP server

### Research Flags

Phases needing deeper research during planning:
- **Phase 7 (.plugin):** Claude Code `.plugin` format and marketplace submission process are less documented than PyPI/VS Code Marketplace; dedicated research pass recommended before this phase
- **Phase 4.x (LSP completions):** YAML frontmatter completions in Markdown files are a genuine ecosystem gap with no established pattern; needs original research when ready to implement

Phases with standard patterns (skip research-phase):
- **Phase 1:** Python packaging with hatchling and `importlib.resources` — authoritative official docs
- **Phase 2:** Protocol + entry_points adapter pattern — standard Python patterns
- **Phase 3:** Fix mode and config parsing — existing validator patterns extend cleanly
- **Phase 4:** LSP server with pygls — microsoft/vscode-python-tools-extension-template is the reference
- **Phase 5:** VS Code extension — same template; well-documented Marketplace publication
- **Phase 6:** FastMCP tool wrapping — well-documented; security review of tool descriptions is the non-standard element

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technology choices verified against official docs, PyPI, and GitHub releases. pygls 2.0.1, fastmcp 3.0.2, vscode-languageclient 9.0.1 are current stable releases. |
| Features | MEDIUM | LSP and VS Code patterns verified against ruff and regal official docs. MCP patterns verified against MCP spec and SonarQube MCP server. YAML frontmatter completions gap is confirmed from GitHub issues but sparse. |
| Architecture | HIGH (LSP/VS Code), MEDIUM (MCP, adapter) | LSP and VS Code architecture verified via official Microsoft template and ruff-lsp deprecation discussion. MCP and platform adapter patterns are community consensus, not single authoritative source. |
| Pitfalls | MEDIUM-HIGH | LSP pitfalls (v2 imports, sync kind, line offsets) verified via official pygls docs and LSP spec. MCP stdout corruption verified via multiple community sources. Security pitfalls (prompt injection) from credible single sources. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **LSP YAML frontmatter completions:** No existing LSP solution handles YAML frontmatter inside `.md` files with custom schema. Confirmed ecosystem gap from GitHub issues (vscode-yaml, Zed). When this feature enters roadmap planning, it will need original research and likely a prototype to estimate complexity correctly.

- **Claude Code .plugin format spec:** The exact YAML frontmatter structure and marketplace submission requirements for the `.plugin` format are less documented than other distribution targets. Needs a targeted research pass before Phase 7 planning.

- **Conflict with redhat.vscode-yaml:** The VS Code extension's frontmatter completions must handle the range exclusively rather than claiming the entire `.md` file, to avoid conflicts with users who have `redhat.vscode-yaml` installed. The exact document selector pattern for frontmatter-only range needs validation against the LSP spec during Phase 4 planning.

- **tiktoken stdout on first run:** tiktoken writes download progress to stdout on first use. Suppression mechanism via `TIKTOKEN_CACHE_DIR` and pre-download at install time is the stated approach, but needs verification that all output paths are captured in both LSP and MCP server contexts.

## Sources

### Primary (HIGH confidence)
- pygls 2.0.1 documentation (https://pygls.readthedocs.io/) — version, Python requirements, lsprotocol dependency, feature decorators, v2 migration guide
- pygls GitHub (https://github.com/openlawlibrary/pygls) — release history, v2.0.0 October 2025
- lsprotocol PyPI (https://pypi.org/project/lsprotocol/2025.0.0) — version 2025.0.0
- fastmcp PyPI (https://pypi.org/project/fastmcp/) — 3.0.2, Python >=3.10
- FastMCP documentation (https://gofastmcp.com/) — 3.0 GA, tool decorator pattern
- FastMCP 3.0 GA announcement (https://www.jlowin.dev/blog/fastmcp-3-launch) — stable release, January 2026
- VS Code Language Server Extension Guide (https://code.visualstudio.com/api/language-extensions/language-server-extension-guide) — extension architecture, stdio transport
- microsoft/vscode-python-tools-extension-template (https://github.com/microsoft/vscode-python-tools-extension-template) — bundled/libs pattern, TypeScript + pygls architecture
- VS Code Bundling Extensions (https://code.visualstudio.com/api/working-with-extensions/bundling-extension) — esbuild recommendation
- Python Packaging User Guide (https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — package data configuration
- Hatchling build configuration (https://hatch.pypa.io/1.13/config/build/) — force-include syntax
- importlib.resources Python 3.11 stdlib (https://docs.python.org/3/library/importlib.resources.html) — files() API
- LSP specification 3.17 (https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/) — protocol requirements, sync kinds, position encoding
- VS Code activation events (https://code.visualstudio.com/api/references/activation-events) — activation scope pitfalls
- MCP Python SDK (https://github.com/modelcontextprotocol/python-sdk) — official repo
- MCP build server guide (https://modelcontextprotocol.io/docs/develop/build-server) — official protocol docs
- MCP Pydantic v2 compatibility bug (https://github.com/modelcontextprotocol/python-sdk/issues/1513) — confirmed issue
- Python packaging entry points (https://packaging.python.org/en/latest/specifications/entry-points/) — adapter discovery

### Secondary (MEDIUM confidence)
- Ruff editor features documentation (https://docs.astral.sh/ruff/editors/features/) — LSP feature comparison
- Ruff VS Code extension (https://github.com/astral-sh/ruff-vscode) — bundling and activation patterns
- Ruff v0.4.5 native server announcement (https://astral.sh/blog/ruff-v0.4.5) — subprocess vs library integration rationale
- Regal language server features (https://docs.styra.com/regal/language-server) — feature comparison for completions, code lenses
- SonarQube MCP server tools (https://docs.sonarsource.com/sonarqube-mcp-server/tools) — MCP tool design patterns
- MCP STDIO stdout corruption (https://github.com/ruvnet/claude-flow/issues/835) — community-verified
- MCP tips/pitfalls Nearform (https://nearform.com/digital-community/implementing-model-context-protocol-mcp-tips-tricks-and-pitfalls/) — community source
- MCP security vulnerabilities (https://strobes.co/blog/mcp-model-context-protocol-and-its-critical-vulnerabilities/) — security research
- LSP incremental vs full sync (https://steve.dignam.xyz/2025/07/14/lsp-server-sync/) — corroborated by LSP spec
- ruff-lsp deprecation discussion (https://github.com/astral-sh/ruff/discussions/15991) — subprocess limitations
- Existing codebase CONCERNS.md — direct code audit, HIGH confidence for existing code state

### Tertiary (LOW confidence)
- YAML frontmatter LSP gap in Zed (https://github.com/zed-industries/zed/issues/43444) — confirms ecosystem gap; single source
- vscode-yaml frontmatter issue (https://github.com/redhat-developer/vscode-yaml/issues/207) — confirms gap; single source
- MCP prompt injection (https://simonwillison.net/2025/Apr/9/mcp-prompt-injection/) — credible single source; no independent verification

---
*Research completed: 2026-03-02*
*Ready for roadmap: yes*
