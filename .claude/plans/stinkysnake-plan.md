# Stinkysnake Phase 3 — Type Modernization Plan

**Date:** 2026-03-13
**Scope:** `packages/skilllint/frontmatter_core.py` (5 `Any` usages) and one function
signature in `packages/skilllint/plugin_validator.py`
**Phase 2 source:** Zero annotation gaps across the project; all remaining `Any` are
concentrated in the two files above.

---

## Background and Correction

Phase 2 identified a `ClaudeSettingsModel` at lines ~183-184 of `frontmatter_core.py`.
That class does not exist. The actual model at those lines is `AgentFrontmatter`. The
Phase 2 report mislabeled it. All five `Any` usages belong to three models in
`frontmatter_core.py`:

| Line | Model | Field |
|------|-------|-------|
| ~95 | `SkillFrontmatter` | `hooks: dict[str, Any] \| None` |
| ~133 | `CommandFrontmatter` | `hooks: dict[str, Any] \| None` |
| ~183 | `AgentFrontmatter` | `mcp_servers: list[Any] \| dict[str, Any] \| None` |
| ~184 | `AgentFrontmatter` | `hooks: dict[str, Any] \| None` |
| ~278 | module-level function | `fix_skill_name_field` params typed `dict[str, Any]` |

---

## Change 1 — Define `HookEntryConfig` TypedDict

### What

Add a new `TypedDict` to `frontmatter_core.py` that represents a single entry in a
hook list.

Evidence from real hooks.json files (hookify, security-guidance, ralph-wiggum):

```
{
  "type": "command",       # always present; values: "command" | "prompt"
  "command": "...",        # present when type == "command"
  "timeout": 10            # optional integer, seconds
}
```

Proposed definition (no implementation — types and fields only):

```python
from typing import Literal, Required
from typing_extensions import TypedDict  # or typing on 3.11+

class HookEntryConfig(TypedDict, total=False):
    type: Required[Literal["command", "prompt"]]
    command: str          # required when type == "command"; optional at TypedDict level
    timeout: int
```

`total=False` with `Required` on `type` is the right shape: `command` is structurally
required for the "command" subtype but is not always present when `type == "prompt"`.
A simpler `total=True` with all fields required would cause false Pydantic validation
failures, so `total=False` + `Required[type]` is preferred.

### Why

`hooks: dict[str, Any]` gives zero information to callers. The actual value is a dict
with event-type keys (`PreToolUse`, `PostToolUse`, `Stop`, `UserPromptSubmit`,
`SessionStart`, `SessionEnd`) mapping to lists of hook groups, each of which has a
`hooks` list of `HookEntryConfig`. Naming the entry type enables type-checked access
to `type`, `command`, and `timeout` fields throughout the validator.

### Also define `HookGroupConfig`

```python
class HookGroupConfig(TypedDict, total=False):
    hooks: Required[list[HookEntryConfig]]
    matcher: str   # optional tool-name filter regex, e.g. "Edit|Write"
```

Evidence: `security-guidance/hooks/hooks.json` shows `matcher` is an optional sibling
of `hooks` at the group level.

### Replace target

```python
# Before
hooks: dict[str, Any] | None

# After
hooks: dict[str, list[HookGroupConfig]] | None
```

The outer dict key is the event-type string (one of the `VALID_EVENT_TYPES` in the
validator). The value is a list of hook groups.

### Risk level: LOW

- Pydantic with `model_config = ConfigDict(extra="allow")` will accept any dict;
  narrowing the annotation does not change runtime validation behaviour because Pydantic
  does not validate `TypedDict` fields inside a `BaseModel` field by default.
- No Pydantic validator exists for the `hooks` field on any of the three models; the
  validator handles hook structure separately in `HooksValidator`.
- The change is annotation-only; no runtime behaviour changes.

### Test update needed: NO

No test exercises the type of the `hooks` field value at the Python type level.
The `HooksValidator` tests cover runtime structure validation independently.

---

## Change 2 — Define `McpServerConfig` TypedDict

### What

Add a `TypedDict` to `frontmatter_core.py` for a single MCP server entry.

Evidence from the three canonical example files in
`plugins/plugin-dev/skills/mcp-integration/examples/`:

