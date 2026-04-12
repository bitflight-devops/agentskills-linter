"""SK-series skill quality rules (SK001-SK009).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects. Functions receive the parsed frontmatter dict,
the file path, and additional keyword arguments as needed.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | SK001 | Skill name contains uppercase characters                  | error     |
    | SK002 | Skill name contains underscores (use hyphens)             | error     |
    | SK003 | Skill name has invalid format                             | error     |
    | SK004 | Description too short or exceeds recommended length       | warning   |
    | SK005 | Description missing trigger phrases                       | warning   |
    | SK006 | Skill body exceeds token warning threshold                | warning   |
    | SK007 | Skill body exceeds token error threshold (must split)     | error     |
    | SK008 | Skill directory name violates naming convention           | error     |
    | SK009 | Plugin uses manual skill selection (informational)        | info      |
    +-------+-----------------------------------------------------------+-----------+

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from skilllint.rule_registry import skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

_SKILLS_SPEC_URL = "https://docs.anthropic.com/en/docs/claude-code/skills"
_SK_DOCS_BASE = "https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md"

# Name pattern: lowercase alphanumeric with hyphens, no leading/trailing/consecutive hyphens.
# Source: skills.md — "Lowercase letters, numbers, and hyphens only (max 64 characters)"
_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Directory naming pattern: same constraints as skill name.
# Source: agentskills.io skill directory convention.
_DIR_CONVENTION_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _docs_url(code: str) -> str:
    """Return the documentation URL for an SK rule code.

    Args:
        code: Rule code string (e.g., "SK001").

    Returns:
        Full URL with anchor for the error code documentation.
    """
    return f"{_SK_DOCS_BASE}#{code.lower()}"


# ---------------------------------------------------------------------------
# SK001 — Name contains uppercase characters
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SK001",
    severity="error",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk001(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK001 — Skill name contains uppercase characters

    The `name` field in the frontmatter must use only lowercase letters.
    Uppercase characters violate the skill naming convention and may cause
    discovery or resolution failures on case-sensitive systems.

    **Source:** skills.md — "name — Lowercase letters, numbers, and hyphens only (max 64 characters)."

    **Fix:** Convert the name to lowercase:

    ```yaml
    # Before
    name: MySkill

    # After
    name: my-skill
    ```

    Returns:
        List containing one error issue when the name contains uppercase
        characters; empty otherwise.

    <!-- examples: SK001 -->
    """
    # Deferred import to break circular dependency:
    # plugin_validator imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    name_val = frontmatter.get("name")
    if not isinstance(name_val, str) or not name_val:
        return []

    if any(c.isupper() for c in name_val):
        return [
            ValidationIssue(
                field="name",
                severity="error",
                message="Name contains uppercase characters",
                code="SK001",
                docs_url=_docs_url("SK001"),
                suggestion=f"Use lowercase only (e.g., '{name_val.lower()}' not '{name_val}')",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# SK002 — Name contains underscores
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SK002",
    severity="error",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk002(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK002 — Skill name contains underscores

    The `name` field must use hyphens (`-`) as word separators, not
    underscores (`_`). Underscores are not part of the allowed character
    set for skill names.

    **Source:** skills.md — "name — Lowercase letters, numbers, and hyphens only (max 64 characters)."

    **Fix:** Replace underscores with hyphens:

    ```yaml
    # Before
    name: my_skill_name

    # After
    name: my-skill-name
    ```

    Returns:
        List containing one error issue when the name contains underscores;
        empty otherwise.

    <!-- examples: SK002 -->
    """
    # Deferred import to break circular dependency:
    # plugin_validator imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    name_val = frontmatter.get("name")
    if not isinstance(name_val, str) or not name_val:
        return []

    if "_" in name_val:
        return [
            ValidationIssue(
                field="name",
                severity="error",
                message="Name contains underscores (use hyphens instead)",
                code="SK002",
                docs_url=_docs_url("SK002"),
                suggestion=f"Replace underscores with hyphens: '{name_val.replace('_', '-')}'",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# SK003 — Name has invalid format (leading/trailing/consecutive hyphens,
#         empty name, or generic pattern mismatch)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SK003",
    severity="error",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk003(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK003 — Skill name has invalid format

    The `name` field must not start or end with a hyphen, must not contain
    consecutive hyphens, and must not be empty. The allowed pattern is
    `^[a-z0-9]+(-[a-z0-9]+)*$`.

    **Source:** skills.md — "name — Lowercase letters, numbers, and hyphens only (max 64 characters)."

    **Fix:** Correct the name to conform to the pattern:

    ```yaml
    # Before (leading hyphen)
    name: -my-skill

    # After
    name: my-skill
    ```

    Returns:
        List of error issues for each format violation found; empty when the
        name is absent (SK001/FM001 covers that), or valid.

    <!-- examples: SK003 -->
    """
    # Deferred import to break circular dependency:
    # plugin_validator imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint._spec_constants import MAX_NAME_LENGTH  # noqa: PLC0415
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    name_val = frontmatter.get("name")
    if not isinstance(name_val, str):
        return []

    issues: list[ValidationIssue] = []

    if not name_val:
        issues.append(
            ValidationIssue(
                field="name",
                severity="error",
                message="Name field is empty",
                code="SK003",
                docs_url=_docs_url("SK003"),
                suggestion="Provide a non-empty name using lowercase letters, numbers, and hyphens",
            )
        )
        return issues

    # Source: agentskills.io spec / _spec_constants.MAX_NAME_LENGTH = 64.
    # FM010 and AS001 enforce the same 64-char ceiling; SK003 must too.
    if len(name_val) > MAX_NAME_LENGTH:
        issues.append(
            ValidationIssue(
                field="name",
                severity="error",
                message=f"Name exceeds maximum length of {MAX_NAME_LENGTH} characters (got {len(name_val)})",
                code="SK003",
                docs_url=_docs_url("SK003"),
                suggestion=f"Shorten the name to {MAX_NAME_LENGTH} characters or less",
            )
        )
        return issues

    if name_val.startswith("-"):
        issues.append(
            ValidationIssue(
                field="name",
                severity="error",
                message="Name has leading hyphen",
                code="SK003",
                docs_url=_docs_url("SK003"),
                suggestion=f"Remove leading hyphen: '{name_val.lstrip('-')}'",
            )
        )

    if name_val.endswith("-"):
        issues.append(
            ValidationIssue(
                field="name",
                severity="error",
                message="Name has trailing hyphen",
                code="SK003",
                docs_url=_docs_url("SK003"),
                suggestion=f"Remove trailing hyphen: '{name_val.rstrip('-')}'",
            )
        )

    if "--" in name_val:
        issues.append(
            ValidationIssue(
                field="name",
                severity="error",
                message="Name has consecutive hyphens",
                code="SK003",
                docs_url=_docs_url("SK003"),
                suggestion="Use single hyphens only (e.g., 'test-skill' not 'test--skill')",
            )
        )

    if not issues and not _NAME_RE.match(name_val):
        issues.append(
            ValidationIssue(
                field="name",
                severity="error",
                message="Name format invalid",
                code="SK003",
                docs_url=_docs_url("SK003"),
                suggestion="Use lowercase letters, numbers, and hyphens only (e.g., 'my-skill-name')",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# SK004 — Description too short or exceeds recommended length
# ---------------------------------------------------------------------------

# Minimum length for description field.
# Source: Architecture lines 349-350 — minimum 20 characters for SK004 quality
# threshold. (Distinct from _spec_constants.MIN_DESCRIPTION_LENGTH = 1, which is
# the agentskills.io absolute minimum used by FM-series existence checks.)
_MIN_DESCRIPTION_LENGTH = 20


@skilllint_rule(
    "SK004",
    severity="warning",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk004(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK004 — Description too short or exceeds recommended length

    For SKILL and AGENT files, the `description` must be at least
    20 characters long. Descriptions shorter than this provide insufficient
    context for Claude Code to determine when to load the skill. Descriptions
    longer than the recommended 1024 characters may be truncated or reduce
    context efficiency.

    **Source:** Architecture lines 349-350 — minimum 20 characters.

    **Source:** `frontmatter_core.RECOMMENDED_DESCRIPTION_LENGTH` = 1024.

    **Fix:** Write a concise, informative description between 20 and 1024
    characters. Front-load the most important information. Run
    `/plugin-creator:write-frontmatter-description` to generate an optimized
    description with proper length and trigger phrases.

    Returns:
        List of warning issues for length violations; empty when the
        description is absent, not a string, or within the allowed range.

    <!-- examples: SK004 -->
    """
    # Deferred import to break circular dependency:
    # plugin_validator imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.frontmatter_core import RECOMMENDED_DESCRIPTION_LENGTH  # noqa: PLC0415
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    if file_type not in {"skill", "agent"}:
        return []

    desc_val = frontmatter.get("description")
    if not isinstance(desc_val, str):
        return []

    issues: list[ValidationIssue] = []
    desc_len = len(desc_val)

    if desc_len < _MIN_DESCRIPTION_LENGTH:
        issues.append(
            ValidationIssue(
                field="description",
                severity="warning",
                message=f"Description too short (minimum {_MIN_DESCRIPTION_LENGTH} characters, got {desc_len})",
                code="SK004",
                docs_url=_docs_url("SK004"),
                suggestion="Run /plugin-creator:write-frontmatter-description to generate an optimized description",
            )
        )
    elif desc_len > RECOMMENDED_DESCRIPTION_LENGTH:
        issues.append(
            ValidationIssue(
                field="description",
                severity="warning",
                message=f"Exceeds recommended length of {RECOMMENDED_DESCRIPTION_LENGTH} characters (got {desc_len})",
                code="SK004",
                docs_url=_docs_url("SK004"),
                suggestion=f"Front-load critical information in first {RECOMMENDED_DESCRIPTION_LENGTH} characters. Run /plugin-creator:write-frontmatter-description to generate an optimized description",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# SK005 — Description missing trigger phrases
# ---------------------------------------------------------------------------

# Trigger phrases that must appear in a skill's description.
# Source: Architecture line 357 — trigger phrases enable Claude Code to decide
# when to auto-load a skill from context.
_REQUIRED_TRIGGER_PHRASES = [
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


@skilllint_rule(
    "SK005",
    severity="warning",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk005(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK005 — Description missing trigger phrases

    Skill descriptions should include a trigger phrase that tells Claude Code
    when to load the skill. Without trigger phrases, the skill may not be
    activated at the right moment in a conversation.

    Required trigger phrases (at least one must appear):
    `use when`, `use this`, `use on`, `used when`, `used by`, `when`,
    `trigger`, `activate`, `load this`, `load when`, `invoke`.

    **Source:** Architecture line 357 — trigger phrase requirements.

    **Fix:** Add a trigger phrase to the description:

    ```yaml
    description: "Use when building Python CLI tools. Provides patterns for
      argument parsing, output formatting, and error handling."
    ```

    Run `/plugin-creator:write-frontmatter-description` to generate a
    compliant description automatically.

    Returns:
        List containing one warning when no trigger phrase is found in a
        SKILL file's description; empty otherwise.

    <!-- examples: SK005 -->
    """
    # Deferred import to break circular dependency:
    # plugin_validator imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    if file_type != "skill":
        return []

    desc_val = frontmatter.get("description")
    if not isinstance(desc_val, str):
        return []

    desc_lower = desc_val.lower()
    if any(phrase in desc_lower for phrase in _REQUIRED_TRIGGER_PHRASES):
        return []

    return [
        ValidationIssue(
            field="description",
            severity="warning",
            message="Description missing trigger phrases",
            code="SK005",
            docs_url=_docs_url("SK005"),
            suggestion=f"Required trigger phrases: {', '.join(_REQUIRED_TRIGGER_PHRASES)}. Run /plugin-creator:write-frontmatter-description to generate a compliant description",
        )
    ]


# ---------------------------------------------------------------------------
# SK006 — Token count exceeds warning threshold
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SK006",
    severity="warning",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk006(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK006 — Skill body exceeds token warning threshold

    The skill body is larger than Anthropic's official skills. Skills with
    very large bodies increase context consumption and may slow response
    times. Consider splitting the skill or moving content to `references/`.

    **Source:** `token_counter.TOKEN_WARNING_THRESHOLD` — sourced from
    `skilllint.token_counter` module.

    **Fix:** Review whether the content can be moved to `references/` or
    whether the skill covers multiple domains that could be separated into
    distinct skills.

    Returns:
        Always an empty list. SK006 is emitted by `ComplexityValidator` in
        `plugin_validator.py` after computing the body token count; this
        function exists for rule metadata registration only.

    <!-- examples: SK006 -->
    """
    return []


# ---------------------------------------------------------------------------
# SK007 — Token count exceeds error threshold (must split)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SK007",
    severity="error",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk007(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK007 — Skill body exceeds token error threshold

    The skill body has grown so large that it exceeds the hard token limit.
    At this size, loading the skill risks hitting context-window limits and
    the skill must be split into multiple smaller skills.

    **Source:** `token_counter.TOKEN_ERROR_THRESHOLD` — sourced from
    `skilllint.token_counter` module.

    **Fix:** Run `/plugin-creator:refactor-skill` to split the skill into
    multiple smaller, focused skills.

    Returns:
        Always an empty list. SK007 is emitted by `ComplexityValidator` in
        `plugin_validator.py` after computing the body token count; this
        function exists for rule metadata registration only.

    <!-- examples: SK007 -->
    """
    return []


# ---------------------------------------------------------------------------
# SK008 — Skill directory name violates naming convention
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SK008",
    severity="error",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk008(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK008 — Skill directory name violates naming convention

    The directory containing `SKILL.md` must follow the same naming
    convention as the `name` field: lowercase letters, digits, and hyphens
    only; no leading, trailing, or consecutive hyphens; no underscores;
    maximum 40 characters.

    **Source:** agentskills.io skill directory convention; `MAX_SKILL_NAME_LENGTH = 40`
    from `frontmatter_core`.

    **Fix:** Rename the skill directory to follow the convention:

    ```bash
    # Before
    skills/My_Skill/SKILL.md

    # After
    skills/my-skill/SKILL.md
    ```

    Returns:
        Always an empty list. SK008 is emitted by `_check_skill_name_and_directory`
        in `plugin_validator.py` after inspecting the filesystem path; this
        function exists for rule metadata registration only.

    <!-- examples: SK008 -->
    """
    return []


# ---------------------------------------------------------------------------
# SK009 — Plugin uses manual skill selection (informational)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SK009",
    severity="info",
    category="skill",
    platforms=["agentskills"],
    authority={"origin": "anthropic.com", "reference": _SKILLS_SPEC_URL},
)
def check_sk009(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## SK009 — Plugin uses manual skill selection

    When the `skills` field is present in `plugin.json`, Claude Code uses
    only the explicitly listed skills and will not auto-discover new skills
    added to `skills/`. This is an `info` notice, not an error — manual
    selection is a valid configuration choice.

    **Source:** Claude Code plugin documentation — auto-discovery behaviour
    when `skills` field is omitted from `plugin.json`.

    **Fix (optional):** To switch to auto-discovery mode, remove the
    `skills` field from `plugin.json`. Claude Code will then discover all
    skills under `./skills/` automatically.

    Returns:
        Always an empty list. SK009 is emitted by `PluginRegistrationValidator`
        in `plugin_validator.py` when `plugin.json` contains a `skills` key;
        this function exists for rule metadata registration only.

    <!-- examples: SK009 -->
    """
    return []


__all__ = [
    "check_sk001",
    "check_sk002",
    "check_sk003",
    "check_sk004",
    "check_sk005",
    "check_sk006",
    "check_sk007",
    "check_sk008",
    "check_sk009",
]
