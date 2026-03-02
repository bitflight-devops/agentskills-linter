# Stack Research

**Domain:** Python linter with LSP server, MCP server, VS Code extension, and .whl distribution
**Researched:** 2026-03-02
**Confidence:** MEDIUM-HIGH (LSP/MCP: HIGH via official docs and PyPI; VS Code extension: HIGH via official MS template; package distribution: HIGH via Python Packaging Authority)

---

## Context: What Is Already Decided

The following are locked in by the existing codebase. Do not revisit these.

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime — existing constraint |
| uv | latest | Package manager and script runner |
| Pydantic | 2.0+ | Schema validation models |
| Typer | 0.21.0+ | CLI framework |
| ruamel.yaml | 0.18.0+ | Round-trip YAML parsing |
| tiktoken | 0.8.0+ | Token complexity measurement |
| Rich | latest | Terminal output |
| pytest | latest | Test suite |

This research covers **only the four new technology dimensions**: LSP server, MCP server, VS Code extension, and Python package distribution.

---

## Recommended Stack: New Additions

### LSP Server (Python)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pygls | 2.0.1 | Language Server Protocol implementation | The standard Python LSP library. Maintained by Open Law Library. v2.0 adds lsprotocol 2025.x with LSP 3.18 type support. Used by Microsoft's own Python tools extension template. |
| lsprotocol | 2025.0.0 | LSP type definitions | Auto-installed as pygls dependency. Provides typed LSP protocol objects (CompletionItem, Diagnostic, Position, etc.). Do not import from pygls internals — always import from lsprotocol.types. |
| pytest-lsp | latest | End-to-end LSP server testing | From the same maintainers as pygls. Spawns the server as a subprocess (same as VS Code would) and tests over stdio. Pairs with existing pytest suite. |

**Why pygls over alternatives:**
- The only actively maintained Python LSP framework in 2025/2026
- Microsoft's `vscode-python-tools-extension-template` uses it as the reference pattern
- Supports async, stdio, and TCP transports
- v2.0 removed Pydantic dependency (was a source of version conflicts) — no conflict with existing Pydantic 2.x usage

**What pygls provides for this project:**
- `@server.feature(TEXT_DOCUMENT_DID_OPEN)` handlers for document sync
- `@server.feature(TEXT_DOCUMENT_COMPLETION)` for frontmatter field completions
- `@server.feature(TEXT_DOCUMENT_DIAGNOSTIC)` for validation diagnostics
- Document store (`server.workspace.get_text_document(uri)`) — returns the full file text

**Minimum supported Python:** 3.9+ (project uses 3.11+ — no conflict)

### MCP Server (Python)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| fastmcp | 3.0.2 | MCP server framework | The dominant Python MCP implementation. 3.0 is stable (GA January 2026). Downloads 1M/day. Powers 70% of MCP servers across all languages per author claim. Functions stay callable Python — not wrapped into opaque objects as in v2. |

**Why fastmcp over `mcp` (official SDK):**
- FastMCP 1.0 was incorporated into the official SDK, but the standalone project (now under PrefectHQ) is more actively maintained and has more features
- FastMCP 3.0 adds OpenTelemetry, provider/transform architecture, and granular authorization not present in the official SDK's bundled version
- Decorator pattern is clean: `@mcp.tool` on a plain Python function. No boilerplate.
- `uv add fastmcp` — integrates with existing uv toolchain

**Requires:** Python >=3.10 — compatible with project's 3.11+

**FastMCP patterns for this project:**
```python
from fastmcp import FastMCP
mcp = FastMCP("skilllint")

@mcp.tool
def validate_skill(content: str) -> dict:
    """Validate a skill YAML frontmatter and return diagnostics."""
    ...

@mcp.tool
def query_schema(platform: str, field: str) -> dict:
    """Return schema definition for a frontmatter field."""
    ...

@mcp.tool
def scaffold_skill(name: str, description: str, platform: str = "claude") -> str:
    """Generate a skeleton skill/plugin YAML with correct frontmatter."""
    ...
```

### VS Code Extension (TypeScript)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| vscode-languageclient | 9.0.1 | LSP client in the extension | Microsoft's official npm package for VS Code extensions talking to an LSP server. The only correct option — it is the VS Code LSP client API. |
| @types/vscode | latest | VS Code extension API types | Required TypeScript typings for VS Code extension development. Version should match `engines.vscode` in package.json. |
| esbuild | latest | Bundle extension TypeScript to single JS file | Faster than webpack (50s → <1s build). VS Code official docs and generator-code both support esbuild. Bundling is required for VS Code Web (github.dev, vscode.dev). |
| @vscode/vsce | latest | Package and publish .vsix | The official VS Code extension packaging CLI. Required to build a `.vsix` file for distribution. |
| yo + generator-code | latest | Scaffold new extension | Microsoft's official scaffolding tool — creates correct package.json structure with activation events, contributes, etc. Use once for scaffolding, then discard. |

