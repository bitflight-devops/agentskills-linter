#!/usr/bin/env python3
r"""Generate a markdown PR comment comparing benchmark results across multiple scenarios.

Reads github-action-benchmark JSON files for each named scenario and writes a
markdown comment showing per-scenario tables with before/after values, change
percentage, and pass/fail indicators based on a configurable regression threshold.

Usage::

    python scripts/bench_comment.py \\
      --scenario scan-clean:scripts/results/bench_io_clean_gh.json:scripts/results/bench_io_clean_base_gh.json \\
      --scenario scan-violations:scripts/results/bench_io_violations_gh.json:scripts/results/bench_io_violations_base_gh.json \\
      --scenario fix-violations:scripts/results/bench_io_fix_gh.json:scripts/results/bench_io_fix_base_gh.json \\
      --scenario cpu:scripts/results/bench_cpu_gh.json:scripts/results/bench_cpu_base_gh.json \\
      --output /tmp/bench_comment.md \\
      --threshold 1.30 \\
      --pages-url https://bitflight-devops.github.io/skilllint/
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import UTC, datetime

# Metrics where smaller is better (timing metrics).
_SMALLER_IS_BETTER: frozenset[str] = frozenset({
    "scan_min_ms",
    "scan_mean_ms",
    "scan_max_ms",
    "fix_min_ms",
    "fix_mean_ms",
    "fix_max_ms",
    "cpu_clean_mean_ms",
    "cpu_violations_mean_ms",
    "cpu_fix_mean_ms",
})

# Hidden marker so sticky-pull-request-comment can find and update the comment.
_MARKER = "<!-- benchmark-results -->"

# Number of colon-separated parts in a --scenario argument: NAME:COMPARE_PATH:BASE_PATH
_SCENARIO_PARTS = 3


def load_entries(path: pathlib.Path, label: str) -> list[dict[str, object]]:
    """Load github-action-benchmark JSON array from *path*.

    Args:
        path: Path to the JSON file.
        label: Human-readable label used in warning messages.

    Returns:
        List of ``{name, value, unit}`` dicts.  Empty list if file is missing
        or unreadable — treated as a soft skip rather than a hard error.
    """
    if not path.exists():
        print(f"Warning: {label} file not found: {path}", file=sys.stderr)
        return []
    try:
        text = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Warning: could not read {label} file {path}: {exc}", file=sys.stderr)
        return []
    if not text:
        print(f"Warning: {label} file is empty: {path}", file=sys.stderr)
        return []
    try:
        data = json.loads(text)
    except ValueError as exc:
        print(f"Warning: could not parse {label} file {path}: {exc}", file=sys.stderr)
        return []
    if isinstance(data, list):
        return data
    # Single-dict fallback (shouldn't happen with bench output).
    return [data]


def build_index(entries: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    """Index benchmark entries by metric name.

    Args:
        entries: List of ``{name, value, unit}`` dicts.

    Returns:
        Dict mapping metric name to entry dict.
    """
    return {str(e["name"]): e for e in entries}


def fmt_value(value: float, unit: str) -> str:
    """Format a benchmark value with its unit for display.

    Args:
        value: Numeric metric value.
        unit: Unit string (e.g. ``"ms"`` or ``"files/s"``).

    Returns:
        Formatted string like ``"430.1 ms"`` or ``"12.3 files/s"``.
    """
    return f"{value:.1f} {unit}"


def change_cell(name: str, base_val: float, cmp_val: float, threshold: float) -> str:
    """Build the markdown change cell for a single metric row.

    Args:
        name: Metric name, used to determine if smaller-is-better.
        base_val: Baseline measurement value.
        cmp_val: Compare (PR head) measurement value.
        threshold: Regression threshold as a multiplier (e.g. 1.30 = 130%).

    Returns:
        Markdown string with emoji indicator and percentage change.
    """
    if base_val == 0:
        return "—"

    ratio = cmp_val / base_val
    pct = (ratio - 1.0) * 100.0

    if name in _SMALLER_IS_BETTER:
        regressed = ratio > threshold
        improved = ratio < 1.0
    else:
        # larger-is-better (e.g. files_per_second)
        regressed = ratio < (1.0 / threshold)
        improved = ratio > 1.0

    if regressed:
        icon = "🔴"
    elif improved:
        icon = "✅"
    else:
        icon = "➡️"

    sign = "+" if pct >= 0 else ""
    return f"{icon} {sign}{pct:.1f}%"


def render_scenario_table(
    scenario_name: str,
    compare_entries: list[dict[str, object]],
    base_entries: list[dict[str, object]],
    threshold: float,
) -> tuple[str, bool]:
    """Render a markdown table section for one benchmark scenario.

    Args:
        scenario_name: Display name for this scenario (used as heading).
        compare_entries: github-action-benchmark entries for the PR head ref.
        base_entries: github-action-benchmark entries for the base ref.
        threshold: Regression threshold multiplier (e.g. 1.30 = 130%).

    Returns:
        Tuple of (markdown_section_string, has_regression_bool).
    """
    cmp_idx = build_index(compare_entries)
    base_idx = build_index(base_entries)

    rows: list[str] = []
    has_regression = False

    for name in sorted(set(cmp_idx) | set(base_idx)):
        cmp_entry = cmp_idx.get(name)
        base_entry = base_idx.get(name)

        cmp_val = float(cmp_entry["value"]) if cmp_entry else None  # type: ignore[arg-type]
        base_val = float(base_entry["value"]) if base_entry else None  # type: ignore[arg-type]
        unit = str(cmp_entry["unit"] if cmp_entry else (base_entry["unit"] if base_entry else ""))

        base_str = fmt_value(base_val, unit) if base_val is not None else "—"
        cmp_str = fmt_value(cmp_val, unit) if cmp_val is not None else "—"

        if base_val is not None and cmp_val is not None:
            change = change_cell(name, base_val, cmp_val, threshold)
            if "🔴" in change:
                has_regression = True
        else:
            change = "—"

        rows.append(f"| `{name}` | {base_str} | {cmp_str} | {change} |")

    table_body = "\n".join(rows)
    section = (
        f"### {scenario_name}\n\n"
        "| Metric | Base | Compare | Change |\n"
        "|--------|------|---------|--------|\n"
        f"{table_body}"
    )
    return section, has_regression


def parse_scenario_arg(raw: str) -> tuple[str, pathlib.Path, pathlib.Path]:
    """Parse a ``NAME:COMPARE_PATH:BASE_PATH`` scenario argument.

    Args:
        raw: Colon-separated string in ``NAME:COMPARE_PATH:BASE_PATH`` format.

    Returns:
        Tuple of (name, compare_path, base_path).

    Raises:
        argparse.ArgumentTypeError: If the string does not have exactly 3
            colon-separated parts.
    """
    parts = raw.split(":", 2)
    if len(parts) != _SCENARIO_PARTS:
        raise argparse.ArgumentTypeError(f"--scenario must be NAME:COMPARE_PATH:BASE_PATH, got: {raw!r}")
    name, compare_raw, base_raw = parts
    return name, pathlib.Path(compare_raw), pathlib.Path(base_raw)


def render_markdown(scenarios: list[tuple[str, pathlib.Path, pathlib.Path]], threshold: float, pages_url: str) -> str:
    """Render the full benchmark PR comment as markdown.

    Scenarios where both compare and base files are missing are silently
    skipped.

    Args:
        scenarios: List of ``(name, compare_path, base_path)`` tuples.
        threshold: Regression threshold multiplier (e.g. 1.30 = 130%).
        pages_url: URL to the GitHub Pages benchmark history chart.

    Returns:
        Complete markdown string for the PR comment.
    """
    threshold_pct = int((threshold - 1.0) * 100)
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")

    sections: list[str] = []
    any_regression = False

    for name, compare_path, base_path in scenarios:
        compare_entries = load_entries(compare_path, f"{name} compare")
        base_entries = load_entries(base_path, f"{name} base")

        # Soft skip: both files missing.
        if not compare_entries and not base_entries:
            continue

        section, has_regression = render_scenario_table(
            scenario_name=name, compare_entries=compare_entries, base_entries=base_entries, threshold=threshold
        )
        sections.append(section)
        if has_regression:
            any_regression = True

    if not sections:
        return f"{_MARKER}\n## Benchmark Results\n\n_No benchmark data available._\n\n<sub>Updated {now}</sub>\n"

    status = "🔴 **Regression detected**" if any_regression else "✅ **No regressions**"
    history_link = f"[View benchmark history]({pages_url})" if pages_url else ""

    sections_text = "\n\n".join(sections)

    return (
        f"{_MARKER}\n"
        "## Benchmark Results\n\n"
        f"{status} — threshold: {threshold_pct}%\n\n"
        f"{sections_text}\n\n"
        f"{history_link}\n\n"
        f"<sub>Updated {now}</sub>\n"
    )


def main() -> None:
    """Parse CLI arguments, generate multi-scenario markdown, write to output file."""
    parser = argparse.ArgumentParser(
        description="Generate a markdown PR comment comparing benchmark results across scenarios."
    )
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        default=[],
        metavar="NAME:COMPARE_PATH:BASE_PATH",
        help=(
            "Benchmark scenario in NAME:COMPARE_PATH:BASE_PATH format. "
            "Repeatable. Scenarios where both files are missing are skipped."
        ),
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        required=True,
        metavar="PATH",
        help="Path to write the generated markdown comment.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=1.30,
        metavar="MULTIPLIER",
        help="Regression threshold multiplier (default: 1.30 = 130%%).",
    )
    parser.add_argument(
        "--pages-url",
        type=str,
        default="",
        metavar="URL",
        help="GitHub Pages URL for benchmark history (included in comment).",
    )
    args = parser.parse_args()

    if not args.scenarios:
        print("Error: at least one --scenario argument is required.", file=sys.stderr)
        sys.exit(2)

    parsed_scenarios: list[tuple[str, pathlib.Path, pathlib.Path]] = []
    for raw in args.scenarios:
        try:
            parsed_scenarios.append(parse_scenario_arg(raw))
        except argparse.ArgumentTypeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(2)

    markdown = render_markdown(scenarios=parsed_scenarios, threshold=args.threshold, pages_url=args.pages_url)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(f"Written benchmark comment to {args.output}")


if __name__ == "__main__":
    main()
