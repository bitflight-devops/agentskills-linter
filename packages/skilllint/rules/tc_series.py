"""TC-series token count rules (TC001).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

TC001 is emitted by ``MarkdownTokenCounter`` in ``plugin_validator.py``.
Detection requires reading file content from the filesystem and counting tokens
using the ``count_tokens()`` utility.  None of that information is available
from frontmatter alone, so the validator function registered here is a
**registration-only stub** — it exists to make rule metadata available via
``RULE_REGISTRY`` (and therefore via ``skilllint rule TC001``) without
duplicating the detection logic that belongs in the filesystem-owning
``MarkdownTokenCounter`` class.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | TC001 | Token count info (total, frontmatter, body)               | info      |
    +-------+-----------------------------------------------------------+-----------+

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

_TC_DOCS_BASE = "https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md"


def _docs_url(code: str) -> str:
    """Return the documentation URL for a TC rule code.

    Args:
        code: Rule code string (e.g., "TC001").

    Returns:
        Full URL with anchor for the error code documentation.
    """
    return f"{_TC_DOCS_BASE}#{code.lower()}"


# ---------------------------------------------------------------------------
# TC001 — Token count info (total, frontmatter, body)
# ---------------------------------------------------------------------------


@skilllint_rule(
    "TC001",
    severity="info",
    category="token-count",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _TC_DOCS_BASE},
)
def check_tc001(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## TC001 — Token count info

    Reports the total token count of a markdown file, broken down into
    frontmatter tokens and body tokens.  This is an informational rule — it
    always passes and never blocks validation.  The message format is:

    ```
    Total: <N> tokens (frontmatter: <F>, body: <B>)
    ```

    Token counts are computed using ``tiktoken`` (cl100k_base encoding by
    default) via the ``count_tokens()`` utility in ``skilllint.token_counter``.
    The frontmatter count is derived as ``total - body``, where ``body`` is
    measured on the content after the closing ``---`` delimiter.

    **Source:** ``MarkdownTokenCounter.validate`` in ``plugin_validator.py``
    — reads file content via ``path.read_text()``, splits frontmatter from
    body using ``extract_frontmatter()``, and counts tokens for each section.

    **Fix:** No action required.  TC001 is informational only.  If the body
    token count approaches the ``TOKEN_WARNING_THRESHOLD`` or
    ``TOKEN_ERROR_THRESHOLD`` defined in ``skilllint.token_counter``, consider
    splitting the file or moving content to ``references/``.

    Returns:
        Always an empty list.  TC001 is emitted by ``MarkdownTokenCounter``
        in ``plugin_validator.py`` after reading file content and counting
        tokens; this function exists for rule metadata registration only.

    <!-- examples: TC001 -->
    """
    # Detection requires reading file content via path.read_text() and
    # counting tokens using count_tokens() from skilllint.token_counter.
    # Owned by MarkdownTokenCounter in plugin_validator.py.
    return []


__all__ = ["check_tc001"]
