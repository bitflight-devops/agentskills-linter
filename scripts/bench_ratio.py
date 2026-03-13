#!/usr/bin/env python3
"""Compute and print the performance ratio between two benchmark result files.

Reads two JSON benchmark result files (compare and base), extracts duration
values, and prints a human-readable ratio showing how much faster or slower
the compare ref is relative to the base ref.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


def extract_duration(data: list[dict[str, object]] | dict[str, object], label: str) -> float | None:
    """Extract duration in seconds from a benchmark result payload.

    Supports two formats:

    1. **github-action-benchmark array** (written by ``bench_io.py --output``):
       a list of ``{name, value, unit}`` dicts.  Looks for an entry whose
       ``name`` ends with ``_mean_ms`` and converts its ``value`` from ms to s.

    2. **Raw dict** (written by ``bench_io.py`` to stdout):
       a single dict with keys like ``scan_mean_ms`` or ``fix_mean_ms``.
       Also accepts a bare ``mean_ms`` key for forward-compatibility.

    Args:
        data: Parsed JSON benchmark result — either a list of dicts or a single dict.
        label: Human-readable name used in error messages (e.g. ``"compare"``).

    Returns:
        Duration in seconds, or ``None`` if the required key is missing.
    """
    if isinstance(data, list):
        # github-action-benchmark array: [{name, value, unit}, ...]
        for entry in data:
            name = str(entry.get("name", ""))
            if name.endswith("_mean_ms"):
                return float(entry["value"]) / 1000.0  # type: ignore[arg-type]
        print(f"{label} data missing an entry with a name ending in '_mean_ms'", file=sys.stderr)
        return None

    # Raw dict output from run_benchmark()
    for key in ("scan_mean_ms", "fix_mean_ms", "mean_ms"):
        if key in data:
            return float(data[key]) / 1000.0  # type: ignore[arg-type]

    print(f"{label} data missing scan_mean_ms, fix_mean_ms, or mean_ms", file=sys.stderr)
    return None


def compute_ratio(compare_path: pathlib.Path, base_path: pathlib.Path) -> None:
    """Read result files, compute the performance ratio, and print the result.

    Exits with code 0 in all cases — missing or empty files are treated as
    soft skips rather than hard errors so the CI step remains non-blocking.

    Args:
        compare_path: Path to the JSON result file for the compare (PR) ref.
        base_path: Path to the JSON result file for the base ref.
    """
    if not compare_path.exists() or not base_path.exists():
        print("Skipping ratio computation: result files not found.")
        sys.exit(0)

    compare_text = compare_path.read_text(encoding="utf-8").strip()
    base_text = base_path.read_text(encoding="utf-8").strip()

    if not compare_text or not base_text:
        print("Skipping ratio computation: one or both result files are empty.")
        sys.exit(0)

    compare_data: list[dict[str, object]] | dict[str, object] = json.loads(compare_text)
    base_data: list[dict[str, object]] | dict[str, object] = json.loads(base_text)

    compare_duration = extract_duration(compare_data, "compare")
    base_duration = extract_duration(base_data, "base")

    if compare_duration is None or base_duration is None:
        sys.exit(0)

    if base_duration > 0 and compare_duration > 0:
        ratio = compare_duration / base_duration
        change_pct = (ratio - 1.0) * 100.0
        direction = "slower" if ratio > 1.0 else "faster"
        print(
            f"BENCHMARK RATIO: compare={compare_duration:.2f}s  "
            f"base={base_duration:.2f}s  "
            f"ratio={ratio:.3f}x ({abs(change_pct):.1f}% {direction})"
        )
    else:
        print("Could not compute ratio: one or both durations are zero.")


def main() -> None:
    """Parse CLI arguments and run the ratio computation.

    Args are read from the command line:
        --compare: path to the compare (PR head) benchmark result JSON.
        --base: path to the base benchmark result JSON.
    """
    parser = argparse.ArgumentParser(
        description="Compute and print the performance ratio between two benchmark result files."
    )
    parser.add_argument(
        "--compare",
        type=pathlib.Path,
        required=True,
        metavar="PATH",
        help="Path to the compare (PR head) benchmark result JSON file.",
    )
    parser.add_argument(
        "--base", type=pathlib.Path, required=True, metavar="PATH", help="Path to the base benchmark result JSON file."
    )
    args = parser.parse_args()
    compute_ratio(args.compare, args.base)


if __name__ == "__main__":
    main()
