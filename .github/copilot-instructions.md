# Copilot instructions for `agentskills-linter`

Trust this file first and only search the repo when these instructions are incomplete or proven wrong.

## What this repo is

- `skilllint` is a small Python CLI package that statically validates AI agent assets: plugins, skills, agents, commands, hooks, and cross-plugin references.
- It targets Claude Code, Cursor, Codex, and third-party adapters exposed through Python entry points.
- Main language/runtime: Python 3.11-3.14. CI currently exercises Python 3.11 and 3.12.
- Packaging/tooling: `uv`, Hatch/Hatchling + `hatch-vcs`, Ruff, Astral's `ty` type checker, `pytest`, `prek` (the Rust pre-commit runner used in this repo), Biome, markdownlint.
- CLI entry points `skilllint`, `agentlint`, `pluginlint`, and the legacy alias `skillint` all point to `skilllint.plugin_validator:app`.

## High-value paths

- `packages/skilllint/plugin_validator.py` - main Typer CLI and most validation/reporting logic.
- `packages/skilllint/frontmatter_core.py` - Pydantic frontmatter schemas and normalization helpers.
- `packages/skilllint/frontmatter_utils.py` - ruamel YAML round-trip helpers used by auto-fix paths.
- `packages/skilllint/auto_sync_manifests.py` - manifest sync/version-bump logic used by pre-commit-style workflows.
- `packages/skilllint/adapters/` - bundled platform adapters (`claude_code`, `cursor`, `codex`).
- `packages/skilllint/tests/` - primary pytest suite.
- `scripts/fetch_platform_docs.py` - standalone `uv` script for refreshing vendor docs under `.claude/vendor/`.
- `.github/workflows/test.yml` - CI format/lint/type/test/release flow.
- `.github/workflows/publish.yml` - release-publish flow (`uv build` + `uv publish`).
- Root config files worth checking before edits: `pyproject.toml`, `.pre-commit-config.yaml`, `.pre-commit-hooks.yaml`, `biome.json`, `.markdownlint-cli2.jsonc`, `.prettierrc`.

## Repo root at a glance

- Product/docs: `README.md`, `LICENSE`, `docs/`
- Python package + tests: `packages/`, `tests/`
- Build/config: `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `.pre-commit-hooks.yaml`, `biome.json`, `.markdownlint-cli2.jsonc`, `.prettierrc`
- Automation: `.github/workflows/`, `scripts/`

## Validated command sequence

Always run commands from the repository root.

1. **Install `uv` if it is missing.** In this sandbox `uv` was not preinstalled; `python3 -m pip install --user uv` was required, then `export PATH="$HOME/.local/bin:$PATH"`.
2. **Bootstrap:** `uv sync`
   - Creates `.venv` and installs the full dev toolchain.
   - Clean bootstrap from `rm -rf .venv && uv sync` worked.
   - Warm rerun was effectively instant (`~0.05s`).
3. **Format check:** `uv run ruff format --check`
4. **Lint:** `uv run ruff check`
5. **Type check:** `uv run ty check packages/ --output-format github`
6. **CLI smoke test:** `uv run skilllint --help` or `uv run skilllint <path>`
7. **Build:** `uv build`
8. **Pre-push gate:** `uv run prek run --all-files`
   - This repo uses `prek` instead of the Python `pre-commit` CLI.

### Observed command behavior

- `uv build` and `uv run skilllint --help` both succeeded, but emitted a `setuptools_scm` warning because this checkout is shallow. Treat that warning as expected in shallow clones; do not change packaging just to suppress it.
- `uv run prek run --all-files` passed, but the first run took about `12s` because it cloned/installed hook repos (`markdownlint-cli2`, Biome, shellcheck, etc.). Subsequent runs should be faster.
- Full pytest on this branch was **not clean at baseline**: `uv run pytest` ended with `590 passed, 1 skipped, 2 failed` in `packages/skilllint/tests/test_auto_sync_manifests.py` (`TestFormatJson` Prettier-format expectations). Unless your task is about manifest JSON formatting, treat those as pre-existing failures and avoid unrelated fixes there.

## Test/validation details

- Pytest config lives in `pyproject.toml`; it runs with coverage and `xdist` (`-n auto`) against `**/tests`, with a `60%` minimum coverage gate.
- CI order in `.github/workflows/test.yml` is:
  1. `uv sync`
  2. `uv run ruff format --check`
  3. `uv run ruff check --output-format=github`
  4. `uv run ty check packages/ --output-format github`
  5. `uv run pytest --cov=packages/skilllint --cov-report=xml --cov-report=term`
- The same workflow publishes a coverage comment on PRs, and on pushes to `main` it runs a release/tag job after all checks pass.
- `.github/workflows/publish.yml` runs only on published GitHub releases and does `uv build` then `uv publish`.

## Change guidance

- Most feature work lands in `packages/skilllint/plugin_validator.py`; schema-only work belongs in `frontmatter_core.py`; adapter-specific logic belongs under `packages/skilllint/adapters/<platform>/`.
- If a task mentions plugin or marketplace version syncing, start in `auto_sync_manifests.py` and the matching tests in `packages/skilllint/tests/test_auto_sync_manifests.py`.
- `docs/plans/` contains planning/history, not runtime behavior; do not edit it unless the task is specifically documentation or planning related.
- Prefer targeted tests for the files you change, then run the validated repo gate(s) above.

Trust these instructions and only fall back to repo-wide searching when the information here is missing or incorrect.
