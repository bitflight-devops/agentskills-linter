---
tasks:
  - task: "Phase 1a: Add ScanContext enum, KNOWN_PROVIDER_DIRS, PLUGIN_FILTER_TYPE_MAP constants"
    status: pending
    dependencies: []
    priority: high
    complexity: low
    agent: "python3-development:python-cli-architect"
  - task: "Phase 1b: Add PluginManifest dataclass and _parse_plugin_manifest()"
    status: pending
    dependencies: ["Phase 1a"]
    priority: high
    complexity: medium
    agent: "python3-development:python-cli-architect"
  - task: "Phase 1c: Add _discover_plugin_paths() for manifest-driven and convention-driven discovery"
    status: pending
    dependencies: ["Phase 1b"]
    priority: high
    complexity: medium
    agent: "python3-development:python-cli-architect"
  - task: "Phase 1d: Add _discover_provider_paths() and detect_scan_context()"
    status: pending
    dependencies: ["Phase 1a"]
    priority: high
    complexity: low
    agent: "python3-development:python-cli-architect"
  - task: "Phase 2a: Replace _discover_validatable_paths() body with context dispatcher"
    status: pending
    dependencies: ["Phase 1c", "Phase 1d"]
    priority: high
    complexity: high
    agent: "python3-development:python-cli-architect"
  - task: "Phase 2b: Make --filter-type context-aware in _resolve_filter_and_expand_paths()"
    status: pending
    dependencies: ["Phase 1a"]
    priority: high
    complexity: low
    agent: "python3-development:python-cli-architect"
  - task: "Phase 3: Add scan_context parameter to FileType.detect_file_type() (defense-in-depth)"
    status: pending
    dependencies: ["Phase 2a"]
    priority: medium
    complexity: medium
    agent: "python3-development:python-cli-architect"
  - task: "Phase 4a: Unit tests for detect_scan_context() and context constants"
    status: pending
    dependencies: ["Phase 1a", "Phase 1d"]
    priority: high
    complexity: low
    agent: "python3-development:python-pytest-architect"
  - task: "Phase 4b: Unit tests for PluginManifest and _parse_plugin_manifest()"
    status: pending
    dependencies: ["Phase 1b"]
    priority: high
    complexity: medium
    agent: "python3-development:python-pytest-architect"
  - task: "Phase 4c: Unit tests for _discover_plugin_paths() (manifest-driven and convention-driven)"
    status: pending
    dependencies: ["Phase 1c"]
    priority: high
    complexity: medium
    agent: "python3-development:python-pytest-architect"
  - task: "Phase 4d: Unit tests for _discover_provider_paths()"
    status: pending
    dependencies: ["Phase 1d"]
    priority: high
    complexity: low
    agent: "python3-development:python-pytest-architect"
  - task: "Phase 4e: Integration tests for context-aware discovery pipeline"
    status: pending
    dependencies: ["Phase 2a", "Phase 2b"]
    priority: high
    complexity: high
    agent: "python3-development:python-pytest-architect"
  - task: "Phase 4f: Regression test for bare directory backward compatibility"
    status: pending
    dependencies: ["Phase 2a"]
    priority: high
    complexity: medium
    agent: "python3-development:python-pytest-architect"
---

# Task Plan: Context-Aware Scan Discovery

**Feature**: Scan context detection — prevent false positives from skill-internal files matching agent/command glob patterns.

**Architecture source**: `plan/architect-scan-context-detection.md`
**Feature spec**: `plan/feature-context-scan-context-detection.md`
**Codebase analysis**: `plan/codebase/scan-discovery-patterns.md`

---

## Context Manifest

### Requirements Addressed

**Active requirements from `.gsd/REQUIREMENTS.md` mapped to this task plan:**

| Requirement | Class | Mapping |
|---|---|---|
| R015 | integration | Phase 1b, 1c (manifest parsing and plugin path discovery) |
| R016 | integration | Phase 1c (convention-driven discovery) |
| R017 | integration | Phase 1d (provider-scoped discovery) |
| R025 | continuity | Phase 2a, 2b (behavioral change while preserving CLI semantics) |

### Architecture Documents Referenced

