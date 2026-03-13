---
tasks:
  - task: "Replace Path.open()+read() with Path.read_text() in auto_sync_manifests.py"
    status: pending
    parent_task: "code-review-2026-03-13"
---

# Task: Use Path.read_text() instead of open()+read() pattern

## Parent Task
- Original: `code-review-2026-03-13`
- Review Date: 2026-03-13

## Status
- [ ] Pending

## Priority
Low

## Description
Multiple locations in `auto_sync_manifests.py` use the `with path.open(encoding="utf-8") as f: data = msgspec.json.decode(f.read())` pattern instead of the simpler `path.read_text(encoding="utf-8")`. Ruff FURB101 flags these. The project already uses `path.read_text()` in other modules (e.g., `_schema_loader.py` uses `ref.read_bytes()`). These should be normalized for consistency.

Note: Since `msgspec.json.decode()` accepts both `str` and `bytes`, these could also use `path.read_bytes()` to skip the decode step entirely -- this is even more efficient.

## Acceptance Criteria
- [ ] All `Path.open()` + `f.read()` patterns replaced with `Path.read_text()` or `Path.read_bytes()`
- [ ] `ruff check packages/skilllint/auto_sync_manifests.py --select FURB101` reports no violations
- [ ] All existing tests pass

## Files to Modify
- `packages/skilllint/auto_sync_manifests.py:487-488` - `update_plugin_json()`
- `packages/skilllint/auto_sync_manifests.py:544-545` - `_read_plugin_name()`
- `packages/skilllint/auto_sync_manifests.py:613-614` - `update_marketplace_json()`
- `packages/skilllint/auto_sync_manifests.py:977-978` - `_reconcile_one_plugin()`
- `packages/skilllint/auto_sync_manifests.py:1157-1158` - `_reconcile_marketplace()`
- `packages/skilllint/auto_sync_manifests.py:1304-1305` - `_precommit_sync()`

## Verification Steps
1. `uv run ruff check packages/skilllint/auto_sync_manifests.py --select FURB101`
2. `uv run pytest packages/skilllint/tests/test_auto_sync_manifests.py -x`

## References
- Ruff rule: FURB101 (use read_text/read_bytes)
