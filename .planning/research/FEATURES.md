# Feature Research

**Domain:** Python linter developer tooling — LSP server, VS Code extension, MCP server for AI agent plugin/skill linting
**Researched:** 2026-03-02
**Confidence:** MEDIUM — LSP and VS Code patterns verified against ruff, pylsp, regal official docs; MCP patterns verified against MCP spec and SonarQube MCP server; YAML-in-markdown frontmatter completions is an active gap in the ecosystem

---

## Context: What skilllint's New Components Must Do

The existing skilllint core validates AI agent plugin/skill YAML frontmatter and emits typed rule codes (SK001–SK009, FM001–FM010, etc.). The three new surface areas each serve a different consumer:

- **LSP server** — serves editors (Neovim, Helix, Zed, any LSP-capable editor)
- **VS Code extension** — wraps the LSP in a VS Code-specific UX package
- **MCP server** — serves AI agents that want to self-validate or query schemas before creating plugins

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or unshippable.

#### LSP Server

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Publish diagnostics on open/change | Every LSP linter does this; users see squiggles immediately | LOW | Use `textDocument/publishDiagnostics`; maps directly to existing ValidationResult objects |
| Code actions for fixable diagnostics | Ruff, regal, eslint-lsp all provide lightbulb quick-fixes | LOW-MEDIUM | `textDocument/codeAction`; only for issues where `can_fix()` is True in existing validators |
| "Fix all auto-fixable issues" code action | Ruff and ESLint VS Code extensions both expose this; users expect batch apply | MEDIUM | Single code action that applies all safe fixes in the document |
| Hover on rule code (e.g. SK003) | Ruff LSP provides rule documentation on hover over noqa comments; users expect inline docs | LOW | `textDocument/hover`; return rule description + docs URL from existing `generate_docs_url()` |
| Configuration reload on file change | Ruff, regal both watch `pyproject.toml`/config for changes; users expect live reload | LOW-MEDIUM | File watching via `workspace/didChangeWatchedFiles`; reload `linter.toml` or `[tool.skilllint]` |
| Diagnostics cleared on file delete | File deleted → diagnostics must disappear; otherwise ghost errors appear | LOW | Send empty diagnostics array when file is deleted |
| Server lifecycle (initialize/shutdown) | Protocol requirement; clients disconnect if server doesn't handle these | LOW | `initialize`, `initialized`, `shutdown`, `exit` — mandatory per LSP spec 3.17 |
| Capability negotiation | Server must advertise what it supports; clients adapt accordingly | LOW | Return `ServerCapabilities` in `initialize` response |

#### VS Code Extension

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Diagnostics in Problems panel | Standard VS Code linter UX; ruff, pylance, eslint all do this | LOW | Flows automatically from LSP diagnostics |
| Squiggly underlines on violations | Visual feedback in editor; users expect this for any linter | LOW | Flows from LSP diagnostics |
| Quick fix lightbulb in editor | Ruff VS Code extension provides this; users expect it | LOW | Flows from LSP code actions |
| "Fix all" command in command palette | Ruff VS Code provides `source.fixAll`; eslint does too | LOW | Register as `source.fixAll.skilllint` code action kind |
| Fix on save option | Ruff and ESLint VS Code both expose `editor.codeActionsOnSave`; users configure this | LOW | `source.fixAll.skilllint` triggered on `editor.codeActionsOnSave` |
| Extension settings in VS Code settings UI | Users expect to configure enable/disable, executable path, etc. from Settings UI | LOW | Declare `contributes.configuration` in `package.json` |
| Status bar server indicator | Ruff VS Code shows language server status; users want to know if it's running | LOW | Shows running/error state; helps debug activation issues |
| Extension marketplace listing with icon | Users discover via marketplace; no icon = unpolished | LOW | Requires icon asset and good `README.md` |
| Workspace trust support | VS Code requires extensions to declare untrusted workspace behavior | LOW | Declare in `package.json`; restrict to read-only diagnostics in untrusted workspaces |

#### MCP Server

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `validate_skill` tool | Core value proposition; AI agent validates a skill before creating it | LOW | Thin wrapper over existing CLI validator |
| `validate_agent` tool | Same as above for agent frontmatter | LOW | Same wrapper pattern |
| `validate_plugin` tool | Same for plugin.json | LOW | Same wrapper pattern |
| `query_schema` tool | AI needs to know what fields are required before authoring | LOW | Returns Pydantic model schema as JSON; driven by existing `frontmatter_core.py` models |
| Structured error output (JSON) | AI agents cannot parse prose; need machine-readable results | LOW | Existing `--format json` output maps directly |
| Tool descriptions + parameter schemas | MCP clients use these for tool discovery; must be accurate | LOW | Required by MCP spec for tool registration |
| MCP `initialize` handshake | Protocol requirement; every MCP server must implement | LOW | Server info, protocol version, capabilities |

