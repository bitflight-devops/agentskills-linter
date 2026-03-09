---
phase: 02-platform-adapters
plan: 03
subsystem: schemas
tags: [json-schema, importlib-resources, cursor, codex, agentskills-io]

# Dependency graph
requires:
  - phase: 02-platform-adapters
    provides: load_bundled_schema() function and namespace package pattern (from 02-01, 01-02)
provides:
  - skilllint.schemas.cursor namespace package with v1.json (mdc frontmatter + skill_md schemas)
  - skilllint.schemas.codex namespace package with v1.json (prefix_rule + agents_md + skill_md schemas)
affects:
  - 02-04 (cursor and codex adapter implementations call load_bundled_schema())
  - 02-05 (any further adapter work)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Schema namespace package: __init__.py + v1.json under schemas/<platform>/ for importlib.resources.files() access"
    - "x-experimental sentinel key on prefix_rule schema signals adapter that format is unstable"
    - "x-non-empty sentinel key on agents_md schema signals adapter to check content presence, not JSON structure"

key-files:
  created:
    - packages/skilllint/schemas/cursor/__init__.py
    - packages/skilllint/schemas/cursor/v1.json
    - packages/skilllint/schemas/codex/__init__.py
    - packages/skilllint/schemas/codex/v1.json
  modified: []

key-decisions:
  - "cursor v1.json uses file_types.mdc (JSON Schema draft-07, description required, additionalProperties false) and file_types.skill_md (agentskills.io: name+description required)"
  - "codex v1.json uses custom sentinel keys (x-experimental, x-non-empty, known_fields) rather than full JSON Schema — Codex .rules format is experimental and has no stable schema spec"
  - "skill_md schema identical across cursor and codex (agentskills.io frontmatter: name, description, license, metadata)"

patterns-established:
  - "Sentinel key pattern: x-experimental/x-non-empty communicate adapter behavior without imposing JSON Schema validation on unstable formats"

requirements-completed: [ADPT-04, ADPT-05]

# Metrics
duration: 4min
completed: 2026-03-09
---

# Phase 2 Plan 03: Cursor and Codex Schema Packages Summary

**JSON Schema draft-07 packages for Cursor (.mdc frontmatter) and Codex (prefix_rule/AGENTS.md) platforms, loadable via load_bundled_schema() with no ModuleNotFoundError**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-09T20:37:49Z
- **Completed:** 2026-03-09T20:41:49Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- cursor namespace package: `__init__.py` marker + `v1.json` with `file_types.mdc` (description required, globs/alwaysApply optional, additionalProperties false) and `file_types.skill_md` (agentskills.io frontmatter)
- codex namespace package: `__init__.py` marker + `v1.json` with `file_types.prefix_rule` (x-experimental, known_fields list), `file_types.agents_md` (x-non-empty sentinel), `file_types.skill_md`
- test_bundled_schema.py: 8 passed, no regressions

## Task Commits

1. **Task 1: Cursor schema namespace package** - `fdc3589` (feat)
2. **Task 2: Codex schema namespace package** - `1b97638` (feat)

## Files Created/Modified

- `packages/skilllint/schemas/cursor/__init__.py` - Namespace package marker for importlib.resources.files()
- `packages/skilllint/schemas/cursor/v1.json` - Cursor MDC frontmatter schema + SKILL.md schema
- `packages/skilllint/schemas/codex/__init__.py` - Namespace package marker for importlib.resources.files()
- `packages/skilllint/schemas/codex/v1.json` - Codex prefix_rule/agents_md/skill_md schemas with sentinel keys

## Decisions Made

- Codex prefix_rule format is marked x-experimental per OpenAI docs. Rather than a full JSON Schema (which would be brittle against future format changes), the codex schema stores a known_fields list and valid_decisions list that the adapter uses for soft validation. This matches the RESEARCH.md guidance.
- agents_md uses an x-non-empty sentinel instead of JSON Schema because AGENTS.md is plain Markdown — there is no structured schema to validate against, only presence/content checks.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both schemas ready for 02-04 adapter implementations
- CursorAdapter.get_schema() can call `load_bundled_schema('cursor', 'v1')` and receive `file_types.mdc`
- CodexAdapter.get_schema() can call `load_bundled_schema('codex', 'v1')` and receive all three file_types

---
*Phase: 02-platform-adapters*
*Completed: 2026-03-09*

## Self-Check: PASSED

- FOUND: packages/skilllint/schemas/cursor/__init__.py
- FOUND: packages/skilllint/schemas/cursor/v1.json
- FOUND: packages/skilllint/schemas/codex/__init__.py
- FOUND: packages/skilllint/schemas/codex/v1.json
- FOUND: .planning/phases/02-platform-adapters/02-03-SUMMARY.md
- FOUND: commit fdc3589 (cursor schema package)
- FOUND: commit 1b97638 (codex schema package)
