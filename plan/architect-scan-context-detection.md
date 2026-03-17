# Architecture: Context-Aware Scan Discovery

## Overview

The scanner currently uses flat `**` glob patterns that recurse into all subdirectories, causing false positives when skill-internal files match agent/command patterns. This design introduces a **scan context** layer that identifies the kind of directory being scanned *before* file discovery, then applies context-appropriate discovery rules.

## Data Model

### ScanContext Enum

```python
# In scan_runtime.py

class ScanContext(StrEnum):
    """The structural context of a scan target directory."""

    PLUGIN = "plugin"       # Has .claude-plugin/plugin.json
    PROVIDER = "provider"   # Is a provider directory (.claude/, .cursor/, .gemini/, etc.)
    BARE = "bare"           # Anything else — fallback to recursive globs
```

**Why an enum, not a class hierarchy**: The context only selects which discovery strategy to use. It carries no behavior of its own. A class hierarchy would be over-engineering for a three-way branch.

### PluginManifest (lightweight data holder)

```python
@dataclass(frozen=True)
class PluginManifest:
    """Parsed paths from plugin.json, if declared."""

    plugin_root: Path
    agents: list[str] | None = None    # Explicit agent paths from manifest
    commands: list[str] | None = None   # Explicit command paths from manifest
    skills: list[str] | None = None     # Explicit skill paths from manifest

    @property
    def is_manifest_driven(self) -> bool:
        """True if plugin.json declares any explicit paths."""
        return any(v is not None for v in (self.agents, self.commands, self.skills))
```

**Source for manifest fields**: `plugin.json` schema supports `"agents"`, `"commands"`, and custom path arrays per the resolved Q1 from the team lead.

## Module Interfaces

All new code lives in `scan_runtime.py` (resolved Q6). No new modules.

### Context Detection

```python
def detect_scan_context(directory: Path) -> ScanContext:
    """Identify the scan context of a directory.

    Decision order:
    1. If directory contains .claude-plugin/plugin.json -> PLUGIN
    2. If directory name matches a known provider prefix (.claude, .cursor,
       .gemini, etc.) -> PROVIDER
    3. Otherwise -> BARE

    Args:
        directory: The target directory to classify.

    Returns:
        ScanContext enum value.
    """
```

**Provider detection**: Match against a `KNOWN_PROVIDER_DIRS` frozenset:

```python
KNOWN_PROVIDER_DIRS: frozenset[str] = frozenset({
    ".claude", ".cursor", ".gemini", ".codex",
})
```

This is the same set the existing adapters cover. New providers are added here and in `adapters/` simultaneously.

### Manifest Parsing

```python
def _parse_plugin_manifest(plugin_root: Path) -> PluginManifest:
    """Read plugin.json and extract declared paths.

    If plugin.json has no path declarations, all fields are None
    (convention-driven mode).

    Args:
        plugin_root: Directory containing .claude-plugin/plugin.json.

    Returns:
        PluginManifest with parsed paths or None fields.
    """
```

### Context-Aware Discovery

```python
def _discover_plugin_paths(manifest: PluginManifest) -> list[Path]:
    """Discover validatable files in a plugin directory.

    Two modes:
    - Manifest-driven: Use exactly the paths declared in plugin.json.
      No globbing beyond resolving the declared paths.
    - Convention-driven: Glob at plugin root only (no ** recursion):
        - {plugin_root}/agents/*.md
        - {plugin_root}/commands/*.md
        - {plugin_root}/skills/*/SKILL.md
        - {plugin_root}/.claude-plugin/plugin.json (as plugin root)
        - {plugin_root}/hooks/hooks.json
        - {plugin_root}/CLAUDE.md

    Never recurses into skills/*/agents/ or skills/*/commands/.

    Args:
        manifest: Parsed plugin manifest.

    Returns:
        Sorted list of unique paths.
    """


def _discover_provider_paths(directory: Path) -> list[Path]:
    """Discover validatable files in a provider directory.

    Uses the provider's known agent location pattern:
        {directory}/agents/**/*.md

    No other files in the provider tree are discovered as agents.

    Args:
        directory: The provider directory (e.g., .claude/).

    Returns:
        Sorted list of unique paths.
    """
```

## Integration with Existing Functions

### `_discover_validatable_paths` — replaced per-context

The current function applies `DEFAULT_SCAN_PATTERNS` uniformly. After this change, it becomes a dispatcher:

