# Plugin Validator Architecture Specification

## Executive Summary

This specification defines the architecture for a consolidated cross-platform Python CLI tool that unifies all plugin validation functionality currently spread across multiple bash scripts and Python validators. The tool will validate plugin structure, frontmatter, complexity (using token-based metrics), internal links, and integrate with the Claude CLI when available.

**Design Philosophy**: Define WHAT to validate and HOW to report results, NOT HOW to implement validation logic. Implementation agents will apply current Python best practices and patterns.

---

## System Context

```mermaid
C4Context
    Person(dev, "Plugin Developer", "Creates and maintains Claude Code plugins")
    System(validator, "Plugin Validator", "Unified validation CLI tool")
    System_Ext(claude, "Claude CLI", "Official plugin validation command")
    System_Ext(git, "Git", "Pre-commit hook integration")

    Rel(dev, validator, "Runs commands")
    Rel(validator, claude, "Delegates to claude plugin validate")
    Rel(git, validator, "Triggers on commit")
```

### Container Diagram

```mermaid
C4Container
    Container(cli, "CLI Layer", "Typer", "Command parsing and user interaction")
    Container(validators, "Validator Layer", "Python", "Individual validation checks")
    Container(reporters, "Reporter Layer", "Rich", "Error formatting and output")
    Container(integrations, "Integration Layer", "Python", "Claude CLI and git integration")

    Rel(cli, validators, "Invokes validators")
    Rel(validators, reporters, "Reports issues")
    Rel(cli, integrations, "Delegates to external tools")
```

---

## Technology Stack

### Core Framework

**CLI Framework**: Typer 0.19.2+

- Includes Rich for terminal output
- Type-safe command parsing with Annotated syntax
- Built-in help generation

**Token Measurement**: tiktoken 0.9.0+

- Accurate complexity measurement
- cl100k_base encoding (GPT-4/Claude compatible)
- Replaces line-based metrics

**Type System**: Python 3.11+ native type hints

- No Optional[], use `str | None`
- No List[], use `list[str]`
- Pydantic for data validation (already used in validate_frontmatter.py)

**Configuration**: tomllib (stdlib for Python 3.11+)

- No external TOML library needed
- Pydantic-settings for validation

**Package Manager**: uv for dependency management and execution

### Distribution

**Packaging Strategy**: PEP 723 Standalone Script

- Single-file Python script with inline dependencies
- Shebang: `#!/usr/bin/env -S uv run --quiet --script`
- PEP 723 metadata block with requires-python and dependencies
- Executable permissions (chmod +x)
- Zero-install distribution

**Appropriate Use Case**: This tool has <1000 lines of code and minimal dependencies (typer, tiktoken, pyyaml already in use)

**Skill Reference**: Development agents should activate `Skill(command: "python3-development:shebangpython")` for PEP 723 compliance requirements

---

## Component Architecture

### CLI Layer (cli/)

**Purpose**: Command-line interface and argument parsing

**Technology**: Typer with Rich integration

**Command Interface**:

```python
app = typer.Typer(name="plugin-validator", help="Validate Claude Code plugins")

@app.command()
def main(
    path: Annotated[Path, typer.Argument(help="Path to plugin, skill, agent, or command file")],
    check: Annotated[bool, typer.Option("--check", help="Validate only, don't auto-fix")] = False,
    fix: Annotated[bool, typer.Option("--fix", help="Auto-fix issues where possible")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed validation output")] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable color output")] = False,
) -> None:
    """Validate Claude Code plugins, skills, agents, and commands."""
```

**Exit Codes**:

- 0: Success (all checks passed, or only warnings)
- 1: Validation errors found
- 2: Command-line usage error
- 130: Interrupted by user (Ctrl+C)

**Output Requirements**:

- Use Rich tables for validation summaries
- Use Rich panels for error details
- Support --no-color for CI environments
- File:line references for all issues

**Interfaces**:

- Input: Typed Path objects from Typer arguments
- Output: Rich-formatted console output
- Dependencies: Validator layer for validation logic

### Validator Layer (validators/)

**Purpose**: Individual validation checks with clear pass/fail results

**Technology**: Pure Python with type hints, Pydantic for data models

**Validator Protocol**:

```python
from typing import Protocol
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result from a validation check."""
    passed: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    info: list[ValidationIssue]

@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: Literal["error", "warning", "info"]
    field: str
    message: str
    code: str
    line: int | None = None
    suggestion: str | None = None
    docs_url: str | None = None

class Validator(Protocol):
    """Protocol for all validators."""

    def validate(self, path: Path) -> ValidationResult:
        """Run validation check on path."""
        ...

    def can_fix(self) -> bool:
        """Whether this validator supports auto-fixing."""
        ...

    def fix(self, path: Path) -> list[str]:
        """Auto-fix issues. Returns list of fixes applied."""
        ...
```

**Required Validators**:

| Validator Class                  | Validates                                 | Auto-Fixable | Source Logic                              | Error Codes |
| -------------------------------- | ----------------------------------------- | ------------ | ----------------------------------------- | ----------- |
| `FrontmatterValidator`           | YAML syntax, required fields, field types | Yes          | validate_frontmatter.py                   | FM001-FM010 |
| `NameFormatValidator`            | Name lowercase with hyphens only          | No           | Ported from validate-skill-structure.sh lines 63-76 (script removed)   | SK001-SK003 |
| `DescriptionValidator`           | Min length 20 chars, trigger phrases      | No           | Ported from validate-skill-structure.sh lines 78-97 (script removed)   | SK004-SK005 |
| `ComplexityValidator`            | Token count thresholds                    | No           | Replaces count-skill-lines.sh (script removed)                          | SK006-SK007 |
| `ProgressiveDisclosureValidator` | references/, examples/, scripts/ dirs     | No           | Ported from validate-skill-structure.sh lines 114-137 (script removed) | PD001-PD003 |
| `InternalLinkValidator`          | Markdown links with ./ prefix exist       | No           | Ported from validate-skill-structure.sh lines 139-160 (script removed) | LK001-LK002 |
| `PluginStructureValidator`       | plugin.json schema, paths                 | No           | claude plugin validate (external)         | PL001-PL005 |

