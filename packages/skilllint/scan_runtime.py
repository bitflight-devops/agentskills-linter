"""Scan expansion and validation-loop orchestration.

Extracted from ``plugin_validator`` so the CLI entrypoint can delegate
path discovery, filtering, ignore-pattern handling, and the main
validation loop to a dedicated module without changing user-facing behavior.
"""

from __future__ import annotations

import fnmatch
import functools
import json
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

import typer
from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from .reporting import CIReporter, ConsoleReporter, FileResults, Reporter

if TYPE_CHECKING:
    from rich.console import Console

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


class ScanContext(StrEnum):
    """The structural context of a scan target directory."""

    PLUGIN = "plugin"
    PROVIDER = "provider"
    BARE = "bare"


KNOWN_PROVIDER_DIRS: frozenset[str] = frozenset({".claude", ".cursor", ".gemini", ".codex"})

PLUGIN_FILTER_TYPE_MAP: dict[str, str] = {
    "skills": "skills/*/SKILL.md",
    "agents": "agents/*.md",
    "commands": "commands/*.md",
}


# ---------------------------------------------------------------------------
# Plugin manifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PluginManifest:
    """Parsed paths from plugin.json, if declared."""

    plugin_root: Path
    agents: list[str] | None = None
    commands: list[str] | None = None
    skills: list[str] | None = None

    @property
    def is_manifest_driven(self) -> bool:
        """True if plugin.json declares any explicit paths."""
        return any(v is not None for v in (self.agents, self.commands, self.skills))


@functools.cache
def _load_plugin_json(plugin_root: Path) -> dict | None:
    """Load and cache .claude-plugin/plugin.json for a given plugin root.

    Cached per ``plugin_root`` so multiple callers within a single
    ``skilllint check`` run (e.g. path discovery in scan_runtime and
    PA001 cross-checking in pa_series) share a single disk read.

    Args:
        plugin_root: Directory containing ``.claude-plugin/plugin.json``.

    Returns:
        Parsed dict, or None if the file is missing or invalid JSON.
    """
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _parse_plugin_manifest(plugin_root: Path) -> PluginManifest:
    """Read plugin.json and extract declared paths.

    If plugin.json has no path declarations, all fields are None
    (convention-driven mode). Returns all-None manifest on error.

    Args:
        plugin_root: Directory containing .claude-plugin/plugin.json.

    Returns:
        PluginManifest with parsed paths or None fields.
    """
    raw = _load_plugin_json(plugin_root)
    if raw is None:
        return PluginManifest(plugin_root=plugin_root)

    def _extract(key: str) -> list[str] | None:
        value = raw.get(key)
        if isinstance(value, list):
            return value
        return None

    return PluginManifest(
        plugin_root=plugin_root, agents=_extract("agents"), commands=_extract("commands"), skills=_extract("skills")
    )


def _discover_plugin_paths(manifest: PluginManifest) -> list[Path]:
    """Discover validatable files in a plugin directory.

    Two modes based on manifest.is_manifest_driven:
    - Manifest-driven: Resolve exactly the declared paths. No globbing.
    - Convention-driven: Glob at plugin root only (no ** recursion).

    Never recurses into skills/*/agents/ or skills/*/commands/.

    In manifest-driven mode, declared paths are added unconditionally regardless
    of whether they exist on disk. This is intentional: a missing declared file
    is a validation error that downstream validators (e.g. PL001) should flag.
    Convention-driven mode uses glob matching so only existing files appear.

    Args:
        manifest: Parsed plugin manifest with plugin_root and path lists.

    Returns:
        Sorted list of unique paths.
    """
    discovered: set[Path] = set()
    root = manifest.plugin_root

    if manifest.is_manifest_driven:
        # Intentionally no existence check — missing declared paths are a lint error.
        # Skills entries may be directories (e.g. "./skills/my-skill/") or
        # direct SKILL.md paths. Use the path name to distinguish: a path whose
        # final component is "SKILL.md" is a direct file reference; anything else
        # is treated as a skill directory and resolved to its SKILL.md child.
        # This avoids an is_dir() check that would silently drop non-existent dirs.
        if manifest.skills is not None:
            for rel in manifest.skills:
                resolved = root / rel
                if resolved.name == "SKILL.md":
                    discovered.add(resolved)
                else:
                    discovered.add(resolved / "SKILL.md")
        # Agents and commands entries should be direct file paths.
        for path_list in (manifest.agents, manifest.commands):
            if path_list is not None:
                discovered.update(root / rel for rel in path_list)
    else:
        discovered.update(root.glob("agents/*.md"))
        discovered.update(root.glob("commands/*.md"))
        discovered.update(root.glob("skills/*/SKILL.md"))

    discovered.add(root)

    if (root / "hooks" / "hooks.json").exists():
        discovered.add(root / "hooks" / "hooks.json")
    if (root / "CLAUDE.md").exists():
        discovered.add(root / "CLAUDE.md")

    return sorted(discovered)


