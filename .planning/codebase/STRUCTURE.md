# Codebase Structure

**Analysis Date:** 2026-03-02

## Directory Layout

```
skilllint/
├── packages/
│   └── skilllint/              # Main package - plugin/skill validator
│       ├── plugin_validator.py # Primary CLI script (PEP 723, ~3000 lines)
│       ├── auto_sync_manifests.py # Manifest sync script (PEP 723, ~1200 lines)
│       ├── frontmatter_core.py # Shared models (importable library, ~300 lines)
│       ├── frontmatter_utils.py # YAML I/O utilities (importable library, ~150 lines)
│       └── tests/
│           ├── conftest.py     # Shared pytest fixtures
│           ├── test_cli.py     # CLI integration tests
│           ├── test_auto_sync_manifests.py # Manifest sync tests
│           ├── test_frontmatter_validator.py # Frontmatter schema tests
│           ├── test_frontmatter_utils.py # YAML I/O tests
│           ├── test_complexity_validator.py # Token counting tests
│           ├── test_description_validator.py # Description validation tests
│           ├── test_name_format_validator.py # Skill name format tests
│           ├── test_internal_link_validator.py # Internal link detection
│           ├── test_plugin_structure_validator.py # Plugin manifest validation
│           ├── test_plugin_registration_validator.py # Component registration
│           ├── test_progressive_disclosure_validator.py # Directory structure
│           ├── test_hook_validator.py # Hook validation
│           ├── test_hook_script_discovery.py # Hook script location
│           ├── test_namespace_reference_validator.py # Namespace links
│           ├── test_markdown_token_counter.py # Token counting implementation
│           ├── test_token_counting.py # Token counting integration
│           ├── test_external_tools.py # External tool integration
│           ├── test_skills_array_bugs.py # YAML array normalization
│           └── test_reporters.py # Output formatting tests
├── .planning/
│   ├── codebase/           # Analysis documents (this directory)
│   ├── todos/              # Task tracking
│   └── ...
├── docs/
│   └── plans/              # Implementation plans
└── .claude/                # Skill configuration, GSD framework
```

## Directory Purposes

**packages/skilllint/:**
- Purpose: Main plugin validator package
- Contains: PEP 723 scripts, shared library modules, test suite
- Key files: `plugin_validator.py` (entry point), `frontmatter_core.py` (schemas)

**packages/skilllint/tests/:**
- Purpose: Comprehensive test coverage for all validators and utilities
- Contains: Pytest test modules, shared fixtures (conftest.py)
- Test organization: One test module per validator class or feature area
- Coverage: CLI integration, frontmatter validation, complexity analysis, link checking, plugin structure

## Key File Locations

**Entry Points:**
- `packages/skilllint/plugin_validator.py`: CLI for validating plugins, skills, agents, commands
- `packages/skilllint/auto_sync_manifests.py`: CLI for syncing plugin.json and marketplace.json manifests

**Configuration:**
- `.claude/`: Skill configuration and GSD framework
- `packages/skilllint/plugin_validator.py` (lines 183-215): Constants for thresholds, patterns, error codes

**Core Logic:**
- `packages/skilllint/frontmatter_core.py`: Pydantic models for skill/agent/command frontmatter validation
- `packages/skilllint/frontmatter_utils.py`: YAML parsing and round-trip formatting
- `packages/skilllint/plugin_validator.py`: Validator classes, validation framework, error reporting

**Testing:**
- `packages/skilllint/tests/conftest.py`: Shared pytest fixtures for all tests
- `packages/skilllint/tests/test_*.py`: Individual test modules per feature (20+ modules)

## Naming Conventions

**Files:**
- PEP 723 Scripts: `{script_name}.py` (e.g., `plugin_validator.py`, `auto_sync_manifests.py`)
- Library Modules: `{module_name}.py` (e.g., `frontmatter_core.py`, `frontmatter_utils.py`)
- Test Files: `test_{feature}.py` (e.g., `test_cli.py`, `test_frontmatter_validator.py`)
- Directories: lowercase with underscores (`packages/skilllint/tests/`)

**Python Identifiers:**
- Classes: PascalCase (e.g., `FrontmatterValidator`, `SkillComplexityValidator`, `ValidationResult`)
- Functions: snake_case (e.g., `_safe_load_yaml()`, `_fix_unquoted_colons()`, `validate()`)
- Constants: UPPER_SNAKE_CASE (e.g., `TOKEN_WARNING_THRESHOLD`, `ERROR_CODE_BASE_URL`, `DEFAULT_SCAN_PATTERNS`)
- Error Codes: ALLCAPS (e.g., `FM001`, `SK006`, `PL005`)
- Private symbols: Leading underscore (e.g., `_VALIDATOR_PATH`, `_yaml_safe`, `_is_suppressed()`)

