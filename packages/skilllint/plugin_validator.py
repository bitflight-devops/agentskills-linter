"""Plugin validator for Claude Code plugins.

Validates:
- Frontmatter schema (skills, agents, commands)
- Plugin structure (plugin.json)
- Skill complexity (token-based)
- Internal links
- Progressive disclosure structure
- Plugin completeness

Token-based complexity measurement replaces line counting for accurate AI cost estimation.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from io import TextIOWrapper

# Ensure UTF-8 output on Windows (cp1252 default cannot encode emoji/spinner chars).
# reconfigure() is available on Python 3.7+ when stdout is a TextIOWrapper.
if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if isinstance(sys.stderr, TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dataclasses import dataclass
from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Annotated,
    ClassVar,
    Literal,
    NoReturn,
    Protocol,
    TypeAlias,
    cast,
)

# YAML/JSON at the edge: dict, list, or JSON-serializable scalars. More specific than Any.
YamlValue: TypeAlias = (
    dict[str, "YamlValue"] | list["YamlValue"] | str | int | float | bool | None
)

import contextlib

import tiktoken
import typer
from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError
from git.index.fun import entry_key
from pydantic import ValidationError
from rich.console import Console, ConsoleRenderable, RichCast
from rich.measure import Measurement
from rich.panel import Panel
from ruamel.yaml import YAML, YAMLError
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from .frontmatter_core import (
    MAX_SKILL_NAME_LENGTH,
    RECOMMENDED_DESCRIPTION_LENGTH,
    AgentFrontmatter,
    CommandFrontmatter,
    SkillFrontmatter,
    extract_frontmatter,
    fix_skill_name_field,
    get_frontmatter_model,
)
from .frontmatter_utils import RuamelYAMLHandler

if TYPE_CHECKING:
    from pydantic_core import ErrorDetails

# Module-level ruamel.yaml safe-mode instance (replaces yaml.safe_load)
_yaml_safe = YAML(typ="safe")

# Round-trip YAML instance (via shared handler) for dumping with format preservation
_rt_handler = RuamelYAMLHandler()
_rt_yaml = _rt_handler.yaml
_rt_yaml.width = 10000  # prevent line wrapping


def _safe_load_yaml(text: str) -> YamlValue:
    """Parse a YAML string using ruamel.yaml safe loader.

    Args:
        text: YAML text to parse (frontmatter content, no --- delimiters).

    Returns:
        Parsed YAML data (dict, list, scalar, or None).

    Raises:
        YAMLError: If the YAML is syntactically invalid.
    """
    if not text or not text.strip():
        return {}
    return _yaml_safe.load(text)


def _dump_yaml(data: dict[str, YamlValue]) -> str:
    """Serialize a dict to YAML using the round-trip handler.

    Preserves key insertion order. Values containing ': ' are wrapped in
    double quotes so YAML parsers handle them correctly.

    Args:
        data: Dictionary to serialize.

    Returns:
        YAML string (may include trailing newline).
    """
    prepared: dict[str, YamlValue] = {}
    for key, value in data.items():
        if isinstance(value, str) and ": " in value:
            prepared[key] = DoubleQuotedScalarString(value)
        else:
            prepared[key] = value

    buf = StringIO()
    _rt_yaml.dump(prepared, buf)
    return buf.getvalue()


def _fix_unquoted_colons(frontmatter_text: str) -> tuple[str, list[str], list[str]]:
    """Quote description (and similar string) values that contain unquoted colons.

    Detects lines of the form ``key: value: more`` where the unquoted colon
    causes a YAML parse error and wraps the value in double-quotes.

    Args:
        frontmatter_text: Raw YAML frontmatter (without ``---`` delimiters).

    Returns:
        Tuple of (possibly-fixed frontmatter text, list of fix descriptions,
        list of field names that were fixed).  The field names list has one entry
        per fixed line and is used by callers to emit FM009 info issues.
    """
    fixes: list[str] = []
    fixed_fields: list[str] = []
    lines = frontmatter_text.splitlines(keepends=True)
    new_lines = []

    # Regex: key: value where value contains an unquoted colon
    # Only matches simple single-line scalar values, not block scalars or already-quoted values
    unquoted_colon_re = re.compile(r'^(\s*([\w-]+):\s+)([^\'"\[\{|>].+:.*)$')

    for line in lines:
        m = unquoted_colon_re.match(line.rstrip("\n"))
        if m:
            prefix = m.group(1)
            field_name = m.group(2)
            value = m.group(3)
            # Escape any existing double-quotes inside the value
            escaped = value.replace('"', '\\"')
            new_line = f'{prefix}"{escaped}"\n'
            fixes.append("Quoted description value containing unquoted colon")
            fixed_fields.append(field_name)
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    if fixes:
        return "".join(new_lines), fixes, fixed_fields
    return frontmatter_text, [], []


# Error code base URL for documentation links
ERROR_CODE_BASE_URL = "https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md"

# Official plugin.json schema (plugin manifest)
PLUGIN_MANIFEST_SCHEMA_URL = (
    "https://code.claude.com/docs/en/plugins-reference.md#plugin-manifest-schema"
)
SKILL_FRONTMATTER_SCHEMA_URL = (
    "https://code.claude.com/docs/en/skills.md#frontmatter-reference"
)

# Token-based complexity thresholds (body content, frontmatter excluded)
TOKEN_WARNING_THRESHOLD = 4400
TOKEN_ERROR_THRESHOLD = 8800

# Convenience glob patterns for --filter-type option
FILTER_TYPE_MAP: dict[str, str] = {
    "skills": "**/skills/*/SKILL.md",
    "agents": "**/agents/*.md",
    "commands": "**/commands/*.md",
}

# Default patterns for auto-discovering validatable files in bare directories
DEFAULT_SCAN_PATTERNS: tuple[str, ...] = (
    "**/skills/*/SKILL.md",
    "**/agents/*.md",
    "**/commands/*.md",
    "**/.claude-plugin/plugin.json",
    "**/hooks/hooks.json",
    "**/CLAUDE.md",
)

# Description requirements (Architecture lines 349-350)
MIN_DESCRIPTION_LENGTH = 20
# RECOMMENDED_DESCRIPTION_LENGTH and MAX_SKILL_NAME_LENGTH imported from frontmatter_core

# Name format — matches agentskills.io/specification and init_skill.py convention:
# lowercase a-z/0-9/hyphen, no leading/trailing/consecutive hyphens.
NAME_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"


def _normalize_skill_name(name: str) -> str:
    """Normalize name to schema format: lowercase, hyphens only, no leading/trailing/consecutive hyphens.

    Returns:
        Normalized name string.
    """
    s = name.lower().replace("_", "-")
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


# Trigger phrase requirements (Architecture line 357)
REQUIRED_TRIGGER_PHRASES = [
    "use when",
    "use this",
    "use on",
    "used when",
    "used by",
    "when ",
    "trigger",
    "activate",
    "load this",
    "load when",
    "invoke",
]

# ============================================================================
# ERROR CODE CONSTANTS (Architecture lines 836-887)
# ============================================================================


class ErrorCode(StrEnum):
    """Validation error codes. Use as type hint for code parameters."""

    # Frontmatter (FM001-FM010)
    FM001 = "FM001"  # Missing required field (name, description)
    FM002 = "FM002"  # Invalid YAML syntax
    FM003 = "FM003"  # Frontmatter not closed with `---`
    FM004 = "FM004"  # Forbidden multiline indicator (`>-`, `|-`)
    FM005 = "FM005"  # Field type mismatch (expected string/bool)
    FM006 = "FM006"  # Invalid field value (model not in enum)
    FM007 = "FM007"  # Tools field is YAML array (not CSV string)
    FM008 = "FM008"  # Skills field is YAML array (not CSV string)
    FM009 = "FM009"  # Unquoted description with colons
    FM010 = "FM010"  # Name pattern invalid (not lowercase-hyphens)

    # Skill (SK001-SK008)
    SK001 = "SK001"  # Name contains uppercase characters
    SK002 = "SK002"  # Name contains underscores (use hyphens)
    SK003 = "SK003"  # Name has leading/trailing/consecutive hyphens
    SK004 = "SK004"  # Description too short (minimum 20 characters)
    SK005 = "SK005"  # Description missing trigger phrases
    SK006 = "SK006"  # Token count exceeds TOKEN_WARNING_THRESHOLD
    SK007 = "SK007"  # Token count exceeds TOKEN_ERROR_THRESHOLD (must split)
    SK008 = "SK008"  # Skill directory name violates naming convention
    SK009 = "SK009"  # Plugin uses manual skill selection (overrides auto-discovery)

    # Link (LK001-LK002)
    LK001 = "LK001"  # Broken internal link (file does not exist)
    LK002 = "LK002"  # Link missing ./ prefix

    # Progressive Disclosure (PD001-PD003)
    PD001 = "PD001"  # No `references/` directory found
    PD002 = "PD002"  # No `examples/` directory found
    PD003 = "PD003"  # No `scripts/` directory found

    # Plugin (PL001-PL005)
    PL001 = "PL001"  # Missing `plugin.json` file
    PL002 = "PL002"  # Invalid JSON syntax in `plugin.json`
    PL003 = "PL003"  # Missing required field `name` in plugin.json
    PL004 = "PL004"  # Component path does not start with `./`
    PL005 = "PL005"  # Referenced component file does not exist

    # Command (CM001)
    CM001 = "CM001"  # Command-specific validation (reserved)

    # Hook (HK001-HK005)
    HK001 = "HK001"  # Invalid hooks.json structure
    HK002 = "HK002"  # Invalid event type in hooks.json
    HK003 = "HK003"  # Invalid hook entry structure
    HK004 = "HK004"  # Hook script referenced but not found
    HK005 = "HK005"  # Hook script exists but is not executable

    # Namespace Reference (NR001-NR002)
    NR001 = "NR001"  # Namespace reference target does not exist
    NR002 = "NR002"  # Namespace reference points outside plugin directory

    # Symlink (SL001)
    SL001 = "SL001"  # Symlink target has trailing whitespace/newlines

    # Token Count (TC001)
    TC001 = "TC001"  # Token count info (total, frontmatter, body)

    # Plugin Registration (PR001-PR005)
    PR001 = "PR001"  # Capability exists but not explicitly registered in plugin.json
    PR002 = "PR002"  # Registered capability path does not exist
    PR003 = (
        "PR003"  # Plugin metadata fields (repository, homepage, author) not populated
    )
    PR004 = "PR004"  # Plugin metadata repository URL mismatches git remote URL
    PR005 = "PR005"  # Registered command path is a skill directory (contains SKILL.md)


# Aliases for backward compatibility and concise usage
FM001, FM002, FM003, FM004, FM005, FM006, FM007, FM008, FM009, FM010 = (
    ErrorCode.FM001,
    ErrorCode.FM002,
    ErrorCode.FM003,
    ErrorCode.FM004,
    ErrorCode.FM005,
    ErrorCode.FM006,
    ErrorCode.FM007,
    ErrorCode.FM008,
    ErrorCode.FM009,
    ErrorCode.FM010,
)
SK001, SK002, SK003, SK004, SK005, SK006, SK007, SK008, SK009 = (
    ErrorCode.SK001,
    ErrorCode.SK002,
    ErrorCode.SK003,
    ErrorCode.SK004,
    ErrorCode.SK005,
    ErrorCode.SK006,
    ErrorCode.SK007,
    ErrorCode.SK008,
    ErrorCode.SK009,
)
LK001, LK002 = ErrorCode.LK001, ErrorCode.LK002
PD001, PD002, PD003 = ErrorCode.PD001, ErrorCode.PD002, ErrorCode.PD003
PL001, PL002, PL003, PL004, PL005 = (
    ErrorCode.PL001,
    ErrorCode.PL002,
    ErrorCode.PL003,
    ErrorCode.PL004,
    ErrorCode.PL005,
)
CM001 = ErrorCode.CM001
HK001, HK002, HK003, HK004, HK005 = (
    ErrorCode.HK001,
    ErrorCode.HK002,
    ErrorCode.HK003,
    ErrorCode.HK004,
    ErrorCode.HK005,
)
NR001, NR002 = ErrorCode.NR001, ErrorCode.NR002
SL001 = ErrorCode.SL001
PR001, PR002, PR003, PR004, PR005 = (
    ErrorCode.PR001,
    ErrorCode.PR002,
    ErrorCode.PR003,
    ErrorCode.PR004,
    ErrorCode.PR005,
)

# Claude CLI timeout
CLAUDE_TIMEOUT = 3  # seconds
GIT_MODE_EXECUTABLE = 0o100755  # Git mode for executable files (100755)

# Filenames exempt from frontmatter requirement (case-sensitive)
FRONTMATTER_EXEMPT_FILENAMES: frozenset[str] = frozenset(
    {
        "AGENT.md",
        "AGENTS.md",
        "GEMINI.md",
        "CLAUDE.md",
        "README.md",
    }
)


def _git_bash_path() -> str | None:
    """Resolve path to bash.exe for CLAUDE_CODE_GIT_BASH_PATH.

    Claude Code on Windows requires git-bash. Tries:
    1. shutil.which("git-bash") — if found, use sibling bin/bash.exe
    2. On Windows: LOCALAPPDATA/Programs/Git — check git-bash.exe exists, use bin/bash.exe

    If resolved, sets os.environ["CLAUDE_CODE_GIT_BASH_PATH"] and returns the path.

    Returns:
        Resolved path to bash.exe, or None if not found
    """
    # Already set
    existing = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH", "").strip()
    if existing and Path(existing).is_file():
        return existing

    # Try PATH for git-bash only (not generic bash — claude requires Git Bash)
    found = shutil.which("git-bash")
    if found:
        path = Path(found).resolve()
        if path.is_file() and path.name.lower() == "git-bash.exe":
            bash_exe = path.parent / "bin" / "bash.exe"
            if bash_exe.is_file():
                resolved = str(bash_exe.resolve())
                os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = resolved
                return resolved
            # Shims may point elsewhere; if path is git-bash.exe, try parent/bin
            # Already tried above; fall through to Windows fallback if no bin/bash

    # Windows fallback: AppData\Local\Programs\Git\git-bash.exe
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA", "").strip()
        if localappdata:
            base = Path(localappdata) / "Programs" / "Git"
            git_bash_exe = base / "git-bash.exe"
            if git_bash_exe.is_file():
                bash_exe = base / "bin" / "bash.exe"
                if bash_exe.is_file():
                    resolved = str(bash_exe.resolve())
                    os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = resolved
                    return resolved

    return None


def _should_skip_claude_validate() -> bool:
    """Detect if running in a context where claude CLI validation should be skipped.

    Skips validation when either:
    - CLAUDE_CODE_REMOTE=true (cloud-hosted Claude Code sessions)
    - CLAUDECODE is set (nested Claude Code session detected by Anthropic)

    Returns:
        True if claude plugin validate should be skipped, False otherwise
    """
    # Check for remote cloud session
    if os.environ.get("CLAUDE_CODE_REMOTE", "").lower() == "true":
        return True

    # Check for nested Claude Code session (CLAUDECODE env var set by Anthropic)
    return bool(os.environ.get("CLAUDECODE"))


# ============================================================================
# IGNORE CONFIG (per-plugin .claude-plugin/validator.json)
# ============================================================================

# Type alias: maps relative path prefix → set of suppressed error codes.
IgnoreConfig: TypeAlias = dict[str, list[str]]


def _load_ignore_config(plugin_root: Path) -> IgnoreConfig:
    """Load per-plugin validator ignore config from .claude-plugin/validator.json.

    Args:
        plugin_root: Directory containing .claude-plugin/plugin.json.

    Returns:
        Mapping of relative path prefixes to lists of suppressed error codes.
        Returns empty dict if config file does not exist or cannot be parsed.
    """
    config_path = plugin_root / ".claude-plugin" / "validator.json"
    if not config_path.is_file():
        return {}
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    ignore = raw.get("ignore", {})
    if not isinstance(ignore, dict):
        return {}
    return {
        str(k): [str(c) for c in v] for k, v in ignore.items() if isinstance(v, list)
    }


def _find_plugin_root(path: Path) -> Path | None:
    """Walk up from path to find the nearest plugin root (directory with .claude-plugin/plugin.json).

    Args:
        path: File or directory path to start from.

    Returns:
        Plugin root directory, or None if not found.
    """
    candidate = path if path.is_dir() else path.parent
    for directory in [candidate, *candidate.parents]:
        if (directory / ".claude-plugin" / "plugin.json").exists():
            return directory
    return None


def _is_suppressed(
    ignore_config: IgnoreConfig, file_path: Path, plugin_root: Path, code: str
) -> bool:
    """Check whether an issue code is suppressed for a given file path.

    Matching is by prefix: a key of "skills/python3-development" suppresses the
    code for any file whose path relative to the plugin root starts with that prefix.

    Args:
        ignore_config: Loaded ignore config mapping prefixes to suppressed codes.
        file_path: Absolute path to the file being validated.
        plugin_root: Plugin root directory (used to compute relative path).
        code: Error code string (e.g. "SK006") to check.

    Returns:
        True if this code is suppressed for file_path, False otherwise.
    """
    if not ignore_config:
        return False
    try:
        rel = file_path.relative_to(plugin_root)
    except ValueError:
        return False
    rel_str = rel.as_posix()
    for prefix, codes in ignore_config.items():
        if (
            rel_str == prefix or rel_str.startswith(prefix.rstrip("/") + "/")
        ) and code in codes:
            return True
    return False


def _filter_result_by_ignore(
    result: ValidationResult,
    file_path: Path,
    plugin_root: Path,
    ignore_config: IgnoreConfig,
) -> ValidationResult:
    """Return a new ValidationResult with suppressed issues removed.

    Suppressed issues are dropped entirely (not downgraded to info).
    The passed flag is recomputed from the remaining errors.

    Args:
        result: Original validation result.
        file_path: Path to the file that was validated.
        plugin_root: Plugin root used for relative-path prefix matching.
        ignore_config: Loaded ignore config.

    Returns:
        Filtered ValidationResult (same object if nothing was suppressed).
    """
    if not ignore_config:
        return result

    def keep(issue: ValidationIssue) -> bool:
        return not _is_suppressed(
            ignore_config, file_path, plugin_root, str(issue.code)
        )

    errors = [i for i in result.errors if keep(i)]
    warnings = [i for i in result.warnings if keep(i)]
    info = [i for i in result.info if keep(i)]

    if errors is result.errors and warnings is result.warnings and info is result.info:
        return result

    return ValidationResult(
        passed=len(errors) == 0, errors=errors, warnings=warnings, info=info
    )


# ============================================================================
# DATA MODELS (Architecture lines 136-480)
# ============================================================================


class FileType(StrEnum):
    """Type of capability file (Architecture lines 369-392)."""

    SKILL = "skill"
    AGENT = "agent"
    COMMAND = "command"
    PLUGIN = "plugin"
    HOOK_CONFIG = "hook_config"
    HOOK_SCRIPT = "hook_script"
    CLAUDE_MD = "claude_md"
    REFERENCE = "reference"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"

    @staticmethod
    def detect_file_type(path: Path) -> FileType:
        """Detect file type from path structure.

        Args:
            path: Path to file or directory to classify

        Returns:
            FileType enum value based on path structure
        """
        if path.name == "SKILL.md":
            result = FileType.SKILL
        elif (
            path.name == "plugin.json" or (path / ".claude-plugin/plugin.json").exists()
        ):
            result = FileType.PLUGIN
        elif "agents" in path.parts:
            result = FileType.AGENT
        elif "commands" in path.parts:
            result = FileType.COMMAND
        elif path.name == "hooks.json":
            result = FileType.HOOK_CONFIG
        elif "hooks" in path.parts and path.suffix in {".js", ".cjs"}:
            result = FileType.HOOK_SCRIPT
        elif path.name == "CLAUDE.md":
            result = FileType.CLAUDE_MD
        elif "references" in path.parts and path.suffix == ".md":
            result = FileType.REFERENCE
        elif path.suffix == ".md":
            result = FileType.MARKDOWN
        else:
            result = FileType.UNKNOWN
        return result


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation issue (Architecture lines 152-160, 395-423)."""

    field: str
    severity: Literal["error", "warning", "info"]
    message: str
    code: ErrorCode
    line: int | None = None
    suggestion: str | None = None
    docs_url: str | None = None

    def format(self) -> str:
        """Format issue for display.

        Returns:
            Formatted string with severity icon, code, field, message, and optional docs URL
        """
        severity_icon = {
            "error": ":cross_mark:",
            "warning": ":warning:",
            "info": ":information:",
        }[self.severity]

        location = f":{self.line}" if self.line else ""
        suggestion_line = f"\n    → {self.suggestion}" if self.suggestion else ""
        docs = f"\n    → {self.docs_url}" if self.docs_url else ""
        return f"  {severity_icon} [{self.code}] {self.field}{location}: {self.message}{suggestion_line}{docs}"


