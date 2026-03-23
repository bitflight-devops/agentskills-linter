"""Offline-first documentation cache with section querying.

This module provides a public API for fetching, caching, and querying
vendor documentation pages. It builds on the low-level I/O primitives in
``skilllint.vendor_io`` and adds TTL-based freshness logic, offline fallback,
and markdown section decomposition.

Public API:
  Enumerations:
    CacheStatus     -- result of a fetch_or_cached call
    IntegrityStatus -- result of a verify_integrity call

  Data classes:
    CacheResult     -- outcome of fetch_or_cached
    IntegrityResult -- outcome of verify_integrity
    MarkdownSection -- a single section parsed from a markdown file

  Exceptions:
    NoCacheError    -- raised when no cache exists and network is unavailable

  Cache operations:
    derive_page_name    -- extract a filesystem-safe name from a documentation URL
    find_latest         -- find the most-recent cached file for a page name
    fetch_or_cached     -- fetch a page or return a cached copy (offline-first)

  Section decomposition:
    list_sections       -- parse a markdown file into MarkdownSection objects
    read_section        -- return the text of a named section
    format_section_index -- return a plain-text table of sections

  Integrity:
    verify_integrity    -- verify a cached file against its .meta.json sidecar
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx
import marko
from marko.block import Heading as MarkoHeading

from skilllint.vendor_io import (
    SOURCES_DIR,
    fetch_url_text,
    load_sidecar,
    read_text_or_none,
    sha256_hex,
    utc_now_iso,
    write_json,
    write_sidecar,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class CacheStatus(enum.Enum):
    """Result status returned by :func:`fetch_or_cached`."""

    FRESH = "fresh"
    """Within TTL; served from the on-disk cache without a network request."""

    REFRESHED = "refreshed"
    """Was stale; re-fetched successfully; content changed on the remote."""

    UNCHANGED = "unchanged"
    """Was stale; re-fetched successfully; content identical; sidecar touched."""

    STALE = "stale"
    """Stale but network unavailable — served from cache anyway."""

    NEW = "new"
    """First fetch; no prior cache existed."""


class IntegrityStatus(enum.Enum):
    """Result status returned by :func:`verify_integrity`."""

    INTACT = "intact"
    """File hash and byte count match the sidecar metadata."""

    MODIFIED = "modified"
    """File hash or byte count does not match the sidecar metadata."""

    UNVERIFIABLE = "unverifiable"
    """No sidecar found; cannot verify the file."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CacheResult:
    """Outcome of a :func:`fetch_or_cached` call.

    Attributes:
        path: Path to the cached file on disk.
        status: How the result was produced (FRESH, REFRESHED, etc.).
        page_name: Filesystem-safe page name derived from the URL.
        url: Original URL that was fetched or looked up.
    """

    path: Path
    status: CacheStatus
    page_name: str
    url: str


@dataclass(frozen=True)
class IntegrityResult:
    """Outcome of a :func:`verify_integrity` call.

    Attributes:
        status: Whether the file is INTACT, MODIFIED, or UNVERIFIABLE.
        file_path: Path to the file that was checked.
        computed_sha256: SHA-256 hex digest computed from the current file content.
        expected_sha256: SHA-256 hex digest recorded in the sidecar, or None if
            no sidecar exists.
        computed_bytes: Byte length of the current file content (UTF-8).
        expected_bytes: Byte length recorded in the sidecar, or None if no
            sidecar exists.
    """

    status: IntegrityStatus
    file_path: Path
    computed_sha256: str
    expected_sha256: str | None
    computed_bytes: int
    expected_bytes: int | None


@dataclass(frozen=True)
class MarkdownSection:
    """A single section within a markdown document.

    Attributes:
        heading: Heading text (empty string for preamble before first heading).
        level: Heading depth 1-6, or 0 for the preamble.
        line_start: First line of the section, 1-indexed inclusive.
        line_end: Last line of the section, 1-indexed inclusive.
    """

    heading: str
    level: int
    line_start: int
    line_end: int


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class NoCacheError(Exception):
    """Raised when no cached copy exists and the network is unavailable.

    Args:
        url: The URL that could not be fetched.
        reason: Human-readable reason for the failure.
    """

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"No cache for {url}: {reason}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_COMMON_PREFIXES = ("/en/", "/docs/", "/api/")
_SAFE_CHAR_RE = re.compile(r"[^a-zA-Z0-9-]+")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_SLUG_STRIP_RE = re.compile(r"[^\w\s-]")
_SLUG_COLLAPSE_RE = re.compile(r"[-\s]+")


