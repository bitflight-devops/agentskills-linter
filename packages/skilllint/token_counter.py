"""First-class token counting module for skilllint.

Token counts are a first-class concern for loading cost visibility. Frontmatter,
body, total skill file collections, and other contexts all expose token counts
to users so they can reason about context window impact.

This module is the single source of truth for:
- The shared tiktoken cl100k_base encoding
- Token threshold constants (TOKEN_WARNING_THRESHOLD, TOKEN_ERROR_THRESHOLD)
- Low-level token counting (count_tokens)
- File-level counting (count_file_tokens)
- Skill-level structured counting (count_skill_tokens, TokenCounts)

Design note: plugin_validator imports from this module rather than token_utils
to avoid a circular import (plugin_validator imports rules.as_series, which
imports token_counter — importing from plugin_validator back would be circular).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import tiktoken

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Shared encoding
# ---------------------------------------------------------------------------

_ENCODING_NAME = "cl100k_base"

# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------

#: Body token count at which AS005 / SK006 emit a warning.
TOKEN_WARNING_THRESHOLD: int = 4400

#: Body token count at which AS005 / SK007 emit an error.
TOKEN_ERROR_THRESHOLD: int = 8800

# ---------------------------------------------------------------------------
# Low-level counting
# ---------------------------------------------------------------------------


def count_tokens(text: str) -> int:
    """Count tokens in *text* using the cl100k_base encoding.

    Args:
        text: Text content to count tokens in.

    Returns:
        Number of tokens in *text*.
    """
    encoding = tiktoken.get_encoding(_ENCODING_NAME)
    return len(encoding.encode(text))


# ---------------------------------------------------------------------------
# Structured result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TokenCounts:
    """Token counts for a skill file broken down by section.

    Attributes:
        total: Total tokens in the full file (frontmatter + body).
        frontmatter: Tokens in the frontmatter block only.
        body: Tokens in the body (everything after the closing ``---``).
    """

    total: int
    frontmatter: int
    body: int


# ---------------------------------------------------------------------------
# Frontmatter splitter (minimal, no external deps)
# ---------------------------------------------------------------------------

_FRONTMATTER_CLOSE_RE = re.compile(r"\n---\s*\n")


def _split_frontmatter_body(content: str) -> tuple[str, str]:
    """Split *content* into (frontmatter_text, body_text).

    Returns:
        A 2-tuple ``(frontmatter, body)`` where *frontmatter* is the raw text
        inside the ``---`` delimiters (empty string if none) and *body* is
        everything after the closing ``---``.
    """
    if not content.startswith("---"):
        return "", content

    match = _FRONTMATTER_CLOSE_RE.search(content[3:])
    if match is None:
        # Unclosed frontmatter — treat whole file as frontmatter, body is empty
        return content, ""

    # content[3:] offset means match positions are relative to after the opening ---
    # match.end() points to just after the closing ---\n in the shifted string
    split_pos = 3 + match.end()
    frontmatter = content[3 : 3 + match.start()]  # between opening --- and closing ---
    body = content[split_pos:]
    return frontmatter, body


# ---------------------------------------------------------------------------
# File-level counting
# ---------------------------------------------------------------------------


def count_file_tokens(path: Path, *, body_only: bool = False) -> int | None:
    """Count tokens in a file.

    Args:
        path: Path to the file to read.
        body_only: When True, strip frontmatter and count only the body.
            This matches what ComplexityValidator measures for threshold
            comparisons.

    Returns:
        Token count (body or total), or None if the file could not be read.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    if body_only:
        _, body = _split_frontmatter_body(content)
        return count_tokens(body)

    return count_tokens(content)


# ---------------------------------------------------------------------------
# Skill-level structured counting
# ---------------------------------------------------------------------------


def count_skill_tokens(content: str) -> TokenCounts:
    """Count tokens in a skill file, split by frontmatter and body.

    Args:
        content: Full text content of the skill file (SKILL.md or similar).

    Returns:
        :class:`TokenCounts` with ``total``, ``frontmatter``, and ``body`` fields.
    """
    _frontmatter_text, body_text = _split_frontmatter_body(content)
    total = count_tokens(content)
    body = count_tokens(body_text)
    frontmatter = total - body
    return TokenCounts(total=total, frontmatter=frontmatter, body=body)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "TOKEN_ERROR_THRESHOLD",
    "TOKEN_WARNING_THRESHOLD",
    "TokenCounts",
    "count_file_tokens",
    "count_skill_tokens",
    "count_tokens",
]