@dataclass(frozen=True)
class ValidationResult:
    """Result from a validation check (Architecture lines 143-149)."""

    passed: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    info: list[ValidationIssue]


# Type alias: maps each unique file path to a list of (validator_name, result) pairs.
# This groups validator results by file so reports count unique files, not validator
# invocations.
FileResults = dict[Path, list[tuple[str, ValidationResult]]]


@dataclass(frozen=True)
class ComplexityMetrics:
    """Token-based complexity metrics (Architecture lines 431-479)."""

    total_tokens: int
    frontmatter_tokens: int
    body_tokens: int
    encoding: str = "cl100k_base"

    @property
    def status(self) -> Literal["ok", "warning", "error"]:
        """Determine status from thresholds.

        Returns:
            Status based on TOKEN_WARNING_THRESHOLD and TOKEN_ERROR_THRESHOLD
        """
        if self.body_tokens > TOKEN_ERROR_THRESHOLD:
            return "error"
        if self.body_tokens > TOKEN_WARNING_THRESHOLD:
            return "warning"
        return "ok"

    @property
    def message(self) -> str:
        """Human-readable status message.

        Returns:
            Status message with token count and threshold
        """
        if self.status == "error":
            return f"CRITICAL: {self.body_tokens} tokens (>{TOKEN_ERROR_THRESHOLD})"
        if self.status == "warning":
            return f"WARNING: {self.body_tokens} tokens (>{TOKEN_WARNING_THRESHOLD})"
        return f"OK: {self.body_tokens} tokens"


# ============================================================================
# VALIDATOR PROTOCOL (Architecture lines 162-176)
# ============================================================================


class Validator(Protocol):
    """Protocol for all validators.

    Defines the interface that all validator classes must implement to be
    compatible with the validation framework. Validators check specific aspects
    of plugin structure and can optionally provide auto-fixing capabilities.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Run validation check on path.

        Args:
            path: Path to file or directory to validate

        Returns:
            ValidationResult with passed status and any issues found
        """
        ...

    def can_fix(self) -> bool:
        """Whether this validator supports auto-fixing.

        Returns:
            True if validator can automatically fix issues, False otherwise
        """
        ...

    def fix(self, path: Path) -> list[str]:
        """Auto-fix issues in the file or directory.

        Args:
            path: Path to file or directory to fix

        Returns:
            List of human-readable descriptions of fixes applied
        """
        ...


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def generate_docs_url(error_code: ErrorCode) -> str:
    """Generate documentation URL for error code.

    Args:
        error_code: Error code (ErrorCode enum or string like "FM001", "SK006").

    Returns:
        Full URL to error code documentation with anchor
    """
    return f"{ERROR_CODE_BASE_URL}#{str(error_code).lower()}"


# extract_frontmatter imported from frontmatter_core


def _get_pydantic_ctx_val(error: ErrorDetails, key: str, default: str = "") -> str:
    """Extract a string value from Pydantic error ctx dict.

    Returns:
        The ctx value as string, or default if not found.
    """
    ctx = error.get("ctx")
    if isinstance(ctx, dict):
        val = ctx.get(key)
        return str(val) if val is not None else default
    return default


def _pydantic_error_to_validation_issue(error: ErrorDetails) -> ValidationIssue:
    """Convert a single Pydantic ValidationError item to a ValidationIssue.

    Args:
        error: Pydantic ErrorDetails from ValidationError.errors().

    Returns:
        ValidationIssue with appropriate code and suggestion.
    """
    loc = error.get("loc", ())
    field = ".".join(
        str(x) for x in (loc if isinstance(loc, (list, tuple)) else (loc,))
    )
    msg = str(error.get("msg", ""))
    code = FM005
    suggestion: str | None = None

    if "Field required" in msg:
        code = FM001
        msg = f"Missing required field: {field}"
    elif "String should match pattern" in msg:
        code = FM010
        msg = "Must use lowercase letters, numbers, and hyphens only"
        suggestion = "Use format: lowercase-with-hyphens"
    elif "String should have at most" in msg:
        max_len = _get_pydantic_ctx_val(error, "max_length", "unknown")
        msg = f"Exceeds maximum length of {max_len} characters"
        suggestion = f"Shorten to {max_len} characters or less"
    elif "Input should be" in msg and "literal" in msg.lower():
        code = FM006
        valid_values = _get_pydantic_ctx_val(error, "expected")
        msg = f"Invalid value. Must be one of: {valid_values}"
    elif isinstance(error.get("input"), list):
        if "tools" in field.lower():
            code = FM007
            msg = "Tools field is YAML array (should be comma-separated string)"
        elif "skills" in field.lower():
            code = FM008
            msg = "Skills field is YAML array (should be comma-separated string)"
        suggestion = "Use format: 'tool1, tool2, tool3'"
    elif "colon" in msg.lower():
        code = FM009
        suggestion = "Quote the description or remove colons"

    return ValidationIssue(
        field=field,
        severity="error",
        message=msg,
        code=code,
        docs_url=generate_docs_url(code),
        suggestion=suggestion,
    )


def _check_list_valued_tool_fields(
    data: dict[str, YamlValue], errors: list[ValidationIssue]
) -> None:
    """Append errors for list-valued tools/skills fields that Pydantic may not catch.

    Args:
        data: Parsed frontmatter dict.
        errors: Mutable list to append ValidationIssue objects to.
    """
    for field_name, field_val in data.items():
        if not isinstance(field_val, list):
            continue
        if field_name in {"tools", "disallowedTools", "allowed-tools"}:
            errors.append(
                ValidationIssue(
                    field=field_name,
                    severity="error",
                    message="Tools field is YAML array (should be comma-separated string)",
                    code=FM007,
                    docs_url=generate_docs_url(FM007),
                    suggestion="Use format: 'tool1, tool2, tool3'",
                )
            )
        elif field_name == "skills":
            errors.append(
                ValidationIssue(
                    field=field_name,
                    severity="error",
                    message="Skills field is YAML array (should be comma-separated string)",
                    code=FM008,
                    docs_url=generate_docs_url(FM008),
                    suggestion="Use format: 'skill1, skill2, skill3'",
                )
            )


def _check_skill_name_and_directory(
    data: dict[str, YamlValue],
    path: Path,
    file_type: FileType,
    errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
) -> None:
    """Validate skill name field and directory name for SKILL.md files.

    Args:
        data: Parsed frontmatter dict.
        path: Path to SKILL.md file.
        file_type: Detected file type.
        errors: Mutable list to append errors to.
        warnings: Mutable list to append warnings to.
    """
    if file_type != FileType.SKILL or path.name != "SKILL.md":
        return

    skill_name_in_fm = data.get("name")
    skill_dir_name = path.parent.name

    if path.parent.parent.name == "skills":
        dir_name_issues = _validate_skill_directory_name(skill_dir_name)
        for issue_msg, issue_suggestion in dir_name_issues:
            errors.append(
                ValidationIssue(
                    field="directory",
                    severity="error",
                    message=issue_msg,
                    code=SK008,
                    docs_url=generate_docs_url(SK008),
                    suggestion=issue_suggestion,
                )
            )

    if skill_name_in_fm and skill_name_in_fm != skill_dir_name:
        warnings.append(
            ValidationIssue(
                field="name",
                severity="warning",
                message=(
                    f"'name' field value '{skill_name_in_fm}' does not match directory name '{skill_dir_name}'"
                ),
                code=FM010,
                docs_url=generate_docs_url(FM010),
                suggestion=(f"Set name: {skill_dir_name} to match the directory name"),
            )
        )


# ============================================================================
# PROGRESSIVE DISCLOSURE VALIDATOR
# ============================================================================


class ProgressiveDisclosureValidator:
    """Validates presence of progressive disclosure directories.

    Checks for references/, examples/, and scripts/ directories that help
    organize additional content for on-demand exploration. Missing directories
    are reported as INFO (not errors) since they're optional organizational aids.

    Architecture lines 1170-1186, Task T7 lines 815-876
    """

    # Directory names to check for progressive disclosure
    DISCLOSURE_DIRS: ClassVar[list[str]] = ["references", "examples", "scripts"]

    def validate(self, path: Path) -> ValidationResult:
        """Validate progressive disclosure structure in skill directory.

        Args:
            path: Path to skill directory (should contain SKILL.md)

        Returns:
            ValidationResult with info messages for missing directories
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        # Only validate skill directories (must contain SKILL.md)
        if path.is_file():
            path = path.parent

        skill_file = path / "SKILL.md"
        if not skill_file.exists():
            # Not a skill directory - skip validation
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        # Check each progressive disclosure directory
        for dir_name in self.DISCLOSURE_DIRS:
            dir_path = path / dir_name
            if not dir_path.exists():
                # Directory missing - report as INFO
                code = self._get_error_code(dir_name)
                info.append(
                    ValidationIssue(
                        field="progressive-disclosure",
                        severity="info",
                        message=f"No {dir_name}/ directory found (consider adding for documentation)",
                        code=code,
                        docs_url=generate_docs_url(code),
                        suggestion=f"Create {dir_name}/ directory to organize additional content",
                    )
                )
            else:
                # Directory exists - count files recursively
                sum(1 for _ in dir_path.rglob("*") if _.is_file())
                # No info message needed when directory exists
                # (only report missing directories)

        # Always pass - info messages don't fail validation
        return ValidationResult(
            passed=True, errors=errors, warnings=warnings, info=info
        )

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (creating directories requires content creation decisions)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix progressive disclosure issues (not supported).

        Args:
            path: Path to directory to fix

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Progressive disclosure validation cannot be auto-fixed
        """
        raise NotImplementedError(
            "Progressive disclosure validation cannot be auto-fixed. "
            "Creating directories requires human decisions about content organization."
        )

    def _get_error_code(self, dir_name: str) -> ErrorCode:
        """Get error code for missing directory.

        Args:
            dir_name: Directory name (references, examples, scripts)

        Returns:
            Error code (PD001, PD002, PD003)
        """
        match dir_name:
            case "references":
                return PD001
            case "examples":
                return PD002
            case "scripts":
                return PD003
            case _:
                return PD001  # Default fallback


# ============================================================================
# INTERNAL LINK VALIDATOR
# ============================================================================


class InternalLinkValidator:
    """Validates internal markdown links in SKILL.md files.

    Checks that relative links point to existing files (LK001) and that
    relative links use the ./ prefix convention (LK002).

    Architecture lines 1188-1256, Task T8 lines 897-982
    """

    # Regex pattern for extracting markdown links (Architecture line 1219)
    LINK_PATTERN: ClassVar[str] = r"\[([^\]]+)\]\(([^)]+)\)"

    # Regex pattern for fenced code blocks (``` or ~~~, with optional language specifier).
    # Uses backreference to match opening/closing fence of equal or greater length.
    CODE_FENCE_PATTERN: ClassVar[str] = r"^(`{3,}|~{3,})[^\n]*\n.*?\n\1\s*$"

    # Regex pattern for inline code spans (single or multiple backticks)
    INLINE_CODE_PATTERN: ClassVar[str] = r"(`+)(?!`)(.+?)(?<!`)\1(?!`)"

    @staticmethod
    def _strip_code_blocks(content: str) -> str:
        """Remove fenced code blocks and inline code spans from content.

        Strips fenced code blocks delimited by ``` or ~~~ (with optional
        language specifiers) and inline code spans wrapped in backticks.
        This prevents code examples from being scanned for markdown links.

        Args:
            content: Raw markdown content

        Returns:
            Content with code blocks and inline code spans removed
        """
        # Strip fenced code blocks first (handles nested fences via greedy
        # backreference matching: a 4-backtick fence won't close on 3 backticks)
        stripped = re.sub(
            InternalLinkValidator.CODE_FENCE_PATTERN,
            "",
            content,
            flags=re.MULTILINE | re.DOTALL,
        )
        # Strip inline code spans
        return re.sub(InternalLinkValidator.INLINE_CODE_PATTERN, "", stripped)

    def validate(self, path: Path) -> ValidationResult:
        """Validate internal markdown links in SKILL.md.

        Args:
            path: Path to SKILL.md file

        Returns:
            ValidationResult with errors for broken links.
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        # Only validate SKILL.md files
        if path.name != "SKILL.md":
            # Not a skill file - skip validation
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        # Read file
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        # Strip fenced code blocks and inline code spans before scanning for
        # links.  Code examples often contain bracket-paren patterns (e.g.
        # Python generics like Sequence[T]) that match the link regex.
        scannable_content = self._strip_code_blocks(content)

        # Extract all markdown links from non-code content
        matches = re.finditer(self.LINK_PATTERN, scannable_content)

        # Process each link
        for match in matches:
            link_text = match.group(1)
            link_url = match.group(2)

            # Filter to relative file links only
            if self._should_ignore_link(link_url):
                continue

            # Strip anchor fragment before resolving path
            # e.g., ./references/file.md#heading → ./references/file.md
            link_url_no_fragment = link_url.split("#")[0]

            # Resolve link path relative to SKILL.md directory
            skill_dir = path.parent
            link_path = (skill_dir / link_url_no_fragment).resolve()

            # Check if linked file exists (error)
            if not link_path.exists():
                errors.append(
                    ValidationIssue(
                        field="internal-links",
                        severity="error",
                        message=f"Broken link: [{link_text}]({link_url}) (file not found)",
                        code=LK001,
                        docs_url=generate_docs_url(LK001),
                        suggestion=f"Create missing file or fix link path: {link_url}",
                    )
                )

            # Warn if relative link is missing ./ prefix (LK002)
            # Links starting with ../ are valid cross-directory references; skip them.
            if not link_url_no_fragment.startswith(("./", "../")):
                warnings.append(
                    ValidationIssue(
                        field="internal-links",
                        severity="warning",
                        message=f"Link missing ./ prefix: [{link_text}]({link_url})",
                        code=LK002,
                        docs_url=generate_docs_url(LK002),
                        suggestion=f"Add ./ prefix: ./{link_url}",
                    )
                )

        # Pass if no errors (warnings don't fail validation)
        passed = len(errors) == 0
        return ValidationResult(
            passed=passed, errors=errors, warnings=warnings, info=info
        )

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (broken links require file creation or manual correction)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix internal link issues (not supported).

        Args:
            path: Path to file to fix

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Internal link validation cannot be auto-fixed
        """
        raise NotImplementedError(
            "Internal link validation cannot be auto-fixed. "
            "Broken links require creating missing files or correcting link paths manually."
        )

    def _should_ignore_link(self, url: str) -> bool:
        """Check if link should be ignored during validation.

        Args:
            url: Link URL to check

        Returns:
            True if link should be ignored (external, anchor, absolute)
        """
        # Ignore external links
        if url.startswith(("http://", "https://", "ftp://")):
            return True

        # Ignore anchor links
        if url.startswith("#"):
            return True

        # Ignore absolute paths
        return bool(url.startswith("/"))


# ============================================================================
# NAMESPACE REFERENCE VALIDATOR
# ============================================================================


