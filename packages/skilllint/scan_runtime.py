"""Scan expansion and validation-loop orchestration.

Extracted from ``plugin_validator`` so the CLI entrypoint can delegate
path discovery, filtering, ignore-pattern handling, and the main
validation loop to a dedicated module without changing user-facing behavior.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn

import typer

from .reporting import CIReporter, ConsoleReporter, FileResults, Reporter

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FILTER_TYPE_MAP: dict[str, str] = {
    "skills": "**/skills/*/SKILL.md",
    "agents": "**/agents/*.md",
    "commands": "**/commands/*.md",
}

# Default patterns for auto-discovering validatable files in bare directories
DEFAULT_SCAN_PATTERNS: tuple[str, ...] = (
    "**/skills/*/SKILL.md",
    "**/agents/*.md",
    "**/commands/*.md",
    "**/.claude-plugin/plugin.json",
    "**/hooks/hooks.json",
    "**/CLAUDE.md",
)


# ---------------------------------------------------------------------------
# Path discovery and filtering
# ---------------------------------------------------------------------------


def _discover_validatable_paths(directory: Path) -> list[Path]:
    """Auto-discover validatable files in a bare directory.

    Globs ``DEFAULT_SCAN_PATTERNS`` against *directory* and returns
    deduplicated, sorted paths.  For any ``.claude-plugin/plugin.json``
    match the **plugin root directory** (grandparent of plugin.json) is
    returned instead of the file itself, because ``detect_file_type``
    recognises directories that contain ``.claude-plugin/plugin.json``.

    Args:
        directory: The directory to scan.

    Returns:
        Sorted list of unique paths suitable for validation.
    """
    discovered: set[Path] = set()
    for pattern in DEFAULT_SCAN_PATTERNS:
        for match in directory.glob(pattern):
            if match.name == "plugin.json":
                discovered.add(match.parent.parent)
            else:
                discovered.add(match)
    return sorted(discovered)


def _resolve_filter_and_expand_paths(
    paths: list[Path], filter_glob: str | None, filter_type: str | None
) -> tuple[list[Path], bool]:
    """Resolve filter options and expand directory paths.

    Validates mutual exclusion of --filter and --filter-type, resolves
    filter_type to glob pattern, and expands directories.

    Returns:
        Tuple of (expanded_paths, is_batch).

    Raises:
        typer.Exit: On invalid filter options.
    """
    if filter_glob is not None and filter_type is not None:
        typer.echo("Error: --filter and --filter-type are mutually exclusive", err=True)
        raise typer.Exit(2) from None

    resolved_glob: str | None = filter_glob
    if filter_type is not None:
        if filter_type not in FILTER_TYPE_MAP:
            valid = ", ".join(FILTER_TYPE_MAP)
            typer.echo(f"Error: --filter-type must be one of: {valid}", err=True)
            raise typer.Exit(2) from None
        resolved_glob = FILTER_TYPE_MAP[filter_type]

    expanded_paths: list[Path] = []
    is_batch = False
    for path in paths:
        if resolved_glob is not None and path.is_dir():
            matched = sorted(path.glob(resolved_glob))
            expanded_paths.extend(matched)
            is_batch = True
        elif resolved_glob is None and path.is_dir():
            if (path / ".claude-plugin/plugin.json").exists():
                expanded_paths.append(path)
                # Also validate SKILL.md files (InternalLinkValidator, etc.)
                expanded_paths.extend(sorted(path.glob("**/skills/*/SKILL.md")))
            else:
                expanded_paths.extend(_discover_validatable_paths(path))
                is_batch = True
        else:
            expanded_paths.append(path)
    return expanded_paths, is_batch


# ---------------------------------------------------------------------------
# Ignore patterns
# ---------------------------------------------------------------------------


def _load_ignore_patterns() -> list[str]:
    """Load glob patterns from .pluginvalidatorignore file.

    Searches for the ignore file in the following order:
    1. Current working directory (.pluginvalidatorignore)
    2. .claude/.pluginvalidatorignore

    Each line is a gitignore-style glob pattern. Lines starting with '#' are
    comments, blank lines are ignored.

    Returns:
        List of glob patterns to match against file paths.
    """
    candidates = [Path.cwd() / ".pluginvalidatorignore", Path.cwd() / ".claude" / ".pluginvalidatorignore"]
    for candidate in candidates:
        if candidate.is_file():
            lines = candidate.read_text(encoding="utf-8").splitlines()
            return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    return []


def _is_ignored(path: Path, patterns: list[str]) -> bool:
    """Check whether a path matches any ignore pattern.

    Patterns follow gitignore-style glob semantics:
    - ``**/templates/*.md`` matches any ``templates`` directory at any depth
    - ``plugins/foo/bar.md`` matches that exact relative path

    The path is tested as a POSIX string (forward slashes) so patterns work
    consistently across platforms.

    Args:
        path: File path to check (absolute or relative).
        patterns: Glob patterns loaded from .pluginvalidatorignore.

    Returns:
        True if the path matches any pattern and should be skipped.
    """
    path_str = path.as_posix()
    for pattern in patterns:
        if fnmatch.fnmatch(path_str, pattern):
            return True
        # Also match against just the relative-to-cwd representation
        try:
            rel = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            rel = path_str
        if fnmatch.fnmatch(rel, pattern):
            return True
    return False


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------


def _compute_summary(all_results: FileResults) -> tuple[int, int, int, int]:
    """Compute validation summary statistics from file results.

    Returns:
        Tuple of (total_files, passed, failed, warnings).
    """
    total_files = len(all_results)
    passed = sum(1 for vr_list in all_results.values() if all(r.passed for _, r in vr_list))
    failed = sum(1 for vr_list in all_results.values() if any(not r.passed for _, r in vr_list))
    warnings = sum(
        1
        for vr_list in all_results.values()
        if all(r.passed for _, r in vr_list) and any(r.warnings for _, r in vr_list)
    )
    return total_files, passed, failed, warnings


# ---------------------------------------------------------------------------
# Validation loop
# ---------------------------------------------------------------------------

# Callback type aliases for dependency injection from plugin_validator.
# This avoids circular imports: plugin_validator imports scan_runtime,
# and passes its own functions as callbacks when calling run_validation_loop.
ValidateSinglePathFn = Callable[..., "FileResults"]
ValidateFileFn = Callable[[Path, dict[str, object], str | None], list[dict]]
ViolationsToResultFn = Callable[[list[dict]], Any]


def run_validation_loop(
    *,
    expanded_paths: list[Path],
    check: bool,
    fix: bool,
    verbose: bool,
    no_color: bool,
    show_progress: bool,
    show_summary: bool,
    platform_override: str | None,
    validate_single_path: ValidateSinglePathFn,
    validate_file: ValidateFileFn,
    violations_to_result: ViolationsToResultFn,
    adapters: dict[str, object],
) -> NoReturn:
    """Execute the validation loop, report results, and exit.

    Dependencies from ``plugin_validator`` are injected as callbacks to
    avoid circular imports at module level.

    Args:
        expanded_paths: Resolved file paths to validate.
        check: Validate only, don't auto-fix.
        fix: Auto-fix issues where possible.
        verbose: Show detailed output.
        no_color: Disable color output.
        show_progress: Show per-file status.
        show_summary: Show summary panel.
        platform_override: Restrict to this adapter ID.
        validate_single_path: Callback to validate a single path.
        validate_file: Callback to validate a file with platform adapters.
        violations_to_result: Callback to convert violations to ValidationResult.
        adapters: Platform adapter registry dict.

    Raises:
        typer.Exit: Always exits with appropriate code.
    """
    ignore_patterns = _load_ignore_patterns()
    all_results: FileResults = {}
    for path in expanded_paths:
        if ignore_patterns and _is_ignored(path, ignore_patterns):
            continue
        if platform_override is not None:
            violations = validate_file(path, adapters, platform_override)
            all_results[path] = [("platform", violations_to_result(violations))]
        else:
            file_results = validate_single_path(path, check=check, fix=fix, verbose=verbose)
            for file_path, validator_results in file_results.items():
                if file_path in all_results:
                    all_results[file_path].extend(validator_results)
                else:
                    all_results[file_path] = list(validator_results)

    reporter: Reporter = CIReporter() if no_color else ConsoleReporter(no_color=no_color)
    reporter.report(all_results, verbose=verbose, show_progress=show_progress)

    total_files, passed, failed, warnings = _compute_summary(all_results)
    if show_summary:
        reporter.summarize(total_files, passed, failed, warnings)

    if failed > 0:
        raise typer.Exit(1) from None
    raise typer.Exit(0) from None
