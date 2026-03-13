# agentskills-linter — Claude Development Notes

## After pushing to a branch

1. **Check CI pipelines** — use `gh run list --repo bitflight-devops/agentskills-linter --limit 10` to see recent runs. If the benchmark or test workflow hasn't triggered (e.g. the workflow file only exists on the branch, not yet on `main`), open a PR to get it running.

2. **Trigger workflow_dispatch manually** — only works if the workflow exists on the default branch. Use:
   ```
   gh workflow run <workflow-file>.yml --repo bitflight-devops/agentskills-linter --ref <branch>
   ```

3. **Check for PR review comments** — after a PR is open, poll with:
   ```
   gh pr checks --repo bitflight-devops/agentskills-linter <pr-number>
   gh api repos/bitflight-devops/agentskills-linter/pulls/<pr-number>/comments
   ```

4. **Always use `--repo bitflight-devops/agentskills-linter`** with `gh` commands — the git remote points to a local proxy (`127.0.0.1`) which `gh` cannot auto-detect as GitHub.

## Benchmark workflow

- Triggers on: PRs targeting `main`, or `workflow_dispatch` (once the file is on `main`)
- Does **not** trigger on plain branch pushes
- Scripts live in `scripts/` — `bench_io.py` (subprocess/I/O) and `bench_cpu.py` (in-process)
- Fixtures in `tests/fixtures/`:
  - `benchmark-plugin-1000-skills.zip` — clean, no violations (no-op scan)
  - `benchmark-plugin-violations.zip` — 200 skills with fixable FM004/FM007/FM008/FM009 violations
- `skilllint --fix` operates **in-place**, so fix benchmarks must copy the fixture to a temp dir before each timed run

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
