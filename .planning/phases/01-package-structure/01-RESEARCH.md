# Phase 1: Package Structure - Research

**Researched:** 2026-03-02
**Domain:** Python packaging with hatchling + uv; PEP 723 to installable package migration; importlib.resources schema bundling
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PKG-01 | Package structured as installable Python package (`packages/skilllint/`) with `pyproject.toml` and hatchling build backend — replacing PEP 723 standalone scripts | Worktree `feature/initial-packaging` has a working `pyproject.toml` with hatchling + hatch-vcs; `__init__.py`, `version.py`, `py.typed` all created; PEP 723 shebang removed from `plugin_validator.py`. 521/522 tests pass. |
| PKG-02 | Package installs via `uv add skilllint` or `pip install skilllint` and is distributable as a `.whl` | Working `.whl` already built in worktree (`skilllint-0.1.dev8+g9e0cbf1da.d20260301-py3-none-any.whl`). `uv build` command confirmed. |
| PKG-03 | CLI entry points `skilllint`, `agentlint`, `pluginlint`, and `skillint` all invoke the same binary | Worktree has 3 of 4 entry points (`skilllint`, `agentlint`, `skillint`). `pluginlint` is missing and must be added to `[project.scripts]` in `pyproject.toml`. |
| PKG-04 | Platform schema snapshots (JSON files) bundled inside the wheel and accessed via `importlib.resources.files()` at runtime | No schema files exist yet. Must create `packages/skilllint/schemas/claude_code/v1.json` and configure `[tool.hatch.build.targets.wheel.force-include]` or ensure the schemas/ directory is inside the package root. |
| PKG-05 | PEP 723 → package migration atomic — pre-commit hook users not broken; existing `uv run plugin_validator.py` workflow preserved or explicitly migrated | No `.pre-commit-hooks.yaml` exists. No pre-commit migration documentation exists. Must add `pluginlint.yaml` (or equivalent) pre-commit hook config and document the migration from `uv run plugin_validator.py`. |
</phase_requirements>

## Summary

Phase 1 starts from a strong position: a `feature/initial-packaging` git worktree at `/home/ubuntulinuxqa2/repos/skilllint/.worktrees/initial-packaging` has already completed most of the packaging work. The worktree has a working `pyproject.toml` with hatchling build backend, `__init__.py`, `version.py`, `py.typed`, removed PEP 723 shebang from `plugin_validator.py`, fixed test import paths, and built a `.whl`. All 521 of 522 tests pass (1 skipped). This work must be merged into `main` or rebased before planning further phases.

Three gaps remain between the worktree state and full PKG-01 through PKG-05 compliance. First, `pluginlint` is missing from `[project.scripts]` — the worktree has `skilllint`, `agentlint`, and `skillint` but not `pluginlint` (PKG-03). Second, no platform schema JSON files exist and the wheel contains no `schemas/` directory (PKG-04). Third, no `.pre-commit-hooks.yaml` exists and there is no documentation for migrating from `uv run plugin_validator.py` to the packaged entry point (PKG-05).

The tests still load `plugin_validator` via `importlib.util.spec_from_file_location` in `conftest.py` — this works but means tests do not exercise the package import path. After packaging, tests should import `from skilllint import plugin_validator` or `import skilllint.plugin_validator` to validate the installed package rather than loading the source file by path. This is not a blocking gap but is a quality issue the planner should address.

