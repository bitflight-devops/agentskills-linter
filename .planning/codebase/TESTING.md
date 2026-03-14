# Testing Patterns

**Analysis Date:** 2026-03-02

## Test Framework

**Runner:**
- pytest (configured via standard pytest discovery conventions)
- Config file: `conftest.py` in `/home/ubuntulinuxqa2/repos/skilllint/packages/skilllint/tests/`

**Assertion Library:**
- pytest's built-in assertions (`assert` statements)
- pytest.raises() for exception testing

**Run Commands:**
```bash
pytest packages/skilllint/tests/                    # Run all tests
pytest packages/skilllint/tests/ -v                 # Verbose output
pytest packages/skilllint/tests/ --cov              # With coverage (pytest-cov)
pytest packages/skilllint/tests/ -k test_name       # Run specific test
pytest -xvs packages/skilllint/tests/test_file.py   # Run single file, stop on first failure
```

## Test File Organization

**Location:**
- Tests co-located with source: `/home/ubuntulinuxqa2/repos/skilllint/packages/skilllint/tests/`
- Source in: `/home/ubuntulinuxqa2/repos/skilllint/packages/skilllint/`
- Tests import source via sys.path insertion or direct module import

**Naming:**
- Test files: `test_*.py` (e.g., `test_frontmatter_validator.py`, `test_cli.py`, `test_external_tools.py`)
- Test classes: `Test*` prefix (e.g., `TestFrontmatterValidatorBasic`, `TestTokenCounting`, `TestCLICommandParsing`)
- Test functions: `test_*` prefix with descriptive names (e.g., `test_valid_skill_frontmatter()`, `test_fix_raises_not_implemented()`)
- Fixture functions: `@pytest.fixture` decorated, lowercase with underscores (e.g., `cli_runner`, `sample_skill_dir`, `invalid_frontmatter_samples`)

**Structure:**
```
packages/skilllint/tests/
├── conftest.py                              # Shared fixtures and test configuration
├── test_frontmatter_validator.py            # Tests for FrontmatterValidator class
├── test_cli.py                              # CLI integration tests
├── test_complexity_validator.py             # Token counting and complexity tests
├── test_external_tools.py                   # Claude CLI detection, git integration
├── test_hook_validator.py                   # Hook validation tests
├── test_plugin_structure_validator.py       # Plugin.json structure validation
├── test_name_format_validator.py            # Name format/pattern validation
├── test_description_validator.py            # Description length/content validation
├── test_token_counting.py                   # Token counting algorithm tests
├── test_markdown_token_counter.py           # Markdown-specific token counting
├── test_internal_link_validator.py          # Relative link path validation
├── test_progressive_disclosure_validator.py # Content section ordering
├── test_namespace_reference_validator.py    # Namespace collision detection
├── test_plugin_registration_validator.py    # Plugin.json registration completeness
├── test_hook_script_discovery.py            # Hook script file discovery
├── test_frontmatter_utils.py                # YAML load/dump utilities
├── test_reporters.py                        # Output formatting (console, CI, summary)
├── test_skills_array_bugs.py                # Known edge cases and regressions
├── test_auto_sync_manifests.py              # Manifest synchronization tool
└── test_cli.py                              # CLI argument parsing and exit codes
```

## Test Structure

**Suite Organization:**
Test classes organize related test cases into logical groups. Each class tests one component or behavior area.

```python
class TestFrontmatterValidatorBasic:
    """Test basic FrontmatterValidator functionality."""

    def test_validator_instantiation(self) -> None:
        """Test FrontmatterValidator can be instantiated."""
        # Arrange
        # Act
        # Assert

class TestTokenCounting:
    """Test token counting functionality."""

    def test_small_skill_passes(self, tmp_path: Path) -> None:
        """Test small skill passes without warnings.

        Tests: Skill with minimal content (<4000 tokens)
        How: Create small SKILL.md, validate
        Why: Ensure skills under threshold pass validation
        """
        # Arrange
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""...""")

        # Act
        validator = ComplexityValidator()
        result = validator.validate(skill_md)

        # Assert
        assert result.passed is True
        assert len(result.errors) == 0
```

**Patterns:**

1. **AAA Pattern (Arrange-Act-Assert):** All test methods follow explicit three-part structure:
   - Arrange: Set up test data and mocks
   - Act: Call the function/method being tested
   - Assert: Verify the results

2. **Docstring Format:** Every test has a docstring describing:
   - What is being tested (single line)
   - How it's being tested
   - Why this test matters
   ```python
   def test_valid_skill_frontmatter(self, tmp_path: Path) -> None:
       """Test validation passes for valid skill frontmatter.

       Tests: Valid skill SKILL.md with minimal frontmatter
       How: Create file with description only, validate
       Why: Ensure validator accepts valid minimal skill frontmatter
       """
   ```

3. **Setup/Teardown:** Uses pytest fixtures instead of setUp/tearDown methods
   - Fixtures defined in `conftest.py` (see below)
   - Environment variables handled with context managers (see `no_color_env` fixture)

## Mocking

**Framework:** pytest-mock (`mocker` fixture)
- Provided via `MockerFixture` type hint
- Used in integration tests where external tools/processes are involved

**Patterns:**
```python
def test_is_claude_available_when_installed(mocker: MockerFixture) -> None:
    """Test is_claude_available returns True when claude CLI is in PATH."""
    # Arrange: Mock shutil.which to return a path
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")

    # Act: Check availability
    result = is_claude_available()

    # Assert: Returns True when claude found
    assert result is True
```

**Mock Targets:**
- External CLI tools: `mocker.patch("shutil.which", ...)` for Claude CLI detection
- Subprocess calls: `mocker.patch("subprocess.run", ...)` for git/process integration tests
- File system operations: Use `tmp_path` fixture instead of mocking (see below)

