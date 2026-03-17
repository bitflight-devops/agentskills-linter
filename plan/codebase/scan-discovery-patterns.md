# Scan Discovery and File Type Patterns

**Analysis Date**: 2026-03-17 (updated post-implementation of scan context detection)
**Scope**: How skilllint discovers and classifies files during validation

---

## 1. Scan Entry Points

### CLI Entry Point Flow

The scan discovery process begins when `skilllint check <path>` is invoked and flows through:

1. **CLI invocation** → `plugin_validator.py` (main CLI handler)
2. **Path expansion** → `scan_runtime.py::_resolve_filter_and_expand_paths()`
3. **Validation loop** → `scan_runtime.py::run_validation_loop()`

### Key Functions

#### `_resolve_filter_and_expand_paths()`
**Location**: `packages/skilllint/scan_runtime.py:275-319`

**Signature**:
```python
def _resolve_filter_and_expand_paths(
    paths: list[Path],
    filter_glob: str | None,
    filter_type: str | None
) -> tuple[list[Path], bool]
```

**Purpose**: Validates mutual exclusion of `--filter` and `--filter-type` flags, resolves filter types to glob patterns, and expands directory paths.

**Logic Flow**:
- Lines 289-296: Raise error if both `--filter` and `--filter-type` specified (mutually exclusive), or if `filter_type` is not in `FILTER_TYPE_MAP`
- Lines 301-308: Context-aware glob resolution when `filter_type` is set:
  - If path is a directory with `ScanContext.PLUGIN` → use `PLUGIN_FILTER_TYPE_MAP` (root-only globs, no `**` recursion into skill subtrees)
  - Otherwise → use `FILTER_TYPE_MAP` (deep recursive globs)
- Lines 310-318: Expand paths:
  - **If resolved glob + path is directory**: Apply glob, add results in batch mode
  - **If no glob + path is directory**: Delegate to `_discover_validatable_paths()` (context dispatch)
  - **If path is file**: Return as-is

**Return**: Tuple of `(expanded_paths: list[Path], is_batch: bool)`

#### `_discover_validatable_paths()`
**Location**: `packages/skilllint/scan_runtime.py:210-272`

**Signature**:
```python
def _discover_validatable_paths(directory: Path) -> list[Path]
```

**Purpose**: Context dispatcher — detects the scan context of the directory and routes to the appropriate discovery function.

**Logic**:
- Line 226: Call `detect_scan_context(directory)` to determine context
- Lines 228-230: `PLUGIN` → parse manifest via `_parse_plugin_manifest()`, discover via `_discover_plugin_paths()`
- Lines 232-233: `PROVIDER` → discover via `_discover_provider_paths()`
- Lines 235-272: `BARE` → three-phase discovery:
  1. Find all nested plugin roots via `**/.claude-plugin/plugin.json`; for each, call `_discover_plugin_paths()`
  2. Find all nested provider directories matching `KNOWN_PROVIDER_DIRS`; skip those inside plugin trees; for each, call `_discover_provider_paths()`
  3. Apply `DEFAULT_SCAN_PATTERNS` for any files not already covered by a plugin or provider subtree

**Return**: Sorted, deduplicated `list[Path]` of paths suitable for validation

#### `run_validation_loop()`
**Location**: `packages/skilllint/scan_runtime.py:413-475`

**Signature**:
```python
def run_validation_loop(
    *,
    expanded_paths: list[Path],
    check: bool,
    fix: bool,
    verbose: bool,
    no_color: bool,
    show_progress: bool,
    show_summary: bool,
    platform_override: str | None,
    validate_single_path: ValidateSinglePathFn,
    validate_file: ValidateFileFn,
    violations_to_result: ViolationsToResultFn,
    adapters: dict[str, object],
) -> NoReturn
```

**Purpose**: Execute validation loop, report results, and exit with appropriate exit code.

