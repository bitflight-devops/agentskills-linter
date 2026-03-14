# skilllint

## What This Is

`skilllint` is a ruff-inspired linter for AI agent plugins, skills, and agents across platforms (Claude Code, Codex, Cursor, Windsurf, and others). It validates schema correctness, enforces best practices via numbered rule codes, and auto-fixes violations. Platform support is delivered via pluggable adapters bundled with the tool. Ships as a Python package (`pip`/`uv`), a Claude Code `.plugin`, a `.skill`, and as part of an LSP + VS Code extension + MCP server ecosystem.

## Core Value

An AI agent or developer who creates a plugin/skill/agent gets instant, actionable feedback — in their editor, in CI, and from the AI itself — before their work ever ships broken.

## Requirements

### Validated

- ✓ Plugin/skill/agent frontmatter validation — existing
- ✓ Rule-code error system (SK001–SK007+, PR001–PR004, etc.) — existing
- ✓ CLI entry point via `uv run plugin_validator.py` — existing
- ✓ Pydantic-based schema models for Claude Code (SkillFrontmatter, AgentFrontmatter, CommandFrontmatter) — existing
- ✓ Round-trip YAML preservation on fixes — existing
- ✓ Pre-commit hook integration — existing
- ✓ Token-based complexity measurement (tiktoken) — existing
- ✓ pytest test suite with fixture infrastructure — existing

### Active

- [ ] `pyproject.toml` + proper Python package structure for `packages/skilllint`
- [ ] Platform adapter architecture — pluggable adapters for Claude Code, Cursor, and Codex (initial bundled adapters); see `.claude/vendor/CLAUDE.md` for all supported platforms
- [ ] Bundled schema snapshots — versioned schemas shipped with the package, updatable on release
- [ ] Named CLI entry points: `skilllint` (primary), `agentlint`, `pluginlint`, `skillint` (aliases)
- [ ] Fix mode — auto-fix violations where safe, report-only otherwise
- [ ] LSP server — diagnostics + schema-aware completions for frontmatter fields
- [ ] VS Code extension — surfaces LSP diagnostics and completions in editor
- [ ] MCP server — `validate_*`, `query_schema`, `scaffold_plugin/skill/agent` tools for AI self-validation
- [ ] Claude Code `.plugin` — installs MCP server + skill + agent into Claude Code
- [ ] Distributable as `.whl`, `.skill`, and `.plugin`
- [ ] `linter.toml` / `pyproject.toml [tool.skilllint]` config support — per-rule enable/disable, per-file overrides

### Out of Scope

- Live schema fetching at lint time — schemas are bundled snapshots, not fetched on demand; reduces fragility in offline/sandbox environments
- Speed/performance as a design goal (Rust rewrite) — Python + uv run is sufficient for current scale
- Mobile or web UI — CLI + LSP + VS Code covers the target surfaces

## Context

The `packages/skilllint/` directory contains the existing validator implementation: `plugin_validator.py` (CLI + validation framework), `frontmatter_core.py` (Pydantic models), `frontmatter_utils.py` (YAML I/O), and `auto_sync_manifests.py` (manifest sync tool). There are 9 open GitHub issues (#3–#11) and a 25-task implementation plan at `docs/plans/tasks-1-plugin-linter/`. Tasks 12–14 are already fixed. The package currently has no `pyproject.toml` and is run as PEP 723 standalone scripts.

The tool is the `skilllint` repo and package/CLI. Aliases `agentlint`, `pluginlint`, `skillint` should all invoke the same binary.

## Constraints

- **Language**: Python 3.11+ — matches existing codebase, no Rust rewrite
- **Package manager**: `uv` — existing toolchain, PEP 723 inline deps in scripts
- **Platform adapters**: Bundled snapshots only — no live fetching of upstream schemas
- **Claude Code .plugin**: Installs into Claude Code only (not generic agent install)
- **Distribution**: Must ship as `.whl`, `.skill`, and `.plugin`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Pluggable adapter architecture for platform support | Platform-agnostic core keeps the linter useful as new AI agent platforms emerge | — Pending |
| Bundled schema snapshots (not live fetch) | Offline/sandbox reliability; deterministic validation across environments | — Pending |
| `skilllint` as primary CLI name | Platform-agnostic name; aliases cover legacy and alternative spellings | — Pending |
| Ruff-style rule codes (e.g. SK001, PR003) | Familiar pattern for Python devs; enables per-rule configuration | ✓ Good — already implemented |
| LSP + VS Code extension (not standalone GUI) | Integrates into existing dev workflows without separate tool | — Pending |

---
*Last updated: 2026-03-02 after initialization*
