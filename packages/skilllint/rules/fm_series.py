"""FM-series frontmatter validation rules (FM001-FM010).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects. Functions receive the parsed frontmatter dict,
the file path, and the detected file type string.

Severities:
    "error"   — FM002, FM003, FM005, FM006; FM010 when the name pattern is invalid
    "warning" — FM001 (skills), FM004, FM007, FM008; FM010 when skill name mismatches parent directory
    "error"   — FM001 (agents)
    "info"    — FM009

Import note: ValidationIssue and generate_docs_url are deferred inside each
function to break the circular import: plugin_validator imports rules/, so
rules/ cannot import plugin_validator at module level.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from skilllint.rule_registry import skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue


# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

_SKILLS_SPEC_URL = "https://docs.anthropic.com/en/docs/claude-code/skills"
_AGENTS_SPEC_URL = "https://docs.anthropic.com/en/docs/claude-code/sub-agents"
_FM_DOCS_BASE = "https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md"

# Name pattern: lowercase alphanumeric with hyphens, no leading/trailing/consecutive hyphens.
# Source: skills.md frontmatter reference table — "Lowercase letters, numbers, and hyphens only (max 64 characters)"
# Source: sub-agents.md — "Unique identifier using lowercase letters and hyphens"
_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
_CONSECUTIVE_HYPHENS_RE = re.compile(r"--")

# Source: skills.md — "Lowercase letters, numbers, and hyphens only (max 64 characters)"
# Source: sub-agents.md — max 64 chars implied by same pattern constraint
_MAX_NAME_LENGTH = 64


def _docs_url(code: str) -> str:
    """Return the documentation URL for an FM rule code.

    Args:
        code: Rule code string (e.g., "FM001").

    Returns:
        Full URL with anchor for the error code documentation.
    """
    return f"{_FM_DOCS_BASE}#{code.lower()}"


def _make_issue(
    *,
    field: str,
    severity: Literal["error", "warning", "info"],
    message: str,
    code: str,
    suggestion: str | None = None,
    line: int | None = None,
) -> ValidationIssue:
    """Construct a ValidationIssue.

    Args:
        field: Frontmatter field name (or "(file)" / "(yaml)" for structural errors).
        severity: Issue severity.
        message: Human-readable description.
        code: Rule code (e.g., "FM001").
        suggestion: Optional auto-fix hint.
        line: Optional 1-based line number.

    Returns:
        A frozen ValidationIssue instance.
    """
    # Deferred import to break circular dependency:
    # plugin_validator imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    return ValidationIssue(
        field=field,
        severity=severity,
        message=message,
        code=code,
        docs_url=_docs_url(code),
        suggestion=suggestion,
        line=line,
    )


# ---------------------------------------------------------------------------
# FM001 — Missing required field (name / description)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "FM001",
    severity="warning",  # default severity; FM001 is file-type-aware (see function body)
    category="frontmatter",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _AGENTS_SPEC_URL},
)
def check_fm001(frontmatter: dict, path: Path, file_type: str) -> list[ValidationIssue]:
    """## FM001 — Missing required field

    For **agents** (`sub-agents.md`): both `name` and `description` are
    Required: Yes — missing either is a schema error.

    For **skills** (`skills.md`): `name` is optional (falls back to directory
    name) and `description` is "Recommended" — missing either is a warning,
    not a schema error.

    **Source (agents):** sub-agents.md — "name — Required: Yes", "description — Required: Yes"

    **Source (skills):** skills.md — "name — Required: No (uses directory name)",
    "description — Required: Recommended"

    **Fix:** Add the missing `name` and/or `description` field to the frontmatter.

    Returns:
        List of ValidationIssue objects, one per missing field; empty when both
        fields are present and non-empty.

    <!-- examples: FM001 -->
    """
    is_agent = file_type == "agent"
    severity: Literal["error", "warning"] = "error" if is_agent else "warning"

    issues: list[ValidationIssue] = []

    name_val = frontmatter.get("name")
    if name_val is None or (isinstance(name_val, str) and not name_val.strip()):
        issues.append(
            _make_issue(
                field="name",
                severity=severity,
                message="Missing required field: name",
                code="FM001",
                suggestion="Add `name: your-name` to the frontmatter block",
            )
        )

    desc_val = frontmatter.get("description")
    if desc_val is None or (isinstance(desc_val, str) and not desc_val.strip()):
        issues.append(
            _make_issue(
                field="description",
                severity=severity,
                message="Missing required field: description",
                code="FM001",
                suggestion="Add `description: <what this does>` to the frontmatter block",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# FM002 — Invalid YAML syntax
# ---------------------------------------------------------------------------


@skilllint_rule(
    "FM002",
    severity="error",
    category="frontmatter",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_fm002(frontmatter: dict, path: Path, file_type: str) -> list[ValidationIssue]:
    """## FM002 — Invalid YAML syntax

    The frontmatter block between `---` markers must be valid YAML. If the
    YAML cannot be parsed, no frontmatter fields can be extracted and the
    runtime cannot interpret the file.

    **Source:** skills.md — "YAML frontmatter fields between `---` markers"
    implies valid YAML is a structural requirement.

    **Fix:** Correct the YAML syntax in the frontmatter block. Common causes
    are unquoted colons in values (e.g. `description: Foo: bar` — quote it
    as `description: "Foo: bar"`).

    Returns:
        Always an empty list. FM002 is emitted by the YAML parsing layer in
        FrontmatterValidator before frontmatter is available; this function
        exists for rule metadata registration only.

    <!-- examples: FM002 -->
    """
    return []


# ---------------------------------------------------------------------------
# FM003 — Frontmatter not closed with `---`
# ---------------------------------------------------------------------------


@skilllint_rule(
    "FM003",
    severity="error",
    category="frontmatter",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_fm003(frontmatter: dict, path: Path, file_type: str) -> list[ValidationIssue]:
    """## FM003 — Frontmatter block not found or not closed

    Every capability file must start with a YAML frontmatter block
    delimited by `---` markers. Without this block the runtime cannot
    distinguish configuration from instructions.

    **Source:** skills.md — "Every skill needs a SKILL.md file with two parts:
    YAML frontmatter (between `---` markers)"

    **Fix:** Ensure the file starts with `---`, contains frontmatter fields,
    and is closed with a second `---` line.

    Returns:
        Always an empty list. FM003 is emitted by
        FrontmatterValidator._extract_frontmatter() before frontmatter content
        is available; this function exists for rule metadata registration only.

    <!-- examples: FM003 -->
    """
    return []


# ---------------------------------------------------------------------------
# FM004 — Multiline YAML indicator in description
# ---------------------------------------------------------------------------

# Block-style description (`>-`, `|`, etc.): YAML parsers fold content to a single-line
# string, so we also inspect raw frontmatter text to preserve FM004 coverage.
_FM004_DESCRIPTION_BLOCK_SCALAR = re.compile(r"(?m)^description\s*:\s*(?:\|[-+]?|>[-+]?)(?:\s+#.*)?\s*$")


@skilllint_rule(
    "FM004",
    severity="warning",
    category="frontmatter",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_fm004(
    frontmatter: dict, path: Path, file_type: str, *, frontmatter_yaml: str | None = None
) -> list[ValidationIssue]:
    """## FM004 — Multiline YAML syntax in description

    The `description` field uses a multiline YAML indicator (`|`, `>`,
    `|-`, or `>-`). The Claude Code runtime accepts this syntax, but
    single-line strings are the documented convention and are easier to read.

    **Source:** skills.md examples show single-line description values.
    No normative clause prohibits multiline syntax — this is a style preference.

    **Fix:** Convert the description to a single-line string:

    ```yaml
    # Before (multiline)
    description: >-
      This skill does something useful.

    # After (single-line)
    description: This skill does something useful.
    ```

    Returns:
        List containing one warning when the description used a block scalar or
        the parsed string still contains a newline; empty otherwise.

    <!-- examples: FM004 -->
    """
    desc = frontmatter.get("description")
    uses_block_scalar = bool(frontmatter_yaml and _FM004_DESCRIPTION_BLOCK_SCALAR.search(frontmatter_yaml))
    folded_multiline = isinstance(desc, str) and ("\n" in desc)
    if uses_block_scalar or folded_multiline:
        return [
            _make_issue(
                field="description",
                severity="warning",
                message="Uses multiline YAML syntax (|, >, |-, >-) — style preference, not a schema requirement",
                code="FM004",
                suggestion="Use single-line string for better readability",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# FM005 — Field type mismatch
# ---------------------------------------------------------------------------


@skilllint_rule(
    "FM005",
    severity="error",
    category="frontmatter",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _AGENTS_SPEC_URL},
)
def check_fm005(frontmatter: dict, path: Path, file_type: str) -> list[ValidationIssue]:
    """## FM005 — Field type mismatch

    A frontmatter field has the wrong data type. For example, a boolean
    field like `disable-model-invocation` was given a string value, or
    a numeric field like `maxTurns` was given a string.

    **Source:** skills.md frontmatter reference table — each field has an
    expected type (string, boolean, number, specific string values).

    **Source:** sub-agents.md — `model` is string, `maxTurns` is number,
    `background` is boolean.

    **Fix:** Correct the field value to match the expected type.

    Returns:
        Always an empty list. FM005 is emitted by the Pydantic validation
        layer (_pydantic_error_to_validation_issue) from ValidationError
        details; this function exists for rule metadata registration only.

    <!-- examples: FM005 -->
    """
    return []


# ---------------------------------------------------------------------------
# FM006 — Invalid enum value
# ---------------------------------------------------------------------------


@skilllint_rule(
    "FM006",
    severity="error",
    category="frontmatter",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _AGENTS_SPEC_URL},
)
def check_fm006(frontmatter: dict, path: Path, file_type: str) -> list[ValidationIssue]:
    """## FM006 — Invalid field value (enum violation)

    A frontmatter field contains a value outside the allowed set. Fields
    like `effort`, `context`, `model`, `permissionMode`, and `isolation`
    have closed enumerations — only specific strings are valid.

    **Source:** skills.md — `effort`: "low", "medium", "high", "max";
    `context`: "fork".

    **Source:** sub-agents.md — `model`: "sonnet", "opus", "haiku", or
    a full model ID or "inherit"; `permissionMode`: "default",
    "acceptEdits", "dontAsk", "bypassPermissions", "plan";
    `isolation`: "worktree".

    **Fix:** Replace the invalid value with one of the allowed values
    listed in the error message.

    Returns:
        Always an empty list. FM006 is emitted by
        _pydantic_error_to_validation_issue when a Literal constraint fails;
        this function exists for rule metadata registration only.

    <!-- examples: FM006 -->
    """
    return []


# ---------------------------------------------------------------------------
# FM007 — Tools field is a YAML array instead of CSV string
# ---------------------------------------------------------------------------


@skilllint_rule(
    "FM007",
    severity="warning",
    category="frontmatter",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_fm007(frontmatter: dict, path: Path, file_type: str) -> list[ValidationIssue]:
    """## FM007 — Tools field is a YAML array (prefer CSV string)

    The `tools` / `allowed-tools` / `disallowedTools` field is written as a
    YAML sequence (list). The Claude Code runtime accepts this, but the
    documented convention is a comma-separated string.

    **Source:** skills.md — `allowed-tools` example: `allowed-tools: Read, Grep, Glob`

    **Source:** sub-agents.md — `tools` example: `tools: Read, Glob, Grep`

    **Fix:** Convert the YAML list to a CSV string:

    ```yaml
    # Before (YAML array — runtime-accepted but non-canonical)
    tools:
      - Read
      - Grep

    # After (CSV string — documented convention)
    tools: Read, Grep
    ```

    Returns:
        List of warning issues, one per tools-variant field that contains a
        YAML list; empty when all tools fields use CSV string format.

    <!-- examples: FM007 -->
    """
    issues: list[ValidationIssue] = []
    for field_name in ("tools", "allowed-tools", "disallowedTools"):
        val = frontmatter.get(field_name)
        if isinstance(val, list):
            issues.append(
                _make_issue(
                    field=field_name,
                    severity="warning",
                    message="Tools field is YAML array — runtime accepts this, but CSV string is preferred style",
                    code="FM007",
                    suggestion="Use format: 'tool1, tool2, tool3'",
                )
            )
    return issues


# ---------------------------------------------------------------------------
# FM008 — Skills field is a YAML array instead of CSV string
# ---------------------------------------------------------------------------


@skilllint_rule(
    "FM008",
    severity="warning",
    category="frontmatter",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _AGENTS_SPEC_URL},
)
def check_fm008(frontmatter: dict, path: Path, file_type: str) -> list[ValidationIssue]:
    """## FM008 — Skills field is a YAML array (prefer CSV string)

    The `skills` field is written as a YAML sequence (list). The Claude Code
    runtime accepts this, but the documented convention is a comma-separated
    string.

    **Source:** sub-agents.md frontmatter fields table — `skills` field.

    **Fix:** Convert the YAML list to a CSV string:

    ```yaml
    # Before (YAML array)
    skills:
      - my-skill
      - other-skill

    # After (CSV string — documented convention)
    skills: my-skill, other-skill
    ```

    Returns:
        List containing one warning issue when the `skills` field is a YAML
        list; empty when `skills` uses CSV string format or is absent.

    <!-- examples: FM008 -->
    """
    val = frontmatter.get("skills")
    if isinstance(val, list):
        return [
            _make_issue(
                field="skills",
                severity="warning",
                message="Skills field is YAML array — runtime accepts this, but CSV string is preferred style",
                code="FM008",
                suggestion="Use format: 'skill1, skill2, skill3'",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# FM009 — Unquoted value containing colon (auto-fixed)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "FM009",
    severity="info",
    category="frontmatter",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_fm009(frontmatter: dict, path: Path, file_type: str) -> list[ValidationIssue]:
    """## FM009 — Unquoted value containing colon (auto-fixed)

    A frontmatter field value contained an unquoted colon (`:`) which can
    break YAML parsing. The linter detected and auto-fixed this by wrapping
    the value in double quotes. This `info` entry reports what was repaired.

    **Source:** YAML specification — colons in unquoted values are interpreted
    as key separators, causing parse errors.

    **Fix:** No action needed — the fix was applied automatically. To prevent
    this in future, quote string values that contain colons:

    ```yaml
    description: "This skill: does something"
    ```

    Returns:
        Always an empty list. FM009 is emitted as ``info`` by
        _queue_fm009_info() after auto-fix; this function exists for rule
        metadata registration only.

    <!-- examples: FM009 -->
    """
    return []


# ---------------------------------------------------------------------------
# FM010 — Name field does not match directory name or violates pattern
# ---------------------------------------------------------------------------


@skilllint_rule(
    "FM010",
    severity="error",
    category="frontmatter",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_fm010(frontmatter: dict, path: Path, file_type: str) -> list[ValidationIssue]:
    """## FM010 — Name field does not match directory name or violates naming pattern

    For skills, when the `name` field is present it must match the parent
    directory name. The name must also use only lowercase letters, numbers,
    and hyphens (no consecutive hyphens, no leading/trailing hyphens,
    max 64 characters).

    **Source:** skills.md — "name — Lowercase letters, numbers, and hyphens only
    (max 64 characters)."

    **Source:** sub-agents.md — "name — Unique identifier using lowercase letters
    and hyphens"

    **Fix:** Set `name` to match the parent directory name, using only lowercase
    letters, digits, and hyphens.

    Returns:
        List of error issues describing pattern violations or a directory-name
        mismatch; empty when the name is absent (FM001 covers that case) or
        valid and matching.

    <!-- examples: FM010 -->
    """
    name_val = frontmatter.get("name")
    if name_val is None:
        # FM001 covers the missing-name case; FM010 only fires on present-but-invalid names.
        return []

    name = str(name_val)
    issues: list[ValidationIssue] = []

    # Pattern validation
    if len(name) == 0 or len(name) > _MAX_NAME_LENGTH:
        issues.append(
            _make_issue(
                field="name",
                severity="error",
                message=f"Name must be 1-{_MAX_NAME_LENGTH} characters (got {len(name)})",
                code="FM010",
                suggestion=f"Shorten the name to {_MAX_NAME_LENGTH} characters or less",
            )
        )
    elif _CONSECUTIVE_HYPHENS_RE.search(name):
        issues.append(
            _make_issue(
                field="name",
                severity="error",
                message=f"Name '{name}' must not contain consecutive hyphens",
                code="FM010",
                suggestion="Remove consecutive hyphens from the name",
            )
        )
    elif not _NAME_RE.match(name):
        issues.append(
            _make_issue(
                field="name",
                severity="error",
                message="Must use lowercase letters, numbers, and hyphens only",
                code="FM010",
                suggestion="Use format: lowercase-with-hyphens",
            )
        )

    # Directory name mismatch (skills only; path.name == "SKILL.md")
    if path.name == "SKILL.md" and not issues:
        dir_name = path.parent.name
        if name != dir_name:
            issues.append(
                _make_issue(
                    field="name",
                    severity="warning",
                    message=f"'name' field value '{name}' does not match directory name '{dir_name}'",
                    code="FM010",
                    suggestion=f"Set name: {dir_name} to match the directory name",
                )
            )

    return issues


__all__ = [
    "check_fm001",
    "check_fm002",
    "check_fm003",
    "check_fm004",
    "check_fm005",
    "check_fm006",
    "check_fm007",
    "check_fm008",
    "check_fm009",
    "check_fm010",
]
