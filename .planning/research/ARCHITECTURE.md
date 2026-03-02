# Architecture Research

**Domain:** Python linter ecosystem (CLI + LSP + MCP + VS Code extension)
**Researched:** 2026-03-02
**Confidence:** HIGH (LSP/VS Code patterns), MEDIUM (MCP patterns, platform adapter patterns)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Consumer Layer                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  CLI (term)  │  │  VS Code ext │  │  MCP client  │  │  pre-commit│  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │
│         │ subprocess/     │ LSP over  │ MCP tools    │ subprocess  │
│         │ direct import   │ stdio     │ (JSON-RPC)   │ invocation  │
├─────────┴─────────────────┴──────────┴──────────────┴─────────────────┤
│                        Protocol Adapter Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │  Typer CLI   │  │ pygls LSP    │  │  FastMCP server              │  │
│  │  entry point │  │ server       │  │  (tool wrappers)             │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────────────┘  │
│         │                 │                      │                       │
│         └─────────────────┴──────────────────────┘                      │
│                           │                                              │
├───────────────────────────┼──────────────────────────────────────────────┤
│                     Core Validation Library                               │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  ValidationEngine                                                    │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ │ │
│  │  │ Validator   │ │ Validator   │ │ Validator   │ │ Validator    │ │ │
│  │  │ (frontmattr)│ │ (complexity)│ │ (links)     │ │ (plugin reg) │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│                     Platform Adapter Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  ClaudeCode  │  │  Cursor      │  │  Windsurf    │  │  Codex     │  │
│  │  Adapter     │  │  Adapter     │  │  Adapter     │  │  Adapter   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│                     Schema Snapshot Store                                 │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  skilllint/schemas/  (JSON/YAML, versioned, bundled in .whl)     │   │
│  │  claude_code/v1.json   cursor/v1.json   windsurf/v1.json ...     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| CLI entry point | Argument parsing, file discovery, report formatting, exit codes | Typer app with `@app.command()` handlers |
| pygls LSP server | Translate document-change events to ValidationEngine calls, push diagnostics | `LanguageServer` subclass with `@server.feature(TEXT_DOCUMENT_DID_OPEN)` etc. |
| FastMCP server | Expose `validate_*`, `query_schema`, `scaffold_*` as named MCP tools | `@mcp.tool()` decorators wrapping ValidationEngine calls |
| ValidationEngine | Orchestrate validators per file type, aggregate results | Thin orchestrator — routes `FileType` → validator list, collects `ValidationResult` objects |
| Validator (per rule group) | Implement `Validator` Protocol: `validate()`, `can_fix()`, `fix()` | Stateless dataclass or class per validator |
| Platform adapter | Resolve platform-specific schema, provide FileType detection rules, map error codes to platform docs | Class implementing `PlatformAdapter` Protocol |
| Schema snapshot store | Bundle versioned schema JSON/YAML inside the Python package for offline access | `skilllint/schemas/{platform}/{version}.json` read via `importlib.resources.files()` |
| VS Code extension | Spawn LSP server process, create `LanguageClient`, surface diagnostics/completions in editor | TypeScript extension using `vscode-languageclient` npm package |

## Recommended Project Structure