**Primary recommendation:** Merge `feature/initial-packaging` into `main`, add `pluginlint` entry point, create minimal `schemas/claude_code/v1.json` schema file, add `.pre-commit-hooks.yaml`, update test imports, and document the PEP 723 migration.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hatchling | latest | Build backend for wheel/sdist | Default backend for `uv init --lib`; supports `force-include` for arbitrary file inclusion; already in worktree pyproject.toml |
| hatch-vcs | >=0.5.0 | VCS-derived versioning from git tags | Already in worktree; `dynamic = ["version"]` + `[tool.hatch.version] source = "vcs"` pattern |
| uv | latest | Package manager; `uv build` produces wheel | Already used for PEP 723 scripts; `uv add skilllint` is the install command for PKG-02 |
| importlib.resources | stdlib 3.11 | Access bundled schema files at runtime | `files("skilllint.schemas.claude_code").joinpath("v1.json")` works in both editable and wheel installs |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=9.0.2 | Test suite runner | Already in worktree dev deps; run with `uv run pytest` |
| pytest-cov | >=7.0.0 | Coverage measurement | Already in worktree; coverage threshold at 60% |
| pytest-xdist | >=3.8.0 | Parallel test execution | Already in worktree; `-n auto` in addopts |
| ruff | >=0.14.0 | Linting and formatting | Already in worktree dev deps |
| basedpyright | >=1.37.2 | Type checking | Already in worktree dev deps |
| prek | >=0.2.19 | Pre-commit hook runner | Already in worktree dev deps — use for `.pre-commit-hooks.yaml` validation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hatchling | setuptools | setuptools requires MANIFEST.in and package-data dict syntax; hatchling is cleaner |
| hatch-vcs | manual version bump | Manual bumps are error-prone; VCS sourcing is zero-maintenance |
| importlib.resources | `__file__`-relative paths | `__file__` breaks in zipimport and some wheel layouts; importlib.resources is the correct stdlib approach |

**Installation:**
```bash
# In worktree/repo root (builds .whl)
uv build

# Test install into isolated env
uv tool install dist/skilllint-*.whl

# Development install
uv sync
```

## Architecture Patterns

### Recommended Project Structure
```
packages/skilllint/         # Hatchling maps this to skilllint/ in the wheel
├── __init__.py             # Package init; imports __version__
├── version.py              # VCS-derived version via hatch-vcs pattern
├── py.typed                # PEP 561 marker — package ships type stubs
├── plugin_validator.py     # CLI + all validators (monolith — not split in Phase 1)
├── frontmatter_core.py     # Pydantic models for frontmatter fields
├── frontmatter_utils.py    # ruamel.yaml round-trip I/O
├── auto_sync_manifests.py  # Manifest sync tool
├── schemas/                # Bundled schema snapshots — NEW in Phase 1
│   └── claude_code/
│       └── v1.json         # Minimal Claude Code schema snapshot
└── tests/
    ├── conftest.py         # Fixtures — update to import from package, not file path
    └── test_*.py           # Existing test suite (521 passing)
```

Note: The monolith is NOT split in Phase 1. Splitting validators into `validators/` is Phase 2+ work. Phase 1 only packages the existing structure.

### Pattern 1: hatchling wheel source mapping
**What:** Map `packages/skilllint/` source directory to `skilllint/` package name in the wheel using `[tool.hatch.build.targets.wheel.sources]`.
**When to use:** Always — this is how the worktree pyproject.toml already works.
**Example:**
```toml
# Source: worktree pyproject.toml (verified working)
[tool.hatch.build.targets.wheel]
include = ["packages/skilllint"]

[tool.hatch.build.targets.wheel.sources]
"packages/skilllint" = "skilllint"
```

### Pattern 2: Schema bundling via include
**What:** Place schema JSON files inside `packages/skilllint/schemas/` — hatchling includes all files in the mapped package directory by default, so no special `force-include` is needed.
**When to use:** For Phase 1 schema bundling. The `force-include` syntax is only needed for files OUTSIDE the package source root.
**Example:**
```
packages/skilllint/schemas/claude_code/v1.json   # Inside package root — auto-included
```

```python
# Runtime access — verified Python 3.11 stdlib pattern
# Source: https://docs.python.org/3/library/importlib.resources.html
from importlib.resources import files
import json

def load_schema(platform: str, version: str = "v1") -> dict:
    ref = files(f"skilllint.schemas.{platform}").joinpath(f"{version}.json")
    return json.loads(ref.read_bytes())
```