- **`plan/architect-scan-context-detection.md`**: Complete design spec with detection tree, dispatch logic, and edge-case handling.
- **`plan/feature-context-scan-context-detection.md`**: User-facing feature requirements and acceptance criteria.
- **`plan/codebase/scan-discovery-patterns.md`**: Current codebase analysis identifying false-positive patterns and current discovery implementation.

### Primary Owner & Slice

- **Milestone**: M002 (Architecture & Detection Decomposition)
- **Slice**: M002/S01 (Validator seam map and boundary extraction)
- **Primary responsibility**: Extract scan expansion and validation-loop orchestration seams; add context-detection logic to seed S02/S03.

### Scope Boundaries

**In scope:**
- Detect scan context (PLUGIN, PROVIDER, BARE) from directory structure
- Parse plugin manifests and extract component declarations
- Implement manifest-driven and convention-driven plugin discovery
- Implement provider-scoped discovery (agents only)
- Wire context dispatcher into `_discover_validatable_paths()` and `_resolve_filter_and_expand_paths()`
- Add defense-in-depth context awareness to `FileType.detect_file_type()`
- Comprehensive unit, integration, and regression tests

**Out of scope (per R029, R030, R031):**
- Autofix behavior changes — detection only
- New lint-rule families — detection only
- Silence all warnings — truthful detection is sufficient

### Risk Mitigation

**Risk**: Behavioral change in Phase 2 could break existing scans if discovery logic is faulty.
**Mitigation**:
- Phase 1 adds only new types/functions (non-breaking); Phase 2 adds dispatcher.
- Regression test (Task 4f) ensures bare directory behavior matches `DEFAULT_SCAN_PATTERNS`.
- Integration tests (Task 4e) verify nested plugins and providers dispatch correctly.

**Risk**: False positives still surface from defensive FileType checks.
**Mitigation**: Phase 3 adds `scan_context` parameter to `detect_file_type()` for in-depth filtering; optional parameter ensures backward compatibility.

### Test Strategy

- **Unit tests** (Tasks 4a–4d): Isolated context detection, manifest parsing, and discovery functions.
- **Integration tests** (Task 4e): Full pipeline through `_discover_validatable_paths()` and `_resolve_filter_and_expand_paths()`.
- **Regression tests** (Task 4f): Bare directory discovery matches pre-change behavior.

### Verification Artifacts

- **Code locations**: `packages/skilllint/scan_runtime.py` (new logic), `packages/skilllint/plugin_validator.py` (dispatcher integration)
- **Test file**: `packages/skilllint/tests/test_scan_context.py` (new; all tests from Tasks 4a–4f)
- **Exit criteria**: All tasks complete, `uv run pytest packages/skilllint/tests/ -x --timeout=60` passes, `uv run ruff check packages/skilllint/{scan_runtime,plugin_validator}.py` passes

---

## Phase 1: New Types and Functions (Non-Breaking)

All new code added to `packages/skilllint/scan_runtime.py`. No existing behavior changes.

### Task 1a: Add ScanContext enum and new constants

**Status**: Pending
**Dependencies**: None
**Priority**: High
**Complexity**: Low
**Agent**: `python3-development:python-cli-architect`

**Description**:
Add the `ScanContext` StrEnum with three values: `PLUGIN`, `PROVIDER`, `BARE`. Add the `KNOWN_PROVIDER_DIRS` frozenset (`{".claude", ".cursor", ".gemini", ".codex"}`). Add `PLUGIN_FILTER_TYPE_MAP` dict with root-only glob patterns for plugin context (`"agents": "agents/*.md"`, etc.).

All additions are at module level in `scan_runtime.py`, after the existing `DEFAULT_SCAN_PATTERNS` constant.

**Acceptance Criteria**:
- `ScanContext` is a `StrEnum` with exactly three members: `PLUGIN`, `PROVIDER`, `BARE`
- `KNOWN_PROVIDER_DIRS` is a `frozenset[str]` containing `{".claude", ".cursor", ".gemini", ".codex"}`
- `PLUGIN_FILTER_TYPE_MAP` maps `"skills"` -> `"skills/*/SKILL.md"`, `"agents"` -> `"agents/*.md"`, `"commands"` -> `"commands/*.md"`
- `ruff check` passes on `scan_runtime.py`

