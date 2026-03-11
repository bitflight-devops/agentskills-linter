#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.21.0",
#   "rich>=13.0",
#   "httpx>=0.27.0",
# ]
# ///
"""Fetch platform documentation for schema auditing.

Clones/updates git repos and fetches doc-site pages into .claude/vendor/.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, TypedDict, final

import httpx
import typer
from rich.console import Console
from rich.panel import Panel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = PROJECT_ROOT / ".claude" / "vendor"
DRIFT_FILE = VENDOR_DIR / ".drift-pending.json"

console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Drift detection data model — TypedDicts for serialized forms
# ---------------------------------------------------------------------------


class HttpFileDriftDict(TypedDict):
    """Serialized form of HttpFileDriftResult."""

    filename: str
    before_hash: str
    after_hash: str
    before_content: str
    after_content: str


class HttpDriftDict(TypedDict):
    """Serialized form of HttpDriftResult."""

    type: str
    provider: str
    files: list[HttpFileDriftDict]
    changelog: str | None


class GitDriftDict(TypedDict):
    """Serialized form of GitDriftResult."""

    type: str
    provider: str
    before_sha: str
    after_sha: str
    diff: str
    changelog: str


class DriftReportDict(TypedDict):
    """Serialized form of DriftReport."""

    fetch_time: str
    changed: list[GitDriftDict | HttpDriftDict]


# ---------------------------------------------------------------------------
# Drift detection data model — dataclasses
# ---------------------------------------------------------------------------


@dataclass
class HttpFileDriftResult:
    """Result of comparing a single HTTP-fetched file before/after."""

    filename: str
    before_hash: str
    after_hash: str
    before_content: str
    after_content: str

    def to_dict(self) -> HttpFileDriftDict:
        """Serialize to a JSON-compatible dictionary.

        Returns:
            Dictionary with all fields.
        """
        return HttpFileDriftDict(
            filename=self.filename,
            before_hash=self.before_hash,
            after_hash=self.after_hash,
            before_content=self.before_content,
            after_content=self.after_content,
        )


@dataclass
class HttpDriftResult:
    """Drift result for an HTTP doc-site platform."""

    provider: str
    files: list[HttpFileDriftResult] = field(default_factory=list)
    changelog: str | None = None

    def to_dict(self) -> HttpDriftDict:
        """Serialize to a JSON-compatible dictionary.

        Includes ``"type": "http"`` to distinguish from git results.

        Returns:
            Dictionary with all fields plus a ``type`` discriminator.
        """
        return HttpDriftDict(
            type="http", provider=self.provider, files=[f.to_dict() for f in self.files], changelog=self.changelog
        )


@dataclass
class GitDriftResult:
    """Drift result for a git-cloned platform."""

    provider: str
    before_sha: str
    after_sha: str
    diff: str = ""
    changelog: str = ""

    def to_dict(self) -> GitDriftDict:
        """Serialize to a JSON-compatible dictionary.

        Includes ``"type": "git"`` to distinguish from HTTP results.

        Returns:
            Dictionary with all fields plus a ``type`` discriminator.
        """
        return GitDriftDict(
            type="git",
            provider=self.provider,
            before_sha=self.before_sha,
            after_sha=self.after_sha,
            diff=self.diff,
            changelog=self.changelog,
        )


@dataclass
class DriftReport:
    """Top-level drift report containing all detected changes."""

    fetch_time: str
    changed: list[GitDriftResult | HttpDriftResult] = field(default_factory=list)

    def to_dict(self) -> DriftReportDict:
        """Serialize to a JSON-compatible dictionary.

        Calls ``to_dict()`` on each item in ``changed``.

        Returns:
            Dictionary with ``fetch_time`` and serialized ``changed`` list.
        """
        return DriftReportDict(fetch_time=self.fetch_time, changed=[item.to_dict() for item in self.changed])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(text: str) -> str:
    """Return hex SHA-256 digest of text content.

    Args:
        text: The string content to hash.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(text.encode()).hexdigest()


