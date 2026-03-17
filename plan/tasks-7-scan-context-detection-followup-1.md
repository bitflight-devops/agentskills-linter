---
tasks:
  - task: "T1"
    title: "Fix plugin_scoped guard in detect_file_type to check scan_context == PLUGIN"
    status: not-started
    agent: "python3-development:python-cli-architect"
    dependencies: []
    priority: 2
    complexity: low
---

# Task Plan: Fix detect_file_type Contract Violation

**Goal**: Fix the `plugin_scoped` guard condition in `FileType.detect_file_type()` so it activates only when `scan_context == ScanContext.PLUGIN`, matching the documented contract.

**Source**: Code review findings in `.claude/reports/code-review-scan-context-detection.md` (Issue 1 + Issue 2)

---

## Context

The architecture spec states: "When `scan_context` is PLUGIN and plugin_root is provided" the filtering applies. The implementation uses:

```python
plugin_scoped = scan_context is not None and plugin_root is not None
```

This activates the guard for ANY non-None scan_context (BARE, PROVIDER, PLUGIN), not only PLUGIN. A future call site passing `scan_context=ScanContext.BARE` with a `plugin_root` would incorrectly suppress AGENT/COMMAND classification.

**File**: `packages/skilllint/plugin_validator.py`, line 762

---

## Task T1: Fix guard condition and add missing test

**Description**:

1. Change line 762 in `plugin_validator.py` from:
   ```python
   plugin_scoped = scan_context is not None and plugin_root is not None
   ```
   to:
   ```python
   plugin_scoped = scan_context == ScanContext.PLUGIN and plugin_root is not None
   ```
   This requires importing `ScanContext` from `scan_runtime` in `plugin_validator.py` (it is already used at the type-hint level for the parameter, so the import should already exist — verify).

2. Add a test in `packages/skilllint/tests/test_scan_context.py` verifying that `detect_file_type` called with `scan_context=ScanContext.BARE` and a `plugin_root` behaves identically to the no-context baseline (does NOT suppress AGENT classification for skill-internal paths).

**Acceptance Criteria**:
- `plugin_scoped` condition is `scan_context == ScanContext.PLUGIN and plugin_root is not None`
- `detect_file_type(path, scan_context=ScanContext.BARE, plugin_root=some_root)` returns AGENT for a path with `"agents"` in parts (same as no-context baseline)
- `detect_file_type(path, scan_context=ScanContext.PLUGIN, plugin_root=some_root)` still returns UNKNOWN for skill-internal agent paths
- `uv run ruff check packages/skilllint/plugin_validator.py packages/skilllint/tests/test_scan_context.py` passes
- `uv run pytest packages/skilllint/tests/ -x -q` passes

**Verification**:
1. `uv run ruff check packages/skilllint/plugin_validator.py`
2. `uv run pytest packages/skilllint/tests/ -x -q`
