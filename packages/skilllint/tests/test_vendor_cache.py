"""Tests for skilllint.vendor_cache — offline-first cache with section querying.

Tests:
- derive_page_name: URL to filesystem-safe name conversion
- find_latest: newest cached file lookup
- fetch_or_cached: full TTL / network / offline logic
- list_sections: markdown heading decomposition
- read_section: section lookup by heading text or slug
- format_section_index: plain-text section table
- verify_integrity: sidecar hash comparison
- NoCacheError: exception contract

How: Unit tests with tmp_path for file isolation, mocker fixture (pytest-mock) for
     network calls. skilllint.vendor_cache.SOURCES_DIR is monkeypatched to tmp_path
     for fetch_or_cached tests. skilllint.vendor_cache.fetch_url_text is patched for
     all network scenarios — never the underlying httpx directly.
Why: vendor_cache is the main entry point for all cached documentation reads used
     by agents and MCP servers; correctness here directly affects offline availability.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import httpx
import pytest

from skilllint.vendor_cache import (
    CacheStatus,
    IntegrityResult,
    IntegrityStatus,
    MarkdownSection,
    NoCacheError,
    derive_page_name,
    fetch_or_cached,
    find_latest,
    format_section_index,
    list_sections,
    read_section,
    verify_integrity,
)
from skilllint.vendor_io import sha256_hex

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _write_md(directory: Path, name: str, content: str) -> Path:
    """Write a markdown file to *directory* and return its path."""
    path = directory / name
    path.write_text(content, encoding="utf-8")
    return path


def _write_sidecar(md_path: Path, *, url: str, sha256: str, byte_count: int, fetched_at: str) -> Path:
    """Write a .meta.json sidecar alongside *md_path* and return the sidecar path."""
    sidecar = md_path.with_suffix(".meta.json")
    sidecar.write_text(
        json.dumps({"url": url, "fetched_at": fetched_at, "sha256": sha256, "byte_count": byte_count}), encoding="utf-8"
    )
    return sidecar


def _fresh_fetched_at() -> str:
    """Return a fetched_at timestamp 30 minutes ago (within any reasonable TTL)."""
    return (datetime.now(UTC) - timedelta(minutes=30)).isoformat()


def _stale_fetched_at() -> str:
    """Return a fetched_at timestamp 8 hours ago (well beyond the default 4-hour TTL)."""
    return (datetime.now(UTC) - timedelta(hours=8)).isoformat()


def _sidecar_for(content: str, url: str, fetched_at: str) -> dict[str, object]:
    """Build the sidecar dict for *content*."""
    return {
        "url": url,
        "fetched_at": fetched_at,
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
        "byte_count": len(content.encode()),
    }


# ---------------------------------------------------------------------------
# derive_page_name
# ---------------------------------------------------------------------------


class TestDerivePageName:
    """Tests for derive_page_name — URL to filesystem-safe name converter.

    Verifies the documented algorithm: strip common prefixes (/en/, /docs/, /api/),
    remove .md extension, join remaining segments with --, and replace non-safe
    characters with hyphens.
    """

    def test_derive_page_name_anthropic_settings(self) -> None:
        """derive_page_name strips /en/docs/ from docs.anthropic.com and joins with --.

        Tests: derive_page_name for docs.anthropic.com URL
        How: Pass the canonical settings URL, assert the exact expected name.
        Why: This name is used as the filename prefix in SOURCES_DIR; the wrong
             name prevents find_latest from locating existing cached files.
        """
        # Arrange
        url = "https://docs.anthropic.com/en/docs/claude-code/settings.md"

        # Act
        result = derive_page_name(url)

        # Assert
        assert result == "claude-code--settings"

    def test_derive_page_name_cursor_context_rules(self) -> None:
        """derive_page_name strips /docs/ from cursor.com URL.

        Tests: derive_page_name for cursor.com URL
        How: Pass a cursor.com documentation URL, assert result.
        Why: Cursor docs live under /docs/; the algorithm must strip that prefix.
        """
        # Arrange
        url = "https://cursor.com/docs/context/rules.md"

        # Act
        result = derive_page_name(url)

        # Assert
        assert result == "context--rules"

    def test_derive_page_name_claude_code_sub_agents(self) -> None:
        """derive_page_name strips /docs/en/ leaving a single segment.

        Tests: derive_page_name for code.claude.com multi-prefix URL
        How: Pass a URL with /docs/en/ prefixes, assert single-segment result.
        Why: /docs/en/ contains two common prefixes; both must be stripped iteratively.
        """
        # Arrange
        url = "https://code.claude.com/docs/en/sub-agents.md"

        # Act
        result = derive_page_name(url)

        # Assert
        assert result == "sub-agents"

    def test_derive_page_name_claude_code_hooks(self) -> None:
        """derive_page_name produces 'hooks' for the hooks documentation URL.

        Tests: derive_page_name for hooks URL
        How: Pass a URL with /docs/en/ prefixes, assert 'hooks' result.
        Why: Consistent single-segment names are the expected output when no path
             hierarchy remains after prefix stripping.
        """
        # Arrange
        url = "https://code.claude.com/docs/en/hooks.md"

        # Act
        result = derive_page_name(url)

        # Assert
        assert result == "hooks"

    def test_derive_page_name_strips_md_extension(self) -> None:
        """derive_page_name removes the .md extension from the result.

        Tests: derive_page_name extension stripping
        How: Verify the result does not end with '.md'.
        Why: Page names must not carry extensions so that glob patterns like
             '{name}-*.md' work correctly in find_latest.
        """
        # Arrange / Act
        result = derive_page_name("https://docs.anthropic.com/en/docs/settings.md")

        # Assert
        assert not result.endswith(".md")

    def test_derive_page_name_replaces_special_chars_with_hyphens(self) -> None:
        """derive_page_name replaces underscore and other non-safe chars with hyphens.

        Tests: derive_page_name special character replacement
        How: Pass a URL with an underscore in the page name, assert no underscores in result.
        Why: Filesystem-safe names must not contain characters that break glob patterns.
        """
        # Arrange
        url = "https://example.com/docs/some_page.md"

        # Act
        result = derive_page_name(url)

        # Assert
        assert "_" not in result

    def test_derive_page_name_single_segment(self) -> None:
        """derive_page_name returns the lone segment for a single-segment path.

        Tests: derive_page_name single segment
        How: Pass a URL with just /docs/overview.md, assert 'overview'.
        Why: Single-segment paths must not produce spurious '--' separators.
        """
        # Arrange / Act
        result = derive_page_name("https://example.com/docs/overview.md")

        # Assert
        assert result == "overview"


# ---------------------------------------------------------------------------
# find_latest
# ---------------------------------------------------------------------------


class TestFindLatest:
    """Tests for find_latest — most recent cached file locator.

    Verifies lexicographic sort on YYYY-MM-DD-HHMM filenames and correct
    exclusion of .meta.json sidecar files.
    """

    def test_find_latest_no_files_returns_none(self, tmp_path: Path) -> None:
        """find_latest returns None when no matching files exist.

        Tests: find_latest empty directory
        How: Call with a page name that has no matching files.
        Why: fetch_or_cached branches on None to handle the no-cache case.
        """
        # Arrange / Act
        result = find_latest("nonexistent-page", sources_dir=tmp_path)

        # Assert
        assert result is None

    def test_find_latest_single_file_returns_it(self, tmp_path: Path) -> None:
        """find_latest returns the only file when exactly one exists.

        Tests: find_latest single candidate
        How: Create one matching file, assert it is returned.
        Why: The max() logic must work for a single-element list.
        """
        # Arrange
        _write_md(tmp_path, "mypage-2026-01-01-1000.md", "# Content")

        # Act
        result = find_latest("mypage", sources_dir=tmp_path)

        # Assert
        assert result is not None
        assert result.name == "mypage-2026-01-01-1000.md"

    def test_find_latest_returns_newest_by_filename_sort(self, tmp_path: Path) -> None:
        """find_latest returns the file whose name sorts lexicographically last.

        Tests: find_latest multiple files
        How: Create files with three different timestamps, assert the latest is returned.
        Why: Timestamps in YYYY-MM-DD-HHMM format sort correctly lexicographically;
             this is the documented contract for find_latest.
        """
        # Arrange
        _write_md(tmp_path, "mypage-2026-01-01-0800.md", "older")
        _write_md(tmp_path, "mypage-2026-01-01-1200.md", "newest")
        _write_md(tmp_path, "mypage-2026-01-01-1000.md", "middle")

        # Act
        result = find_latest("mypage", sources_dir=tmp_path)

        # Assert
        assert result is not None
        assert result.name == "mypage-2026-01-01-1200.md"

    def test_find_latest_ignores_meta_json_files(self, tmp_path: Path) -> None:
        """find_latest ignores .meta.json sidecar files when scanning.

        Tests: find_latest sidecar exclusion
        How: Create both .md and .meta.json files, assert only the .md is returned.
        Why: Sidecar files share the base name pattern; returning them would break
             all downstream text reads.
        """
        # Arrange
        md_path = _write_md(tmp_path, "mypage-2026-01-01-1000.md", "content")
        (tmp_path / "mypage-2026-01-01-1000.meta.json").write_text("{}", encoding="utf-8")

        # Act
        result = find_latest("mypage", sources_dir=tmp_path)

        # Assert
        assert result == md_path

    def test_find_latest_does_not_match_different_page_name(self, tmp_path: Path) -> None:
        """find_latest does not return files belonging to a different page name.

        Tests: find_latest page name scoping
        How: Create a file for 'otherpage', query for 'mypage', assert None.
        Why: Without strict name scoping, one page's cached files would bleed
             into another page's lookup.
        """
        # Arrange
        _write_md(tmp_path, "otherpage-2026-01-01-1000.md", "content")

        # Act
        result = find_latest("mypage", sources_dir=tmp_path)

        # Assert
        assert result is None

    def test_find_latest_uses_sources_dir_default_when_no_override(self) -> None:
        """find_latest uses SOURCES_DIR when no sources_dir override is provided.

        Tests: find_latest default sources_dir
        How: Call without sources_dir kwarg for a page name that cannot exist; assert None.
        Why: Confirms the signature default is accepted without raising, so callers
             that rely on the default path do not need to pass the argument.
        """
        # Arrange / Act — page name is guaranteed not to exist
        result = find_latest("nonexistent-page-xyz-unique-99999")

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# fetch_or_cached
# ---------------------------------------------------------------------------


class TestFetchOrCachedFresh:
    """Tests for fetch_or_cached — cache hit within TTL (FRESH status)."""

    def test_fetch_or_cached_returns_fresh_when_within_ttl(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """fetch_or_cached returns FRESH without a network call when the cache is young.

        Tests: fetch_or_cached FRESH status
        How: Create a cached file with a fresh fetched_at, mock fetch_url_text,
             assert it is never called and status is FRESH.
        Why: The entire value of offline-first caching collapses if fresh files
             trigger unnecessary network requests.
        """
        # Arrange
        mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
        url = "https://example.com/docs/mypage.md"
        content = "# Cached\nSome content."
        md_path = _write_md(tmp_path, "mypage-2026-03-23-1000.md", content)
        _write_sidecar(
            md_path,
            url=url,
            sha256=hashlib.sha256(content.encode()).hexdigest(),
            byte_count=len(content.encode()),
            fetched_at=_fresh_fetched_at(),
        )

        mock_fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text")

        # Act
        result = fetch_or_cached(url, ttl_hours=4.0)

        # Assert
        mock_fetch.assert_not_called()
        assert result.status == CacheStatus.FRESH
        assert result.path == md_path
        assert result.url == url


class TestFetchOrCachedStale:
    """Tests for fetch_or_cached — stale cache scenarios."""

    def test_fetch_or_cached_returns_refreshed_when_content_changed(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """fetch_or_cached returns REFRESHED and writes a new file when remote content changed.

        Tests: fetch_or_cached REFRESHED status
        How: Create stale cache with old content, mock fetch returning different content,
             assert REFRESHED and a new file was written.
        Why: Changed remote content must be persisted so agents always get the latest docs.
        """
        # Arrange
        mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
        url = "https://example.com/docs/refreshpage.md"
        old_content = "# Old\nOld content."
        new_content = "# New\nUpdated content."

        md_path = _write_md(tmp_path, "refreshpage-2026-01-01-0000.md", old_content)
        _write_sidecar(
            md_path,
            url=url,
            sha256=hashlib.sha256(old_content.encode()).hexdigest(),
            byte_count=len(old_content.encode()),
            fetched_at=_stale_fetched_at(),
        )

        mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value=new_content)

        # Act
        result = fetch_or_cached(url, ttl_hours=4.0)

        # Assert
        assert result.status == CacheStatus.REFRESHED
        assert result.path != md_path  # new timestamped file was written
        assert result.path.read_text(encoding="utf-8") == new_content

    def test_fetch_or_cached_returns_unchanged_when_content_identical(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """fetch_or_cached returns UNCHANGED and touches only the sidecar when content is the same.

        Tests: fetch_or_cached UNCHANGED status
        How: Create stale cache, mock fetch returning same content, assert UNCHANGED
             and same file path is returned.
        Why: Re-writing an identical file wastes disk I/O and pollutes file history.
        """
        # Arrange
        mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
        url = "https://example.com/docs/samepage.md"
        content = "# Same\nIdentical content."

        md_path = _write_md(tmp_path, "samepage-2026-01-01-0000.md", content)
        _write_sidecar(
            md_path,
            url=url,
            sha256=hashlib.sha256(content.encode()).hexdigest(),
            byte_count=len(content.encode()),
            fetched_at=_stale_fetched_at(),
        )

        mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value=content)

        # Act
        result = fetch_or_cached(url, ttl_hours=4.0)

        # Assert
        assert result.status == CacheStatus.UNCHANGED
        assert result.path == md_path  # same path, no new file

    def test_fetch_or_cached_unchanged_updates_sidecar_fetched_at(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """fetch_or_cached touches the sidecar fetched_at when content is unchanged.

        Tests: fetch_or_cached sidecar touch on UNCHANGED
        How: Record the old fetched_at, trigger UNCHANGED, assert sidecar was updated.
        Why: Updating fetched_at resets the TTL clock so the next call also gets a
             fresh hit instead of repeatedly re-fetching unchanged content.
        """
        # Arrange
        mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
        url = "https://example.com/docs/touchpage.md"
        content = "# Same\nIdentical content."
        old_fetched_at = "2026-01-01T00:00:00+00:00"

        md_path = _write_md(tmp_path, "touchpage-2026-01-01-0000.md", content)
        sidecar_path = _write_sidecar(
            md_path,
            url=url,
            sha256=hashlib.sha256(content.encode()).hexdigest(),
            byte_count=len(content.encode()),
            fetched_at=old_fetched_at,
        )

        mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value=content)

        # Act
        fetch_or_cached(url, ttl_hours=4.0)

        # Assert
        updated = json.loads(sidecar_path.read_text(encoding="utf-8"))
        assert updated["fetched_at"] != old_fetched_at

    def test_fetch_or_cached_returns_stale_when_network_unavailable(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """fetch_or_cached returns STALE and serves the cached copy when network fails.

        Tests: fetch_or_cached STALE status
        How: Create stale cache, mock fetch_url_text to raise ConnectError, assert STALE.
        Why: Offline-first means stale content is always preferred over raising an error
             when a cached copy exists, regardless of its age.
        """
        # Arrange
        mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
        url = "https://example.com/docs/stalepage.md"
        content = "# Stale\nOld content."

        md_path = _write_md(tmp_path, "stalepage-2026-01-01-0000.md", content)
        _write_sidecar(
            md_path,
            url=url,
            sha256=hashlib.sha256(content.encode()).hexdigest(),
            byte_count=len(content.encode()),
            fetched_at=_stale_fetched_at(),
        )

        mocker.patch("skilllint.vendor_cache.fetch_url_text", side_effect=httpx.ConnectError("Network unreachable"))

        # Act
        result = fetch_or_cached(url, ttl_hours=4.0)

        # Assert
        assert result.status == CacheStatus.STALE
        assert result.path == md_path

    def test_fetch_or_cached_returns_stale_on_timeout(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """fetch_or_cached returns STALE on a network timeout.

        Tests: fetch_or_cached STALE on TimeoutException
        How: Raise TimeoutException from fetch_url_text, assert STALE is returned.
        Why: Timeouts are network failures; the offline-first fallback must apply
             to them just as it does to ConnectError.
        """
        # Arrange
        mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
        url = "https://example.com/docs/stalepage.md"
        content = "# Stale\nOld content."

        md_path = _write_md(tmp_path, "stalepage-2026-01-01-0001.md", content)
        _write_sidecar(
            md_path,
            url=url,
            sha256=hashlib.sha256(content.encode()).hexdigest(),
            byte_count=len(content.encode()),
            fetched_at=_stale_fetched_at(),
        )

        mocker.patch("skilllint.vendor_cache.fetch_url_text", side_effect=httpx.TimeoutException("timeout"))

        # Act
        result = fetch_or_cached(url, ttl_hours=4.0)

        # Assert
        assert result.status == CacheStatus.STALE


class TestFetchOrCachedNew:
    """Tests for fetch_or_cached — no prior cache exists."""

    def test_fetch_or_cached_returns_new_on_first_fetch(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """fetch_or_cached returns NEW and writes a new file when no cache exists.

        Tests: fetch_or_cached NEW status
        How: Empty tmp_path, mock fetch_url_text, assert NEW status and file created.
        Why: First-time page fetching must persist the content for future offline use.
        """
        # Arrange
        mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
        url = "https://example.com/docs/en/newpage.md"
        content = "# New page\nFetched content."

        mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value=content)

        # Act
        result = fetch_or_cached(url)

        # Assert
        assert result.status == CacheStatus.NEW
        assert result.path.exists()
        assert result.path.read_text(encoding="utf-8") == content

    def test_fetch_or_cached_raises_no_cache_error_when_no_cache_and_network_fails(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """fetch_or_cached raises NoCacheError when no cache exists and network fails.

        Tests: fetch_or_cached NoCacheError on no-cache + network failure
        How: Empty tmp_path, mock fetch_url_text to raise ConnectError, assert NoCacheError.
        Why: Without a cache and without a network, the caller must be told explicitly
             that the resource is unavailable rather than receiving None silently.
        """
        # Arrange
        mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
        url = "https://example.com/docs/en/gone.md"

        mocker.patch("skilllint.vendor_cache.fetch_url_text", side_effect=httpx.ConnectError("connection refused"))

        # Act / Assert
        with pytest.raises(NoCacheError) as exc_info:
            fetch_or_cached(url)

        assert exc_info.value.url == url


class TestFetchOrCachedForce:
    """Tests for fetch_or_cached — force=True bypasses the TTL check."""

    def test_fetch_or_cached_force_bypasses_ttl_and_fetches(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """fetch_or_cached with force=True fetches even when the cache is within TTL.

        Tests: fetch_or_cached force flag
        How: Create a fresh cached file, set force=True, mock fetch with new content,
             assert fetch was called and result reflects the new content.
        Why: Agents must be able to force an immediate refresh after a known remote
             update, without waiting for TTL expiry.
        """
        # Arrange
        mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
        url = "https://example.com/docs/forcepage.md"
        old_content = "# Fresh\nFresh content."
        new_content = "# Updated\nNew content."

        md_path = _write_md(tmp_path, "forcepage-2026-03-23-1000.md", old_content)
        _write_sidecar(
            md_path,
            url=url,
            sha256=hashlib.sha256(old_content.encode()).hexdigest(),
            byte_count=len(old_content.encode()),
            fetched_at=_fresh_fetched_at(),
        )

        mock_fetch = mocker.patch("skilllint.vendor_cache.fetch_url_text", return_value=new_content)

        # Act
        result = fetch_or_cached(url, force=True)

        # Assert
        mock_fetch.assert_called_once_with(url)
        assert result.status in {CacheStatus.NEW, CacheStatus.REFRESHED}

    def test_fetch_or_cached_force_serves_stale_when_network_fails(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """fetch_or_cached with force=True falls back to STALE when network fails.

        Tests: fetch_or_cached force + network failure with cache present
        How: Fresh cache, force=True, fetch raises ConnectError, assert STALE.
        Why: Even a forced refresh should not crash if a cached copy exists;
             stale content is better than an unhandled exception.
        """
        # Arrange
        mocker.patch("skilllint.vendor_cache.SOURCES_DIR", tmp_path)
        url = "https://example.com/docs/settings.md"

        md_path = _write_md(tmp_path, "settings-2026-03-23-1400.md", "# Settings\n")
        _write_sidecar(
            md_path,
            url=url,
            sha256=hashlib.sha256(b"# Settings\n").hexdigest(),
            byte_count=len(b"# Settings\n"),
            fetched_at=_fresh_fetched_at(),
        )

        mocker.patch("skilllint.vendor_cache.fetch_url_text", side_effect=httpx.ConnectError("unreachable"))

        # Act
        result = fetch_or_cached(url, force=True)

        # Assert
        assert result.status == CacheStatus.STALE
        assert result.path == md_path


# ---------------------------------------------------------------------------
# NoCacheError
# ---------------------------------------------------------------------------


class TestNoCacheError:
    """Tests for the NoCacheError exception contract."""

    def test_no_cache_error_stores_url_and_reason(self) -> None:
        """NoCacheError stores the url and reason attributes.

        Tests: NoCacheError attributes
        How: Instantiate with url and reason, assert both are accessible.
        Why: Callers inspect these to log or display structured error messages.
        """
        # Arrange / Act
        exc = NoCacheError("https://example.com/x.md", "connection refused")

        # Assert
        assert exc.url == "https://example.com/x.md"
        assert exc.reason == "connection refused"
        assert "No cache for https://example.com/x.md" in str(exc)

    def test_no_cache_error_is_exception_subclass(self) -> None:
        """NoCacheError is a subclass of Exception.

        Tests: NoCacheError inheritance
        How: Check issubclass relationship.
        Why: Callers may catch Exception broadly; NoCacheError must be catchable.
        """
        # Arrange / Act / Assert
        assert issubclass(NoCacheError, Exception)


# ---------------------------------------------------------------------------
# list_sections
# ---------------------------------------------------------------------------


class TestListSections:
    """Tests for list_sections — markdown heading decomposition.

    Uses marko AST parsing to correctly handle fenced code blocks containing
    hash characters. Sections are 1-indexed to match the Read tool's format.
    """

    def test_list_sections_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        """list_sections returns an empty list for a file with no content.

        Tests: list_sections empty file
        How: Write a zero-byte file, assert empty list returned.
        Why: Callers must handle the empty case without raising; an empty list is
             the documented return value.
        """
        # Arrange
        md = _write_md(tmp_path, "empty.md", "")

        # Act
        result = list_sections(md)

        # Assert
        assert result == []

    def test_list_sections_no_headings_returns_single_preamble(self, tmp_path: Path) -> None:
        """list_sections returns a single level=0 preamble for a file with no headings.

        Tests: list_sections no-heading file
        How: Write plain text without headings, assert one preamble section.
        Why: Content without headings is still addressable via the preamble section.
        """
        # Arrange
        md = _write_md(tmp_path, "noheadings.md", "Just some text\nwithout any headings.")

        # Act
        result = list_sections(md)

        # Assert
        assert len(result) == 1
        assert result[0].heading == ""
        assert result[0].level == 0
        assert result[0].line_start == 1
        assert result[0].line_end == 2

    def test_list_sections_preamble_before_first_heading_has_level_zero(self, tmp_path: Path) -> None:
        """list_sections creates a level=0 preamble for content before the first heading.

        Tests: list_sections preamble with heading
        How: Write markdown with intro text before first #, assert level=0 first section.
        Why: Preamble content (badges, notices) must be accessible; level=0 is the
             documented marker for pre-heading content.
        """
        # Arrange
        md = _write_md(tmp_path, "preamble.md", "Preamble text.\n\n# Section One\nContent.")

        # Act
        result = list_sections(md)

        # Assert
        assert result[0].heading == ""
        assert result[0].level == 0
        assert result[0].line_start == 1
        assert result[0].line_end == 2
        assert result[1].heading == "Section One"
        assert result[1].line_start == 3

    def test_list_sections_single_h1_returns_one_section(self, tmp_path: Path) -> None:
        """list_sections returns one section for a file with a single h1 heading.

        Tests: list_sections single heading
        How: Write a file with one # heading, assert one section with correct attributes.
        Why: The basic case must work before testing compound documents.
        """
        # Arrange
        md = _write_md(tmp_path, "single.md", "# Title\nContent here.")

        # Act
        result = list_sections(md)

        # Assert
        assert len(result) == 1
        assert result[0].heading == "Title"
        assert result[0].level == 1
        assert result[0].line_start == 1
        assert result[0].line_end == 2

    def test_list_sections_code_fence_hash_not_treated_as_heading(self, tmp_path: Path) -> None:
        """list_sections ignores # lines inside fenced code blocks.

        Tests: list_sections code fence handling
        How: Write markdown with a fenced block containing a bash comment line,
             assert no spurious section is created for it.
        Why: Code examples commonly use # for comments; misidentifying them as headings
             would produce wrong line offsets for agents using the Read tool.
        """
        # Arrange
        content = (
            "# Real Heading\n\n"
            "```bash\n"
            "# Not a heading — this is a bash comment\n"
            "echo hello\n"
            "```\n\n"
            "## Another Real Heading\n\n"
            "Content.\n"
        )
        md = _write_md(tmp_path, "code_fence.md", content)

        # Act
        sections = list_sections(md)
        headings = [s.heading for s in sections]

        # Assert
        assert "Not a heading \u2014 this is a bash comment" not in headings
        assert "Real Heading" in headings
        assert "Another Real Heading" in headings

    def test_list_sections_h2_ends_at_next_h1(self, tmp_path: Path) -> None:
        """list_sections terminates an h2 section at the next h1 boundary.

        Tests: list_sections section boundary logic
        How: Write h1 > h2 > h1, assert the h2 ends at the line before the second h1.
        Why: Section ranges must match the Read tool's expected line ranges for
             agents to retrieve correct section text.
        """
        # Arrange
        content = "# Top\n## Sub\nSubcontent.\n# Next Top\nMore."
        md = _write_md(tmp_path, "nested.md", content)

        # Act
        result = list_sections(md)
        sub_section = next(s for s in result if s.heading == "Sub")
        next_top = next(s for s in result if s.heading == "Next Top")

        # Assert
        assert sub_section.line_end == next_top.line_start - 1

    def test_list_sections_line_numbers_are_1_indexed(self, tmp_path: Path) -> None:
        """list_sections returns 1-indexed line_start values.

        Tests: list_sections line indexing
        How: Write a simple doc with consecutive headings, assert line starts.
        Why: The Read tool uses 1-indexed lines; 0-indexed values would cause
             off-by-one errors when agents request specific sections.
        """
        # Arrange
        md = _write_md(tmp_path, "lines.md", "# A\n# B\n# C\n")

        # Act
        result = list_sections(md)

        # Assert
        assert result[0].line_start == 1
        assert result[1].line_start == 2
        assert result[2].line_start == 3

    def test_list_sections_returns_markdown_section_instances(self, tmp_path: Path) -> None:
        """list_sections returns MarkdownSection dataclass instances.

        Tests: list_sections return type
        How: Assert all elements are instances of MarkdownSection.
        Why: Callers access .heading, .level, .line_start, .line_end attributes
             by name; the type must match the documented dataclass.
        """
        # Arrange
        md = _write_md(tmp_path, "typed.md", "# Heading\nBody.")

        # Act
        result = list_sections(md)

        # Assert
        assert all(isinstance(s, MarkdownSection) for s in result)

    def test_list_sections_h3_bounded_by_higher_level_headings(self, tmp_path: Path) -> None:
        """list_sections terminates an h3 section at the next h2 boundary.

        Tests: list_sections deep nesting boundary
        How: Write h1 > h2 > h3 > h2, assert h3 ends before the second h2.
        Why: Deep nesting is common in long documentation; boundary detection must
             work for all heading levels, not just h1/h2.
        """
        # Arrange
        content = "# H1\n## H2\n### H3\nText.\n## H2 again\nMore."
        md = _write_md(tmp_path, "deep.md", content)

        # Act
        result = list_sections(md)
        h3 = next(s for s in result if s.level == 3)
        h2_again = next(s for s in result if s.heading == "H2 again")

        # Assert
        assert h3.line_end == h2_again.line_start - 1


# ---------------------------------------------------------------------------
# read_section
# ---------------------------------------------------------------------------


class TestReadSection:
    """Tests for read_section — section text retrieval by heading or slug."""

    def test_read_section_matches_by_exact_heading_text(self, tmp_path: Path) -> None:
        """read_section returns section text when queried by heading text.

        Tests: read_section heading text match
        How: Write markdown with a named section, query by name, assert content returned.
        Why: Agents query sections using human-readable heading names; exact text
             match is the primary lookup mechanism.
        """
        # Arrange
        md = _write_md(tmp_path, "doc.md", "# Intro\nIntro text.\n# Guide\nGuide text.\n")

        # Act
        result = read_section(md, "Guide")

        # Assert
        assert result is not None
        assert "Guide text." in result

    def test_read_section_is_case_insensitive(self, tmp_path: Path) -> None:
        """read_section matches heading text case-insensitively.

        Tests: read_section case-insensitive matching
        How: Write a heading, query in lowercase, assert match succeeds.
        Why: Case-insensitive matching avoids fragile exact-case queries from agents.
        """
        # Arrange
        md = _write_md(tmp_path, "case.md", "# My Section\nContent.")

        # Act
        result = read_section(md, "my section")

        # Assert
        assert result is not None
        assert "Content." in result

    def test_read_section_matches_by_anchor_slug(self, tmp_path: Path) -> None:
        """read_section returns section text when queried by markdown anchor slug.

        Tests: read_section slug match
        How: Write a multi-word heading, query using its slug form, assert content.
        Why: Some callers derive slugs programmatically; both heading text and slug
             must work to avoid forcing callers to normalise differently.
        """
        # Arrange
        md = _write_md(tmp_path, "hooks.md", "# Hook Input and Output\nInput docs here.\n")

        # Act
        result = read_section(md, "hook-input-and-output")

        # Assert
        assert result is not None
        assert "Hook Input and Output" in result

    def test_read_section_strips_leading_hashes_from_query(self, tmp_path: Path) -> None:
        """read_section strips leading # characters from the query before matching.

        Tests: read_section hash stripping
        How: Query with '## My Section' prefix hashes, assert match succeeds.
        Why: Callers may copy headings directly from markdown source including the
             # prefix; these must still resolve correctly.
        """
        # Arrange
        md = _write_md(tmp_path, "hashes.md", "# My Section\nContent.")

        # Act
        result = read_section(md, "## My Section")

        # Assert
        assert result is not None

    def test_read_section_missing_heading_returns_none(self, tmp_path: Path) -> None:
        """read_section returns None when the heading does not exist in the file.

        Tests: read_section missing heading
        How: Query for a heading that does not appear in the document.
        Why: Callers must be able to detect absent sections without an exception.
        """
        # Arrange
        md = _write_md(tmp_path, "missing.md", "# Existing\nContent.")

        # Act
        result = read_section(md, "Nonexistent Section")

        # Assert
        assert result is None

    def test_read_section_includes_heading_line(self, tmp_path: Path) -> None:
        """read_section includes the heading line itself in the returned text.

        Tests: read_section full text range
        How: Write a doc, read a section, assert the heading line starts the result.
        Why: Agents need the heading line for context when presenting sections to users.
        """
        # Arrange
        md = _write_md(tmp_path, "heading.md", "# Target\nBody line.")

        # Act
        result = read_section(md, "Target")

        # Assert
        assert result is not None
        assert result.startswith("# Target")


# ---------------------------------------------------------------------------
# format_section_index
# ---------------------------------------------------------------------------


class TestFormatSectionIndex:
    """Tests for format_section_index — plain-text section table formatter.

    Columns (0-indexed): index, level, heading, lines (start-end).
    """

    def test_format_section_index_empty_file_returns_no_sections_message(self, tmp_path: Path) -> None:
        """format_section_index returns '(no sections found)' for an empty file.

        Tests: format_section_index empty file
        How: Write empty file, assert result contains the documented message.
        Why: The documented return value for an empty file must be predictable so
             callers can distinguish 'no sections' from parse errors.
        """
        # Arrange
        md = _write_md(tmp_path, "empty.md", "")

        # Act
        result = format_section_index(md)

        # Assert
        assert "(no sections found)" in result

    def test_format_section_index_contains_expected_column_headers(self, tmp_path: Path) -> None:
        """format_section_index output contains index, level, heading, and lines columns.

        Tests: format_section_index column headers
        How: Write a markdown file, call format_section_index, assert header labels.
        Why: The documented contract specifies exactly four columns; agents parsing
             this output depend on the column names being present.
        """
        # Arrange
        md = _write_md(tmp_path, "doc.md", "# Section One\nContent.")

        # Act
        result = format_section_index(md)

        # Assert
        assert "index" in result
        assert "level" in result
        assert "heading" in result
        assert "lines" in result

    def test_format_section_index_contains_section_heading(self, tmp_path: Path) -> None:
        """format_section_index includes all section headings as rows.

        Tests: format_section_index row completeness
        How: Write a doc with a named section, assert heading appears in output.
        Why: Missing rows would cause agents to be unaware of sections they could read.
        """
        # Arrange
        md = _write_md(tmp_path, "doc.md", "# My Section\nContent.")

        # Act
        result = format_section_index(md)

        # Assert
        assert "My Section" in result

    def test_format_section_index_contains_line_range(self, tmp_path: Path) -> None:
        """format_section_index includes start-end line ranges for each section.

        Tests: format_section_index line range column
        How: Write a two-line file, assert '1-2' appears in the output.
        Why: Agents use line ranges to construct Read tool calls with exact offsets.
        """
        # Arrange
        md = _write_md(tmp_path, "doc.md", "# Only\nLine two.")

        # Act
        result = format_section_index(md)

        # Assert
        assert "1-2" in result

    def test_format_section_index_shows_preamble_label(self, tmp_path: Path) -> None:
        """format_section_index labels the preamble section as '(preamble)'.

        Tests: format_section_index preamble label
        How: Write a file with intro text before the first heading, assert label.
        Why: The preamble has no heading text; '(preamble)' is the documented label.
        """
        # Arrange
        md = _write_md(tmp_path, "pre.md", "Preamble line.\n\n# Section\nContent.")

        # Act
        result = format_section_index(md)

        # Assert
        assert "(preamble)" in result

    def test_format_section_index_returns_plain_text(self, tmp_path: Path) -> None:
        """format_section_index returns plain text without Rich markup.

        Tests: format_section_index plain text contract
        How: Write a simple doc, assert no unbalanced Rich markup brackets.
        Why: The function is documented as plain-text only with no Rich dependency.
        """
        # Arrange
        md = _write_md(tmp_path, "plain.md", "# Section\nContent.")

        # Act
        result = format_section_index(md)

        # Assert — no Rich-style [markup] brackets
        assert "[bold" not in result
        assert "[red" not in result


# ---------------------------------------------------------------------------
# verify_integrity
# ---------------------------------------------------------------------------


class TestVerifyIntegrity:
    """Tests for verify_integrity — sidecar hash comparison.

    Reads the file, computes SHA-256 and byte count, compares against the sidecar.
    Returns INTACT, MODIFIED, or UNVERIFIABLE.
    """

    def test_verify_integrity_matching_sidecar_returns_intact(self, tmp_path: Path) -> None:
        """verify_integrity returns INTACT when file content matches the sidecar.

        Tests: verify_integrity INTACT status
        How: Write a file and its sidecar with matching hash/byte_count, assert INTACT.
        Why: The INTACT result is the baseline assertion that a cached file has not
             been tampered with since the sidecar was written.
        """
        # Arrange
        content = "# Doc\nBody text."
        md_path = _write_md(tmp_path, "intact.md", content)
        _write_sidecar(
            md_path,
            url="https://example.com/x.md",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
            byte_count=len(content.encode()),
            fetched_at="2026-01-01T00:00:00+00:00",
        )

        # Act
        result = verify_integrity(md_path)

        # Assert
        assert result.status == IntegrityStatus.INTACT

    def test_verify_integrity_altered_file_returns_modified(self, tmp_path: Path) -> None:
        """verify_integrity returns MODIFIED when file content differs from the sidecar.

        Tests: verify_integrity MODIFIED detection
        How: Write file + sidecar for original content, then overwrite file with different
             content without updating the sidecar, assert MODIFIED.
        Why: MODIFIED detection is the primary tamper-evident check; it must trigger
             whenever the on-disk bytes no longer match the recorded hash.
        """
        # Arrange
        original = "# Original\nOriginal body."
        md_path = _write_md(tmp_path, "modified.md", "# Modified\nDifferent body.")
        _write_sidecar(
            md_path,
            url="https://example.com/x.md",
            sha256=hashlib.sha256(original.encode()).hexdigest(),
            byte_count=len(original.encode()),
            fetched_at="2026-01-01T00:00:00+00:00",
        )

        # Act
        result = verify_integrity(md_path)

        # Assert
        assert result.status == IntegrityStatus.MODIFIED
        assert result.computed_sha256 != result.expected_sha256

    def test_verify_integrity_no_sidecar_returns_unverifiable(self, tmp_path: Path) -> None:
        """verify_integrity returns UNVERIFIABLE when no sidecar exists for the file.

        Tests: verify_integrity UNVERIFIABLE status
        How: Write a file without a sidecar, assert UNVERIFIABLE is returned.
        Why: Files without sidecars cannot be verified; returning UNVERIFIABLE
             rather than INTACT prevents false-positive integrity checks.
        """
        # Arrange
        md_path = _write_md(tmp_path, "nosidecar.md", "# No sidecar\nContent.")

        # Act
        result = verify_integrity(md_path)

        # Assert
        assert result.status == IntegrityStatus.UNVERIFIABLE
        assert result.expected_sha256 is None
        assert result.expected_bytes is None

    def test_verify_integrity_result_contains_computed_sha256(self, tmp_path: Path) -> None:
        """verify_integrity result contains the correctly computed SHA-256 digest.

        Tests: verify_integrity computed_sha256 accuracy
        How: Write a file with known content, assert computed_sha256 matches expected.
        Why: Callers may use computed values to update stale sidecars.
        """
        # Arrange
        content = "Hello, world.\n"
        md_path = _write_md(tmp_path, "known.md", content)

        # Act
        result = verify_integrity(md_path)

        # Assert
        assert result.computed_sha256 == sha256_hex(content)

    def test_verify_integrity_result_contains_computed_bytes(self, tmp_path: Path) -> None:
        """verify_integrity result contains the correct UTF-8 byte count.

        Tests: verify_integrity computed_bytes accuracy
        How: Write a file with known content, assert computed_bytes matches len(encode).
        Why: Byte count is a secondary integrity signal; it must be accurate
             to detect truncation or padding attacks.
        """
        # Arrange
        content = "Hello, world.\n"
        md_path = _write_md(tmp_path, "known2.md", content)

        # Act
        result = verify_integrity(md_path)

        # Assert
        assert result.computed_bytes == len(content.encode("utf-8"))

    def test_verify_integrity_returns_integrity_result_instance(self, tmp_path: Path) -> None:
        """verify_integrity returns an IntegrityResult dataclass instance.

        Tests: verify_integrity return type
        How: Call verify_integrity, assert the return type is IntegrityResult.
        Why: Callers access named attributes; the type must match the documented dataclass.
        """
        # Arrange
        md_path = _write_md(tmp_path, "typed.md", "# T\nBody.")

        # Act
        result = verify_integrity(md_path)

        # Assert
        assert isinstance(result, IntegrityResult)

    def test_verify_integrity_wrong_byte_count_returns_modified(self, tmp_path: Path) -> None:
        """verify_integrity returns MODIFIED when the byte count in the sidecar is wrong.

        Tests: verify_integrity byte count mismatch detection
        How: Write sidecar with correct hash but wrong byte_count, assert MODIFIED.
        Why: Byte count is independently checked; a wrong count alone must trigger
             MODIFIED even if the SHA-256 happens to match.
        """
        # Arrange
        content = "# Doc\nBody."
        md_path = _write_md(tmp_path, "wrongbytes.md", content)
        _write_sidecar(
            md_path,
            url="https://example.com/x.md",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
            byte_count=9999,  # intentionally wrong
            fetched_at="2026-01-01T00:00:00+00:00",
        )

        # Act
        result = verify_integrity(md_path)

        # Assert
        assert result.status == IntegrityStatus.MODIFIED

    def test_verify_integrity_computed_bytes_handles_unicode(self, tmp_path: Path) -> None:
        """verify_integrity computed_bytes correctly encodes multi-byte unicode characters.

        Tests: verify_integrity unicode encoding
        How: Write a file with multi-byte unicode, assert computed_bytes matches UTF-8 len.
        Why: A naive len() would return character count, not byte count; unicode content
             must use len(content.encode()) to get the correct value.
        """
        # Arrange
        content = "# Unicode: \u00e9\u00e0\u00fc\n"
        md_path = _write_md(tmp_path, "unicode.md", content)

        # Act
        result = verify_integrity(md_path)

        # Assert
        assert result.computed_bytes == len(content.encode("utf-8"))