**Extension architecture (Microsoft template pattern):**

The VS Code extension is a thin TypeScript shell. It:
1. Detects the Python interpreter (using ms-python.python extension API if available, else system python)
2. Spawns `skilllint --lsp` as a subprocess over stdio
3. Forwards all LSP traffic via `vscode-languageclient`
4. Bundles its Python dependencies in `bundled/libs/` — pip-installed at build time into the extension directory

The Python code lives in `bundled/tool/lsp_server.py`. The TypeScript extension locates and spawns it. This is the exact pattern from `microsoft/vscode-python-tools-extension-template`.

**Do not write a Node.js LSP server.** The Python LSP server (pygls) is spawned by the TypeScript extension — this is the correct architecture.

**Minimum VS Code version:** 1.82.0+ (required by vscode-languageclient 9.x)

### Python Package Distribution

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| hatchling | latest | Build backend for wheel/sdist | Default backend for `uv init --lib`. Supports `force-include` for mapping arbitrary files into the wheel. Better than setuptools for non-trivial file inclusion patterns. |
| importlib.resources | stdlib 3.11 | Load bundled schema files at runtime | Python 3.11 stdlib — no extra dep. `importlib.resources.files("skilllint.schemas").joinpath("claude.json")` correctly handles both installed wheels and editable installs. |
| uv build | latest | Build wheel + sdist | Wraps hatchling. `uv build` produces both `.tar.gz` and `.whl` in `dist/`. Integrates with existing uv toolchain. |

**Schema snapshot bundling pattern:**

```toml
# pyproject.toml
[tool.hatch.build.targets.wheel]
packages = ["src/skilllint"]

[tool.hatch.build.targets.wheel.force-include]
"src/skilllint/schemas" = "skilllint/schemas"
```

```python
# Runtime access at runtime (Python 3.11+)
from importlib.resources import files

def load_schema(platform: str) -> dict:
    schema_bytes = files("skilllint.schemas").joinpath(f"{platform}.json").read_bytes()
    return json.loads(schema_bytes)
```

**Do not use `pkg_resources`.** It is deprecated in favor of `importlib.resources`. Do not use `__file__`-relative paths — they break in zipimport and some wheel layouts.

---

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-lsp | latest | End-to-end LSP server tests | When writing tests for LSP diagnostics and completions |
| lsp-devtools | latest | Debug LSP traffic interactively | Development only — inspect LSP messages between client and server |
| nox | latest | Run build tasks (install bundled_libs) | VS Code extension build: nox session installs Python deps into `bundled/libs/` |

---

## Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| yo + generator-code | Scaffold VS Code extension | `npm install -g yo generator-code` then `yo code`. Select "New Extension (TypeScript)" + esbuild. Use once. |
| @vscode/vsce | Package .vsix | `npx @vscode/vsce package` produces `.vsix`. Publish with `npx @vscode/vsce publish`. |
| mcp dev (FastMCP inspector) | Debug MCP server | `fastmcp dev src/skilllint/mcp_server.py` opens browser-based MCP inspector at localhost:6274. |
| uv build | Build Python wheel | `uv build` → `dist/skilllint-*.whl` |

---

## Installation