**Verification Steps**:
1. `uv run ruff check packages/skilllint/scan_runtime.py`
2. `uv run python -c "from skilllint.scan_runtime import ScanContext, KNOWN_PROVIDER_DIRS, PLUGIN_FILTER_TYPE_MAP; print(list(ScanContext)); print(KNOWN_PROVIDER_DIRS); print(PLUGIN_FILTER_TYPE_MAP)"`
3. `uv run pytest packages/skilllint/tests/ -x --timeout=30` (existing tests still pass)

---

### Task 1b: Add PluginManifest dataclass and _parse_plugin_manifest()

**Status**: Pending
**Dependencies**: Phase 1a
**Priority**: High
**Complexity**: Medium
**Agent**: `python3-development:python-cli-architect`

**Description**:
Add `PluginManifest` as a frozen dataclass in `scan_runtime.py`. Fields: `plugin_root: Path`, `agents: list[str] | None = None`, `commands: list[str] | None = None`, `skills: list[str] | None = None`. Include `is_manifest_driven` property that returns `True` if any path list is not None.

Add `_parse_plugin_manifest(plugin_root: Path) -> PluginManifest` that reads `.claude-plugin/plugin.json`, extracts `agents`, `commands`, `skills` arrays if present, and returns a `PluginManifest`. If the keys are absent or the file cannot be parsed, return a manifest with all `None` fields (convention-driven mode).

**Acceptance Criteria**:
- `PluginManifest` is a `frozen=True` dataclass with the four fields described
- `is_manifest_driven` returns `True` only when at least one path list is not `None`
- `_parse_plugin_manifest()` reads `plugin_root / ".claude-plugin" / "plugin.json"` and extracts path arrays
- Missing keys in plugin.json result in `None` fields (not empty lists)
- Invalid JSON or missing file returns all-`None` manifest (graceful, no crash)

**Verification Steps**:
1. `uv run ruff check packages/skilllint/scan_runtime.py`
2. `uv run python -c "from skilllint.scan_runtime import PluginManifest; m = PluginManifest(plugin_root=__import__('pathlib').Path('.')); print(m.is_manifest_driven)"`
3. `uv run pytest packages/skilllint/tests/ -x --timeout=30`

---

### Task 1c: Add _discover_plugin_paths()

**Status**: Pending
**Dependencies**: Phase 1b
**Priority**: High
**Complexity**: Medium
**Agent**: `python3-development:python-cli-architect`

**Description**:
Add `_discover_plugin_paths(manifest: PluginManifest) -> list[Path]` to `scan_runtime.py`.

Two modes based on `manifest.is_manifest_driven`:

**Manifest-driven**: Resolve exactly the paths declared in the manifest's `agents`, `commands`, and `skills` lists relative to `manifest.plugin_root`. No globbing. Also include `plugin_root` itself (for plugin.json validation), `hooks/hooks.json` and `CLAUDE.md` if they exist.

**Convention-driven**: Glob at the plugin root only (no `**` recursion):
- `{plugin_root}/agents/*.md`
- `{plugin_root}/commands/*.md`
- `{plugin_root}/skills/*/SKILL.md`
- `{plugin_root}` itself (for plugin.json validation)
- `{plugin_root}/hooks/hooks.json` if exists
- `{plugin_root}/CLAUDE.md` if exists

Never recurse into `skills/*/agents/` or `skills/*/commands/`.

Return sorted, deduplicated list.

**Acceptance Criteria**:
- Convention-driven mode uses root-only globs, never `**` patterns
- Manifest-driven mode resolves declared paths without globbing
- Both modes include the plugin root directory itself in the output
- Files under `skills/*/agents/` are never returned
- Return type is `list[Path]`, sorted and deduplicated

**Verification Steps**:
1. `uv run ruff check packages/skilllint/scan_runtime.py`
2. `uv run pytest packages/skilllint/tests/ -x --timeout=30`
3. Manual inspection: confirm no `**` glob patterns in the function body (except in BARE fallback, which is in a different function)

---

### Task 1d: Add _discover_provider_paths() and detect_scan_context()

**Status**: Pending
**Dependencies**: Phase 1a
**Priority**: High
**Complexity**: Low
**Agent**: `python3-development:python-cli-architect`