For the `schemas/` subdirectory to be importable as a Python package via `importlib.resources.files()`, it needs `__init__.py` files at each level, OR use the `files()` traversal API which does NOT require `__init__.py` in Python 3.11+.

### Pattern 3: Multiple CLI entry points — all pointing to same function
**What:** `[project.scripts]` maps multiple command names to the same `module:attribute` target.
**When to use:** To satisfy PKG-03 — all four aliases invoke identical binary.
**Example:**
```toml
# Source: Python Packaging Authority — project.scripts spec
[project.scripts]
skilllint  = "skilllint.plugin_validator:app"
agentlint  = "skilllint.plugin_validator:app"
pluginlint = "skilllint.plugin_validator:app"
skillint   = "skilllint.plugin_validator:app"
```

Note: `pluginlint` is the MISSING entry point in the current worktree (has 3 of 4).

### Pattern 4: Pre-commit hook definition
**What:** `.pre-commit-hooks.yaml` at repo root declares the hook so users can reference it via `repo:` in their `.pre-commit-config.yaml`.
**When to use:** Required for PKG-05 — pre-commit hook users must not be broken.
**Example:**
```yaml
# .pre-commit-hooks.yaml at repo root
- id: skilllint
  name: skilllint
  description: Lint AI agent plugins, skills, and agents
  language: python
  entry: skilllint
  types: [markdown, json, yaml]
  pass_filenames: true
  additional_dependencies: []
```

Users' `.pre-commit-config.yaml` would reference:
```yaml
repos:
  - repo: https://github.com/bitflight-devops/skilllint
    rev: v0.1.0
    hooks:
      - id: skilllint
```

### Pattern 5: Test import from package (not file path)
**What:** Replace `importlib.util.spec_from_file_location` with a direct package import so tests exercise the installed package import path.
**When to use:** After packaging — tests should validate the package, not the source file.
**Example:**
```python
# Before (current conftest.py — loads by file path)
_VALIDATOR_PATH = Path(__file__).parent.parent / "plugin_validator.py"
spec = importlib.util.spec_from_file_location("plugin_validator", _VALIDATOR_PATH)
plugin_validator = importlib.util.module_from_spec(spec)

# After (correct for packaged module)
import skilllint.plugin_validator as plugin_validator
```

The `conftest.py` `pythonpath = [".", "packages/"]` in `pyproject.toml` already sets up the path so that `import skilllint.plugin_validator` resolves correctly during tests.

### Anti-Patterns to Avoid
- **Tests bundled in wheel:** The current worktree includes `tests/` inside the wheel (visible in wheel contents). Tests should be excluded with a `[tool.hatch.build.targets.wheel.exclude]` rule: `"**/tests"`. Tests in the distributed wheel waste space and confuse users.
- **schema files outside package root:** Do not put `schemas/` at repo root or `packages/schemas/`. They must be inside `packages/skilllint/schemas/` to be picked up by hatchling's wheel include.
- **`__file__`-relative resource paths:** Do not use `Path(__file__).parent / "schemas" / "..."` to load schemas at runtime. Use `importlib.resources.files()` exclusively.
- **`pkg_resources`:** Deprecated. Never use for resource access. `importlib.resources` is the stdlib replacement.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| VCS-derived versioning | Custom git tag parsing | `hatch-vcs` | Handles dirty trees, dev suffixes, PEP 440 normalization correctly |
| Schema file bundling | Custom file copy script | hatchling's package include mechanism | Files inside the package directory are auto-included; `force-include` for files outside |
| Runtime resource access | `__file__`-relative path joins | `importlib.resources.files()` | `__file__` is unreliable in zipimport and some wheel install configurations |
| Entry point aliasing | Wrapper scripts | `[project.scripts]` pointing same target | pip installs shim scripts automatically; no shell wrapper needed |
| Pre-commit hook language detection | Custom entry wrapper | `language: python` in `.pre-commit-hooks.yaml` | pre-commit creates an isolated venv and installs the package via pip automatically |