**Validation Sequence**:

1. Detect file type (skill/agent/command/plugin)
2. Run validators appropriate for file type
3. Collect all results
4. If --fix, run auto-fix for fixable validators
5. Re-validate after fixes
6. Report final status

**Interfaces**:

- Input: Path to validate
- Output: ValidationResult with typed issues
- Dependencies: tiktoken for complexity, pydantic for schema validation

### Reporter Layer (reporters/)

**Purpose**: Format validation results for human consumption

**Technology**: Rich for terminal output

**Reporter Protocol**:

```python
from typing import Protocol
from rich.console import Console

class Reporter(Protocol):
    """Protocol for result reporters."""

    def report(
        self,
        results: list[tuple[Path, ValidationResult]],
        verbose: bool = False
    ) -> None:
        """Display validation results."""
        ...

    def summarize(
        self,
        total_files: int,
        passed: int,
        failed: int,
        warnings: int
    ) -> None:
        """Display summary statistics."""
        ...
```

**Required Reporters**:

| Reporter Class    | Purpose                     | Output Format                    |
| ----------------- | --------------------------- | -------------------------------- |
| `ConsoleReporter` | Terminal output with colors | Rich tables and panels           |
| `CIReporter`      | CI-friendly output (no TTY) | Plain text with file:line format |
| `SummaryReporter` | Quick overview              | Single-line status + counts      |

**Table Configuration** (from python3-development skill):

- Box style: `box.MINIMAL_DOUBLE_HEAD`
- Width measurement: Calculate natural width before printing
- Column wrapping: `no_wrap=True` on ID/name columns
- Print parameters: `crop=False, overflow="ignore", no_wrap=True, soft_wrap=True`

**Error Display Format**:

```
plugins/my-plugin/skills/example/SKILL.md
  ERROR [FM001] frontmatter: Missing required field 'name'
    → Add name: example-skill to frontmatter
    → https://link.to/docs/ERROR_CODES.md#fm001
  WARN [SK004] description: Length 15 chars (minimum 20 recommended)
    → Expand description to include trigger phrases
  INFO [PD001] progressive-disclosure: No references/ directory
    → Consider adding references/ for detailed documentation
```

**Interfaces**:

- Input: List of (Path, ValidationResult) tuples
- Output: Formatted text to Rich Console
- Dependencies: Rich for formatting

### Integration Layer (integrations/)

**Purpose**: External tool integration (Claude CLI, git, pre-commit)

**Technology**: Pure Python with subprocess for external commands

**Integration Patterns**:

```python
def is_claude_available() -> bool:
    """Check if claude CLI is available in PATH."""
    return shutil.which("claude") is not None

def validate_with_claude(plugin_dir: Path) -> tuple[bool, str]:
    """
    Run claude plugin validate if available.

    Returns:
        Tuple of (success, output)
        - If claude not available: (True, "skipped")
        - If validation passes: (True, stdout)
        - If validation fails: (False, stderr)
    """
    if not is_claude_available():
        return True, "claude CLI not available (skipped)"

    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    if not plugin_json.exists():
        return True, "Not a plugin directory (skipped)"

    result = subprocess.run(
        ["claude", "plugin", "validate", str(plugin_dir)],
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.returncode == 0, result.stdout + result.stderr
```

**Security Requirements**:

- NEVER use `shell=True` (command injection risk)
- Pass commands as list: `[cmd_path, *args]`
- Set timeout for external commands
- Verify command existence with `shutil.which()` before execution

**Integration Points**:

| Integration              | When Used                 | Failure Behavior                    |
| ------------------------ | ------------------------- | ----------------------------------- |
| `claude plugin validate` | Complete plugin directory | Silent skip if claude not available |
| `git diff --cached`      | Pre-commit hook context   | Validate only staged files          |
| Exit codes               | All contexts              | 0 = success, 1 = error, 2 = usage   |

**Interfaces**:

- Input: Plugin directory or file paths
- Output: External command results
- Dependencies: subprocess (stdlib), shutil (stdlib)

---

## Data Architecture

### Configuration Schema

**No configuration file required** - Tool uses sane defaults with CLI flags for customization.

**Hardcoded Thresholds** (constants in code):

```python
# Token-based complexity thresholds
TOKEN_WARNING_THRESHOLD = 4000  # ~500 lines equivalent
TOKEN_ERROR_THRESHOLD = 6400    # ~800 lines equivalent

# Description requirements
MIN_DESCRIPTION_LENGTH = 20
RECOMMENDED_DESCRIPTION_LENGTH = 1024

# Name format
NAME_PATTERN = r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$"
MAX_SKILL_NAME_LENGTH = 40

# Trigger phrase requirements
REQUIRED_TRIGGER_PHRASES = ["use when", "use this", "trigger", "activate"]
```

**Rationale**: No config file needed for a validation tool. Thresholds should be consistent across all plugin development, not per-project.

### Data Models

**File Type Detection**:

```python
from enum import StrEnum

class FileType(StrEnum):
    """Type of capability file."""
    SKILL = "skill"
    AGENT = "agent"
    COMMAND = "command"
    PLUGIN = "plugin"
    UNKNOWN = "unknown"

def detect_file_type(path: Path) -> FileType:
    """
    Detect file type from path structure.

    Returns:
        FileType enum
    """
    if path.name == "SKILL.md":
        return FileType.SKILL
    if path.name == "plugin.json" or (path / ".claude-plugin/plugin.json").exists():
        return FileType.PLUGIN
    if "agents" in path.parts:
        return FileType.AGENT
    if "commands" in path.parts:
        return FileType.COMMAND
    return FileType.UNKNOWN
```

