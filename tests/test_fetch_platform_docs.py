"""Tests for drift detection data model and hash helpers in fetch_platform_docs."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
from scripts.fetch_platform_docs import (
    DocPage,
    DocSitePlatform,
    DriftReport,
    GitDriftResult,
    GitPlatform,
    HttpDriftResult,
    HttpFileDriftResult,
    _git_head_sha,
    clone_or_update_repo,
    fetch_doc_site,
)

from skilllint.vendor_io import read_text_or_none as _read_text_or_none, sha256_hex as _sha256

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# _sha256 tests
# ---------------------------------------------------------------------------


def test_sha256_returns_hex_digest() -> None:
    """Known SHA-256 of 'hello' matches reference value."""
    assert _sha256("hello") == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


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
        provider="claude_code", before_sha="aaa", after_sha="bbb", diff="some diff", changelog="v2 released"
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
        filename="rules.md", before_hash="abc", after_hash="def", before_content="old", after_content="new"
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
        filename="rules.md", before_hash="aaa", after_hash="bbb", before_content="old", after_content="new"
    )
    result = HttpDriftResult(provider="cursor", files=[file_result], changelog="updated rules")

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
                filename="rules.md", before_hash="h1", after_hash="h2", before_content="old", after_content="new"
            )
        ],
    )
    report = DriftReport(fetch_time="2026-03-11T00:00:00+00:00", changed=[git_result, http_result])

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
# DocSitePlatform.releases_url tests
# ---------------------------------------------------------------------------


def test_doc_site_platform_releases_url_default_none() -> None:
    """DocSitePlatform.releases_url defaults to None."""
    platform = DocSitePlatform("test", [])
    assert platform.releases_url is None


def test_doc_site_platform_releases_url_set() -> None:
    """DocSitePlatform.releases_url can be set via constructor."""
    platform = DocSitePlatform("test", [], releases_url="https://example.com/releases")
    assert platform.releases_url == "https://example.com/releases"


# ---------------------------------------------------------------------------
# fetch_doc_site snapshot/compare tests
# ---------------------------------------------------------------------------


def _make_platform(
    name: str = "testplatform", pages: list[DocPage] | None = None, releases_url: str | None = None
) -> DocSitePlatform:
    """Create a DocSitePlatform for testing."""
    if pages is None:
        pages = [DocPage("https://example.com/docs/page.md", "page.md")]
    return DocSitePlatform(name, pages, releases_url=releases_url)


def _mock_response(text: str, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response with given text."""
    resp = MagicMock(spec=httpx.Response)
    resp.text = text
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


def test_fetch_doc_site_detects_content_change_returns_drift_result(tmp_path: Path) -> None:
    """When existing file has different content than fetched, return HttpDriftResult."""
    # Arrange
    platform = _make_platform()
    vendor_dir = tmp_path / ".claude" / "vendor"
    dest = vendor_dir / platform.name
    dest.mkdir(parents=True)
    (dest / "page.md").write_text("old content", encoding="utf-8")

    mock_resp = _mock_response("new content")

    with (
        patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir),
        patch("scripts.fetch_platform_docs.httpx.Client") as mock_client_cls,
    ):
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Act
        result = fetch_doc_site(platform, dry_run=False)

    # Assert
    assert result is not None
    assert result.provider == "testplatform"
    assert len(result.files) == 1
    assert result.files[0].filename == "page.md"
    assert result.files[0].before_content == "old content"
    assert result.files[0].after_content == "new content"
    assert result.files[0].before_hash == _sha256("old content")
    assert result.files[0].after_hash == _sha256("new content")
    assert result.files[0].before_hash != result.files[0].after_hash


def test_fetch_doc_site_no_change_returns_none(tmp_path: Path) -> None:
    """When existing file matches fetched content, return None."""
    # Arrange
    platform = _make_platform()
    vendor_dir = tmp_path / ".claude" / "vendor"
    dest = vendor_dir / platform.name
    dest.mkdir(parents=True)
    (dest / "page.md").write_text("same content", encoding="utf-8")

    mock_resp = _mock_response("same content")

    with (
        patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir),
        patch("scripts.fetch_platform_docs.httpx.Client") as mock_client_cls,
    ):
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Act
        result = fetch_doc_site(platform, dry_run=False)

    # Assert
    assert result is None