**stdio shape** (`stdio-server.json`):
```json
{
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "..."],
  "env": {"LOG_LEVEL": "info"}
}
```

**HTTP shape** (`http-server.json`):
```json
{
  "type": "http",
  "url": "https://api.example.com/mcp",
  "headers": {"Authorization": "Bearer ${API_TOKEN}"}
}
```

**SSE shape** (`sse-server.json`):
```json
{
  "type": "sse",
  "url": "https://mcp.example.com/sse",
  "headers": {"X-API-Version": "v1"}
}
```

The discriminant is `type`. When `type` is absent the entry is stdio.

Proposed definition (no implementation):

```python
class McpServerConfig(TypedDict, total=False):
    type: Literal["http", "sse"]   # absent = stdio
    command: str                    # stdio only
    args: list[str]                 # stdio only
    env: dict[str, str]             # stdio only
    url: str                        # http/sse
    headers: dict[str, str]         # http/sse, optional
```

### Replace target

`mcp_servers` on `AgentFrontmatter` has the union type
`list[Any] | dict[str, Any] | None`. In practice the field is:

- `dict[str, McpServerConfig]` — a named map of server name → config (the standard
  shape used in agent frontmatter, matching the `mcpServers` key in Claude settings)
- `list[Any]` — the list branch appears in the annotation but has no evidence in
  fixtures or vendor examples; it may have been added defensively

Recommendation: keep the union but narrow both branches:

```python
# Before
mcp_servers: list[Any] | dict[str, Any] | None

# After
mcp_servers: list[McpServerConfig] | dict[str, McpServerConfig] | None
```

If no real-world YAML uses the list form, a follow-up Phase 4 task can remove it after
confirming with test fixtures. Do not remove it in Phase 3 (breaking change risk).

### Why

`dict[str, Any]` provides no information about server fields. With `McpServerConfig`,
mypy and pyright can flag missing required keys (`command` for stdio, `url` for
http/sse) and typos in field names.

### Risk level: LOW for annotation; LOW-MEDIUM for list branch removal (defer)

Pydantic does not validate TypedDict field contents inside a BaseModel union field
by default. Annotation tightening is safe. Removing the `list` branch would be a
semantic narrowing — defer to Phase 4 with fixture evidence.

### Test update needed: NO

The `AgentFrontmatter` model tests validate round-trip serialization of the whole
model, not the inner structure of `mcp_servers`. No test will fail from this
annotation change.

---

## Change 3 — Replace `dict[str, Any]` with `YamlValue` in `fix_skill_name_field`

### What

`plugin_validator.py` already defines:

```python
# Line ~40 in plugin_validator.py
YamlValue: TypeAlias = dict[str, "YamlValue"] | list["YamlValue"] | str | int | float | bool | None
```

The function `fix_skill_name_field` in `frontmatter_core.py` (line ~278) is currently:

```python
def fix_skill_name_field(
    normalized_dict: dict[str, Any],
    file_path: Path,
    fixes: list[str],
) -> dict[str, Any]:
```

`dict[str, Any]` is structurally equivalent to the `dict[str, YamlValue]` variant of
`YamlValue`, but without the shared alias the two files diverge in expressed intent.

### Two options

**Option A (preferred): import `YamlValue` into `frontmatter_core.py`**

- Add `YamlValue` TypeAlias definition directly to `frontmatter_core.py` (copy, do
  not import from `plugin_validator.py` — `frontmatter_core` is a library module
  intentionally free of imports from `plugin_validator` per the DI constraint in its
  module docstring).
- Replace `dict[str, Any]` with `dict[str, YamlValue]` in the function signature.
- The `YamlValue` alias in `plugin_validator.py` remains; both files define it
  independently. This avoids a circular import and preserves the DI boundary.

**Option B: widen to bare `YamlValue`**

- Not applicable here: the parameter is specifically a dict, not an arbitrary YAML
  value. `dict[str, YamlValue]` is the correct type.

### Why

Eliminates the last `Any` in `frontmatter_core.py`. Aligns with the alias already
used pervasively in `plugin_validator.py`. Makes the function's contract explicit:
it accepts YAML-parsed frontmatter dicts, not arbitrary Python objects.

### Risk level: LOW

`fix_skill_name_field` is only called from `plugin_validator.py`, which already passes
`dict[str, YamlValue]` arguments. The annotation tightening is compatible.

