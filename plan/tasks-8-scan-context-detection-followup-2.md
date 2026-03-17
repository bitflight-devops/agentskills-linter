---
tasks:
  - task: "T1"
    title: "Add test for BARE-context provider-inside-plugin-tree skip branch"
    status: not-started
    agent: "python3-development:python-pytest-architect"
    dependencies: []
    priority: 3
    complexity: low
---

# Task Plan: Add Missing Q2-Precedence Test

**Goal**: Add a test for the BARE context path where a known provider directory (e.g. `.claude/`) is nested inside a plugin tree and should be skipped (plugin takes precedence over provider — architecture spec Q2 resolution).

**Source**: Code review findings in `.claude/reports/code-review-scan-context-detection.md` (Issue 3)

---

## Context

`scan_runtime.py` lines 252-253:
```python
if any(provider_dir.is_relative_to(pr) for pr in plugin_roots):
    continue
```

This branch — provider dir inside a plugin tree, so it gets skipped — has zero test coverage (lines 252-253 appear in the coverage "Missing" column). The architecture spec names this as Q2: "Plugin takes precedence: `.claude/` inside a plugin is plugin content". Without a test, a future refactor could silently break this invariant.

---

## Task T1: Add test for plugin-over-provider precedence in BARE context

**Description**:

Add a test to `packages/skilllint/tests/test_scan_context.py` inside `TestIntegrationContextAwareDiscovery` (or a new `TestBareContextProviderPrecedence` class):

Scenario: a BARE directory containing a plugin that itself has a `.claude/` subdirectory with agents. The `.claude/` dir is inside the plugin tree, so it should be treated as plugin content (not as a provider directory). The agents inside `.claude/` should NOT appear twice (once from plugin discovery, once from provider discovery).

```python
def test_bare_dir_provider_inside_plugin_tree_skips_provider_discovery(tmp_path):
    # Arrange: plugin with an embedded .claude/ provider dir
    plugin = tmp_path / "my-plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text("{}")
    (plugin / ".claude" / "agents").mkdir(parents=True)
    (plugin / ".claude" / "agents" / "plugin-agent.md").write_text("# Agent")

    # Act
    result = _discover_validatable_paths(tmp_path)

    # Assert: .claude/ inside the plugin is treated as plugin content, not a
    # separate provider. Provider discovery is NOT invoked on it separately.
    # The file may or may not appear (plugin discovery uses convention globs
    # that don't recurse into .claude/), but it must not appear via provider
    # discovery in addition to plugin discovery (no double-counting).
    # Key assertion: the covered_roots branch at line 252 was exercised —
    # verify by counting occurrences.
    agent_path = plugin / ".claude" / "agents" / "plugin-agent.md"
    occurrences = result.count(agent_path)
    assert occurrences <= 1, "Provider dir inside plugin tree must not be double-discovered"
```

**Acceptance Criteria**:
- At least one test exercises the `provider_dir.is_relative_to(pr)` branch at line 252
- Test uses `tmp_path` with real filesystem structures (no mocking)
- `uv run pytest packages/skilllint/tests/test_scan_context.py -v -x -q` passes
- `uv run ruff check packages/skilllint/tests/test_scan_context.py` passes
- Coverage for `scan_runtime.py` lines 250, 253 improves

**Verification**:
1. `uv run ruff check packages/skilllint/tests/test_scan_context.py`
2. `uv run pytest packages/skilllint/tests/ -x -q`
3. `uv run pytest --cov=packages/skilllint --cov-report=term-missing packages/skilllint/tests/ -q 2>&1 | grep "scan_runtime"` — verify lines 250 and 253 no longer appear in Missing
