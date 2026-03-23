"""Typer sub-app for the ``skilllint docs`` subcommand group.

Provides ``fetch``, ``latest``, ``sections``, ``section``, and ``verify``
commands that wrap :mod:`skilllint.vendor_cache`.  All business logic lives in
that module — this file is a pure CLI adapter.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from skilllint.vendor_cache import (
    CacheStatus,
    IntegrityStatus,
    NoCacheError,
    fetch_or_cached,
    find_latest,
    format_section_index,
    read_section,
    verify_integrity,
)

# ---------------------------------------------------------------------------
# Consoles
# ---------------------------------------------------------------------------

console = Console()  # stdout — file paths and data output
err_console = Console(stderr=True)  # stderr — status, warnings, errors

# ---------------------------------------------------------------------------
# Typer sub-app
# ---------------------------------------------------------------------------

docs_app = typer.Typer(
    help="Fetch, query, and verify cached vendor documentation.",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------


@docs_app.command()
def fetch(
    url: Annotated[str, typer.Argument(help="Documentation URL to fetch or serve from cache.")],
    ttl: Annotated[
        float,
        typer.Option(
            "--ttl", help="Cache time-to-live in hours before a refresh is attempted.", rich_help_panel="Cache Options"
        ),
    ] = 4.0,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Skip the freshness check and always attempt a network fetch.",
            rich_help_panel="Cache Options",
        ),
    ] = False,
) -> None:
    """Fetch a documentation page or return a cached copy.

    Prints the cached file path to stdout so agents can capture it.
    Status information is written to stderr.

    Raises:
        typer.Exit: Exit code 1 when no cache exists and network is unavailable.
    """
    try:
        result = fetch_or_cached(url, ttl_hours=ttl, force=force)
    except NoCacheError as exc:
        err_console.print(
            Panel(
                f"[bold]URL:[/bold] {exc.url}\n[bold]Reason:[/bold] {exc.reason}",
                title=":cross_mark: No Cache Available",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc

    if result.status is CacheStatus.STALE:
        err_console.print(":warning: [yellow]Serving stale cache — network unavailable[/yellow]")
    else:
        status_label = result.status.value.upper()
        err_console.print(f":white_check_mark: [green]{status_label}[/green] {result.page_name}")

    console.print(result.path)


# ---------------------------------------------------------------------------
# latest
# ---------------------------------------------------------------------------


@docs_app.command()
def latest(
    page_name: Annotated[
        str, typer.Argument(help="Filesystem-safe page name to look up (e.g. 'claude-code--settings').")
    ],
) -> None:
    """Find the most recent cached file for a page name.

    Prints the file path to stdout when found.

    Raises:
        typer.Exit: Exit code 1 when no cached file exists for the given page name.
    """
    path = find_latest(page_name)
    if path is None:
        err_console.print(f":cross_mark: [red]No cached file found for page name:[/red] {page_name}")
        raise typer.Exit(code=1)

    console.print(path)


# ---------------------------------------------------------------------------
# sections
# ---------------------------------------------------------------------------


@docs_app.command()
def sections(file_path: Annotated[Path, typer.Argument(help="Path to the cached markdown file to index.")]) -> None:
    """Print a table of sections in a cached markdown file.

    Output is written to stdout.
    """
    table = format_section_index(file_path)
    console.print(table)


# ---------------------------------------------------------------------------
# section
# ---------------------------------------------------------------------------


@docs_app.command()
def section(
    file_path: Annotated[Path, typer.Argument(help="Path to the cached markdown file.")],
    heading: Annotated[str, typer.Argument(help="Heading text to locate (case-insensitive, leading # optional).")],
) -> None:
    """Print the text of a named section from a cached markdown file.

    Output is written to stdout.

    Raises:
        typer.Exit: Exit code 1 when the heading is not found.
    """
    text = read_section(file_path, heading)
    if text is None:
        err_console.print(f":cross_mark: [red]Section not found:[/red] {heading!r} in {file_path}")
        raise typer.Exit(code=1)

    console.print(text, end="")


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


@docs_app.command()
def verify(
    file_path: Annotated[Path, typer.Argument(help="Path to the cached markdown file to verify against its sidecar.")],
) -> None:
    """Verify a cached file against its .meta.json sidecar.

    Exits 0 when the file is intact, 1 otherwise.

    Raises:
        typer.Exit: Exit code 1 when MODIFIED or UNVERIFIABLE.
    """
    result = verify_integrity(file_path)

    match result.status:
        case IntegrityStatus.INTACT:
            console.print(
                f":white_check_mark: [green]INTACT[/green] {file_path}\n"
                f"  sha256: {result.computed_sha256}\n"
                f"  bytes:  {result.computed_bytes}"
            )

        case IntegrityStatus.MODIFIED:
            err_console.print(
                Panel(
                    f"[bold]File:[/bold] {file_path}\n"
                    f"[bold]Computed sha256:[/bold]  {result.computed_sha256}\n"
                    f"[bold]Expected sha256:[/bold]  {result.expected_sha256}\n"
                    f"[bold]Computed bytes:[/bold]   {result.computed_bytes}\n"
                    f"[bold]Expected bytes:[/bold]   {result.expected_bytes}",
                    title=":warning: MODIFIED — file differs from sidecar",
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=1)

        case IntegrityStatus.UNVERIFIABLE:
            err_console.print(
                Panel(
                    f"[bold]File:[/bold] {file_path}\nNo .meta.json sidecar found — cannot verify this file.",
                    title=":warning: UNVERIFIABLE — no sidecar",
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=1)
