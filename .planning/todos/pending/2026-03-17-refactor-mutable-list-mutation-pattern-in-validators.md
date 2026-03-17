---
created: 2026-03-17T18:14:32.370Z
title: Refactor mutable list mutation pattern in validators
area: tooling
files:
  - packages/skilllint/plugin_validator.py
  - packages/skilllint/rules/pa_series.py
  - packages/skilllint/frontmatter_core.py
---

## Problem

Functions throughout the validation pipeline take mutable `errors` and `warnings` lists as parameters and append to them as a side effect. This pattern:

- Makes data flow hard to trace (hidden side effects)
- Couples callers to the mutation contract
- Was flagged by /simplify review as "consistent with codebase" — which means the smell has been copied enough times to look intentional

Examples: `_check_hooks()`, `_check_mcp_servers()`, `_check_permission_mode()` in pa_series.py; `_validate_pydantic_model()`, `_check_list_valued_tool_fields()` in plugin_validator.py.

## Solution

Functions should return their issues (e.g., `list[ValidationIssue]`), letting callers collect via `errors.extend(check_hooks(...))`. The top-level `check_pa001()` already does this correctly — the internal helpers should follow the same pattern.

Scope: all validator helpers that currently mutate passed-in lists. This is a systematic refactor, not a one-off fix.