```
packages/skilllint/
├── skilllint/                   # Installable package (not PEP 723 scripts)
│   ├── __init__.py
│   ├── cli.py                   # Typer app — CLI entry point
│   ├── engine.py                # ValidationEngine — orchestrates validators
│   ├── models.py                # ValidationResult, ValidationIssue, FileType (moved from plugin_validator.py)
│   ├── validators/              # One module per rule group
│   │   ├── __init__.py
│   │   ├── frontmatter.py       # FrontmatterValidator
│   │   ├── complexity.py        # SkillComplexityValidator
│   │   ├── links.py             # InternalLinkValidator
│   │   ├── plugin_struct.py     # PluginStructureValidator
│   │   └── plugin_reg.py        # PluginRegistrationValidator
│   ├── platforms/               # Platform adapters
│   │   ├── __init__.py          # PlatformAdapter Protocol definition + registry
│   │   ├── claude_code.py       # ClaudeCode adapter
│   │   ├── cursor.py            # Cursor adapter (stub initially)
│   │   └── windsurf.py          # Windsurf adapter (stub initially)
│   ├── schemas/                 # Bundled snapshots — included in .whl as package data
│   │   ├── claude_code/
│   │   │   └── v1.json
│   │   ├── cursor/
│   │   │   └── v1.json
│   │   └── windsurf/
│   │       └── v1.json
│   ├── frontmatter_core.py      # Pydantic models (existing, keep as-is)
│   ├── frontmatter_utils.py     # YAML I/O (existing, keep as-is)
│   └── lsp/
│       ├── __init__.py
│       └── server.py            # pygls LanguageServer — imports engine.py, calls validate()
├── mcp/
│   ├── __init__.py
│   └── server.py                # FastMCP server — @mcp.tool() wrappers around engine.py
├── vscode-extension/            # TypeScript project
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       └── extension.ts         # Spawns lsp/server.py via stdio, creates LanguageClient
├── pyproject.toml               # [tool.setuptools.package-data] includes schemas/**
└── tests/
    └── ...                      # Existing test suite (moved here)
```

### Structure Rationale

- **skilllint/ (package):** All importable code lives here. Validators become their own module files instead of one 3000-line script so they can be imported cleanly by both CLI and LSP.
- **skilllint/schemas/:** Non-Python data files inside the package directory so `importlib.resources.files("skilllint.schemas")` works post-installation and inside zip/wheel environments.
- **skilllint/lsp/server.py:** Isolated from CLI concerns. pygls requires a long-running asyncio process; importing it into the CLI entry point would be incorrect.
- **mcp/server.py:** FastMCP server wraps engine.py tools via `@mcp.tool()` decorators. Lives outside `skilllint/` because it is a deployment artifact, not a library.
- **vscode-extension/:** TypeScript project with its own `package.json`. Communicates with LSP server via stdio. Packaged and published separately to VS Code Marketplace.

## Architectural Patterns

### Pattern 1: Core-First — Validation Logic as Library, Protocols on Top

**What:** The `ValidationEngine` and all `Validator` classes form a pure Python library with no I/O concerns. CLI, LSP server, and MCP server are each thin wrappers that call the engine and translate results to their respective output formats.

**When to use:** Always. This is the enabling pattern for the entire ecosystem. Without it, each protocol surface (CLI, LSP, MCP) must duplicate validation logic.

**Trade-offs:** Requires refactoring the existing monolithic `plugin_validator.py` into importable modules before LSP/MCP work can begin. This is the correct build order dependency.

**Example:**
```python
# engine.py — pure library, no I/O
from skilllint.models import ValidationResult, FileType
from skilllint.validators.frontmatter import FrontmatterValidator

class ValidationEngine:
    def validate_file(self, path: Path) -> list[ValidationResult]:
        file_type = FileType.detect(path)
        validators = self._validators_for(file_type)
        return [v.validate(path) for v in validators]

# cli.py — thin wrapper, handles I/O
@app.command()
def check(path: Path) -> None:
    engine = ValidationEngine()
    results = engine.validate_file(path)
    _print_results(results)     # CLI-specific formatting
    raise SystemExit(1 if any(r.has_errors for r in results) else 0)

# lsp/server.py — thin wrapper, handles LSP protocol
@server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: DidOpenTextDocumentParams) -> None:
    path = _uri_to_path(params.text_document.uri)
    results = engine.validate_file(path)
    ls.publish_diagnostics(params.text_document.uri, _to_lsp_diagnostics(results))
```

### Pattern 2: Subprocess (ruff-lsp) vs Library Integration (ruff server)

**What:** Two approaches exist for how the LSP server calls the validator core. Subprocess invocation (spawn the CLI binary per document change) is simpler to implement but stateless and slow. Library integration (import the engine directly) enables stateful operations and eliminates per-invocation overhead.