**Directories:**
- Pattern: lowercase with underscores or hyphens (packages/skilllint, .planning/codebase)

## Where to Add New Code

**New Validator:**
- Implementation: Create new validator class in `packages/skilllint/plugin_validator.py` (after line 1000)
  - Implement Validator protocol: `validate(path) -> ValidationResult`, `can_fix() -> bool`, `fix(path) -> list[str]`
  - Add to VALIDATORS list for registration (bottom of file)
  - Define error codes in ErrorCode enum (lines 254-321)
- Tests: Create `packages/skilllint/tests/test_{feature}_validator.py`
  - Use fixtures from `conftest.py` (cli_runner, sample_skill_dir, invalid_frontmatter_samples, etc.)
  - Test both validation and fix workflows
  - Test with sample data generated in fixtures

**New Frontmatter Model:**
- Implementation: Add Pydantic model to `packages/skilllint/frontmatter_core.py` (after line 160)
  - Extend BaseModel with ConfigDict(extra="allow")
  - Add field validators for normalization (e.g., array->CSV conversion)
  - Add one entry to _MODEL_REGISTRY dict (lines 218-222)
  - No other code changes needed (Open/Closed principle)
- Tests: Update `packages/skilllint/tests/test_frontmatter_validator.py`
  - Test model validation with valid/invalid data
  - Test field normalization edge cases

**New YAML Utility Function:**
- Location: `packages/skilllint/frontmatter_utils.py`
- Pattern: Wrapper around python-frontmatter or RuamelYAMLHandler API
- Export: Add to public API section docstring and make callable from plugin_validator.py

**CLI Command:**
- Location: `packages/skilllint/plugin_validator.py` (main() function at end of file)
- Pattern: Typer command handler decorated with @app.command()
- Implementation: Call appropriate validators and reporters, emit results

## Special Directories

**packages/skilllint/tests/:**
- Purpose: Test suite
- Generated: No
- Committed: Yes — full test suite is source

**.planning/codebase/:**
- Purpose: Architecture and structure documentation
- Generated: Yes (via /gsd:map-codebase command)
- Committed: Yes

**.claude/:**
- Purpose: Skill configuration, GSD framework integration
- Generated: Partial (user-modified, framework-generated)
- Committed: Yes (except secrets)

## Import Patterns

**PEP 723 Scripts → Library Modules:**
```python
# In plugin_validator.py (PEP 723 script)
import sys
from pathlib import Path
_SCRIPTS_DIR = str(Path(__file__).parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from frontmatter_core import SkillFrontmatter, extract_frontmatter
from frontmatter_utils import RuamelYAMLHandler
```

**Library Module Exports:**
```python
# In frontmatter_core.py (plain library)
# No PEP 723 header
# Direct imports only:
from pydantic import BaseModel, Field, field_validator

# Public API explicitly documented in module docstring
```

**Test Imports:**
```python
# In test modules
import sys
import importlib.util
from pathlib import Path

# Load PEP 723 script as module
_VALIDATOR_PATH = Path(__file__).parent.parent / "plugin_validator.py"
spec = importlib.util.spec_from_file_location("plugin_validator", _VALIDATOR_PATH)
if spec and spec.loader:
    plugin_validator = importlib.util.module_from_spec(spec)
    sys.modules["plugin_validator"] = plugin_validator
    spec.loader.exec_module(plugin_validator)
```

## Code Organization Within Files

**plugin_validator.py (~3000 lines):**
1. Shebang and PEP 723 header (lines 1-12)
2. Module docstring (lines 13-24)
3. Platform compatibility setup (lines 26-42)
4. Imports (lines 43-85)
5. Constants (lines 183-387)
6. Error code definitions (lines 250-387)
7. Utility functions (lines 389-560)
8. Data models (lines 562-689)
9. Validator protocol (lines 695-732)
10. Validator implementations (lines 800+)
11. Reporters/output formatting
12. CLI handler (main())

**frontmatter_core.py (~300 lines):**
1. Module docstring with public API (lines 1-38)
2. Constants (lines 51-70)
3. Pydantic models (lines 77-209)
4. Registry (lines 218-222)
5. Public functions (lines 230-304)

**Tests:**
- Conftest fixtures at top (lines 1-362)
- Test classes organized by feature
- Arrange-Act-Assert pattern
- Extensive use of parametrize for data-driven testing

---

*Structure analysis: 2026-03-02*
