# skilllint — Claude Development Notes

## After pushing to a branch

1. **Check CI pipelines** — use `gh run list --repo bitflight-devops/skilllint --limit 10` to see recent runs. If the benchmark or test workflow hasn't triggered (e.g. the workflow file only exists on the branch, not yet on `main`), open a PR to get it running.

2. **Trigger workflow_dispatch manually** — only works if the workflow exists on the default branch. Use:
   ```
   gh workflow run <workflow-file>.yml --repo bitflight-devops/skilllint --ref <branch>
   ```

3. **Check for PR review comments** — after a PR is open, poll with:
   ```
   gh pr checks --repo bitflight-devops/skilllint <pr-number>
   gh api repos/bitflight-devops/skilllint/pulls/<pr-number>/comments
   ```

4. **Always use `--repo bitflight-devops/skilllint`** with `gh` commands — the git remote points to a local proxy (`127.0.0.1`) which `gh` cannot auto-detect as GitHub.

## Benchmark workflow

- Triggers on: PRs targeting `main`, or `workflow_dispatch` (once the file is on `main`)
- Does **not** trigger on plain branch pushes
- Scripts live in `scripts/` — `bench_io.py` (subprocess/I/O) and `bench_cpu.py` (in-process)
- Fixtures in `tests/fixtures/`:
  - `benchmark-plugin-1000-skills.zip` — clean, no violations (no-op scan)
  - `benchmark-plugin-violations.zip` — 200 skills with fixable FM004/FM007/FM008/FM009 violations
- `skilllint check --fix` operates **in-place**, so fix benchmarks must copy the fixture to a temp dir before each timed run

## Vendor documentation cache (`skilllint docs`)

When agents need external documentation (Claude hooks docs, Cursor rules docs, etc.), they must **not** use WebFetch or MCP URL-reading tools to pull pages into context. Fetch to disk first, then read from disk.

### CLI commands

```
# Cache a page (prints the file path to stdout)
skilllint docs fetch URL

# List sections in a cached file
skilllint docs sections FILE

# Extract a single section (heading text or markdown anchor slug)
skilllint docs section FILE HEADING

# Verify file integrity against its .meta.json sidecar
skilllint docs verify FILE

# Find the most recent cached file for a page name
skilllint docs latest PAGE_NAME
```

### Standalone script (outside the skilllint CLI)

```
uv run --script scripts/fetch_doc_source.py fetch URL
uv run --script scripts/fetch_doc_source.py sections FILE
uv run --script scripts/fetch_doc_source.py section FILE HEADING
uv run --script scripts/fetch_doc_source.py verify FILE
uv run --script scripts/fetch_doc_source.py latest PAGE_NAME
```

`scripts/fetch_doc_source.py` is a PEP 723 standalone script with `[tool.uv.sources]` pointing to the local skilllint package. Same commands as `skilllint docs`, usable before `skilllint` is installed.

### File locations

- Cached pages: `.claude/vendor/sources/{page-name}-{YYYY-MM-DD-HHMM}.md`
- Sidecar metadata: `.claude/vendor/sources/{page-name}-{YYYY-MM-DD-HHMM}.meta.json`
- Page names are derived from the URL path (e.g. `https://docs.anthropic.com/en/docs/claude-code/settings.md` → `claude-code--settings`)

### Offline-first behaviour

Stale cache is served when the network is unavailable (`STALE` status, warning to stderr). The command only fails when **no cache exists AND the network is down**.

### Agent instructions

1. Run `skilllint docs fetch URL` to cache the page. The file path is printed to stdout.
2. Use the Read tool on that file path. For large files, run `skilllint docs sections FILE` first to find the right section, then `skilllint docs section FILE HEADING` to extract just that part.

### Relationship to `fetch_platform_docs.py`

`scripts/fetch_platform_docs.py` handles **bulk vendor sync** — git clones and HTTP crawl to `.claude/vendor/{provider}/`. `skilllint docs` handles **on-demand single-page capture** to `.claude/vendor/sources/`. Both scripts import shared low-level utilities from `packages/skilllint/vendor_io.py`. `scripts/fetch_spec_schema.py` also imports from `vendor_io.py`.

## Orchestrator delegation discipline

Claude operates as an orchestrator — it coordinates agents rather than doing file-level work itself.

**The rule:** Never read a source file, config, or test file into your own context unless you are about to Edit or Write it in that same turn. Pass the file path to an agent instead.