**When to use:** Use library integration. For Python projects with no Rust-tier performance requirements, library integration is straightforward. Subprocess was ruff's compromise when the linter was a Rust binary; skilllint is Python all the way through.

**Trade-offs:** Library integration requires the package structure refactor first (Pattern 1). Subprocess is tempting as a shortcut but limits LSP features to stateless request-response.

**Example:**
```python
# AVOID: subprocess — ruff-lsp legacy pattern
import subprocess
result = subprocess.run(["skilllint", "--format", "json", str(path)], capture_output=True)
diagnostics = json.loads(result.stdout)

# PREFER: library — ruff server modern pattern
from skilllint.engine import ValidationEngine
engine = ValidationEngine()  # stateful — created once at server startup
results = engine.validate_file(path)  # called per document change
```

### Pattern 3: Platform Adapter Protocol

**What:** Each supported AI platform (Claude Code, Cursor, Windsurf, Codex) has different frontmatter schemas, file discovery rules, and error documentation URLs. A `PlatformAdapter` Protocol defines the interface; concrete adapters implement it. A registry maps platform name strings to adapter instances.

**When to use:** When adding support for a new platform. The engine routes validation through the active adapter; callers never reference platform-specific classes directly.

**Trade-offs:** Adds indirection. Justified because platform schemas diverge in unpredictable ways and new platforms will emerge. The open/closed principle already exists for validators — this extends it to platforms.

**Example:**
```python
# platforms/__init__.py
from typing import Protocol, runtime_checkable
from pathlib import Path

@runtime_checkable
class PlatformAdapter(Protocol):
    platform_id: str
    schema_version: str

    def load_schema(self) -> dict:
        """Load bundled JSON schema for this platform."""
        ...

    def get_scan_patterns(self) -> list[str]:
        """File glob patterns for this platform's artifact types."""
        ...

    def docs_url(self, error_code: str) -> str:
        """Generate documentation URL for an error code."""
        ...

# platforms/claude_code.py
import importlib.resources
import json

class ClaudeCodeAdapter:
    platform_id = "claude_code"
    schema_version = "v1"

    def load_schema(self) -> dict:
        ref = importlib.resources.files("skilllint.schemas.claude_code").joinpath("v1.json")
        with ref.open() as f:
            return json.load(f)

    def get_scan_patterns(self) -> list[str]:
        return ["skills/*/SKILL.md", "agents/*.md", ".claude/commands/*.md", "plugin.json"]

    def docs_url(self, error_code: str) -> str:
        return f"https://docs.agentskills-linter.dev/rules/{error_code.lower()}"
```

### Pattern 4: Bundled Schema Snapshots via importlib.resources

**What:** Platform schemas are JSON files shipped inside the Python package directory (`skilllint/schemas/`). They are declared in `pyproject.toml` as package data and accessed at runtime via `importlib.resources.files()`, which works correctly whether the package is installed from a wheel or unpacked.

**When to use:** Always — this is the correct Python pattern for non-Python data files that must be accessible post-installation, including in zip-imported packages.

**Trade-offs:** Schemas are snapshots. When a platform updates its schema, the package must release a new version. This is the declared constraint (no live fetching) and the correct trade-off for offline/sandbox reliability.

**Example:**
```toml
# pyproject.toml
[tool.setuptools.package-data]
skilllint = ["schemas/**/*.json", "schemas/**/*.yaml"]
```

```python
# Access bundled schema at runtime
import importlib.resources
import json

def load_bundled_schema(platform: str, version: str) -> dict:
    pkg = f"skilllint.schemas.{platform}"
    ref = importlib.resources.files(pkg).joinpath(f"{version}.json")
    with ref.open("r") as f:
        return json.load(f)
```

### Pattern 5: VS Code Extension as LSP Client (TypeScript → Python)

**What:** The VS Code extension is a TypeScript/Node.js project that uses the `vscode-languageclient` npm package to spawn the Python LSP server process and communicate over stdio. The extension does not perform any validation; it only starts the server, relays editor events to it, and renders the diagnostics and completions the server returns.

