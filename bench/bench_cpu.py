"""CPU benchmark tests for skilllint internal YAML parsing logic.

This module is a pytest-compatible benchmark suite that exercises
``skilllint.frontmatter_utils.loads_frontmatter`` with large in-memory
YAML payloads — no disk I/O involved.

Run via::

    uv run pytest bench/bench_cpu.py -v --no-header
"""

from __future__ import annotations

import time

from skilllint.frontmatter_utils import loads_frontmatter

_ITERATIONS = 1000
_TIME_LIMIT_SECONDS = 10.0


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


def test_cpu_linting_large_yaml() -> None:
    """Benchmark: parse large YAML frontmatter 1000 times within 10 seconds.

    Constructs a ~10 KB YAML document in memory then calls
    ``loads_frontmatter`` for each iteration, recording total elapsed time.
    Asserts that 1000 iterations complete within the time budget.
    """
    document = _build_large_yaml_document(num_keys=50, value_length=100)

    start = time.perf_counter()
    for _ in range(_ITERATIONS):
        post = loads_frontmatter(document)
        # Guard to prevent the loop being optimised away.
        if post is None:
            raise RuntimeError("loads_frontmatter returned None for a non-empty document")
    elapsed = time.perf_counter() - start

    mean_ms = (elapsed / _ITERATIONS) * 1000.0

    print(f"\nCPU BENCHMARK: {_ITERATIONS} iterations in {elapsed:.3f}s (mean {mean_ms:.3f} ms/iter)")

    if elapsed >= _TIME_LIMIT_SECONDS:
        raise AssertionError(
            f"CPU benchmark exceeded {_TIME_LIMIT_SECONDS}s time limit: {elapsed:.3f}s "
            f"({_ITERATIONS} iterations, mean {mean_ms:.3f} ms/iter)"
        )
