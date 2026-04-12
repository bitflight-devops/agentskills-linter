"""LK-series internal link rules (LK001-LK002).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

LK001 and LK002 are emitted by ``InternalLinkValidator`` in
``plugin_validator.py`` after reading file content and resolving filesystem
paths.  The validator functions registered here are **registration-only
stubs** — they exist to make rule metadata available via ``RULE_REGISTRY``
(and therefore via ``skilllint rule LKxxx``) without duplicating the
detection logic that requires live file I/O.

Rule IDs and default severities:
    +-------+-----------------------------------------------+-----------+
    | ID    | Summary                                       | Severity  |
    +-------+-----------------------------------------------+-----------+
    | LK001 | Broken internal link (file does not exist)    | error     |
    | LK002 | Relative link missing ./ prefix               | warning   |
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

_LK_DOCS_BASE = "https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md"


def _docs_url(code: str) -> str:
    """Return the documentation URL for an LK rule code.

    Args:
        code: Rule code string (e.g., "LK001").

    Returns:
        Full URL with anchor for the error code documentation.
    """
    return f"{_LK_DOCS_BASE}#{code.lower()}"


# ---------------------------------------------------------------------------
# LK001 — Broken internal link (file does not exist)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "LK001",
    severity="error",
    category="link",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _LK_DOCS_BASE},
)
def check_lk001(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## LK001 — Broken internal link

    A relative markdown link in `SKILL.md` points to a file that does not
    exist on the filesystem.  Broken links prevent readers and tools from
    following references and indicate stale documentation.

    **Source:** `InternalLinkValidator` in `plugin_validator.py` — resolves
    each relative link path against the `SKILL.md` parent directory and
    checks for existence via ``Path.exists()``.

    **Fix:** Either create the missing file at the referenced path, or
    correct the link to point to an existing file:

    ```markdown
    <!-- Before (file does not exist) -->
    See [Reference](./references/missing-file.md)

    <!-- After (file exists) -->
    See [Reference](./references/existing-file.md)
    ```

    Returns:
        Always an empty list.  LK001 is emitted by ``InternalLinkValidator``
        in ``plugin_validator.py`` after resolving the linked path on the
        filesystem; this function exists for rule metadata registration only.

    <!-- examples: LK001 -->
    """
    return []


# ---------------------------------------------------------------------------
# LK002 — Relative link missing ./ prefix
# ---------------------------------------------------------------------------


@skilllint_rule(
    "LK002",
    severity="warning",
    category="link",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _LK_DOCS_BASE},
)
def check_lk002(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## LK002 — Relative link missing ./ prefix

    A relative markdown link does not start with `./` or `../`.  The `./`
    prefix makes the relative nature of the link explicit and avoids
    ambiguity on systems that interpret bare names differently.

    **Source:** `InternalLinkValidator` in `plugin_validator.py` — checks
    each relative link URL for a leading `./` or `../` prefix.

    **Fix:** Add the `./` prefix to the relative link:

    ```markdown
    <!-- Before -->
    See [Reference](references/my-doc.md)

    <!-- After -->
    See [Reference](./references/my-doc.md)
    ```

    Links that already start with `../` (cross-directory references) are
    valid and do not trigger this warning.

    Returns:
        Always an empty list.  LK002 is emitted by ``InternalLinkValidator``
        in ``plugin_validator.py`` after inspecting the link URL prefix; this
        function exists for rule metadata registration only.

    <!-- examples: LK002 -->
    """
    return []


__all__ = ["check_lk001", "check_lk002"]
