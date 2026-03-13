---
tasks:
  - task: "Replace bare print() calls with structured logging or Rich console in auto_sync_manifests.py"
    status: pending
    parent_task: "code-review-2026-03-13"
---

# Task: Replace bare print() calls with structured logging or Rich console in auto_sync_manifests.py

## Parent Task
- Original: `code-review-2026-03-13`
- Review Date: 2026-03-13

## Status
- [ ] Pending

## Priority
Low

## Description
`packages/skilllint/auto_sync_manifests.py` uses bare `print()` calls throughout for user-facing output (e.g., lines 610, 1014, 1089, 1092, 1181, 1224, 1247, 1270) and `sys.stderr.write()` for warnings. The rest of the project uses `rich.console.Console` for formatted output (as seen in `plugin_validator.py`).

This inconsistency means:
- Output from `auto_sync_manifests.py` is unformatted plain text while `plugin_validator.py` uses Rich formatting
- There is no way to suppress output in tests without capturing stdout
- Warning messages written via `sys.stderr.write()` bypass any centralized logging

The `print()` calls should be replaced with either:
1. A `rich.console.Console` instance (matching `plugin_validator.py` patterns), or
2. Python `logging` module for structured output that can be configured by callers

## Acceptance Criteria
- [ ] All bare `print()` calls replaced with console output or logging
- [ ] All `sys.stderr.write()` warning calls replaced with `logging.warning()` or `console.print(..., style="yellow")`
- [ ] Output remains functionally equivalent for end users
- [ ] Tests can control output (no unexpected stdout/stderr in test runs)

## Files to Modify
- `packages/skilllint/auto_sync_manifests.py` - Replace ~15 print/sys.stderr.write calls

## Verification Steps
1. `uv run ruff check packages/skilllint/auto_sync_manifests.py`
2. `uv run pytest packages/skilllint/tests/test_auto_sync_manifests.py -x`
3. Manual test: Run `uv run python -m skilllint.auto_sync_manifests --reconcile --dry-run` and verify output is still readable

## References
- Rich console usage: `packages/skilllint/plugin_validator.py` (Console import at line 49)
- Current print calls: `packages/skilllint/auto_sync_manifests.py`