def test_fetch_doc_site_first_fetch_returns_none(tmp_path: Path) -> None:
    """When no existing file (first time fetch), return None."""
    # Arrange
    platform = _make_platform()
    vendor_dir = tmp_path / ".claude" / "vendor"

    mock_resp = _mock_response("brand new content")

    with (
        patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir),
        patch("scripts.fetch_platform_docs.httpx.Client") as mock_client_cls,
    ):
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Act
        result = fetch_doc_site(platform, dry_run=False)

    # Assert
    assert result is None
    # File should still be written on first fetch
    written = (vendor_dir / platform.name / "page.md").read_text(encoding="utf-8")
    assert written == "brand new content"


def test_fetch_doc_site_fetches_releases_url_when_changes_detected(tmp_path: Path) -> None:
    """When changes detected and releases_url set, changelog is included."""
    # Arrange
    platform = _make_platform(releases_url="https://example.com/changelog")
    vendor_dir = tmp_path / ".claude" / "vendor"
    dest = vendor_dir / platform.name
    dest.mkdir(parents=True)
    (dest / "page.md").write_text("old content", encoding="utf-8")

    page_resp = _mock_response("new content")
    changelog_resp = _mock_response("## v2.0\n- Big changes")

    def mock_get(url: str) -> MagicMock:
        if "changelog" in url:
            return changelog_resp
        return page_resp

    with (
        patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir),
        patch("scripts.fetch_platform_docs.httpx.Client") as mock_client_cls,
    ):
        mock_client = MagicMock()
        mock_client.get.side_effect = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Act
        result = fetch_doc_site(platform, dry_run=False)

    # Assert
    assert result is not None
    assert result.changelog == "## v2.0\n- Big changes"
    assert len(result.files) == 1


def test_fetch_doc_site_dry_run_returns_none() -> None:
    """Dry-run mode returns None without making HTTP requests."""
    # Arrange
    platform = _make_platform()

    # Act
    result = fetch_doc_site(platform, dry_run=True)

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# _git_head_sha tests
# ---------------------------------------------------------------------------


def test_git_head_sha_returns_sha_for_valid_repo(tmp_path: Path, mocker: MockerFixture) -> None:
    """Return the HEAD SHA when the directory is a valid git repo.

    Tests: _git_head_sha correctly extracts SHA from git rev-parse output.
    How: Create a .git directory so the is_dir() check passes, then mock
        _run_git to return a CompletedProcess with a known SHA on stdout.
    Why: Drift detection depends on capturing the before/after SHA to
        determine whether vendor content changed.
    """
    # Arrange
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    expected_sha = "abc123def456789012345678901234567890abcd"

    mock_run = mocker.patch(
        "scripts.fetch_platform_docs._run_git",
        return_value=subprocess.CompletedProcess(
            args=["git", "rev-parse", "HEAD"], returncode=0, stdout=f"  {expected_sha}  \n", stderr=""
        ),
    )

    # Act
    result = _git_head_sha(repo_dir)

    # Assert
    assert result == expected_sha
    mock_run.assert_called_once_with(["rev-parse", "HEAD"], cwd=repo_dir)


def test_git_head_sha_returns_none_for_non_repo(tmp_path: Path, mocker: MockerFixture) -> None:
    """Return None when the directory has no .git subdirectory.

    Tests: _git_head_sha guards against non-repo directories.
    How: Create a plain directory without .git, verify None is returned
        and _run_git is never called.
    Why: Before cloning a repo for the first time the destination directory
        may not exist or may not be a git repo. The function must handle
        this gracefully without subprocess errors.
    """
    # Arrange
    repo_dir = tmp_path / "not_a_repo"
    repo_dir.mkdir()
    mock_run = mocker.patch("scripts.fetch_platform_docs._run_git")

    # Act
    result = _git_head_sha(repo_dir)

    # Assert
    assert result is None
    mock_run.assert_not_called()


