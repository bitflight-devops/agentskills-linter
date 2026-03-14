---
id: T01
parent: S02
milestone: M001
provides:
  - Adapters using load_provider_schema() with constraint_scopes() method
  - AS-series rules with authority metadata
  - Violation dicts including authority provenance
  - constraint_scope filtering available in validate_file()
key_files:
  - packages/skilllint/adapters/claude_code/adapter.py
  - packages/skilllint/adapters/cursor/adapter.py
  - packages/skilllint/adapters/codex/adapter.py
  - packages/skilllint/adapters/protocol.py
  - packages/skilllint/rules/as_series.py
  - packages/skilllint/plugin_validator.py
  - packages/skilllint/schemas/agentskills_io/v1.json
key_decisions:
  - D004: Added constraint_scopes() method to PlatformAdapter protocol for provider-specific rule filtering
  - D005: AS-series rules use authority metadata from agentskills.io specification
patterns_established:
  - _make_violation() helper automatically includes authority from rule registry
  - Adapters expose constraint_scopes() for future provider-specific rule filtering
observability_surfaces:
  - DEBUG-level logging in validate_file() shows constraint_scopes per adapter
  - Violation JSON output includes 'authority' field with origin and reference
duration: 2h
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Wire provider schema routing and authority into validation path

**Wired S01's provider schema infrastructure into the validation path, enabling provider-aware validation with authority provenance.**

## What Happened

Updated all three platform adapters (claude_code, cursor, codex) to use `load_provider_schema()` from `skilllint.schemas` instead of `load_bundled_schema()`. Added `constraint_scopes()` method to the PlatformAdapter protocol and each adapter implementation, returning the set of constraint_scope values from the loaded schema.

Added authority metadata to all AS-series rules (AS001-AS006) via the `@skilllint_rule` decorator, with origin pointing to agentskills.io and reference URLs to the specification sections.

Created `_make_violation()` helper function in as_series.py that automatically looks up and includes authority metadata from the rule registry when building violation dicts.

Updated `validate_file()` in plugin_validator.py to extract constraint_scopes from the primary adapter, logging at DEBUG level for visibility.

Fixed missing `provenance` key in agentskills_io schema that was causing a pre-existing test failure.

## Verification

- `cd packages/skilllint && python -m pytest tests/ -x` — 570 passed, 1 skipped
- `python -c "from skilllint.schemas import load_provider_schema; s = load_provider_schema('claude_code'); print(s['provenance'])"` — prints provenance dict with authority_url, last_verified, provider_id
- `python -c "from skilllint.rules.as_series import *; from skilllint.rule_registry import list_rules; print([r.authority for r in list_rules() if r.authority])"` — shows all 6 AS-series rules with authority
- Manual verification: violation dicts now include `authority` field with `origin` and `reference` keys

## Diagnostics

- Run `skilllint check --platform claude-code --verbose` to see constraint_scopes in debug output
- Check `violation.authority` in JSON output for provenance (origin + reference URL)
- Use `.venv/bin/python -c "from skilllint.adapters.claude_code import ClaudeCodeAdapter; print(ClaudeCodeAdapter().constraint_scopes())"` to inspect scopes

## Deviations

None — implemented exactly as specified in the task plan.

## Known Issues

None discovered during implementation.

## Files Created/Modified

- `packages/skilllint/adapters/claude_code/adapter.py` — switched to load_provider_schema(), added constraint_scopes() method
- `packages/skilllint/adapters/cursor/adapter.py` — switched to load_provider_schema(), added constraint_scopes() method
- `packages/skilllint/adapters/codex/adapter.py` — switched to load_provider_schema(), added constraint_scopes() method
- `packages/skilllint/adapters/protocol.py` — added constraint_scopes() to Protocol definition
- `packages/skilllint/rules/as_series.py` — added authority metadata to all AS-series rules, added _make_violation() helper
- `packages/skilllint/plugin_validator.py` — added constraint_scopes extraction in validate_file(), added logging
- `packages/skilllint/schemas/agentskills_io/v1.json` — added missing provenance key and constraint_scope annotations
- `.gsd/milestones/M001/slices/S02/S02-PLAN.md` — added observability section
- `.gsd/milestones/M001/slices/S02/tasks/T01-PLAN.md` — added observability impact section