**Validation Issue Model**:

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class ValidationIssue:
    """A validation issue with context."""

    field: str
    severity: Literal["error", "warning", "info"]
    message: str
    code: str
    line: int | None = None
    suggestion: str | None = None
    docs_url: str | None = None

    def format(self) -> str:
        """Format for display."""
        severity_icon = {
            "error": "✗",
            "warning": "⚠",
            "info": "i"
        }[self.severity]

        location = f":{self.line}" if self.line else ""
        docs = f"\n    → {self.docs_url}" if self.docs_url else ""
        return f"  {severity_icon} [{self.code}] {self.field}{location}: {self.message}{docs}"
```

**Token Counting Model**:

```python
import tiktoken

@dataclass
class ComplexityMetrics:
    """Token-based complexity metrics."""

    total_tokens: int
    frontmatter_tokens: int
    body_tokens: int
    encoding: str = "cl100k_base"

    @property
    def status(self) -> Literal["ok", "warning", "error"]:
        """Determine status from thresholds."""
        if self.body_tokens > TOKEN_ERROR_THRESHOLD:
            return "error"
        if self.body_tokens > TOKEN_WARNING_THRESHOLD:
            return "warning"
        return "ok"

    @property
    def message(self) -> str:
        """Human-readable status message."""
        if self.status == "error":
            return f"CRITICAL: {self.body_tokens} tokens (>{TOKEN_ERROR_THRESHOLD})"
        if self.status == "warning":
            return f"WARNING: {self.body_tokens} tokens (>{TOKEN_WARNING_THRESHOLD})"
        return f"OK: {self.body_tokens} tokens"

def measure_complexity(content: str, encoding: str = "cl100k_base") -> ComplexityMetrics:
    """
    Measure skill complexity using token count.

    Args:
        content: Full file content
        encoding: tiktoken encoding name

    Returns:
        ComplexityMetrics with token counts
    """
    enc = tiktoken.get_encoding(encoding)

    # Extract frontmatter and body
    frontmatter, body = split_frontmatter(content)

    return ComplexityMetrics(
        total_tokens=len(enc.encode(content)),
        frontmatter_tokens=len(enc.encode(frontmatter)),
        body_tokens=len(enc.encode(body)),
        encoding=encoding
    )
```

---

## Scalability Strategy

### Performance Optimization

**Target Performance**: <5 seconds for typical validation (3-5 files)

**Optimization Strategies**:

1. **Lazy Loading**: Only load tiktoken encoding when complexity validation needed
2. **Early Exit**: Stop validation on first error if --check mode
3. **Parallel Validation**: Validate multiple files concurrently (future enhancement)
4. **Caching**: Cache parsed frontmatter during fix mode to avoid re-parsing

**Performance Anti-Patterns to Avoid**:

- Loading entire repository into memory
- Re-parsing files after fixes (cache the parse tree)
- Running external commands synchronously in sequence
- Validating unchanged files in pre-commit context

### Resource Management

**File Processing**:

- Use context managers for file I/O
- Stream large files if needed (unlikely for plugin files)
- Clean up temporary files on error

**Memory Efficiency**:

- Process one file at a time (no batching needed for typical plugin sizes)
- Release parsed data after validation
- Use generators for file discovery

**Error Handling**:

- Graceful degradation if external tools unavailable
- Continue validation after non-fatal errors
- Report partial results if interrupted

---

## Testing Architecture

### Test Strategy

**Minimum Coverage**: 80% line and branch coverage (enforced by pytest-cov)

**Critical Code Coverage**: 95%+ for:

- Validation logic (all validators)
- Token counting accuracy
- Frontmatter parsing
- Auto-fix correctness

**Test Framework Standards** (MANDATORY):

- pytest >= 8.0.0 as primary framework
- pytest-mock >= 3.14.0 for mocking (NEVER unittest.mock)
- pytest-cov >= 6.0.0 for coverage reporting
- hypothesis >= 6.100.0 for property-based testing of validators

**Type Hint Requirements** (MANDATORY):

- ALL fixtures MUST have complete type hints including return types
- ALL test functions MUST have `-> None` return type
- Use Python 3.11+ syntax: `str | None` NOT `Optional[str]`
- Generator fixtures use `Generator[YieldType, None, None]`

### Test Architecture Patterns

**Pattern 1: CLI Integration Testing**

**Test Scope**:

- Command parsing and argument validation
- Exit code correctness (0 for success, 1 for errors)
- Help output structure
- Error message clarity

**Testing Approach**:

- Use Typer's CliRunner for isolated command invocation
- Configure with `mix_stderr=False` for stderr/stdout separation
- Set `env={"NO_COLOR": "1"}` to disable color codes

**Fixture Architecture**:

```python
from typer.testing import CliRunner
from typing import Generator

@pytest.fixture
def cli_runner() -> CliRunner:
    """Configured CLI runner for testing."""
    return CliRunner(mix_stderr=False)