class NamespaceReferenceValidator:
    """Validates namespace-qualified references in plugin files.

    Checks that ``Skill()``, ``Task()``, ``@agent``, and ``/command`` references
    with namespace prefixes (``plugin:name``) resolve to actual files in the
    referenced plugin directory.

    Detects patterns such as:
    - ``Skill(command: "plugin:skill-name")``
    - ``Skill(skill="plugin:skill-name")``
    - ``Task(agent="plugin:agent-name")``
    - ``@plugin:agent-name`` (prose agent references)
    - ``/plugin:skill-name`` (slash command references)
    """

    # Regex patterns for extracting namespace-qualified references
    SKILL_COMMAND_PATTERN: ClassVar[str] = r'Skill\(command:\s*"([^"]+):([^"]+)"'
    SKILL_SKILL_PATTERN: ClassVar[str] = r'Skill\(skill="([^"]+):([^"]+)"'
    TASK_AGENT_PATTERN: ClassVar[str] = r'Task\(agent[=:]\s*"([^"]+):([^"]+)"'
    AT_AGENT_PATTERN: ClassVar[str] = r"@([a-z0-9-]+):([a-z0-9-]+)"
    SLASH_COMMAND_PATTERN: ClassVar[str] = r"(?<!\w)/([a-z0-9-]+):([a-z0-9-]+)"

    # Built-in agent types that should be skipped (not plugin agents)
    BUILTIN_AGENTS: ClassVar[frozenset[str]] = frozenset(
        {
            "Explore",
            "general-purpose",
            "Plan",
            "Bash",
            "context-gathering",
            "code-review",
            "code-refactorer-agent",
            "system-architect",
            "comprehensive-researcher",
            "technical-researcher",
            "trace-protocol-investigator",
            "doc-freshness-guardian",
            "documentation-expert",
            "test-architect",
            "live-api-integration-tester",
            "subagent-generator",
            "github-project-manager",
            "metadata-vault-manager",
            "doc-drift-auditor",
            "service-documentation",
            "backlog-item-groomer",
            "plugin-assessor",
            "skill-refactorer-agent",
            "contextual-ai-documentation-optimizer",
            "plugin-docs-writer",
            "logging",
            "context-refinement",
            "qa-devops-lead",
            "embedded-dev-specialist",
            "c-systems-programmer",
            "statusline-setup",
            "linting-root-cause-resolver",
            "python-cli-architect",
            "python-portable-script",
            "python-code-reviewer",
        }
    )

    def validate(self, path: Path) -> ValidationResult:
        """Validate namespace-qualified references in a plugin file.

        Extracts references from the file body (after frontmatter) and verifies
        each namespace-qualified reference resolves to an existing file in the
        referenced plugin directory.

        Args:
            path: Path to a SKILL.md, agent .md, or command .md file

        Returns:
            ValidationResult with errors for broken references
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=NR001,
                    docs_url=generate_docs_url(NR001),
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        # Only check the body (after frontmatter)
        body = self._extract_body(content)
        if not body:
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        # Find the plugins root directory
        plugins_root = self._find_plugins_root(path)
        if plugins_root is None:
            # Not inside a plugins directory structure -- skip validation
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        # Collect all references: (pattern_label, plugin, name, ref_type)
        references = self._extract_references(body)

        for label, plugin, name, ref_type in references:
            # Skip template placeholders containing { or }
            if "{" in plugin or "}" in plugin or "{" in name or "}" in name:
                continue

            match ref_type:
                case "skill":
                    found = self._resolve_skill_reference(plugins_root, plugin, name)
                    expected = (
                        f"plugins/{plugin}/skills/{name}/SKILL.md "
                        f"or plugins/{plugin}/skills/{{category}}/{name}/SKILL.md"
                    )
                case "agent":
                    # Skip built-in agent names
                    if name in self.BUILTIN_AGENTS or plugin in self.BUILTIN_AGENTS:
                        continue
                    found = self._resolve_agent_reference(plugins_root, plugin, name)
                    expected = f"plugins/{plugin}/agents/{name}.md"
                case "command":
                    found = self._resolve_command_reference(plugins_root, plugin, name)
                    expected = (
                        f"plugins/{plugin}/skills/{name}/SKILL.md, "
                        f"plugins/{plugin}/skills/{{category}}/{name}/SKILL.md, "
                        f"or plugins/{plugin}/commands/{name}.md"
                    )
                case _:
                    continue

            # Check if the reference target is inside the plugins root
            plugin_dir = plugins_root / plugin
            if not plugin_dir.is_dir():
                errors.append(
                    ValidationIssue(
                        field="namespace-reference",
                        severity="error",
                        message=(
                            f"Namespace reference target does not exist: "
                            f"{label} -- plugin directory '{plugin}' not found"
                        ),
                        code=NR001,
                        docs_url=generate_docs_url(NR001),
                        suggestion=(
                            f"Expected plugin directory at: {plugins_root / plugin}. "
                            f"Create the plugin or fix the namespace prefix."
                        ),
                    )
                )
                continue

            if not found:
                errors.append(
                    ValidationIssue(
                        field="namespace-reference",
                        severity="error",
                        message=(f"Namespace reference target does not exist: {label}"),
                        code=NR001,
                        docs_url=generate_docs_url(NR001),
                        suggestion=f"Expected file at: {expected}",
                    )
                )

        passed = len(errors) == 0
        return ValidationResult(
            passed=passed, errors=errors, warnings=warnings, info=info
        )

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (namespace references require manual correction)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix namespace reference issues (not supported).

        Args:
            path: Path to file to fix

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Namespace reference validation cannot be auto-fixed
        """
        raise NotImplementedError(
            "Namespace reference validation cannot be auto-fixed. "
            "Broken references require creating missing files or correcting "
            "the namespace prefix manually."
        )

    def _extract_body(self, content: str) -> str:
        """Extract file body content after YAML frontmatter.

        Args:
            content: Full file content

        Returns:
            Body text after the closing ``---`` delimiter, or the full content
            if no frontmatter is present
        """
        if not content.startswith("---"):
            return content

        # Find closing delimiter
        end_match = re.search(r"\n---\s*\n", content[3:])
        if not end_match:
            return content

        # Return everything after the closing ---
        return content[3 + end_match.end() :]

    def _find_plugins_root(self, path: Path) -> Path | None:
        """Find the repository-level ``plugins/`` directory from a file path.

        Walks up from the file path looking for a directory named ``plugins``
        that appears in the path's parents.

        Args:
            path: Path to a file inside a plugin

        Returns:
            Path to the ``plugins/`` directory, or None if not found
        """
        resolved = path.resolve()
        parts = resolved.parts
        for i in range(len(parts) - 1, -1, -1):
            if parts[i] == "plugins":
                candidate = Path(*parts[: i + 1])
                if candidate.is_dir():
                    return candidate
        return None

    @staticmethod
    def _resolve_to_directory(path: Path) -> Path | None:
        """Resolve path to directory, following symlinks and Git pointer files (Windows).

        On Windows, Git may store symlinks as regular files whose content is the
        target path. This allows validation to work cross-platform.

        Args:
            path: Path that may be a directory, symlink, or pointer file

        Returns:
            Resolved directory path, or None if resolution fails
        """
        result: Path | None = None
        if path.is_dir():
            result = path.resolve()
        elif path.is_symlink():
            resolved = path.resolve()
            result = resolved if resolved.is_dir() else None
        elif path.is_file():
            try:
                content = path.read_text(encoding="utf-8").strip()
            except OSError:
                pass
            else:
                if content and "\n" not in content:
                    try:
                        target = (path.parent / content).resolve()
                        result = target if target.is_dir() else None
                    except (OSError, RuntimeError):
                        pass
        return result

    def _resolve_skill_reference(
        self, plugins_root: Path, plugin: str, name: str
    ) -> bool:
        """Check if a skill reference resolves to an existing file.

        Checks direct path and nested (category) paths. Resolves symlinks and
        Git pointer files (Windows) before existence checks.

        Args:
            plugins_root: Path to the ``plugins/`` directory
            plugin: Plugin name (namespace prefix)
            name: Skill name

        Returns:
            True if the skill SKILL.md exists at any valid location
        """
        # Direct: plugins/{plugin}/skills/{name}/SKILL.md
        skill_dir = plugins_root / plugin / "skills" / name
        resolved_dir = self._resolve_to_directory(skill_dir)
        if resolved_dir is not None and (resolved_dir / "SKILL.md").is_file():
            return True

        # Also check direct path (real symlinks resolve via resolve())
        direct = plugins_root / plugin / "skills" / name / "SKILL.md"
        if direct.is_file():
            return True

        # Nested: plugins/{plugin}/skills/*/{name}/SKILL.md
        nested_pattern = plugins_root / plugin / "skills"
        if nested_pattern.is_dir():
            for category_dir in nested_pattern.iterdir():
                resolved_cat = self._resolve_to_directory(category_dir)
                if resolved_cat is not None:
                    nested = resolved_cat / name / "SKILL.md"
                    if nested.is_file():
                        return True
                    # Pointer/symlink: category_dir may resolve to skill dir itself
                    if (
                        category_dir.name == name
                        and (resolved_cat / "SKILL.md").is_file()
                    ):
                        return True

        return False

    def _resolve_agent_reference(
        self, plugins_root: Path, plugin: str, name: str
    ) -> bool:
        """Check if an agent reference resolves to an existing file.

        Args:
            plugins_root: Path to the ``plugins/`` directory
            plugin: Plugin name (namespace prefix)
            name: Agent name

        Returns:
            True if the agent .md file exists
        """
        agent_path = plugins_root / plugin / "agents" / f"{name}.md"
        return agent_path.is_file()

    def _resolve_command_reference(
        self, plugins_root: Path, plugin: str, name: str
    ) -> bool:
        """Check if a command/slash-command reference resolves to an existing file.

        Slash command references can resolve to skills or commands.

        Args:
            plugins_root: Path to the ``plugins/`` directory
            plugin: Plugin name (namespace prefix)
            name: Command or skill name

        Returns:
            True if the target exists as a skill or command
        """
        # Check as skill first (most common)
        if self._resolve_skill_reference(plugins_root, plugin, name):
            return True

        # Check as command: plugins/{plugin}/commands/{name}.md
        command_path = plugins_root / plugin / "commands" / f"{name}.md"
        return command_path.is_file()

    @staticmethod
    def _strip_urls_and_code(body: str) -> str:
        """Remove URLs, fenced code blocks, and inline code spans from body.

        Strips content that may contain slash-colon patterns that are not
        real namespace references (e.g. ``http://localhost:8080``).

        Args:
            body: Markdown body content

        Returns:
            Body with URLs, fenced code blocks, and inline code spans removed
        """
        # Strip fenced code blocks (``` or ~~~ delimited)
        stripped = re.sub(
            r"^(`{3,}|~{3,})[^\n]*\n.*?\n\1\s*$",
            "",
            body,
            flags=re.MULTILINE | re.DOTALL,
        )
        # Strip inline code spans
        stripped = re.sub(r"(`+)(?!`)(.+?)(?<!`)\1(?!`)", "", stripped)
        # Strip URLs (http:// and https:// through end of URL)
        return re.sub(r"https?://[^\s)\]>\"']+", "", stripped)

    def _extract_references(self, body: str) -> list[tuple[str, str, str, str]]:
        """Extract all namespace-qualified references from file body.

        Args:
            body: File body content (after frontmatter)

        Returns:
            List of (label, plugin, name, ref_type) tuples where ref_type is
            one of 'skill', 'agent', or 'command'
        """
        references: list[tuple[str, str, str, str]] = []

        # Skill(command: "plugin:name")
        for match in re.finditer(self.SKILL_COMMAND_PATTERN, body):
            plugin, name = match.group(1), match.group(2)
            label = f'Skill(command: "{plugin}:{name}")'
            references.append((label, plugin, name, "skill"))

        # Skill(skill="plugin:name")
        for match in re.finditer(self.SKILL_SKILL_PATTERN, body):
            plugin, name = match.group(1), match.group(2)
            label = f'Skill(skill="{plugin}:{name}")'
            references.append((label, plugin, name, "skill"))

        # Task(agent="plugin:name")
        for match in re.finditer(self.TASK_AGENT_PATTERN, body):
            plugin, name = match.group(1), match.group(2)
            label = f'Task(agent="{plugin}:{name}")'
            references.append((label, plugin, name, "agent"))

        # @plugin:agent-name
        for match in re.finditer(self.AT_AGENT_PATTERN, body):
            plugin, name = match.group(1), match.group(2)
            label = f"@{plugin}:{name}"
            references.append((label, plugin, name, "agent"))

        # /plugin:skill-name -- use stripped body to avoid URL false positives
        stripped_body = self._strip_urls_and_code(body)
        for match in re.finditer(self.SLASH_COMMAND_PATTERN, stripped_body):
            plugin, name = match.group(1), match.group(2)
            label = f"/{plugin}:{name}"
            references.append((label, plugin, name, "command"))

        return references


# ============================================================================
# SYMLINK TARGET VALIDATOR
# ============================================================================


class SymlinkTargetValidator:
    r"""Validates that symlinks within the validated path have clean target paths.

    Detects symlinks whose targets contain trailing whitespace or newlines
    (e.g. ``os.readlink()`` returns ``'../../python3-development/skills/uv\\n'``).
    Such symlinks cause ``Path.resolve()`` and ``is_file()``/``is_dir()`` to
    fail silently, producing false-positive errors in other validators.

    When ``path`` is a file: checks whether the file itself is a symlink with
    a dirty target.  When ``path`` is a directory: scans all symlinks found
    recursively within the directory.

    Auto-fix (SL001): strips trailing whitespace from the target, removes the
    old symlink, and recreates it pointing to the clean target.  The fix is
    only applied when the cleaned target resolves to an existing path.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Detect symlinks with trailing whitespace in their target paths.

        Args:
            path: Path to a file or directory to inspect for dirty symlinks.

        Returns:
            ValidationResult with errors for each dirty symlink found.
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        for symlink_path in self._iter_symlinks(path):
            try:
                raw_target = str(Path(symlink_path).readlink())
            except OSError:
                continue

            if raw_target != raw_target.rstrip():
                clean_target = raw_target.rstrip()
                errors.append(
                    ValidationIssue(
                        field=str(symlink_path),
                        severity="error",
                        message=(
                            f"Symlink target has trailing whitespace: "
                            f"{symlink_path!s} -> {raw_target!r} "
                            f"(should be {clean_target!r})"
                        ),
                        code=SL001,
                        docs_url=generate_docs_url(SL001),
                        suggestion=(
                            "Run with --fix to strip trailing whitespace and recreate the symlink, "
                            'or run: python3 -c "'
                            f"import os; p='{symlink_path}'; t=os.readlink(p).rstrip(); "
                            'os.remove(p); os.symlink(t, p)"'
                        ),
                    )
                )

        passed = len(errors) == 0
        return ValidationResult(
            passed=passed, errors=errors, warnings=warnings, info=info
        )

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            True (trailing whitespace in symlink targets can be stripped automatically)
        """
        return True

    def fix(self, path: Path) -> list[str]:
        """Strip trailing whitespace from symlink targets and recreate affected symlinks.

        Only recreates symlinks whose cleaned target resolves to an existing path.
        Symlinks whose cleaned target does not exist are left untouched and reported
        as unfixable.

        Args:
            path: Path to a file or directory to scan for dirty symlinks.

        Returns:
            List of human-readable descriptions of fixes applied.
        """
        fixes: list[str] = []

        for symlink_path in self._iter_symlinks(path):
            try:
                raw_target = str(Path(symlink_path).readlink())
            except OSError:
                continue

            if raw_target == raw_target.rstrip():
                continue  # Target is already clean

            clean_target = raw_target.rstrip()

            # Resolve the cleaned target to verify it exists before recreating
            resolved = (symlink_path.parent / clean_target).resolve()
            if not resolved.exists():
                continue  # Cannot verify cleaned target — leave untouched

            try:
                Path(symlink_path).unlink()
                Path(symlink_path).symlink_to(clean_target)
                fixes.append(
                    f"Fixed symlink {symlink_path}: stripped trailing whitespace from target "
                    f"({raw_target!r} -> {clean_target!r})"
                )
            except OSError:
                # Best-effort: if remove/symlink fails, leave the original in place
                with contextlib.suppress(OSError):
                    Path(symlink_path).symlink_to(raw_target)

        return fixes

    @staticmethod
    def _iter_symlinks(path: Path) -> list[Path]:
        """Yield all symlinks at or under *path*.

        When *path* is itself a symlink, returns ``[path]``.
        When *path* is a directory (real or symlink), returns all symlinks
        found by ``os.walk`` (which does not follow symlinks by default).

        Args:
            path: Starting path to search for symlinks.

        Returns:
            List of symlink paths found.
        """
        symlinks: list[Path] = []

        if path.is_symlink():
            symlinks.append(path)
            return symlinks

        if path.is_dir():
            for root, dirs, files in os.walk(path, followlinks=False):
                root_path = Path(root)
                for name in dirs + files:
                    candidate = root_path / name
                    if candidate.is_symlink():
                        symlinks.append(candidate)

        return symlinks


# SkillFrontmatter, CommandFrontmatter, AgentFrontmatter imported from frontmatter_core


_SKILL_DIR_CONVENTION_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _validate_skill_directory_name(skill_dir_name: str) -> list[tuple[str, str]]:
    """Validate skill directory name against naming conventions.

    Checks: non-empty, max 40 chars, lowercase+digits+hyphens only,
    no leading/trailing/consecutive hyphens, no underscores.

    Args:
        skill_dir_name: Directory name to validate.

    Returns:
        List of (message, suggestion) tuples for each violation found.
        Empty list if the name is valid.
    """
    if not skill_dir_name:
        return [
            (
                "Skill directory name cannot be empty",
                "Provide a non-empty directory name",
            )
        ]

    results: list[tuple[str, str]] = []

    if len(skill_dir_name) > MAX_SKILL_NAME_LENGTH:
        results.append(
            (
                f"Directory name exceeds maximum length of {MAX_SKILL_NAME_LENGTH} characters (got {len(skill_dir_name)})",
                f"Shorten directory name to {MAX_SKILL_NAME_LENGTH} characters or less",
            )
        )

    if not _SKILL_DIR_CONVENTION_PATTERN.match(skill_dir_name):
        violations: list[str] = []
        if re.search(r"[A-Z]", skill_dir_name):
            violations.append("contains uppercase letters")
        if re.search(r"[^a-z0-9-]", skill_dir_name):
            violations.append(
                "contains invalid characters (only lowercase, digits, hyphens allowed)"
            )
        if skill_dir_name.startswith("-"):
            violations.append("starts with hyphen")
        if skill_dir_name.endswith("-"):
            violations.append("ends with hyphen")
        if "--" in skill_dir_name:
            violations.append("contains consecutive hyphens")
        if "_" in skill_dir_name:
            violations.append("contains underscores (use hyphens instead)")
        violation_msg = "; ".join(violations) if violations else "invalid format"
        results.append(
            (
                f"Directory name {violation_msg}",
                "Use lowercase-hyphen-case (e.g., 'my-skill-name')",
            )
        )

    return results


# ============================================================================
# FRONTMATTER VALIDATOR
# ============================================================================


