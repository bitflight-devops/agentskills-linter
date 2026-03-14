"""AS-series rule validation for agentskills.io SKILL.md files.

Rules AS001-AS006 fire on any SKILL.md file regardless of which platform
adapter is active. They enforce cross-platform quality standards.

Entry point: check_skill_md(path: Path) -> list[dict]

Each violation dict has the shape:
    {"code": str, "severity": str, "message": str}

Severities:
    "error"   — AS001, AS002, AS003, AS004
    "warning" — AS005
    "info"    — AS006
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from skilllint.rule_registry import RULE_REGISTRY, skilllint_rule
from skilllint.token_counter import TOKEN_ERROR_THRESHOLD, TOKEN_WARNING_THRESHOLD, count_tokens

if TYPE_CHECKING:
    import pathlib

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rule registry — maps code to human-readable description
# ---------------------------------------------------------------------------

AS_RULES: dict[str, str] = {
    "AS001": "Skill name must be lowercase alphanumeric with hyphens only, 1-64 chars, no consecutive hyphens",
    "AS002": "Skill name must match the parent directory name",
    "AS003": "description field must be present and non-empty",
    "AS004": "description contains unquoted colons that break YAML — quote the string to fix",
    "AS005": f"SKILL.md body token count exceeds {TOKEN_WARNING_THRESHOLD} tokens — consider splitting into sub-skills",
    "AS006": "No eval_queries.json found — add evaluation queries for quality assurance",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MAX_NAME_LENGTH = 64

_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
_CONSECUTIVE_HYPHENS_RE = re.compile(r"--")


def _parse_skill_md(path: pathlib.Path) -> tuple[dict, list[str], str | None]:
    """Parse a SKILL.md file into frontmatter dict and body lines.

    Frontmatter is delimited by leading '---' lines. Everything after
    the closing '---' is the body.

    Returns:
        (frontmatter, body_lines, raw_description_line) where frontmatter is a dict of parsed
        YAML fields, body_lines is a list of non-empty content lines
        after the frontmatter block, and raw_description_line is the raw
        "description:" line from frontmatter (if present) for validation.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    frontmatter: dict = {}
    body_lines: list[str] = []
    raw_description_line: str | None = None

    if not lines or lines[0].strip() != "---":
        # No frontmatter — treat entire file as body
        return {}, lines, None

    # Find closing '---'
    close_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            close_idx = i
            break

    if close_idx is None:
        # Unclosed frontmatter — parse what we can, no body
        return {}, [], None

    # Parse frontmatter lines as simple key: value YAML
    for line in lines[1:close_idx]:
        if ":" in line:
            key, _, value = line.partition(":")
            key_stripped = key.strip()
            value_stripped = value.strip()
            frontmatter[key_stripped] = value_stripped

            # Track raw description line for AS004 validation
            if key_stripped == "description":
                raw_description_line = line

    body_lines = lines[close_idx + 1 :]

    return frontmatter, body_lines, raw_description_line


def _violation(
    code: str,
    severity: str,
    message: str,
    fix: str | None = None,
    authority: dict | None = None,
) -> dict:
    result = {"code": code, "severity": severity, "message": message}
    if fix:
        result["fix"] = fix
    if authority:
        result["authority"] = authority
    return result


def _get_rule_authority(code: str) -> dict | None:
    """Get authority metadata for a rule from the registry.

    Args:
        code: Rule ID (e.g., "AS001")

    Returns:
        Authority dict with 'origin' and optional 'reference', or None if not found.
    """
    entry = RULE_REGISTRY.get(code.upper())
    if entry and entry.authority:
        result = {"origin": entry.authority.origin}
        if entry.authority.reference:
            result["reference"] = entry.authority.reference
        return result
    return None


def _make_violation(code: str, severity: str, message: str, fix: str | None = None) -> dict:
    """Create a violation dict with authority metadata from the rule registry.

    This is a convenience wrapper around _violation that automatically
    looks up and includes authority metadata from the rule registry.

    Args:
        code: Rule ID (e.g., "AS001")
        severity: One of "error", "warning", "info"
        message: Human-readable violation message
        fix: Optional auto-fix suggestion

    Returns:
        Violation dict with code, severity, message, and optionally fix and authority.
    """
    return _violation(code, severity, message, fix=fix, authority=_get_rule_authority(code))


# ---------------------------------------------------------------------------
# Individual rule checks
# ---------------------------------------------------------------------------


