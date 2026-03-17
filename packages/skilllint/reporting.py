"""Validation result reporters.

Extracted from ``plugin_validator`` so the CLI entrypoint can delegate output
formatting to a dedicated module without changing user-facing behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeAlias

from rich.console import Console, ConsoleRenderable, RichCast
from rich.measure import Measurement
from rich.panel import Panel

if TYPE_CHECKING:
    from skilllint.plugin_validator import ValidationIssue, ValidationResult

FileResults: TypeAlias = dict[Path, list[tuple[str, "ValidationResult"]]]


class Reporter(Protocol):
    """Protocol for result reporters.

    Defines interface for formatting and displaying validation results to users.
    Different implementations support various output formats (Rich terminal,
    plain text for CI, summary).
    """

    def report(self, file_results: FileResults, verbose: bool = False, *, show_progress: bool = False) -> None:
        """Display validation results grouped by file."""
        ...

    def summarize(self, total_files: int, passed: int, failed: int, warnings: int) -> None:
        """Display summary statistics."""
        ...


class ConsoleReporter:
    """Rich-based terminal reporter with colored output."""

    def __init__(self, console: Console | None = None, *, no_color: bool = False) -> None:
        if console is not None:
            self.console = console
        else:
            self.console = Console(force_terminal=not no_color, no_color=no_color)
        self.no_color = no_color

    @staticmethod
    def _get_rendered_width(renderable: ConsoleRenderable | RichCast | str) -> int:
        """Get actual rendered width of any Rich renderable.

        Returns:
            The maximum rendered width in characters.
        """
        temp_console = Console(width=999999)
        measurement = Measurement.get(temp_console, temp_console.options, renderable)
        return int(measurement.maximum)

    def _print_issue(self, issue: ValidationIssue) -> None:
        """Print a single validation issue with Rich formatting."""
        severity_icons = {"error": ":cross_mark:", "warning": ":warning:", "info": ":information:"}
        severity_colors = {"error": "red", "warning": "yellow", "info": "blue"}

        icon = severity_icons.get(issue.severity, "")
        color = severity_colors.get(issue.severity, "white")
        location = f":{issue.line}" if issue.line else ""

        self.console.print(
            f"    {icon} [{color}][{issue.code}][/{color}] {issue.field}{location}: {issue.message}",
            crop=False,
            overflow="ignore",
        )

        if issue.suggestion:
            self.console.print(f"      [dim]→[/dim] {issue.suggestion}", crop=False, overflow="ignore")

        if issue.docs_url:
            self.console.print(f"      [dim]→[/dim] [link]{issue.docs_url}[/link]", crop=False, overflow="ignore")

    def report(self, file_results: FileResults, verbose: bool = False, *, show_progress: bool = False) -> None:
        """Display validation results with Rich formatting, grouped by file."""
        for file_path, validator_results in file_results.items():
            all_passed = all(r.passed for _, r in validator_results)
            any_issues = False

            for _vname, result in validator_results:
                issues_to_show = [*result.errors, *result.warnings]
                if verbose:
                    issues_to_show.extend(result.info)
                if issues_to_show:
                    any_issues = True

            if all_passed and not any_issues:
                if show_progress:
                    self.console.print(
                        f":white_check_mark: [green]{file_path}[/green] - PASSED", crop=False, overflow="ignore"
                    )
                continue

            self.console.print(f"\n[bold]{file_path}[/bold]", crop=False, overflow="ignore")

            for validator_name, result in validator_results:
                issues_to_show = [*result.errors, *result.warnings]
                if verbose:
                    issues_to_show.extend(result.info)

                if not issues_to_show:
                    if show_progress:
                        self.console.print(
                            f"  :white_check_mark: [dim]{validator_name}:[/dim] PASSED", crop=False, overflow="ignore"
                        )
                    continue

                status_icon = ":cross_mark:" if not result.passed else ":warning:"
                self.console.print(f"  {status_icon} [dim]{validator_name}:[/dim]", crop=False, overflow="ignore")

                for issue in issues_to_show:
                    self._print_issue(issue)

    def summarize(self, total_files: int, passed: int, failed: int, warnings: int) -> None:
        """Display summary statistics with Rich formatting."""
        if failed == 0:
            status_icon = ":white_check_mark:"
            status_text = "PASSED"
            status_color = "green"
        else:
            status_icon = ":cross_mark:"
            status_text = "FAILED"
            status_color = "red"

        summary_lines = [
            f"{status_icon} [bold {status_color}]{status_text}[/bold {status_color}]",
            "",
            f"Total files: {total_files}",
            f"[green]Passed: {passed}[/green]",
            f"[red]Failed: {failed}[/red]",
        ]

        if warnings > 0:
            summary_lines.append(f"[yellow]Warnings: {warnings}[/yellow]")

        summary = "\n".join(summary_lines)
        panel = Panel(summary, title="Validation Summary", border_style=status_color, expand=False)
        panel_width = self._get_rendered_width(panel)
        self.console.width = panel_width
        self.console.print(panel, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)


class CIReporter:
    """Plain text reporter for CI environments."""

    @staticmethod
    def _print_issue(issue: ValidationIssue) -> None:
        """Print a single validation issue in plain text."""
        severity_prefixes = {"error": "✗ ERROR", "warning": "⚠ WARN", "info": "i INFO"}
        prefix = severity_prefixes.get(issue.severity, "")
        location = f":{issue.line}" if issue.line else ""

        print(f"    {prefix} [{issue.code}] {issue.field}{location}: {issue.message}")

        if issue.suggestion:
            print(f"      → {issue.suggestion}")

        if issue.docs_url:
            print(f"      → {issue.docs_url}")

    def report(self, file_results: FileResults, verbose: bool = False, *, show_progress: bool = False) -> None:
        """Display validation results in plain text, grouped by file."""
        for file_path, validator_results in file_results.items():
            all_passed = all(r.passed for _, r in validator_results)
            any_issues = False

            for _vname, result in validator_results:
                issues_to_show = [*result.errors, *result.warnings]
                if verbose:
                    issues_to_show.extend(result.info)
                if issues_to_show:
                    any_issues = True

            if all_passed and not any_issues:
                if show_progress:
                    print(f"✓ {file_path} - PASSED")
                continue

            print(f"\n{file_path}")

            for validator_name, result in validator_results:
                issues_to_show = [*result.errors, *result.warnings]
                if verbose:
                    issues_to_show.extend(result.info)

                if not issues_to_show:
                    if show_progress:
                        print(f"  ✓ {validator_name}: PASSED")
                    continue

                status_icon = "✗" if not result.passed else "⚠"
                print(f"  {status_icon} {validator_name}:")

                for issue in issues_to_show:
                    self._print_issue(issue)

    def summarize(self, total_files: int, passed: int, failed: int, warnings: int) -> None:
        """Display summary statistics in plain text."""
        status = "✓ PASSED" if failed == 0 else "✗ FAILED"

        print("\n" + "=" * 60)
        print(f"{status}")
        print(f"Total files: {total_files}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        if warnings > 0:
            print(f"Warnings: {warnings}")
        print("=" * 60)


class SummaryReporter:
    """Single-line summary reporter for quick status checks."""

    def report(self, file_results: FileResults, verbose: bool = False, *, show_progress: bool = False) -> None:
        """Display nothing (summary-only reporter)."""

    def summarize(self, total_files: int, passed: int, failed: int, warnings: int) -> None:
        """Display single-line summary."""
        if failed == 0:
            status_icon = "✓"
            status = f"{passed}/{total_files} files passed"
        else:
            status_icon = "✗"
            status = f"{failed}/{total_files} files failed"

        if warnings > 0:
            status += f" ({warnings} with warnings)"

        print(f"{status_icon} {status}")