**Description**:
Add `_discover_provider_paths(directory: Path) -> list[Path]` that discovers validatable files in a provider directory using `{directory}/agents/**/*.md` pattern. Return sorted list.

Add `detect_scan_context(directory: Path) -> ScanContext` with detection order:
1. If `directory / ".claude-plugin" / "plugin.json"` exists -> `ScanContext.PLUGIN`
2. If `directory.name` is in `KNOWN_PROVIDER_DIRS` -> `ScanContext.PROVIDER`
3. Otherwise -> `ScanContext.BARE`

**Acceptance Criteria**:
- `detect_scan_context()` returns `PLUGIN` when `.claude-plugin/plugin.json` exists in the directory
- `detect_scan_context()` returns `PROVIDER` when directory name matches a known provider dir
- `detect_scan_context()` returns `BARE` for all other directories
- Plugin check takes precedence over provider check (a `.claude` dir with a `plugin.json` is PLUGIN)
- `_discover_provider_paths()` only discovers markdown files under `agents/` subdirectory

**Verification Steps**:
1. `uv run ruff check packages/skilllint/scan_runtime.py`
2. `uv run python -c "from skilllint.scan_runtime import detect_scan_context, ScanContext; print(detect_scan_context.__doc__)"`
3. `uv run pytest packages/skilllint/tests/ -x --timeout=30`

---

## Phase 2: Wire into Discovery Pipeline (Behavioral Change)

### Task 2a: Replace _discover_validatable_paths() body with context dispatcher

**Status**: Pending
**Dependencies**: Phase 1c, Phase 1d
**Priority**: High
**Complexity**: High
**Agent**: `python3-development:python-cli-architect`

**Description**:
Replace the body of `_discover_validatable_paths(directory: Path) -> list[Path]` (currently at `scan_runtime.py:45-67`) with context-dispatching logic per the architecture spec:

1. Call `detect_scan_context(directory)`.
2. If `PLUGIN`: parse manifest, call `_discover_plugin_paths(manifest)`.
3. If `PROVIDER`: call `_discover_provider_paths(directory)`.
4. If `BARE`: find nested plugin roots and provider dirs, dispatch to their respective discovery functions, then use `DEFAULT_SCAN_PATTERNS` for remaining files not covered by any plugin/provider subtree.

For BARE context with nested plugins: collect all plugin roots found via `**/.claude-plugin/plugin.json` glob. For each, dispatch to `_discover_plugin_paths`. For nested providers: iterate `KNOWN_PROVIDER_DIRS`, find matches, skip any inside a plugin tree (plugin takes precedence per Q2 resolution). Apply `DEFAULT_SCAN_PATTERNS` only to files not already within a discovered plugin or provider subtree.

Also update the plugin-detection branch in `_resolve_filter_and_expand_paths()` (currently lines 103-110) to use the new dispatcher. The existing logic that checks `(path / ".claude-plugin/plugin.json").exists()` and manually adds skill paths should be replaced by a call to `_discover_validatable_paths(path)`, which now handles plugin context internally.

**Acceptance Criteria**:
- `_discover_validatable_paths` dispatches based on `detect_scan_context()` result
- Plugin context never recurses into `skills/*/agents/` or `skills/*/commands/`
- Provider context only discovers `agents/**/*.md`
- BARE context handles nested plugins and providers, with plugin taking precedence
- The existing plugin-detection branch in `_resolve_filter_and_expand_paths` is simplified to use the dispatcher
- All existing tests pass (behavioral change is limited to excluding false positives)

**Verification Steps**:
1. `uv run ruff check packages/skilllint/scan_runtime.py`
2. `uv run pytest packages/skilllint/tests/ -x --timeout=60`
3. `uv run skilllint check --help` (CLI still works)

---

### Task 2b: Make --filter-type context-aware in _resolve_filter_and_expand_paths()

**Status**: Pending
**Dependencies**: Phase 1a
**Priority**: High
**Complexity**: Low
**Agent**: `python3-development:python-cli-architect`

