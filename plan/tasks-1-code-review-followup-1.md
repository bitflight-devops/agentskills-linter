---
tasks:
  - task: "Remove unused `tempfile` import in auto_sync_manifests.py"
    status: pending
    parent_task: "code-review-2026-03-13"
---

# Task: Remove unused import in auto_sync_manifests.py

## Parent Task
- Original: `code-review-2026-03-13`
- Review Date: 2026-03-13

## Status
- [ ] Pending

## Priority
Low

## Description
The `tempfile` module is imported at line 33 of `auto_sync_manifests.py` but never used anywhere in the file. Ruff reports this as F401. The import should be removed to keep the module clean. Note that ruff has `unfixable = ["F401"]` in pyproject.toml, so this must be fixed manually.

## Acceptance Criteria
- [ ] `import tempfile` removed from `auto_sync_manifests.py`
- [ ] `ruff check packages/skilllint/auto_sync_manifests.py` reports no F401

## Files to Modify
- `packages/skilllint/auto_sync_manifests.py:33` - Remove `import tempfile`

## Verification Steps
1. `uv run ruff check packages/skilllint/auto_sync_manifests.py --select F401`
2. `uv run pytest packages/skilllint/tests/test_auto_sync_manifests.py -x`

## References
- Ruff rule: F401 (imported but unused)
