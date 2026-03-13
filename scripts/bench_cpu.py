"""CPU benchmark tests for skilllint internal YAML parsing logic.

This module is a pytest-compatible benchmark suite that exercises
``skilllint.frontmatter_utils.loads_frontmatter`` with large in-memory
YAML payloads — no disk I/O involved.

Run via pytest::

    uv run pytest scripts/bench_cpu.py -v --no-header

Run directly with output for github-action-benchmark::

    python scripts/bench_cpu.py --output bench/results/bench_cpu_gh.json
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from skilllint.frontmatter_utils import loads_frontmatter

_ITERATIONS = 1000
_TIME_LIMIT_SECONDS = 30.0


def _build_large_yaml_document(num_keys: int = 50, value_length: int = 100) -> str:
    """Build a synthetic YAML frontmatter document entirely in memory.

    Generates a ``---`` delimited frontmatter block followed by a short
    body, with *num_keys* keys whose values are repeated ASCII strings of
    *value_length* characters each.

    Args:
        num_keys: Number of top-level YAML keys to emit.
        value_length: Character length of each scalar value string.

    Returns:
        Complete markdown string with YAML frontmatter (~10 KB for defaults).
    """
    value_template = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_-+="
    repeated_value = (value_template * ((value_length // len(value_template)) + 1))[:value_length]

    lines = ["---"]
    lines.extend(f"key_{i:03d}: {repeated_value}" for i in range(num_keys))
    lines.extend((
        "---",
        "",
        "# Benchmark skill content",
        "",
        "This is the body of the synthetic skill document used for CPU benchmarks.",
    ))
    return "\n".join(lines)


def _run_scenario(num_keys: int, value_length: int, label: str) -> dict[str, float]:
    """Execute one CPU benchmark scenario and return aggregated timing data.

    Runs :func:`skilllint.frontmatter_utils.loads_frontmatter` for
    :data:`_ITERATIONS` iterations on a synthetic YAML document of the
    specified size and measures total and mean elapsed time.

    Args:
        num_keys: Number of top-level YAML keys in the synthetic document.
        value_length: Character length of each scalar value string.
        label: Human-readable scenario label used in printed output.

    Returns:
        Dictionary with keys ``mean_ms`` and ``total_ms``.

    Raises:
        RuntimeError: If ``loads_frontmatter`` returns ``None`` for a
            non-empty document (indicates a parsing failure).
        AssertionError: If the total elapsed time exceeds
            :data:`_TIME_LIMIT_SECONDS`.
    """
    document = _build_large_yaml_document(num_keys=num_keys, value_length=value_length)

    start = time.perf_counter()
    for _ in range(_ITERATIONS):
        post = loads_frontmatter(document)
        # Guard to prevent the loop being optimised away.
        if post is None:
            raise RuntimeError("loads_frontmatter returned None for a non-empty document")
    elapsed = time.perf_counter() - start

    mean_ms = (elapsed / _ITERATIONS) * 1000.0
    total_ms = elapsed * 1000.0

    print(f"\nCPU BENCHMARK [{label}]: {_ITERATIONS} iterations in {total_ms:.3f}ms (mean {mean_ms:.6f} ms/iter)")

    if elapsed >= _TIME_LIMIT_SECONDS:
        raise AssertionError(
            f"CPU benchmark [{label}] exceeded {_TIME_LIMIT_SECONDS}s time limit: {elapsed:.3f}s "
            f"({_ITERATIONS} iterations, mean {mean_ms:.3f} ms/iter)"
        )

    return {"mean_ms": round(mean_ms, 6), "total_ms": round(total_ms, 3)}


def test_cpu_linting_small_yaml() -> None:
    """Benchmark: parse small YAML frontmatter (~1 KB) 1000 times within time limit.

    Constructs a ~1 KB YAML document in memory then calls
    ``loads_frontmatter`` for each iteration, recording total elapsed time.
    Asserts that 1000 iterations complete within the time budget.
    """
    _run_scenario(num_keys=10, value_length=50, label="small")


def test_cpu_linting_large_yaml() -> None:
    """Benchmark: parse medium YAML frontmatter (~10 KB) 1000 times within time limit.

    Constructs a ~10 KB YAML document in memory then calls
    ``loads_frontmatter`` for each iteration, recording total elapsed time.
    Asserts that 1000 iterations complete within the time budget.
    """
    _run_scenario(num_keys=50, value_length=100, label="medium")


def test_cpu_linting_very_large_yaml() -> None:
    """Benchmark: parse large YAML frontmatter (~30 KB) 1000 times within time limit.

    Constructs a ~30 KB YAML document in memory then calls
    ``loads_frontmatter`` for each iteration, recording total elapsed time.
    Asserts that 1000 iterations complete within the time budget.
    """
    _run_scenario(num_keys=100, value_length=200, label="large")


def _build_gh_benchmark_array(
    small: dict[str, float], medium: dict[str, float], large: dict[str, float]
) -> list[dict[str, float | str]]:
    """Build a ``customSmallerIsBetter`` JSON array for github-action-benchmark.

    Args:
        small: Timing dict for the small (~1 KB) scenario.
        medium: Timing dict for the medium (~10 KB) scenario.
        large: Timing dict for the large (~30 KB) scenario.

    Returns:
        List of benchmark entry dicts, each with ``name``, ``value``, and
        ``unit`` keys, suitable for the ``customSmallerIsBetter`` tool format.
    """
    return [
        {"name": "cpu_small_mean_ms", "value": small["mean_ms"], "unit": "ms"},
        {"name": "cpu_medium_mean_ms", "value": medium["mean_ms"], "unit": "ms"},
        {"name": "cpu_large_mean_ms", "value": large["mean_ms"], "unit": "ms"},
        # Legacy entries kept for backward compatibility with existing benchmark history.
        {"name": "cpu_mean_ms", "value": medium["mean_ms"], "unit": "ms"},
        {"name": "cpu_total_ms", "value": medium["total_ms"], "unit": "ms"},
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CPU benchmark for skilllint YAML parsing logic")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write customSmallerIsBetter JSON array to this file path",
    )
    args = parser.parse_args()
    output_path: Path | None = args.output

    small_timing = _run_scenario(num_keys=10, value_length=50, label="small")
    medium_timing = _run_scenario(num_keys=50, value_length=100, label="medium")
    large_timing = _run_scenario(num_keys=100, value_length=200, label="large")

    if output_path is not None:
        gh_array = _build_gh_benchmark_array(small_timing, medium_timing, large_timing)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(gh_array, indent=2), encoding="utf-8")