**Why this matters:**
- Reading files consumes shared context window space
- Agents have fresh, full context — they can discover, diagnose, and fix in one pass
- The orchestrator stays lightweight and can coordinate multiple agents in parallel

**Correct pattern:**
- Instead of: read file → understand issue → tell agent where/how to fix
- Do: tell agent "find the issue in `path/to/file.py` and fix it", let the agent read and act

**For CI failures specifically:**
- Delegate log fetching + root cause analysis + fix to a single agent
- Don't grep logs into your own context — pass the run ID and repo to the agent

**For formatting/lint fixes:**
- Delegate even single-file ruff format calls — the agent handles it without bloating orchestrator context

## No inline CI code

Never write logic directly in `.github/workflows/*.yml` `run:` blocks beyond a single-line call.

**Why:** Inline shell in YAML cannot be linted, has no syntax highlighting, cannot be unit-tested, and is invisible to ruff/shellcheck.

**Rule:** Any logic beyond a trivial one-liner belongs in `scripts/`. Create a Python or shell script there and call it from the workflow:

```yaml
# BAD — logic inline in CI
- name: Run benchmark
  run: |
    python -c "import json, pathlib; ..."
    if [ -f result.json ]; then
      ...
    fi

# GOOD — script in scripts/, called from CI
- name: Run benchmark
  run: python scripts/bench_io.py /tmp/bench-plugin --output scripts/results/bench_io_gh.json
```

This applies to: data processing, conditional logic, multi-step setup, JSON manipulation, file operations.

## Test directory layout

The project has two test locations — this is intentional, not accidental.

### `packages/skilllint/tests/`
Unit and integration tests for the `skilllint` package itself: validators, CLI, adapters, reporters, frontmatter utilities. These tests import directly from the package and run entirely in-process.

### `tests/` (root)
Project-level tests that are not owned by any package:
- `test_fetch_platform_docs.py` — tests `scripts/fetch_platform_docs.py`, a root-level project script
- `tests/benchmarks/` — performance benchmarks that invoke `skilllint` as an installed CLI via subprocess (black-box tests); cannot live inside the package tests because they treat `skilllint` as an external process
- `tests/fixtures/` — shared zip archives used by the benchmark suite

### Rule: where does a new test go?
- Tests that `import` from `skilllint` → `packages/skilllint/tests/`
- Tests for root-level scripts (`scripts/*.py`) → `tests/`
- Benchmarks (subprocess/CLI invocation) → `tests/benchmarks/`

Both locations are discovered by `pytest` via `testpaths = ["**/tests"]` in `pyproject.toml`.

## Python typing policy

External input is ingested only through explicit boundaries (`packages/skilllint/boundary/`, `*_ingest.py`, etc.), validated with **Pydantic** (`BaseModel` / `TypeAdapter`, strict mode where producer errors must not be coerced away), and passed inward as concrete types. Property-test boundary validators with **Hypothesis** where practical. The typed core avoids `typing.Any`, unjustified `cast()`, and raw payloads as application data. **Type checking:** `uv run ty check packages/` only (CI / pre-commit). `pyproject.toml` keeps **mypy** and **basedpyright** effectively off so they do not overlap or conflict with `ty` or duplicate config. Full standard: `docs/TYPING_POLICY.md`.

## No invented constraints

A numeric limit without a source is a hallucination. Every threshold, max length, timeout, or cap must have an origin.

**Invented constraint (bad):**
```python
if len(summary) > 60:
    summary = summary[:57] + "..."
```

Where does 60 come from? No spec, no comment, no justification. This is made up.

**Sourced constraint (good):**
```python
# Claude Code spec: skill names 1-64 chars, alphanumeric + hyphens
# https://docs.anthropic.com/claude-code/skills#naming
MAX_SKILL_NAME_LENGTH = 64
```

**Rules:**

1. **Every numeric constant must have a source** — a spec URL, a config value, a library default, or a comment explaining the reasoning.

2. **Check if the library already handles it** — Rich tables auto-size columns. Requests has timeouts. Don't reinvent limits the tool already provides.

3. **If there's no source, there's no constraint** — don't invent a "reasonable" threshold. Either find the spec or remove the limit.

**Why this matters:** Invented constraints are a leading indicator of hallucination. The model makes up something plausible-sounding but baseless. Catching these prevents subtle bugs and documents the actual requirements.