---

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued by target users.

#### LSP Server

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| YAML frontmatter completions in Markdown files | No existing LSP handles YAML frontmatter *inside* `.md` files with custom schema; yamlls doesn't cover frontmatter in markdown (open issue in vscode-yaml, zed as of Nov 2025) | HIGH | Requires custom LSP text sync handler that detects frontmatter block and provides field name/value completions from Pydantic models; biggest differentiator |
| Field value completions (enum fields) | Completing `tools:` with known tool names, `color:` with valid colours — specific to skilllint schemas | MEDIUM | Requires schema introspection from `frontmatter_core.py` registered models |
| Hover on frontmatter field names | Inline documentation for each frontmatter field (what it means, valid values) | MEDIUM | `textDocument/hover` triggered on frontmatter field names, not just rule codes |
| Safe vs. unsafe fix labeling | Ruff introduced safe/unsafe distinction; users benefit from knowing which fixes are safe to auto-apply | LOW | Already modelled in validator; surface via `preferred` flag on code action |
| Multi-platform adapter diagnostics | Emit platform-specific context in diagnostic messages (e.g., "This field is required for Claude Code agents but optional for Cursor") | MEDIUM | Requires adapter-aware messaging in ValidationResult |
| Inlay hints for token count | Show token count inline next to skill body; directly maps to existing `ComplexityMetrics` | MEDIUM | `textDocument/inlayHint`; requires LSP 3.17 inlay hint support |

#### VS Code Extension

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Bundled binary (no separate install) | Ruff VS Code bundles ruff; users expect zero-config install — no `pip install` required | MEDIUM | Bundle `skilllint` wheel or use subprocess to `uvx` on first run |
| Platform adapter selector in status bar | Quick-switch between Claude Code / Cursor / Windsurf validation modes | MEDIUM | Dropdown in status bar; persists per workspace |
| Walkthrough for first-time users | VS Code walkthroughs API (`workbench.action.openWalkthrough`) guides new users through setup | LOW | Low effort, high polish signal; VS Code recommends this for extensions |
| Scaffold command from command palette | "skilllint: New Skill" / "skilllint: New Agent" generates skeleton file | MEDIUM | Calls MCP `scaffold_skill` or generates template inline |
| Rule code documentation panel | Click a diagnostic → open a side panel with full rule documentation | MEDIUM | WebviewPanel showing rule docs; Ruff doesn't have this, would be a visible differentiator |

#### MCP Server

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `scaffold_skill` tool | AI agent can generate a valid skeleton skill file; avoids common frontmatter errors from scratch | LOW-MEDIUM | Returns YAML string; schema-driven from Pydantic models |
| `scaffold_agent` tool | Same for agent frontmatter | LOW | Same pattern |
| `scaffold_command` tool | Same for command frontmatter | LOW | Same pattern |
| `list_rules` tool | AI agent queries all rule codes with descriptions; enables self-aware validation guidance | LOW | Enumerates existing rule registry |
| `get_rule_detail` tool | AI agent looks up a specific rule code's documentation, examples, fix availability | LOW | Maps to existing `generate_docs_url()` + rule metadata |
| Platform-scoped validation | `validate_skill(path, platform="cursor")` uses the Cursor adapter schema — AI gets platform-specific errors | MEDIUM | Requires adapter architecture to be complete first |

---

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Go-to-definition for frontmatter fields | Developers ask for "jump to schema definition" | frontmatter fields aren't code symbols; there's no definition location to jump to | Hover documentation covers the information need |
| Full code completions for skill body content | Developers want completions in the Markdown prose body | The body is free-form Markdown prose, not structured; completions would require an LLM and would conflict with existing Markdown LSP | Keep completions limited to YAML frontmatter block only |
| Live schema fetching from upstream platforms | Users want the latest Claude Code / Cursor schemas | Breaks in offline/sandbox environments; introduces network dependency at lint time; already decided against in PROJECT.md | Bundled schema snapshots, updatable on package release |
| Real-time formatting of YAML frontmatter | "Format on save" for the frontmatter block | Risks breaking user-intentional formatting; YAML round-trip is fragile; current code already handles this carefully with ruamel.yaml | Offer explicit `--fix` only, not auto-format |
| Generic Markdown linting (prose, spelling) | Users want one extension for everything in a skill file | Out of scope; write-good, markdownlint, vale already exist; building it pulls focus from the core value prop | Recommend complementary extensions; don't bundle prose linting |
| Persistent MCP session state / job tracking | MCP 2025 spec supports tasks and long-running operations | Each validation request is fast (<1s); task tracking adds complexity with no benefit | Synchronous tools; all validation is request/response |
| GUI config editor (sidebar tree view) | Users want a visual config editor for rule enable/disable | High complexity, fragile UX, rarely used once initial setup is done | Settings UI via VS Code `contributes.configuration` covers the need cleanly |
| Auto-update schema snapshots at runtime | Users want snapshots updated automatically | Same as live fetching; breaks determinism; offline environments break | Ship updated snapshots in new package releases |

