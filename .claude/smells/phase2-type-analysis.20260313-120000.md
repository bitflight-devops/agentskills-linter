## Phase 2: Type Analysis

### Python Version Constraint
- Minimum version: 3.11
- Maximum version: <3.15
- Available features: `match` statements (3.10+), `ExceptionGroup` (3.11+), `Self` type (3.11+), `StrEnum` (3.11+), `TaskGroup` (3.11+), `tomllib` (3.11+), built-in generics (`list[int]` vs `List[int]`), `X | Y` union syntax (3.10+), `type` statement (3.12+, not min-version safe)

### Explicit Any Usage

#### Production Code (packages/skilllint/, excluding tests/)

| File:Line | Variable/Return | Current: Any | Proposed Replacement |
|-----------|----------------|--------------|---------------------|
| frontmatter_core.py:95 | `hooks` field | `dict[str, Any] \| None` | `dict[str, str \| list[str] \| dict[str, str]] \| None` -- or define a `HookConfig` TypedDict |
| frontmatter_core.py:133 | `hooks` field | `dict[str, Any] \| None` | Same as above -- shared `HookConfig` TypedDict |
| frontmatter_core.py:183 | `mcp_servers` field | `list[Any] \| dict[str, Any] \| None` | `list[McpServerConfig] \| dict[str, McpServerConfig] \| None` -- define `McpServerConfig` TypedDict |
| frontmatter_core.py:184 | `hooks` field | `dict[str, Any] \| None` | Shared `HookConfig` TypedDict |
| frontmatter_core.py:278 | `fix_skill_name_field` params & return | `dict[str, Any]` (x2) | Consider `dict[str, YamlValue]` -- the project already defines `YamlValue` in `plugin_validator.py` |

**Note:** `plugin_validator.py` line 40 already defines a proper `YamlValue` TypeAlias that is more specific than `Any`:
```python
YamlValue: TypeAlias = dict[str, "YamlValue"] | list["YamlValue"] | str | int | float | bool | None
```
This alias could replace several `Any` usages in `frontmatter_core.py`.

#### Test Code (excluded from priority -- ANN rules are already suppressed for tests)

| File:Line | Variable/Return | Current: Any | Notes |
|-----------|----------------|--------------|-------|
| tests/conftest.py:34 | `invoke(*args, **kwargs)` | `*args: Any, **kwargs: Any` | Acceptable -- wrapper delegation pattern |
| tests/test_auto_sync_manifests.py (22 occurrences) | `monkeypatch: Any` | Should be `pytest.MonkeyPatch` | Low priority, tests exempt from ANN rules |
| tests/benchmarks/test_benchmark.py:39,51,96 | `dict[str, Any]` | JSON record dicts | Acceptable for benchmark JSON serialization |

#### plugin_validator.py -- No Any in type annotations
Line 4297 contains "Any" only in a docstring (`renderable: Any Rich renderable`), not in a type annotation. No action needed.

### Annotation Gaps (implicit Any risk)

| File:Line | Function | Missing |
|-----------|----------|---------|
| (none)    | --       | --      |

**All production functions have complete type annotations.** Zero annotation gaps were found in `packages/skilllint/` (excluding tests). Zero annotation gaps were found in `scripts/`, `tests/`, and `.github/` directories.

### ty Type Checker Results

```
$ uv run ty check packages/ --output-format concise 2>&1
All checks passed!
```

Zero type errors detected by ty.

### Summary
- **Explicit Any count (production):** 5 locations across 1 file (`frontmatter_core.py`)
- **Explicit Any count (tests):** 25 occurrences (exempt per ruff config)
- **Annotation gaps:** 0
- **ty errors:** 0
- **High-priority replacements:**
  1. **`frontmatter_core.py:278` -- `fix_skill_name_field`**: Replace `dict[str, Any]` with `dict[str, YamlValue]` using the existing `YamlValue` alias from `plugin_validator.py`. This is the simplest win since the type already exists in the project.
  2. **`frontmatter_core.py:95,133,184` -- `hooks` fields**: Define a `HookConfig = TypedDict(...)` or at minimum use `dict[str, str | list[str]]` to constrain the hooks structure across all three Pydantic models (`SkillFrontmatter`, `AgentFrontmatter`, `ClaudeSettingsModel`).
  3. **`frontmatter_core.py:183` -- `mcp_servers` field**: Define `McpServerConfig` as a TypedDict or Pydantic model to replace `list[Any] | dict[str, Any]`. This field accepts external configuration and would benefit most from structural validation.

### Assessment

The codebase is in excellent shape regarding type safety. Production code has **zero annotation gaps**, the ty checker reports **zero errors**, and explicit `Any` usage is confined to a single module (`frontmatter_core.py`) where it is used for schema-validated Pydantic fields. The project already demonstrates best practices by defining `YamlValue` as a recursive TypeAlias in `plugin_validator.py` rather than using `Any` -- this pattern should be extended to the remaining 5 locations in `frontmatter_core.py`.
