# Initial Packaging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Package the existing `plugin_validator.py` and supporting scripts into a proper Python project publishable to PyPI as `skilllint`, with three CLI entry points (`skilllint`, `agentlint`, `skillint`).

**Architecture:** Source lives in `packages/skilllint/` following the `mcp-json-yaml-toml` repo pattern. Build backend is `hatchling` + `hatch-vcs` for VCS-derived versioning. No logic changes — packaging only.

**Tech Stack:** Python 3.11+, hatchling, hatch-vcs, uv, typer, pydantic, ruamel.yaml, python-frontmatter, tiktoken, gitpython

---

### Task 1: Fix hardcoded `scripts/` import paths in tests

The test files currently load modules via `importlib` pointing at `../scripts/plugin_validator.py` and `../scripts/auto_sync_manifests.py`. In the new layout those files live at `../plugin_validator.py` and `../auto_sync_manifests.py`.

**Files:**
- Modify: `packages/skilllint/tests/conftest.py:27`
- Modify: `packages/skilllint/tests/test_auto_sync_manifests.py:42`

**Step 1: Fix conftest.py**

Change line 27:
```python
# Before
_VALIDATOR_PATH = Path(__file__).parent.parent / "scripts" / "plugin_validator.py"

# After
_VALIDATOR_PATH = Path(__file__).parent.parent / "plugin_validator.py"
```

**Step 2: Fix test_auto_sync_manifests.py**

Change line 42:
```python
# Before
_SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "auto_sync_manifests.py"

# After
_SCRIPT_PATH = Path(__file__).parent.parent / "auto_sync_manifests.py"
```

**Step 3: Commit**

```bash
git add packages/skilllint/tests/conftest.py packages/skilllint/tests/test_auto_sync_manifests.py
git commit -m "fix(tests): update importlib paths from scripts/ to package root"
```

---

### Task 2: Create `__init__.py` and `version.py`

**Files:**
- Create: `packages/skilllint/__init__.py`
- Create: `packages/skilllint/version.py`
- Create: `packages/skilllint/py.typed`

**Step 1: Create `version.py`**

Copy exactly from `mcp-json-yaml-toml` pattern — only change the docstring:

```python
# /// script
# List dependencies for linting only
# dependencies = [
#   "hatchling>=1.14.0",
# ]
# ///
"""Compute the version number and store it in the `__version__` variable.

Based on <https://github.com/maresb/hatch-vcs-footgun-example>.
"""

from __future__ import annotations

import pathlib


def _get_hatch_version() -> str | None:
    try:
        from hatchling.metadata.core import ProjectMetadata
        from hatchling.plugin.manager import PluginManager
        from hatchling.utils.fs import locate_file
    except ImportError:
        return None

    pyproject_toml = locate_file(__file__, "pyproject.toml")
    if pyproject_toml is None:
        raise RuntimeError("pyproject.toml not found although hatchling is installed")
    root = pathlib.Path(pyproject_toml).parent
    metadata = ProjectMetadata(root=str(root), plugin_manager=PluginManager())
    return str(metadata.core.version or metadata.hatch.version.cached)


def _get_importlib_metadata_version() -> str:
    from importlib.metadata import version

    return version(__package__ or __name__)


__version__ = _get_hatch_version() or _get_importlib_metadata_version()
```

**Step 2: Create `__init__.py`**

```python
"""skilllint — static analysis linter for Claude Code plugins, skills, and agents."""

from __future__ import annotations

from skilllint.version import __version__

__all__ = ["__version__"]
```

**Step 3: Create `py.typed`**

Empty marker file:
```bash
touch packages/skilllint/py.typed
```

**Step 4: Commit**

```bash
git add packages/skilllint/__init__.py packages/skilllint/version.py packages/skilllint/py.typed
git commit -m "feat(package): add __init__.py, version.py, py.typed"
```

---

### Task 3: Create `pyproject.toml`

**Files:**
- Create: `pyproject.toml`

**Step 1: Write `pyproject.toml`**