---

## Feature Dependencies

```
[LSP server core (diagnostics)]
    └──required by──> [VS Code extension diagnostics]
    └──required by──> [VS Code extension code actions]
    └──required by──> [VS Code extension hover]

[Validator Protocol (can_fix)]
    └──required by──> [LSP code actions]
    └──required by──> [MCP validate_* tools]

[frontmatter_core.py Pydantic models]
    └──required by──> [LSP YAML completions]
    └──required by──> [MCP query_schema tool]
    └──required by──> [MCP scaffold_* tools]

[Platform adapter architecture (Active milestone)]
    └──required by──> [Platform-scoped validation in MCP]
    └──required by──> [Platform adapter selector in VS Code]
    └──required by──> [Multi-platform diagnostic messages in LSP]

[LSP inlay hints]
    └──requires──> [LSP 3.17 inlay hint capability]
    └──requires──> [Editor client support for inlayHint]

[MCP scaffold_* tools]
    └──enhances──> [VS Code scaffold command]
    (VS Code extension can delegate scaffold to MCP server instead of duplicating logic)

[Bundled binary in VS Code]
    └──requires──> [pyproject.toml package structure (Active milestone)]
    └──requires──> [Named CLI entry points: skilllint (Active milestone)]
```

### Dependency Notes

- **Platform adapter architecture must be complete before** platform-scoped LSP/MCP features: the LSP and MCP servers can be built against the core validator first, then gain adapter-specific features once the adapter architecture lands.
- **VS Code extension completions are the highest complexity item** and depend on custom text sync logic not available off-the-shelf; treat as a Phase 2+ feature.
- **MCP scaffold tools are low complexity** and do not depend on the adapter architecture — they can use the default (Claude Code) schema immediately.
- **LSP YAML frontmatter completions conflict with standard YAML LSP**: users often have `redhat.vscode-yaml` installed; the extension must handle the frontmatter range exclusively rather than claiming the entire `.md` file.

---

## MVP Definition

### Launch With (v1 — per component)

**LSP Server v1:**
- [ ] Diagnostics on open/change — why essential: core value, without this the LSP is useless
- [ ] Code actions for fixable diagnostics — why essential: table stakes; users expect lightbulb
- [ ] "Fix all" code action — why essential: batch fixing is the primary efficiency gain
- [ ] Hover on rule codes — why essential: inline documentation removes context switching
- [ ] Configuration reload on file change — why essential: without this, rule config changes require restarting the server
- [ ] Server lifecycle (initialize/shutdown/exit) — why essential: protocol requirement

**VS Code Extension v1:**
- [ ] Diagnostics in Problems panel + squiggles — why essential: primary UX surface
- [ ] Quick fix lightbulb — why essential: table stakes for any VS Code linter
- [ ] Fix all / fix on save — why essential: users configure this immediately on install
- [ ] Extension settings (enable/disable, executable path) — why essential: users in monorepos need per-workspace config
- [ ] Status bar indicator — why essential: debugging activation without it is frustrating
- [ ] Workspace trust declaration — why essential: VS Code rejects extensions that don't declare this

**MCP Server v1:**
- [ ] `validate_skill`, `validate_agent`, `validate_plugin` tools — why essential: core value proposition for AI consumers
- [ ] `query_schema` tool — why essential: AI agents need to know what's valid before authoring
- [ ] `list_rules` tool — why essential: enables AI agents to explain violations and guide fixes
- [ ] Structured JSON output — why essential: AI agents cannot parse prose error messages

### Add After Validation (v1.x)

- [ ] LSP YAML frontmatter completions — trigger: user feedback that completion is the #1 missing feature; high complexity, defer until core is stable
- [ ] MCP `scaffold_skill/agent/command` tools — trigger: MCP v1 deployed; add as fast follow (low complexity)
- [ ] VS Code platform adapter selector — trigger: platform adapter architecture milestone is complete
- [ ] VS Code walkthrough — trigger: marketplace publish; walkthrough improves first-run experience
- [ ] LSP inlay hints for token count — trigger: after v1 LSP is stable; confirms LSP 3.17 support in target editors

### Future Consideration (v2+)