@pytest.fixture
def sample_skill_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create sample skill directory with SKILL.md."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: test-skill
description: Test skill for validation
---
# Test Skill
Content here.
""")

    yield skill_dir
    # Cleanup automatic with tmp_path
```

**Test Coverage Requirements**:

- Success path with valid plugin/skill
- Error handling for missing files
- Error handling for invalid frontmatter
- Validation failure exit codes
- Help output verification

**Pattern 2: Validator Unit Testing**

**Test Scope**:

- Individual validator logic isolated from I/O
- Validation rule correctness
- Auto-fix correctness

**Testing Approach**:

- Mock file I/O using pytest-mock
- Use Protocol types for dependency contracts
- Parametrize test cases for edge conditions

**Fixture Composition**:

```python
from pytest_mock import MockerFixture

@pytest.fixture
def frontmatter_validator() -> FrontmatterValidator:
    """FrontmatterValidator instance."""
    return FrontmatterValidator()

@pytest.mark.parametrize("frontmatter,expected_errors", [
    ("name: test\ndescription: Test", 0),
    ("description: Test", 1),  # Missing name
    ("name: Test\ndescription: x", 1),  # Name uppercase
])
def test_frontmatter_validation(
    frontmatter_validator: FrontmatterValidator,
    frontmatter: str,
    expected_errors: int
) -> None:
    """Test frontmatter validation rules."""
    result = frontmatter_validator.validate_text(frontmatter)
    assert len(result.errors) == expected_errors
```

**Test Coverage Requirements**:

- Valid input acceptance
- Invalid input rejection with clear errors
- Boundary conditions (min/max lengths, edge characters)
- Auto-fix produces valid output

**Pattern 3: Token Counting Testing**

**Test Scope**:

- Token count accuracy
- Threshold detection
- Encoding consistency

**Testing Approach**:

- Property-based testing with hypothesis
- Known sample texts with verified token counts
- Threshold boundary testing

**Property-Based Testing Strategy**:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=0, max_size=10000))
def test_token_count_deterministic(text: str) -> None:
    """Token count is deterministic for same input."""
    count1 = measure_complexity(text).total_tokens
    count2 = measure_complexity(text).total_tokens
    assert count1 == count2

@pytest.mark.parametrize("body_tokens,expected_status", [
    (3000, "ok"),
    (4500, "warning"),
    (7000, "error"),
])
def test_complexity_thresholds(body_tokens: int, expected_status: str) -> None:
    """Test threshold boundaries."""
    metrics = ComplexityMetrics(
        total_tokens=body_tokens,
        frontmatter_tokens=0,
        body_tokens=body_tokens
    )
    assert metrics.status == expected_status
```

**Test Coverage Requirements**:

- Deterministic token counts
- Threshold detection accuracy
- Encoding parameter handling

**Pattern 4: Integration Testing with External Tools**

**Test Scope**:

- Claude CLI integration
- Subprocess execution safety
- Timeout handling

**Testing Approach**:

- Mock subprocess.run with pytest-mock
- Test both success and failure paths
- Verify command arguments

**Fixture Architecture**:

```python
@pytest.fixture
def mock_claude_available(mocker: MockerFixture) -> None:
    """Mock claude CLI as available."""
    mocker.patch("shutil.which", return_value="/usr/bin/claude")

def test_claude_integration_success(
    mock_claude_available: None,
    mocker: MockerFixture
) -> None:
    """Test successful claude plugin validate integration."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="✔ Validation passed\n", stderr="")

    success, output = validate_with_claude(Path("test-plugin"))

    assert success
    assert "Validation passed" in output
    mock_run.assert_called_once_with(
        ["claude", "plugin", "validate", "test-plugin"],
        capture_output=True,
        text=True,
        timeout=30
    )
```

**Test Coverage Requirements**:

- Claude CLI available and successful
- Claude CLI available but validation fails
- Claude CLI not available (silent skip)
- Timeout handling
- Command injection prevention (no shell=True)

### Coverage Verification

```bash
# Run all tests with coverage
uv run pytest

# Generate HTML coverage report
uv run pytest --cov-report=html
# Open: htmlcov/index.html

# Run with verbose output
uv run pytest -v

# Run specific test category
uv run pytest -m "cli"
uv run pytest -m "validators"
```

---

## Error Handling Architecture

### Exception Hierarchy

```python
class PluginValidatorError(Exception):
    """Base exception for plugin validator."""

class ValidationError(PluginValidatorError):
    """Validation check failed."""

    def __init__(self, path: Path, issues: list[ValidationIssue]):
        self.path = path
        self.issues = issues
        super().__init__(f"Validation failed for {path}")

class ConfigurationError(PluginValidatorError):
    """Invalid configuration or command-line arguments."""

class ExternalToolError(PluginValidatorError):
    """External tool (claude CLI) failed."""