def _heading_to_slug(heading: str) -> str:
    """Convert a heading to a markdown anchor slug.

    Mirrors GitHub/GitLab slug generation: lowercase, strip non-word chars
    (except hyphens and spaces), collapse whitespace/hyphens to single hyphens.

    Returns:
        Slug string suitable for use as a markdown anchor.

    Examples:
        "Hook input and output" → "hook-input-and-output"
        "The `/hooks` menu"     → "the-hooks-menu"
    """
    slug = heading.lower()
    slug = _SLUG_STRIP_RE.sub("", slug)
    return _SLUG_COLLAPSE_RE.sub("-", slug).strip("-")


def _is_network_error(exc: Exception) -> bool:
    """Return True for exceptions that indicate network unavailability."""
    return isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError))


def _age_hours(fetched_at_iso: str) -> float:
    """Return age in hours between *fetched_at_iso* and now (UTC)."""
    try:
        fetched_at = datetime.fromisoformat(fetched_at_iso)
    except (ValueError, TypeError):
        # Treat unparseable timestamps as maximally stale.
        return float("inf")
    now = datetime.now(UTC)
    delta = now - fetched_at
    return delta.total_seconds() / 3600.0


# ---------------------------------------------------------------------------
# Cache operations
# ---------------------------------------------------------------------------


def derive_page_name(url: str) -> str:
    """Extract a filesystem-safe page name from a documentation URL.

    Algorithm:
    1. Parse the URL and take the path component.
    2. Strip common prefixes: ``/en/``, ``/docs/``, ``/api/``.
    3. Strip ``.md`` extension.
    4. Join remaining non-empty path segments with ``--``.
    5. Replace any non-alphanumeric-or-hyphen characters with a hyphen.

    Args:
        url: Full documentation URL.

    Returns:
        Filesystem-safe page name string.

    Examples:
        >>> derive_page_name("https://docs.anthropic.com/en/docs/claude-code/settings.md")
        'claude-code--settings'
        >>> derive_page_name("https://cursor.com/docs/context/rules.md")
        'context--rules'
        >>> derive_page_name("https://code.claude.com/docs/en/sub-agents.md")
        'sub-agents'
    """
    path = urlparse(url).path

    # Strip common prefixes one at a time until none remain.
    changed = True
    while changed:
        changed = False
        for prefix in _COMMON_PREFIXES:
            if path.startswith(prefix):
                path = path[len(prefix) :]
                if not path.startswith("/"):
                    path = "/" + path
                changed = True
                break

    # Strip .md extension.
    path = path.removesuffix(".md")

    # Split on "/" and drop empty segments.
    segments = [s for s in path.split("/") if s]

    # Join with "--".
    name = "--".join(segments)

    # Replace any non-alphanumeric-or-hyphen character with hyphen.
    name = _SAFE_CHAR_RE.sub("-", name)

    # Collapse multiple consecutive hyphens.
    return re.sub(r"-{2,}", "--", name)


def find_latest(page_name: str, *, sources_dir: Path | None = None) -> Path | None:
    """Find the most recent cached file for a given page name.

    Scans *sources_dir* (defaults to :data:`~skilllint.vendor_io.SOURCES_DIR`)
    for files matching ``{page_name}-*.md`` (excluding ``*.meta.json`` files).
    Returns the path whose filename sorts lexicographically last (timestamps
    in ``YYYY-MM-DD-HHMM`` format sort correctly by lexicographic order), or
    ``None`` if no matches exist.

    Args:
        page_name: Filesystem-safe page name, as returned by
            :func:`derive_page_name`.
        sources_dir: Directory to search. Defaults to
            :data:`~skilllint.vendor_io.SOURCES_DIR`.

    Returns:
        Path to the latest cached file, or None.
    """
    directory = sources_dir if sources_dir is not None else SOURCES_DIR
    candidates = [p for p in directory.glob(f"{page_name}-*.md") if not p.name.endswith(".meta.json")]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)