def test_git_head_sha_returns_none_when_rev_parse_fails(tmp_path: Path, mocker: MockerFixture) -> None:
    """Return None when git rev-parse HEAD raises CalledProcessError.

    Tests: _git_head_sha handles git command failures gracefully.
    How: Create a .git directory so the guard passes, then mock _run_git
        to raise CalledProcessError (e.g. empty repo with no commits).
    Why: A freshly-initialized repo with no commits will fail rev-parse.
        The function must return None instead of propagating the error.
    """
    # Arrange
    repo_dir = tmp_path / "empty_repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    mocker.patch(
        "scripts.fetch_platform_docs._run_git",
        side_effect=subprocess.CalledProcessError(
            returncode=128, cmd=["git", "rev-parse", "HEAD"], output="", stderr="fatal: bad default revision 'HEAD'"
        ),
    )

    # Act
    result = _git_head_sha(repo_dir)

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# clone_or_update_repo snapshot/compare tests
# ---------------------------------------------------------------------------


def _make_git_platform(name: str = "test_repo", url: str = "https://github.com/example/repo") -> GitPlatform:
    """Create a GitPlatform for testing.

    Args:
        name: Platform name used as the vendor subdirectory.
        url: Repository clone URL.

    Returns:
        A GitPlatform instance.
    """
    return GitPlatform(name, url)


def test_clone_or_update_repo_detects_change_returns_drift_result(tmp_path: Path, mocker: MockerFixture) -> None:
    """Return GitDriftResult with diff and changelog when SHA changes.

    Tests: clone_or_update_repo detects vendor content drift via SHA comparison.
    How: Set up a fake existing repo (.git dir present), mock _git_head_sha to
        return different SHAs before and after the pull, and mock _run_git to
        provide diff and log output.
    Why: The drift detection pipeline requires a GitDriftResult containing the
        before/after SHAs, diff of doc-relevant files, and commit changelog
        to generate actionable audit reports.
    """
    # Arrange
    vendor_dir = tmp_path / "vendor"
    platform = _make_git_platform()
    dest = vendor_dir / platform.name
    dest.mkdir(parents=True)
    (dest / ".git").mkdir()

    before_sha = "aaaa" * 10
    after_sha = "bbbb" * 10

    mocker.patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir)

    sha_call_count = 0

    def fake_git_head_sha(repo_dir: Path) -> str | None:
        nonlocal sha_call_count
        sha_call_count += 1
        if sha_call_count == 1:
            return before_sha
        return after_sha

    mocker.patch("scripts.fetch_platform_docs._git_head_sha", side_effect=fake_git_head_sha)

    def fake_run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        if args[0] == "pull":
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args[0] == "fetch" and "--unshallow" in args:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args[0] == "diff":
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="diff --git a/CLAUDE.md b/CLAUDE.md\n", stderr=""
            )
        if args[0] == "log":
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="abc1234 feat: update docs\ndef5678 fix: typo", stderr=""
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    mocker.patch("scripts.fetch_platform_docs._run_git", side_effect=fake_run_git)

    # Create .git/shallow to simulate a shallow clone
    (dest / ".git" / "shallow").touch()

    # Act
    result = clone_or_update_repo(platform, dry_run=False)

    # Assert
    assert result is not None
    assert isinstance(result, GitDriftResult)
    assert result.provider == "test_repo"
    assert result.before_sha == before_sha
    assert result.after_sha == after_sha
    assert "CLAUDE.md" in result.diff
    assert "feat: update docs" in result.changelog


def test_clone_or_update_repo_no_change_returns_none(tmp_path: Path, mocker: MockerFixture) -> None:
    """Return None when HEAD SHA is the same before and after pull.

    Tests: clone_or_update_repo correctly identifies no-change scenario.
    How: Mock _git_head_sha to return the same SHA both times (before and
        after the pull operation), mock _run_git for the pull command.
    Why: When a vendor repo has no new commits since the last fetch, no
        drift result should be generated to avoid false-positive reports.
    """
    # Arrange
    vendor_dir = tmp_path / "vendor"
    platform = _make_git_platform()
    dest = vendor_dir / platform.name
    dest.mkdir(parents=True)
    (dest / ".git").mkdir()

    same_sha = "cccc" * 10

    mocker.patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir)
    mocker.patch("scripts.fetch_platform_docs._git_head_sha", return_value=same_sha)
    mocker.patch(
        "scripts.fetch_platform_docs._run_git",
        return_value=subprocess.CompletedProcess(args=["git", "pull"], returncode=0, stdout="", stderr=""),
    )

    # Act
    result = clone_or_update_repo(platform, dry_run=False)

    # Assert
    assert result is None