def _read_text_or_none(path: Path) -> str | None:
    """Read file content or return None if file does not exist.

    Args:
        path: Path to the file to read.

    Returns:
        File content as string, or None if file is missing.
    """
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


# ---------------------------------------------------------------------------
# Drift report writer
# ---------------------------------------------------------------------------


def _write_drift_report(report: DriftReport) -> None:
    """Serialize and write a drift report to the pending-drift JSON file.

    Creates parent directories if they do not exist.

    Args:
        report: The drift report to persist.
    """
    DRIFT_FILE.parent.mkdir(parents=True, exist_ok=True)
    _ = DRIFT_FILE.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Platform definitions
# ---------------------------------------------------------------------------


@final
class GitPlatform:
    """A platform whose docs come from a git repository."""

    __slots__ = ("name", "url")

    def __init__(self, name: str, url: str) -> None:
        self.name = name
        self.url = url


@final
class DocPage:
    """A single remote documentation page to fetch."""

    __slots__ = ("filename", "url")

    def __init__(self, url: str, filename: str) -> None:
        self.url = url
        self.filename = filename


@final
class DocSitePlatform:
    """A platform whose docs are fetched page-by-page via HTTP."""

    __slots__ = ("name", "pages", "releases_url")

    def __init__(self, name: str, pages: list[DocPage], releases_url: str | None = None) -> None:
        self.name = name
        self.pages = pages
        self.releases_url = releases_url


GIT_PLATFORMS: list[GitPlatform] = [
    GitPlatform("claude_code", "https://github.com/anthropics/claude-code"),
    GitPlatform("gemini_cli", "https://github.com/google-gemini/gemini-cli"),
    GitPlatform("codex", "https://github.com/openai/codex"),
    GitPlatform("kilocode", "https://github.com/Kilo-Org/kilocode"),
    GitPlatform("kimi", "https://github.com/MoonshotAI/kimi-cli"),
    GitPlatform("opencode", "https://github.com/anomalyco/opencode"),
]

DOC_SITE_PLATFORMS: list[DocSitePlatform] = [
    DocSitePlatform(
        "cursor",
        [DocPage("https://cursor.com/docs/context/rules", "rules.md")],
        releases_url="https://www.cursor.com/changelog",
    ),
    DocSitePlatform(
        "copilot_cli",
        [
            DocPage(
                "https://docs.github.com/api/article/body?pathname=/en/copilot/concepts/agents/copilot-cli/about-copilot-cli",
                "about-copilot-cli.md",
            ),
            DocPage(
                "https://docs.github.com/api/article/body?pathname=/en/copilot/how-tos/use-copilot-agents/use-copilot-cli",
                "using-copilot-cli.md",
            ),
        ],
        releases_url="https://github.com/github/copilot-cli/releases",
    ),
]

# ---------------------------------------------------------------------------
# Git operations
# ---------------------------------------------------------------------------