class FrontmatterValidator:
    """Validates and auto-fixes YAML frontmatter in capability files.

    Implements Validator protocol for frontmatter validation of skills, agents,
    and commands. Uses shared Pydantic models from frontmatter_core.
    """

    def __init__(self) -> None:
        """Initialize frontmatter validator.

        ``_pending_fm009_info`` accumulates FM009 info issues produced by
        :meth:`fix` (via :meth:`_apply_fixes`) so that the next
        :meth:`validate` call can surface them as ``info`` entries.  This lets
        ``--verbose`` output show exactly which fields were silently repaired by
        the unquoted-colon auto-fix.
        """
        self._pending_fm009_info: list[ValidationIssue] = []

    def validate(self, path: Path) -> ValidationResult:
        """Validate frontmatter in file.

        Args:
            path: Path to file with YAML frontmatter

        Returns:
            ValidationResult with errors, warnings, and info issues

        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        # Drain any FM009 info issues queued by a preceding fix() call so that
        # --verbose output shows what was silently repaired.
        info: list[ValidationIssue] = self._pending_fm009_info
        self._pending_fm009_info = []

        # Read file
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        # Extract frontmatter
        frontmatter_text, _start_line, _end_line = self._extract_frontmatter(content)
        if frontmatter_text is None:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message="No YAML frontmatter found",
                    code=FM003,
                    docs_url=generate_docs_url(FM003),
                    suggestion="File must start with '---' delimiter",
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        # Detect file type
        file_type = FileType.detect_file_type(path)
        if file_type == FileType.UNKNOWN:
            file_type = FileType.SKILL

        # Check for forbidden multiline indicators
        if re.search(r"description:\s*[|>][-+]?\s*\n", frontmatter_text):
            errors.append(
                ValidationIssue(
                    field="description",
                    severity="error",
                    message="Uses forbidden multiline YAML syntax (|, >, |-, >-)",
                    code=FM004,
                    docs_url=generate_docs_url(FM004),
                    suggestion="Use single-line string",
                )
            )

        # Parse YAML
        try:
            data = _safe_load_yaml(frontmatter_text)
        except YAMLError as e:
            errors.append(
                ValidationIssue(
                    field="(yaml)",
                    severity="error",
                    message=f"Invalid YAML syntax: {e}",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        if not isinstance(data, dict):
            errors.append(
                ValidationIssue(
                    field="(yaml)",
                    severity="error",
                    message="Frontmatter must be a YAML mapping",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        # Select Pydantic model based on file type
        model_class = self._get_model_class(file_type)
        if not model_class:
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        # Validate with Pydantic
        try:
            validated = model_class.model_validate(data)

            # Add warning for long descriptions
            if (
                hasattr(validated, "description")
                and validated.description
                and len(validated.description) > RECOMMENDED_DESCRIPTION_LENGTH
            ):
                warnings.append(
                    ValidationIssue(
                        field="description",
                        severity="warning",
                        message=f"Exceeds recommended length of {RECOMMENDED_DESCRIPTION_LENGTH} characters (got {len(validated.description)})",
                        code=SK004,
                        docs_url=generate_docs_url(SK004),
                        suggestion=f"Front-load critical information in first {RECOMMENDED_DESCRIPTION_LENGTH} characters. Run /plugin-creator:write-frontmatter-description to generate an optimized description",
                    )
                )

        except ValidationError as e:
            errors.extend(
                _pydantic_error_to_validation_issue(err) for err in e.errors()
            )

        if isinstance(data, dict):
            _check_list_valued_tool_fields(data, errors)
            _check_skill_name_and_directory(data, path, file_type, errors, warnings)

        # Validate hook script file-path references declared in frontmatter ``hooks:`` field.
        # The ``hooks:`` field in SKILL.md / agent / command frontmatter uses the same
        # structure as the root ``"hooks"`` key in hooks.json.
        if isinstance(data, dict) and isinstance(data.get("hooks"), dict):
            hook_validator = HookValidator()
            hook_validator.validate_hook_script_references_in_hooks_dict(
                data["hooks"], path.parent, errors
            )

        passed = len(errors) == 0
        return ValidationResult(
            passed=passed, errors=errors, warnings=warnings, info=info
        )

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            True (frontmatter validator supports auto-fixing)
        """
        return True

    def fix(self, path: Path) -> list[str]:
        """Auto-fix frontmatter issues in file.

        Fixes FM004, FM007, FM008, FM009 only. Does not fix schema violations.

        Args:
            path: Path to file to fix

        Returns:
            List of human-readable descriptions of fixes applied
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return []

        # Detect file type
        file_type = FileType.detect_file_type(path)
        if file_type == FileType.UNKNOWN:
            file_type = FileType.SKILL

        # Apply fixes
        fixed_content, fixes = self._apply_fixes(content, file_type, path)

        if not fixes:
            return []

        # Write fixed content
        try:
            path.write_text(fixed_content, encoding="utf-8")
        except OSError:
            return []

        return fixes

    def _extract_frontmatter(self, content: str) -> tuple[str | None, int, int]:
        """Extract YAML frontmatter from content.

        Returns:
            Tuple of (frontmatter_text, start_line, end_line) or (None, 0, 0)

        Deprecated:
            Use module-level extract_frontmatter() function instead.
        """
        return extract_frontmatter(content)

    def _get_model_class(
        self, file_type: FileType
    ) -> type[SkillFrontmatter | CommandFrontmatter | AgentFrontmatter] | None:
        """Get Pydantic model class for file type.

        Delegates to frontmatter_core.get_frontmatter_model().

        Returns:
            Pydantic model class or None if unknown type.
        """
        return get_frontmatter_model(file_type.value)

    def _queue_fm009_info(self, fixed_fields: list[str]) -> None:
        """Append FM009 info issues for fields that were auto-fixed by colon quoting.

        Args:
            fixed_fields: Field names whose values were quoted.
        """
        for field_name in fixed_fields:
            self._pending_fm009_info.append(
                ValidationIssue(
                    field=field_name,
                    severity="info",
                    message=(
                        f"Auto-fixed: unquoted value containing colon was quoted in field '{field_name}'"
                    ),
                    code=FM009,
                    docs_url=generate_docs_url(FM009),
                )
            )

    def _parse_frontmatter_with_colon_fix(
        self, frontmatter_text: str
    ) -> tuple[str, dict[str, YamlValue] | None, list[str]]:
        """Parse frontmatter, applying unquoted-colon fix if YAML parse fails.

        Returns:
            Tuple of (frontmatter_text, parsed_data, colon_fix_descriptions).
            parsed_data is None if parse failed even after colon fix.
        """
        colon_fixes: list[str] = []
        try:
            original_data = _safe_load_yaml(frontmatter_text)
        except YAMLError:
            fixed_fm, colon_fixes, colon_fields = _fix_unquoted_colons(frontmatter_text)
            if colon_fixes:
                self._queue_fm009_info(colon_fields)
                try:
                    original_data = _safe_load_yaml(fixed_fm)
                except YAMLError:
                    pass
                else:
                    return (
                        fixed_fm,
                        cast("dict[str, YamlValue]", original_data),
                        colon_fixes,
                    )
            return frontmatter_text, None, colon_fixes
        else:
            return (
                frontmatter_text,
                cast("dict[str, YamlValue]", original_data),
                colon_fixes,
            )

    def _normalize_tool_fields_and_detect_changes(
        self,
        normalized_dict: dict[str, YamlValue],
        original_data: dict[str, YamlValue],
        frontmatter_text: str,
        colon_fixes: list[str],
        file_type: FileType,
        file_path: Path | None,
    ) -> tuple[dict[str, YamlValue], list[str]]:
        """Normalize tool/skills fields and detect other changes.

        Returns:
            Tuple of (dict to dump, combined list of fix descriptions).
            The dict may be a new instance when fix_skill_name_field adds a name.
        """
        fixes = list(colon_fixes)
        if file_type == FileType.SKILL and file_path is not None:
            normalized_dict = fix_skill_name_field(normalized_dict, file_path, fixes)
        tool_fields = {"tools", "disallowedTools", "allowed-tools", "skills"}
        for field_name in tool_fields:
            val = normalized_dict.get(field_name)
            if isinstance(val, list):
                normalized_dict[field_name] = ", ".join(str(x) for x in val)
                fixes.append(
                    f"Converted {field_name} from YAML array to comma-separated string"
                )
        for key, value in normalized_dict.items():
            if key in tool_fields:
                continue
            orig_val = original_data.get(key)
            if orig_val is not None and orig_val != value:
                if isinstance(orig_val, list) and isinstance(value, str):
                    fixes.append(
                        f"Converted {key} from YAML array to comma-separated string"
                    )
                elif (
                    isinstance(orig_val, str)
                    and "\n" in orig_val
                    and "\n" not in str(value)
                ):
                    fixes.append(f"Normalized {key} to single line")
        if re.search(r":\s*[|>][-+]?", frontmatter_text):
            fixes.append("Removed YAML multiline indicators")
        return normalized_dict, fixes

    def _compute_normalized_fixes(
        self,
        original_data: dict[str, YamlValue],
        frontmatter_text: str,
        body: str,
        file_type: FileType,
        file_path: Path | None,
        colon_fixes: list[str],
    ) -> tuple[str, list[str]] | None:
        """Compute normalized frontmatter and list of fixes.

        Returns:
            Tuple of (fixed_content, fixes_list) or None if validation fails.
        """
        model_class = self._get_model_class(file_type)
        if model_class is None:
            return None
        try:
            validated = model_class.model_validate(original_data)
            normalized_dict = validated.model_dump(
                by_alias=True, exclude_none=True, mode="python"
            )
        except ValidationError:
            return (
                (f"---\n{frontmatter_text}\n---\n{body}", colon_fixes)
                if colon_fixes
                else None
            )

        normalized_dict, fixes = self._normalize_tool_fields_and_detect_changes(
            normalized_dict,
            original_data,
            frontmatter_text,
            colon_fixes,
            file_type,
            file_path,
        )
        if not fixes:
            return None
        return f"---\n{_dump_yaml(normalized_dict)}---\n{body}", fixes

    def _apply_fixes(
        self, content: str, file_type: FileType, file_path: Path | None = None
    ) -> tuple[str, list[str]]:
        """Apply auto-fixes to content.

        Args:
            content: File content with frontmatter
            file_type: Type of capability file
            file_path: Optional path to file, used to derive skill name from directory

        Returns:
            Tuple of (fixed_content, list_of_fixes_applied)

        """
        result_content = content
        result_fixes: list[str] = []

        frontmatter_text, _, _ = self._extract_frontmatter(content)
        end_match = (
            re.search(r"\n---\s*\n", content[3:])
            if frontmatter_text is not None
            else None
        )
        if frontmatter_text is None or end_match is None:
            return result_content, result_fixes

        body = content[end_match.end() + 3 :]
        frontmatter_text, original_data, colon_fixes = (
            self._parse_frontmatter_with_colon_fix(frontmatter_text)
        )

        if isinstance(original_data, dict):
            computed = self._compute_normalized_fixes(
                original_data, frontmatter_text, body, file_type, file_path, colon_fixes
            )
            if computed is not None:
                result_content, result_fixes = computed

        return result_content, result_fixes


# ============================================================================
# NAME FORMAT VALIDATOR
# ============================================================================


class NameFormatValidator:
    """Validates skill/agent/command name format.

    Checks for:
    - Lowercase characters only (no uppercase)
    - Hyphens only (no underscores)
    - No leading/trailing hyphens
    - No consecutive hyphens

    Architecture lines 1074-1090, Task T4 lines 518-593
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate name format in frontmatter.

        Args:
            path: Path to file with YAML frontmatter

        Returns:
            ValidationResult with errors for invalid name format
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []
        result: ValidationResult | None = None
        frontmatter_text: str | None = None

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                )
            )
            result = ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        if result is None:
            frontmatter_text, _start_line, _end_line = extract_frontmatter(content)
            if frontmatter_text is None:
                result = ValidationResult(
                    passed=True, errors=errors, warnings=warnings, info=info
                )

        if result is None and frontmatter_text is not None:
            try:
                data = _safe_load_yaml(frontmatter_text)
            except YAMLError:
                result = ValidationResult(
                    passed=True, errors=errors, warnings=warnings, info=info
                )
            else:
                if not isinstance(data, dict):
                    result = ValidationResult(
                        passed=True, errors=errors, warnings=warnings, info=info
                    )
                else:
                    name = data.get("name")
                    if name is None or not isinstance(name, str):
                        result = ValidationResult(
                            passed=True, errors=errors, warnings=warnings, info=info
                        )
                    elif not name:
                        errors.append(
                            ValidationIssue(
                                field="name",
                                severity="error",
                                message="Name field is empty",
                                code=SK003,
                                docs_url=generate_docs_url(SK003),
                                suggestion=f"Provide a non-empty name using lowercase letters, numbers, and hyphens. Schema: {SKILL_FRONTMATTER_SCHEMA_URL}",
                            )
                        )
                        result = ValidationResult(
                            passed=False, errors=errors, warnings=warnings, info=info
                        )
                    else:
                        self._check_name_format(name, errors)
                        result = ValidationResult(
                            passed=len(errors) == 0,
                            errors=errors,
                            warnings=warnings,
                            info=info,
                        )

        return (
            result
            if result is not None
            else ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )
        )

    def _check_name_format(self, name: str, errors: list[ValidationIssue]) -> None:
        """Append format errors for a non-empty name string.

        Args:
            name: The name value to check (must be non-empty str).
            errors: Mutable list to append ValidationIssue objects to.
        """
        # Check for uppercase characters
        if any(c.isupper() for c in name):
            errors.append(
                ValidationIssue(
                    field="name",
                    severity="error",
                    message="Name contains uppercase characters",
                    code=SK001,
                    docs_url=generate_docs_url(SK001),
                    suggestion=f"Use lowercase only (e.g., 'test-skill' not 'Test-Skill'). Schema: {SKILL_FRONTMATTER_SCHEMA_URL}",
                )
            )

        # Check for underscores
        if "_" in name:
            errors.append(
                ValidationIssue(
                    field="name",
                    severity="error",
                    message="Name contains underscores (use hyphens instead)",
                    code=SK002,
                    docs_url=generate_docs_url(SK002),
                    suggestion=f"Replace underscores with hyphens: '{name.replace('_', '-')}'. Schema: {SKILL_FRONTMATTER_SCHEMA_URL}",
                )
            )

        # Check for leading hyphens
        if name.startswith("-"):
            errors.append(
                ValidationIssue(
                    field="name",
                    severity="error",
                    message="Name has leading hyphen",
                    code=SK003,
                    docs_url=generate_docs_url(SK003),
                    suggestion=f"Remove leading hyphen: '{name.lstrip('-')}'. Schema: {SKILL_FRONTMATTER_SCHEMA_URL}",
                )
            )

        # Check for trailing hyphens
        if name.endswith("-"):
            errors.append(
                ValidationIssue(
                    field="name",
                    severity="error",
                    message="Name has trailing hyphen",
                    code=SK003,
                    docs_url=generate_docs_url(SK003),
                    suggestion=f"Remove trailing hyphen: '{name.rstrip('-')}'. Schema: {SKILL_FRONTMATTER_SCHEMA_URL}",
                )
            )

        # Check for consecutive hyphens
        if "--" in name:
            errors.append(
                ValidationIssue(
                    field="name",
                    severity="error",
                    message="Name has consecutive hyphens",
                    code=SK003,
                    docs_url=generate_docs_url(SK003),
                    suggestion=f"Use single hyphens only (e.g., 'test-skill' not 'test--skill'). Schema: {SKILL_FRONTMATTER_SCHEMA_URL}",
                )
            )

        # Validate against full pattern
        if not re.match(NAME_PATTERN, name) and not errors:
            # If we didn't catch specific issues above, add generic pattern error
            errors.append(
                ValidationIssue(
                    field="name",
                    severity="error",
                    message="Name format invalid",
                    code=SK003,
                    docs_url=generate_docs_url(SK003),
                    suggestion=f"Use lowercase letters, numbers, and hyphens only (e.g., 'my-skill-name'). Schema: {SKILL_FRONTMATTER_SCHEMA_URL}",
                )
            )

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            True (name format is auto-fixable on case-sensitive filesystems)
        """
        return True

    def fix(self, path: Path) -> list[str]:
        """Auto-fix name format issues (uppercase, underscores, hyphens).

        Normalizes the frontmatter name field and, for SKILL.md in a skill
        directory, renames the directory to match. Uses a two-step rename on
        case-insensitive filesystems so Test-Skill -> test-skill works.

        Args:
            path: Path to file to fix

        Returns:
            List of fix descriptions, or empty if nothing was fixed
        """
        fixes = self._try_fix_name_format(path)
        return fixes if fixes is not None else []

    def _read_name_and_frontmatter(
        self, path: Path
    ) -> tuple[str, dict[str, YamlValue], str] | None:
        """Read file, parse frontmatter, extract name.

        Returns:
            Tuple of (content, data, name) or None if any step fails.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return None
        fm_text, _start, _end = extract_frontmatter(content)
        if fm_text is None:
            return None
        try:
            data = _safe_load_yaml(fm_text)
        except YAMLError:
            return None
        if not isinstance(data, dict):
            return None
        name = data.get("name")
        if not isinstance(name, str) or not name:
            return None
        return content, data, name

    def _try_fix_name_format(self, path: Path) -> list[str] | None:
        """Attempt to fix name format.

        Returns:
            List of fix descriptions if fixes were applied, None otherwise.
        """
        parsed = self._read_name_and_frontmatter(path)
        if parsed is None:
            return None
        content, data, name = parsed

        fixed_name = _normalize_skill_name(name)
        if (
            not fixed_name
            or fixed_name == name
            or not re.match(NAME_PATTERN, fixed_name)
        ):
            return None

        data["name"] = fixed_name
        end_match = re.search(r"\n---\s*\n", content[3:])
        body = content[end_match.end() + 3 :] if end_match else ""
        new_content = f"---\n{_dump_yaml(data)}{body}"
        try:
            path.write_text(new_content, encoding="utf-8")
        except OSError:
            return None

        fixes = [f"Normalized name from '{name}' to '{fixed_name}'"]
        # Rename skill directory to match (two-step on case-insensitive filesystems)
        if path.name == "SKILL.md" and path.parent.name != fixed_name:
            skill_dir = path.parent
            parent_dir = skill_dir.parent
            try:
                temp_name = f"{skill_dir.name}.fmtemp"
                skill_dir.rename(parent_dir / temp_name)
                (parent_dir / temp_name).rename(parent_dir / fixed_name)
                fixes.append(f"Renamed directory to '{fixed_name}'")
            except OSError:
                pass  # Directory rename best-effort; frontmatter fix already applied

        return fixes


# ============================================================================
# DESCRIPTION VALIDATOR
# ============================================================================


class DescriptionValidator:
    """Validates description field quality.

    Checks:
    - Minimum length (20 characters) — SKILL and AGENT files only
    - Presence of trigger phrases — SKILL files only

    Both checks produce warnings, not errors, since description quality is subjective.
    Commands have different frontmatter schemas and do not require trigger phrases.

    Architecture lines 1092-1113, Task T5 lines 602-672
    """

    def __init__(self, file_type: FileType = FileType.SKILL) -> None:
        """Initialize with file type to scope validation checks.

        Args:
            file_type: The type of file being validated. SK004 (too short) applies
                to SKILL and AGENT files. SK005 (missing triggers) applies to SKILL only.
        """
        self.file_type = file_type

    def validate(self, path: Path) -> ValidationResult:
        """Validate description field in frontmatter.

        Args:
            path: Path to file with YAML frontmatter

        Returns:
            ValidationResult with warnings for description quality issues

        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        frontmatter_text, _start_line, _end_line = extract_frontmatter(content)
        if frontmatter_text is None:
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        try:
            data = _safe_load_yaml(frontmatter_text)
        except YAMLError:
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        if not isinstance(data, dict):
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        description = data.get("description")
        if description is None or not isinstance(description, str):
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        self._check_description_quality(description, warnings)
        return ValidationResult(
            passed=len(errors) == 0, errors=errors, warnings=warnings, info=info
        )

    def _check_description_quality(
        self, description: str, warnings: list[ValidationIssue]
    ) -> None:
        """Append warnings for description length and trigger phrases."""
        if (
            self.file_type in {FileType.SKILL, FileType.AGENT}
            and len(description) < MIN_DESCRIPTION_LENGTH
        ):
            warnings.append(
                ValidationIssue(
                    field="description",
                    severity="warning",
                    message=f"Description too short (minimum {MIN_DESCRIPTION_LENGTH} characters, got {len(description)})",
                    code=SK004,
                    docs_url=generate_docs_url(SK004),
                    suggestion="Run /plugin-creator:write-frontmatter-description to generate an optimized description with proper length and trigger phrases",
                )
            )
        if self.file_type == FileType.SKILL:
            description_lower = description.lower()
            if not any(
                phrase in description_lower for phrase in REQUIRED_TRIGGER_PHRASES
            ):
                warnings.append(
                    ValidationIssue(
                        field="description",
                        severity="warning",
                        message="Description missing trigger phrases",
                        code=SK005,
                        docs_url=generate_docs_url(SK005),
                        suggestion=f"Required trigger phrases: {', '.join(REQUIRED_TRIGGER_PHRASES)}. Run /plugin-creator:write-frontmatter-description to generate a compliant description",
                    )
                )

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (description quality requires human-written content)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix description issues (not supported).

        Args:
            path: Path to file to fix

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Description quality cannot be auto-fixed
        """
        raise NotImplementedError(
            "Description validation cannot be auto-fixed. Writing quality descriptions requires human judgment."
        )


