"""
AS-series rule validation for agentskills.io SKILL.md files.

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

import pathlib
import re

# ---------------------------------------------------------------------------
# Rule registry — maps code to human-readable description
# ---------------------------------------------------------------------------

AS_RULES: dict[str, str] = {
    "AS001": "Skill name must be lowercase alphanumeric with hyphens only, 1-64 chars, no consecutive hyphens",
    "AS002": "Skill name must match the parent directory name",
    "AS003": "description field must be present and non-empty",
    "AS004": "description must not contain HTML tags (< or >)",
    "AS005": "SKILL.md body exceeds 500 lines — consider splitting into sub-skills",
    "AS006": "No eval_queries.json found — add evaluation queries for quality assurance",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
_CONSECUTIVE_HYPHENS_RE = re.compile(r"--")


def _parse_skill_md(path: pathlib.Path) -> tuple[dict, list[str]]:
    """Parse a SKILL.md file into frontmatter dict and body lines.

    Frontmatter is delimited by leading '---' lines. Everything after
    the closing '---' is the body.

    Returns:
        (frontmatter, body_lines) where frontmatter is a dict of parsed
        YAML fields and body_lines is a list of non-empty content lines
        after the frontmatter block.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    frontmatter: dict = {}
    body_lines: list[str] = []

    if not lines or lines[0].strip() != "---":
        # No frontmatter — treat entire file as body
        return {}, lines

    # Find closing '---'
    close_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            close_idx = i
            break

    if close_idx is None:
        # Unclosed frontmatter — parse what we can, no body
        return {}, []

    # Parse frontmatter lines as simple key: value YAML
    for line in lines[1:close_idx]:
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip()

    body_lines = lines[close_idx + 1 :]

    return frontmatter, body_lines


def _violation(code: str, severity: str, message: str) -> dict:
    return {"code": code, "severity": severity, "message": message}


# ---------------------------------------------------------------------------
# Individual rule checks
# ---------------------------------------------------------------------------


def _check_as001(name: str | None) -> dict | None:
    """AS001: name format — lowercase alphanumeric + hyphens, 1-64 chars, no consecutive hyphens."""
    if name is None:
        return _violation("AS001", "error", "name field is missing")

    if len(name) == 0 or len(name) > 64:
        return _violation(
            "AS001",
            "error",
            f"name '{name}' must be 1-64 characters long (got {len(name)})",
        )

    if _CONSECUTIVE_HYPHENS_RE.search(name):
        return _violation(
            "AS001",
            "error",
            f"name '{name}' must not contain consecutive hyphens",
        )

    if not _NAME_RE.match(name):
        return _violation(
            "AS001",
            "error",
            f"name '{name}' must match ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ "
            "(lowercase letters, digits, and hyphens only)",
        )

    return None


def _check_as002(name: str | None, path: pathlib.Path) -> dict | None:
    """AS002: name must equal the parent directory name."""
    if name is None:
        return None  # AS001 already covers missing name

    dir_name = path.parent.name
    if name != dir_name:
        return _violation(
            "AS002",
            "error",
            f"name '{name}' does not match parent directory name '{dir_name}'",
        )

    return None


def _check_as003(description: str | None) -> dict | None:
    """AS003: description must be present and non-empty."""
    if description is None or description.strip() == "":
        return _violation(
            "AS003",
            "error",
            "description field must be present and non-empty",
        )

    return None


def _check_as004(description: str | None) -> dict | None:
    """AS004: description must not contain HTML tags (< or >)."""
    if description is None:
        return None  # AS003 already covers missing description

    if "<" in description or ">" in description:
        return _violation(
            "AS004",
            "error",
            "description must not contain HTML tags (< or > characters detected)",
        )

    return None


def _check_as005(body_lines: list[str]) -> dict | None:
    """AS005: body length > 500 lines produces a warning."""
    if len(body_lines) > 500:
        return _violation(
            "AS005",
            "warning",
            f"SKILL.md body is {len(body_lines)} lines — exceeds 500 line limit; "
            "consider splitting into sub-skills",
        )

    return None


def _check_as006(path: pathlib.Path) -> dict | None:
    """AS006: no eval_queries.json (or *eval*.json / *queries*.json) in skill directory."""
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

    return _violation(
        "AS006",
        "info",
        "No eval_queries.json found in skill directory — add evaluation queries "
        "to enable automated quality assessment",
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
    """
    frontmatter, body_lines = _parse_skill_md(path)

    name: str | None = frontmatter.get("name") or None
    description: str | None = frontmatter.get("description") or None

    # Normalise empty strings to None
    if name is not None and name.strip() == "":
        name = None
    if description is not None and description.strip() == "":
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


# Alias for plan 02-02 spec compatibility (run_as_series is the plan name,
# check_skill_md is what the tests actually import).
def run_as_series(
    path: pathlib.Path,
    frontmatter: dict,
    body_lines: list[str],
) -> list[dict]:
    """Run AS-series rules given pre-parsed frontmatter and body lines.

    This is a lower-level entry point for callers that have already parsed
    the frontmatter. check_skill_md() is preferred for file-based callers.
    """
    name: str | None = frontmatter.get("name") or None
    description: str | None = frontmatter.get("description") or None

    if name is not None and name.strip() == "":
        name = None
    if description is not None and description.strip() == "":
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