```bash
# Python: LSP + MCP
uv add pygls lsprotocol fastmcp

# Python: dev
uv add --dev pytest-lsp lsp-devtools nox

# VS Code extension: Node dependencies
cd packages/vscode-skilllint
npm install vscode-languageclient @types/vscode esbuild @vscode/vsce

# VS Code extension: install Python deps into bundled/libs (at build time)
# Handled by noxfile.py session — pip install -t bundled/libs -r requirements.txt
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| pygls 2.0.1 | python-lsp-server (pylsp) | Never for this project — pylsp is a Python language server (for Python code), not a framework for building custom servers |
| pygls 2.0.1 | raw asyncio + JSON-RPC | Only if pygls becomes unmaintained; significant implementation cost for no benefit |
| fastmcp 3.0 | mcp (official SDK) | If you need zero extra dependencies and only use basic tool registration — fastmcp is strictly better otherwise |
| fastmcp 3.0 | fastmcp 2.x | Never — 3.0 is stable GA; upgrade path is straightforward |
| hatchling | setuptools | If the project needs legacy compatibility; hatchling is cleaner for new packages |
| importlib.resources | pkg_resources | Never — pkg_resources is deprecated |
| esbuild | webpack | webpack if you need complex transformations; esbuild is 50x faster for straightforward TypeScript bundling |
| vscode-languageclient 9.x | custom LSP client | Never — vscode-languageclient is the only supported VS Code LSP client API |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| python-lsp-server (pylsp) | It is a Python language server (for Python source files), not a framework for building LSP servers | pygls |
| pkg_resources | Deprecated by setuptools maintainers; slow import; breaks in some zip layouts | importlib.resources (stdlib 3.11+) |
| fastmcp 2.x | 3.0 is stable GA; v2 is superseded | fastmcp 3.0.2 |
| MANIFEST.in | Legacy setuptools mechanism; not used with hatchling | `[tool.hatch.build.targets.wheel.force-include]` in pyproject.toml |
| webpack for VS Code extension | 50x slower than esbuild for this use case; no TypeScript advantages that matter here | esbuild |
| Node.js LSP server | The project's validation logic is Python; don't rewrite it in JS to serve as LSP backend | pygls Python server spawned by TypeScript extension |
| __file__ for resource paths | Breaks in some wheel/zip install layouts | importlib.resources.files() |

---

## Stack Patterns by Variant

**If building LSP server only (no VS Code extension yet):**
- Use `pygls` standalone with stdio transport
- Test with `pytest-lsp`
- Ship as `skilllint --lsp` CLI flag

**If building VS Code extension:**
- Follow `microsoft/vscode-python-tools-extension-template` structure exactly
- TypeScript extension in `packages/vscode-skilllint/`
- Python server in `packages/vscode-skilllint/bundled/tool/lsp_server.py`
- Python deps bundled in `packages/vscode-skilllint/bundled/libs/`

**If the MCP server needs to ship as part of the .whl:**
- Add `skilllint-mcp` as a console script entry point in pyproject.toml
- Claude Code plugin installs it via `uv tool install skilllint`

**If packaging the .plugin for Claude Code:**
- Claude Code .plugin format is a YAML-frontmatter file that declares MCP server, skill, and agent installs
- The MCP server must already be on PATH or addressable via `uvx skilllint-mcp` / `uv run -m skilllint.mcp`

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| pygls 2.0.1 | lsprotocol 2025.0.0 | lsprotocol is an auto-installed dependency of pygls 2.x |
| pygls 2.0.1 | Python 3.9+ | No conflict with project's 3.11+ constraint |
| fastmcp 3.0.2 | Python 3.10+ | No conflict with project's 3.11+ constraint |
| vscode-languageclient 9.0.1 | VS Code ^1.82.0 | Set `engines.vscode` to `"^1.82.0"` in package.json |
| pygls 2.x | Pydantic 2.x | pygls 2.x removed Pydantic dependency entirely — no version conflict |

---

## Sources

- [pygls 2.0.1 documentation](https://pygls.readthedocs.io/) — verified: version, Python requirements, lsprotocol dependency, feature decorators. Confidence: HIGH
- [pygls GitHub](https://github.com/openlawlibrary/pygls) — verified: release history, v2.0.0 Oct 2025, v2.0.1 patch. Confidence: HIGH
- [lsprotocol PyPI](https://pypi.org/project/lsprotocol/2025.0.0) — verified: version 2025.0.0. Confidence: HIGH
- [fastmcp PyPI](https://pypi.org/project/fastmcp/) — verified: 3.0.2, Python >=3.10. Confidence: HIGH
- [FastMCP documentation](https://gofastmcp.com/) — verified: 3.0 GA, tool decorator pattern, installation. Confidence: HIGH
- [FastMCP 3.0 GA announcement](https://www.jlowin.dev/blog/fastmcp-3-launch) — verified: stable release, upgrade path. Confidence: HIGH
- [VS Code Language Server Extension Guide](https://code.visualstudio.com/api/language-extensions/language-server-extension-guide) — verified: vscode-languageclient usage, extension architecture. Confidence: HIGH
- [microsoft/vscode-python-tools-extension-template](https://github.com/microsoft/vscode-python-tools-extension-template) — verified: bundled/libs pattern, TypeScript + pygls architecture. Confidence: HIGH
- [VS Code Bundling Extensions](https://code.visualstudio.com/api/working-with-extensions/bundling-extension) — verified: esbuild recommendation, .vscodeignore, dist/ output. Confidence: HIGH
- [pytest-lsp documentation](https://lsp-devtools.readthedocs.io/en/release/pytest-lsp/guide/getting-started.html) — verified: subprocess test pattern. Confidence: HIGH
- [Python Packaging User Guide — pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — verified: package data configuration. Confidence: HIGH
- [Hatchling build configuration](https://hatch.pypa.io/1.13/config/build/) — verified: force-include syntax for wheel data files. Confidence: HIGH
- [importlib.resources Python 3.11 stdlib](https://docs.python.org/3/library/importlib.resources.html) — verified: files() API for package resource access. Confidence: HIGH
- [uv build backend docs](https://docs.astral.sh/uv/concepts/build-backend/) — verified: uv_build vs hatchling recommendation. Confidence: HIGH

---

*Stack research for: skilllint — LSP, MCP, VS Code extension, and Python packaging*
*Researched: 2026-03-02*