# ---------------------------------------------------------------------------
# Scan context detection
# ---------------------------------------------------------------------------


def detect_scan_context(directory: Path) -> ScanContext:
    """Identify the scan context of a directory.

    Decision order:
    1. If directory contains .claude-plugin/plugin.json -> PLUGIN
    2. If directory name matches a known provider prefix (.claude, .cursor,
       .gemini, etc.) -> PROVIDER
    3. Otherwise -> BARE

    Plugin check takes precedence over provider check: a .claude/ directory
    that also contains .claude-plugin/plugin.json is classified as PLUGIN.

    Args:
        directory: The target directory to classify.

    Returns:
        ScanContext enum value.
    """
    if (directory / ".claude-plugin" / "plugin.json").exists():
        return ScanContext.PLUGIN
    if directory.name in KNOWN_PROVIDER_DIRS:
        return ScanContext.PROVIDER
    return ScanContext.BARE


def _discover_provider_paths(directory: Path) -> list[Path]:
    """Discover validatable files in a provider directory.

    Uses the provider's known agent location pattern:
        {directory}/agents/**/*.md

    No other files in the provider tree are discovered as agents.

    Args:
        directory: The provider directory (e.g., .claude/).

    Returns:
        Sorted list of unique paths.
    """
    return sorted(set(directory.glob("agents/**/*.md")))


# ---------------------------------------------------------------------------
# Path discovery and filtering
# ---------------------------------------------------------------------------


def _discover_validatable_paths(directory: Path) -> list[Path]:
    """Auto-discover validatable files using context-appropriate rules.

    Detects the scan context of the directory and dispatches to the
    appropriate discovery function:
    - PLUGIN: parse manifest and discover plugin-scoped paths
    - PROVIDER: discover agents/**/*.md only
    - BARE: handle nested plugins and providers, then apply DEFAULT_SCAN_PATTERNS
             for paths not covered by any plugin/provider subtree

    Args:
        directory: The directory to scan.

    Returns:
        Sorted list of unique paths suitable for validation.
    """
    context = detect_scan_context(directory)

    if context == ScanContext.PLUGIN:
        manifest = _parse_plugin_manifest(directory)
        return _discover_plugin_paths(manifest)

    if context == ScanContext.PROVIDER:
        return _discover_provider_paths(directory)

    # BARE context: find nested plugins and providers, then apply DEFAULT_SCAN_PATTERNS
    discovered: set[Path] = set()
    plugin_roots: set[Path] = set()

    # Find nested plugin roots
    for plugin_json in directory.glob("**/.claude-plugin/plugin.json"):
        plugin_root = plugin_json.parent.parent
        plugin_roots.add(plugin_root)
        manifest = _parse_plugin_manifest(plugin_root)
        discovered.update(_discover_plugin_paths(manifest))

    # Find nested provider directories (skip those inside plugin trees)
    provider_roots: set[Path] = set()
    for provider_name in KNOWN_PROVIDER_DIRS:
        for provider_dir in directory.glob(f"**/{provider_name}"):
            if not provider_dir.is_dir():
                continue
            # Plugin takes precedence: skip providers inside plugin trees
            if any(provider_dir.is_relative_to(pr) for pr in plugin_roots):
                continue
            provider_roots.add(provider_dir)
            discovered.update(_discover_provider_paths(provider_dir))

    # Files outside any plugin/provider subtree: use DEFAULT_SCAN_PATTERNS
    covered_roots = plugin_roots | provider_roots

    for pattern in DEFAULT_SCAN_PATTERNS:
        for match in directory.glob(pattern):
            # For plugin.json matches, add the plugin root (grandparent)
            candidate = match.parent.parent if pattern.endswith("plugin.json") else match
            # Only add if not already inside a discovered plugin/provider tree
            if not any(candidate.is_relative_to(root) for root in covered_roots):
                discovered.add(candidate)

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

    if filter_type is not None and filter_type not in FILTER_TYPE_MAP:
        valid = ", ".join(FILTER_TYPE_MAP)
        typer.echo(f"Error: --filter-type must be one of: {valid}", err=True)
        raise typer.Exit(2) from None

    expanded_paths: list[Path] = []
    is_batch = False
    for path in paths:
        if filter_type is not None:
            # Context-aware resolution: plugin dirs use root-only globs to
            # avoid matching skill-internal agent/command files.
            if path.is_dir() and detect_scan_context(path) == ScanContext.PLUGIN:
                resolved_glob: str | None = PLUGIN_FILTER_TYPE_MAP.get(filter_type, FILTER_TYPE_MAP[filter_type])
            else:
                resolved_glob = FILTER_TYPE_MAP[filter_type]
        else:
            resolved_glob = filter_glob
        if resolved_glob is not None and path.is_dir():
            matched = sorted(path.glob(resolved_glob))
            expanded_paths.extend(matched)
            is_batch = True
        elif resolved_glob is None and path.is_dir():
            expanded_paths.extend(_discover_validatable_paths(path))
            is_batch = True
        else:
            expanded_paths.append(path)
    return expanded_paths, is_batch