**Flow**:
- Line 450: Load ignore patterns from `.pluginvalidatorignore` or `.claude/.pluginvalidatorignore`
- Lines 452-464: Iterate expanded paths:
  - Line 453: Skip if matched by ignore patterns
  - Lines 455-457: If platform override specified, validate with specific adapter
  - Lines 458-464: Otherwise, validate via `validate_single_path()` callback (validates against all applicable adapters)
- Line 466: Create reporter (CI or Console based on `no_color`)
- Lines 467-471: Report results and optionally show summary
- Lines 473-474: Exit with code 0 (success) or 1 (failures)

---

## 2. File Type Classification

### FileType Enum
**Location**: `packages/skilllint/plugin_validator.py` (search results indicate presence)

The FileType enum is referenced throughout the codebase but specific definition not located in first 300 lines. However, the supported types are evident from:
- Default scan patterns (§5)
- Validator ownership mappings (line 427-442 of plugin_validator.py)
- Error codes (FM001-FM010, SK001-SK009, PL001-PL005, etc.)

**Supported File Types**:
1. **Skill**: `**/skills/*/SKILL.md` files (required filename)
2. **Agent**: `**/agents/*.md` files (any markdown file in agents directory)
3. **Command**: `**/commands/*.md` files (any markdown file in commands directory)
4. **Plugin**: Directories containing `.claude-plugin/plugin.json`
5. **Hooks**: `**/hooks/hooks.json` files (configuration file)
6. **CLAUDE.md**: Project-level configuration/documentation files

### File Type Detection

#### `detect_file_type()` Function
**Location**: `packages/skilllint/plugin_validator.py`

The function:
- Takes a `Path` parameter
- Returns a classification (plugin, skill, agent, command, hooks, or claude.md)
- Recognizes **directories** containing `.claude-plugin/plugin.json` as plugins (not the JSON file itself)
- Context detection in `_discover_validatable_paths()` ensures plugin root directories (not bare `plugin.json` files) are passed to the validation loop

---

## 3. Plugin Detection

### Plugin Root Directory Location
**Location**: `packages/skilllint/plugin_validator.py:105-121`

#### `find_plugin_dir()` Function

**Signature**:
```python
def find_plugin_dir(path: Path) -> Path | None
```

**Purpose**: Find the plugin directory containing `.claude-plugin/plugin.json` by walking up directory tree.

**Logic** (lines 117-121):
- Start from `path.parent` if path is a file, otherwise from path itself
- Walk up directory tree checking each level
- Return first parent where `.claude-plugin/plugin.json` exists
- Return `None` if not found

### Plugin Detection in Path Expansion

**Location**: `scan_runtime.py:314-316`

When a directory path is provided without filters, `_resolve_filter_and_expand_paths()` delegates unconditionally to `_discover_validatable_paths()`:

```python
elif resolved_glob is None and path.is_dir():
    expanded_paths.extend(_discover_validatable_paths(path))
```

The explicit `.claude-plugin/plugin.json` existence check that previously lived in `_resolve_filter_and_expand_paths()` has been removed. Plugin detection is now handled entirely by `detect_scan_context()` inside `_discover_validatable_paths()`.

**Behavior**:
- `_discover_validatable_paths()` calls `detect_scan_context()` and routes to `_discover_plugin_paths()` when the directory is a plugin root
- `_discover_plugin_paths()` adds the plugin root directory itself plus all component files (skills, agents, commands, hooks, CLAUDE.md)
- For bare directories, nested plugin roots are discovered recursively before falling back to `DEFAULT_SCAN_PATTERNS`

---

## 4. Provider Detection and Adapters

### Adapter Architecture

#### Protocol Definition
**Location**: `packages/skilllint/adapters/protocol.py:16-46`