def _run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result.

    Args:
        args: Git subcommand and arguments (without leading 'git').
        cwd: Working directory for the command.

    Returns:
        Completed process with captured stdout/stderr.

    Raises:
        subprocess.CalledProcessError: If git exits non-zero.
    """
    git_bin = shutil.which("git")
    if git_bin is None:
        msg = "git executable not found on PATH"
        raise FileNotFoundError(msg)
    return subprocess.run([git_bin, *args], cwd=cwd, capture_output=True, text=True, check=True)


def _git_head_sha(repo_dir: Path) -> str | None:
    """Return the HEAD commit SHA for a git repository.

    Args:
        repo_dir: Path to the git repository root.

    Returns:
        The 40-character hex SHA, or None if the directory is not a git repo
        or does not exist.
    """
    if not (repo_dir / ".git").is_dir():
        return None
    try:
        result = _run_git(["rev-parse", "HEAD"], cwd=repo_dir)
    except subprocess.CalledProcessError:
        return None
    return result.stdout.strip() or None


def clone_or_update_repo(platform: GitPlatform, *, dry_run: bool) -> GitDriftResult | None:
    """Clone a repo on first run, or pull updates on subsequent runs.

    Captures the HEAD SHA before and after the git operation. When both
    SHAs are present and differ, a ``GitDriftResult`` with the diff and
    changelog between the two commits is returned.

    Args:
        platform: The git platform to clone/update.
        dry_run: If True, log what would happen without side effects.

    Returns:
        A ``GitDriftResult`` when vendor content changed, or ``None`` when
        there is no change, dry-run mode, or first clone (no *before* SHA).
    """
    dest = VENDOR_DIR / platform.name

    if dry_run:
        action = "pull" if (dest / ".git").is_dir() else "clone"
        console.print(f"  [dim]:fast-forward_button: dry-run: would git {action}[/dim] {platform.name}")
        return None

    before_sha = _git_head_sha(dest)

    VENDOR_DIR.mkdir(parents=True, exist_ok=True)

    if (dest / ".git").is_dir():
        console.print(f"  :fast-forward_button: Updating [cyan]{platform.name}[/cyan] (git pull)")
        try:
            _ = _run_git(["pull", "--ff-only", "--quiet"], cwd=dest)
        except subprocess.CalledProcessError:
            console.print("    [yellow]:warning: pull failed, trying fetch+reset[/yellow]")
            _ = _run_git(["fetch", "origin", "--quiet"], cwd=dest)
            try:
                result = _run_git(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=dest)
                default_branch = result.stdout.strip().removeprefix("refs/remotes/origin/")
            except subprocess.CalledProcessError:
                default_branch = "main"
            _ = _run_git(["reset", "--hard", f"origin/{default_branch}", "--quiet"], cwd=dest)
    else:
        console.print(f"  :inbox_tray: Cloning [cyan]{platform.name}[/cyan] from {platform.url}")
        _ = _run_git(["clone", "--quiet", "--depth", "1", platform.url, str(dest)])

    after_sha = _git_head_sha(dest)

    # First clone (no before_sha) or no change — nothing to report
    if before_sha is None or after_sha is None or before_sha == after_sha:
        return None

    # Unshallow if needed so before_sha is reachable for diff/log
    if (dest / ".git" / "shallow").exists():
        _ = _run_git(["fetch", "--unshallow"], cwd=dest)

    # Capture doc-relevant diff and changelog between the two SHAs
    try:
        diff_result = _run_git(["diff", f"{before_sha}..{after_sha}", "--", "*.md", "docs/", "CLAUDE.md"], cwd=dest)
        diff_output = diff_result.stdout
    except subprocess.CalledProcessError:
        diff_output = ""

    try:
        log_result = _run_git(["log", "--oneline", f"{before_sha}..{after_sha}"], cwd=dest)
        log_output = log_result.stdout.strip()
    except subprocess.CalledProcessError:
        log_output = ""

    return GitDriftResult(
        provider=platform.name, before_sha=before_sha, after_sha=after_sha, diff=diff_output, changelog=log_output
    )


# ---------------------------------------------------------------------------
# HTTP doc fetching
# ---------------------------------------------------------------------------


def fetch_doc_site(platform: DocSitePlatform, *, dry_run: bool) -> HttpDriftResult | None:
    """Fetch markdown pages from a documentation website.

    Compares fetched content against existing files to detect drift.
    When changes are detected and a ``releases_url`` is configured,
    the changelog page is fetched and included in the result.

    Args:
        platform: The doc-site platform with page URLs.
        dry_run: If True, log what would happen without side effects.

    Returns:
        An ``HttpDriftResult`` when at least one page changed, or
        ``None`` when no changes were detected (or on dry-run / first fetch).
    """
    dest = VENDOR_DIR / platform.name

    if dry_run:
        console.print(
            f"  [dim]:fast-forward_button: dry-run: would fetch {len(platform.pages)} pages for[/dim] {platform.name}"
        )
        return None

    dest.mkdir(parents=True, exist_ok=True)

    changed_files: list[HttpFileDriftResult] = []

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for page in platform.pages:
            console.print(f"  :globe_with_meridians: Fetching [cyan]{platform.name}[/cyan]/{page.filename}")
            try:
                # Snapshot existing content before fetch
                existing_content = _read_text_or_none(dest / page.filename)
                before_hash = _sha256(existing_content) if existing_content is not None else None

                response = client.get(page.url)
                _ = response.raise_for_status()
                new_content = response.text
                after_hash = _sha256(new_content)

                # Write the new content
                _ = (dest / page.filename).write_text(new_content, encoding="utf-8")

                # Detect drift: only when there was a previous file and hashes differ
                if before_hash is not None and before_hash != after_hash:
                    if existing_content is None:
                        continue
                    changed_files.append(
                        HttpFileDriftResult(
                            filename=page.filename,
                            before_hash=before_hash,
                            after_hash=after_hash,
                            before_content=existing_content,
                            after_content=new_content,
                        )
                    )
            except httpx.HTTPError as exc:
                err_console.print(f"    [yellow]:warning: Failed to fetch {page.url}: {exc}[/yellow]")

    if not changed_files:
        return None

    # Fetch changelog when changes detected and releases_url is set
    changelog: str | None = None
    if platform.releases_url:
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(platform.releases_url)
                _ = resp.raise_for_status()
                changelog = resp.text
        except httpx.HTTPError as exc:
            err_console.print(
                f"    [yellow]:warning: Failed to fetch changelog {platform.releases_url}: {exc}[/yellow]"
            )

    return HttpDriftResult(provider=platform.name, files=changed_files, changelog=changelog)


# ---------------------------------------------------------------------------
# Typer CLI
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="fetch-platform-docs",
    help="Clone/update platform repos and fetch doc-site pages for schema auditing.",
    no_args_is_help=False,
    rich_markup_mode="rich",
)


@app.command()
def fetch(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show what would happen without writing files or cloning repos.",
            rich_help_panel="Options",
        ),
    ] = False,
) -> None:
    """Fetch platform documentation into .claude/vendor/.

    Clones or updates git repos and fetches doc-site pages.

    Idempotent: safe to run multiple times. Uses git pull for existing
    clones, git clone for first run.

    Raises:
        typer.Exit: Exit code 2 when vendor changes are detected (non-dry-run).
    """
    if dry_run:
        console.print(
            Panel(
                "[dim]No files will be written or repos cloned.[/dim]",
                title=":eyes: Dry Run Mode",
                border_style="yellow",
            )
        )

    console.print(
        Panel(f"Vendor dir: {VENDOR_DIR}", title=":open_file_folder: Platform Documentation Fetch", border_style="blue")
    )

    # Phase A: Clone/update git repos
    console.print("\n[bold]Phase A: Clone/update git repos[/bold]")
    git_results: list[GitDriftResult] = []
    for platform in GIT_PLATFORMS:
        result = clone_or_update_repo(platform, dry_run=dry_run)
        if result is not None:
            git_results.append(result)

    # Phase B: Fetch doc-site pages
    console.print("\n[bold]Phase B: Fetch doc-site pages[/bold]")
    http_results: list[HttpDriftResult] = []
    for platform in DOC_SITE_PLATFORMS:
        result = fetch_doc_site(platform, dry_run=dry_run)
        if result is not None:
            http_results.append(result)

    # Collect all changes
    changed_results = git_results + http_results

    # Summary
    console.print()
    if dry_run:
        console.print(":white_check_mark: [bold green]Dry run complete.[/bold green]")
    elif changed_results:
        report = DriftReport(fetch_time=datetime.now(UTC).isoformat(), changed=changed_results)
        _write_drift_report(report)

        provider_names = ", ".join(r.provider for r in changed_results)
        console.print(
            Panel(
                f"Providers with changes: [bold]{provider_names}[/bold]\nReport written to: {DRIFT_FILE}",
                title=":warning: Vendor Drift Detected",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=2)
    else:
        console.print(f":white_check_mark: [bold green]Done. Vendor dir: {VENDOR_DIR}[/bold green]")


if __name__ == "__main__":
    app()