def fetch_or_cached(url: str, *, ttl_hours: float = 4.0, force: bool = False) -> CacheResult:
    """Fetch a documentation page, or return a cached copy. Offline-first.

    Flow:

    1. Derive a filesystem-safe *page_name* from *url*.
    2. Look up the most recent cached file for *page_name*.
    3. If a cached file exists **and** *force* is False:

       a. Load its sidecar and check age against *ttl_hours*.
       b. If fresh (age < TTL) → return :attr:`CacheStatus.FRESH`.
       c. If stale → attempt a network fetch:

          - Network OK, content changed → write a new timestamped file →
            :attr:`CacheStatus.REFRESHED`.
          - Network OK, content identical → update ``fetched_at`` in the
            existing sidecar only → :attr:`CacheStatus.UNCHANGED`.
          - Network failure (connect error, timeout, HTTP error) → return the
            stale copy as :attr:`CacheStatus.STALE`.

    4. If no cached file exists (or *force* is True):

       a. Attempt a network fetch:

          - Network OK → write a new timestamped file →
            :attr:`CacheStatus.NEW`.
          - Network failure → raise :exc:`NoCacheError`.

    File naming convention: ``{page_name}-{YYYY-MM-DD-HHMM}.md`` inside
    :data:`~skilllint.vendor_io.SOURCES_DIR`.

    Args:
        url: URL of the documentation page to fetch.
        ttl_hours: Maximum age in hours before a cached copy is considered
            stale. Defaults to 4.0.
        force: If True, skip the freshness check and always attempt a network
            fetch. Defaults to False.

    Returns:
        A :class:`CacheResult` describing the outcome.

    Raises:
        NoCacheError: If no cached copy exists and the network is unavailable.
    """
    page_name = derive_page_name(url)
    cached_path = find_latest(page_name)

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    def _timestamp() -> str:
        return datetime.now(UTC).strftime("%Y-%m-%d-%H%M")

    def _new_path() -> Path:
        return SOURCES_DIR / f"{page_name}-{_timestamp()}.md"

    if cached_path is not None and not force:
        sidecar = load_sidecar(cached_path)
        fetched_at = sidecar.get("fetched_at", "") if sidecar else ""
        age = _age_hours(fetched_at)

        if age < ttl_hours:
            return CacheResult(path=cached_path, status=CacheStatus.FRESH, page_name=page_name, url=url)

        # Stale — attempt refresh.
        # Catch broadly; re-raise anything that isn't a network error.
        try:
            new_content = fetch_url_text(url)
        except Exception as exc:
            if _is_network_error(exc):
                return CacheResult(path=cached_path, status=CacheStatus.STALE, page_name=page_name, url=url)
            raise

        old_content = read_text_or_none(cached_path) or ""
        if sha256_hex(new_content) == sha256_hex(old_content):
            # Content unchanged — touch sidecar only.
            if sidecar is not None:
                sidecar["fetched_at"] = utc_now_iso()
                sidecar_path = cached_path.with_suffix(".meta.json")
                write_json(sidecar_path, sidecar)
            else:
                write_sidecar(cached_path, url=url, content=new_content)
            return CacheResult(path=cached_path, status=CacheStatus.UNCHANGED, page_name=page_name, url=url)

        # Content changed — write new file.
        new_path = _new_path()
        new_path.write_text(new_content, encoding="utf-8")
        write_sidecar(new_path, url=url, content=new_content)
        return CacheResult(path=new_path, status=CacheStatus.REFRESHED, page_name=page_name, url=url)

    # No cached file, or force=True — must fetch.
    # Catch broadly; re-raise anything that isn't a network error.
    try:
        new_content = fetch_url_text(url)
    except Exception as exc:
        if _is_network_error(exc):
            if cached_path is not None:
                # force=True but network down; serve stale.
                return CacheResult(path=cached_path, status=CacheStatus.STALE, page_name=page_name, url=url)
            raise NoCacheError(url, str(exc)) from exc
        raise

    new_path = _new_path()
    new_path.write_text(new_content, encoding="utf-8")
    write_sidecar(new_path, url=url, content=new_content)
    return CacheResult(path=new_path, status=CacheStatus.NEW, page_name=page_name, url=url)