# ---------------------------------------------------------------------------
# Ignore patterns
# ---------------------------------------------------------------------------


def _build_gitignore_set(paths: Sequence[Path], scan_base: Path | None) -> frozenset[str]:
    """Return the set of absolute path strings that git considers ignored.

    Calls repo.ignored() once for all paths rather than once per file.
    Returns an empty frozenset when no git repo is found or paths is empty.

    Args:
        paths: Paths to test against git's ignore rules.
        scan_base: Directory used to locate the governing git repo. Evaluating
            from the scan base is important when scanning an external directory:
            files inside git worktrees nested under the scan root would otherwise
            resolve to their own repo, bypassing the parent repo's .gitignore rules.

    Returns:
        Frozenset of resolved absolute path strings that git would ignore.
    """
    if not paths or scan_base is None:
        return frozenset()
    anchor = scan_base
    try:
        repo = Repo(anchor, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return frozenset()
    ignored = repo.ignored(*[str(p.resolve()) for p in paths])
    return frozenset(str(Path(p).resolve()) for p in ignored)


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
    resolved_path = path.resolve()
    cwd = Path.cwd().resolve()
    for pattern in patterns:
        if fnmatch.fnmatch(path_str, pattern):
            return True
        # Also match against just the relative-to-cwd representation
        try:
            rel = resolved_path.relative_to(cwd).as_posix()
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
    passed = 0
    failed = 0
    warnings = 0
    for vr_list in all_results.values():
        all_passed = all(r.passed for _, r in vr_list)
        if all_passed:
            passed += 1
            if any(r.warnings for _, r in vr_list):
                warnings += 1
        else:
            failed += 1
    return total_files, passed, failed, warnings


def _compute_scan_base(paths: list[Path]) -> Path | None:
    """Return the common ancestor directory of *paths* for gitignore evaluation.

    Gitignore rules must be evaluated from the perspective of the repo that
    owns the scan root, not from inside each individual file's own repo.  This
    matters when the scan root contains git worktrees: a file inside a worktree
    would otherwise resolve to the worktree's repo and miss the parent repo's
    ``.gitignore`` entries (e.g. ``.claude/worktrees/``).

    Args:
        paths: Expanded list of paths to be scanned.

    Returns:
        The common ancestor path, or None when *paths* is empty.
    """
    if not paths:
        return None
    if len(paths) == 1:
        return paths[0]

    return Path(os.path.commonpath(paths))


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
    record_console: Console | None = None,
    include_gitignore: bool = False,
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
        record_console: When provided, pass this Rich Console to ConsoleReporter
            so its output is captured for export (e.g. SVG/HTML recording).
        include_gitignore: When False (default), paths excluded by git's ignore
            rules are skipped. When True, gitignored paths are included.

    Raises:
        typer.Exit: Always exits with appropriate code.
    """
    ignore_patterns = _load_ignore_patterns()

    scan_base = _compute_scan_base(expanded_paths)

    ignored_set: frozenset[str] = (
        _build_gitignore_set(expanded_paths, scan_base) if not include_gitignore else frozenset()
    )

    def _should_skip(p: Path) -> bool:
        if ignore_patterns and _is_ignored(p, ignore_patterns):
            return True
        return str(p.resolve()) in ignored_set

    all_results: FileResults = {}
    for path in expanded_paths:
        if _should_skip(path):
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

    reporter: Reporter
    if record_console is not None:
        reporter = ConsoleReporter(console=record_console)
    elif no_color:
        reporter = CIReporter()
    else:
        reporter = ConsoleReporter(no_color=no_color)
    reporter.report(all_results, verbose=verbose, show_progress=show_progress)

    total_files, passed, failed, warnings = _compute_summary(all_results)
    if show_summary:
        reporter.summarize(total_files, passed, failed, warnings)

    if failed > 0:
        raise typer.Exit(1) from None
    raise typer.Exit(0) from None