**What to Mock:**
- External processes (subprocess.run, shutil.which)
- Network calls (if any)
- External CLI tools (Claude CLI)
- Time/datetime (if testing time-dependent logic)

**What NOT to Mock:**
- Filesystem operations — use pytest's `tmp_path` fixture
- Internal modules — test the actual code path
- Pydantic validation — test with real data
- YAML parsing — test with actual YAML strings

## Fixtures and Factories

**Test Data:**
Fixtures in `conftest.py` provide reusable sample data and utilities:

```python
@pytest.fixture
def sample_skill_dir(tmp_path: Path) -> Path:
    """Create sample skill directory with valid SKILL.md."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
description: Use this skill when you need a test skill for validation
tools: Read, Write, Grep
model: sonnet
---

# Test Skill

This is a test skill with valid frontmatter.
""")
    return skill_dir
```

**Available Fixtures (from `/home/ubuntulinuxqa2/repos/skilllint/packages/skilllint/tests/conftest.py`):**

1. **CLI Runner:**
   - `cli_runner: CliRunner` — Returns `_PlainCliRunner` that strips ANSI escape codes from output

2. **Directory Fixtures:**
   - `sample_skill_dir(tmp_path) -> Path` — Valid SKILL.md with frontmatter
   - `sample_agent_dir(tmp_path) -> Path` — Valid agent.md with required fields
   - `sample_plugin_dir(tmp_path) -> Path` — Complete .claude-plugin/plugin.json with skills and agents

3. **Content Fixtures:**
   - `invalid_frontmatter_samples() -> dict[str, str]` — Dict of invalid frontmatter scenarios (missing delimiters, YAML arrays, multiline descriptions, etc.)
   - `broken_link_samples(tmp_path) -> dict[str, tuple[Path, str]]` — Files with broken/valid/missing-prefix links
   - `mock_frontmatter_file(tmp_path) -> Path` — Simple test file with standard frontmatter

4. **Environment Fixtures:**
   - `no_color_env() -> Generator` — Context manager setting NO_COLOR=1 during test

**Location:** `/home/ubuntulinuxqa2/repos/skilllint/packages/skilllint/tests/conftest.py`

## Coverage

**Requirements:** No explicit coverage threshold enforced in configuration

**View Coverage:**
```bash
pytest --cov=packages/skilllint packages/skilllint/tests/
pytest --cov=packages/skilllint --cov-report=html packages/skilllint/tests/
```

**Coverage areas:**
- All validator classes have unit tests (FrontmatterValidator, ComplexityValidator, etc.)
- CLI argument parsing and exit codes tested in `test_cli.py`
- Edge cases and boundary conditions (YAML parsing, token thresholds, link patterns)
- Integration tests for external tools (Claude CLI, git operations)

## Test Types

**Unit Tests:**
- Scope: Individual validator classes and functions
- Approach: Test single responsibility in isolation
- Example: `test_valid_skill_frontmatter()` tests FrontmatterValidator.validate() with valid input
- Mocks: Only external dependencies (subprocess, file I/O uses tmp_path)
- Files: `test_frontmatter_validator.py`, `test_complexity_validator.py`, `test_token_counting.py`

**Integration Tests:**
- Scope: Multiple components working together (CLI + validators, validators + YAML parsing, etc.)
- Approach: Use real fixtures and mocks only for external tools
- Example: `test_validate_with_claude_when_not_available()` tests graceful degradation when Claude CLI missing
- Mocks: External processes (shutil.which, subprocess.run)
- Files: `test_external_tools.py`, `test_cli.py`, `test_plugin_registration_validator.py`

**E2E Tests:**
- Not explicitly labeled as E2E
- CLI end-to-end: `test_cli.py` invokes full CLI with `cli_runner.invoke()` and verifies output/exit codes
- Plugin end-to-end: `test_auto_sync_manifests.py` tests complete manifest synchronization workflow

## Common Patterns

**Async Testing:**
Not used (codebase is synchronous, no async/await)

**Error Testing:**
```python
def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
    """Test fix() raises NotImplementedError."""
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("""---
description: Test skill
---

# Complex skill
""" + ("x" * 10000))

    validator = ComplexityValidator()
    with pytest.raises(NotImplementedError):
        validator.fix(skill_md)
```

**Parametrized Tests:**
Not explicitly used; instead use fixture dictionaries and loop over scenarios:
```python
@pytest.fixture
def invalid_frontmatter_samples() -> dict[str, str]:
    return {
        "missing_delimiters": "...",
        "yaml_array_tools": "...",
        ...
    }

def test_invalid_frontmatter(self, invalid_frontmatter_samples):
    for scenario, content in invalid_frontmatter_samples.items():
        # test each scenario
```

**Temporary Files:**
Use pytest's `tmp_path` fixture (PathLib Path to temp directory):
```python
def test_something(self, tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("content")
    # File auto-cleaned up after test
```

**ANSI Code Stripping:**
`_PlainCliRunner` in conftest.py strips ANSI escape codes from CLI output:
```python
class _PlainCliRunner(CliRunner):
    """CliRunner that strips ANSI escape codes from captured output."""
    def invoke(self, *args: Any, **kwargs: Any) -> Result:
        result = super().invoke(*args, **kwargs)
        result.stdout_bytes = _ANSI_ESCAPE.sub(b"", result.stdout_bytes)
        if result.stderr_bytes is not None:
            result.stderr_bytes = _ANSI_ESCAPE.sub(b"", result.stderr_bytes)
        return result
```
Reason: Rich emits ANSI codes in CI environments (FORCE_COLOR=1), making string assertions fail without stripping.

---

*Testing analysis: 2026-03-02*
