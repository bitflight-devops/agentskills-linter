"""I/O benchmark script for the skilllint CLI.

Runs ``skilllint`` via subprocess against an extracted plugin directory,
repeats the measurement three times, and emits a JSON summary to stdout.

Usage::

    python bench/bench_io.py <plugin_dir>
    python bench/bench_io.py <plugin_dir> --output path/to/output.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _count_files(directory: Path) -> int:
    """Count all files beneath *directory* recursively.

    Args:
        directory: Root directory to walk.

    Returns:
        Total number of files found.
    """
    count = 0
    for _root, _dirs, files in os.walk(directory):
        count += len(files)
    return count


def _run_once(plugin_dir: Path) -> float:
    """Run ``skilllint`` against *plugin_dir* and return wall-clock seconds.

    Args:
        plugin_dir: Path to the extracted plugin directory.

    Returns:
        Elapsed wall-clock time in seconds.

    Raises:
        FileNotFoundError: If the ``skilllint`` executable cannot be located on PATH.
        subprocess.CalledProcessError: If skilllint exits with a non-zero code
            that is not an expected lint-result code (1 = lint errors found).
    """
    skilllint_exe = shutil.which("skilllint")
    if skilllint_exe is None:
        raise FileNotFoundError("'skilllint' executable not found on PATH")
    start = time.perf_counter()
    result = subprocess.run([skilllint_exe, str(plugin_dir)], capture_output=True, text=True, check=False)
    elapsed = time.perf_counter() - start
    # skilllint exits 0 (clean) or 1 (lint errors found) — both are valid.
    # Any other exit code is an unexpected failure.
    if result.returncode not in {0, 1}:
        raise subprocess.CalledProcessError(result.returncode, "skilllint", result.stdout, result.stderr)
    return elapsed


def run_benchmark(plugin_dir: Path, runs: int = 3) -> dict[str, float | int]:
    """Run the I/O benchmark and return aggregated timing data.

    Args:
        plugin_dir: Path to the extracted plugin directory to lint.
        runs: Number of measurement repetitions.

    Returns:
        Dictionary with keys ``min_ms``, ``mean_ms``, ``max_ms``,
        ``runs``, and ``file_count``.
    """
    timings: list[float] = []
    for _ in range(runs):
        elapsed = _run_once(plugin_dir)
        timings.append(elapsed * 1000.0)

    file_count = _count_files(plugin_dir)

    return {
        "min_ms": round(min(timings), 3),
        "mean_ms": round(sum(timings) / len(timings), 3),
        "max_ms": round(max(timings), 3),
        "runs": runs,
        "file_count": file_count,
    }


def build_gh_benchmark_array(result: dict[str, float | int]) -> list[dict[str, float | str]]:
    """Build a ``customSmallerIsBetter`` JSON array for github-action-benchmark.

    Args:
        result: Aggregated timing data returned by :func:`run_benchmark`.

    Returns:
        List of benchmark entry dicts, each with ``name``, ``value``, and
        ``unit`` keys, suitable for the ``customSmallerIsBetter`` tool format.
    """
    min_ms = float(result["min_ms"])
    mean_ms = float(result["mean_ms"])
    max_ms = float(result["max_ms"])
    file_count = int(result["file_count"])
    skills_per_sec = file_count / (mean_ms / 1000.0) if mean_ms > 0 else 0.0

    return [
        {"name": "scan_min_ms", "value": round(min_ms, 3), "unit": "ms"},
        {"name": "scan_mean_ms", "value": round(mean_ms, 3), "unit": "ms"},
        {"name": "scan_max_ms", "value": round(max_ms, 3), "unit": "ms"},
        {"name": "skills_per_second", "value": round(skills_per_sec, 3), "unit": "skills/s"},
    ]


def main() -> None:
    """Entry point: parse CLI args, run benchmark, print JSON to stdout.

    When ``--output`` is provided, also write the ``customSmallerIsBetter``
    JSON array to the given file path.

    Raises:
        SystemExit: With code 2 if the plugin_dir argument is missing or
            the path does not exist.
    """
    parser = argparse.ArgumentParser(description="I/O benchmark for the skilllint CLI")
    parser.add_argument("plugin_dir", type=Path, help="Path to the extracted plugin directory")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write customSmallerIsBetter JSON array to this file path",
    )
    args = parser.parse_args()

    plugin_dir: Path = args.plugin_dir
    output_path: Path | None = args.output

    if not plugin_dir.is_dir():
        print(f"Error: '{plugin_dir}' is not a directory", file=sys.stderr)
        sys.exit(2)

    result = run_benchmark(plugin_dir)
    print(json.dumps(result, indent=2))

    if output_path is not None:
        gh_array = build_gh_benchmark_array(result)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(gh_array, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
