"""Tests for skilllint.token_counter module.

Tests:
- _split_frontmatter_body edge cases (no frontmatter, unclosed, valid)
- count_file_tokens (normal, body_only, OSError, missing file)
- count_skill_tokens structured breakdown
- TokenCounts dataclass attributes

How: Creates temp files and exercises the public API directly.
Why: token_counter is the single source of truth for counting; its
     count_file_tokens and count_skill_tokens paths were previously
     untested, making threshold regressions invisible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from skilllint.token_counter import (
    TokenCounts,
    _split_frontmatter_body,
    count_file_tokens,
    count_skill_tokens,
    count_tokens,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestSplitFrontmatterBody:
    """Tests for the _split_frontmatter_body helper."""

    def test_no_frontmatter_returns_empty_fm_and_full_body(self) -> None:
        """Content without '---' yields empty frontmatter and full body."""
        content = "# Title\n\nSome body text.\n"
        fm, body = _split_frontmatter_body(content)
        assert fm == ""
        assert body == content

    def test_valid_frontmatter_splits_correctly(self) -> None:
        """Standard frontmatter block is split at the closing '---'."""
        content = "---\nname: test\n---\n\nBody here.\n"
        fm, body = _split_frontmatter_body(content)
        assert "name: test" in fm
        assert "Body here." in body

    def test_unclosed_frontmatter_returns_whole_file_as_fm(self) -> None:
        """When there is no closing '---', the whole file is frontmatter."""
        content = "---\nname: test\ndescription: missing closing delimiter\n"
        fm, body = _split_frontmatter_body(content)
        assert fm == content
        assert body == ""

    def test_empty_string_returns_empty_fm_and_body(self) -> None:
        """Empty string yields empty frontmatter and body."""
        fm, body = _split_frontmatter_body("")
        assert fm == ""
        assert body == ""

    def test_body_after_closing_delimiter_captured(self) -> None:
        """Everything after the closing '---\\n' ends up in body."""
        content = "---\nkey: val\n---\nline1\nline2\n"
        _, body = _split_frontmatter_body(content)
        assert "line1" in body
        assert "line2" in body


class TestCountFileTokens:
    """Tests for count_file_tokens."""

    def test_counts_tokens_in_file(self, tmp_path: Path) -> None:
        """Returns a positive integer for a non-empty file."""
        f = tmp_path / "test.md"
        f.write_text("Hello world, this is some content.\n", encoding="utf-8")
        result = count_file_tokens(f)
        assert isinstance(result, int)
        assert result > 0

    def test_body_only_excludes_frontmatter(self, tmp_path: Path) -> None:
        """body_only=True counts fewer tokens than the full file."""
        content = "---\nname: skill\ndescription: A skill\n---\n\nBody content here.\n"
        f = tmp_path / "skill.md"
        f.write_text(content, encoding="utf-8")

        total = count_file_tokens(f)
        body_only = count_file_tokens(f, body_only=True)

        assert isinstance(total, int)
        assert isinstance(body_only, int)
        assert total > body_only

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        """Returns None when the file does not exist."""
        result = count_file_tokens(tmp_path / "nonexistent.md")
        assert result is None

    def test_empty_file_returns_zero(self, tmp_path: Path) -> None:
        """Empty file yields 0 tokens."""
        f = tmp_path / "empty.md"
        f.write_text("", encoding="utf-8")
        result = count_file_tokens(f)
        assert result == 0

    def test_body_only_plain_markdown(self, tmp_path: Path) -> None:
        """body_only on a file without frontmatter counts the full content."""
        content = "# Title\n\nSome body text.\n"
        f = tmp_path / "plain.md"
        f.write_text(content, encoding="utf-8")

        total = count_file_tokens(f)
        body_only = count_file_tokens(f, body_only=True)

        # Without frontmatter, body == full content
        assert total == body_only


class TestCountSkillTokens:
    """Tests for count_skill_tokens."""

    def test_returns_token_counts_dataclass(self) -> None:
        """Returns a TokenCounts instance."""
        content = "---\nname: test\n---\n\nBody text.\n"
        result = count_skill_tokens(content)
        assert isinstance(result, TokenCounts)

    def test_total_equals_frontmatter_plus_body(self) -> None:
        """total == frontmatter + body always holds."""
        content = "---\nname: test\ndescription: A skill\n---\n\nBody content here.\n"
        result = count_skill_tokens(content)
        assert result.total == result.frontmatter + result.body

    def test_plain_content_has_zero_frontmatter(self) -> None:
        """Content without frontmatter has frontmatter == 0."""
        content = "# Title\n\nJust body text with no frontmatter.\n"
        result = count_skill_tokens(content)
        assert result.frontmatter == 0
        assert result.body == result.total

    def test_body_tokens_positive_for_non_empty_body(self) -> None:
        """body > 0 when the body section has content."""
        content = "---\nname: skill\n---\n\nSome body words here.\n"
        result = count_skill_tokens(content)
        assert result.body > 0

    def test_empty_content_returns_zeros(self) -> None:
        """Empty string returns all-zero TokenCounts."""
        result = count_skill_tokens("")
        assert result.total == 0
        assert result.frontmatter == 0
        assert result.body == 0


class TestTokenCounts:
    """Tests for the TokenCounts dataclass."""

    def test_is_frozen(self) -> None:
        """TokenCounts is immutable (frozen=True)."""
        import dataclasses

        tc = TokenCounts(total=10, frontmatter=3, body=7)
        with pytest.raises(dataclasses.FrozenInstanceError):
            tc.total = 99  # ty: ignore[invalid-assignment]

    def test_fields_accessible(self) -> None:
        """All three fields are readable."""
        tc = TokenCounts(total=100, frontmatter=20, body=80)
        assert tc.total == 100
        assert tc.frontmatter == 20
        assert tc.body == 80

    def test_equality(self) -> None:
        """Two TokenCounts with identical values compare equal."""
        a = TokenCounts(total=5, frontmatter=2, body=3)
        b = TokenCounts(total=5, frontmatter=2, body=3)
        assert a == b

    def test_count_tokens_function(self) -> None:
        """count_tokens returns a consistent, positive integer for a known string."""
        result = count_tokens("Hello world")
        assert isinstance(result, int)
        assert result > 0
        # Deterministic
        assert count_tokens("Hello world") == result