- [ ] VS Code rule documentation panel (WebviewPanel) — why defer: high UX polish effort; validate that users want inline docs before building a panel
- [ ] LSP hover on frontmatter field names — why defer: requires field-level documentation strings not yet in `frontmatter_core.py`; authoring content is non-trivial
- [ ] Platform-scoped validation in MCP (`platform` parameter) — why defer: depends on adapter architecture being mature
- [ ] Multi-platform LSP diagnostic messages — why defer: requires adapter-aware diagnostic text; scope after adapters are settled
- [ ] Debug adapter protocol (like regal) — why defer: skill/plugin validation doesn't have a "run" concept; DAP is only relevant if skilllint gains execution features

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| LSP diagnostics | HIGH | LOW | P1 |
| LSP code actions (fix) | HIGH | LOW | P1 |
| LSP hover on rule codes | HIGH | LOW | P1 |
| LSP configuration reload | HIGH | LOW | P1 |
| VS Code diagnostics + squiggles | HIGH | LOW | P1 |
| VS Code quick fix lightbulb | HIGH | LOW | P1 |
| VS Code fix on save | HIGH | LOW | P1 |
| VS Code extension settings | MEDIUM | LOW | P1 |
| MCP validate_skill/agent/plugin | HIGH | LOW | P1 |
| MCP query_schema | HIGH | LOW | P1 |
| MCP list_rules | MEDIUM | LOW | P1 |
| VS Code status bar indicator | MEDIUM | LOW | P1 |
| MCP scaffold_* tools | MEDIUM | LOW | P2 |
| VS Code walkthrough | MEDIUM | LOW | P2 |
| LSP inlay hints (token count) | MEDIUM | MEDIUM | P2 |
| VS Code platform adapter selector | HIGH | MEDIUM | P2 (after adapters) |
| LSP YAML frontmatter completions | HIGH | HIGH | P2 (Phase 2) |
| VS Code rule docs panel | MEDIUM | HIGH | P3 |
| LSP hover on frontmatter field names | MEDIUM | MEDIUM | P3 |
| Platform-scoped MCP validation | MEDIUM | MEDIUM | P3 (after adapters) |

**Priority key:**
- P1: Must have for component launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | ruff (LSP + VS Code) | regal (LSP + VS Code) | Our Approach |
|---------|----------------------|-----------------------|--------------|
| Diagnostics | YES — squiggles, Problems panel | YES | YES — maps to ValidationResult |
| Code actions / quick fix | YES — safe/unsafe labeled | YES | YES — use can_fix() |
| Fix on save | YES — `source.fixAll.ruff` | YES | YES — `source.fixAll.skilllint` |
| Hover docs | YES — rule docs on noqa hover | YES | YES — rule code hover |
| Completions | NO — ruff explicitly does not provide completions | YES — context-aware Rego completions | YAML frontmatter completions — but only in frontmatter block, not whole file |
| Code lenses | NO | YES — evaluate rule in editor | NO in v1 |
| Debug adapter | NO | YES | NO — not applicable |
| Inlay hints | NO | NO | YES (v1.x) — token count is unique to our domain |
| Bundled binary | YES — ships with ruff | YES — ships with regal | YES — goal to bundle `skilllint` wheel |
| MCP server | NO | NO | YES — first-mover; no comparable tool has an MCP server |
| AI scaffold tools | NO | NO | YES — differentiator for AI-first workflow |
| Platform adapter selector | NO | NO | YES — unique to multi-platform linting |

---

## Sources

- Ruff editor features documentation: https://docs.astral.sh/ruff/editors/features/ (MEDIUM confidence — WebSearch verified against official astral.sh docs)
- Ruff VS Code extension: https://github.com/astral-sh/ruff-vscode (MEDIUM confidence — WebSearch verified against official repo)
- ruff-lsp deprecation / native server: https://github.com/astral-sh/ruff/discussions/15991 (MEDIUM confidence — WebSearch)
- Regal language server features: https://docs.styra.com/regal/language-server (MEDIUM confidence — WebSearch verified against official Styra docs)
- python-lsp-server: https://github.com/python-lsp/python-lsp-server (MEDIUM confidence — WebSearch)
- LSP specification 3.17: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/ (HIGH confidence — official spec)
- SonarQube MCP server tools: https://docs.sonarsource.com/sonarqube-mcp-server/tools (MEDIUM confidence — WebSearch verified against official Sonar docs)
- MCP protocol spec 2025-11-25: https://modelcontextprotocol.io/specification/2025-11-25 (HIGH confidence — official spec)
- YAML frontmatter LSP gap (zed issue Nov 2025): https://github.com/zed-industries/zed/issues/43444 (LOW confidence — single source; confirms ecosystem gap)
- vscode-yaml frontmatter issue: https://github.com/redhat-developer/vscode-yaml/issues/207 (LOW confidence — single source; confirms gap)
- Ruff v0.4.5 native server announcement: https://astral.sh/blog/ruff-v0.4.5 (MEDIUM confidence — official blog)

---

*Feature research for: skilllint LSP + VS Code extension + MCP server*
*Researched: 2026-03-02*