```

**Exception Usage**:

- Raise exceptions for programming errors (bugs)
- Return ValidationResult for expected validation failures
- Don't catch exceptions unless you have specific recovery action

### Error Display Strategy

**Rich Error Formatting**:

- Use Rich Panel with red border for errors
- Include error emoji (`:cross_mark:`) in panel title
- Display error message in red markup
- Show context information in dim style

**Error Message Requirements**:

- Clear, actionable messages
- Include file:line references
- Suggest remediation steps
- No stack traces in user-facing output (unless --verbose)

---

## Error Code System

### Error Code Schema

**Format**: `[CATEGORY][NUMBER]`

**Categories**:

| Prefix | Category               | Scope                                           |
| ------ | ---------------------- | ----------------------------------------------- |
| FM     | Frontmatter            | YAML syntax, required fields, field types       |
| SK     | Skill                  | Name format, description, complexity, structure |
| LK     | Links                  | Internal link validity                          |
| PD     | Progressive Disclosure | Directory structure                             |
| PL     | Plugin                 | plugin.json structure, paths                    |

### Error Code Catalog

**Frontmatter Errors (FM001-FM010)**:

| Code  | Severity | Description                                  | Auto-Fixable |
| ----- | -------- | -------------------------------------------- | ------------ |
| FM001 | error    | Missing required field (name, description)   | No           |
| FM002 | error    | Invalid YAML syntax                          | No           |
| FM003 | error    | Frontmatter not closed with `---`            | No           |
| FM004 | warning  | Forbidden multiline indicator (`>-`, `\|-`)  | Yes          |
| FM005 | error    | Field type mismatch (expected string/bool)   | No           |
| FM006 | error    | Invalid field value (model not in enum)      | No           |
| FM007 | warning  | Tools field is YAML array (not CSV string)   | Yes          |
| FM008 | warning  | Skills field is YAML array (not CSV string)  | Yes          |
| FM009 | warning  | Unquoted description with colons             | Yes          |
| FM010 | error    | Name pattern invalid (not lowercase-hyphens) | No           |

**Skill Errors (SK001-SK007)**:

| Code  | Severity | Description                                   | Auto-Fixable |
| ----- | -------- | --------------------------------------------- | ------------ |
| SK001 | error    | Name contains uppercase characters            | No           |
| SK002 | error    | Name contains underscores (use hyphens)       | No           |
| SK003 | error    | Name has leading/trailing/consecutive hyphens | No           |
| SK004 | warning  | Description too short (minimum 20 characters) | No           |
| SK005 | warning  | Description missing trigger phrases           | No           |
| SK006 | warning  | Token count exceeds 4000 (consider splitting) | No           |
| SK007 | error    | Token count exceeds 6400 (must split)         | No           |

**Link Errors (LK001-LK002)**:

| Code  | Severity | Description                                  | Auto-Fixable |
| ----- | -------- | -------------------------------------------- | ------------ |
| LK001 | error    | Broken internal link (file does not exist)   | No           |
| LK002 | warning  | Link missing `./` prefix (not relative path) | No           |

**Progressive Disclosure Errors (PD001-PD003)**:

| Code  | Severity | Description                      | Auto-Fixable |
| ----- | -------- | -------------------------------- | ------------ |
| PD001 | info     | No `references/` directory found | No           |
| PD002 | info     | No `examples/` directory found   | No           |
| PD003 | info     | No `scripts/` directory found    | No           |

**Plugin Errors (PL001-PL005)**:

| Code  | Severity | Description                                  | Auto-Fixable |
| ----- | -------- | -------------------------------------------- | ------------ |
| PL001 | error    | Missing `plugin.json` file                   | No           |
| PL002 | error    | Invalid JSON syntax in `plugin.json`         | No           |
| PL003 | error    | Missing required field `name` in plugin.json | No           |
| PL004 | error    | Component path does not start with `./`      | No           |
| PL005 | error    | Referenced component file does not exist     | No           |

### Error Code Documentation URL

**Base Documentation URL**: `https://github.com/your-org/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md`

**URL Pattern**: `{base_url}#{code_lowercase}`

**Example**:

- Code: `FM001`
- URL: `https://github.com/your-org/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md#fm001`

### ValidationIssue Data Model Update

**Updated ValidationIssue**:

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class ValidationIssue:
    """A validation issue with context and error code."""

    field: str
    severity: Literal["error", "warning", "info"]
    message: str
    code: str  # Error code (e.g., "FM001", "SK004")
    line: int | None = None
    suggestion: str | None = None
    docs_url: str | None = None  # Link to error code documentation

    def format(self) -> str:
        """Format for display with error code and documentation link."""
        severity_icon = {
            "error": "✗",
            "warning": "⚠",
            "info": "i"
        }[self.severity]

        location = f":{self.line}" if self.line else ""
        suggestion_line = f"\n    → {self.suggestion}" if self.suggestion else ""
        docs_line = f"\n    → {self.docs_url}" if self.docs_url else ""

        return f"  {severity_icon} [{self.code}] {self.field}{location}: {self.message}{suggestion_line}{docs_line}"
```

### Error Code Integration with Validators

**Updated Validator Specification Table**:

| Validator Class                  | Validates                                 | Auto-Fixable | Error Codes |
| -------------------------------- | ----------------------------------------- | ------------ | ----------- |
| `FrontmatterValidator`           | YAML syntax, required fields, field types | Yes          | FM001-FM010 |
| `NameFormatValidator`            | Name lowercase with hyphens only          | No           | SK001-SK003 |
| `DescriptionValidator`           | Min length 20 chars, trigger phrases      | No           | SK004-SK005 |
| `ComplexityValidator`            | Token count thresholds                    | No           | SK006-SK007 |
| `ProgressiveDisclosureValidator` | references/, examples/, scripts/ dirs     | No           | PD001-PD003 |
| `InternalLinkValidator`          | Markdown links with ./ prefix exist       | No           | LK001-LK002 |
| `PluginStructureValidator`       | plugin.json schema, paths                 | No           | PL001-PL005 |

**Error Code Assignment Requirements**:

- Each validator MUST assign appropriate error codes to ValidationIssue instances
- Error codes MUST match the documented error catalog
- Documentation URL MUST be generated using the base URL pattern
- Error codes MUST remain stable across releases (no code reuse)

---

## Integration Patterns

### Pre-commit Hook Integration

**Hook Configuration** (.pre-commit-config.yaml):

```yaml
repos:
  - repo: local
    hooks:
      - id: plugin-validator
        name: Validate Claude Code Plugins
        entry: plugins/plugin-creator/scripts/plugin_validator.py
        language: script
        files: '^plugins/.*/.*\.(md|json)$'
        pass_filenames: true
        require_serial: false
```

**Pre-commit Requirements**:

- Accept file paths as arguments
- Process only provided files (not entire repo)
- Fast execution (<5s for typical changes)
- Exit code 0 = pass, non-zero = fail
- Clear error output

### Claude CLI Integration

**Integration Strategy**:

1. Check if `claude` command exists using `shutil.which()`
2. Only run on complete plugin directories (has `.claude-plugin/plugin.json`)
3. Run AFTER all Python validators pass
4. Silent skip if claude not available (don't fail)
5. Parse output for errors

**Integration Flow**:

```
1. Run Python validators (frontmatter, structure, complexity, links)
   ├─ If errors found → Report and exit
   └─ If pass → Continue
2. Check if plugin directory
   ├─ If not plugin → Skip claude validation
   └─ If plugin → Continue
