"""Tests for drift detection data model and hash helpers in fetch_platform_docs."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.fetch_platform_docs import (
    DriftReport,
    GitDriftResult,
    HttpDriftResult,
    HttpFileDriftResult,
    _read_text_or_none,
    _sha256,
)

# ---------------------------------------------------------------------------
# _sha256 tests
# ---------------------------------------------------------------------------


def test_sha256_returns_hex_digest() -> None:
    """Known SHA-256 of 'hello' matches reference value."""
    assert (
        _sha256("hello")
        == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_sha256_same_input_same_output() -> None:
    """Deterministic: same input always produces same digest."""
    assert _sha256("foo") == _sha256("foo")


def test_sha256_different_inputs_different_output() -> None:
    """Different inputs produce different digests."""
    assert _sha256("foo") != _sha256("bar")


# ---------------------------------------------------------------------------
# _read_text_or_none tests
# ---------------------------------------------------------------------------


def test_read_text_or_none_existing_file_returns_content(tmp_path: Path) -> None:
    """Existing file content is returned as string."""
    f = tmp_path / "test.txt"
    f.write_text("hello", encoding="utf-8")
    assert _read_text_or_none(f) == "hello"


def test_read_text_or_none_missing_file_returns_none(tmp_path: Path) -> None:
    """Missing file returns None instead of raising."""
    assert _read_text_or_none(tmp_path / "nonexistent.txt") is None


# ---------------------------------------------------------------------------
# GitDriftResult.to_dict tests
# ---------------------------------------------------------------------------


def test_git_drift_result_to_dict_includes_type_git() -> None:
    """GitDriftResult.to_dict() includes type discriminator 'git'."""
    # Arrange
    result = GitDriftResult(
        provider="claude_code",
        before_sha="aaa",
        after_sha="bbb",
        diff="some diff",
        changelog="v2 released",
    )

    # Act
    d = result.to_dict()

    # Assert
    assert d["type"] == "git"
    assert d["provider"] == "claude_code"
    assert d["before_sha"] == "aaa"
    assert d["after_sha"] == "bbb"
    assert d["diff"] == "some diff"
    assert d["changelog"] == "v2 released"


def test_git_drift_result_to_dict_json_serializable() -> None:
    """GitDriftResult.to_dict() output is JSON-serializable."""
    result = GitDriftResult(provider="codex", before_sha="a", after_sha="b")
    serialized = json.dumps(result.to_dict())
    assert '"type": "git"' in serialized


# ---------------------------------------------------------------------------
# HttpFileDriftResult.to_dict tests
# ---------------------------------------------------------------------------


def test_http_file_drift_result_to_dict_round_trip() -> None:
    """HttpFileDriftResult round-trips through to_dict and back."""
    # Arrange
    original = HttpFileDriftResult(
        filename="rules.md",
        before_hash="abc",
        after_hash="def",
        before_content="old",
        after_content="new",
    )

    # Act
    d = original.to_dict()
    restored = HttpFileDriftResult(**d)

    # Assert
    assert restored == original


# ---------------------------------------------------------------------------
# HttpDriftResult.to_dict tests
# ---------------------------------------------------------------------------


def test_http_drift_result_to_dict_serializes_type_field() -> None:
    """HttpDriftResult.to_dict() includes hardcoded type discriminator 'http'."""
    # Arrange
    result = HttpDriftResult(provider="cursor")

    # Act
    d = result.to_dict()

    # Assert
    assert d["type"] == "http"
    assert "type_" not in d


def test_http_drift_result_to_dict_nested_files() -> None:
    """HttpDriftResult.to_dict() serializes nested HttpFileDriftResult list."""
    # Arrange
    file_result = HttpFileDriftResult(
        filename="rules.md",
        before_hash="aaa",
        after_hash="bbb",
        before_content="old",
        after_content="new",
    )
    result = HttpDriftResult(
        provider="cursor",
        files=[file_result],
        changelog="updated rules",
    )

    # Act
    d = result.to_dict()

    # Assert
    assert len(d["files"]) == 1
    assert d["files"][0]["filename"] == "rules.md"
    assert d["changelog"] == "updated rules"
    # Full dict must be JSON-serializable
    json.dumps(d)


# ---------------------------------------------------------------------------
# DriftReport.to_dict tests
# ---------------------------------------------------------------------------


def test_drift_report_to_dict_empty_changed() -> None:
    """DriftReport with no changes serializes correctly."""
    report = DriftReport(fetch_time="2026-03-11T00:00:00+00:00", changed=[])
    d = report.to_dict()
    assert d["fetch_time"] == "2026-03-11T00:00:00+00:00"
    assert d["changed"] == []
    json.dumps(d)  # must not raise


def test_drift_report_to_dict_mixed_results() -> None:
    """DriftReport.to_dict() calls to_dict() on each item in changed."""
    # Arrange
    git_result = GitDriftResult(provider="claude_code", before_sha="a1", after_sha="b2")
    http_result = HttpDriftResult(
        provider="cursor",
        files=[
            HttpFileDriftResult(
                filename="rules.md",
                before_hash="h1",
                after_hash="h2",
                before_content="old",
                after_content="new",
            )
        ],
    )
    report = DriftReport(
        fetch_time="2026-03-11T00:00:00+00:00",
        changed=[git_result, http_result],
    )

    # Act
    d = report.to_dict()

    # Assert
    assert len(d["changed"]) == 2
    assert d["changed"][0]["type"] == "git"
    assert d["changed"][1]["type"] == "http"
    # Full round-trip through JSON
    serialized = json.dumps(d)
    deserialized = json.loads(serialized)
    assert deserialized["fetch_time"] == "2026-03-11T00:00:00+00:00"
    assert len(deserialized["changed"]) == 2