**When to use:** This is the standard pattern for Python-backed VS Code extensions. The `vscode-black-formatter` and (legacy) `ruff-vscode` extensions both follow this exact architecture.

**Trade-offs:** The extension depends on the LSP server being installed in the active Python environment. The extension must detect the Python executable and spawn the server via `python -m skilllint.lsp.server` or the `skilllint-lsp` console script entry point.

**Example:**
```typescript
// extension.ts
import * as vscode from "vscode";
import { LanguageClient, ServerOptions, TransportKind } from "vscode-languageclient/node";

export function activate(context: vscode.ExtensionContext) {
    const serverOptions: ServerOptions = {
        command: "python",
        args: ["-m", "skilllint.lsp.server"],
        transport: TransportKind.stdio,
    };
    const clientOptions = {
        documentSelector: [{ scheme: "file", language: "markdown" }],
    };
    const client = new LanguageClient("skilllint", "Skilllint", serverOptions, clientOptions);
    context.subscriptions.push(client.start());
}
```

### Pattern 6: MCP Server as Tool Wrappers (FastMCP)

**What:** The MCP server uses FastMCP `@mcp.tool()` decorators to expose validator functions as named tools. Each tool is a thin wrapper that calls `ValidationEngine` and formats results as structured JSON for the LLM. FastMCP handles JSON schema generation from type hints, parameter validation, and MCP protocol compliance.

**When to use:** The recommended Python MCP pattern as of 2026. FastMCP 3.0 (released January 2026) includes component versioning and OpenTelemetry, making it suitable for production use.

**Trade-offs:** FastMCP is a higher-level framework than the raw `mcp` SDK. The `@mcp.tool()` decorator cannot be the canonical implementation — it must wrap the engine, not contain validation logic.

**Example:**
```python
# mcp/server.py
from fastmcp import FastMCP
from skilllint.engine import ValidationEngine
from pathlib import Path

mcp = FastMCP("skilllint")
engine = ValidationEngine()

@mcp.tool()
def validate_skill(path: str) -> dict:
    """Validate a skill frontmatter file and return structured diagnostics."""
    results = engine.validate_file(Path(path))
    return {"issues": [r.to_dict() for r in results], "passed": all(r.passed for r in results)}

@mcp.tool()
def query_schema(platform: str, version: str = "v1") -> dict:
    """Return the bundled schema snapshot for an AI platform."""
    from skilllint.platforms import get_adapter
    adapter = get_adapter(platform)
    return adapter.load_schema()
```

## Data Flow

### Validation Request Flow (CLI)

```
User: skilllint check ./my-skills/
    │
    ▼
CLI (cli.py)
  parse args → resolve paths → detect FileType per path
    │
    ▼
ValidationEngine (engine.py)
  for each path: select validators from registry → call validator.validate(path)
    │
    ▼
PlatformAdapter (platforms/claude_code.py)
  load schema → provide scan patterns
    │
    ▼
Validator (validators/frontmatter.py)
  read YAML → extract frontmatter → validate against Pydantic model
  → returns ValidationResult(issues=[ValidationIssue(...)])
    │
    ▼
Reporter (cli.py)
  format results as Rich table or JSON → write to stdout
    │
    ▼
SystemExit(0 or 1)
```

### Validation Request Flow (LSP)

```
Editor: user opens/edits skills/my-skill/SKILL.md
    │ LSP textDocument/didOpen or textDocument/didChange
    ▼
pygls server (lsp/server.py)
  receives notification → extracts URI → resolves to Path
    │
    ▼
ValidationEngine (engine.py)  ← same engine instance, no subprocess
  validate_file(path) → list[ValidationResult]
    │
    ▼
pygls server (lsp/server.py)
  _to_lsp_diagnostics(results) → list[Diagnostic]
  ls.publish_diagnostics(uri, diagnostics)
    │ LSP textDocument/publishDiagnostics notification
    ▼
Editor: underline squiggles, Problems panel populated
```

### Validation Request Flow (MCP)