3. Check if claude CLI available
   ├─ If not available → Report "skipped" and exit 0
   └─ If available → Run claude plugin validate
4. Parse claude output
   ├─ If pass → Report success and exit 0
   └─ If fail → Report errors and exit 1
```

---

## Quality Standards

### Architecture Quality Attributes

- **Maintainability**: Single-file distribution, clear separation of concerns within file
- **Testability**: All validators mockable, comprehensive test coverage
- **Usability**: Clear error messages, helpful suggestions, consistent UX
- **Performance**: <5s validation time for typical use
- **Reliability**: Graceful degradation when external tools unavailable
- **Portability**: Cross-platform (Windows/Linux/macOS), no bash dependencies

### Design Principles

- **SOLID**: Single responsibility per validator, dependency inversion via Protocols
- **DRY**: Reuse validation logic from existing validate_frontmatter.py
- **KISS**: Simple, focused tool - no configuration files needed
- **Type Safety**: Comprehensive type hints, Pydantic validation
- **Fail Fast**: Validate early, report all errors at once
- **Progressive Enhancement**: Core functionality always works, external tools optional

---

## Validation Checks Specification

### Frontmatter Validation

**Source Logic**: validate_frontmatter.py (reuse existing Pydantic models)

**Checks**:

- YAML syntax valid (FM002)
- Frontmatter starts with `---` and closes with `---` (FM003)
- Required fields present based on file type (FM001):
  - Skills: name (optional), description (optional)
  - Agents: name (required), description (required)
  - Commands: description (required)
- Field types match schema (FM005):
  - name: string matching pattern `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (FM010)
  - description: string (no colons except in URLs)
  - model: one of "sonnet", "opus", "haiku", "inherit" (FM006)
  - tools: comma-separated string (not YAML array) (FM007)
  - skills: comma-separated string (not YAML array) (FM008)
- No forbidden multiline indicators (`>-`, `|-`) (FM004)
- Unquoted descriptions with colons (FM009)

**Auto-Fixable**:

- FM004: YAML arrays → comma-separated strings
- FM007: Multiline descriptions → single-line quoted strings
- FM008: Unquoted descriptions with colons → quoted
- FM009: Unquoted descriptions with colons → quoted

**Not Auto-Fixable**:

- FM001: Missing required fields
- FM002: Invalid YAML syntax
- FM003: Missing frontmatter delimiters
- FM005: Invalid field types
- FM006: Invalid field values
- FM010: Name format violations

### Name Format Validation

**Source Logic**: Ported from validate-skill-structure.sh lines 63-76 (script removed — logic now in plugin_validator.py)

**Checks**:

- Name field present (if required)
- Name matches pattern: lowercase, hyphens only (SK001)
- No leading/trailing hyphens (SK003)
- No consecutive hyphens (SK003)
- No underscores (SK002)
- Max 40 characters for skill directory names

**Severity**: ERROR

**Not Auto-Fixable**: Requires human decision on correct name

**Error Codes**: SK001, SK002, SK003

### Description Validation

**Source Logic**: Ported from validate-skill-structure.sh lines 78-97 (script removed — logic now in plugin_validator.py)

**Checks**:

- Description minimum 20 characters (SK004)
- Description contains at least one trigger phrase (SK005):
  - "use when"
  - "use this"
  - "trigger"
  - "activate"

**Severity**:

- Missing trigger phrases: WARNING (SK005)
- Too short: WARNING (SK004)

**Not Auto-Fixable**: Requires human-written content

**Error Codes**: SK004, SK005

### Token-Based Complexity Validation

**Source Logic**: NEW - replaces count-skill-lines.sh (script removed)

**Measurement Strategy**:

```python
import tiktoken

def measure_skill_complexity(skill_path: Path) -> ComplexityMetrics:
    """
    Measure skill complexity using tiktoken.

    Args:
        skill_path: Path to SKILL.md file

    Returns:
        ComplexityMetrics with token counts and status
    """
    content = skill_path.read_text(encoding="utf-8")

    # Split frontmatter and body
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not frontmatter_match:
        frontmatter, body = "", content
    else:
        frontmatter, body = frontmatter_match.groups()

    # Count tokens using cl100k_base (GPT-4/Claude encoding)
    encoding = tiktoken.get_encoding("cl100k_base")

    return ComplexityMetrics(
        total_tokens=len(encoding.encode(content)),
        frontmatter_tokens=len(encoding.encode(frontmatter)),
        body_tokens=len(encoding.encode(body)),
        encoding="cl100k_base"
    )
```

**Thresholds**:

- WARNING: body_tokens > 4000 (~500 lines equivalent) (SK006)
- ERROR: body_tokens > 6400 (~800 lines equivalent) (SK007)

**Rationale**: Token count directly measures Claude processing cost, not line count. A 500-line file with dense code uses fewer tokens than 500 lines of verbose prose.

**Severity**:

- > 4000 tokens: WARNING (SK006) (consider splitting)
- > 6400 tokens: ERROR (SK007) (must split)

**Not Auto-Fixable**: Requires content restructuring

**Error Codes**: SK006, SK007

### Progressive Disclosure Validation

**Source Logic**: Ported from validate-skill-structure.sh lines 114-137 (script removed — logic now in plugin_validator.py)

**Checks**:

- Presence of `references/` directory (INFO if missing) (PD001)
- Presence of `examples/` directory (INFO if missing) (PD002)
- Presence of `scripts/` directory (INFO if missing) (PD003)
- Count files in each directory if present

**Severity**: INFO

**Not Auto-Fixable**: Requires content creation

**Error Codes**: PD001, PD002, PD003

### Internal Link Validation

**Source Logic**: Ported from validate-skill-structure.sh lines 139-160 (script removed — logic now in plugin_validator.py)