```toml
[project]
name = "skilllint"
description = "Static analysis linter for Claude Code plugins, skills, and agents"
readme = "README.md"
dynamic = ["version"]
authors = [{name = "Jamie Nelson", email = "jamie@bitflight.io"}]
maintainers = [{name = "Jamie Nelson", email = "jamie@bitflight.io"}]
license = {text = "MIT"}
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Quality Assurance",
]
keywords = [
    "claude",
    "claude-code",
    "agent",
    "skill",
    "plugin",
    "linter",
    "static-analysis",
]
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
agentlint = "skilllint.plugin_validator:app"
skillint = "skilllint.plugin_validator:app"
skilllint = "skilllint.plugin_validator:app"

[project.urls]
Homepage = "https://github.com/bitflight-devops/skilllint"
Issues = "https://github.com/bitflight-devops/skilllint/issues"
Repository = "https://github.com/bitflight-devops/skilllint"

[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "basedpyright>=1.37.2",
    "hatch-vcs>=0.5.0",
    "hatchling>=1.14.0",
    "prek>=0.2.19",
    "pytest-cov>=7.0.0",
    "pytest-mock>=3.14.0",
    "pytest-xdist>=3.8.0",
    "pytest>=9.0.2",
    "ruff>=0.14.0",
]

[tool.hatch.build.targets.sdist]
include = [
    "packages/skilllint",
    "README.md",
    "LICENSE",
    "pyproject.toml",
]

[tool.hatch.build.targets.wheel]
include = ["packages/skilllint"]

[tool.hatch.build.targets.wheel.sources]
"packages/skilllint" = "skilllint"

[tool.hatch.version]
source = "vcs"

[tool.pytest.ini_options]
addopts = [
    "--cov-report=term-missing",
    "--cov=packages/skilllint",
    "-v",
    "-n",
    "auto",
]
python_classes = ["Test*"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
pythonpath = [".", "packages/"]
testpaths = ["packages/skilllint/tests"]

[tool.coverage.report]
fail_under = 60
show_missing = true

[tool.coverage.run]
omit = [
    "**/tests/*",
]

[tool.ruff]
fix = true
src = ["packages", "scripts"]
target-version = "py311"

[tool.ruff.lint]
extend-select = ["I", "UP", "B", "RUF"]

[tool.ruff.lint.isort]
required-imports = ["from __future__ import annotations"]
```

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "feat(package): add pyproject.toml with hatchling + three CLI entry points"
```

---

### Task 4: Install and verify the package

**Step 1: Initialize uv and install**

```bash
uv sync
```

Expected: resolves all deps, creates `.venv/`, generates `uv.lock`

**Step 2: Verify three CLI entry points exist**

```bash
uv run skilllint --help
uv run agentlint --help
uv run skillint --help
```

Expected: all three print the Typer help for `plugin-validator`

**Step 3: Commit lockfile**

```bash
git add uv.lock
git commit -m "chore: add uv.lock"
```

---

### Task 5: Fix `plugin_validator.py` PEP 723 shebang

`plugin_validator.py` has a PEP 723 `# /// script` block at the top for running as a standalone script. As a package module it still works, but the shebang line `#!/usr/bin/env -S uv run --quiet --script` will cause issues if the file is executed directly inside the package. Strip the shebang and PEP 723 block — the deps are now declared in `pyproject.toml`.

**Files:**
- Modify: `packages/skilllint/plugin_validator.py:1-11`

**Step 1: Remove lines 1–11**

Lines 1–11 currently read:
```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.21.0",
#     "tiktoken>=0.8.0",
#     "ruamel.yaml>=0.18.0",
#     "python-frontmatter>=1.1.0",
#     "pydantic>=2.0.0",
#     "gitpython>=3.1.45",
# ]
# ///
```

Delete them. The file should start at line 12 (`"""Plugin validator for Claude Code plugins.`).

**Step 2: Run tests to confirm nothing broke**

```bash
uv run pytest packages/skilllint/tests/ -x -q
```

Expected: same pass/fail count as before this change

**Step 3: Commit**

```bash
git add packages/skilllint/plugin_validator.py
git commit -m "chore(package): remove PEP 723 shebang from plugin_validator (deps in pyproject.toml)"
```

---

### Task 6: Run full test suite and verify

**Step 1: Run all tests**

```bash
uv run pytest
```

Note the pass/fail count. Any failures are pre-existing (from the source in `claude_skills`) or from the path fix in Task 1 — do not fix new issues here; log them as follow-up.

**Step 2: Verify package builds**

```bash
uv build
```

Expected: `dist/skilllint-*.whl` and `dist/skilllint-*.tar.gz` created

**Step 3: Commit any final state**

```bash
git add -A
git commit -m "chore: initial working package build"
```

---

### Task 7: Create minimal `README.md` and `LICENSE`

**Files:**
- Create: `README.md`
- Create: `LICENSE`

**Step 1: Write `README.md`**

```markdown
# skilllint

Static analysis linter for Claude Code plugins, skills, and agents.

## Installation

```bash
pip install skilllint
```

## Usage

```bash
skilllint check path/to/plugin/
agentlint check path/to/skill/SKILL.md
skillint check path/to/plugin/plugin.json
```

## CLI entry points

All three commands are aliases for the same tool:
- `skilllint`
- `agentlint`
- `skillint`
```

**Step 2: Copy LICENSE from mcp-json-yaml-toml**

```bash
cp /home/ubuntulinuxqa2/repos/mcp-json-yaml-toml/LICENSE /home/ubuntulinuxqa2/repos/skilllint/LICENSE
```

**Step 3: Commit**

```bash
git add README.md LICENSE
git commit -m "docs: add README and LICENSE"
```