```
LLM / Claude Code: calls validate_skill tool with {"path": "skills/auth/SKILL.md"}
    │ MCP tool call (JSON-RPC)
    ▼
FastMCP server (mcp/server.py)
  deserialize args → validate types via Pydantic
    │
    ▼
ValidationEngine (engine.py)  ← same engine, imported directly
  validate_file(path) → list[ValidationResult]
    │
    ▼
FastMCP server (mcp/server.py)
  serialize results to dict → return as tool result
    │ MCP tool response
    ▼
LLM: receives structured diagnostics, can reason about and fix them
```

### Fix Workflow (all surfaces)

```
fix request (--fix flag / code action / MCP fix_skill tool)
    │
    ▼
ValidationEngine.fix_file(path)
  for each validator where can_fix() == True:
    fixes = validator.fix(path)
  write modified YAML preserving round-trip formatting (ruamel.yaml)
    │
    ▼
return list of applied fixes → surface to caller
```

## Build Order — Suggested Phase Sequence

The dependency graph between components dictates build order. Each phase must be complete before the next begins.

```
Phase 1: Package restructure
  plugin_validator.py → skilllint/ package
  pyproject.toml, entry points, tests pass
         │
         ▼
Phase 2: Platform adapter architecture
  PlatformAdapter Protocol
  ClaudeCode adapter (existing logic migrated)
  Schema snapshots bundled via importlib.resources
         │
         ▼
Phase 3: Fix mode + config
  --fix flag wired through engine
  linter.toml / pyproject.toml [tool.skilllint] config parsing
         │
         ▼
Phase 4: LSP server
  pygls LanguageServer subclass
  validate_file() called on didOpen/didChange
  Diagnostics pushed back to editor
         │
         ▼
Phase 5: VS Code extension
  TypeScript project, vscode-languageclient
  Spawns Phase 4 LSP server via stdio
         │
         ▼
Phase 6: MCP server
  FastMCP server wrapping engine.py
  validate_*, query_schema, scaffold_* tools
         │
         ▼
Phase 7: Claude Code .plugin
  Bundles MCP server + skill definition + agent definition
  plugin.json, marketplace.json pointing to Phase 6
```

**Why this order:**
- Phases 4, 5, 6, 7 all import from `engine.py` — Phase 1 must ship a proper importable package first.
- Phase 4 (LSP) is independent of Phase 6 (MCP) — they can be parallelised after Phase 3.
- Phase 5 (VS Code) depends on Phase 4 existing — the extension is just a launcher for the server.
- Phase 7 (.plugin) depends on Phase 6 (MCP server) being deployable.

## Anti-Patterns

### Anti-Pattern 1: LSP Server Calls CLI as Subprocess

**What people do:** Implement the LSP server by spawning `skilllint check {path}` as a subprocess and parsing the JSON stdout output.

**Why it's wrong:** Each document change spawns a new process with its own import overhead (~0.3-0.5 seconds for a Pydantic-heavy Python package). Stateful LSP features (unsaved-buffer content, cross-file diagnostics) become impossible because the subprocess reads from disk. This is the explicitly documented failure mode of the original `ruff-lsp` Python approach.

**Do this instead:** Import `ValidationEngine` directly in `lsp/server.py`. Create one engine instance at server startup. Call `engine.validate_file()` on each notification.

### Anti-Pattern 2: Validation Logic Duplicated in MCP Wrappers

**What people do:** Implement `validate_skill` in `mcp/server.py` by copying validation logic from `plugin_validator.py` rather than importing from the engine.

**Why it's wrong:** Divergence between CLI and MCP validation behaviour. Two sets of rules to maintain. Bugs fixed in one surface silently persist in the other.

**Do this instead:** `mcp/server.py` may only call `engine.py` functions. No validator logic lives in tool wrappers.

### Anti-Pattern 3: Schema Files Outside the Package Directory

**What people do:** Store schemas in a top-level `schemas/` directory or load them relative to `__file__` in a script.

**Why it's wrong:** `__file__` is unreliable in zip-imported packages (wheels). Top-level `schemas/` is not included in the installed package. The package data mechanism in setuptools only includes files inside the package directory.