### Test update needed: NO

No test directly asserts the parameter type of `fix_skill_name_field`. Existing
call-site tests continue to pass unchanged.

---

## Change 4 — Assess Pydantic `model_config` strictness

### Current state

All three frontmatter models use:

```python
model_config = ConfigDict(extra="allow")
```

`AgentFrontmatter` additionally sets `populate_by_name=True`.

### Assessment

**Should `strict=True` be added now that fields are typed?**

**Recommendation: NO for Phase 3. Conditional YES for a future phase.**

Reasons against adding `strict=True` now:

1. **`extra="allow"` is deliberate.** The module docstring explicitly documents the
   Open/Closed design: new fields are added to the YAML spec without changing the
   model. `strict=True` in Pydantic controls type coercion, not extra fields, but the
   combination of `strict=True` + validators that coerce list→str would create
   contradictions: the `normalize_comma_separated` validators accept `list` inputs and
   convert them. With `strict=True`, Pydantic would reject the list before the
   validator runs.

2. **`normalize_comma_separated` requires coercion mode.** The validators on `skills`,
   `tools`, `allowed_tools`, `disallowed_tools` explicitly handle `list` input for
   fields typed as `str | None`. This is standard lax-mode validation. `strict=True`
   would break these validators.

3. **No type-safety regression from the current `Any` fields.** The `hooks` and
   `mcp_servers` fields are not validated by Pydantic — they pass through as-is
   (structural validation is done by `HooksValidator`). Typing them more precisely
   does not require model-level strictness.

**What would be appropriate in a future phase:**

- Add `model_config = ConfigDict(extra="allow", strict=False)` explicitly to document
  the intent (it is already the default, but making it explicit prevents accidental
  addition of `strict=True` by a future contributor).
- Consider `model_config = ConfigDict(extra="forbid")` on `CommandFrontmatter` only,
  since `CommandFrontmatter.description` is `str` (required, not optional) and the
  command schema is tighter. This would be a breaking change requiring test updates.

**Risk level of adding `strict=True`: HIGH — do not do it.**

**Risk level of documenting `strict=False` explicitly: LOW — optional housekeeping.**

---

## Implementation Order

Perform changes in this sequence to keep diffs reviewable:

1. **Change 3 first** — add `YamlValue` alias to `frontmatter_core.py` and update
   `fix_skill_name_field` signature. This is a pure annotation change with no
   structural impact on the models, easiest to verify in isolation.

2. **Change 1** — define `HookEntryConfig` and `HookGroupConfig` TypedDicts, then
   replace all three `hooks: dict[str, Any] | None` fields. All three models change
   in one commit so the TypedDicts are introduced and consumed together.

3. **Change 2** — define `McpServerConfig` TypedDict and narrow `mcp_servers` on
   `AgentFrontmatter`. Separate commit from Change 1 so MCP and hooks changes are
   independently reviewable.

4. **Change 4 (optional)** — add explicit `strict=False` annotation to `model_config`
   calls as a documentation-only clarification. Can be combined with Change 2 or
   deferred to a later housekeeping pass.

---

## Files to Modify

| File | Changes |
|------|---------|
| `packages/skilllint/frontmatter_core.py` | Add `YamlValue` TypeAlias; add `HookEntryConfig`, `HookGroupConfig`, `McpServerConfig` TypedDicts; update 5 field annotations and 1 function signature |
| `packages/skilllint/plugin_validator.py` | No changes required — `YamlValue` alias stays in place; `fix_skill_name_field` call sites already pass `dict[str, YamlValue]` |

---

## Summary Table

| Change | Files | Risk | Test update |
|--------|-------|------|-------------|
| 1. `HookEntryConfig` + `HookGroupConfig`, replace 3 `hooks` fields | `frontmatter_core.py` | Low | No |
| 2. `McpServerConfig`, narrow `mcp_servers` | `frontmatter_core.py` | Low | No |
| 3. `YamlValue` alias + `fix_skill_name_field` signature | `frontmatter_core.py` | Low | No |
| 4. Explicit `strict=False` on `model_config` | `frontmatter_core.py` | Low (optional) | No |
| Do NOT add `strict=True` | — | High if done | — |