**PlatformAdapter Protocol** (runtime_checkable):
```python
@runtime_checkable
class PlatformAdapter(Protocol):
    def id(self) -> str
        """Unique platform identifier (e.g. 'claude_code', 'cursor')"""

    def path_patterns(self) -> list[str]
        """Glob patterns matching files this adapter handles"""

    def applicable_rules(self) -> set[str]
        """Rule-series codes this adapter applies (e.g. {'AS', 'CC'})"""

    def constraint_scopes(self) -> set[str]
        """Provider schema constraint_scope values ('shared' or 'provider_specific')"""

    def validate(self, path: pathlib.Path) -> list[dict]
        """Validate file and return violation dicts"""
```

**Key Features**:
- Structural subtyping (no inheritance required) via `@runtime_checkable`
- Any class implementing all five methods satisfies the protocol
- Adapters are platform-specific validators (Claude Code, Cursor, etc.)

#### Adapter Loading and Registration
**Location**: `packages/skilllint/adapters/registry.py:22-53`

**Function**: `load_adapters()`

**Signature**:
```python
def load_adapters() -> list[PlatformAdapter]
```

**Logic**:
- Line 33: Use `importlib.metadata.entry_points(group="skilllint.adapters")`
- Lines 35-37: Load and instantiate each entry point
- Returns list of adapter instances

**Entry Point Discovery**: Adapters are registered via `pyproject.toml`:
- Bundled adapters: Registered in project's `pyproject.toml`
- Third-party adapters: Can register without modifying core

**Adapter Registration in Core** (plugin_validator.py:88):
```python
ADAPTERS: dict[str, object] = {a.id(): a for a in load_adapters()}
```

Maps adapter IDs (e.g., "claude_code", "cursor") to adapter instances.

#### Path Pattern Matching
**Location**: `packages/skilllint/adapters/registry.py:41-53`

**Function**: `matches_file()`

**Signature**:
```python
def matches_file(adapter: PlatformAdapter, path: pathlib.PurePath) -> bool
```

**Logic** (lines 52-53):
```python
return any(path.match(pattern) for pattern in adapter.path_patterns())
```

Checks if path matches ANY of adapter's glob patterns using `PurePath.match()`.

### Known Adapters

**ClaudeCodeAdapter**
**Location**: `packages/skilllint/adapters/claude_code.py` (referenced at plugin_validator.py:56)

Validates Claude Code platform-specific requirements. Specific path_patterns() and rules not shown in first read.

### Provider Context Detection

Adapters detect provider contexts by:
1. **Path patterns** in `path_patterns()` method
2. Provider-specific validation rules in `applicable_rules()`
3. Constraint scopes (`shared` vs `provider_specific`) determine which validators run

Example flow:
- If file matches adapter's path patterns → adapter is applicable
- If adapter's constraint_scopes includes "provider_specific" → provider-specific validators run
- Otherwise only "shared" validators run

---

## 5. Scan Context Detection

### ScanContext Enum
**Location**: `packages/skilllint/scan_runtime.py:43-48`

```python
class ScanContext(StrEnum):
    PLUGIN = "plugin"
    PROVIDER = "provider"
    BARE = "bare"
```

Three mutually exclusive contexts classify any target directory:
- **PLUGIN**: Directory is a plugin root (contains `.claude-plugin/plugin.json`)
- **PROVIDER**: Directory name matches a known provider prefix (`.claude`, `.cursor`, `.gemini`, `.codex`)
- **BARE**: Neither — typically a workspace root or arbitrary directory containing nested structures

### KNOWN_PROVIDER_DIRS
**Location**: `packages/skilllint/scan_runtime.py:51`

```python
KNOWN_PROVIDER_DIRS: frozenset[str] = frozenset({".claude", ".cursor", ".gemini", ".codex"})
```

Provider directory names recognized by context detection. Matched against `directory.name`.

### `detect_scan_context()`
**Location**: `packages/skilllint/scan_runtime.py:163-185`

**Signature**:
```python
def detect_scan_context(directory: Path) -> ScanContext
```

**Decision order** (first match wins):
1. If `.claude-plugin/plugin.json` exists inside directory → `PLUGIN`
2. If `directory.name` is in `KNOWN_PROVIDER_DIRS` → `PROVIDER`
3. Otherwise → `BARE`