def test_clone_or_update_repo_unshallows_before_diff(tmp_path: Path, mocker: MockerFixture) -> None:
    """Run ``git fetch --unshallow`` when .git/shallow exists before diffing.

    Tests: clone_or_update_repo unshallows a shallow clone so before_sha is
        reachable for git diff and git log.
    How: Set up a fake repo with .git/shallow present, mock _run_git and
        _git_head_sha to simulate a SHA change, then verify that the
        ``fetch --unshallow`` call was made before diff/log.
    Why: Shallow clones created with ``--depth 1`` do not retain older commits.
        After a pull the before_sha becomes unreachable, causing git diff and
        git log to fail. Unshallowing restores full history.
    """
    # Arrange
    vendor_dir = tmp_path / "vendor"
    platform = _make_git_platform()
    dest = vendor_dir / platform.name
    dest.mkdir(parents=True)
    (dest / ".git").mkdir()
    (dest / ".git" / "shallow").touch()

    before_sha = "aaaa" * 10
    after_sha = "bbbb" * 10

    mocker.patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir)

    sha_call_count = 0

    def fake_git_head_sha(repo_dir: Path) -> str | None:
        nonlocal sha_call_count
        sha_call_count += 1
        if sha_call_count == 1:
            return before_sha
        return after_sha

    mocker.patch("scripts.fetch_platform_docs._git_head_sha", side_effect=fake_git_head_sha)

    git_calls: list[list[str]] = []

    def fake_run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        git_calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    mocker.patch("scripts.fetch_platform_docs._run_git", side_effect=fake_run_git)

    # Act
    _ = clone_or_update_repo(platform, dry_run=False)

    # Assert — fetch --unshallow was called
    unshallow_calls = [c for c in git_calls if c == ["fetch", "--unshallow"]]
    assert len(unshallow_calls) == 1, f"Expected exactly 1 unshallow call, got {git_calls}"

    # Assert — unshallow happens before diff and log
    call_commands = [c[0] for c in git_calls]
    unshallow_idx = next(i for i, c in enumerate(git_calls) if "--unshallow" in c)
    diff_indices = [i for i, c in enumerate(git_calls) if c[0] == "diff"]
    log_indices = [i for i, c in enumerate(git_calls) if c[0] == "log"]
    for idx in diff_indices + log_indices:
        assert unshallow_idx < idx, (
            f"unshallow (index {unshallow_idx}) must precede diff/log (index {idx}), calls: {call_commands}"
        )


def test_clone_or_update_repo_skips_unshallow_when_not_shallow(tmp_path: Path, mocker: MockerFixture) -> None:
    """Skip ``git fetch --unshallow`` when .git/shallow does not exist.

    Tests: clone_or_update_repo does not unshallow a full clone.
    How: Set up a fake repo WITHOUT .git/shallow, mock SHA change, verify
        no fetch --unshallow call is made.
    """
    # Arrange
    vendor_dir = tmp_path / "vendor"
    platform = _make_git_platform()
    dest = vendor_dir / platform.name
    dest.mkdir(parents=True)
    (dest / ".git").mkdir()
    # No .git/shallow file — this is a full clone

    before_sha = "aaaa" * 10
    after_sha = "bbbb" * 10

    mocker.patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir)

    sha_call_count = 0

    def fake_git_head_sha(repo_dir: Path) -> str | None:
        nonlocal sha_call_count
        sha_call_count += 1
        if sha_call_count == 1:
            return before_sha
        return after_sha

    mocker.patch("scripts.fetch_platform_docs._git_head_sha", side_effect=fake_git_head_sha)

    git_calls: list[list[str]] = []

    def fake_run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        git_calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    mocker.patch("scripts.fetch_platform_docs._run_git", side_effect=fake_run_git)

    # Act
    _ = clone_or_update_repo(platform, dry_run=False)

    # Assert — no unshallow call
    unshallow_calls = [c for c in git_calls if "--unshallow" in c]
    assert len(unshallow_calls) == 0, f"Unexpected unshallow call in {git_calls}"