**Key insight:** Everything a Phase 1 packaging task requires is handled by standard Python packaging tooling. No custom build scripts, no post-install hooks, no shell wrappers.

## Common Pitfalls

### Pitfall 1: PEP 723 shebang left in plugin_validator.py
**What goes wrong:** If the `#!/usr/bin/env -S uv run --quiet --script` shebang line remains, the file can still be run as a script but the `uv run` invocation creates a new isolated venv with its own deps, ignoring the installed package. Developers may unknowingly run the old PEP 723 script instead of the packaged CLI.
**Why it happens:** Worktree already removed it (commit `9e0cbf1`), but it is easy to reintroduce on merge or rebase conflicts.
**How to avoid:** After merge, verify `plugin_validator.py` line 1 does NOT start with `#!`.
**Warning signs:** `uv run plugin_validator.py` installs different deps than `uv sync`; CLI behavior differs between `skilllint` and `uv run plugin_validator.py`.

### Pitfall 2: Tests bundled in the distributed wheel
**What goes wrong:** The current worktree wheel includes `skilllint/tests/*.py`. End users who `uv add skilllint` receive test files they don't need, increasing wheel size. CI running `import skilllint.tests` unexpectedly succeeds.
**Why it happens:** Hatchling includes everything in the mapped package directory by default.
**How to avoid:** Add wheel exclude to `pyproject.toml`:
```toml
[tool.hatch.build.targets.wheel]
include = ["packages/skilllint"]
exclude = ["packages/skilllint/tests"]
```
**Warning signs:** `unzip -l dist/skilllint-*.whl | grep test` shows test files.

### Pitfall 3: schema/ directory not importable via importlib.resources without __init__.py (Python < 3.9 only)
**What goes wrong:** In Python 3.9+, `importlib.resources.files()` works on namespace packages (no `__init__.py` needed). But earlier Python versions require `__init__.py` at each level. Since the project requires Python >=3.11, this is not a blocking issue.
**Why it happens:** Historical `pkg_resources` requirement for `__init__.py` in data directories.
**How to avoid:** Since Python >=3.11 is required, empty `__init__.py` files in `schemas/` subdirectories are optional but harmless. Add them for IDE navigation clarity.
**Warning signs:** `importlib.resources.files("skilllint.schemas")` raises `ModuleNotFoundError` (would only happen on Python < 3.9, not applicable here).

### Pitfall 4: pluginlint missing from entry points (currently in worktree)
**What goes wrong:** PKG-03 requires all four aliases; the worktree has 3. Any user or CI that types `pluginlint` gets `command not found`.
**Why it happens:** The worktree's initial packaging plan only specified 3 entry points (see `docs/plans/2026-02-27-initial-packaging.md`).
**How to avoid:** Add `pluginlint = "skilllint.plugin_validator:app"` to `[project.scripts]` before merging.
**Warning signs:** `pluginlint --help` returns exit 127 after `uv tool install`.

### Pitfall 5: PEP 723 → package migration breaks pre-commit hook users
**What goes wrong:** Users who have `.pre-commit-config.yaml` referencing `uv run plugin_validator.py` or using `local` hooks pointing at the script path get import errors (`ModuleNotFoundError: No module named 'frontmatter_core'`) after the package restructure, because `frontmatter_core.py` is now inside the `skilllint` package and not on the script's `sys.path`.
**Why it happens:** PEP 723 scripts used `sys.path.insert(0, _SCRIPTS_DIR)` to find sibling modules. Once packaged, `frontmatter_core` is `skilllint.frontmatter_core` — the old import path breaks.
**How to avoid:** Add `.pre-commit-hooks.yaml` defining a `skilllint` hook. Document the migration path in `README.md`. The existing `sys.path.insert` in `plugin_validator.py` is now dead code and should be removed (it does nothing in the packaged context since modules resolve via the package hierarchy).
**Warning signs:** `ModuleNotFoundError: No module named 'frontmatter_core'` in CI after upgrading.