**Description**:
Update the `--filter-type` resolution in `_resolve_filter_and_expand_paths()` so that when the scan target is a plugin directory, `PLUGIN_FILTER_TYPE_MAP` is used instead of `FILTER_TYPE_MAP`. This ensures `--filter-type agents` resolves to `agents/*.md` (root-only) in plugin context instead of `**/agents/*.md` (recursive).

Logic change at the point where `filter_type` is resolved to `resolved_glob`:
- If `filter_type` is set and the path is a directory, call `detect_scan_context(path)`.
- If context is `PLUGIN`, use `PLUGIN_FILTER_TYPE_MAP.get(filter_type, FILTER_TYPE_MAP[filter_type])`.
- Otherwise, use `FILTER_TYPE_MAP[filter_type]` (current behavior).

Explicit `--filter` (raw glob) continues to override context entirely — no change needed there.

**Acceptance Criteria**:
- `--filter-type agents` on a plugin dir uses `agents/*.md` (not `**/agents/*.md`)
- `--filter-type skills` on a plugin dir uses `skills/*/SKILL.md` (not `**/skills/*/SKILL.md`)
- `--filter-type` on a non-plugin dir uses the existing recursive patterns (no regression)
- `--filter` (raw glob) is unaffected by scan context

**Verification Steps**:
1. `uv run ruff check packages/skilllint/scan_runtime.py`
2. `uv run pytest packages/skilllint/tests/ -x --timeout=30`
3. `uv run pytest packages/skilllint/tests/ -k "filter" -x --timeout=30` (filter-related tests pass)

---

## Phase 3: Defense-in-Depth Hardening

### Task 3: Add scan_context parameter to FileType.detect_file_type()

**Status**: Pending
**Dependencies**: Phase 2a
**Priority**: Medium
**Complexity**: Medium
**Agent**: `python3-development:python-cli-architect`

**Description**:
Add optional `scan_context: ScanContext | None = None` and `plugin_root: Path | None = None` parameters to `FileType.detect_file_type()` in `plugin_validator.py`.

When `scan_context` is `PLUGIN` and `plugin_root` is provided:
- Only classify as `AGENT` if path is directly under `{plugin_root}/agents/`
- Only classify as `COMMAND` if path is directly under `{plugin_root}/commands/`
- Files under `skills/*/agents/` or `skills/*/commands/` within the plugin are classified as `UNKNOWN` (or equivalent non-agent type)

When `scan_context` is `None`: current behavior unchanged (all existing call sites unaffected).

Update call sites within the context-aware discovery pipeline (inside `_discover_validatable_paths` and `run_validation_loop`) to pass the context when available.

**Acceptance Criteria**:
- New parameters have `None` defaults — all existing call sites work without changes
- In PLUGIN context with plugin_root, files under `skills/*/agents/` are NOT classified as AGENT
- In PLUGIN context with plugin_root, files under `{plugin_root}/agents/` ARE classified as AGENT
- `ruff check` passes on both `scan_runtime.py` and `plugin_validator.py`

**Verification Steps**:
1. `uv run ruff check packages/skilllint/scan_runtime.py packages/skilllint/plugin_validator.py`
2. `uv run pytest packages/skilllint/tests/ -x --timeout=60`
3. Verify backward compatibility: `uv run python -c "from skilllint.plugin_validator import FileType; print(FileType.detect_file_type.__doc__)"`

---

## Phase 4: Tests

All tests go in `packages/skilllint/tests/test_scan_context.py` (new file) per the architecture spec and project test directory conventions.

### Task 4a: Unit tests for detect_scan_context() and context constants

**Status**: Pending
**Dependencies**: Phase 1a, Phase 1d
**Priority**: High
**Complexity**: Low
**Agent**: `python3-development:python-pytest-architect`

**Description**:
Test `detect_scan_context()` with each context type using `tmp_path` fixtures:
- Directory with `.claude-plugin/plugin.json` -> `PLUGIN`
- Directory named `.claude` -> `PROVIDER`
- Directory named `.cursor` -> `PROVIDER`
- Directory named `.gemini` -> `PROVIDER`
- Directory named `.codex` -> `PROVIDER`
- Regular directory -> `BARE`
- Edge case: `.claude` directory that also contains `.claude-plugin/plugin.json` -> `PLUGIN` (plugin takes precedence)