def test_clone_or_update_repo_first_clone_returns_none(tmp_path: Path, mocker: MockerFixture) -> None:
    """Return None on first clone when before_sha is None.

    Tests: clone_or_update_repo handles first-time clone scenario.
    How: Set up a vendor directory where the platform subdirectory does not
        exist (no .git), so _git_head_sha returns None for the before_sha.
        Mock _run_git for the clone command and _git_head_sha to return a
        SHA only on the second call (after clone).
    Why: On first clone there is no before_sha to compare against, so no
        drift can be reported. The function must return None rather than
        creating a misleading GitDriftResult.
    """
    # Arrange
    vendor_dir = tmp_path / "vendor"
    platform = _make_git_platform()

    mocker.patch("scripts.fetch_platform_docs.VENDOR_DIR", vendor_dir)

    sha_call_count = 0

    def fake_git_head_sha(repo_dir: Path) -> str | None:
        nonlocal sha_call_count
        sha_call_count += 1
        if sha_call_count == 1:
            return None  # No repo before clone
        return "dddd" * 10  # After clone

    mocker.patch("scripts.fetch_platform_docs._git_head_sha", side_effect=fake_git_head_sha)

    def fake_run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        if args[0] == "clone":
            # Simulate clone by creating the .git dir
            dest = vendor_dir / platform.name
            dest.mkdir(parents=True, exist_ok=True)
            (dest / ".git").mkdir(exist_ok=True)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    mocker.patch("scripts.fetch_platform_docs._run_git", side_effect=fake_run_git)

    # Act
    result = clone_or_update_repo(platform, dry_run=False)

    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# _write_drift_report tests
# ---------------------------------------------------------------------------


def test_write_drift_report_creates_json_file(tmp_path: Path) -> None:
    """_write_drift_report writes a valid JSON file to DRIFT_FILE."""
    # Arrange
    drift_file = tmp_path / ".drift-pending.json"
    report = DriftReport(
        fetch_time="2026-03-11T00:00:00+00:00",
        changed=[GitDriftResult(provider="claude_code", before_sha="aaa", after_sha="bbb")],
    )

    with patch("scripts.fetch_platform_docs.DRIFT_FILE", drift_file):
        # Act
        from scripts.fetch_platform_docs import _write_drift_report

        _write_drift_report(report)

    # Assert
    assert drift_file.exists()
    data = json.loads(drift_file.read_text(encoding="utf-8"))
    assert data["fetch_time"] == "2026-03-11T00:00:00+00:00"
    assert len(data["changed"]) == 1
    assert data["changed"][0]["provider"] == "claude_code"


# ---------------------------------------------------------------------------
# fetch command integration tests (CliRunner)
# ---------------------------------------------------------------------------


def test_fetch_command_exits_2_when_changes_detected(tmp_path: Path, mocker: MockerFixture) -> None:
    """Exit code 2 when vendor drift is detected in non-dry-run mode."""
    from scripts.fetch_platform_docs import app
    from typer.testing import CliRunner

    cli_runner = CliRunner()

    # Arrange — mock git platforms to return a drift result
    mocker.patch("scripts.fetch_platform_docs.GIT_PLATFORMS", [GitPlatform("test_repo", "https://example.com/repo")])
    mocker.patch("scripts.fetch_platform_docs.DOC_SITE_PLATFORMS", [])
    mocker.patch(
        "scripts.fetch_platform_docs.clone_or_update_repo",
        return_value=GitDriftResult(provider="test_repo", before_sha="aaa", after_sha="bbb"),
    )
    mocker.patch("scripts.fetch_platform_docs.DRIFT_FILE", tmp_path / ".drift-pending.json")

    # Act
    result = cli_runner.invoke(app)

    # Assert
    assert result.exit_code == 2


def test_fetch_command_exits_0_when_no_changes(tmp_path: Path, mocker: MockerFixture) -> None:
    """Exit code 0 when no vendor drift is detected."""
    from scripts.fetch_platform_docs import app
    from typer.testing import CliRunner

    cli_runner = CliRunner()

    # Arrange — mock all platforms to return None (no changes)
    mocker.patch("scripts.fetch_platform_docs.GIT_PLATFORMS", [GitPlatform("test_repo", "https://example.com/repo")])
    mocker.patch("scripts.fetch_platform_docs.DOC_SITE_PLATFORMS", [])
    mocker.patch("scripts.fetch_platform_docs.clone_or_update_repo", return_value=None)

    # Act
    result = cli_runner.invoke(app)

    # Assert
    assert result.exit_code == 0