Plugin check takes precedence: a `.claude/` directory that also contains `.claude-plugin/plugin.json` is classified as `PLUGIN`.

### `PluginManifest` Dataclass
**Location**: `packages/skilllint/scan_runtime.py:65-77`

```python
@dataclass(frozen=True)
class PluginManifest:
    plugin_root: Path
    agents: list[str] | None = None
    commands: list[str] | None = None
    skills: list[str] | None = None
```

Parsed representation of `plugin.json` path declarations. `is_manifest_driven` property returns `True` if any field is not `None`.

### `_parse_plugin_manifest()`
**Location**: `packages/skilllint/scan_runtime.py:80-106`

**Signature**:
```python
def _parse_plugin_manifest(plugin_root: Path) -> PluginManifest
```

Reads `.claude-plugin/plugin.json` and extracts `agents`, `commands`, and `skills` list fields. Returns an all-`None` manifest on read/parse errors (convention-driven fallback).

### `_discover_plugin_paths()`
**Location**: `packages/skilllint/scan_runtime.py:109-155`

**Signature**:
```python
def _discover_plugin_paths(manifest: PluginManifest) -> list[Path]
```

Two modes controlled by `manifest.is_manifest_driven`:

| Mode | Source | Glob depth |
|---|---|---|
| Manifest-driven | Declared paths in plugin.json | No globbing — resolves declared paths exactly |
| Convention-driven | Directory structure | Root-only: `agents/*.md`, `commands/*.md`, `skills/*/SKILL.md` |

Always adds: plugin root directory, `hooks/hooks.json` (if present), `CLAUDE.md` (if present).

Never recurses into `skills/*/agents/` or `skills/*/commands/` — skills are validated as opaque units.

### `_discover_provider_paths()`
**Location**: `packages/skilllint/scan_runtime.py:188-202`

**Signature**:
```python
def _discover_provider_paths(directory: Path) -> list[Path]
```

Discovers agent files in a provider directory using `agents/**/*.md`. No other files in the provider tree are discovered. Returns a sorted list of unique paths.

---

## 6. Filter Type System

### FILTER_TYPE_MAP
**Location**: `packages/skilllint/scan_runtime.py:26-30`

```python
FILTER_TYPE_MAP: dict[str, str] = {
    "skills": "**/skills/*/SKILL.md",
    "agents": "**/agents/*.md",
    "commands": "**/commands/*.md",
}
```

**Behavior**:
- Maps user-provided `--filter-type` values to deep recursive glob patterns
- Used when the scan target is a bare directory or provider directory
- Each pattern is applied only when the user specifies `--filter-type <key>`

### PLUGIN_FILTER_TYPE_MAP
**Location**: `packages/skilllint/scan_runtime.py:53-57`

```python
PLUGIN_FILTER_TYPE_MAP: dict[str, str] = {
    "skills": "skills/*/SKILL.md",
    "agents": "agents/*.md",
    "commands": "commands/*.md",
}
```

**Behavior**:
- Equivalent keys to `FILTER_TYPE_MAP` but uses root-only globs (no `**` prefix)
- Used when `_resolve_filter_and_expand_paths()` detects `ScanContext.PLUGIN` for the target directory
- Prevents matching agent/command files nested inside skill subdirectories (e.g., `skills/my-skill/agents/helper.md`)
- Contrast with `FILTER_TYPE_MAP`: `"agents": "**/agents/*.md"` would inadvertently match skill-internal agents

### Pattern Recursion Analysis

| Filter Type | Pattern | Recursion | Scope |
|---|---|---|---|
| skills | `**/skills/*/SKILL.md` | Deep recursive (`**`) | Matches `SKILL.md` one level deep inside any `skills/` directory at any depth |
| agents | `**/agents/*.md` | Deep recursive (`**`) | Matches any `.md` file directly in `agents/` directory at any depth |
| commands | `**/commands/*.md` | Deep recursive (`**`) | Matches any `.md` file directly in `commands/` directory at any depth |