### Pitfall 6: conftest.py still loads by file path (spec_from_file_location)
**What goes wrong:** `conftest.py` uses `importlib.util.spec_from_file_location("plugin_validator", _VALIDATOR_PATH)` to load the module by filesystem path. This means tests exercise the raw source file, not the installed package import chain. After packaging, the correct test target is `import skilllint.plugin_validator`.
**Why it happens:** Legacy pattern from when the code was a PEP 723 script with no package.
**How to avoid:** Replace `spec_from_file_location` with a direct `import skilllint.plugin_validator as plugin_validator`. The `pythonpath = [".", "packages/"]` in `pyproject.toml` pytest config already makes this work.
**Warning signs:** Mocker patches reference `plugin_validator.shutil.which` — after migration to package imports, patches must use `skilllint.plugin_validator.shutil.which`.

## Code Examples

Verified patterns from official sources:

### pyproject.toml: complete Phase 1 configuration
```toml
# Source: https://hatch.pypa.io/1.13/config/build/ (hatchling docs, verified)
[project]
name = "skilllint"
description = "Static analysis linter for Claude Code plugins, skills, and agents"
readme = "README.md"
dynamic = ["version"]
requires-python = ">=3.11,<3.15"
dependencies = [
    "gitpython>=3.1.45",
    "pydantic>=2.0.0",
    "python-frontmatter>=1.1.0",
    "ruamel.yaml>=0.18.0",
    "tiktoken>=0.8.0",
    "typer>=0.21.0",
]

[project.scripts]
skilllint  = "skilllint.plugin_validator:app"
agentlint  = "skilllint.plugin_validator:app"
pluginlint = "skilllint.plugin_validator:app"
skillint   = "skilllint.plugin_validator:app"

[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
include = ["packages/skilllint"]
exclude = ["packages/skilllint/tests"]

[tool.hatch.build.targets.wheel.sources]
"packages/skilllint" = "skilllint"

[tool.hatch.version]
source = "vcs"
```

### importlib.resources schema access (Python 3.11+)
```python
# Source: https://docs.python.org/3/library/importlib.resources.html (stdlib, verified)
from __future__ import annotations

import json
from importlib.resources import files


def load_bundled_schema(platform: str, version: str = "v1") -> dict:
    """Load a bundled platform schema snapshot."""
    ref = files(f"skilllint.schemas.{platform}").joinpath(f"{version}.json")
    return json.loads(ref.read_bytes())


# Usage
schema = load_bundled_schema("claude_code")
```

### Minimal .pre-commit-hooks.yaml
```yaml
# Source: https://pre-commit.com/index.html#creating-new-hooks (official docs pattern)
- id: skilllint
  name: skilllint
  description: Validate AI agent plugins, skills, and agents
  language: python
  entry: skilllint
  types_or: [markdown, json, yaml]
  pass_filenames: true
```

### conftest.py updated import (post-packaging)
```python
# Before (loads by file path — current worktree state)
import importlib.util
_VALIDATOR_PATH = Path(__file__).parent.parent / "plugin_validator.py"
spec = importlib.util.spec_from_file_location("plugin_validator", _VALIDATOR_PATH)
plugin_validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin_validator)

# After (imports from installed package — correct post-packaging)
import skilllint.plugin_validator as plugin_validator
```

Note: After this change, mocker patches must use the full module path:
`mocker.patch("skilllint.plugin_validator.shutil.which", return_value=...)`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PEP 723 `#!/usr/bin/env -S uv run` shebang script | Proper `pyproject.toml` package with `hatchling` build backend | Phase 1 (this phase) | `uv add skilllint` works; `pip install skilllint` works; wheel distributable |
| `sys.path.insert(0, _SCRIPTS_DIR)` for sibling imports | Package imports: `from skilllint.frontmatter_core import ...` | Phase 1 (this phase) | IDE autocomplete works; mypy resolves imports; no runtime path manipulation |
| `importlib.util.spec_from_file_location` in tests | `import skilllint.plugin_validator as plugin_validator` | Phase 1 (this phase) | Tests validate the installed package, not the raw source file |
| No CLI entry points | `[project.scripts]` with 4 aliases | Phase 1 (this phase) | `skilllint`, `agentlint`, `pluginlint`, `skillint` all work after install |

