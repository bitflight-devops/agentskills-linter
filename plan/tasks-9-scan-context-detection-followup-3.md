---
tasks:
  - task: "T1"
    title: "Make manifest-driven agents/commands path addition existence-consistent with skills"
    status: not-started
    agent: "python3-development:python-cli-architect"
    dependencies: []
    priority: 4
    complexity: low
---

# Task Plan: Fix Inconsistent Existence-Checking in _discover_plugin_paths

**Goal**: Align the manifest-driven `agents` and `commands` path-addition code with the `skills` branch, which checks for existence before adding paths to the discovery set.

**Source**: Code review findings in `.claude/reports/code-review-scan-context-detection.md` (Issue 4)

---

## Context

In `packages/skilllint/scan_runtime.py`, `_discover_plugin_paths()` manifest-driven mode:

**Skills branch (lines 130-138)** — checks existence before adding:
```python
if manifest.skills is not None:
    for rel in manifest.skills:
        resolved = root / rel
        if resolved.is_dir():
            skill_md = resolved / "SKILL.md"
            if skill_md.exists():
                discovered.add(skill_md)
        else:
            discovered.add(resolved)
```

**Agents/commands branch (lines 140-142)** — adds unconditionally:
```python
for path_list in (manifest.agents, manifest.commands):
    if path_list is not None:
        discovered.update(root / rel for rel in path_list)
```

A plugin.json that declares a nonexistent agent or command path causes a nonexistent `Path` object to enter the discovery result. Downstream validators receiving nonexistent paths may raise `FileNotFoundError` or silently skip, producing confusing output.

---

## Task T1: Add existence check for manifest-driven agents and commands

**Description**:

Update `_discover_plugin_paths()` in `packages/skilllint/scan_runtime.py` to only add agent and command paths if the resolved path exists:

```python
for path_list in (manifest.agents, manifest.commands):
    if path_list is not None:
        for rel in path_list:
            resolved = root / rel
            if resolved.exists():
                discovered.add(resolved)
```

Also add a test in `packages/skilllint/tests/test_scan_context.py` verifying that a manifest declaring a nonexistent agent path does not add the nonexistent path to the discovery result.

**Acceptance Criteria**:
- Manifest-declared agent/command paths are only added if they exist on disk
- Behavior is now consistent with the skills branch
- New test: `PluginManifest(agents=["agents/ghost.md"])` on a directory without `agents/ghost.md` — `ghost.md` must not appear in the result
- `uv run ruff check packages/skilllint/scan_runtime.py packages/skilllint/tests/test_scan_context.py` passes
- `uv run pytest packages/skilllint/tests/ -x -q` passes

**Note**: If there is a deliberate design intent for agents/commands to be added unconditionally (e.g., to allow validators to flag missing declared files), document it as a comment in the code and close this task without changing the code. The current absence of any such comment or test makes this look like an oversight.

**Verification**:
1. `uv run ruff check packages/skilllint/scan_runtime.py`
2. `uv run pytest packages/skilllint/tests/ -x -q`
