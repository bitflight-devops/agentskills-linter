"""Shared low-level I/O utilities for vendor documentation fetching scripts.

This module is a plain library module with no CLI or presentation layer.
It is imported by scripts that fetch, cache, and compare external documentation:

  - scripts/fetch_platform_docs.py — bulk vendor sync with SHA-256 drift detection
  - scripts/fetch_spec_schema.py   — spec fetching with hash-based drift
  - scripts/fetch_doc_source.py    — on-demand single-page cache

Public API:
  Constants:
    PROJECT_ROOT -- absolute path to the repository root
    VENDOR_DIR   -- PROJECT_ROOT / ".claude" / "vendor"
    SOURCES_DIR  -- VENDOR_DIR / "sources"

  Functions:
    sha256_hex         -- full hex SHA-256 digest of text
    sha256_hex_short   -- truncated hex SHA-256 digest
    read_text_or_none  -- safe UTF-8 file read, None if missing
    write_json         -- write JSON with indent=2 and trailing newline
    load_json_or_none  -- load JSON from path, None if missing/corrupt
    fetch_url_text     -- fetch URL and return response body as text
    write_sidecar      -- write .meta.json sidecar alongside a saved file
    load_sidecar       -- load .meta.json sidecar for a given file path
    utc_now_iso        -- current UTC time as ISO 8601 string

Dependencies:
  httpx -- HTTP client (already a project dev dependency)
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Directory constants
# ---------------------------------------------------------------------------

#: Absolute path to the repository root.
#: vendor_io.py lives at packages/skilllint/vendor_io.py:
#:   .parent                → packages/skilllint/
#:   .parent.parent         → packages/
#:   .parent.parent.parent  → repo root (contains pyproject.toml)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

#: Vendor documentation directory inside .claude/.
VENDOR_DIR: Path = PROJECT_ROOT / ".claude" / "vendor"

#: Per-source cached documents directory.
SOURCES_DIR: Path = VENDOR_DIR / "sources"


# ---------------------------------------------------------------------------
# Hash utilities
# ---------------------------------------------------------------------------


def sha256_hex(text: str) -> str:
    """Return full hex SHA-256 digest of text content.

    Args:
        text: The string content to hash (encoded as UTF-8).

    Returns:
        64-character hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(text.encode()).hexdigest()


def sha256_hex_short(text: str, *, length: int = 12) -> str:
    """Return truncated hex SHA-256 digest.

    Args:
        text: The string content to hash (encoded as UTF-8).
        length: Number of hex characters to return. Defaults to 12.

    Returns:
        Hex-encoded SHA-256 digest truncated to ``length`` characters.
    """
    return hashlib.sha256(text.encode()).hexdigest()[:length]


# ---------------------------------------------------------------------------
# File I/O utilities
# ---------------------------------------------------------------------------


def read_text_or_none(path: Path) -> str | None:
    """Read file content as UTF-8, or return None if missing.

    Args:
        path: Path to the file to read.

    Returns:
        File content as a string, or None if the file does not exist.
    """
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def write_json(path: Path, data: dict[str, Any] | list[Any]) -> None:
    """Write JSON with indent=2 and a trailing newline.

    Creates parent directories if they do not exist.

    Args:
        path: Destination file path.
        data: JSON-serialisable dict or list to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_json_or_none(path: Path) -> dict[str, Any] | None:
    """Load JSON from path, or return None if missing or unparseable.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed dict, or None if the file does not exist or contains invalid JSON.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# HTTP utilities
# ---------------------------------------------------------------------------


def fetch_url_text(url: str, *, timeout: float = 30.0, follow_redirects: bool = True) -> str:
    """Fetch a URL and return the response body as text.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds. Defaults to 30.0.
        follow_redirects: Whether to follow HTTP redirects. Defaults to True.

    Returns:
        Response body decoded as text.

    Raises:
        httpx.HTTPStatusError: On non-2xx HTTP responses.
        ValueError: If the response body is empty.
    """
    with httpx.Client(timeout=timeout, follow_redirects=follow_redirects) as client:
        response = client.get(url)
        response.raise_for_status()
        text = response.text
        if not text:
            raise ValueError(f"Empty response body from {url!r}")
        return text


# ---------------------------------------------------------------------------
# Sidecar (.meta.json) utilities
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    """Return current UTC time as an ISO 8601 string.

    Returns:
        UTC timestamp in ISO 8601 format, e.g. ``"2026-03-23T14:05:00+00:00"``.
    """
    return datetime.now(UTC).isoformat()


def write_sidecar(md_path: Path, *, url: str, content: str) -> Path:
    """Write a ``.meta.json`` sidecar alongside a saved file.

    Records provenance metadata: source URL, fetch timestamp, SHA-256 digest,
    and byte count of the content.

    Sidecar path convention: for ``/path/to/file.md`` the sidecar is
    ``/path/to/file.meta.json``.

    Args:
        md_path: Path to the saved content file (e.g. a ``.md`` file).
        url: The URL the content was fetched from.
        content: The raw text content that was saved.

    Returns:
        Path to the written sidecar file.
    """
    sidecar_path = md_path.with_suffix(".meta.json")
    metadata: dict[str, Any] = {
        "url": url,
        "fetched_at": utc_now_iso(),
        "sha256": sha256_hex(content),
        "byte_count": len(content.encode()),
    }
    write_json(sidecar_path, metadata)
    return sidecar_path


def load_sidecar(md_path: Path) -> dict[str, Any] | None:
    """Load the ``.meta.json`` sidecar for a given file path.

    Args:
        md_path: Path to the content file whose sidecar to load.

    Returns:
        Parsed sidecar dict, or None if the sidecar is missing or corrupt.
    """
    sidecar_path = md_path.with_suffix(".meta.json")
    return load_json_or_none(sidecar_path)