# ---------------------------------------------------------------------------
# Section decomposition
# ---------------------------------------------------------------------------


def _extract_ast_headings(text: str) -> list[tuple[int, str]]:
    """Extract ``(level, heading_text)`` pairs from a marko AST.

    Uses marko's parser to correctly identify ATX headings while ignoring
    ``#`` lines inside fenced code blocks.  Heading text is reconstructed
    from all inline children (RawText, CodeSpan, Emphasis, etc.) so that
    headings like ``The `/hooks` menu`` are captured fully.

    Returns:
        Ordered list of ``(level, text)`` tuples for each heading found.
    """
    doc = marko.parse(text)
    result: list[tuple[int, str]] = []
    for child in doc.children:
        if isinstance(child, MarkoHeading):
            parts: list[str] = []
            for inline in child.children:
                raw = getattr(inline, "children", "")
                parts.append(raw if isinstance(raw, str) else str(raw))
            result.append((child.level, "".join(parts).strip()))
    return result


def _map_headings_to_lines(ast_headings: list[tuple[int, str]], raw_lines: Sequence[str]) -> list[tuple[int, int, str]]:
    """Map AST headings to their 1-indexed source line numbers.

    Uses a code-fence state tracker to skip false-positive ``#`` lines
    inside fenced code blocks, then matches by heading level and position
    order (not text comparison, since marko strips inline formatting like
    backticks from heading text).

    Returns:
        List of ``(line_1indexed, level, heading_text_from_source)`` tuples.
    """
    headings: list[tuple[int, int, str]] = []
    ast_idx = 0
    in_fence = False

    for idx, line in enumerate(raw_lines):
        if ast_idx >= len(ast_headings):
            break

        # Track fenced code block state.
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue

        if in_fence:
            continue

        m = _HEADING_RE.match(line)
        if m:
            line_level = len(m.group(1))
            ast_level, _ast_text = ast_headings[ast_idx]
            if line_level == ast_level:
                # Use the source line text (preserves inline formatting).
                headings.append((idx + 1, line_level, m.group(2).strip()))
                ast_idx += 1
    return headings


def _build_sections(headings: list[tuple[int, int, str]], total_lines: int) -> list[MarkdownSection]:
    """Build :class:`MarkdownSection` objects from positioned headings.

    Returns:
        List of sections in document order, including preamble if present.
    """
    if not headings:
        return [MarkdownSection(heading="", level=0, line_start=1, line_end=total_lines)]

    def _find_end(start_line: int, level: int) -> int:
        for h_line, h_level, _ in headings:
            if h_line > start_line and h_level <= level:
                return h_line - 1
        return total_lines

    sections: list[MarkdownSection] = []
    first_heading_line = headings[0][0]

    if first_heading_line > 1:
        sections.append(MarkdownSection(heading="", level=0, line_start=1, line_end=first_heading_line - 1))

    for h_line, h_level, h_text in headings:
        sections.append(
            MarkdownSection(heading=h_text, level=h_level, line_start=h_line, line_end=_find_end(h_line, h_level))
        )

    return sections


def list_sections(file_path: Path) -> list[MarkdownSection]:
    r"""Parse a markdown file into a list of :class:`MarkdownSection` objects.

    Uses `marko <https://github.com/frostming/marko>`_ to parse the markdown
    AST, which correctly ignores ``#`` lines inside fenced code blocks.  The
    AST headings are then mapped back to source line numbers so that agents
    can use the :class:`~claude_code.Read` tool with exact line ranges.

    Scanning rules:

    - Headings are identified via the marko AST (ATX headings only).
    - Content before the first heading becomes a preamble section with
      ``heading=""`` and ``level=0``.
    - Each section spans from its heading line to the line immediately before
      the next heading of equal or higher level (lower number), or EOF.
    - Lines are 1-indexed to match the Read tool's display format.

    Args:
        file_path: Path to the markdown file to parse.

    Returns:
        List of :class:`MarkdownSection` objects in document order.
    """
    text = read_text_or_none(file_path) or ""
    raw_lines = text.splitlines()
    if not raw_lines:
        return []

    ast_headings = _extract_ast_headings(text)
    positioned = _map_headings_to_lines(ast_headings, raw_lines)
    return _build_sections(positioned, len(raw_lines))


