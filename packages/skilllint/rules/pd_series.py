"""PD-series progressive disclosure rules (PD001-PD003).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

PD001, PD002, and PD003 are emitted by ``ProgressiveDisclosureValidator`` in
``plugin_validator.py`` after checking whether ``references/``, ``examples/``,
and ``scripts/`` directories exist under the skill directory.  The validator
functions registered here are **registration-only stubs** — they exist to make
rule metadata available via ``RULE_REGISTRY`` (and therefore via
``skilllint rule PDxxx``) without duplicating the detection logic that requires
live filesystem path checks.

Rule IDs and default severities:
    +-------+-----------------------------------------------+-----------+
    | ID    | Summary                                       | Severity  |
    +-------+-----------------------------------------------+-----------+
    | PD001 | No references/ directory found                | info      |
    | PD002 | No examples/ directory found                  | info      |
    | PD003 | No scripts/ directory found                   | info      |
    +-------+-----------------------------------------------+-----------+

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skilllint.rule_registry import skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

_PD_DOCS_BASE = "https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md"


def _docs_url(code: str) -> str:
    """Return the documentation URL for a PD rule code.

    Args:
        code: Rule code string (e.g., "PD001").

    Returns:
        Full URL with anchor for the error code documentation.
    """
    return f"{_PD_DOCS_BASE}#{code.lower()}"


# ---------------------------------------------------------------------------
# PD001 — No references/ directory found
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PD001",
    severity="info",
    category="progressive-disclosure",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PD_DOCS_BASE},
)
def check_pd001(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## PD001 — No references/ directory found

    The skill directory does not contain a ``references/`` subdirectory.
    A ``references/`` directory provides supporting documentation, external
    links, and background material that readers can explore on demand without
    cluttering the main ``SKILL.md``.

    This is an informational notice, not an error.  Missing the directory does
    not prevent the skill from functioning; it is a recommendation for better
    content organisation.

    **Source:** ``ProgressiveDisclosureValidator`` in ``plugin_validator.py`` —
    checks for the presence of ``references/`` under the skill directory.

    **Fix:** Create a ``references/`` directory and populate it with supporting
    documentation:

    ```
    my-skill/
      SKILL.md
      references/
        background.md
        external-links.md
    ```

    Returns:
        Always an empty list.  PD001 is emitted by
        ``ProgressiveDisclosureValidator`` in ``plugin_validator.py`` after
        checking directory existence on the filesystem; this function exists
        for rule metadata registration only.

    <!-- examples: PD001 -->
    """
    return []


# ---------------------------------------------------------------------------
# PD002 — No examples/ directory found
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PD002",
    severity="info",
    category="progressive-disclosure",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PD_DOCS_BASE},
)
def check_pd002(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## PD002 — No examples/ directory found

    The skill directory does not contain an ``examples/`` subdirectory.
    An ``examples/`` directory holds concrete usage samples, demo inputs, and
    worked scenarios that help users understand how to invoke the skill
    effectively.

    This is an informational notice, not an error.  Missing the directory does
    not prevent the skill from functioning; it is a recommendation for better
    content organisation.

    **Source:** ``ProgressiveDisclosureValidator`` in ``plugin_validator.py`` —
    checks for the presence of ``examples/`` under the skill directory.

    **Fix:** Create an ``examples/`` directory and populate it with usage
    samples:

    ```
    my-skill/
      SKILL.md
      examples/
        basic-usage.md
        advanced-usage.md
    ```

    Returns:
        Always an empty list.  PD002 is emitted by
        ``ProgressiveDisclosureValidator`` in ``plugin_validator.py`` after
        checking directory existence on the filesystem; this function exists
        for rule metadata registration only.

    <!-- examples: PD002 -->
    """
    return []


# ---------------------------------------------------------------------------
# PD003 — No scripts/ directory found
# ---------------------------------------------------------------------------


@skilllint_rule(
    "PD003",
    severity="info",
    category="progressive-disclosure",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _PD_DOCS_BASE},
)
def check_pd003(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## PD003 — No scripts/ directory found

    The skill directory does not contain a ``scripts/`` subdirectory.
    A ``scripts/`` directory holds helper scripts, automation utilities, and
    supporting code referenced or used by the skill.

    This is an informational notice, not an error.  Missing the directory does
    not prevent the skill from functioning; it is a recommendation for better
    content organisation.

    **Source:** ``ProgressiveDisclosureValidator`` in ``plugin_validator.py`` —
    checks for the presence of ``scripts/`` under the skill directory.

    **Fix:** Create a ``scripts/`` directory and populate it with helper
    scripts:

    ```
    my-skill/
      SKILL.md
      scripts/
        setup.sh
        run-example.py
    ```

    Returns:
        Always an empty list.  PD003 is emitted by
        ``ProgressiveDisclosureValidator`` in ``plugin_validator.py`` after
        checking directory existence on the filesystem; this function exists
        for rule metadata registration only.

    <!-- examples: PD003 -->
    """
    return []


__all__ = ["check_pd001", "check_pd002", "check_pd003"]