**Do this instead:** Store schemas at `skilllint/schemas/{platform}/{version}.json` and declare them in `[tool.setuptools.package-data]`. Access via `importlib.resources.files("skilllint.schemas.{platform}").joinpath("{version}.json")`.

### Anti-Pattern 4: One PEP 723 Monolith for LSP/MCP

**What people do:** Add `--lsp` and `--mcp` flags to `plugin_validator.py`, turning it into a single entry point that conditionally enters server mode.

**Why it's wrong:** PEP 723 scripts resolve dependencies at `uv run` invocation time. LSP and MCP servers require long-running asyncio event loops incompatible with the synchronous Typer CLI structure. `pygls` and `fastmcp` have distinct startup semantics. Mixing them compounds complexity and makes testing difficult.

**Do this instead:** `lsp/server.py` and `mcp/server.py` are separate modules with their own `console_scripts` entry points (`skilllint-lsp`, `skilllint-mcp`). The CLI, LSP server, and MCP server share `engine.py` as a library — they are not the same process.

### Anti-Pattern 5: Platform Adapter Logic Inline in Validators

**What people do:** Hard-code Claude Code path patterns and schema field names inside `FrontmatterValidator.validate()`.

**Why it's wrong:** Adding Cursor or Windsurf support requires modifying existing validator code, violating the open/closed principle the codebase already follows for rule groups. Platform differences leak throughout the validator logic.

**Do this instead:** Validators receive a `PlatformAdapter` instance (or the resolved schema dict) as a constructor argument. The engine resolves the adapter; validators remain platform-agnostic.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| VS Code Marketplace | VSIX package upload via `vsce publish` | Extension is TypeScript; published independently of the Python wheel |
| PyPI | `uv build` + `twine upload` or `uv publish` | Wheel includes schema snapshots via package-data |
| Claude Code plugin registry | `plugin.json` + `marketplace.json` with MCP server reference | `.plugin` distribution format; MCP server must be installed first |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI → ValidationEngine | Direct Python import | No serialization overhead |
| LSP server → ValidationEngine | Direct Python import | Stateful; engine created once at startup |
| MCP server → ValidationEngine | Direct Python import | FastMCP wrapper; engine created once at startup |
| VS Code extension → LSP server | LSP over stdio (JSON-RPC) | TypeScript client spawns Python server process |
| Platform adapter → Schema store | `importlib.resources.files()` | Reads bundled JSON from package data |
| Validators → Platform adapter | Constructor injection | Adapter passed in by engine; validators stateless |
| Test suite → ValidationEngine | Direct import + Typer `CliRunner` | Existing `importlib.util.spec_from_file_location` pattern replaced by proper package import post-restructure |

## Sources

- Ruff v0.4.5 blog post (native LSP, subprocess limitations): https://astral.sh/blog/ruff-v0.4.5
- ruff-lsp GitHub (deprecated Python subprocess approach): https://github.com/astral-sh/ruff-lsp
- ruff-lsp deprecation discussion: https://github.com/astral-sh/ruff/discussions/15991
- pygls documentation (diagnostics push model): https://pygls.readthedocs.io/en/latest/servers/examples/publish-diagnostics.html
- VS Code Language Server Extension Guide (stdio transport, client/server process model): https://code.visualstudio.com/api/language-extensions/language-server-extension-guide
- microsoft/vscode-black-formatter (reference implementation, Python backend): https://github.com/microsoft/vscode-black-formatter
- FastMCP documentation (tool wrapping pattern): https://gofastmcp.com/servers/tools
- FastMCP GitHub (v3.0 released 2026-01-19): https://github.com/jlowin/fastmcp
- Python Packaging User Guide (pyproject.toml, package-data): https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- setuptools data files documentation: https://setuptools.pypa.io/en/latest/userguide/datafiles.html
- importlib.resources documentation: https://docs.python.org/3/library/importlib.resources.html

---
*Architecture research for: Python AI agent plugin linter ecosystem (skilllint)*
*Researched: 2026-03-02*