@skilllint_rule(
    "AS001",
    severity="error",
    category="skill",
    authority={"origin": "agentskills.io", "reference": "/specification#skill-naming"},
)
def _check_as001(name: str | None) -> dict | None:
    """AS001 — Invalid skill name format.

    Skill names must be lowercase alphanumeric with hyphens only, between
    1-64 characters, with no consecutive hyphens. The name must start and
    end with a letter or digit.

    Args:
        name: The skill name from frontmatter, or None if missing.

    Returns:
        Violation dict if invalid, None otherwise.

    Fix:
        Rename the skill to use lowercase letters, digits, and hyphens only.
        For example, change ``My_Skill`` to ``my-skill``.

    Examples:
        Valid: ``my-skill``, ``skill-123``, ``a``
        Invalid: ``MySkill``, ``my_skill``, ``skill--name``, ``-skill``
    """
    if name is None:
        return _make_violation("AS001", "error", "name field is missing")

    if len(name) == 0 or len(name) > _MAX_NAME_LENGTH:
        return _make_violation(
            "AS001", "error", f"name '{name}' must be 1-{_MAX_NAME_LENGTH} characters long (got {len(name)})"
        )

    if _CONSECUTIVE_HYPHENS_RE.search(name):
        return _make_violation("AS001", "error", f"name '{name}' must not contain consecutive hyphens")

    if not _NAME_RE.match(name):
        return _make_violation(
            "AS001",
            "error",
            f"name '{name}' must match ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ (lowercase letters, digits, and hyphens only)",
        )

    return None


@skilllint_rule(
    "AS002",
    severity="error",
    category="skill",
    authority={"origin": "agentskills.io", "reference": "/specification#skill-directory-structure"},
)
def _check_as002(name: str | None, path: pathlib.Path) -> dict | None:
    """AS002 — Skill name does not match directory name.

    The skill's ``name`` field in frontmatter must match the parent
    directory name. This ensures consistency and makes skills easier
    to locate.

    Args:
        name: The skill name from frontmatter, or None if missing.
        path: Path to the SKILL.md file being validated.

    Returns:
        Violation dict if invalid, None otherwise.

    Fix:
        Either rename the directory to match the ``name`` field, or update
        the ``name`` field to match the directory name.
    """
    if name is None:
        return None  # AS001 already covers missing name

    dir_name = path.parent.name
    if name != dir_name:
        return _make_violation("AS002", "error", f"name '{name}' does not match parent directory name '{dir_name}'")

    return None


@skilllint_rule(
    "AS003",
    severity="error",
    category="skill",
    authority={"origin": "agentskills.io", "reference": "/specification#skill-description"},
)
def _check_as003(description: str | None) -> dict | None:
    """AS003 — Missing or empty description field.

    Every SKILL.md must have a ``description`` field in its frontmatter.
    The description helps AI agents understand when to use this skill
    and provides context for users.

    Args:
        description: The description from frontmatter, or None if missing.

    Returns:
        Violation dict if invalid, None otherwise.

    Fix:
        Add a ``description`` field to the frontmatter with a brief
        explanation of what this skill does.
    """
    if description is None or not description.strip():
        return _make_violation("AS003", "error", "description field must be present and non-empty")

    return None


@skilllint_rule(
    "AS004",
    severity="error",
    category="skill",
    authority={"origin": "agentskills.io", "reference": "/specification#yaml-frontmatter"},
)
def _check_as004(description: str | None, raw_line: str | None = None) -> dict | None:
    """AS004 — Description contains unquoted colons that will break YAML.

    The ``description`` field must be valid YAML. If it contains unquoted
    colons (e.g., "Examples: Context:"), YAML parsing will fail because
    the colon is interpreted as a key-value separator.

    Args:
        description: The parsed description from frontmatter, or None if missing.
        raw_line: The raw frontmatter line before parsing (optional, for validation).

    Returns:
        Violation dict if invalid, None otherwise.

    Fix:
        Quote the description string in the frontmatter. For example, change:
            description: Use this: for examples
        To:
            description: "Use this: for examples"
    """
    if description is None:
        return None  # AS003 already covers missing description

    # Check if the raw line (if provided) has unquoted colons that would break YAML
    # An unquoted colon is ":" followed by a space, not inside quotes
    if raw_line is not None and raw_line.startswith("description:"):
        value_part = raw_line[len("description:") :].strip()
        # Check for unquoted colons (colon followed by space, not in quotes)
        if _has_unquoted_colon(value_part):
            return _make_violation(
                "AS004",
                "error",
                "description contains unquoted colon that will break YAML parsing",
                fix=f'Wrap description in quotes: description: "{value_part}"',
            )

    return None


def _has_unquoted_colon(text: str) -> bool:
    """Check if text contains an unquoted colon followed by space.

    This detects YAML-breaking patterns like "Examples: Context: Test"
    which would cause 'mapping values are not allowed here' error.

    Returns:
        True when an unquoted colon-space pattern is present, False otherwise.
    """
    if not text:
        return False

    # Already quoted - safe
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return False

    # Simple check: look for ":" followed by space/alphanumeric
    # that indicates YAML value separator
    colon_pattern = re.compile(r":\s+[a-zA-Z<]")
    return bool(colon_pattern.search(text))


