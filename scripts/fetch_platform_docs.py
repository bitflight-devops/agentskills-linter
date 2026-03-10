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

Clones/updates 6 git repos and fetches 2 doc-site platforms into
dated snapshots under official_sources/{YYYY-MM-DD}/.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, final

import httpx
import typer
from rich.console import Console
from rich.panel import Panel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = PROJECT_ROOT / ".claude" / "vendor"

console = Console()
err_console = Console(stderr=True)


class SourceKind(StrEnum):
    """How a platform's documentation is obtained."""

    GIT = "git"
    HTTPX = "httpx"


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

    __slots__ = ("name", "pages")

    def __init__(self, name: str, pages: list[DocPage]) -> None:
        self.name = name
        self.pages = pages


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
        [
            DocPage("https://cursor.com/docs/context/rules", "rules.md"),
        ],
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
    ),
]

# Key markdown files to extract from git repos
EXTRACT_MD_FILES: list[str] = [
    "README.md",
    "CHANGELOG.md",
    "RELEASES.md",
    "CONTRIBUTING.md",
]

# ---------------------------------------------------------------------------
# Git operations
# ---------------------------------------------------------------------------


def _run_git(
    args: list[str], *, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result.

    Args:
        args: Git subcommand and arguments (without leading 'git').
        cwd: Working directory for the command.

    Returns:
        Completed process with captured stdout/stderr.

    Raises:
        subprocess.CalledProcessError: If git exits non-zero.
    """
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def clone_or_update_repo(platform: GitPlatform, *, dry_run: bool) -> None:
    """Clone a repo on first run, or pull updates on subsequent runs.

    Args:
        platform: The git platform to clone/update.
        dry_run: If True, log what would happen without side effects.
    """
    dest = VENDOR_DIR / platform.name

    if dry_run:
        action = "pull" if (dest / ".git").is_dir() else "clone"
        console.print(
            f"  [dim]:fast-forward_button: dry-run: would git {action}[/dim] {platform.name}"
        )
        return

    VENDOR_DIR.mkdir(parents=True, exist_ok=True)

    if (dest / ".git").is_dir():
        console.print(
            f"  :fast-forward_button: Updating [cyan]{platform.name}[/cyan] (git pull)"
        )
        try:
            _ = _run_git(["pull", "--ff-only", "--quiet"], cwd=dest)
        except subprocess.CalledProcessError:
            console.print(
                "    [yellow]:warning: pull failed, trying fetch+reset[/yellow]"
            )
            _ = _run_git(["fetch", "origin", "--quiet"], cwd=dest)
            try:
                result = _run_git(
                    ["symbolic-ref", "refs/remotes/origin/HEAD"],
                    cwd=dest,
                )
                default_branch = result.stdout.strip().removeprefix(
                    "refs/remotes/origin/"
                )
            except subprocess.CalledProcessError:
                default_branch = "main"
            _ = _run_git(
                ["reset", "--hard", f"origin/{default_branch}", "--quiet"],
                cwd=dest,
            )
    else:
        console.print(
            f"  :inbox_tray: Cloning [cyan]{platform.name}[/cyan] from {platform.url}"
        )
        _ = _run_git(["clone", "--quiet", "--depth", "1", platform.url, str(dest)])


# ---------------------------------------------------------------------------
# HTTP doc fetching
# ---------------------------------------------------------------------------


def fetch_doc_site(platform: DocSitePlatform, *, dry_run: bool) -> None:
    """Fetch markdown pages from a documentation website.

    Args:
        platform: The doc-site platform with page URLs.
        dry_run: If True, log what would happen without side effects.
    """
    dest = VENDOR_DIR / platform.name

    if dry_run:
        console.print(
            f"  [dim]:fast-forward_button: dry-run: would fetch {len(platform.pages)} pages for[/dim] {platform.name}"
        )
        return

    dest.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for page in platform.pages:
            console.print(
                f"  :globe_with_meridians: Fetching [cyan]{platform.name}[/cyan]/{page.filename}"
            )
            try:
                response = client.get(page.url)
                _ = response.raise_for_status()
                _ = (dest / page.filename).write_text(response.text, encoding="utf-8")
            except httpx.HTTPError as exc:
                err_console.print(
                    f"    [yellow]:warning: Failed to fetch {page.url}: {exc}[/yellow]"
                )


# ---------------------------------------------------------------------------
# Extraction into dated snapshot
# ---------------------------------------------------------------------------


def extract_git_platform(
    platform: GitPlatform, output_dir: Path, *, dry_run: bool
) -> None:
    """Extract relevant docs from a vendor clone into the dated snapshot.

    Args:
        platform: The git platform to extract from.
        output_dir: Root dated snapshot directory.
        dry_run: If True, log what would happen without side effects.
    """
    vendor_path = VENDOR_DIR / platform.name
    snapshot_path = output_dir / platform.name

    if not vendor_path.is_dir():
        err_console.print(
            f"    [yellow]:warning: vendor dir missing for {platform.name}, skipping[/yellow]"
        )
        return

    if dry_run:
        console.print(
            f"  [dim]:fast-forward_button: dry-run: would extract docs for[/dim] {platform.name}"
        )
        return

    _ = snapshot_path.mkdir(parents=True, exist_ok=True)

    # Copy docs/ directory if present
    docs_src = vendor_path / "docs"
    if docs_src.is_dir():
        docs_dest = snapshot_path / "docs"
        if docs_dest.exists():
            shutil.rmtree(docs_dest)
        _ = shutil.copytree(docs_src, docs_dest)
        console.print(f"    Copied docs/ for {platform.name}")

    # Copy key markdown files
    for md_name in EXTRACT_MD_FILES:
        md_src = vendor_path / md_name
        if md_src.is_file():
            _ = shutil.copy2(md_src, snapshot_path / md_name)
            console.print(f"    Copied {md_name} for {platform.name}")

    # Save recent git log
    if (vendor_path / ".git").is_dir():
        try:
            result = _run_git(["log", "--oneline", "-50"], cwd=vendor_path)
            _ = (snapshot_path / "git-log.txt").write_text(
                result.stdout, encoding="utf-8"
            )
            console.print(f"    Saved git-log.txt for {platform.name}")
        except subprocess.CalledProcessError:
            pass


def extract_doc_platform(
    platform: DocSitePlatform, output_dir: Path, *, dry_run: bool
) -> None:
    """Copy fetched doc-site files into the dated snapshot.

    Args:
        platform: The doc-site platform to extract.
        output_dir: Root dated snapshot directory.
        dry_run: If True, log what would happen without side effects.
    """
    vendor_path = VENDOR_DIR / platform.name
    snapshot_path = output_dir / platform.name

    if not vendor_path.is_dir():
        err_console.print(
            f"    [yellow]:warning: vendor dir missing for {platform.name}, skipping[/yellow]"
        )
        return

    if dry_run:
        console.print(
            f"  [dim]:fast-forward_button: dry-run: would copy doc files for[/dim] {platform.name}"
        )
        return

    _ = snapshot_path.mkdir(parents=True, exist_ok=True)
    for md_file in vendor_path.glob("*.md"):
        _ = shutil.copy2(md_file, snapshot_path / md_file.name)
    console.print(f"    Copied doc files for {platform.name}")


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def _collect_files(directory: Path) -> list[str]:
    """Collect relative file paths under a directory, sorted.

    Args:
        directory: Directory to scan.

    Returns:
        Sorted list of relative paths as strings.
    """
    if not directory.is_dir():
        return []
    return sorted(
        str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()
    )


def write_manifest(output_dir: Path, *, dry_run: bool) -> None:
    """Write MANIFEST.json recording all fetched platforms and their files.

    Args:
        output_dir: Root dated snapshot directory.
        dry_run: If True, log what would happen without side effects.
    """
    if dry_run:
        console.print(
            "  [dim]:fast-forward_button: dry-run: would write MANIFEST.json[/dim]"
        )
        return

    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot_date = output_dir.name  # The YYYY-MM-DD directory name

    platforms_data: list[dict[str, str | list[str]]] = []

    # Git platforms
    for platform in GIT_PLATFORMS:
        vendor_path = VENDOR_DIR / platform.name
        sha = "unknown"
        if (vendor_path / ".git").is_dir():
            try:
                result = _run_git(["rev-parse", "HEAD"], cwd=vendor_path)
                sha = result.stdout.strip()
            except subprocess.CalledProcessError:
                pass

        platforms_data.append(
            {
                "name": platform.name,
                "source": SourceKind.GIT,
                "url": platform.url,
                "sha": sha,
                "timestamp": timestamp,
                "files": _collect_files(output_dir / platform.name),
            }
        )

    # Doc-site platforms
    for platform in DOC_SITE_PLATFORMS:
        platforms_data.append(
            {
                "name": platform.name,
                "source": SourceKind.HTTPX,
                "url": "see script for page list",
                "sha": "n/a",
                "timestamp": timestamp,
                "files": _collect_files(output_dir / platform.name),
            }
        )

    manifest = {
        "fetch_date": snapshot_date,
        "timestamp": timestamp,
        "platforms": platforms_data,
    }

    manifest_path = output_dir / "MANIFEST.json"
    _ = manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    console.print(f"  :white_check_mark: Wrote {manifest_path}")


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
    """Fetch platform documentation into a dated snapshot.

    Clones or updates 6 git repos and fetches 2 doc-site platforms.
    Extracted docs land in official_sources/{YYYY-MM-DD}/{platform}/.

    Idempotent: safe to run multiple times. Uses git pull for existing
    clones, git clone for first run.
    """
    snapshot_date = datetime.now(UTC).strftime("%Y-%m-%d")
    output_dir = PROJECT_ROOT / "official_sources" / snapshot_date

    if dry_run:
        console.print(
            Panel(
                "[dim]No files will be written or repos cloned.[/dim]",
                title=":eyes: Dry Run Mode",
                border_style="yellow",
            )
        )

    console.print(
        Panel(
            f"Vendor dir:   {VENDOR_DIR}\nSnapshot dir: {output_dir}",
            title=":open_file_folder: Platform Documentation Fetch",
            border_style="blue",
        )
    )

    # Phase A: Clone/update git repos
    console.print("\n[bold]Phase A: Clone/update git repos[/bold]")
    for platform in GIT_PLATFORMS:
        clone_or_update_repo(platform, dry_run=dry_run)

    # Phase B: Fetch doc-site pages
    console.print("\n[bold]Phase B: Fetch doc-site pages[/bold]")
    for platform in DOC_SITE_PLATFORMS:
        fetch_doc_site(platform, dry_run=dry_run)

    # Phase C: Extract docs into dated snapshot
    console.print("\n[bold]Phase C: Extract docs into snapshot[/bold]")
    if not dry_run:
        _ = output_dir.mkdir(parents=True, exist_ok=True)

    for platform in GIT_PLATFORMS:
        extract_git_platform(platform, output_dir, dry_run=dry_run)

    for platform in DOC_SITE_PLATFORMS:
        extract_doc_platform(platform, output_dir, dry_run=dry_run)

    # Phase D: Write manifest
    console.print("\n[bold]Phase D: Write manifest[/bold]")
    write_manifest(output_dir, dry_run=dry_run)

    # Summary
    console.print()
    if dry_run:
        console.print(":white_check_mark: [bold green]Dry run complete.[/bold green]")
    else:
        console.print(":white_check_mark: [bold green]Done.[/bold green]")
        console.print(f"  Snapshot at:  {output_dir}")
        console.print(f"  Manifest at:  {output_dir / 'MANIFEST.json'}")


if __name__ == "__main__":
    app()