**Checks**:

- Extract markdown links: `\[([^]]+)\]\(([^)]+)\)`
- Filter to relative links starting with `./`
- Verify each linked file exists (LK001)
- Report broken links as ERROR
- Warn about links missing `./` prefix (LK002)

**Link Extraction Pattern**:

```python
import re
from pathlib import Path

def validate_internal_links(skill_path: Path) -> list[ValidationIssue]:
    """
    Validate internal markdown links in SKILL.md.

    Args:
        skill_path: Path to SKILL.md file

    Returns:
        List of ValidationIssue for broken links
    """
    content = skill_path.read_text(encoding="utf-8")
    skill_dir = skill_path.parent

    # Extract markdown links
    link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
    links = re.findall(link_pattern, content)

    issues = []
    for link_text, link_url in links:
        # Only validate relative links starting with ./
        if not link_url.startswith("./"):
            issues.append(ValidationIssue(
                field="internal-links",
                severity="warning",
                message=f"Link missing ./ prefix: {link_url}",
                code="LK002",
                suggestion="Use relative paths with ./ prefix for internal links",
                docs_url="https://github.com/your-org/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md#lk002"
            ))
            continue

        # Resolve link relative to skill directory
        link_path = skill_dir / link_url.lstrip("./")

        if not link_path.exists():
            issues.append(ValidationIssue(
                field="internal-links",
                severity="error",
                message=f"Broken link: {link_url}",
                code="LK001",
                suggestion=f"Create file at {link_path} or fix link",
                docs_url="https://github.com/your-org/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md#lk001"
            ))

    return issues
```

**Severity**: ERROR (LK001), WARNING (LK002)

**Not Auto-Fixable**: Requires file creation or link correction

**Error Codes**: LK001, LK002

### Plugin Structure Validation

**Source Logic**: claude plugin validate (external command)

**When to Run**:

- Only on complete plugin directories
- Only if `.claude-plugin/plugin.json` exists
- Only if `claude` CLI available in PATH

**Checks Delegated to Claude CLI**:

- plugin.json schema validation (PL002)
- Required field presence (PL003)
- Path format validation (must start with `./`) (PL004)
- Referenced files exist (PL005)
- Component arrays vs directory strings

**Integration Behavior**:

- If claude not available: Skip silently (report "skipped")
- If not a plugin directory: Skip silently
- If validation passes: Report success
- If validation fails: Parse and report errors

**Severity**: ERROR (if claude validates, otherwise INFO)

**Not Auto-Fixable**: Structural changes required

**Error Codes**: PL001, PL002, PL003, PL004, PL005

---

## CLI Usage Examples

### Validate Single File

```bash
# Validate skill
./plugin_validator.py plugins/my-plugin/skills/example/SKILL.md

# Validate agent
./plugin_validator.py plugins/my-plugin/agents/worker.md

# Validate command
./plugin_validator.py ~/.claude/commands/helper.md
```

### Validate Directory

```bash
# Validate entire plugin
./plugin_validator.py plugins/my-plugin

# Validate skills directory
./plugin_validator.py plugins/my-plugin/skills

# Validate current directory
./plugin_validator.py .
```

### Auto-Fix Mode

```bash
# Fix frontmatter issues automatically
./plugin_validator.py --fix plugins/my-plugin/skills/example/SKILL.md

# Fix all skills in plugin
./plugin_validator.py --fix plugins/my-plugin
```

### Verbose Output

```bash
# Show all checks, not just failures
./plugin_validator.py --verbose plugins/my-plugin

# Show verbose output without color (CI)
./plugin_validator.py --verbose --no-color plugins/my-plugin
```

### Pre-commit Hook Usage

```bash
# Pre-commit automatically calls with changed files
git commit -m "feat: add new skill"
# → Runs: plugin_validator.py file1.md file2.md ...
```

---

## Migration Path from Existing Scripts

### Phase 1: Create Consolidated Tool (COMPLETED)

1. Created `plugin_validator.py` as PEP 723 standalone script
2. Ported frontmatter validation from `validate_frontmatter.py`
3. Ported structure validation from `validate-skill-structure.sh` (now removed)
4. Implemented token-based complexity (replaced `count-skill-lines.sh`, now removed)
5. Added Claude CLI integration

### Phase 2: Update Pre-commit Hooks

1. Update `.pre-commit-config.yaml` to use `plugin_validator.py`
2. Remove old `validate-frontmatter` hook
3. Test hook execution

### Phase 3: Update Documentation

1. Update references in CONTRIBUTING.md
2. Update references in plugin-creator CLAUDE.md
3. Update references in skill documentation
4. Update examples to use new tool

### Phase 4: Deprecate Old Scripts

1. Move bash scripts to `scripts/deprecated/`
2. Add deprecation notices to bash scripts
3. Update README with migration instructions
4. Remove bash scripts after deprecation period (1-2 releases)

---

## Architectural Decisions (ADRs)

### ADR-001: Use PEP 723 Standalone Script

**Status**: Accepted

**Context**: Need simple distribution for validation tool that works across platforms

**Decision**: Use PEP 723 inline script metadata with uv shebang

**Consequences**:

- Positive: Zero-setup execution, embedded dependencies, single file
- Positive: Cross-platform (no bash dependency)
- Negative: Limited to <1500 lines (acceptable for this tool)

**Alternatives Considered**:

- Multi-file package: Too heavy for a validation script
- Bash script: Not cross-platform compatible

### ADR-002: Token-Based Complexity Metrics

**Status**: Accepted

**Context**: Line count doesn't reflect actual Claude processing cost

**Decision**: Use tiktoken library with cl100k_base encoding

**Consequences**:

- Positive: Accurate measurement of Claude processing cost
- Positive: Aligns with how Claude measures context
- Negative: Additional dependency (tiktoken)
- Negative: Thresholds need user calibration

