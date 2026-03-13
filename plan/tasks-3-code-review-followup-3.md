---
tasks:
  - task: "Remove dead code: unused rglob result in ProgressiveDisclosureValidator"
    status: pending
    parent_task: "code-review-2026-03-13"
---

# Task: Remove dead code in ProgressiveDisclosureValidator.validate()

## Parent Task
- Original: `code-review-2026-03-13`
- Review Date: 2026-03-13

## Status
- [ ] Pending

## Priority
Medium

## Description
In `plugin_validator.py`, the `ProgressiveDisclosureValidator.validate()` method at line 938 computes a file count but discards the result:

```python
sum(1 for _ in dir_path.rglob("*") if _.is_file())
```

This expression iterates all files recursively in the directory but does not assign the result to any variable or use it. This is wasted I/O with no functional purpose. The comment on line 939 says "No info message needed when directory exists" -- confirming the count was likely a leftover from an earlier design that reported file counts.

The dead expression should be removed entirely, or if the intent was to report file counts in verbose mode, it should be properly integrated.

## Acceptance Criteria
- [ ] Dead `sum(1 for ...)` expression removed from line 938
- [ ] Tests still pass
- [ ] No functional behavior change (expression had no side effects)

## Files to Modify
- `packages/skilllint/plugin_validator.py:938` - Remove dead `sum()` expression

## Verification Steps
1. `uv run ruff check packages/skilllint/plugin_validator.py`
2. `uv run pytest packages/skilllint/tests/test_progressive_disclosure_validator.py -x`

## References
- Related code: `packages/skilllint/plugin_validator.py:885-943`