**Deprecated/outdated:**
- `uv run plugin_validator.py`: Still works if the PEP 723 shebang is present, but intentionally deprecated in Phase 1. Migration path: use `skilllint` entry point instead.
- `sys.path.insert(0, _SCRIPTS_DIR)` in `plugin_validator.py:67-69`: Dead code post-packaging. The `frontmatter_core` and `frontmatter_utils` modules are in the same package; Python resolves them via the package hierarchy.

## Open Questions

1. **Should tests/ be excluded from the wheel?**
   - What we know: Current worktree wheel includes test files; this wastes space for end users
   - What's unclear: Whether any downstream consumers need `import skilllint.tests` (unlikely)
   - Recommendation: Exclude with `[tool.hatch.build.targets.wheel] exclude = ["packages/skilllint/tests"]`

2. **What should the minimal claude_code/v1.json schema contain?**
   - What we know: The existing `frontmatter_core.py` already has Pydantic models for `SkillFrontmatter`, `AgentFrontmatter`, `CommandFrontmatter` — these ARE the schema
   - What's unclear: PKG-04 says "bundled schema JSON files accessible via importlib.resources.files()" — Phase 2 will define the full `PlatformAdapter` that loads these; Phase 1 only needs to establish the directory and file structure
   - Recommendation: Create a minimal `v1.json` that is a JSON Schema derived from the Pydantic models; the exact content can be a placeholder that Phase 2 will flesh out

3. **Should `uv run plugin_validator.py` still work after Phase 1?**
   - What we know: PKG-05 says the migration must be atomic and pre-commit hook users not broken; `uv run plugin_validator.py` currently works via PEP 723 inline deps
   - What's unclear: The PEP 723 shebang was removed in the worktree. Without the shebang, `uv run plugin_validator.py` still works in newer uv but without inline dep installation. With the shebang removed, `python plugin_validator.py` would fail (missing deps).
   - Recommendation: Remove the shebang and document in README that `uv run plugin_validator.py` is replaced by `skilllint`. Add a deprecation notice at the top of `plugin_validator.py` (as a comment, not runtime output).

4. **Does the initial-packaging worktree need to be rebased before Phase 1 starts?**
   - What we know: The worktree branch `feature/initial-packaging` has 8 commits ahead of `main` with all packaging work done; `main` has the planning files the worktree doesn't
   - What's unclear: Whether the planner should plan a rebase/merge task or treat the worktree as the starting point
   - Recommendation: The planner should include a task to merge `feature/initial-packaging` into `main` (or rebase it on top of the planning commits), verify tests still pass, then continue from there

## Sources

### Primary (HIGH confidence)
- Hatchling build configuration: https://hatch.pypa.io/1.13/config/build/ — force-include syntax, wheel sources mapping, package include/exclude
- Python Packaging User Guide: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ — project.scripts, package data
- importlib.resources Python 3.11 stdlib: https://docs.python.org/3/library/importlib.resources.html — files() API, Python 3.11 namespace package support
- Pre-commit hook creation guide: https://pre-commit.com/index.html#creating-new-hooks — .pre-commit-hooks.yaml format
- Existing worktree `feature/initial-packaging` — direct inspection; 521/522 tests pass, wheel built, entry points verified

### Secondary (MEDIUM confidence)
- Existing codebase audit (conftest.py, pyproject.toml, plugin_validator.py) — direct file reads, current state of tests and entry points verified

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — worktree already works; all tools verified in production
- Architecture: HIGH — patterns verified in built wheel and passing test suite
- Pitfalls: HIGH — most pitfalls observed directly by inspecting worktree state (missing pluginlint, tests in wheel, file-path test imports)

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (Python packaging tooling is stable; hatchling/uv APIs change slowly)
