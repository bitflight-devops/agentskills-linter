---
tasks:
  - task: "Extract validator classes from plugin_validator.py into separate modules"
    status: pending
    parent_task: "code-review-2026-03-13"
---

# Task: Extract validator classes from plugin_validator.py into separate modules

## Parent Task
- Original: `code-review-2026-03-13`
- Review Date: 2026-03-13

## Status
- [ ] Pending

## Priority
Medium

## Description
`packages/skilllint/plugin_validator.py` is over 2000 lines long and contains at least 7 distinct validator classes plus data models, utility functions, error codes, and CLI entry points all in a single file. This violates separation of concerns and makes the file difficult to navigate, test in isolation, and maintain.

The following classes/sections should be extracted into their own modules under a `validators/` or similar package:

1. **Data models** (`ErrorCode`, `FileType`, `ValidationIssue`, `ValidationResult`, `ComplexityMetrics`) -> `models.py` or `shared/models.py`
2. **`ProgressiveDisclosureValidator`** -> `validators/progressive_disclosure.py`
3. **`InternalLinkValidator`** -> `validators/internal_links.py`
4. **`NamespaceReferenceValidator`** -> `validators/namespace_references.py`
5. **`SymlinkTargetValidator`** -> `validators/symlink_targets.py`
6. **`FrontmatterValidator`** -> `validators/frontmatter.py`
7. **Ignore config logic** (`_load_ignore_config`, `_is_suppressed`, etc.) -> `ignore_config.py`

The current `plugin_validator.py` would become a thin facade that imports and orchestrates the validators.

## Acceptance Criteria
- [ ] Each validator class is in its own module
- [ ] Data models (`ErrorCode`, `ValidationIssue`, `ValidationResult`, etc.) are in a shared models module
- [ ] `plugin_validator.py` imports from new modules and maintains backward-compatible public API
- [ ] All existing tests pass without modification (or with minimal import path updates)
- [ ] No circular imports introduced

## Files to Modify
- `packages/skilllint/plugin_validator.py` - Refactor into thin facade
- `packages/skilllint/validators/` (new package) - Individual validator modules
- `packages/skilllint/models.py` (new) - Shared data models and error codes

## Verification Steps
1. `uv run ruff check packages/skilllint/`
2. `uv run pytest packages/skilllint/tests/ -x`
3. Verify no circular imports: `python -c "from skilllint.plugin_validator import *"`

## References
- Current monolith: `packages/skilllint/plugin_validator.py` (2000+ lines)