All three patterns use `**` prefix, enabling discovery at any directory depth. However, they constrain matches by:
- **skills**: Exact filename `SKILL.md` + exact depth (one level inside skill dir)
- **agents**: Exact depth (direct child of agents dir) + any `.md` filename
- **commands**: Exact depth (direct child of commands dir) + any `.md` filename

### DEFAULT_SCAN_PATTERNS
**Location**: `packages/skilllint/scan_runtime.py:33-40`

```python
DEFAULT_SCAN_PATTERNS: tuple[str, ...] = (
    "**/skills/*/SKILL.md",
    "**/agents/*.md",
    "**/commands/*.md",
    "**/.claude-plugin/plugin.json",
    "**/hooks/hooks.json",
    "**/CLAUDE.md",
)
```

Used by `_discover_validatable_paths()` in `BARE` context only — for files not already covered by a discovered plugin or provider subtree. Adds:
- `**/.claude-plugin/plugin.json` (plugin structure file at any depth; resolved to grandparent plugin root)
- `**/hooks/hooks.json` (hooks configuration at any depth)
- `**/CLAUDE.md` (Claude Code configuration file at any depth)

Not used in `PLUGIN` or `PROVIDER` context — those dispatch to `_discover_plugin_paths()` and `_discover_provider_paths()` respectively.

---

## 7. FRONTMATTER_EXEMPT_FILENAMES

### Definition
**Location**: `packages/skilllint/plugin_validator.py:536-543`

```python
FRONTMATTER_EXEMPT_FILENAMES: frozenset[str] = frozenset({
    "AGENT.md",
    "AGENTS.md",
    "GEMINI.md",
    # ... (more entries visible in grep output)
})
```

**Purpose**: Filenames exempt from frontmatter requirement (case-sensitive).

### Usage Locations

1. **Plugin Registration Validator** (plugin_validator.py:3248)
   - Excludes exempt files when discovering actual agents
   - Used to identify which agents are registered in plugin.json

2. **Plugin Registration Validator** (plugin_validator.py:3254)
   - Excludes exempt files when discovering actual commands
   - Used to identify which commands are registered in plugin.json

3. **Plugin Registration Validator** (plugin_validator.py:3282)
   - Excludes exempt files when expanding directory paths in plugin.json
   - Allows glob path references that match multiple files

4. **PA Series Validator** (pa_series.py:360)
   - Skips validation of exempt agent files
   - Prevents validating template/reference agents that shouldn't have frontmatter

5. **Frontmatter Requirement Detector** (plugin_validator.py:4486)
   - Exempts files from frontmatter requirement check
   - Returns `_FrontmatterRequirement.EXEMPT` for these files

### Why Files Are Exempt

Exempt filenames are typically:
- Template/reference files (AGENT.md, AGENTS.md, etc.)
- Platform-specific documentation (GEMINI.md, etc.)
- Files that serve as examples or documentation, not actual skills/agents/commands

These files:
- Are NOT included in plugin.json component registration
- Do NOT require frontmatter metadata
- Are discovered by path matching but excluded from frontmatter validation

---

## End-to-End Scan Flow Example

### Scenario: `skilllint check /path/to/plugin`

1. **Input**: Directory path without filters

2. **Path Resolution** (`_resolve_filter_and_expand_paths`):
   - No filter specified → `resolved_glob` is `None`
   - Path is a directory → delegate to `_discover_validatable_paths()`

3. **Context Detection** (`detect_scan_context`):
   - Check if `/path/to/plugin/.claude-plugin/plugin.json` exists → `ScanContext.PLUGIN`
   - Check if directory name is in `KNOWN_PROVIDER_DIRS` → `ScanContext.PROVIDER`
   - Otherwise → `ScanContext.BARE`

