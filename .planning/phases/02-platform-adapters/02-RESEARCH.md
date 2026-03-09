# Phase 2: Platform Adapters - Research

**Researched:** 2026-03-09
**Domain:** Python typing.Protocol, importlib.metadata entry_points, platform-specific schema validation
**Confidence:** HIGH

## Summary

Phase 2 builds a pluggable `PlatformAdapter` architecture using `typing.Protocol` (structural subtyping) so third-party adapters never import from `skilllint`. Three bundled adapters ship with the package — Claude Code, Cursor, and Codex — registered via Python entry_points in the `skilllint.adapters` group. A new AS-series rule set fires cross-platform on any SKILL.md, layered beneath platform-specific rule series.

The key design insight from CONTEXT.md is that adapters are **data providers, not logic owners**: each adapter declares its schema, path patterns, and applicable rule codes; the core validator owns all execution. The layered validation model (AS-series baseline + platform-specific rules) means the same SKILL.md can be validated by multiple adapters simultaneously without double-counting AS violations.

The primary technical risk is schema completeness for the Cursor `.mdc` format and the Codex `.rules` Starlark format — both are documented but the `.rules` format is explicitly experimental. All three bundled schemas are Phase 2 deliverables as real `v1.json` files, not stubs.

**Primary recommendation:** Define `PlatformAdapter` as a `@runtime_checkable Protocol`, register all three bundled adapters in `pyproject.toml` under `[project.entry-points."skilllint.adapters"]`, discover at runtime via `importlib.metadata.entry_points(group="skilllint.adapters")`, and use `pathlib.PurePath.match()` semantics for adapter path pattern declarations.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Adapter Protocol design**
- Use `typing.Protocol` (structural subtyping) — third-party adapters do NOT import from skilllint to be compatible
- Each adapter has a string ID (e.g., `claude_code`, `cursor`, `codex`)
- Adapter's responsibilities: provide schema for each file type, declare path patterns for auto-detection, declare applicable rule codes
- Core validator owns all rule execution — adapters are data providers, not logic owners
- Adapter exposes `applicable_rules()` returning a set of rule code prefixes or explicit codes — core filters checks accordingly
- Bundled adapters registered in `pyproject.toml` via `skilllint.adapters` entry_points group
- Third-party adapters install via the same entry_points mechanism — no core modification needed

**Rule code series**
- New AS-series codes for agentskills.io spec violations (AS001, AS002, AS003, …)
- AS-series fires on ANY SKILL.md regardless of platform adapter
- Examples: AS001 = name format, AS002 = description length/quality, AS003 = directory name mismatch
- SK/PR/HK codes remain Claude Code-specific
- Each platform adapter declares which code series it activates

**Shared agentskills.io validation (AS-series)**
All platforms that have SKILL.md files get:
- `name`: 1–64 chars, lowercase alphanumeric + hyphens, no leading/trailing/consecutive hyphens, must match parent directory name
- `description`: 1–1024 chars, non-empty, should be trigger-oriented
- Directory structure: `SKILL.md` required, `scripts/`, `references/`, `assets/` optional
- Progressive disclosure: warn if `SKILL.md` body exceeds 500 lines
- Test case detection: identify if `eval_queries.json` or equivalent test fixtures exist

**Platform detection**
- Each adapter declares its own path patterns (glob patterns) — not hardcoded in core
- CLI matches a file against all registered adapter patterns; all matching adapters run their checks
- `--platform` flag overrides auto-detection
- Multi-adapter files: run AS-series rules once, then each matching adapter's platform-specific checks
- Layered validation model: AS-series = cross-platform baseline; platform-specific = only fire when adapter matches

**Claude Code adapter**
- Validates: `plugin.json`, `SKILL.md` (under `.claude/`), `agents/*.md`, `commands/*.md`, `hooks.json`
- Path patterns: `.claude/**/*.md`, `plugin.json`, `hooks.json`, `agents/**/*.md`, `commands/**/*.md`
- Runs existing SK/PR/HK rule series in addition to AS-series

**Cursor adapter**
- Validates: `.mdc` rule files, SKILL.md in `.cursor/` directory
- Path patterns: `**/*.mdc`, `.cursor/**/*.md`, `.agents/skills/**/*.md`
- Runs AS-series for SKILL.md files; Cursor-specific schema checks for `.mdc` files

**Codex adapter**
- Validates: SKILL.md (under `.agents/skills/`), `AGENTS.md`, `.rules` files
- Path patterns: `.agents/skills/**/*.md`, `AGENTS.md`, `**/*.rules`, `.codex/**`
- AS-series applies to SKILL.md files
- `AGENTS.md`: check presence and non-empty content
- `.rules` files: validate known Starlark `prefix_rule()` fields

