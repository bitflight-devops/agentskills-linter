---
phase: 01-package-structure
plan: "01"
subsystem: packaging
tags: [hatchling, hatch-vcs, uv, pyproject, pep-561, wheel, pytest]

requires: []

provides:
  - "pyproject.toml with hatchling build backend, hatch-vcs versioning, 3 CLI entry points"
  - "packages/skilllint/__init__.py importing __version__"
  - "packages/skilllint/version.py with VCS-derived version via hatch-vcs"
  - "packages/skilllint/py.typed PEP 561 marker"
  - "Installable wheel: skilllint-0.1.dev20+g42cab43c2-py3-none-any.whl"
  - "521 tests passing at 76.63% coverage on main branch"

affects:
  - 01-package-structure
  - all subsequent phases (package must be importable before any further dev)

tech-stack:
  added:
    - hatchling (build backend)
    - hatch-vcs (VCS-based version management)
    - uv (dependency/venv management)
    - pytest + pytest-cov + pytest-xdist + pytest-mock (test infrastructure)
    - hypothesis (property-based testing)
    - basedpyright (type checking)
    - ruff (linting/formatting)
  patterns:
    - "packages/skilllint/ layout with [tool.hatch.build.targets.wheel.sources] mapping packages/skilllint -> skilllint"
    - "pythonpath = [\".\", \"packages/\"] in pytest config for bare-name module imports"
    - "hatch-vcs for dynamic version from git tags"

key-files:
  created:
    - pyproject.toml
    - packages/skilllint/__init__.py
    - packages/skilllint/version.py
    - packages/skilllint/py.typed
    - LICENSE
    - README.md
    - uv.lock
  modified:
    - packages/skilllint/plugin_validator.py
    - packages/skilllint/tests/conftest.py

key-decisions:
  - "sys.path.insert block retained in plugin_validator.py — removing it breaks frontmatter_core bare-name imports in installed CLI binary; requires module rename refactor before removal"
  - "3 CLI entry points installed: skilllint, skillint, agentlint — all map to skilllint.plugin_validator:app"

patterns-established:
  - "Package source layout: packages/skilllint/ mapped to skilllint namespace via hatch wheel sources"
  - "All module imports use bare names (frontmatter_core, frontmatter_utils) resolved via pythonpath in pytest config and sys.path.insert at runtime"

requirements-completed: [PKG-01, PKG-02]

duration: 7min
completed: 2026-03-03
---

# Phase 1 Plan 01: Initial Package Structure Summary

**Hatchling-based installable package with 3 CLI entry points, hatch-vcs versioning, and 521 tests passing at 76.63% coverage landed on main from feature/initial-packaging**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-03T15:13:42Z
- **Completed:** 2026-03-03T15:20:38Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Merged 9 commits from feature/initial-packaging into main via `--no-ff` merge (no conflicts)
- Package importable as `import skilllint` with version `0.1.dev20+g42cab43c2`
- Wheel produced at `dist/skilllint-0.1.dev20+g42cab43c2-py3-none-any.whl`
- Full test suite: 521 passed, 1 skipped, 0 failures, 76.63% coverage (threshold: 60%)
- No PEP 723 shebang on plugin_validator.py line 1

## Task Commits

Each task was committed atomically:

1. **Task 1: Merge feature/initial-packaging into main** - `42cab43` (feat: merge commit)
2. **Task 2: Verify full test suite passes on merged main** - no additional commit (verification only, no file changes)

## Files Created/Modified

- `pyproject.toml` - Hatchling build config, hatch-vcs version, 3 CLI entry points, pytest + ruff config
- `packages/skilllint/__init__.py` - Package init importing `__version__` from `version.py`
- `packages/skilllint/version.py` - VCS-derived version via `hatch-vcs`
- `packages/skilllint/py.typed` - PEP 561 type marker (empty marker file)
- `packages/skilllint/plugin_validator.py` - PEP 723 shebang removed; sys.path.insert block retained
- `packages/skilllint/tests/conftest.py` - Updated importlib paths from scripts/ to package root
- `uv.lock` - Locked dependency graph (48 packages)
- `LICENSE` - MIT license
- `README.md` - Project readme

## pyproject.toml Entry Points (for Plan 02 reference)

```toml
[project.scripts]
agentlint = "skilllint.plugin_validator:app"
skillint  = "skilllint.plugin_validator:app"
skilllint = "skilllint.plugin_validator:app"
```

Three aliases, all pointing to `skilllint.plugin_validator:app` (Typer app).

## Decisions Made

- **sys.path.insert retained:** The plan suggested removing `sys.path.insert(0, _SCRIPTS_DIR)` from `plugin_validator.py`. This block was NOT removed because `frontmatter_core`, `frontmatter_utils`, and `auto_sync_manifests` are imported using bare module names (`from frontmatter_core import ...`). When the package is installed in a venv, these bare names are not resolvable without the path insertion — confirmed with `python -c "from frontmatter_core import AgentFrontmatter"` failing in the venv. Removing it would break the CLI binary. The proper fix requires renaming these imports to `from skilllint.frontmatter_core import ...` — that refactor is deferred to a later plan (likely Plan 03).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Retained sys.path.insert block — removal would cause runtime import failure**
- **Found during:** Task 1 (Merge feature/initial-packaging into main)
- **Issue:** Plan instructed to remove `sys.path.insert(0, _SCRIPTS_DIR)` block (lines 66-68 in plugin_validator.py). Verified that `from frontmatter_core import ...` imports fail with `ModuleNotFoundError` in the installed venv without this block, because `frontmatter_core.py` is a sibling file in the package but not on `sys.path` at runtime.
- **Fix:** Left the block in place. Documented the prerequisite refactor (rename bare imports to `skilllint.frontmatter_core`) as deferred work.
- **Files modified:** none (no change made)
- **Verification:** `.venv/bin/python -c "import skilllint; print(skilllint.__version__)"` succeeds; all 521 tests pass.

---

**Total deviations:** 1 (plan instruction skipped — removal would cause regression)
**Impact on plan:** All success criteria met. The unremoved sys.path.insert block is pre-existing technical debt from the script-to-package migration, not introduced by this plan.

## Issues Encountered

None beyond the deviation documented above. Merge completed with no conflicts.

## Next Phase Readiness

- Package is installable and importable — all subsequent Phase 1 plans can proceed
- `pyproject.toml` entry points documented above for Plan 02 reference
- `sys.path.insert` + bare module name pattern must be resolved before renaming modules in Plan 03
- The `conftest.py` still uses `spec_from_file_location` for test imports — Plan 03 will address this

---
*Phase: 01-package-structure*
*Completed: 2026-03-03*

## Self-Check: PASSED

- FOUND: .planning/phases/01-package-structure/01-01-SUMMARY.md
- FOUND: pyproject.toml
- FOUND: packages/skilllint/__init__.py
- FOUND: packages/skilllint/version.py
- FOUND: packages/skilllint/py.typed
- FOUND: dist/skilllint-0.1.dev20+g42cab43c2-py3-none-any.whl
- FOUND: commit 42cab43