4. **Context Dispatch** (`_discover_validatable_paths`):
   - `PLUGIN`: Parse manifest via `_parse_plugin_manifest()`, call `_discover_plugin_paths()`
   - `PROVIDER`: Call `_discover_provider_paths()` (returns `agents/**/*.md`)
   - `BARE`: Recursively discover nested plugins and providers, then apply `DEFAULT_SCAN_PATTERNS` for uncovered files

5. **Plugin discovery** (`_discover_plugin_paths`, manifest-driven or convention-driven):
   - **Manifest-driven** (plugin.json declares paths): Resolve exactly the declared paths
   - **Convention-driven** (no declared paths): Glob `agents/*.md`, `commands/*.md`, `skills/*/SKILL.md` at plugin root only (no `**`)
   - Always adds: plugin root dir itself, `hooks/hooks.json` if present, `CLAUDE.md` if present

6. **Example discovered paths** (plugin at `/path/to/plugin/`):
   ```
   /path/to/plugin/                              # plugin root (always added)
   /path/to/plugin/skills/my-skill/SKILL.md
   /path/to/plugin/agents/helper.md
   /path/to/plugin/commands/run.md
   /path/to/plugin/hooks/hooks.json
   /path/to/plugin/CLAUDE.md
   ```

7. **Validation Loop** (`run_validation_loop`):
   - Load ignore patterns from `.pluginvalidatorignore`
   - For each path:
     - Skip if ignored
     - Match against registered adapters (`matches_file`)
     - Run applicable validators for matched adapters
   - Collect and report violations

8. **Exit**: Code 0 if no failures, code 1 if any failures

---

## Summary Table

| Component | Location | Purpose |
|-----------|----------|---------|
| `_resolve_filter_and_expand_paths()` | scan_runtime.py:275-319 | Parse CLI filter options, expand directory paths with context-aware glob selection |
| `_discover_validatable_paths()` | scan_runtime.py:210-272 | Context dispatcher: routes to plugin, provider, or bare discovery |
| `detect_scan_context()` | scan_runtime.py:163-185 | Classify directory as PLUGIN, PROVIDER, or BARE |
| `_discover_plugin_paths()` | scan_runtime.py:109-155 | Discover plugin component files (manifest-driven or convention-driven) |
| `_discover_provider_paths()` | scan_runtime.py:188-202 | Discover agent files in a provider directory |
| `_parse_plugin_manifest()` | scan_runtime.py:80-106 | Parse plugin.json path declarations into PluginManifest |
| `run_validation_loop()` | scan_runtime.py:413-475 | Execute validation, handle ignore patterns, report results |
| `find_plugin_dir()` | plugin_validator.py:105-121 | Walk directory tree to find plugin root |
| `PlatformAdapter` protocol | adapters/protocol.py:16-46 | Define adapter interface (id, path_patterns, validate, etc.) |
| `load_adapters()` | adapters/registry.py:22-38 | Load adapters via importlib.metadata entry points |
| `matches_file()` | adapters/registry.py:41-53 | Check if path matches adapter's glob patterns |
| `ScanContext` | scan_runtime.py:43-48 | Enum: PLUGIN / PROVIDER / BARE |
| `PluginManifest` | scan_runtime.py:65-77 | Frozen dataclass holding parsed plugin.json path declarations |
| `FILTER_TYPE_MAP` | scan_runtime.py:26-30 | Map --filter-type values to deep recursive glob patterns |
| `PLUGIN_FILTER_TYPE_MAP` | scan_runtime.py:53-57 | Map --filter-type values to root-only globs for plugin directories |
| `KNOWN_PROVIDER_DIRS` | scan_runtime.py:51 | frozenset of provider directory names (.claude, .cursor, .gemini, .codex) |
| `DEFAULT_SCAN_PATTERNS` | scan_runtime.py:33-40 | Default glob patterns for bare directory auto-discovery |
| `FRONTMATTER_EXEMPT_FILENAMES` | plugin_validator.py:536-543 | Files exempt from frontmatter requirement |
