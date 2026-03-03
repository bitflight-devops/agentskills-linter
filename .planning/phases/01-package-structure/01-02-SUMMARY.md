---
phase: 01-package-structure
plan: 02
subsystem: packaging
tags: [hatchling, wheel, importlib-resources, pyproject-toml, cli-entrypoints, json-schema]

# Dependency graph
requires:
  - phase: 01-package-structure/01-01
    provides: merged hatchling package with 3 CLI entry points and 521 passing tests
provides:
  - All 4 CLI aliases (skilllint, agentlint, pluginlint, skillint) defined in pyproject.toml
  - Test exclusion from distributed wheel
  - Bundled schema snapshot at skilllint/schemas/claude_code/v1.json
  - load_bundled_schema() utility exported from skilllint package
  - importlib.resources.files() access pattern for runtime schema loading
affects:
  - 02-platform-adapters (consumes load_bundled_schema and schemas directory)
  - 03-validation-rules (may reference bundled schemas)
  - 07-plugin-distribution (wheel packaging patterns established)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "importlib.resources.files() for bundled data file access (Python 3.11+ style)"
    - "pyproject.toml [tool.hatch.build.targets.wheel] exclude pattern for test exclusion"
    - "Namespace package __init__.py for schema subdirectories"

key-files:
  created:
    - packages/skilllint/schemas/__init__.py
    - packages/skilllint/schemas/claude_code/__init__.py
    - packages/skilllint/schemas/claude_code/v1.json
    - packages/skilllint/tests/test_bundled_schema.py
  modified:
    - pyproject.toml
    - packages/skilllint/__init__.py

key-decisions:
  - "pluginlint added as 4th CLI alias — all four map to skilllint.plugin_validator:app"
  - "Schema directory uses __init__.py namespace markers for IDE navigation and importlib.resources compatibility"
  - "v1.json is a Phase 1 placeholder with field-type metadata; Phase 2 replaces with adapter-driven content"
  - "load_bundled_schema() added to skilllint.__init__.__all__ for direct package-level import"

patterns-established:
  - "Bundled JSON data files accessed via importlib.resources.files('skilllint.schemas.<platform>').joinpath('<version>.json')"
  - "Wheel test exclusion: exclude = ['packages/skilllint/tests'] in [tool.hatch.build.targets.wheel]"

requirements-completed: [PKG-03, PKG-04]

# Metrics
duration: 4min
completed: 2026-03-03
---

# Phase 1 Plan 02: CLI Entry Points, Wheel Test Exclusion, and Bundled Schema Summary

**All 4 CLI aliases active (pluginlint added), tests excluded from wheel, and importlib.resources-accessible v1.json schema bundled with load_bundled_schema() utility**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-03T15:24:15Z
- **Completed:** 2026-03-03T15:28:34Z
- **Tasks:** 2 (Task 2 used TDD — 3 commits: test RED, feat GREEN)
- **Files modified:** 6

## Accomplishments

- Added `pluginlint` as the 4th CLI entry point; all 4 aliases produce identical `--help` output
- Added `exclude = ["packages/skilllint/tests"]` to wheel config; `unzip -l dist/*.whl | grep tests` returns empty
- Created `packages/skilllint/schemas/claude_code/v1.json` — bundled schema snapshot present in wheel
- Added `load_bundled_schema(platform, version='v1')` to `skilllint.__init__`, exported via `__all__`
- Full test suite: 529 passing (was 521 — 8 new tests added), 1 skipped, 0 failing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pluginlint entry point and exclude tests from wheel** - `0083d86` (feat)
2. **Task 2 RED: Failing tests for bundled schema** - `96bd723` (test)
3. **Task 2 GREEN: Create bundled schema directory and load_bundled_schema** - `ee32104` (feat)

**Plan metadata:** _(docs commit — pending final commit)_

_Note: TDD task 2 has two commits (test → feat)._

## Files Created/Modified

- `pyproject.toml` - Added pluginlint entry point; added wheel test exclusion
- `packages/skilllint/__init__.py` - Added load_bundled_schema() function and import
- `packages/skilllint/schemas/__init__.py` - Namespace package marker for schemas directory
- `packages/skilllint/schemas/claude_code/__init__.py` - Namespace package marker for claude_code subdirectory
- `packages/skilllint/schemas/claude_code/v1.json` - Bundled schema snapshot with $schema, platform, and file_types keys
- `packages/skilllint/tests/test_bundled_schema.py` - 8 tests verifying importlib.resources access and load_bundled_schema()

## Wheel Contents Verification

```
$ unzip -l dist/skilllint-0.1.dev23+g96bd72306.d20260303-py3-none-any.whl | grep -E "(schemas|tests)"
       99  2020-02-02 00:00   skilllint/schemas/__init__.py
      107  2020-02-02 00:00   skilllint/schemas/claude_code/__init__.py
     1042  2020-02-02 00:00   skilllint/schemas/claude_code/v1.json
# (no tests entries — excluded as required)
```

```
$ unzip -p dist/*.whl "*.dist-info/entry_points.txt"
[console_scripts]
agentlint = skilllint.plugin_validator:app
pluginlint = skilllint.plugin_validator:app
skillint = skilllint.plugin_validator:app
skilllint = skilllint.plugin_validator:app
```

## Decisions Made

- `pluginlint` added as 4th alias matching the existing pattern — all four map to `skilllint.plugin_validator:app`
- Schema directory uses `__init__.py` namespace markers for IDE navigation alongside importlib.resources traversal
- `v1.json` is a Phase 1 placeholder capturing Pydantic model field names; Phase 2 PlatformAdapter will populate full schemas
- `load_bundled_schema()` added to package `__all__` for clean import at `from skilllint import load_bundled_schema`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- PKG-03 and PKG-04 requirements complete
- Phase 2 (platform adapters) can import `load_bundled_schema("claude_code")` and override with adapter-driven schemas
- Schema directory structure at `packages/skilllint/schemas/<platform>/` is ready for additional platform directories
- Wheel distribution tested end-to-end: build, install, CLI execution all confirmed working

## Self-Check: PASSED

- FOUND: `packages/skilllint/schemas/__init__.py`
- FOUND: `packages/skilllint/schemas/claude_code/__init__.py`
- FOUND: `packages/skilllint/schemas/claude_code/v1.json`
- FOUND: `.planning/phases/01-package-structure/01-02-SUMMARY.md`
- FOUND commit `0083d86`: feat(01-02): add pluginlint entry point and exclude tests from wheel
- FOUND commit `96bd723`: test(01-02): add failing tests for bundled schema and load_bundled_schema
- FOUND commit `ee32104`: feat(01-02): create bundled schema directory and load_bundled_schema utility

---
*Phase: 01-package-structure*
*Completed: 2026-03-03*