@skilllint_rule(
    "AS005",
    severity="warning",
    category="skill",
    authority={"origin": "agentskills.io", "reference": "/specification#skill-complexity"},
)
def _check_as005(body_lines: list[str]) -> dict | None:
    """AS005 — SKILL.md body exceeds token threshold.

    Counts tokens in the body text (frontmatter excluded) using tiktoken
    cl100k_base encoding. Large skills can degrade AI agent performance
    and increase API costs.

    Args:
        body_lines: List of content lines from the SKILL.md body.

    Returns:
        Violation dict if threshold exceeded, None otherwise.

    Thresholds:
        - Warning at 4400 tokens — consider splitting
        - Error at 8800 tokens — must split

    Fix:
        Split the skill into smaller sub-skills or move detailed content
        to reference files in a ``references/`` directory.
    """
    body_text = "\n".join(body_lines)
    token_count = count_tokens(body_text)

    if token_count > TOKEN_ERROR_THRESHOLD:
        return _make_violation(
            "AS005",
            "error",
            f"SKILL.md body is {token_count} tokens — exceeds {TOKEN_ERROR_THRESHOLD} token limit; skill must be split into sub-skills",
        )

    if token_count > TOKEN_WARNING_THRESHOLD:
        return _make_violation(
            "AS005",
            "warning",
            f"SKILL.md body is {token_count} tokens — exceeds {TOKEN_WARNING_THRESHOLD} token threshold; consider splitting into sub-skills",
        )

    return None


@skilllint_rule(
    "AS006",
    severity="info",
    category="skill",
    authority={"origin": "agentskills.io", "reference": "/specification#evaluation-queries"},
)
def _check_as006(path: pathlib.Path) -> dict | None:
    """AS006 — No evaluation queries file found.

    Recommends adding an ``eval_queries.json`` file to the skill directory
    to enable automated quality assessment. The file should contain test
    queries that exercise the skill's functionality.

    Args:
        path: Path to the SKILL.md file being validated.

    Returns:
        Violation dict if no eval file found, None otherwise.

    Fix:
        Create ``eval_queries.json`` in the skill directory with test queries
        in JSON format.

    Note:
        This is an informational message, not an error. Skills work
        without evaluation queries, but they're recommended for quality
        assurance.
    """
    parent = path.parent

    # Check for eval_queries.json exact name first
    if (parent / "eval_queries.json").exists():
        return None

    # Check for any file matching *eval*.json or *queries*.json
    for f in parent.iterdir():
        if f.suffix == ".json":
            stem = f.stem.lower()
            if "eval" in stem or "queries" in stem:
                return None

    return _make_violation(
        "AS006",
        "info",
        "No eval_queries.json found in skill directory — add evaluation queries to enable automated quality assessment",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_skill_md(path: pathlib.Path) -> list[dict]:
    """Run AS001-AS006 checks on a SKILL.md file.

    Reads and parses the file at the given path, then runs all AS-series
    rules. Returns a list of violation dicts; empty list means no issues.

    Args:
        path: Path to the SKILL.md file to validate.

    Returns:
        List of violation dicts, each with keys: code, severity, message.
        May include 'fix' key with auto-fix suggestion for AS004.
    """
    frontmatter, body_lines, raw_description_line = _parse_skill_md(path)

    name: str | None = frontmatter.get("name") or None
    description: str | None = frontmatter.get("description") or None

    # Normalise empty strings to None
    if name is not None and not name.strip():
        name = None
    if description is not None and not description.strip():
        description = None

    violations: list[dict] = []

    v = _check_as001(name)
    if v:
        violations.append(v)

    v = _check_as002(name, path)
    if v:
        violations.append(v)

    v = _check_as003(description)
    if v:
        violations.append(v)

    v = _check_as004(description, raw_description_line)
    if v:
        violations.append(v)

    v = _check_as005(body_lines)
    if v:
        violations.append(v)

    v = _check_as006(path)
    if v:
        violations.append(v)

    return violations


# Alias for plan 02-02 spec compatibility (run_as_series is the plan name,
# check_skill_md is what the tests actually import).
def run_as_series(path: pathlib.Path, frontmatter: dict, body_lines: list[str]) -> list[dict]:
    """Run AS-series rules given pre-parsed frontmatter and body lines.

    This is a lower-level entry point for callers that have already parsed
    the frontmatter. check_skill_md() is preferred for file-based callers.

    Returns:
        List of violation dicts, each with keys: code, severity, message.
    """
    name: str | None = frontmatter.get("name") or None
    description: str | None = frontmatter.get("description") or None

    if name is not None and not name.strip():
        name = None
    if description is not None and not description.strip():
        description = None

    violations: list[dict] = []

    v = _check_as001(name)
    if v:
        violations.append(v)

    v = _check_as002(name, path)
    if v:
        violations.append(v)

    v = _check_as003(description)
    if v:
        violations.append(v)

    v = _check_as004(description)
    if v:
        violations.append(v)

    v = _check_as005(body_lines)
    if v:
        violations.append(v)

    v = _check_as006(path)
    if v:
        violations.append(v)

    return violations


__all__ = ["AS_RULES", "check_skill_md", "run_as_series"]