Also verify `KNOWN_PROVIDER_DIRS` and `PLUGIN_FILTER_TYPE_MAP` contain the expected values.

**Acceptance Criteria**:
- Each `ScanContext` variant has at least one test
- Plugin-over-provider precedence is tested
- Constants are validated for expected contents
- All tests use `tmp_path` — no hardcoded paths

**Verification Steps**:
1. `uv run pytest packages/skilllint/tests/test_scan_context.py -v -x --timeout=30`
2. `uv run ruff check packages/skilllint/tests/test_scan_context.py`
3. `uv run pytest packages/skilllint/tests/ -x --timeout=60` (full suite still passes)

---

### Task 4b: Unit tests for PluginManifest and _parse_plugin_manifest()

**Status**: Pending
**Dependencies**: Phase 1b
**Priority**: High
**Complexity**: Medium
**Agent**: `python3-development:python-pytest-architect`

**Description**:
Test `PluginManifest` dataclass and `_parse_plugin_manifest()`:
- `PluginManifest` with all `None` fields: `is_manifest_driven` is `False`
- `PluginManifest` with one field set: `is_manifest_driven` is `True`
- `_parse_plugin_manifest` with full plugin.json (agents, commands, skills arrays) -> fields populated
- `_parse_plugin_manifest` with empty plugin.json (no path arrays) -> all `None` fields
- `_parse_plugin_manifest` with partial plugin.json (only agents) -> only agents populated
- `_parse_plugin_manifest` with invalid JSON -> all `None` fields (graceful)
- `_parse_plugin_manifest` with missing plugin.json -> all `None` fields (graceful)

**Acceptance Criteria**:
- `is_manifest_driven` property tested for both True and False cases
- All edge cases for plugin.json content covered (full, empty, partial, invalid, missing)
- Tests use `tmp_path` fixtures with actual file I/O
- No mocking of file reads — use real temporary files

**Verification Steps**:
1. `uv run pytest packages/skilllint/tests/test_scan_context.py -v -x -k "manifest" --timeout=30`
2. `uv run ruff check packages/skilllint/tests/test_scan_context.py`
3. `uv run pytest packages/skilllint/tests/ -x --timeout=60`

---

### Task 4c: Unit tests for _discover_plugin_paths() (both modes)

**Status**: Pending
**Dependencies**: Phase 1c
**Priority**: High
**Complexity**: Medium
**Agent**: `python3-development:python-pytest-architect`

**Description**:
Test `_discover_plugin_paths()` with `tmp_path` plugin directory structures:

**Convention-driven tests**:
- Plugin with `agents/a.md`, `agents/b.md` -> both discovered
- Plugin with `commands/run.md` -> discovered
- Plugin with `skills/my-skill/SKILL.md` -> discovered
- Plugin with `skills/my-skill/agents/helper.md` -> NOT discovered (the core false positive scenario)
- Plugin with `skills/my-skill/commands/internal.md` -> NOT discovered
- Plugin with `hooks/hooks.json` -> discovered
- Plugin with `CLAUDE.md` -> discovered
- Plugin root itself in output (for plugin.json validation)

**Manifest-driven tests**:
- Manifest declares `agents: ["agents/main.md"]` and `agents/main.md` + `agents/extra.md` exist -> only `main.md` discovered
- Manifest declares `skills: ["skills/review"]` -> skill path resolved

**Acceptance Criteria**:
- `skills/*/agents/*.md` paths are NEVER in the output (convention-driven mode)
- Manifest-driven mode returns exactly the declared paths (no extras)
- Convention-driven mode uses root-only globs
- All file types (agents, commands, skills, hooks, CLAUDE.md, plugin root) tested

**Verification Steps**:
1. `uv run pytest packages/skilllint/tests/test_scan_context.py -v -x -k "discover_plugin" --timeout=30`
2. `uv run ruff check packages/skilllint/tests/test_scan_context.py`
3. `uv run pytest packages/skilllint/tests/ -x --timeout=60`

---

### Task 4d: Unit tests for _discover_provider_paths()

**Status**: Pending
**Dependencies**: Phase 1d
**Priority**: High
**Complexity**: Low
**Agent**: `python3-development:python-pytest-architect`