**Bundled schema snapshots**
- Phase 1 established `load_bundled_schema("claude_code", "v1")` via `importlib.resources.files()`
- Phase 2 adds `skilllint.schemas.cursor` and `skilllint.schemas.codex` namespace packages with `v1.json`
- v1.json is a Phase 2 deliverable with real field definitions

**Phase 2 validation depth**
- Schema validation: required fields present, types correct, no unknown fields
- AS-series shared rules: name/description/structure per agentskills.io spec
- Platform-specific field validation per adapter
- NO full SK/PR rule execution for Cursor/Codex adapters in Phase 2
- .rules (Starlark) and agents/*.toml validated for structure only

### Claude's Discretion
- Exact AS rule code numbering beyond AS001-AS003
- Internal adapter registry implementation detail (lazy vs eager loading)
- Error message wording for AS-series violations
- Whether adapter path patterns use fnmatch or pathlib glob semantics

### Deferred Ideas (OUT OF SCOPE)
- Windsurf adapter — v2 scope (ADPT-V2-01)
- Roo Code, Amp/Sourcegraph Cody, generic agentskills.io adapters — v2 scope
- Schema update tooling (automated snapshot refresh) — v2 scope (REG-V2-01)
- Full SK/PR rule validation for Cursor/Codex files — Phase 3+
- `agents/*.toml` deep validation for Codex agent roles — not in Phase 2
- MCP server wrapping for holistic_lint.py — v2 scope (MCP-V2-01)
- agentskills.io specification updates — separate task outside this phase
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADPT-01 | `PlatformAdapter` Protocol defines the interface for platform-specific schema and rule sets | `typing.Protocol` structural subtyping confirmed; `@runtime_checkable` decorator enables isinstance checks in registry |
| ADPT-02 | Adapters register via Python entry_points (`skilllint.adapters`) so third-party adapters can be installed without modifying the core package | `importlib.metadata.entry_points(group="skilllint.adapters")` is the correct modern API (Python 3.10+); pyproject.toml `[project.entry-points."skilllint.adapters"]` syntax confirmed |
| ADPT-03 | Claude Code adapter — validates plugin.json, SKILL.md, agents/*.md, commands/*.md, hooks.json | Loading locations confirmed (see matrix below); schema sources confirmed in codebase at `packages/skilllint/skilllint/__init__.py` |
| ADPT-04 | Cursor adapter — validates `.mdc` rule files and Cursor-specific configuration | `.mdc` frontmatter fields confirmed: `description`, `globs`, `alwaysApply`; Cursor also loads SKILL.md from `.cursor/skills/` and `.claude/skills/` |
| ADPT-05 | Codex / OpenAI adapter — validates OpenAI Codex agent format files | `prefix_rule()` fields confirmed: `pattern`, `decision`, `justification`, `match`, `not_match`; skill loading scopes confirmed |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typing.Protocol` | stdlib (3.8+) | Structural subtyping for PlatformAdapter | No import coupling; third-party adapters implement without depending on skilllint |
| `importlib.metadata` | stdlib (3.10+) | Entry point discovery for adapter registry | Official Python plugin mechanism; no setuptools dependency |
| `importlib.resources` | stdlib (3.9+) | Bundled schema file access | Already established in Phase 1 via `load_bundled_schema()` |
| `pathlib` | stdlib | Path pattern matching for adapter file detection | `PurePath.match()` handles glob semantics without fnmatch quirks |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `jsonschema` | already in project | Schema validation for JSON files (plugin.json, hooks.json) | Claude Code adapter JSON validation |
| `python-frontmatter` | already in project | YAML frontmatter parsing for .md and .mdc files | All three adapters for SKILL.md and .mdc frontmatter |

### Entry Points Declaration (pyproject.toml)
```toml
[project.entry-points."skilllint.adapters"]
claude_code = "skilllint.adapters.claude_code:ClaudeCodeAdapter"
cursor     = "skilllint.adapters.cursor:CursorAdapter"
codex      = "skilllint.adapters.codex:CodexAdapter"
```

### Entry Points Discovery (runtime)
```python
# Source: https://docs.python.org/3/library/importlib.metadata.html
from importlib.metadata import entry_points

def load_adapters() -> dict[str, PlatformAdapter]:
    discovered = entry_points(group="skilllint.adapters")
    return {ep.name: ep.load()() for ep in discovered}
```

## Architecture Patterns

### Recommended Package Structure
```
packages/skilllint/skilllint/
├── adapters/
│   ├── __init__.py          # load_adapters() registry function
│   ├── protocol.py          # PlatformAdapter Protocol definition
│   ├── claude_code.py       # ClaudeCodeAdapter
│   ├── cursor.py            # CursorAdapter
│   └── codex.py             # CodexAdapter
├── rules/
│   ├── __init__.py
│   └── as_series.py         # AS001–AS00N cross-platform rules
├── schemas/
│   ├── __init__.py
│   ├── claude_code/
│   │   ├── __init__.py
│   │   └── v1.json          # existing
│   ├── cursor/
│   │   ├── __init__.py
│   │   └── v1.json          # new Phase 2 deliverable
│   └── codex/
│       ├── __init__.py
│       └── v1.json          # new Phase 2 deliverable
└── plugin_validator.py      # CLI — add --platform flag here
```

### Pattern 1: PlatformAdapter Protocol
**What:** A `typing.Protocol` with `@runtime_checkable` so the registry can verify adapter shape at load time without requiring adapters to inherit from a base class.
**When to use:** All adapter implementations must conform to this interface.

```python
# Source: PEP 544 / https://typing.python.org/en/latest/reference/protocols.html
from typing import Protocol, runtime_checkable
from pathlib import PurePath

@runtime_checkable
class PlatformAdapter(Protocol):
    @property
    def platform_id(self) -> str: ...

    def path_patterns(self) -> list[str]: ...

    def applicable_rules(self) -> set[str]: ...

    def get_schema(self, file_type: str) -> dict | None: ...

    def matches_file(self, path: PurePath) -> bool:
        return any(path.match(p) for p in self.path_patterns())
```

### Pattern 2: Layered Validation Dispatch
**What:** For each file, collect all matching adapters, run AS-series once, then each adapter's platform-specific checks.
**When to use:** Any file that matches multiple adapter patterns (e.g., `.claude/skills/foo/SKILL.md` matches both Claude Code and Cursor adapters).

```python
def validate_file(path: Path, adapters: dict[str, PlatformAdapter],
                  platform_override: str | None = None) -> list[Violation]:
    violations = []
    pure = PurePath(path)

    if platform_override:
        matching = [adapters[platform_override]]
    else:
        matching = [a for a in adapters.values() if a.matches_file(pure)]

    if not matching:
        return violations

    # AS-series fires once regardless of how many adapters match
    if is_skill_md(path):
        violations.extend(run_as_series(path))

    # Platform-specific checks per adapter
    for adapter in matching:
        violations.extend(run_platform_checks(path, adapter))

    return violations
```

### Pattern 3: Schema Namespace Package
**What:** Each platform schema is a Python namespace package with `__init__.py` marker and a `v1.json` file, accessed via `importlib.resources.files()`.
**When to use:** Adding `cursor` and `codex` schema packages, following the `claude_code` pattern established in Phase 1.

```python
# Source: existing load_bundled_schema() in packages/skilllint/skilllint/__init__.py
from importlib.resources import files

def load_bundled_schema(platform: str, version: str) -> dict:
    pkg = f"skilllint.schemas.{platform}"
    data = files(pkg).joinpath(f"{version}.json").read_text(encoding="utf-8")
    return json.loads(data)
```

### Anti-Patterns to Avoid
- **Adapter imports from skilllint core:** Breaks the structural subtyping guarantee — third-party adapters become version-coupled.
- **Hardcoding platform paths in core:** Path patterns belong in each adapter's `path_patterns()` method, not in the CLI dispatch logic.
- **Running AS-series per adapter:** AS-series violations must be deduplicated. Run AS-series once per file, not once per matching adapter.
- **Eager schema loading at import time:** Load schemas only when `get_schema()` is called. Avoids I/O cost when adapters are not used.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Plugin discovery | Custom file scanning / import hooks | `importlib.metadata.entry_points()` | Standard Python plugin mechanism; pip install automatically registers; no subprocess or filesystem scanning needed |
| Structural interface checking | ABC with required `__init__` | `typing.Protocol` + `@runtime_checkable` | No inheritance coupling; isinstance() still works for registry validation |
| Schema file bundling | Copying JSON to temp dirs or reading from install paths | `importlib.resources.files()` | Already proven in Phase 1; works in wheels, zipimport, and editable installs |
| Glob-based path matching | Custom regex builder | `pathlib.PurePath.match()` | Handles `**` glob correctly; no external dependency |

**Key insight:** The entry_points mechanism is the correct Python-ecosystem approach for plugins. Attempting to replicate it with file scanning or direct imports creates fragile coupling that defeats the "no core modification" requirement of ADPT-02.

## Platform Loading Location Matrix

This matrix is the authoritative source for adapter `path_patterns()` declarations.

### Claude Code (ADPT-03)
| Scope | Location | Files |
|-------|----------|-------|
| Project | `.claude/skills/**` | `SKILL.md` |
| User | `~/.claude/skills/**` | `SKILL.md` (out of scope for linter path patterns) |
| Plugin | `.claude/agents/**` | `*.md` |
| Plugin | `.claude/commands/**` | `*.md` |
| Plugin | `plugin.json` | root |
| Plugin | `hooks.json` | root |

Path patterns for adapter declaration:
```python
[".claude/**/*.md", "plugin.json", "hooks.json", "agents/**/*.md", "commands/**/*.md"]
```
Confidence: HIGH — verified via Claude Code official docs (code.claude.com/docs/en/skills)

### Cursor (ADPT-04)
| Scope | Location | Files |
|-------|----------|-------|
| Project rules | `.cursor/rules/**` | `*.mdc` |
| Project skills | `.cursor/skills/**` | `SKILL.md` |
| Shared (compat) | `.claude/skills/**` | `SKILL.md` |
| Cross-platform | `.agents/skills/**` | `SKILL.md` |

Path patterns for adapter declaration:
```python
["**/*.mdc", ".cursor/**/*.md", ".claude/skills/**/*.md", ".agents/skills/**/*.md"]
```
Confidence: MEDIUM — Cursor docs confirm `.cursor/rules/*.mdc` and `.cursor/skills/`; `.claude/skills/` compatibility is confirmed by community docs and the unified skills pattern; `.agents/skills/` confirmed as a widely-adopted cross-platform convention.

**`.mdc` frontmatter fields** (Cursor rules):
- `description` — required, brief explanation of the rule's purpose
- `globs` — list of file patterns; controls auto-attach behavior
- `alwaysApply` — boolean; when `true` rule always attaches regardless of context

Confidence: HIGH — verified via cursor.com/docs/context/rules

### Codex / OpenAI (ADPT-05)
| Scope | Location | Files |
|-------|----------|-------|
| Repo | `.agents/skills/**` | `SKILL.md` + supporting files |
| User | `~/.codex/skills/**` | `SKILL.md` (out of scope for linter) |
| Admin/System | managed environments | out of scope |
| Repo | `AGENTS.md` | root and subdirectories |
| User rules | `~/.codex/rules/*.rules` | Starlark |
| Repo rules | `.codex/rules/*.rules` | Starlark |

Path patterns for adapter declaration:
```python
[".agents/skills/**/*.md", "AGENTS.md", "**/*.rules", ".codex/**"]
```
Confidence: HIGH for `.agents/skills/`, `AGENTS.md`, `.rules` — verified via developers.openai.com/codex/skills/ and developers.openai.com/codex/rules/

**`.rules` file `prefix_rule()` fields** (Starlark):
- `pattern` — required; list where each element is a literal string or list of alternatives
- `decision` — defaults to `"allow"`; values: `"allow"`, `"prompt"`, `"forbidden"`
- `justification` — optional; human-readable reason surfaced in approval prompts
- `match` — optional; inline unit test cases that should match the rule
- `not_match` — optional; inline unit test cases that should not match

Confidence: HIGH — verified via developers.openai.com/codex/rules/

### agentskills.io Open Standard
The spec defines **what goes inside a skill directory**, not where directories live. The standard scan location is `.agents/skills/` for cross-client compatibility, with `.claude/skills/` added for pragmatic compatibility.

**SKILL.md frontmatter fields** (from agentskills.io spec):
- `name` — required; identifier, lowercase alphanumeric + hyphens, must match parent directory name
- `description` — required; max 1024 chars, no `<` or `>`, trigger-oriented
- `license` — optional; license identifier
- `metadata` — optional; object with `author`, `version`, etc.

Confidence: HIGH — verified via agentskills.io/specification

### GitHub Copilot CLI (context only — v1 scope TBD)
Loads SKILL.md from: `.github/skills/`, `.claude/skills/` (project); `~/.copilot/skills/`, `~/.claude/skills/` (user). Uses identical agentskills.io SKILL.md format. AS-series rules fully apply. A GitHub Copilot adapter would be a thin wrapper with distinct path patterns. Confirmed v1 scope decision is deferred — CONTEXT.md does not lock it in Phase 2.

### OpenCode (OUT OF SCOPE for Phase 2)
Uses its own agent format (Markdown + YAML frontmatter with `description`, `mode`, `model`, `tools`, `permission`, `temperature`, `steps`, `color`) — not agentskills.io SKILL.md format. OpenCode also reads `.agents/skills/` for agentskills.io compatibility (confirmed via opencode.ai/docs/skills/). An OpenCode adapter is v2 scope.

## AS-Series Rule Derivation

Cross-platform rules derived from agentskills.io spec. These fire on any file classified as a SKILL.md.

| Code | Check | Severity |
|------|-------|----------|
| AS001 | `name` field present and matches `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (1–64 chars, no leading/trailing/consecutive hyphens) | error |
| AS002 | `name` value matches parent directory name | error |
| AS003 | `description` field present, 1–1024 chars, non-empty after strip | error |
| AS004 | `description` does not contain `<` or `>` | error |
| AS005 | `SKILL.md` body does not exceed 500 lines (progressive disclosure warning) | warning |
| AS006 | Test fixture detection: warn if no `eval_queries.json` or equivalent exists | info |

Additional AS codes (AS007+) are at Claude's discretion per CONTEXT.md.

## Common Pitfalls

### Pitfall 1: Multi-Adapter AS-Series Double-Reporting
**What goes wrong:** A SKILL.md in `.agents/skills/` matches both the Cursor and Codex adapters. AS-series rules fire twice, producing duplicate violations.
**Why it happens:** Naive implementation runs the full rule set per adapter.
**How to avoid:** Track which files have had AS-series run. Run AS-series once per file path in the validation session, regardless of how many adapters match.
**Warning signs:** Violation output showing the same AS001 error twice for the same file.

### Pitfall 2: entry_points Not Available After pip install -e
**What goes wrong:** Adapter registry returns empty set immediately after `pip install -e .` with old pip/setuptools versions.
**Why it happens:** Editable installs in older tooling don't write entry_points.txt until `pip install` runs the full build.
**How to avoid:** Use `uv` or pip >= 21.3 which correctly handles entry_points in editable installs. Document in dev setup.
**Warning signs:** `entry_points(group="skilllint.adapters")` returns empty `SelectableGroups` during tests.

### Pitfall 3: Cursor Skills vs Cursor Rules Path Overlap
**What goes wrong:** `.cursor/skills/**/*.md` files get validated as `.mdc` rule files.
**Why it happens:** Adapter path pattern `**/*.mdc` is fine, but a broad `.cursor/**/*.md` would incorrectly include non-SKILL.md markdown files and attempt schema validation against them.
**How to avoid:** Be precise: `.cursor/skills/**/*.md` for SKILL.md detection (check filename == "SKILL.md"), `**/*.mdc` for rule files. Do not use `.cursor/**/*.md` as a pattern.

### Pitfall 4: importlib.resources on Namespace Packages
**What goes wrong:** `files("skilllint.schemas.cursor")` raises `ModuleNotFoundError` if the namespace package `__init__.py` is missing.
**Why it happens:** `importlib.resources.files()` requires the package to be importable. Empty namespace packages without `__init__.py` are not importable via the `files()` API.
**How to avoid:** Add `__init__.py` (even empty) to each schema subpackage — identical to the `skilllint/schemas/claude_code/__init__.py` pattern established in Phase 1.

### Pitfall 5: Starlark .rules Parser Complexity
**What goes wrong:** Implementing a Starlark parser to validate `.rules` files is a significant scope expansion.
**Why it happens:** Starlark is not YAML/JSON; full parsing requires a dedicated library.
**How to avoid:** Validate only the structural shape (is it valid Starlark syntax? does it contain `prefix_rule()` calls with known fields?) using regex/string matching rather than a full Starlark AST. The format is explicitly experimental — over-investment here is waste. Use `ast`-level regex matching: extract `prefix_rule(` calls and validate field names within.

## Code Examples

### Adapter Protocol Definition
```python
# packages/skilllint/skilllint/adapters/protocol.py
from typing import Protocol, runtime_checkable
from pathlib import PurePath

@runtime_checkable
class PlatformAdapter(Protocol):
    """Structural protocol for platform-specific validators.

    Third-party adapters do NOT import from skilllint to implement this.
    The protocol is satisfied structurally (duck typing).
    """

    @property
    def platform_id(self) -> str:
        """Unique identifier, e.g. 'claude_code', 'cursor', 'codex'."""
        ...

    def path_patterns(self) -> list[str]:
        """Glob patterns this adapter claims ownership of."""
        ...

    def applicable_rules(self) -> set[str]:
        """Rule code prefixes this adapter activates, e.g. {'SK', 'PR', 'HK', 'AS'}."""
        ...

    def get_schema(self, file_type: str) -> dict | None:
        """Return JSON schema dict for a given file_type key, or None."""
        ...
```

### Entry Points Registration
```toml
# pyproject.toml — add under [project]
[project.entry-points."skilllint.adapters"]
claude_code = "skilllint.adapters.claude_code:ClaudeCodeAdapter"
cursor      = "skilllint.adapters.cursor:CursorAdapter"
codex       = "skilllint.adapters.codex:CodexAdapter"
```

### Cursor .mdc Schema (v1.json shape)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Cursor MDC Rule Frontmatter",
  "type": "object",
  "required": ["description"],
  "properties": {
    "description": { "type": "string", "minLength": 1 },
    "globs":       { "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}] },
    "alwaysApply": { "type": "boolean" }
  },
  "additionalProperties": false
}
```
Confidence: HIGH — fields verified via cursor.com/docs/context/rules

### Codex .rules Starlark Field Validation (structural, not full parse)
```python
import re

KNOWN_PREFIX_RULE_FIELDS = {"pattern", "decision", "justification", "match", "not_match"}
VALID_DECISIONS = {"allow", "prompt", "forbidden"}

def validate_rules_file(content: str) -> list[str]:
    """Return list of violation messages for a .rules file."""
    violations = []
    # Find all prefix_rule(...) calls
    calls = re.findall(r'prefix_rule\(([^)]+)\)', content, re.DOTALL)
    for call in calls:
        # Extract field names from keyword arguments
        fields = set(re.findall(r'(\w+)\s*=', call))
        unknown = fields - KNOWN_PREFIX_RULE_FIELDS
        for f in unknown:
            violations.append(f"Unknown prefix_rule field: '{f}'")
    return violations
```
Confidence: HIGH for field names — verified via developers.openai.com/codex/rules/

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pkg_resources.iter_entry_points()` | `importlib.metadata.entry_points(group=...)` | Python 3.10 / importlib-metadata 3.6+ | stdlib only, no setuptools dependency; `pkg_resources` is deprecated |
| ABC-based plugin interfaces | `typing.Protocol` structural subtyping | Python 3.8+ | Eliminates import coupling between plugin and host package |
| Manual schema file paths | `importlib.resources.files()` | Python 3.9+ | Works in wheels, zip imports, editable installs |

**Deprecated/outdated:**
- `pkg_resources.iter_entry_points()`: deprecated, use `importlib.metadata.entry_points()`
- `setup.py entry_points={}`: use `pyproject.toml [project.entry-points."group"]` instead

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, 529 tests passing at end of Phase 1) |
| Config file | `packages/skilllint/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd packages/skilllint && uv run pytest tests/test_adapters.py tests/test_as_series.py -x` |
| Full suite command | `cd packages/skilllint && uv run pytest` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADPT-01 | `PlatformAdapter` Protocol is defined; all three bundled adapters satisfy it without error | unit | `uv run pytest tests/test_adapters.py::test_protocol_conformance -x` | Wave 0 |
| ADPT-01 | `isinstance(adapter, PlatformAdapter)` returns `True` for each bundled adapter | unit | `uv run pytest tests/test_adapters.py::test_runtime_checkable -x` | Wave 0 |
| ADPT-02 | `load_adapters()` discovers all three adapters via entry_points after `uv pip install -e .` | integration | `uv run pytest tests/test_adapters.py::test_entry_points_discovery -x` | Wave 0 |
| ADPT-02 | A mock third-party adapter installed as a separate dist is discovered without core changes | integration | `uv run pytest tests/test_adapters.py::test_third_party_adapter_discovery -x` | Wave 0 |
| ADPT-03 | `skilllint --platform claude-code <file>` validates plugin.json, SKILL.md, agents/*.md, commands/*.md, hooks.json | integration | `uv run pytest tests/test_adapters.py::test_claude_code_adapter_validates_all_file_types -x` | Wave 0 |
| ADPT-03 | Claude Code adapter `path_patterns()` matches `.claude/**/*.md`, `plugin.json`, `hooks.json`, `agents/**/*.md`, `commands/**/*.md` | unit | `uv run pytest tests/test_adapters.py::test_claude_code_path_patterns -x` | Wave 0 |
| ADPT-03 | AS-series rules fire on SKILL.md validated through Claude Code adapter | unit | `uv run pytest tests/test_as_series.py -x` | Wave 0 |
| ADPT-04 | `skilllint --platform cursor <file.mdc>` validates `.mdc` frontmatter fields (description, globs, alwaysApply) | integration | `uv run pytest tests/test_adapters.py::test_cursor_adapter_mdc_validation -x` | Wave 0 |
| ADPT-04 | Cursor adapter rejects `.mdc` with unknown frontmatter fields | unit | `uv run pytest tests/test_adapters.py::test_cursor_mdc_unknown_fields -x` | Wave 0 |
| ADPT-04 | Cursor adapter validates SKILL.md using AS-series | unit | `uv run pytest tests/test_adapters.py::test_cursor_skill_md_uses_as_series -x` | Wave 0 |
| ADPT-05 | `skilllint --platform codex <AGENTS.md>` checks presence and non-empty content | unit | `uv run pytest tests/test_adapters.py::test_codex_agents_md_validation -x` | Wave 0 |
| ADPT-05 | `skilllint --platform codex <file.rules>` validates known `prefix_rule()` fields; reports unknown fields | unit | `uv run pytest tests/test_adapters.py::test_codex_rules_field_validation -x` | Wave 0 |
| ADPT-05 | Codex adapter path patterns match `.agents/skills/**/*.md`, `AGENTS.md`, `**/*.rules`, `.codex/**` | unit | `uv run pytest tests/test_adapters.py::test_codex_path_patterns -x` | Wave 0 |

### Success Criterion Coverage

**SC1 — Protocol defined + adapters implement:**
- `tests/test_adapters.py::test_protocol_conformance` — instantiates each bundled adapter, asserts `isinstance(adapter, PlatformAdapter)` is `True`
- `tests/test_adapters.py::test_runtime_checkable` — verifies `@runtime_checkable` enables isinstance without inheritance
- Fixture: three minimal adapter instances (no I/O), protocol module importable

**SC2 — entry_points discovery:**
- `tests/test_adapters.py::test_entry_points_discovery` — calls `load_adapters()` in an installed editable package, asserts all three adapter IDs present
- `tests/test_adapters.py::test_third_party_adapter_discovery` — uses `importlib.metadata` dist mocking (or a minimal in-tree test dist) to simulate a fourth adapter installed by a separate package; verifies it appears in `load_adapters()` without modifying core
- Fixture: `conftest.py` ensures package is installed (`uv pip install -e .` or via pytest-dev fixture)

**SC3 — claude-code platform validation:**
- `tests/test_adapters.py::test_claude_code_adapter_validates_all_file_types` — runs `validate_file()` against fixture files for each of: `plugin.json`, `SKILL.md`, `agents/foo.md`, `commands/bar.md`, `hooks.json`; asserts no false positives on valid files; asserts expected violations on invalid files
- `tests/test_as_series.py` — full AS-series rule coverage (AS001–AS006) against SKILL.md fixtures; existing `test_name_format_validator.py` and `test_description_validator.py` tests extend naturally here
- Fixtures: `tests/fixtures/claude_code/` directory with valid and invalid examples of each file type

**SC4 — cursor + codex platform validation:**
- `tests/test_adapters.py::test_cursor_adapter_mdc_validation` — validates `.mdc` files with correct/incorrect frontmatter; asserts `description` required, `alwaysApply` must be boolean, unknown fields rejected
- `tests/test_adapters.py::test_codex_rules_field_validation` — validates `.rules` files for `prefix_rule()` field names; unknown fields produce violations; `decision` values validated against `{"allow", "prompt", "forbidden"}`
- `tests/test_adapters.py::test_codex_agents_md_validation` — empty `AGENTS.md` produces violation; non-empty passes
- Fixtures: `tests/fixtures/cursor/` and `tests/fixtures/codex/` directories with valid and invalid examples

### Sampling Rate
- **Per task commit:** `cd packages/skilllint && uv run pytest tests/test_adapters.py tests/test_as_series.py -x`
- **Per wave merge:** `cd packages/skilllint && uv run pytest`
- **Phase gate:** Full suite green (including pre-existing 529 tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `packages/skilllint/tests/test_adapters.py` — covers ADPT-01, ADPT-02, ADPT-03, ADPT-04, ADPT-05
- [ ] `packages/skilllint/tests/test_as_series.py` — covers AS001–AS006 cross-platform rules
- [ ] `packages/skilllint/tests/fixtures/claude_code/` — valid/invalid plugin.json, SKILL.md, agents/*.md, commands/*.md, hooks.json
- [ ] `packages/skilllint/tests/fixtures/cursor/` — valid/invalid .mdc files, SKILL.md
- [ ] `packages/skilllint/tests/fixtures/codex/` — valid/invalid AGENTS.md, .rules files, SKILL.md

## Open Questions

1. **Cursor SKILL.md loading from `.claude/skills/` — confirmed or community convention?**
   - What we know: Multiple community sources confirm Cursor loads from `.claude/skills/`; Cursor's own changelog (2.4) confirms agentskills.io SKILL.md support; unified skills symlink pattern is widely documented
   - What's unclear: Whether Cursor's official docs explicitly list `.claude/skills/` as a first-class location vs. incidental compatibility
   - Recommendation: Include `.claude/skills/**/*.md` in the Cursor adapter path patterns with MEDIUM confidence; the planner should note this is validated at implementation time

2. **GitHub Copilot CLI adapter — v1 or v2 scope?**
   - What we know: Copilot loads from `.github/skills/` and `.claude/skills/` (project), `~/.copilot/skills/` and `~/.claude/skills/` (user); uses identical agentskills.io SKILL.md format; AS-series fully applies
   - What's unclear: CONTEXT.md does not lock the Copilot adapter into Phase 2 or defer it explicitly
   - Recommendation: Treat as out of scope for Phase 2. REQUIREMENTS.md lists only ADPT-01 through ADPT-05. The adapter would be trivial but is not a stated deliverable.

3. **Starlark `.rules` parsing depth**
   - What we know: Format is explicitly experimental per OpenAI docs; `prefix_rule()` fields are `pattern`, `decision`, `justification`, `match`, `not_match`
   - What's unclear: Whether Codex will change the format between Phase 2 planning and implementation
   - Recommendation: Use structural regex validation (not a Starlark AST parser) for Phase 2. Mark as provisional in the adapter's `get_schema()` docstring.

## Sources

### Primary (HIGH confidence)
- [agentskills.io/specification](https://agentskills.io/specification) — SKILL.md frontmatter fields: name, description, license, metadata
- [agentskills.io/client-implementation/adding-skills-support](https://agentskills.io/client-implementation/adding-skills-support) — loading location conventions
- [cursor.com/docs/context/rules](https://cursor.com/docs/context/rules) — `.mdc` frontmatter: description, globs, alwaysApply
- [cursor.com/docs/context/skills](https://cursor.com/docs/context/skills) — Cursor SKILL.md loading from `.cursor/skills/`
- [developers.openai.com/codex/skills/](https://developers.openai.com/codex/skills/) — Codex skill format, `.agents/skills/`, `~/.codex/skills/`
- [developers.openai.com/codex/rules/](https://developers.openai.com/codex/rules/) — `prefix_rule()` fields: pattern, decision, justification, match, not_match
- [developers.openai.com/codex/guides/agents-md/](https://developers.openai.com/codex/guides/agents-md/) — AGENTS.md loading behavior
- [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills) — Claude Code skill loading from `.claude/skills/`, `~/.claude/skills/`
- [docs.python.org/3/library/importlib.metadata.html](https://docs.python.org/3/library/importlib.metadata.html) — entry_points() API
- [typing.python.org/en/latest/reference/protocols.html](https://typing.python.org/en/latest/reference/protocols.html) — Protocol structural subtyping
- [packaging.python.org/en/latest/guides/creating-and-discovering-plugins/](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) — pyproject.toml entry-points syntax

### Secondary (MEDIUM confidence)
- [docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-skills) — GitHub Copilot CLI loading from `.github/skills/`, `.claude/skills/`, `~/.copilot/skills/`
- [opencode.ai/docs/skills/](https://opencode.ai/docs/skills/) — OpenCode loads `.agents/skills/` for agentskills.io compatibility
- Community sources confirming `.claude/skills/` as Cursor-compatible location

### Tertiary (LOW confidence)
- Community forum posts about Cursor duplicate skills loading from multiple directories — flags implementation risk but needs official confirmation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or already in project
- Architecture: HIGH — Protocol + entry_points pattern is well-established Python
- Platform loading locations: HIGH (Claude Code, Codex), MEDIUM (Cursor `.claude/skills/` compat)
- `.mdc` schema fields: HIGH — verified via official Cursor docs
- Codex `.rules` fields: HIGH — verified via official OpenAI docs
- AS-series rule derivation: HIGH — derived directly from agentskills.io spec
- Pitfalls: HIGH — all grounded in verified technical facts
- Validation Architecture: HIGH — test file locations match existing project conventions in `packages/skilllint/tests/`

**Research date:** 2026-03-09
**Valid until:** 2026-06-09 (stable Python stdlib patterns); `.rules` Starlark format flagged as experimental — re-verify before implementation