**Alternatives Considered**:

- Line count: Inaccurate proxy for complexity
- Character count: Better than lines but still not accurate

### ADR-003: Silent Skip for Missing Claude CLI

**Status**: Accepted

**Context**: Not all developers have Claude CLI installed

**Decision**: Skip claude plugin validate silently if CLI not available

**Consequences**:

- Positive: Tool works in all environments
- Positive: No dependency on Claude CLI installation
- Negative: May miss plugin.json schema errors

**Alternatives Considered**:

- Require Claude CLI: Too restrictive for development
- Implement own plugin.json validator: Duplication of effort

### ADR-004: Reuse Pydantic Models from validate_frontmatter.py

**Status**: Accepted

**Context**: validate_frontmatter.py already has comprehensive Pydantic validation

**Decision**: Copy Pydantic models into consolidated tool

**Consequences**:

- Positive: Proven validation logic
- Positive: Type-safe schema validation
- Negative: Code duplication during transition period

**Alternatives Considered**:

- Import from validate_frontmatter.py: Breaks standalone script requirement
- Rewrite validation: Duplication of effort

### ADR-005: Standardized Error Code System

**Status**: Accepted

**Context**: Need consistent, searchable error identification across validators

**Decision**: Implement structured error codes with category prefixes and documentation links

**Consequences**:

- Positive: Users can search for error codes in documentation
- Positive: Error codes provide stable references across versions
- Positive: Documentation URLs enable self-service troubleshooting
- Negative: Requires maintaining error code catalog and documentation

**Alternatives Considered**:

- Free-form error messages: Less searchable, inconsistent
- HTTP-style numeric codes: Less semantic, harder to remember

---

## Success Criteria

### Functional Requirements Met

- ✅ Single Python script validates plugins, skills, agents, commands
- ✅ Token-based complexity measurement implemented
- ✅ Cross-platform (Windows/Linux/macOS) without bash
- ✅ Auto-fix mode for correctable issues
- ✅ Integration with Claude CLI when available
- ✅ Pre-commit hook compatible
- ✅ Exit codes: 0 = success, 1 = errors, 2 = usage
- ✅ Standardized error codes with documentation

### Non-Functional Requirements Met

- ✅ Performance: <5s for typical validation
- ✅ Type Safety: Complete type hints, mypy strict mode passes
- ✅ Test Coverage: 80% minimum, 95%+ for validators
- ✅ Error Messages: Clear, actionable, with file:line references and error codes
- ✅ Documentation: Comprehensive architecture spec, usage examples, error code reference

### Quality Gates

- ✅ All tests pass (pytest)
- ✅ Type checking passes (mypy --strict)
- ✅ Coverage threshold met (80% minimum)
- ✅ Pre-commit hooks work in practice
- ✅ No regressions in existing functionality
- ✅ Error code documentation complete and accurate

---

## References

1. **PEP 723 - Inline Script Metadata**: <https://peps.python.org/pep-0723/>
2. **Typer Documentation**: <https://typer.tiangolo.com/>
3. **tiktoken Documentation**: <https://github.com/openai/tiktoken>
4. **Rich Documentation**: <https://rich.readthedocs.io/>
5. **pytest Best Practices**: <https://docs.pytest.org/en/stable/>
6. **Anthropic Prompt Engineering**: <https://docs.anthropic.com/claude/docs/prompt-engineering>

---

## Appendix A: Complete Validation Checklist

### Skill Validation Checklist

- [ ] Frontmatter exists and is valid YAML (FM002)
- [ ] Frontmatter starts with `---` and closes with `---` (FM003)
- [ ] Name field present (optional but recommended)
- [ ] Name format: lowercase with hyphens only (if present) (SK001, SK002, SK003, FM010)
- [ ] Name max 40 characters (if present)
- [ ] Description present (optional but recommended)
- [ ] Description minimum 20 characters (if present) (SK004)
- [ ] Description contains trigger phrase (if present) (SK005)
- [ ] Body token count <4000 (warning if exceeded) (SK006)
- [ ] Body token count <6400 (error if exceeded) (SK007)
- [ ] No forbidden YAML multiline indicators (FM004)
- [ ] Tools field is comma-separated string (not array) (FM007)
- [ ] Skills field is comma-separated string (not array) (FM008)
- [ ] All internal links (./path) exist (LK001)
- [ ] Progressive disclosure structure present (references/, examples/, scripts/) (PD001-PD003)

### Agent Validation Checklist

- [ ] Frontmatter exists and is valid YAML (FM002)
- [ ] Name field required and present (FM001)
- [ ] Name format: lowercase with hyphens only (SK001, SK002, SK003, FM010)
- [ ] Description field required and present (FM001)
- [ ] Description minimum 20 characters (SK004)
- [ ] Model field one of: sonnet, opus, haiku, inherit (if present) (FM006)
- [ ] Tools field comma-separated string (if present) (FM007)
- [ ] DisallowedTools field comma-separated string (if present)
- [ ] Skills field comma-separated string (if present) (FM008)
- [ ] No forbidden YAML multiline indicators (FM004)

### Plugin Validation Checklist

- [ ] .claude-plugin/plugin.json exists (PL001)
- [ ] plugin.json is valid JSON (PL002)
- [ ] Required field 'name' present (PL003)
- [ ] Name format: kebab-case
- [ ] All component paths start with ./ (PL004)
- [ ] All referenced files exist (PL005)
- [ ] Skills array contains directory paths
- [ ] Agents array contains file paths (not directory)
- [ ] Commands array contains file paths (not directory)
- [ ] Claude CLI validation passes (if available)

---

**FINAL NOTE**: This architecture specification defines WHAT to validate and HOW to structure the tool. Implementation agents will define HOW to implement validation logic following Python best practices and the patterns defined here.