```python
def _discover_validatable_paths(directory: Path) -> list[Path]:
    """Auto-discover validatable files using context-appropriate rules.

    1. Detect scan context.
    2. Dispatch to context-specific discovery function.
    3. For BARE context with nested plugins/providers, recurse into
       each subtree with its own context.

    Args:
        directory: The directory to scan.

    Returns:
        Sorted list of unique paths suitable for validation.
    """
    context = detect_scan_context(directory)

    if context == ScanContext.PLUGIN:
        manifest = _parse_plugin_manifest(directory)
        return _discover_plugin_paths(manifest)

    if context == ScanContext.PROVIDER:
        return _discover_provider_paths(directory)

    # BARE context: check for nested plugins and providers
    discovered: set[Path] = set()

    # Find nested plugin roots
    for plugin_json in directory.glob("**/.claude-plugin/plugin.json"):
        plugin_root = plugin_json.parent.parent
        manifest = _parse_plugin_manifest(plugin_root)
        discovered.update(_discover_plugin_paths(manifest))

    # Find nested provider directories
    for provider_name in KNOWN_PROVIDER_DIRS:
        for provider_dir in directory.glob(f"**/{provider_name}"):
            if provider_dir.is_dir():
                # Skip provider dirs inside plugin trees (Q2: plugin takes precedence)
                if any(_is_within_plugin(provider_dir, pr) for pr in _plugin_roots):
                    continue
                discovered.update(_discover_provider_paths(provider_dir))

    # Files outside any plugin/provider subtree: use legacy glob patterns
    # but only for paths not already covered
    for pattern in DEFAULT_SCAN_PATTERNS:
        for match in directory.glob(pattern):
            resolved = match.parent.parent if match.name == "plugin.json" else match
            if not _is_within_any_context(resolved, discovered):
                discovered.add(resolved)

    return sorted(discovered)
```

### `_resolve_filter_and_expand_paths` — filter interaction

Per resolved Q5: **explicit filter overrides context**. When the user passes `--filter` or `--filter-type`, the filter glob is applied as-is, bypassing context-aware discovery. This matches CLI conventions (explicit flags override defaults).

The existing code path at lines 99-101 of `scan_runtime.py` already handles this:

```python
if resolved_glob is not None and path.is_dir():
    matched = sorted(path.glob(resolved_glob))
    expanded_paths.extend(matched)
```

No change needed here. Context-aware discovery only affects the `resolved_glob is None` branch (lines 103-110), which calls `_discover_validatable_paths`.

However, `--filter-type` should be context-aware in PLUGIN mode. The `FILTER_TYPE_MAP` patterns use `**` recursion. For plugin context, `--filter-type agents` should resolve to `agents/*.md` (root-only), not `**/agents/*.md`. This requires a small change:

```python
# In _resolve_filter_and_expand_paths, when filter_type is set:
if filter_type is not None:
    context = detect_scan_context(path) if path.is_dir() else ScanContext.BARE
    if context == ScanContext.PLUGIN:
        resolved_glob = PLUGIN_FILTER_TYPE_MAP.get(filter_type, FILTER_TYPE_MAP[filter_type])
    else:
        resolved_glob = FILTER_TYPE_MAP[filter_type]
```

With a new constant:

```python
PLUGIN_FILTER_TYPE_MAP: dict[str, str] = {
    "skills": "skills/*/SKILL.md",
    "agents": "agents/*.md",
    "commands": "commands/*.md",
}
```

### `FileType.detect_file_type` — context parameter

The current `detect_file_type` at `plugin_validator.py:737` uses `"agents" in path.parts` which matches skill-internal agent files. This is the secondary source of false positives (discovery is the primary one).

With context-aware discovery, files reaching `detect_file_type` should already be correctly scoped. However, as a defense-in-depth measure, `detect_file_type` gains an optional `scan_context` parameter:

```python
@staticmethod
def detect_file_type(
    path: Path,
    scan_context: ScanContext | None = None,
    plugin_root: Path | None = None,
) -> FileType:
    """Detect file type from path structure, optionally scoped by context.

    When scan_context is PLUGIN and plugin_root is provided:
    - Only classify as AGENT if path is under {plugin_root}/agents/
    - Only classify as COMMAND if path is under {plugin_root}/commands/
    - Files under skills/*/agents/ are classified as UNKNOWN (skill-internal)

    When scan_context is None: current behavior (backward compatible).
    """
```