**Description**:
Test `_discover_provider_paths()` with `tmp_path` provider directory structures:
- Provider dir with `agents/my-agent.md` -> discovered
- Provider dir with `agents/subdir/nested-agent.md` -> discovered (agents supports `**/*.md`)
- Provider dir with `commands/something.md` -> NOT discovered (providers only discover agents)
- Provider dir with no agents dir -> empty list
- Provider dir with non-md files in agents/ -> NOT discovered

**Acceptance Criteria**:
- Only `agents/**/*.md` files are discovered
- Non-agent files in provider directories are excluded
- Empty provider directory returns empty list
- Output is sorted

**Verification Steps**:
1. `uv run pytest packages/skilllint/tests/test_scan_context.py -v -x -k "discover_provider" --timeout=30`
2. `uv run ruff check packages/skilllint/tests/test_scan_context.py`
3. `uv run pytest packages/skilllint/tests/ -x --timeout=60`

---

### Task 4e: Integration tests for context-aware discovery pipeline

**Status**: Pending
**Dependencies**: Phase 2a, Phase 2b
**Priority**: High
**Complexity**: High
**Agent**: `python3-development:python-pytest-architect`

**Description**:
End-to-end integration tests that exercise the full discovery pipeline through `_discover_validatable_paths` and `_resolve_filter_and_expand_paths`:

1. **Plugin directory scan**: Create a tmp_path plugin with agents at root and agents inside skills. Verify `_discover_validatable_paths` returns root agents but NOT skill-internal agents.

2. **Plugin with --filter-type agents**: Verify `_resolve_filter_and_expand_paths` with `filter_type="agents"` on a plugin dir uses root-only pattern.

3. **Plugin with --filter (raw glob)**: Verify `--filter "**/agents/*.md"` overrides context and returns ALL agent files including skill-internal ones (explicit filter overrides context).

4. **Provider directory scan**: Verify only agents are discovered.

5. **Bare directory with nested plugin**: Create a tmp_path with a plugin subdirectory. Verify the nested plugin's skill-internal agents are excluded.

6. **Bare directory with nested provider**: Create a tmp_path with a `.claude/` subdirectory. Verify provider-scoped discovery applies.

**Acceptance Criteria**:
- Plugin scan excludes `skills/*/agents/*.md` from discovery
- `--filter-type` is context-aware in plugin mode
- `--filter` overrides context (explicit filter wins)
- BARE context correctly dispatches to plugin/provider discovery for nested subtrees
- All tests use real filesystem structures via `tmp_path`

**Verification Steps**:
1. `uv run pytest packages/skilllint/tests/test_scan_context.py -v -x -k "integration" --timeout=60`
2. `uv run ruff check packages/skilllint/tests/test_scan_context.py`
3. `uv run pytest packages/skilllint/tests/ -x --timeout=60`

---

### Task 4f: Regression test for bare directory backward compatibility

**Status**: Pending
**Dependencies**: Phase 2a
**Priority**: High
**Complexity**: Medium
**Agent**: `python3-development:python-pytest-architect`

**Description**:
Verify that bare directory scanning (no plugin.json, no provider directory) produces the same results as before the change. Create a tmp_path structure with:
- `skills/my-skill/SKILL.md`
- `agents/helper.md`
- `commands/run.md`
- `hooks/hooks.json`
- `CLAUDE.md`
- Nested: `subdir/agents/nested-agent.md`
- Nested: `subdir/skills/other-skill/SKILL.md`

Verify `_discover_validatable_paths()` returns all of these (bare context uses `DEFAULT_SCAN_PATTERNS` with `**` recursion for files outside plugin/provider subtrees).

**Acceptance Criteria**:
- Bare directory discovery matches `DEFAULT_SCAN_PATTERNS` behavior
- Nested files at arbitrary depth are discovered (bare context preserves `**` recursion)
- No regressions in the discovery set for non-plugin, non-provider directories
- Test explicitly asserts the full set of discovered paths

**Verification Steps**:
1. `uv run pytest packages/skilllint/tests/test_scan_context.py -v -x -k "regression" --timeout=30`
2. `uv run ruff check packages/skilllint/tests/test_scan_context.py`
3. `uv run pytest packages/skilllint/tests/ -x --timeout=60`

