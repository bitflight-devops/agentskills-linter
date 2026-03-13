---
tasks:
  - task: "Add unit tests for ClaudeCodeAdapter class"
    status: pending
    parent_task: "code-review-2026-03-13"
---

# Task: Add unit tests for ClaudeCodeAdapter

## Parent Task
- Original: `code-review-2026-03-13`
- Review Date: 2026-03-13

## Status
- [ ] Pending

## Priority
High

## Description
The `ClaudeCodeAdapter` class in `packages/skilllint/adapters/claude_code/adapter.py` has no dedicated unit tests. While `test_adapters.py` exists, it does not contain tests for `ClaudeCodeAdapter` specifically. This class implements the `PlatformAdapter` Protocol and contains validation logic for JSON plugin files (PL002, PL003 error codes), schema loading delegation, and path pattern matching -- all of which need test coverage.

Key behaviors to test:
- `id()` returns `"claude_code"`
- `path_patterns()` returns expected glob patterns
- `applicable_rules()` returns `{"SK", "PR", "HK", "AS"}`
- `get_schema()` loads and returns correct schema sections
- `validate()` returns empty list for non-JSON files
- `validate()` returns PL002 error for invalid JSON
- `validate()` returns PL003 errors for missing required fields
- `validate()` returns empty list for valid plugin JSON

## Acceptance Criteria
- [ ] New test class `TestClaudeCodeAdapter` in `test_adapters.py` (or new `test_claude_code_adapter.py`)
- [ ] Tests cover all 5 public methods: `id`, `path_patterns`, `applicable_rules`, `get_schema`, `validate`
- [ ] Tests cover error paths: invalid JSON (PL002), missing required fields (PL003)
- [ ] Tests cover happy path: valid plugin JSON returns no violations
- [ ] All tests pass with `uv run pytest`

## Files to Modify
- `packages/skilllint/tests/test_adapters.py` - Add `TestClaudeCodeAdapter` test class (or create new file)

## Verification Steps
1. `uv run pytest packages/skilllint/tests/test_adapters.py -x -v`
2. `uv run pytest --cov=skilllint.adapters.claude_code --cov-report=term-missing`

## References
- Source code: `packages/skilllint/adapters/claude_code/adapter.py`
- Protocol definition: `packages/skilllint/adapters/protocol.py`