**Backward compatibility**: The new parameters are optional with `None` defaults. All existing call sites continue to work unchanged. Call sites inside the context-aware discovery path pass the context.

## How PA001 and Other Validators Consume Context

PA001 (`check_pa001`) and similar plugin-aware validators already operate on paths passed to them. They don't discover files themselves. The fix is upstream: context-aware discovery ensures PA001 never receives `skills/skill-creator/agents/researcher.md` as a plugin agent path.

No changes needed in PA001 or other validators. They benefit automatically from correctly-scoped input.

## Migration Path

### Phase 1: Add context detection (non-breaking)

1. Add `ScanContext` enum and `detect_scan_context()` to `scan_runtime.py`
2. Add `PluginManifest` dataclass and `_parse_plugin_manifest()`
3. Add `_discover_plugin_paths()` and `_discover_provider_paths()`
4. Add `KNOWN_PROVIDER_DIRS` and `PLUGIN_FILTER_TYPE_MAP`

All new code, no existing behavior changes.

### Phase 2: Wire into discovery (behavioral change)

1. Replace body of `_discover_validatable_paths()` with context-dispatching logic
2. Update the `resolved_glob is None` branch in `_resolve_filter_and_expand_paths()` (already calls `_discover_validatable_paths`, so this is automatic)
3. Update `--filter-type` handling to use `PLUGIN_FILTER_TYPE_MAP` in plugin context

### Phase 3: Defense-in-depth (optional hardening)

1. Add `scan_context` parameter to `FileType.detect_file_type()`
2. Pass context from validation loop call sites
3. This prevents misclassification even if a path somehow bypasses discovery scoping

### Phase 4: Tests

1. Unit tests for `detect_scan_context()` with each context type
2. Unit tests for `_discover_plugin_paths()` — manifest-driven and convention-driven
3. Unit tests for `_discover_provider_paths()`
4. Integration test: scanning a plugin directory does NOT flag skill-internal agents (the original false positive scenario from `claude-plugins-official`)
5. Integration test: `--filter-type agents` in plugin context uses root-only pattern
6. Regression test: bare directory scanning behavior unchanged

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Module location | `scan_runtime.py` | Resolved Q6 — context is part of scan logic, not a separate concern |
| Adapter relationship | Adapters remain validation-only | Resolved Q7 — scan context is independent of adapter validation |
| Overlapping contexts | Plugin takes precedence | Resolved Q2 — `.claude/` inside a plugin is plugin content |
| Skill-internal files | Not validated as agents/commands | Resolved Q3 — outside skilllint's agent/command scope |
| Nested skills | All subdirs are skill-internal | Resolved Q4 — no recursion for plugin-level discovery |
| Explicit filter | Overrides context | Resolved Q5 — user knows what they want |
| `detect_file_type` change | Optional parameter, backward compatible | Defense-in-depth without breaking existing call sites |

## Constants Summary

```python
# New in scan_runtime.py

KNOWN_PROVIDER_DIRS: frozenset[str] = frozenset({
    ".claude", ".cursor", ".gemini", ".codex",
})

PLUGIN_FILTER_TYPE_MAP: dict[str, str] = {
    "skills": "skills/*/SKILL.md",
    "agents": "agents/*.md",
    "commands": "commands/*.md",
}

# Existing (unchanged)
FILTER_TYPE_MAP: dict[str, str] = {
    "skills": "**/skills/*/SKILL.md",
    "agents": "**/agents/*.md",
    "commands": "**/commands/*.md",
}

DEFAULT_SCAN_PATTERNS: tuple[str, ...] = (
    "**/skills/*/SKILL.md",
    "**/agents/*.md",
    "**/commands/*.md",
    "**/.claude-plugin/plugin.json",
    "**/hooks/hooks.json",
    "**/CLAUDE.md",
)
```

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `packages/skilllint/scan_runtime.py` | Modified | Add `ScanContext`, `PluginManifest`, detection/discovery functions, update `_discover_validatable_paths` and `_resolve_filter_and_expand_paths` |
| `packages/skilllint/plugin_validator.py` | Modified | Add optional `scan_context` parameter to `FileType.detect_file_type()` (Phase 3) |
| `packages/skilllint/tests/test_scan_context.py` | New | Tests for context detection and context-aware discovery |
