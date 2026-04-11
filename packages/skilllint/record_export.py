"""Rich console recording export utilities.

Provides helpers to create a recording-capable Rich Console and export its
captured output to an SVG or HTML file atomically.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

from rich.console import Console

__all__ = ["build_svg_title", "export_recording", "make_recording_console"]


def make_recording_console(*, no_color: bool = False) -> Console:
    """Return a Rich Console configured for recording.

    The console uses ``record=True`` so that output written to it can later be
    exported via :func:`export_recording`.  ``force_terminal=True`` ensures
    Rich renders ANSI codes and colours regardless of whether stdout is a TTY
    (required for faithful SVG/HTML output).

    Args:
        no_color: When *True*, disable colour output (passes ``no_color=True``
            to Rich, which suppresses ANSI colour codes).

    Returns:
        A :class:`rich.console.Console` instance ready for recording.
    """
    return Console(record=True, force_terminal=True, no_color=no_color)


def export_recording(console: Console, path: Path, *, title: str) -> None:
    """Export a recorded Rich console session to *path*.

    The output format is determined by the file extension:

    - ``.html`` — :meth:`rich.console.Console.export_html`
    - anything else (including ``.svg``) — :meth:`rich.console.Console.export_svg`

    The write is atomic: content is first written to a :class:`tempfile.NamedTemporaryFile`
    in the same directory as *path*, then renamed into place with :func:`os.replace`.
    This ensures that a partial failure (e.g. disk full mid-write) never leaves a
    truncated file at the destination.

    Args:
        console: A :class:`rich.console.Console` that was created with
            ``record=True``.
        path: Destination file path.  The parent directory must already exist.
        title: Title string embedded in SVG exports (ignored for HTML exports,
            which do not expose a title parameter in Rich's API).

    Raises:
        ValueError: If *path* has an unsupported extension (only ``.svg`` and
            ``.html`` are accepted).
    """
    suffix = path.suffix.lower()
    if suffix not in {".svg", ".html"}:
        raise ValueError(f"Unsupported file extension {path.suffix!r}. Use .svg or .html.")
    content = console.export_html(clear=False) if suffix == ".html" else console.export_svg(title=title, clear=False)

    # Atomic write: write to a sibling temp file, then rename.
    dir_ = path.parent
    fd, tmp_path_str = tempfile.mkstemp(dir=dir_, suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        Path(tmp_path_str).replace(path)
    except Exception:
        # Clean up the temp file if anything goes wrong before the rename.
        with contextlib.suppress(OSError):
            Path(tmp_path_str).unlink()
        raise


def build_svg_title(argv: list[str]) -> str:
    """Build a human-readable SVG title from a command-line argument list.

    The function joins *argv* elements with spaces.  If the first element is
    not already ``"skilllint"``, the prefix ``"skilllint "`` is prepended so
    that the title always starts with the program name.

    Args:
        argv: Argument list, typically ``sys.argv[1:]`` (without the program
            name) or a full ``sys.argv``-style list.

    Returns:
        A title string suitable for embedding in an SVG ``<title>`` element.

    Examples:
        >>> build_svg_title(["check", "plugins/"])
        'skilllint check plugins/'
        >>> build_svg_title(["skilllint", "check", "plugins/"])
        'skilllint check plugins/'
    """
    joined = " ".join(argv)
    if not argv or argv[0] != "skilllint":
        return f"skilllint {joined}".strip()
    return joined