def read_section(file_path: Path, heading: str) -> str | None:
    """Return the full text of the section matching *heading*.

    Matching supports two formats:

    - **Heading text** (case-insensitive): ``"Hook input and output"``
    - **Markdown anchor slug**: ``"hook-input-and-output"``

    Leading ``#`` characters and surrounding whitespace are stripped before
    comparison.  Both the heading text and its derived slug are tested
    against the query.

    Args:
        file_path: Path to the markdown file.
        heading: Heading text or markdown anchor slug to find.

    Returns:
        The full text of the matching section (including its heading line),
        or None if no match is found.
    """
    normalised_query = heading.lstrip("#").strip().lower()
    slug_query = _heading_to_slug(normalised_query)
    text = read_text_or_none(file_path) or ""
    lines = text.splitlines(keepends=True)

    for section in list_sections(file_path):
        candidate_text = section.heading.lstrip("#").strip().lower()
        candidate_slug = _heading_to_slug(section.heading)
        if normalised_query in {candidate_text, candidate_slug} or slug_query == candidate_slug:
            # line_start and line_end are 1-indexed.
            start = section.line_start - 1
            end = section.line_end  # exclusive upper bound for slicing
            return "".join(lines[start:end])

    return None


def format_section_index(file_path: Path) -> str:
    """Return a plain-text table of sections in *file_path*.

    Columns (0-indexed): ``index``, ``level``, ``heading``, ``lines``
    (``start-end``).  No Rich dependency; plain text only.

    Args:
        file_path: Path to the markdown file.

    Returns:
        Multi-line string containing a formatted table of sections.
    """
    sections = list_sections(file_path)
    if not sections:
        return "(no sections found)"

    rows: list[tuple[str, str, str, str]] = []
    for idx, sec in enumerate(sections):
        heading_display = sec.heading or "(preamble)"
        rows.append((str(idx), str(sec.level), heading_display, f"{sec.line_start}-{sec.line_end}"))

    headers = ("index", "level", "heading", "lines")
    col_widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]

    def _fmt_row(row: tuple[str, str, str, str]) -> str:
        return "  ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row))

    separator = "  ".join("-" * w for w in col_widths)
    table_lines = [_fmt_row(headers), separator, *(_fmt_row(row) for row in rows)]
    return "\n".join(table_lines)


# ---------------------------------------------------------------------------
# Integrity verification
# ---------------------------------------------------------------------------


def verify_integrity(file_path: Path) -> IntegrityResult:
    """Verify a cached file against its ``.meta.json`` sidecar.

    Reads the file, computes its SHA-256 digest and byte count, then compares
    against values stored in the sidecar (if any).

    Args:
        file_path: Path to the cached markdown file to verify.

    Returns:
        An :class:`IntegrityResult` describing the verification outcome.
    """
    content = read_text_or_none(file_path) or ""
    computed_sha256 = sha256_hex(content)
    computed_bytes = len(content.encode())

    sidecar = load_sidecar(file_path)
    if sidecar is None:
        return IntegrityResult(
            status=IntegrityStatus.UNVERIFIABLE,
            file_path=file_path,
            computed_sha256=computed_sha256,
            expected_sha256=None,
            computed_bytes=computed_bytes,
            expected_bytes=None,
        )

    expected_sha256: str | None = sidecar.get("sha256")
    expected_bytes: int | None = sidecar.get("byte_count")

    if computed_sha256 == expected_sha256 and computed_bytes == expected_bytes:
        status = IntegrityStatus.INTACT
    else:
        status = IntegrityStatus.MODIFIED

    return IntegrityResult(
        status=status,
        file_path=file_path,
        computed_sha256=computed_sha256,
        expected_sha256=expected_sha256,
        computed_bytes=computed_bytes,
        expected_bytes=expected_bytes,
    )