# ============================================================================
# COMPLEXITY VALIDATOR (TOKEN-BASED)
# ============================================================================


class ComplexityValidator:
    """Validates skill complexity using token counting.

    Measures skill complexity by counting tokens in body content (excluding
    frontmatter) using tiktoken. Provides more accurate complexity measurement
    than line counting since it reflects actual Claude processing cost.

    Architecture lines 1115-1168, Task T6 lines 685-797
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate skill complexity using token counting.

        Args:
            path: Path to SKILL.md file

        Returns:
            ValidationResult with warnings/errors based on token thresholds

        Note:
            Multiple early returns are necessary to handle various skip conditions gracefully.
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        # Only validate SKILL.md files
        if path.name != "SKILL.md":
            # Not a skill file - skip validation
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        # Read file
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        # Split frontmatter and body
        frontmatter_text, _start_line, _end_line = extract_frontmatter(content)

        # Calculate body content (everything after frontmatter)
        # Note: re module already imported at module level (line 27)
        if frontmatter_text is not None:
            # Find end of frontmatter
            end_match = re.search(r"\n---\s*\n", content[3:])
            body = content[end_match.end() + 3 :] if end_match else content
        else:
            # No frontmatter - entire file is body
            body = content

        # Count tokens using tiktoken
        body_tokens = self._count_tokens(body, errors, warnings, info)

        # Check against thresholds
        if body_tokens > TOKEN_ERROR_THRESHOLD:
            # CRITICAL: Must split skill
            errors.append(
                ValidationIssue(
                    field="complexity",
                    severity="error",
                    message=f"Skill body exceeds token limit ({body_tokens} tokens > {TOKEN_ERROR_THRESHOLD} threshold)",
                    code=SK007,
                    docs_url=generate_docs_url(SK007),
                    suggestion="Run /plugin-creator:refactor-skill to split into multiple smaller skills",
                )
            )
        elif body_tokens > TOKEN_WARNING_THRESHOLD:
            # WARNING: Larger than Anthropic's official skills
            warnings.append(
                ValidationIssue(
                    field="complexity",
                    severity="warning",
                    message=f"Skill body is large ({body_tokens} tokens > {TOKEN_WARNING_THRESHOLD} threshold)",
                    code=SK006,
                    docs_url=generate_docs_url(SK006),
                    suggestion="This skill is larger than Anthropic's official skills. Review whether content can be moved to references/ or if the skill covers multiple domains that could be separated",
                )
            )

        # Pass if no errors (warnings don't fail validation)
        passed = len(errors) == 0
        return ValidationResult(
            passed=passed, errors=errors, warnings=warnings, info=info
        )

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (complexity requires content restructuring)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix complexity issues (not supported).

        Args:
            path: Path to file to fix

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Complexity issues cannot be auto-fixed
        """
        raise NotImplementedError(
            "Complexity validation cannot be auto-fixed. "
            "Reducing complexity requires content restructuring and splitting skills."
        )

    def _count_tokens(
        self,
        text: str,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
        info: list[ValidationIssue],
    ) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text content to count tokens in
            errors: List to append errors to (unused; tiktoken fails at import if unavailable)
            warnings: Warnings list (unused but required for signature consistency)
            info: Info list (unused but required for signature consistency)

        Returns:
            Token count.
        """
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))


# ============================================================================
# MARKDOWN TOKEN COUNTER (General markdown files)
# ============================================================================


class MarkdownTokenCounter:
    """Counts tokens in general markdown files (CLAUDE.md, references, etc.).

    Unlike ComplexityValidator which only processes SKILL.md files and applies
    skill-specific threshold checks, this counter works on any markdown file.
    It reports total and body token counts as info messages without applying
    skill-specific thresholds or triggering errors/warnings.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Count tokens in a markdown file and report as info.

        Args:
            path: Path to markdown file

        Returns:
            ValidationResult with token count info (always passes)
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        # Read file
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=FM002,
                    docs_url=generate_docs_url(FM002),
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        # Split frontmatter and body
        frontmatter_text, _start_line, _end_line = extract_frontmatter(content)

        if frontmatter_text is not None:
            end_match = re.search(r"\n---\s*\n", content[3:])
            body = content[end_match.end() + 3 :] if end_match else content
        else:
            body = content

        # Count tokens
        total_tokens = self._count_tokens(content)
        body_tokens = self._count_tokens(body)
        frontmatter_tokens = total_tokens - body_tokens

        info.append(
            ValidationIssue(
                field="token-count",
                severity="info",
                message=(
                    f"Total: {total_tokens} tokens (frontmatter: {frontmatter_tokens}, body: {body_tokens})"
                ),
                code=ErrorCode.TC001,
            )
        )

        return ValidationResult(
            passed=True, errors=errors, warnings=warnings, info=info
        )

    def count_file_tokens(self, path: Path, *, body_only: bool = False) -> int | None:
        """Count tokens in a file for programmatic use.

        Args:
            path: Path to markdown file
            body_only: When True, strip frontmatter and count only the body.
                Matches what ComplexityValidator measures for threshold comparisons.

        Returns:
            Token count (body or total), or None if counting failed
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return None

        if body_only:
            frontmatter_text, _start, _end = extract_frontmatter(content)
            if frontmatter_text is not None:
                end_match = re.search(r"\n---\s*\n", content[3:])
                text = content[end_match.end() + 3 :] if end_match else content
            else:
                text = content
            return self._count_tokens(text)

        return self._count_tokens(content)

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (token counting is read-only)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix not supported for token counting.

        Args:
            path: Path to file

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Token counting cannot be auto-fixed
        """
        raise NotImplementedError("Token counting is read-only, no fixes to apply.")

    @staticmethod
    def _count_tokens(text: str) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text content to count tokens in

        Returns:
            Token count.
        """
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))


# ============================================================================
# PLUGIN REGISTRATION VALIDATOR
# ============================================================================


def _git_file_has_execute_bit(file_path: Path) -> bool | None:
    """Check if a file has the execute bit in Git's index or HEAD.

    Uses Git's tracked mode (100755 = executable, 100644 = not) so validation
    is consistent across platforms. On Windows, os.access(X_OK) is unreliable;
    checking Git ensures plugins that pass on Windows will also pass on Linux.

    Uses GitPython (project dependency) for consistency with other scripts.

    Args:
        file_path: Absolute path to the file.

    Returns:
        True if executable in Git, False if not, None if not in a Git repo or
        file is untracked.
    """
    if not file_path.exists():
        return None

    try:
        repo = Repo(file_path.resolve().parent, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return None

    if repo.working_tree_dir is None:
        return None

    working_dir = Path(repo.working_tree_dir)
    try:
        rel = file_path.resolve().relative_to(working_dir)
    except ValueError:
        return None

    rel_str = str(rel).replace("\\", "/")

    # Prefer index (staged/unstaged); fall back to HEAD
    entry = repo.index.entries.get(entry_key(rel_str, 0))
    if entry is not None:
        return entry.mode == GIT_MODE_EXECUTABLE

    try:
        blob = repo.head.commit.tree[rel_str]
    except KeyError:
        return None
    else:
        return blob.mode == GIT_MODE_EXECUTABLE


def _get_git_remote_url(repo_dir: Path) -> str | None:
    """Extract the remote URL for the git repository at repo_dir.

    Args:
        repo_dir: Root of a git repository (directory containing .git/).

    Returns:
        Remote URL string with .git suffix stripped, or None if unavailable.
    """
    git_path = shutil.which("git")
    if not git_path:
        return None

    try:
        result = subprocess.run(
            [git_path, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=str(repo_dir),
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    remote_url = result.stdout.strip()
    if not remote_url:
        return None

    return remote_url.removesuffix(".git")


def _get_git_author() -> dict[str, str] | None:
    """Extract author info from git config.

    Returns:
        Dict with 'name' and optionally 'email', or None if unavailable.
    """
    git_path = shutil.which("git")
    if not git_path:
        return None

    try:
        name_result = subprocess.run(
            [git_path, "config", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    name = name_result.stdout.strip()
    if not name:
        return None

    try:
        email_result = subprocess.run(
            [git_path, "config", "user.email"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"name": name}

    email = email_result.stdout.strip() if email_result.returncode == 0 else None
    author: dict[str, str] = {"name": name}
    if email:
        author["email"] = email
    return author


def _generate_plugin_metadata(plugin_dir: Path) -> dict[str, YamlValue]:
    """Generate plugin.json metadata from git and file structure.

    Args:
        plugin_dir: Path to the plugin directory.

    Returns:
        Dict with repository, homepage, and author fields populated from git.
        Empty dict if git is unavailable or not in a repo.
    """
    metadata: dict[str, YamlValue] = {}

    current = plugin_dir
    while current != current.parent:
        if (current / ".git").exists():
            repo_url = _get_git_remote_url(current)
            if repo_url:
                metadata["repository"] = repo_url
                relative_path = plugin_dir.relative_to(current)
                metadata["homepage"] = f"{repo_url}/tree/main/{relative_path}"
            break
        current = current.parent

    author = _get_git_author()
    if author:
        metadata["author"] = author

    return metadata


def _find_actual_capabilities(
    plugin_dir: Path,
) -> tuple[set[Path], set[Path], set[Path]]:
    """Find all actual capability files in a plugin directory.

    Args:
        plugin_dir: Path to the plugin directory.

    Returns:
        Tuple of (actual_skills, actual_agents, actual_commands) as sets of
        paths relative to plugin_dir.
    """
    actual_skills: set[Path] = set()
    actual_agents: set[Path] = set()
    actual_commands: set[Path] = set()

    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        actual_skills = {
            d.relative_to(plugin_dir)
            for d in skills_dir.glob("*/")
            if d.is_dir() and (d / "SKILL.md").exists()
        }

    agents_dir = plugin_dir / "agents"
    if agents_dir.is_dir():
        actual_agents = {
            f.relative_to(plugin_dir)
            for f in agents_dir.glob("*.md")
            if f.name not in {"CLAUDE.md", "README.md"}
        }

    commands_dir = plugin_dir / "commands"
    if commands_dir.is_dir():
        actual_commands = {
            f.relative_to(plugin_dir)
            for f in commands_dir.glob("*.md")
            if f.name not in {"CLAUDE.md", "README.md"}
        }

    return actual_skills, actual_agents, actual_commands


def _parse_registered_paths(
    plugin_config: dict[str, YamlValue], plugin_dir: Path, field: str
) -> set[Path]:
    """Parse registered capability paths from a plugin.json field.

    Args:
        plugin_config: Loaded plugin.json content.
        plugin_dir: Plugin directory path.
        field: Field name (skills, agents, commands).

    Returns:
        Set of registered paths relative to plugin_dir.
    """
    registered: set[Path] = set()

    if field not in plugin_config:
        return registered

    value = plugin_config[field]

    if isinstance(value, str):
        value_path = plugin_dir / value.lstrip("./")
        if value_path.is_dir():
            registered.update(
                f.relative_to(plugin_dir)
                for f in value_path.glob("*.md")
                if f.name not in {"CLAUDE.md", "README.md"}
            )
        else:
            registered.add(Path(value.lstrip("./")))
    elif isinstance(value, list):
        registered.update(Path(item.lstrip("./")) for item in value)

    return registered


def _sk009_message(unlisted: set[Path]) -> str:
    """Build the SK009 info message based on unlisted disk skills.

    Args:
        unlisted: Skills present on disk but absent from the explicit skills array.

    Returns:
        Human-readable message describing the manual-selection state.
    """
    if unlisted:
        paths = ", ".join(sorted(f"./{s}" for s in unlisted))
        return (
            "Plugin uses manual skill selection — new skills added to skills/ "
            f"will not be auto-loaded. The following skills are present on disk but not listed: {paths}"
        )
    return "Plugin uses manual skill selection — all skills/ are explicitly registered."


class PluginRegistrationValidator:
    """Validates capability registration against plugin.json.

    Checks that all capability files are registered and all registered paths
    exist. Also validates plugin.json metadata against git-derived values.

    Open/Closed: new capability types can be added by extending
    _find_actual_capabilities() and adding entries in validate().
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate registration and metadata for the plugin containing path.

        Args:
            path: Path to a file or directory within the plugin.

        Returns:
            ValidationResult with registration and metadata issues.
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        plugin_dir = self._find_plugin_dir(path)
        if plugin_dir is None:
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        plugin_json_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if not plugin_json_path.exists():
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        try:
            with plugin_json_path.open() as f:
                plugin_config = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(
                ValidationIssue(
                    field="plugin.json",
                    severity="error",
                    message=f"Invalid JSON: {e}",
                    code=PL002,
                    docs_url=generate_docs_url(PL002),
                    suggestion="Fix JSON syntax errors",
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        # Registration checks
        actual_skills, actual_agents, actual_commands = _find_actual_capabilities(
            plugin_dir
        )
        registered_skills = _parse_registered_paths(plugin_config, plugin_dir, "skills")
        registered_agents = _parse_registered_paths(plugin_config, plugin_dir, "agents")
        registered_commands = _parse_registered_paths(
            plugin_config, plugin_dir, "commands"
        )

        # When plugin.json has no ``skills`` field at all, the plugin relies
        # entirely on Claude Code's auto-discovery of the ./skills/ directory.
        # Standard-path skills (under ./skills/) are auto-discovered and need
        # no explicit registration — suppress PR001 for them in this case.
        # When an explicit ``skills`` array is present (even if empty), the
        # plugin has opted into explicit registration and unregistered
        # standard-path skills should still be flagged.
        warnings.extend(
            ValidationIssue(
                field="plugin.json",
                severity="warning",
                message=f"Skill '{orphan}' exists but is not registered (relies on default discovery)",
                code=PR001,
                docs_url=generate_docs_url(PR001),
                suggestion=f"Add './{orphan}' to the skills array in plugin.json",
            )
            for orphan in actual_skills - registered_skills
            if "skills" in plugin_config or not str(orphan).startswith("skills/")
        )

        warnings.extend(
            ValidationIssue(
                field="plugin.json",
                severity="warning",
                message=f"Agent '{orphan}' exists but is not registered",
                code=PR001,
                docs_url=generate_docs_url(PR001),
                suggestion=f"Add './{orphan}' to the agents array in plugin.json",
            )
            for orphan in actual_agents - registered_agents
        )

        warnings.extend(
            ValidationIssue(
                field="plugin.json",
                severity="warning",
                message=f"Command '{orphan}' exists but is not registered",
                code=PR001,
                docs_url=generate_docs_url(PR001),
                suggestion=f"Add './{orphan}' to the commands array in plugin.json",
            )
            for orphan in actual_commands - registered_commands
        )

        errors.extend(
            ValidationIssue(
                field="plugin.json",
                severity="error",
                message=f"Registered skill '{ref}' does not exist",
                code=PR002,
                docs_url=generate_docs_url(PR002),
                suggestion=f"Remove from plugin.json or create {ref}/SKILL.md",
            )
            for ref in registered_skills
            if not (plugin_dir / ref / "SKILL.md").exists()
        )

        errors.extend(
            ValidationIssue(
                field="plugin.json",
                severity="error",
                message=f"Registered agent '{ref}' does not exist",
                code=PR002,
                docs_url=generate_docs_url(PR002),
                suggestion=f"Remove from plugin.json or create {ref}",
            )
            for ref in registered_agents
            if not (plugin_dir / ref).exists()
        )

        errors.extend(
            ValidationIssue(
                field="plugin.json",
                severity="error",
                message=f"Registered command '{ref}' does not exist",
                code=PR002,
                docs_url=generate_docs_url(PR002),
                suggestion=f"Remove from plugin.json or create {ref}",
            )
            for ref in registered_commands
            if not (plugin_dir / ref).exists()
        )

        errors.extend(
            ValidationIssue(
                field="plugin.json",
                severity="error",
                message=(
                    f"Registered command '{ref}' is a skill directory (contains SKILL.md). "
                    f"Skill directories must not be listed under 'commands'."
                ),
                code=PR005,
                docs_url=generate_docs_url(PR005),
                suggestion=f"Move '{ref}' from the 'commands' array to the 'skills' array in plugin.json",
            )
            for ref in registered_commands
            if (plugin_dir / ref).is_dir() and (plugin_dir / ref / "SKILL.md").exists()
        )

        # SK009 — manual skill selection mode (informational)
        if "skills" in plugin_config:
            info.append(
                ValidationIssue(
                    field="plugin.json",
                    severity="info",
                    message=_sk009_message(actual_skills - registered_skills),
                    code=SK009,
                    docs_url=generate_docs_url(SK009),
                    suggestion=(
                        "To switch to auto-discovery mode, remove the 'skills' field from "
                        "plugin.json. Claude Code will discover all skills under ./skills/ "
                        "automatically."
                    ),
                )
            )

        # Metadata checks (informational)
        git_metadata = _generate_plugin_metadata(plugin_dir)
        if git_metadata:
            missing = [
                k
                for k in ("repository", "homepage", "author")
                if k not in plugin_config and k in git_metadata
            ]
            if missing:
                suggestion_json = json.dumps(
                    {k: git_metadata[k] for k in missing}, indent=2
                )
                info.append(
                    ValidationIssue(
                        field="plugin.json",
                        severity="info",
                        message=f"Metadata could be populated from git: {', '.join(missing)}",
                        code=PR003,
                        docs_url=generate_docs_url(PR003),
                        suggestion=f"Add to plugin.json:\n{suggestion_json}",
                    )
                )

            if (
                "repository" in plugin_config
                and "repository" in git_metadata
                and plugin_config["repository"] != git_metadata["repository"]
            ):
                warnings.append(
                    ValidationIssue(
                        field="plugin.json",
                        severity="warning",
                        message=(
                            f"Repository URL mismatch: plugin.json has "
                            f"'{plugin_config['repository']}', git has '{git_metadata['repository']}'"
                        ),
                        code=PR004,
                        docs_url=generate_docs_url(PR004),
                        suggestion=f"Update repository to: {git_metadata['repository']}",
                    )
                )

        return ValidationResult(
            passed=len(errors) == 0, errors=errors, warnings=warnings, info=info
        )

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (registration issues require manual plugin.json edits).
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix registration issues (not supported).

        Args:
            path: Path to file or directory.

        Raises:
            NotImplementedError: Registration issues require manual fixes.
        """
        raise NotImplementedError(
            "Plugin registration issues require manual edits to plugin.json."
        )

    def _find_plugin_dir(self, path: Path) -> Path | None:
        """Find the plugin directory containing .claude-plugin/plugin.json.

        Args:
            path: Path to start searching from.

        Returns:
            Plugin directory path, or None if not found.
        """
        search_path = path.parent if path.is_file() else path
        for parent in [search_path, *search_path.parents]:
            if (parent / ".claude-plugin" / "plugin.json").exists():
                return parent
        return None


# ============================================================================
# PLUGIN STRUCTURE VALIDATOR (CLAUDE CLI INTEGRATION)
# ============================================================================


class PluginStructureValidator:
    """Validates plugin structure using claude CLI.

    Integrates with external `claude plugin validate` CLI command for
    plugin.json validation. Gracefully handles cases where claude CLI
    is not available by skipping validation.

    Architecture lines 1258-1286, Task T9 lines 1034-1124
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate plugin structure using claude CLI.

        Args:
            path: Path to plugin directory or file within plugin

        Returns:
            ValidationResult with errors from claude CLI or info if skipped
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        # Find plugin directory (contains .claude-plugin/plugin.json)
        plugin_dir = self._find_plugin_directory(path)
        if plugin_dir is None:
            # Not a plugin directory - skip validation
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        # Validate plugin.json JSON syntax locally before delegating to claude CLI.
        # Catches encoding/line-ending issues that may cause claude to fail inconsistently.
        plugin_json_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if plugin_json_path.exists():
            json_error = self._validate_plugin_json_syntax(plugin_json_path)
            if json_error is not None:
                errors.append(
                    ValidationIssue(
                        field="plugin.json",
                        severity="error",
                        message=json_error,
                        code=PL002,
                        docs_url=generate_docs_url(PL002),
                        suggestion=f"plugin.json must be valid JSON. Schema: {PLUGIN_MANIFEST_SCHEMA_URL}",
                    )
                )
                return ValidationResult(
                    passed=False, errors=errors, warnings=warnings, info=info
                )

        # Skip claude plugin validate when running inside a Claude Code session
        # (nested CLI invocations are blocked by Anthropic safety measure).
        if _should_skip_claude_validate():
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message="Skipping claude plugin validate (nested CLI sessions not supported)",
                    code=PL001,
                    docs_url=generate_docs_url(PL001),
                )
            )
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        # Check if claude CLI is available and get full path
        claude_path = self._get_claude_path()
        if claude_path is None:
            # Claude not available - skip with info message
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message="Claude CLI not available, skipping plugin structure validation",
                    code=PL001,
                    docs_url=generate_docs_url(PL001),
                    suggestion="Install Claude Code to enable plugin validation",
                )
            )
            return ValidationResult(
                passed=True, errors=errors, warnings=warnings, info=info
            )

        # On Windows, ensure CLAUDE_CODE_GIT_BASH_PATH is set if git-bash can be found
        _git_bash_path()

        # Run claude plugin validate
        try:
            result = subprocess.run(
                [claude_path, "plugin", "validate", str(plugin_dir)],
                capture_output=True,
                text=True,
                timeout=CLAUDE_TIMEOUT,
                check=False,
            )

            # Parse output for errors
            if result.returncode != 0:
                # Validation failed - parse errors from output
                self._parse_claude_errors(
                    result.stdout, result.stderr, errors, warnings, info
                )

        except subprocess.TimeoutExpired:
            errors.append(
                ValidationIssue(
                    field="(plugin-validation)",
                    severity="error",
                    message=f"Claude plugin validation timed out after {CLAUDE_TIMEOUT} seconds",
                    code=PL002,
                    docs_url=generate_docs_url(PL002),
                )
            )
        except FileNotFoundError:
            # Claude CLI not found (should be caught by _is_claude_available)
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message="Claude CLI not found in PATH",
                    code=PL001,
                    docs_url=generate_docs_url(PL001),
                    suggestion="Install Claude Code to enable plugin validation",
                )
            )
        except OSError as e:
            # Subprocess failed to run (permissions, env, etc.) — skip, do not fail
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message=f"Claude CLI could not run; skipping plugin structure validation: {e}",
                    code=PL001,
                    docs_url=generate_docs_url(PL001),
                )
            )

        # Pass if no errors (warnings/info don't fail validation)
        passed = len(errors) == 0
        return ValidationResult(
            passed=passed, errors=errors, warnings=warnings, info=info
        )

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (plugin structure issues require manual structural changes)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix plugin structure issues (not supported).

        Args:
            path: Path to plugin directory to fix

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Plugin structure validation cannot be auto-fixed
        """
        raise NotImplementedError(
            "Plugin structure validation cannot be auto-fixed. "
            "Structural issues require manual changes to plugin.json and component files."
        )

    def _get_claude_path(self) -> str | None:
        """Get full path to claude CLI if available.

        Returns:
            Full path to claude executable, or None if not found
        """
        return shutil.which("claude")

    def _find_plugin_directory(self, path: Path) -> Path | None:
        """Find plugin directory containing .claude-plugin/plugin.json.

        Args:
            path: Path to file or directory within plugin

        Returns:
            Path to plugin directory, or None if not found
        """
        # If path is a file, start from parent directory
        search_path = path.parent if path.is_file() else path

        # Search up the directory tree for .claude-plugin/plugin.json
        for parent in [search_path, *search_path.parents]:
            plugin_json = parent / ".claude-plugin" / "plugin.json"
            if plugin_json.exists():
                return parent

        return None

    def _validate_plugin_json_syntax(self, plugin_json_path: Path) -> str | None:
        """Validate plugin.json is parseable JSON. Catches syntax/encoding issues.

        Args:
            plugin_json_path: Path to plugin.json file.

        Returns:
            None if valid; otherwise human-readable error message string.
        """
        try:
            with Path(plugin_json_path).open(encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            return f"Invalid JSON syntax in plugin.json: {e}"
        except OSError as e:
            return f"Cannot read plugin.json: {e}"
        else:
            return None

    def _is_claude_startup_failure(self, output: str) -> bool:
        """Return True if output indicates claude failed to start (env/runtime), not validation.

        We must not fail validation when claude cannot run (e.g. git-bash not found on
        Windows). Only fail when claude ran and reported plugin structure errors.
        """
        startup_patterns = (
            r"requires git-bash",
            r"CLAUDE_CODE_GIT_BASH_PATH",
            r"not in PATH",
        )
        combined = output.lower()
        return any(re.search(p, combined, re.IGNORECASE) for p in startup_patterns)

    def _parse_claude_errors(
        self,
        stdout: str,
        stderr: str,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
        info: list[ValidationIssue],
    ) -> None:
        """Parse claude CLI output for validation errors.

        Args:
            stdout: Standard output from claude CLI
            stderr: Standard error from claude CLI
            errors: List to append error issues to
            warnings: List to append warning issues to
            info: List to append info issues to
        """
        # Combine stdout and stderr for parsing
        output = stdout + "\n" + stderr

        # If claude failed to start (env/runtime), skip — do not fail validation
        if self._is_claude_startup_failure(output):
            detail = (stdout.strip() + "\n" + stderr.strip())[:300] or "(no output)"
            info.append(
                ValidationIssue(
                    field="(plugin-structure)",
                    severity="info",
                    message="Claude CLI could not start; skipping plugin structure validation",
                    code=PL001,
                    docs_url=generate_docs_url(PL001),
                    suggestion=detail,
                )
            )
            return

        # Map claude CLI error patterns to error codes
        error_patterns = {
            PL001: r"missing.*plugin\.json|plugin\.json.*not found",
            PL002: r"invalid.*json|json.*syntax|parse.*error",
            PL003: r"missing.*required.*field.*name|name.*required",
            PL004: r"path.*must.*start.*with.*\./|invalid.*path.*format",
            PL005: r"file.*does not exist|referenced.*file.*not found|missing.*file",
        }

        # Check for each error pattern
        for code, pattern in error_patterns.items():
            if re.search(pattern, output, re.IGNORECASE):
                errors.append(
                    ValidationIssue(
                        field="plugin.json",
                        severity="error",
                        message=self._get_error_message(code, output),
                        code=code,
                        docs_url=generate_docs_url(code),
                        suggestion=self._get_error_suggestion(code),
                    )
                )

        # If no specific error pattern matched but validation failed, add generic error
        # Include actual CLI output for diagnosis (truncate to avoid huge messages)
        if not errors:
            detail = (stdout.strip() + "\n" + stderr.strip())[:500] or "(no output)"
            errors.append(
                ValidationIssue(
                    field="plugin.json",
                    severity="error",
                    message="Plugin validation failed (see claude CLI output for details)",
                    code=PL002,
                    docs_url=generate_docs_url(PL002),
                    suggestion=f"Run 'claude plugin validate <plugin-dir>'. CLI output: {detail}",
                )
            )

    def _get_error_message(self, code: str, output: str) -> str:
        """Get human-readable error message for code.

        Args:
            code: Error code (PL001-PL005)
            output: CLI output containing error details

        Returns:
            Human-readable error message
        """
        lines = output.split("\n")
        for text_line in lines:
            stripped_line = text_line.strip()
            if (
                stripped_line
                and not stripped_line.startswith("#")
                and any(
                    kw in stripped_line.lower()
                    for kw in ["error", "missing", "invalid", "required", "not found"]
                )
            ):
                return stripped_line[:200]

        fallbacks: dict[str, str] = {
            "PL001": "Missing plugin.json file in .claude-plugin/ directory",
            "PL002": "Invalid JSON syntax in plugin.json",
            "PL003": "Missing required field 'name' in plugin.json",
            "PL004": "Component path does not start with './'",
            "PL005": "Referenced component file does not exist",
        }
        return fallbacks.get(str(code), "Plugin structure validation failed")

    def _get_error_suggestion(self, code: str) -> str:
        """Get suggestion for fixing error.

        Args:
            code: Error code (PL001-PL005)

        Returns:
            Human-readable suggestion for fixing the error
        """
        match code:
            case "PL001":
                return "Create .claude-plugin/plugin.json with required fields"
            case "PL002":
                return "Validate JSON syntax: python3 -m json.tool .claude-plugin/plugin.json"
            case "PL003":
                return 'Add \'name\' field to plugin.json: {"name": "plugin-name"}'
            case "PL004":
                return "Ensure all component paths start with './' (e.g., './skills/skill-name/')"
            case "PL005":
                return "Verify all referenced files exist at specified paths"
            case _:
                return "Run 'claude plugin validate' for detailed error information"


# ============================================================================
# HOOK VALIDATOR
# ============================================================================


class HookValidator:
    """Validates Claude Code hooks.json configuration files.

    Validates JSON structure, event types, and hook entries.
    Hook scripts themselves are language-agnostic (any executable) and validated
    by their respective language linters (biome, ruff, shellcheck, etc.).
    """

    VALID_EVENT_TYPES: ClassVar[frozenset[str]] = frozenset(
        {
            "PreToolUse",
            "PermissionRequest",
            "PostToolUse",
            "PostToolUseFailure",
            "Notification",
            "UserPromptSubmit",
            "Stop",
            "SubagentStart",
            "SubagentStop",
            "PreCompact",
            "Setup",
            "SessionStart",
            "SessionEnd",
        }
    )

    VALID_HOOK_TYPES: ClassVar[frozenset[str]] = frozenset({"command", "prompt"})

    def validate(self, path: Path) -> ValidationResult:
        """Validate a hooks.json configuration file.

        Args:
            path: Path to hooks.json

        Returns:
            ValidationResult with errors/warnings for hook issues
        """
        return self._validate_hook_config(path)

    def can_fix(self) -> bool:
        """Check if validator supports auto-fixing.

        Returns:
            False (hook validation cannot be auto-fixed)
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix hook issues (not supported).

        Args:
            path: Path to hook file to fix

        Returns:
            Never returns (always raises)

        Raises:
            NotImplementedError: Hook validation cannot be auto-fixed
        """
        raise NotImplementedError("Hook validation cannot be auto-fixed.")

    def _validate_hook_config(self, path: Path) -> ValidationResult:
        """Validate hooks.json structure and contents.

        Checks:
        1. Valid JSON (HK001 if invalid)
        2. Top-level has "hooks" key that is a dict (HK001 if not)
        3. Each key in hooks is a valid event type (HK002 if not)
        4. Each event type value is a list of hook groups (HK003)
        5. Each hook group has "hooks" key with list of entries (HK003)
        6. Each entry has valid "type" field (HK003)
        7. "command" type requires "command" field (HK003)
        8. "prompt" type requires "prompt" field (HK003)

        Args:
            path: Path to hooks.json file

        Returns:
            ValidationResult with errors for structural issues
        """
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        info: list[ValidationIssue] = []

        # Read and parse JSON
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(
                ValidationIssue(
                    field="(file)",
                    severity="error",
                    message=f"Could not read file: {e}",
                    code=HK001,
                    docs_url=generate_docs_url(HK001),
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            errors.append(
                ValidationIssue(
                    field="(json)",
                    severity="error",
                    message=f"Invalid JSON syntax: {e}",
                    code=HK001,
                    docs_url=generate_docs_url(HK001),
                    suggestion="Fix JSON syntax errors in hooks.json",
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        # Check top-level structure
        if not isinstance(data, dict) or "hooks" not in data:
            errors.append(
                ValidationIssue(
                    field="hooks",
                    severity="error",
                    message="Missing required top-level 'hooks' key",
                    code=HK001,
                    docs_url=generate_docs_url(HK001),
                    suggestion='hooks.json must have structure: {"hooks": {...}}',
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        hooks_obj = data["hooks"]
        if not isinstance(hooks_obj, dict):
            errors.append(
                ValidationIssue(
                    field="hooks",
                    severity="error",
                    message="'hooks' value must be an object",
                    code=HK001,
                    docs_url=generate_docs_url(HK001),
                )
            )
            return ValidationResult(
                passed=False, errors=errors, warnings=warnings, info=info
            )

        # Validate each event type
        for event_type, hook_groups in hooks_obj.items():
            if event_type not in self.VALID_EVENT_TYPES:
                errors.append(
                    ValidationIssue(
                        field=f"hooks.{event_type}",
                        severity="error",
                        message=f"Invalid event type: '{event_type}'",
                        code=HK002,
                        docs_url=generate_docs_url(HK002),
                        suggestion=f"Valid event types: {', '.join(sorted(self.VALID_EVENT_TYPES))}",
                    )
                )
                continue

            # Each event type value must be a list of hook groups
            if not isinstance(hook_groups, list):
                errors.append(
                    ValidationIssue(
                        field=f"hooks.{event_type}",
                        severity="error",
                        message=f"Event type '{event_type}' value must be an array of hook groups",
                        code=HK003,
                        docs_url=generate_docs_url(HK003),
                    )
                )
                continue

            # Validate each hook group
            for group_idx, group in enumerate(hook_groups):
                self._validate_hook_group(group, event_type, group_idx, errors)

        # Validate that file-path command references actually exist and are executable.
        # HK004/HK005 issues are appended directly to the combined errors list so that
        # missing-script warnings surface in the same result as structural errors.
        self.validate_hook_script_references_in_hooks_dict(
            hooks_obj, path.parent, errors
        )

        passed = len(errors) == 0
        return ValidationResult(
            passed=passed, errors=errors, warnings=warnings, info=info
        )

    def _validate_hook_group(
        self,
        group: object,
        event_type: str,
        group_idx: int,
        errors: list[ValidationIssue],
    ) -> None:
        """Validate a single hook group within an event type.

        Args:
            group: The hook group object to validate
            event_type: Parent event type name
            group_idx: Index of this group in the event type array
            errors: List to append validation errors to
        """
        if not isinstance(group, dict):
            errors.append(
                ValidationIssue(
                    field=f"hooks.{event_type}[{group_idx}]",
                    severity="error",
                    message="Hook group must be an object",
                    code=HK003,
                    docs_url=generate_docs_url(HK003),
                )
            )
            return

        group_dict = cast("dict[str, YamlValue]", group)

        if "hooks" not in group_dict or not isinstance(group_dict["hooks"], list):
            errors.append(
                ValidationIssue(
                    field=f"hooks.{event_type}[{group_idx}]",
                    severity="error",
                    message="Hook group must have 'hooks' array",
                    code=HK003,
                    docs_url=generate_docs_url(HK003),
                    suggestion='Each hook group needs: {"hooks": [...]}',
                )
            )
            return

        for entry_idx, entry in enumerate(group_dict["hooks"]):
            self._validate_hook_entry(entry, event_type, group_idx, entry_idx, errors)

    def _validate_hook_entry(
        self,
        entry: object,
        event_type: str,
        group_idx: int,
        entry_idx: int,
        errors: list[ValidationIssue],
    ) -> None:
        """Validate a single hook entry.

        Args:
            entry: The hook entry object to validate
            event_type: Parent event type name
            group_idx: Index of the parent group
            entry_idx: Index of this entry in the hooks array
            errors: List to append validation errors to
        """
        field_prefix = f"hooks.{event_type}[{group_idx}].hooks[{entry_idx}]"

        if not isinstance(entry, dict):
            errors.append(
                ValidationIssue(
                    field=field_prefix,
                    severity="error",
                    message="Hook entry must be an object",
                    code=HK003,
                    docs_url=generate_docs_url(HK003),
                )
            )
            return

        entry_dict = cast("dict[str, YamlValue]", entry)
        hook_type = entry_dict.get("type")
        if hook_type not in self.VALID_HOOK_TYPES:
            errors.append(
                ValidationIssue(
                    field=f"{field_prefix}.type",
                    severity="error",
                    message=f"Invalid or missing hook type: '{hook_type}'",
                    code=HK003,
                    docs_url=generate_docs_url(HK003),
                    suggestion=f"Hook type must be one of: {', '.join(sorted(self.VALID_HOOK_TYPES))}",
                )
            )
            return

        match hook_type:
            case "command":
                if "command" not in entry_dict:
                    errors.append(
                        ValidationIssue(
                            field=f"{field_prefix}.command",
                            severity="error",
                            message="Hook type 'command' requires 'command' field",
                            code=HK003,
                            docs_url=generate_docs_url(HK003),
                        )
                    )
            case "prompt":
                if "prompt" not in entry_dict:
                    errors.append(
                        ValidationIssue(
                            field=f"{field_prefix}.prompt",
                            severity="error",
                            message="Hook type 'prompt' requires 'prompt' field",
                            code=HK003,
                            docs_url=generate_docs_url(HK003),
                        )
                    )

    @staticmethod
    def _is_file_path_reference(command: str) -> bool:
        """Return True if *command* looks like a file path rather than a bare shell command.

        File path references start with ``./``, ``../``, ``/`` (absolute), or
        ``${CLAUDE_PLUGIN_ROOT}/``.  Bare shell commands (e.g. ``echo hello``,
        ``python3 -m pytest``) do not match.

        Args:
            command: The ``command`` value from a hook entry.

        Returns:
            True if command is a file path reference, False otherwise.
        """
        return bool(command) and (
            command.startswith(("./", "../", "/", "${CLAUDE_PLUGIN_ROOT}/"))
        )

    @staticmethod
    def _find_plugin_root(base_dir: Path) -> Path:
        """Walk up from *base_dir* to find the plugin root directory.

        The plugin root is the first ancestor directory that contains a
        ``.claude-plugin/`` subdirectory.  Falls back to *base_dir* if not found.

        Args:
            base_dir: Starting directory for the search.

        Returns:
            Plugin root Path, or *base_dir* if the plugin root cannot be determined.
        """
        current = base_dir.resolve()
        for parent in [current, *current.parents]:
            if (parent / ".claude-plugin").is_dir():
                return parent
        return base_dir

    def _validate_command_script_references(
        self,
        hook_entries: list[dict[str, YamlValue]],
        base_dir: Path,
        errors: list[ValidationIssue],
    ) -> None:
        """Check that file-path ``command`` values in hook entries actually exist.

        For each entry where ``type == "command"`` and the ``command`` value
        looks like a file path reference (starts with ``./``, ``../``, ``/``,
        or ``${CLAUDE_PLUGIN_ROOT}/``), resolve the path relative to *base_dir*
        and verify:

        - The file exists (HK004 error if not).
        - The file is executable (HK005 warning if not).

        Bare shell commands such as ``echo hello`` or ``python3 -m pytest`` are
        intentionally skipped.

        Args:
            hook_entries: List of hook entry dicts to inspect.
            base_dir: Directory to use as the resolution base for relative paths.
            errors: List to append HK004 errors and HK005 warnings to.
        """
        plugin_root = self._find_plugin_root(base_dir)

        for entry in hook_entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("type") != "command":
                continue

            command = entry.get("command", "")
            if not isinstance(command, str) or not self._is_file_path_reference(
                command
            ):
                continue

            # Substitute ${CLAUDE_PLUGIN_ROOT} with the detected plugin root
            resolved_command = command.replace(
                "${CLAUDE_PLUGIN_ROOT}", str(plugin_root)
            )

            resolved_path = Path(resolved_command)
            if not resolved_path.is_absolute():
                resolved_path = (base_dir / resolved_command).resolve()

            if not resolved_path.exists():
                errors.append(
                    ValidationIssue(
                        field="command",
                        severity="error",
                        message=f"Hook script not found: {command}",
                        code=HK004,
                        docs_url=generate_docs_url(HK004),
                        suggestion=f"Create the script at {resolved_path} or fix the path",
                    )
                )
            else:
                # Use Git's tracked mode when available for cross-platform consistency.
                # On Windows, os.access(X_OK) is unreliable; Git check ensures plugins
                # that pass on Windows will also pass on Linux.
                git_exec = _git_file_has_execute_bit(resolved_path)
                if git_exec is False:
                    errors.append(
                        ValidationIssue(
                            field="command",
                            severity="warning",
                            message=f"Hook script is not executable in Git: {command}",
                            code=HK005,
                            docs_url=generate_docs_url(HK005),
                            suggestion=f"Run: git update-index --chmod=+x {resolved_path}",
                        )
                    )
                elif git_exec is None and not os.access(resolved_path, os.X_OK):
                    # Fallback when not in Git: os.access works on Unix only
                    errors.append(
                        ValidationIssue(
                            field="command",
                            severity="warning",
                            message=f"Hook script is not executable: {command}",
                            code=HK005,
                            docs_url=generate_docs_url(HK005),
                            suggestion=f"Run: chmod +x {resolved_path}",
                        )
                    )

    def validate_hook_script_references_in_hooks_dict(
        self,
        hooks_dict: dict[str, YamlValue],
        base_dir: Path,
        errors: list[ValidationIssue],
    ) -> None:
        """Validate command file-path references in a hooks configuration dict.

        Iterates over a hooks configuration dict (same structure as the root
        ``"hooks"`` key in ``hooks.json``) and calls
        :meth:`_validate_command_script_references` for every hook entry found.

        Args:
            hooks_dict: Hooks configuration mapping event types to groups.
            base_dir: Directory used as base for resolving relative script paths.
            errors: List to append HK004 errors and HK005 warnings to.
        """
        for groups in hooks_dict.values():
            if not isinstance(groups, list):
                continue
            for group in groups:
                if not isinstance(group, dict):
                    continue
                for entry in group.get("hooks", []):
                    if isinstance(entry, dict):
                        self._validate_command_script_references(
                            [entry], base_dir, errors
                        )


# ============================================================================
# INTEGRATION LAYER (Architecture lines 274-332, Task T12 lines 1374-1452)
# ============================================================================


def is_claude_available() -> bool:
    """Check if claude CLI is available in PATH.

    Uses shutil.which() to safely detect claude CLI without shell execution.
    This function is used by validators to determine if Claude CLI-based
    validation is possible.

    Security: Uses shutil.which() to get full command path, no shell=True.

    Returns:
        True if claude CLI found in PATH, False otherwise
    """
    return shutil.which("claude") is not None


def validate_with_claude(plugin_dir: Path) -> tuple[bool, str]:
    """Run claude plugin validate if available.

    Executes claude CLI validation on a plugin directory. Gracefully handles
    cases where claude CLI is not available by returning success with skip message.

    Security requirements:
    - NEVER uses shell=True (command injection risk)
    - Passes command as list: [cmd_path, arg1, arg2]
    - Sets timeout to prevent hanging
    - Gets full command path via shutil.which()

    Args:
        plugin_dir: Path to plugin directory containing .claude-plugin/plugin.json

    Returns:
        Tuple of (success, output):
        - If claude not available: (True, "skipped")
        - If not a plugin directory: (True, "skipped")
        - If validation passes: (True, stdout)
        - If validation fails: (False, stderr + stdout)

    Raises:
        Never raises - returns (False, error_message) on failure
    """
    # Check if claude CLI is available
    claude_path = shutil.which("claude")
    if claude_path is None:
        return True, "claude CLI not available (skipped)"

    # Check if this is a plugin directory
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    if not plugin_json.exists():
        return True, "Not a plugin directory (skipped)"

    # Run claude plugin validate with security best practices
    try:
        result = subprocess.run(
            [claude_path, "plugin", "validate", str(plugin_dir)],
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT,
            check=False,  # Handle non-zero exit code ourselves
        )
    except subprocess.TimeoutExpired:
        return (
            False,
            f"Claude plugin validation timed out after {CLAUDE_TIMEOUT} seconds",
        )
    except (FileNotFoundError, OSError) as e:
        # FileNotFoundError: Claude CLI not found (should be caught by shutil.which)
        # OSError: Other subprocess errors (permission denied, etc.)
        is_not_found = isinstance(e, FileNotFoundError)
        message = (
            "Claude CLI not found in PATH (skipped)"
            if is_not_found
            else f"Failed to run claude plugin validate: {e}"
        )
        # Not found is a skip (success), other OS errors are failures
        return is_not_found, message
    else:
        # Return success if validation passed, failure with details otherwise
        success = result.returncode == 0
        output = result.stdout if success else result.stderr + "\n" + result.stdout
        return success, output


def get_staged_files() -> list[Path]:
    """Get list of staged files for pre-commit context.

    Parses output of `git diff --cached --name-only` to identify which files
    are staged for commit. Used in pre-commit hooks to validate only changed files.

    Security requirements:
    - Uses list arguments: ["git", "diff", ...]
    - Sets timeout to prevent hanging
    - Never uses shell=True

    Returns:
        List of Path objects for staged files
        Empty list if not in a git repository or no staged files

    Raises:
        Never raises - returns empty list on failure
    """
    # Get full path to git command
    git_path = shutil.which("git")
    if git_path is None:
        return []

    try:
        result = subprocess.run(
            [git_path, "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=10,  # 10 seconds should be plenty for git diff
            check=False,
        )

        # If command failed (not a git repo, etc.), return empty list
        if result.returncode != 0:
            return []

        # Parse output into Path objects
        # Filter out empty lines
        return [
            Path(line.strip()) for line in result.stdout.splitlines() if line.strip()
        ]

    except subprocess.TimeoutExpired:
        # Git diff shouldn't take this long - something is wrong
        return []
    except FileNotFoundError:
        # Git not found (should be caught by shutil.which check above)
        return []
    except OSError:
        # Other subprocess errors
        return []


# ============================================================================
# REPORTER PROTOCOL (Architecture lines 206-272)
# ============================================================================


class Reporter(Protocol):
    """Protocol for result reporters.

    Defines interface for formatting and displaying validation results to users.
    Different implementations support various output formats (Rich terminal,
    plain text for CI, summary).
    """

    def report(
        self,
        file_results: FileResults,
        verbose: bool = False,
        *,
        show_progress: bool = False,
    ) -> None:
        """Display validation results grouped by file.

        Args:
            file_results: Mapping of file paths to lists of (validator_name,
                ValidationResult) tuples from validation
            verbose: Whether to show additional detail like info messages
            show_progress: Whether to show per-file PASSED status for clean files
        """
        ...

    def summarize(
        self, total_files: int, passed: int, failed: int, warnings: int
    ) -> None:
        """Display summary statistics.

        Args:
            total_files: Total number of unique files validated
            passed: Number of files where all validators passed
            failed: Number of files where any validator failed
            warnings: Number of files with warnings (all passed but with issues)
        """
        ...


# ============================================================================
# CONSOLE REPORTER (Rich-based)
# ============================================================================


class ConsoleReporter:
    """Rich-based terminal reporter with colored output.

    Uses Rich library for formatted terminal output with colors, tables, and
    styled text. Implements Rich table best practices from python3-development
    skill for proper width handling and no-wrap display.

    Architecture lines 239-252
    """

    def __init__(
        self, console: Console | None = None, *, no_color: bool = False
    ) -> None:
        """Initialize console reporter.

        Args:
            console: Optional pre-built Rich Console instance. When provided,
                the ``no_color`` parameter is ignored because color behaviour is
                determined by the supplied console.
            no_color: Disable color output for non-TTY environments. Only used
                when ``console`` is not provided.
        """
        if console is not None:
            self.console = console
        else:
            self.console = Console(force_terminal=not no_color, no_color=no_color)
        self.no_color = no_color

    @staticmethod
    def _get_rendered_width(renderable: ConsoleRenderable | RichCast | str) -> int:
        """Get actual rendered width of any Rich renderable.

        Uses a temporary wide console to measure the natural width of a
        renderable without any wrapping constraints. Handles color codes,
        Unicode, styling, padding, and borders.

        Args:
            renderable: Any Rich renderable (Panel, Table, Text, etc.)

        Returns:
            The maximum rendered width in characters.
        """
        temp_console = Console(width=999999)
        measurement = Measurement.get(temp_console, temp_console.options, renderable)
        return int(measurement.maximum)

    def _print_issue(self, issue: ValidationIssue) -> None:
        """Print a single validation issue with Rich formatting.

        Args:
            issue: The validation issue to display
        """
        severity_icons = {
            "error": ":cross_mark:",
            "warning": ":warning:",
            "info": ":information:",
        }
        severity_colors = {"error": "red", "warning": "yellow", "info": "blue"}

        icon = severity_icons.get(issue.severity, "")
        color = severity_colors.get(issue.severity, "white")
        location = f":{issue.line}" if issue.line else ""

        # Main message line -- may contain long paths or messages
        self.console.print(
            f"    {icon} [{color}][{issue.code}][/{color}] {issue.field}{location}: {issue.message}",
            crop=False,
            overflow="ignore",
        )

        # Suggestion line -- may contain long commands or paths
        if issue.suggestion:
            self.console.print(
                f"      [dim]→[/dim] {issue.suggestion}", crop=False, overflow="ignore"
            )

        # Docs URL line -- must never wrap
        if issue.docs_url:
            self.console.print(
                f"      [dim]→[/dim] [link]{issue.docs_url}[/link]",
                crop=False,
                overflow="ignore",
            )

    def report(
        self,
        file_results: FileResults,
        verbose: bool = False,
        *,
        show_progress: bool = False,
    ) -> None:
        """Display validation results with Rich formatting, grouped by file.

        Args:
            file_results: Mapping of file paths to lists of (validator_name,
                ValidationResult) tuples from validation
            verbose: Whether to show info messages in addition to errors/warnings
            show_progress: Whether to show per-file PASSED status for clean files
        """
        for file_path, validator_results in file_results.items():
            # Determine overall file status
            all_passed = all(r.passed for _, r in validator_results)
            any_issues = False

            for _vname, result in validator_results:
                issues_to_show = [*result.errors, *result.warnings]
                if verbose:
                    issues_to_show.extend(result.info)
                if issues_to_show:
                    any_issues = True

            if all_passed and not any_issues:
                # File passed all validators with no issues
                if show_progress:
                    self.console.print(
                        f":white_check_mark: [green]{file_path}[/green] - PASSED",
                        crop=False,
                        overflow="ignore",
                    )
                continue

            # File has issues - show file header once, then per-validator results
            # File paths may be long -- prevent wrapping
            self.console.print(
                f"\n[bold]{file_path}[/bold]", crop=False, overflow="ignore"
            )

            for validator_name, result in validator_results:
                issues_to_show = [*result.errors, *result.warnings]
                if verbose:
                    issues_to_show.extend(result.info)

                if not issues_to_show:
                    # This validator passed — only show if progress requested
                    if show_progress:
                        self.console.print(
                            f"  :white_check_mark: [dim]{validator_name}:[/dim] PASSED",
                            crop=False,
                            overflow="ignore",
                        )
                    continue

                # Show validator name as sub-header
                status_icon = ":cross_mark:" if not result.passed else ":warning:"
                self.console.print(
                    f"  {status_icon} [dim]{validator_name}:[/dim]",
                    crop=False,
                    overflow="ignore",
                )

                for issue in issues_to_show:
                    self._print_issue(issue)

    def summarize(
        self, total_files: int, passed: int, failed: int, warnings: int
    ) -> None:
        """Display summary statistics with Rich formatting.

        Args:
            total_files: Total number of unique files validated
            passed: Number of files where all validators passed
            failed: Number of files where any validator failed
            warnings: Number of files with warnings (all passed but with issues)
        """
        # Determine overall status
        if failed == 0:
            status_icon = ":white_check_mark:"
            status_text = "PASSED"
            status_color = "green"
        else:
            status_icon = ":cross_mark:"
            status_text = "FAILED"
            status_color = "red"

        # Build summary text
        summary_lines = [
            f"{status_icon} [bold {status_color}]{status_text}[/bold {status_color}]",
            "",
            f"Total files: {total_files}",
            f"[green]Passed: {passed}[/green]",
            f"[red]Failed: {failed}[/red]",
        ]

        if warnings > 0:
            summary_lines.append(f"[yellow]Warnings: {warnings}[/yellow]")

        summary = "\n".join(summary_lines)

        # Display in panel -- set console width to panel's natural width
        # to prevent Panel from wrapping at 80 chars in non-TTY environments
        panel = Panel(
            summary, title="Validation Summary", border_style=status_color, expand=False
        )
        panel_width = self._get_rendered_width(panel)
        self.console.width = panel_width
        self.console.print(
            panel, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True
        )


# ============================================================================
# CI REPORTER (Plain text)
# ============================================================================


class CIReporter:
    """Plain text reporter for CI environments.

    Outputs validation results without ANSI color codes or Rich formatting.
    Uses standard file:line:code:message format for compatibility with CI
    tools and log parsers.

    Architecture lines 239-252
    """

    @staticmethod
    def _print_issue(issue: ValidationIssue) -> None:
        """Print a single validation issue in plain text.

        Args:
            issue: The validation issue to display
        """
        severity_prefixes = {"error": "✗ ERROR", "warning": "⚠ WARN", "info": "i INFO"}
        prefix = severity_prefixes.get(issue.severity, "")
        location = f":{issue.line}" if issue.line else ""

        # Main message line
        print(f"    {prefix} [{issue.code}] {issue.field}{location}: {issue.message}")

        # Suggestion line (if present)
        if issue.suggestion:
            print(f"      → {issue.suggestion}")

        # Docs URL line (if present)
        if issue.docs_url:
            print(f"      → {issue.docs_url}")

    def report(
        self,
        file_results: FileResults,
        verbose: bool = False,
        *,
        show_progress: bool = False,
    ) -> None:
        """Display validation results in plain text, grouped by file.

        Args:
            file_results: Mapping of file paths to lists of (validator_name,
                ValidationResult) tuples from validation
            verbose: Whether to show info messages in addition to errors/warnings
            show_progress: Whether to show per-file PASSED status for clean files
        """
        for file_path, validator_results in file_results.items():
            # Determine overall file status
            all_passed = all(r.passed for _, r in validator_results)
            any_issues = False

            for _vname, result in validator_results:
                issues_to_show = [*result.errors, *result.warnings]
                if verbose:
                    issues_to_show.extend(result.info)
                if issues_to_show:
                    any_issues = True

            if all_passed and not any_issues:
                # File passed all validators with no issues
                if show_progress:
                    print(f"✓ {file_path} - PASSED")
                continue

            # File has issues - show file header once, then per-validator results
            print(f"\n{file_path}")

            for validator_name, result in validator_results:
                issues_to_show = [*result.errors, *result.warnings]
                if verbose:
                    issues_to_show.extend(result.info)

                if not issues_to_show:
                    if show_progress:
                        print(f"  ✓ {validator_name}: PASSED")
                    continue

                # Show validator name as sub-header
                status_icon = "✗" if not result.passed else "⚠"
                print(f"  {status_icon} {validator_name}:")

                for issue in issues_to_show:
                    self._print_issue(issue)

    def summarize(
        self, total_files: int, passed: int, failed: int, warnings: int
    ) -> None:
        """Display summary statistics in plain text.

        Args:
            total_files: Total number of files validated
            passed: Number of files that passed validation
            failed: Number of files that failed validation
            warnings: Number of files with warnings (passed but with issues)
        """
        # Determine overall status
        status = "✓ PASSED" if failed == 0 else "✗ FAILED"

        # Display summary
        print("\n" + "=" * 60)
        print(f"{status}")
        print(f"Total files: {total_files}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        if warnings > 0:
            print(f"Warnings: {warnings}")
        print("=" * 60)


# ============================================================================
# SUMMARY REPORTER (One-line status)
# ============================================================================


class SummaryReporter:
    """Single-line summary reporter for quick status checks.

    Outputs minimal validation summary in a single line format. Useful for
    scripts, pre-commit hooks, or quick status checks.

    Architecture lines 239-252
    """

    def report(
        self,
        file_results: FileResults,
        verbose: bool = False,
        *,
        show_progress: bool = False,
    ) -> None:
        """Display nothing (summary-only reporter).

        Args:
            file_results: Mapping of file paths to lists of (validator_name,
                ValidationResult) tuples (ignored for summary reporter)
            verbose: Whether to show info messages (ignored for summary reporter)
            show_progress: Whether to show per-file PASSED status (ignored)
        """
        # Summary reporter only shows final summary, not per-file results

    def summarize(
        self, total_files: int, passed: int, failed: int, warnings: int
    ) -> None:
        """Display single-line summary.

        Args:
            total_files: Total number of files validated
            passed: Number of files that passed validation
            failed: Number of files that failed validation
            warnings: Number of files with warnings (passed but with issues)
        """
        # Determine overall status
        if failed == 0:
            status_icon = "✓"
            status = f"{passed}/{total_files} files passed"
        else:
            status_icon = "✗"
            status = f"{failed}/{total_files} files failed"

        # Add warnings if present
        if warnings > 0:
            status += f" ({warnings} with warnings)"

        print(f"{status_icon} {status}")


# ============================================================================
# IGNORE PATTERN SUPPORT
# ============================================================================


def _load_ignore_patterns() -> list[str]:
    """Load glob patterns from .pluginvalidatorignore file.

    Searches for the ignore file in the following order:
    1. Current working directory (.pluginvalidatorignore)
    2. .claude/.pluginvalidatorignore

    Each line is a gitignore-style glob pattern. Lines starting with '#' are
    comments, blank lines are ignored.

    Returns:
        List of glob patterns to match against file paths.
    """
    candidates = [
        Path.cwd() / ".pluginvalidatorignore",
        Path.cwd() / ".claude" / ".pluginvalidatorignore",
    ]
    for candidate in candidates:
        if candidate.is_file():
            lines = candidate.read_text(encoding="utf-8").splitlines()
            return [
                line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]
    return []


def _is_ignored(path: Path, patterns: list[str]) -> bool:
    """Check whether a path matches any ignore pattern.

    Patterns follow gitignore-style glob semantics:
    - ``**/templates/*.md`` matches any ``templates`` directory at any depth
    - ``plugins/foo/bar.md`` matches that exact relative path

    The path is tested as a POSIX string (forward slashes) so patterns work
    consistently across platforms.

    Args:
        path: File path to check (absolute or relative).
        patterns: Glob patterns loaded from .pluginvalidatorignore.

    Returns:
        True if the path matches any pattern and should be skipped.
    """
    path_str = path.as_posix()
    for pattern in patterns:
        if fnmatch.fnmatch(path_str, pattern):
            return True
        # Also match against just the relative-to-cwd representation
        try:
            rel = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            rel = path_str
        if fnmatch.fnmatch(rel, pattern):
            return True
    return False


# ============================================================================
# FRONTMATTER REQUIREMENT LOGIC
# ============================================================================


class _FrontmatterRequirement(StrEnum):
    """Whether a file requires YAML frontmatter."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    EXEMPT = "exempt"


def _frontmatter_requirement(path: Path) -> _FrontmatterRequirement:
    """Determine whether frontmatter is required for a given path.

    Rules:
    - Files in FRONTMATTER_EXEMPT_FILENAMES are always exempt.
    - ``**/skills/*/SKILL.md`` (direct child of skill dir) -- required.
    - ``**/agents/*.md`` (direct child of agents dir) -- required.
    - ``**/commands/*.md`` (direct child of commands dir) -- required.
    - Deeper nested files under agents/ or commands/ -- optional.
      If the file already contains frontmatter it will be validated normally;
      if it does not, frontmatter validation is skipped entirely.

    Args:
        path: Path to the markdown file.

    Returns:
        _FrontmatterRequirement indicating the frontmatter policy for this file.
    """
    # Exempt well-known filenames regardless of location
    if path.name in FRONTMATTER_EXEMPT_FILENAMES:
        return _FrontmatterRequirement.EXEMPT

    # SKILL.md files are always required (the FileType detector already handles this)
    if path.name == "SKILL.md":
        return _FrontmatterRequirement.REQUIRED

    # Check parent directory name to distinguish direct child vs nested
    parent_name = path.parent.name

    if parent_name == "agents":
        return _FrontmatterRequirement.REQUIRED
    if parent_name == "commands":
        return _FrontmatterRequirement.REQUIRED

    # If "agents" or "commands" appears anywhere in the path parts but the
    # immediate parent is NOT that directory, this is a nested subdirectory file.
    parts = set(path.parts)
    if "agents" in parts or "commands" in parts:
        return _FrontmatterRequirement.OPTIONAL

    # Default: required (preserves existing behavior for any other case)
    return _FrontmatterRequirement.REQUIRED


def _file_has_frontmatter(path: Path) -> bool:
    """Quick check whether a file starts with a YAML frontmatter delimiter.

    Args:
        path: Path to file to check.

    Returns:
        True if the file content starts with ``---``.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return content.startswith("---")


# ============================================================================
# CLI LAYER (Architecture lines 87-129)
# ============================================================================


def _get_validators_for_path(path: Path) -> list[Validator]:
    """Return validators to run for the given path based on file type.

    Args:
        path: Path to validate.

    Returns:
        List of validator instances.

    Raises:
        typer.Exit: If path type is unknown.
    """
    file_type = FileType.detect_file_type(path)
    validators: list[Validator] = [SymlinkTargetValidator()]

    if file_type in {FileType.SKILL, FileType.AGENT, FileType.COMMAND}:
        fm_req = _frontmatter_requirement(path)
        if fm_req == _FrontmatterRequirement.EXEMPT:
            return [SymlinkTargetValidator()]
        if fm_req == _FrontmatterRequirement.REQUIRED or _file_has_frontmatter(path):
            validators.append(FrontmatterValidator())
        if fm_req == _FrontmatterRequirement.REQUIRED or _file_has_frontmatter(path):
            validators.extend(
                [NameFormatValidator(), DescriptionValidator(file_type=file_type)]
            )
        validators.append(NamespaceReferenceValidator())
        if file_type == FileType.SKILL:
            validators.extend(
                [
                    ComplexityValidator(),
                    InternalLinkValidator(),
                    ProgressiveDisclosureValidator(),
                ]
            )
    elif file_type == FileType.PLUGIN:
        validators.append(PluginStructureValidator())
    elif file_type == FileType.HOOK_CONFIG:
        validators.append(HookValidator())
    elif file_type == FileType.HOOK_SCRIPT:
        pass
    elif file_type in {FileType.CLAUDE_MD, FileType.REFERENCE, FileType.MARKDOWN}:
        validators.append(MarkdownTokenCounter())
    else:
        typer.echo(f"Error: Cannot determine file type for: {path}", err=True)
        typer.echo(
            "Expected: SKILL.md, agent .md, command .md, hooks.json, plugin directory, or markdown file",
            err=True,
        )
        raise typer.Exit(2) from None

    return validators


def _validate_single_path(
    path: Path, *, check: bool, fix: bool, verbose: bool
) -> FileResults:
    """Validate a single path and return results grouped by file.

    Args:
        path: Path to validate.
        check: Validate only, don't auto-fix.
        fix: Auto-fix issues where possible.
        verbose: Show detailed output.

    Returns:
        Mapping of file path to list of (validator_class_name, result) tuples.

    Raises:
        typer.Exit: If path doesn't exist or file type is unknown.

    """
    if not path.exists():
        typer.echo(f"Error: Path does not exist: {path}", err=True)
        raise typer.Exit(2) from None

    validators = _get_validators_for_path(path)
    if not validators:
        return {path: []}

    # Load per-plugin ignore config (once per plugin root)
    plugin_root = _find_plugin_root(path)
    ignore_config: IgnoreConfig = (
        _load_ignore_config(plugin_root) if plugin_root is not None else {}
    )

    # Run validation — group results by file path with validator class names
    validator_results: list[tuple[str, ValidationResult]] = []
    for validator in validators:
        result = validator.validate(path)
        if plugin_root is not None:
            result = _filter_result_by_ignore(result, path, plugin_root, ignore_config)
        validator_results.append((type(validator).__name__, result))

    # Apply fixes if requested and validator supports it
    # Note: --fix still runs even for suppressed issues (ignore = suppress reporting, not fixing)
    if fix:
        fixes_applied: list[str] = []
        for validator in validators:
            if validator.can_fix():
                try:
                    validator_fixes = validator.fix(path)
                    fixes_applied.extend(validator_fixes)
                except NotImplementedError:
                    pass  # Validator doesn't support fixing

        # Re-validate after fixes
        if fixes_applied:
            validator_results = []
            for validator in validators:
                result = validator.validate(path)
                if plugin_root is not None:
                    result = _filter_result_by_ignore(
                        result, path, plugin_root, ignore_config
                    )
                validator_results.append((type(validator).__name__, result))

    return {path: validator_results}


def _handle_tokens_only(paths: list[Path], *, batch: bool = False) -> None:
    r"""Output only the integer token count for each path, then exit.

    For a single path, prints just the integer. For multiple paths (or when
    ``batch`` is True), prints one entry per line. When ``batch`` is True,
    each line is tab-separated ``<count>\\t<path>`` for machine readability.

    Token counting always uses body-only (frontmatter stripped) so that the
    numbers match what ComplexityValidator measures against thresholds.

    Args:
        paths: Paths to count tokens for
        batch: When True, emit ``<count>\\t<path>`` tab-separated output.

    Raises:
        typer.Exit: Always exits (code 0 on success, code 2 on error)
    """
    counter = MarkdownTokenCounter()
    entries: list[tuple[int, Path]] = []
    for path in paths:
        if not path.exists():
            typer.echo(f"Error: Path does not exist: {path}", err=True)
            raise typer.Exit(2) from None
        # Always count body-only so output matches ComplexityValidator thresholds
        token_count = counter.count_file_tokens(path, body_only=True)
        if token_count is None:
            typer.echo(f"Error: Could not count tokens for: {path}", err=True)
            raise typer.Exit(2) from None
        entries.append((token_count, path))

    if batch:
        for count, path in entries:
            print(f"{count}\t{path}")
    else:
        for count, _path in entries:
            print(count)
    raise typer.Exit(0) from None


def _discover_validatable_paths(directory: Path) -> list[Path]:
    """Auto-discover validatable files in a bare directory.

    Globs ``DEFAULT_SCAN_PATTERNS`` against *directory* and returns
    deduplicated, sorted paths.  For any ``.claude-plugin/plugin.json``
    match the **plugin root directory** (grandparent of plugin.json) is
    returned instead of the file itself, because ``detect_file_type``
    recognises directories that contain ``.claude-plugin/plugin.json``.

    Args:
        directory: The directory to scan.

    Returns:
        Sorted list of unique paths suitable for validation.
    """
    discovered: set[Path] = set()
    for pattern in DEFAULT_SCAN_PATTERNS:
        for match in directory.glob(pattern):
            if match.name == "plugin.json":
                discovered.add(match.parent.parent)
            else:
                discovered.add(match)
    return sorted(discovered)


def _resolve_filter_and_expand_paths(
    paths: list[Path], filter_glob: str | None, filter_type: str | None
) -> tuple[list[Path], bool]:
    """Resolve filter options and expand directory paths.

    Validates mutual exclusion of --filter and --filter-type, resolves
    filter_type to glob pattern, and expands directories.

    Returns:
        Tuple of (expanded_paths, is_batch).

    Raises:
        typer.Exit: On invalid filter options.
    """
    if filter_glob is not None and filter_type is not None:
        typer.echo("Error: --filter and --filter-type are mutually exclusive", err=True)
        raise typer.Exit(2) from None

    resolved_glob: str | None = filter_glob
    if filter_type is not None:
        if filter_type not in FILTER_TYPE_MAP:
            valid = ", ".join(FILTER_TYPE_MAP)
            typer.echo(f"Error: --filter-type must be one of: {valid}", err=True)
            raise typer.Exit(2) from None
        resolved_glob = FILTER_TYPE_MAP[filter_type]

    expanded_paths: list[Path] = []
    is_batch = False
    for path in paths:
        if resolved_glob is not None and path.is_dir():
            matched = sorted(path.glob(resolved_glob))
            expanded_paths.extend(matched)
            is_batch = True
        elif resolved_glob is None and path.is_dir():
            if (path / ".claude-plugin/plugin.json").exists():
                expanded_paths.append(path)
                # Also validate SKILL.md files (InternalLinkValidator, etc.)
                expanded_paths.extend(sorted(path.glob("**/skills/*/SKILL.md")))
            else:
                expanded_paths.extend(_discover_validatable_paths(path))
                is_batch = True
        else:
            expanded_paths.append(path)
    return expanded_paths, is_batch


def _compute_summary(all_results: FileResults) -> tuple[int, int, int, int]:
    """Compute validation summary statistics from file results.

    Returns:
        Tuple of (total_files, passed, failed, warnings).
    """
    total_files = len(all_results)
    passed = sum(
        1 for vr_list in all_results.values() if all(r.passed for _, r in vr_list)
    )
    failed = sum(
        1 for vr_list in all_results.values() if any(not r.passed for _, r in vr_list)
    )
    warnings = sum(
        1
        for vr_list in all_results.values()
        if all(r.passed for _, r in vr_list) and any(r.warnings for _, r in vr_list)
    )
    return total_files, passed, failed, warnings


def _show_help_and_exit(ctx: typer.Context, code: int = 0) -> NoReturn:
    """Print the help text for the current command and exit.

    Args:
        ctx: The Typer/Click context to extract help from.
        code: Exit code to use.

    Raises:
        typer.Exit: Always raised to terminate after displaying help.
    """
    typer.echo(ctx.get_help())
    raise typer.Exit(code) from None


def main(
    ctx: typer.Context,
    paths: Annotated[
        list[Path] | None,
        typer.Argument(
            help="Paths to plugin, skill, agent, or command files to validate"
        ),
    ] = None,
    check: Annotated[
        bool, typer.Option("--check", help="Validate only, don't auto-fix")
    ] = False,
    fix: Annotated[
        bool, typer.Option("--fix", help="Auto-fix issues where possible")
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Show detailed validation output including info messages",
        ),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output for CI environments"),
    ] = False,
    tokens_only: Annotated[
        bool,
        typer.Option(
            "--tokens-only",
            help="Output only the integer token count (for programmatic use)",
        ),
    ] = False,
    show_progress: Annotated[
        bool,
        typer.Option(
            "--show-progress", help="Show per-file PASSED/FAILED status for all files"
        ),
    ] = False,
    show_summary: Annotated[
        bool,
        typer.Option("--show-summary", help="Show validation summary panel at the end"),
    ] = False,
    filter_glob: Annotated[
        str | None,
        typer.Option(
            "--filter",
            help=(
                "Glob pattern to match files within a directory "
                "(e.g. '**/skills/*/SKILL.md'). "
                "Ignored when the positional path is a file. "
                "Mutually exclusive with --filter-type."
            ),
        ),
    ] = None,
    filter_type: Annotated[
        str | None,
        typer.Option(
            "--filter-type",
            help=(
                "Shortcut for common filter patterns. "
                "Choices: skills (**/skills/*/SKILL.md), "
                "agents (**/agents/*.md), "
                "commands (**/commands/*.md). "
                "Mutually exclusive with --filter."
            ),
        ),
    ] = None,
) -> None:
    """Validate Claude Code plugins, skills, agents, and commands.

    Validates frontmatter schema, plugin structure, skill complexity, internal links,
    and progressive disclosure. Optionally auto-fixes issues.

    Supports token counting for any markdown file (CLAUDE.md, reference docs, etc.).

    Accepts one or more paths (compatible with pre-commit pass_filenames).

    Examples:
        # Validate single file (silent on success)
        ./plugin_validator.py path/to/SKILL.md

        # Validate multiple files (pre-commit mode, silent on success)
        ./plugin_validator.py file1.md file2.md file3.md

        # Validate entire plugin
        ./plugin_validator.py plugins/my-plugin

        # Auto-fix issues
        ./plugin_validator.py --fix path/to/SKILL.md

        # Validate for CI (no color)
        ./plugin_validator.py --no-color plugins/my-plugin

        # Show per-file PASSED/FAILED status
        ./plugin_validator.py --show-progress plugins/my-plugin

        # Show summary panel at the end
        ./plugin_validator.py --show-summary plugins/my-plugin

        # Count tokens in any markdown file
        ./plugin_validator.py --verbose .claude/CLAUDE.md

        # Get just the token count for programmatic use
        ./plugin_validator.py --tokens-only .claude/CLAUDE.md

        # Token counts for all skills in a plugin directory (batch mode)
        ./plugin_validator.py --tokens-only --filter-type=skills plugins/my-plugin

        # Token counts matching a custom glob pattern
        ./plugin_validator.py --tokens-only --filter='**/SKILL.md' ../other-repo

    Exit Codes:
        0: Success (all checks passed)
        1: Validation errors found
        2: Usage error (invalid arguments)
        130: Interrupted by user (Ctrl+C)
    """
    # Show help when no arguments provided
    if not paths:
        _show_help_and_exit(ctx, code=0)

    # Validate that all provided paths exist; report non-existent ones
    bad_paths = [str(p) for p in paths if not p.exists()]
    if bad_paths:
        typer.echo(f"Path does not exist: {', '.join(bad_paths)}", err=True)
        typer.echo("", err=True)
        _show_help_and_exit(ctx, code=2)

    try:
        expanded_paths, is_batch = _resolve_filter_and_expand_paths(
            paths, filter_glob, filter_type
        )

        if tokens_only:
            _handle_tokens_only(expanded_paths, batch=is_batch)

        if check and fix:
            typer.echo("Error: Cannot use both --check and --fix flags", err=True)
            raise typer.Exit(2) from None

        ignore_patterns = _load_ignore_patterns()
        all_results: FileResults = {}
        for path in expanded_paths:
            if ignore_patterns and _is_ignored(path, ignore_patterns):
                continue
            file_results = _validate_single_path(
                path, check=check, fix=fix, verbose=verbose
            )
            for file_path, validator_results in file_results.items():
                if file_path in all_results:
                    all_results[file_path].extend(validator_results)
                else:
                    all_results[file_path] = list(validator_results)

        reporter: Reporter = (
            CIReporter() if no_color else ConsoleReporter(no_color=no_color)
        )
        reporter.report(all_results, verbose=verbose, show_progress=show_progress)

        total_files, passed, failed, warnings = _compute_summary(all_results)
        if show_summary:
            reporter.summarize(total_files, passed, failed, warnings)

        # Exit with appropriate code
        if failed > 0:
            raise typer.Exit(1) from None
        raise typer.Exit(0) from None

    except KeyboardInterrupt:
        typer.echo("\nInterrupted by user", err=True)
        raise typer.Exit(130) from None


# Create Typer app
app = typer.Typer(
    help="Validate Claude Code plugins and skills",
    add_completion=False,
)
app.command()(main)


if __name__ == "__main__":
    app()