def test_fetch_command_writes_drift_pending_json(tmp_path: Path, mocker: MockerFixture) -> None:
    """Drift report JSON file is written when changes are detected."""
    from scripts.fetch_platform_docs import app
    from typer.testing import CliRunner

    cli_runner = CliRunner()

    # Arrange
    drift_file = tmp_path / ".drift-pending.json"
    mocker.patch("scripts.fetch_platform_docs.GIT_PLATFORMS", [GitPlatform("test_repo", "https://example.com/repo")])
    mocker.patch("scripts.fetch_platform_docs.DOC_SITE_PLATFORMS", [])
    mocker.patch(
        "scripts.fetch_platform_docs.clone_or_update_repo",
        return_value=GitDriftResult(provider="test_repo", before_sha="aaa", after_sha="bbb"),
    )
    mocker.patch("scripts.fetch_platform_docs.DRIFT_FILE", drift_file)

    # Act
    _ = cli_runner.invoke(app)

    # Assert
    assert drift_file.exists()
    data = json.loads(drift_file.read_text(encoding="utf-8"))
    assert "fetch_time" in data
    assert "changed" in data
    assert len(data["changed"]) == 1


def test_fetch_command_dry_run_exits_0_regardless(tmp_path: Path, mocker: MockerFixture) -> None:
    """Dry-run exits 0 even when changes would be detected."""
    from scripts.fetch_platform_docs import app
    from typer.testing import CliRunner

    cli_runner = CliRunner()

    # Arrange — dry_run returns None from clone_or_update_repo
    mocker.patch("scripts.fetch_platform_docs.GIT_PLATFORMS", [GitPlatform("test_repo", "https://example.com/repo")])
    mocker.patch("scripts.fetch_platform_docs.DOC_SITE_PLATFORMS", [])
    mocker.patch("scripts.fetch_platform_docs.clone_or_update_repo", return_value=None)

    # Act
    result = cli_runner.invoke(app, ["--dry-run"])

    # Assert
    assert result.exit_code == 0


def test_drift_pending_json_matches_schema(tmp_path: Path, mocker: MockerFixture) -> None:
    """Written JSON has expected keys: fetch_time, changed array with provider entries."""
    from scripts.fetch_platform_docs import app
    from typer.testing import CliRunner

    cli_runner = CliRunner()

    # Arrange
    drift_file = tmp_path / ".drift-pending.json"
    mocker.patch("scripts.fetch_platform_docs.GIT_PLATFORMS", [GitPlatform("repo_a", "https://example.com/a")])
    mocker.patch(
        "scripts.fetch_platform_docs.DOC_SITE_PLATFORMS",
        [DocSitePlatform("site_b", [DocPage("https://example.com/page", "page.md")])],
    )
    mocker.patch(
        "scripts.fetch_platform_docs.clone_or_update_repo",
        return_value=GitDriftResult(provider="repo_a", before_sha="aaa", after_sha="bbb"),
    )
    mocker.patch(
        "scripts.fetch_platform_docs.fetch_doc_site",
        return_value=HttpDriftResult(
            provider="site_b",
            files=[
                HttpFileDriftResult(
                    filename="page.md", before_hash="h1", after_hash="h2", before_content="old", after_content="new"
                )
            ],
        ),
    )
    mocker.patch("scripts.fetch_platform_docs.DRIFT_FILE", drift_file)

    # Act
    _ = cli_runner.invoke(app)

    # Assert — validate schema structure
    data = json.loads(drift_file.read_text(encoding="utf-8"))
    assert "fetch_time" in data
    assert isinstance(data["changed"], list)
    assert len(data["changed"]) == 2

    # Check git entry
    git_entry = data["changed"][0]
    assert git_entry["type"] == "git"
    assert git_entry["provider"] == "repo_a"
    assert "before_sha" in git_entry
    assert "after_sha" in git_entry

    # Check http entry
    http_entry = data["changed"][1]
    assert http_entry["type"] == "http"
    assert http_entry["provider"] == "site_b"
    assert isinstance(http_entry["files"], list)
    assert len(http_entry["files"]) == 1