---

## Discovered During Implementation

_Session Date: 2026-03-17_

During implementation, several deviations from the planned state were found. These are recorded here for future developers working on this feature or related scan-discovery work.

**Key Discoveries:**

1. **Phase 3 was pre-implemented**: The `scan_context` and `plugin_root` parameters on `FileType.detect_file_type()` were already present in `plugin_validator.py` when Phase 3 ran. The guard `scan_context is not None and plugin_root is not None` was already in place. Phase 3 had no net code change to make.

2. **Phase 4c partial implementation on first attempt**: The Phase 4c agent hit a rate limit mid-task. Before the limit, it had already written the `TestDiscoverPluginPaths` class to `test_scan_context.py`. The restarted agent found the class present and continued from where it left off. Both runs completed successfully — no duplicate or conflicting code was introduced.

3. **`pytest-timeout` plugin not installed**: The `--timeout=60` / `--timeout=30` flags in verification steps exit with code 4 (unknown option) in this environment. All verification commands that use `--timeout` must be run without that flag. Tests pass normally without it. The flag should be removed from the Verification Steps above or the plugin should be added to the dev dependencies.

4. **`plugin_scoped` guard activates for ANY non-None scan_context, not just PLUGIN**: In `plugin_validator.py`, the branch that restricts AGENT/COMMAND classification is guarded by `scan_context is not None and plugin_root is not None`. If a caller passes `ScanContext.BARE` or `ScanContext.PROVIDER` with a non-None `plugin_root`, the restriction activates incorrectly. No current call site triggers this, but the guard is latent. Future callers should only pass `scan_context=ScanContext.PLUGIN` when they also pass `plugin_root`.

5. **Q2 precedence rule (BARE + provider-inside-plugin-tree skip) has no test coverage**: The BARE-context dispatch in `scan_runtime.py` (approximately lines 250 and 253) contains logic to skip provider directories found inside a plugin subtree (plugin takes precedence per the Q2 resolution in the architecture spec). This path has no dedicated test. Tasks 4e and 4f do not exercise it. Follow-up task 3 (`plan/tasks-9-scan-context-detection-followup-3.md`) tracks adding coverage.

6. **`_discover_plugin_paths()` manifest-driven mode adds paths without existence checks**: In manifest-driven mode, declared agent, command, and skill paths are resolved relative to `plugin_root` and added to the output unconditionally — no `Path.exists()` check is performed. This appears intentional: validators downstream are expected to flag declared-but-missing files. Convention-driven mode uses glob matching, so non-existent files are naturally excluded.

7. **SAM CLI unavailable in this environment**: `uv run sam` exits with "No such file or directory". Task status tracking was managed manually throughout this session. The `uv run sam read` / `uv run sam update` commands specified in the context-refinement agent SOP do not function here.

8. **Follow-up task files created**: Three follow-up task files were created to address gaps and latent bugs found during implementation:
   - `plan/tasks-7-scan-context-detection-followup-1.md`
   - `plan/tasks-8-scan-context-detection-followup-2.md`
   - `plan/tasks-9-scan-context-detection-followup-3.md`

#### Updated Technical Details

- `FileType.detect_file_type()` in `packages/skilllint/plugin_validator.py` already accepts `scan_context: ScanContext | None = None` and `plugin_root: Path | None = None` — do not re-add these parameters.
- The `plugin_scoped` branch guard should be tightened in a follow-up to `scan_context == ScanContext.PLUGIN` rather than the current truthiness check.
- Verification commands in all Phase tasks should drop `--timeout=N` until `pytest-timeout` is added as a dev dependency.

#### Gotchas for Future Developers

- Do not assume Phase 3 is unimplemented — check `plugin_validator.py` before writing `detect_file_type()` changes.
- The `--timeout` pytest flag requires the `pytest-timeout` package; it is not a built-in pytest option.
- The `plugin_scoped` guard in `plugin_validator.py` is broader than the architecture spec intends. Be careful passing non-PLUGIN contexts with a non-None `plugin_root`.
- The Q2 skip logic in the BARE dispatcher is the highest-risk untested path in this feature. Treat it with extra scrutiny when adding integration tests.
