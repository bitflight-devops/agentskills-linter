"""Tests for drift detection data model and hash helpers in fetch_platform_docs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.fetch_platform_docs import (
    DriftReport,
    GitDriftResult,
    GitPlatform,
    HttpDriftResult,
    HttpFileDriftResult,
    _git_head_sha,
    _read_text_or_none,
    _sha256,
    clone_or_update_repo,
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


# ---------------------------------------------------------------------------
# _git_head_sha tests
# ---------------------------------------------------------------------------


def _make_completed_process(stdout: str) -> subprocess.CompletedProcess[str]:
    """Create a CompletedProcess with the given stdout."""
    return subprocess.CompletedProcess(args=["git"], returncode=0, stdout=stdout)


def test_git_head_sha_returns_sha_for_valid_repo(tmp_path: Path) -> None:
    """_git_head_sha returns the SHA when rev-parse HEAD succeeds."""
    # Arrange
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    expected_sha = "abc123def456789012345678901234567890abcd"

    # Act
    with patch(
        "scripts.fetch_platform_docs._run_git",
        return_value=_make_completed_process(f"{expected_sha}\n"),
    ) as mock_git:
        result = _git_head_sha(tmp_path)

    # Assert
    assert result == expected_sha
    mock_git.assert_called_once_with(["rev-parse", "HEAD"], cwd=tmp_path)


def test_git_head_sha_returns_none_for_non_repo(tmp_path: Path) -> None:
    """_git_head_sha returns None when directory has no .git subdirectory."""
    # Arrange — tmp_path has no .git directory

    # Act
    result = _git_head_sha(tmp_path)

    # Assert
    assert result is None


def test_git_head_sha_returns_none_when_rev_parse_fails(tmp_path: Path) -> None:
    """_git_head_sha returns None when git rev-parse raises CalledProcessError."""
    # Arrange
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    # Act
    with patch(
        "scripts.fetch_platform_docs._run_git",
        side_effect=subprocess.CalledProcessError(128, "git"),
    ):
        result = _git_head_sha(tmp_path)

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# clone_or_update_repo snapshot/compare tests
# ---------------------------------------------------------------------------

BEFORE_SHA = "aaaa" * 10
AFTER_SHA = "bbbb" * 10


def _mock_run_git_update(
    before_sha: str, after_sha: str, diff: str = "", log: str = ""
) -> MagicMock:
    """Create a mock _run_git that simulates an existing repo being updated.

    Returns different SHAs for rev-parse HEAD calls (before and after pull),
    and the provided diff/log output for the diff and log commands.
    """
    sha_calls: list[str] = []

    def side_effect(
        args: list[str], *, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        if args == ["rev-parse", "HEAD"]:
            # First call returns before_sha, second returns after_sha
            sha = before_sha if len(sha_calls) == 0 else after_sha
            sha_calls.append(sha)
            return _make_completed_process(f"{sha}\n")
        if args[0] == "pull":
            return _make_completed_process("")
        if args[0] == "diff":
            return _make_completed_process(diff)
        if args[0] == "log":
            return _make_completed_process(log)
        return _make_completed_process("")

    return MagicMock(side_effect=side_effect)


def test_clone_or_update_repo_detects_change_returns_drift_result(
    tmp_path: Path,
) -> None:
    """When SHAs differ after pull, clone_or_update_repo returns GitDriftResult."""
    # Arrange
    platform = GitPlatform("test_platform", "https://example.com/repo.git")
    dest = tmp_path / "test_platform"
    dest.mkdir()
    (dest / ".git").mkdir()

    mock_git = _mock_run_git_update(
        BEFORE_SHA, AFTER_SHA, diff="diff content here", log="abc1234 some commit"
    )

    # Act
    with (
        patch("scripts.fetch_platform_docs._run_git", mock_git),
        patch("scripts.fetch_platform_docs.VENDOR_DIR", tmp_path),
    ):
        result = clone_or_update_repo(platform, dry_run=False)

    # Assert
    assert result is not None
    assert isinstance(result, GitDriftResult)
    assert result.provider == "test_platform"
    assert result.before_sha == BEFORE_SHA
    assert result.after_sha == AFTER_SHA
    assert result.diff == "diff content here"
    assert result.changelog == "abc1234 some commit"


def test_clone_or_update_repo_no_change_returns_none(tmp_path: Path) -> None:
    """When SHAs are identical after pull, clone_or_update_repo returns None."""
    # Arrange
    platform = GitPlatform("test_platform", "https://example.com/repo.git")
    dest = tmp_path / "test_platform"
    dest.mkdir()
    (dest / ".git").mkdir()

    mock_git = _mock_run_git_update(BEFORE_SHA, BEFORE_SHA)

    # Act
    with (
        patch("scripts.fetch_platform_docs._run_git", mock_git),
        patch("scripts.fetch_platform_docs.VENDOR_DIR", tmp_path),
    ):
        result = clone_or_update_repo(platform, dry_run=False)

    # Assert
    assert result is None


def test_clone_or_update_repo_first_clone_returns_none(tmp_path: Path) -> None:
    """First clone (no existing .git dir) returns None — no before_sha to compare."""
    # Arrange
    platform = GitPlatform("test_platform", "https://example.com/repo.git")
    # dest does NOT exist yet — simulates first clone

    call_count = 0

    def side_effect(
        args: list[str], *, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        nonlocal call_count
        if args == ["rev-parse", "HEAD"]:
            # After clone, rev-parse returns a SHA
            call_count += 1
            if call_count == 1:
                # This is the post-clone call (before_sha was None)
                return _make_completed_process(f"{AFTER_SHA}\n")
            return _make_completed_process(f"{AFTER_SHA}\n")
        if args[0] == "clone":
            # Simulate clone by creating .git dir
            dest = tmp_path / "test_platform"
            dest.mkdir(exist_ok=True)
            (dest / ".git").mkdir(exist_ok=True)
            return _make_completed_process("")
        return _make_completed_process("")

    # Act
    with (
        patch(
            "scripts.fetch_platform_docs._run_git", MagicMock(side_effect=side_effect)
        ),
        patch("scripts.fetch_platform_docs.VENDOR_DIR", tmp_path),
    ):
        result = clone_or_update_repo(platform, dry_run=False)

    # Assert — before_sha was None so result is None
    assert result is None
