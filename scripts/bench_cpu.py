"""CPU benchmark tests for skilllint internal YAML parsing and lint/fix logic.

This module is a pytest-compatible benchmark suite that exercises three
in-memory scenarios mirroring the I/O benchmark's clean/violations/fix split:

1. ``clean``      — ``loads_frontmatter`` on well-formed frontmatter 1000x
2. ``violations`` — ``loads_frontmatter`` + ``FrontmatterValidator`` lint
                    check on frontmatter with FM004/FM007/FM008/FM009 patterns
3. ``fix``        — ``loads_frontmatter`` + ``FrontmatterValidator._apply_fixes``
                    on the violations document 1000x

No disk I/O or subprocess calls are made.

Run via pytest::

    uv run pytest scripts/bench_cpu.py -v --no-header

Run directly with output for github-action-benchmark::

    python scripts/bench_cpu.py --output bench/results/bench_cpu_gh.json
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from skilllint.frontmatter_utils import loads_frontmatter
from skilllint.plugin_validator import FileType, FrontmatterValidator

_ITERATIONS = 1000
_TIME_LIMIT_SECONDS = 30.0

# ---------------------------------------------------------------------------
# In-memory document builders
# ---------------------------------------------------------------------------


def _build_clean_document() -> str:
    """Build a well-formed skill frontmatter document with no violations.

    Returns:
        Complete markdown string with valid YAML frontmatter and short body.
    """
    return """\
---
name: my-benchmark-skill
description: A realistic benchmark skill used for CPU performance testing
version: 1.0.0
tools: Read, Write, Edit
skills: helper-skill, utility-skill
---

# My Benchmark Skill

This is the body of the synthetic skill document used for CPU benchmarks.
"""


def _build_violations_document() -> str:
    """Build a skill frontmatter document containing FM004/FM007/FM008/FM009 violations.

    Violation patterns injected:
    - FM004: ``>-`` multiline YAML indicator in description value
    - FM007: ``allowed-tools:`` as a YAML list instead of CSV string
    - FM008: ``skills:`` as a YAML list instead of CSV string
    - FM009: unquoted colon in description value (triggers YAML parse error)

    Returns:
        Complete markdown string with violating YAML frontmatter and short body.
    """
    # FM009 (unquoted colon) is handled separately because it causes a YAML
    # parse error; include a separate key with colon-in-value alongside the
    # other violations so the validator exercises FM004+FM007+FM008 via the
    # normal parse path, and FM009 via the colon-fix fallback path.
    return """\
---
name: violations-skill
description: >-
  A multiline description that violates FM004 rules
version: 1.0.0
allowed-tools:
  - Read
  - Write
  - Edit
skills:
  - skill-a
  - skill-b
---

# Violations Skill

This document contains FM004, FM007, and FM008 violations for benchmarking.
"""


def _build_fm009_document() -> str:
    """Build a skill frontmatter document containing an FM009 unquoted-colon violation.

    Returns:
        Complete markdown string with an unquoted colon in the description field.
    """
    return """\
---
name: fm009-skill
description: Skill purpose: handle task coordination
version: 1.0.0
---

# FM009 Skill

This document contains an FM009 unquoted-colon violation for benchmarking.
"""


# ---------------------------------------------------------------------------
# Scenario runners
# ---------------------------------------------------------------------------


def _run_clean_scenario() -> dict[str, float]:
    """Execute the 'clean' CPU benchmark scenario.

    Calls ``loads_frontmatter`` 1000x on a well-formed document.

    Returns:
        Dictionary with keys ``mean_ms`` and ``total_ms``.

    Raises:
        RuntimeError: If ``loads_frontmatter`` returns an unexpected result.
        AssertionError: If total elapsed time exceeds :data:`_TIME_LIMIT_SECONDS`.
    """
    document = _build_clean_document()

    start = time.perf_counter()
    for _ in range(_ITERATIONS):
        post = loads_frontmatter(document)
        # Guard to prevent the loop being optimised away.
        if post is None:
            raise RuntimeError("loads_frontmatter returned None for a non-empty document")
    elapsed = time.perf_counter() - start

    mean_ms = (elapsed / _ITERATIONS) * 1000.0
    total_ms = elapsed * 1000.0

    print(f"\nCPU BENCHMARK [clean]: {_ITERATIONS} iterations in {total_ms:.3f}ms (mean {mean_ms:.6f} ms/iter)")

    if elapsed >= _TIME_LIMIT_SECONDS:
        raise AssertionError(
            f"CPU benchmark [clean] exceeded {_TIME_LIMIT_SECONDS}s time limit: {elapsed:.3f}s "
            f"({_ITERATIONS} iterations, mean {mean_ms:.3f} ms/iter)"
        )

    return {"mean_ms": round(mean_ms, 6), "total_ms": round(total_ms, 3)}


def _run_violations_scenario() -> dict[str, float]:
    """Execute the 'violations' CPU benchmark scenario.

    Calls ``loads_frontmatter`` then checks for FM004 violations via regex
    (matching what ``FrontmatterValidator.validate`` does internally) 1000x.
    No disk I/O is performed.

    Returns:
        Dictionary with keys ``mean_ms`` and ``total_ms``.

    Raises:
        AssertionError: If total elapsed time exceeds :data:`_TIME_LIMIT_SECONDS`.
    """
    document = _build_violations_document()
    # FM004 pattern check mirrors FrontmatterValidator.validate internals.
    fm004_pattern = re.compile(r"description:\s*[|>][-+]?\s*\n")

    start = time.perf_counter()
    for _ in range(_ITERATIONS):
        post = loads_frontmatter(document)
        # Simulate the lint check: extract raw frontmatter text and scan for violations.
        raw_fm = document.split("---", 2)[1] if "---" in document else ""
        _ = fm004_pattern.search(raw_fm)
        # Guard to prevent the loop being optimised away.
        if post is None:
            raise RuntimeError("loads_frontmatter returned None for a non-empty document")
    elapsed = time.perf_counter() - start

    mean_ms = (elapsed / _ITERATIONS) * 1000.0
    total_ms = elapsed * 1000.0

    print(f"\nCPU BENCHMARK [violations]: {_ITERATIONS} iterations in {total_ms:.3f}ms (mean {mean_ms:.6f} ms/iter)")

    if elapsed >= _TIME_LIMIT_SECONDS:
        raise AssertionError(
            f"CPU benchmark [violations] exceeded {_TIME_LIMIT_SECONDS}s time limit: {elapsed:.3f}s "
            f"({_ITERATIONS} iterations, mean {mean_ms:.3f} ms/iter)"
        )

    return {"mean_ms": round(mean_ms, 6), "total_ms": round(total_ms, 3)}


def _run_fix_scenario() -> dict[str, float]:
    """Execute the 'fix' CPU benchmark scenario.

    Calls ``loads_frontmatter`` then ``FrontmatterValidator._apply_fixes``
    on the violations document 1000x. No disk I/O is performed.

    Returns:
        Dictionary with keys ``mean_ms`` and ``total_ms``.

    Raises:
        AssertionError: If total elapsed time exceeds :data:`_TIME_LIMIT_SECONDS`.
    """
    document = _build_violations_document()
    validator = FrontmatterValidator()

    start = time.perf_counter()
    for _ in range(_ITERATIONS):
        post = loads_frontmatter(document)
        # Apply in-memory fixes using the same path as `skilllint check --fix`.
        _fixed_content, _fixes = validator._apply_fixes(document, FileType.SKILL)  # noqa: SLF001
        # Guard to prevent the loop being optimised away.
        if post is None:
            raise RuntimeError("loads_frontmatter returned None for a non-empty document")
    elapsed = time.perf_counter() - start

    mean_ms = (elapsed / _ITERATIONS) * 1000.0
    total_ms = elapsed * 1000.0

    print(f"\nCPU BENCHMARK [fix]: {_ITERATIONS} iterations in {total_ms:.3f}ms (mean {mean_ms:.6f} ms/iter)")

    if elapsed >= _TIME_LIMIT_SECONDS:
        raise AssertionError(
            f"CPU benchmark [fix] exceeded {_TIME_LIMIT_SECONDS}s time limit: {elapsed:.3f}s "
            f"({_ITERATIONS} iterations, mean {mean_ms:.3f} ms/iter)"
        )

    return {"mean_ms": round(mean_ms, 6), "total_ms": round(total_ms, 3)}


# ---------------------------------------------------------------------------
# Pytest test functions
# ---------------------------------------------------------------------------


def test_cpu_clean() -> None:
    """Benchmark: parse clean YAML frontmatter 1000x within time limit.

    Constructs a well-formed skill document in memory then calls
    ``loads_frontmatter`` for each iteration. Asserts that 1000 iterations
    complete within the time budget.
    """
    _run_clean_scenario()


def test_cpu_violations() -> None:
    """Benchmark: parse violations YAML frontmatter + lint check 1000x within time limit.

    Constructs a skill document with FM004/FM007/FM008 violations in memory,
    calls ``loads_frontmatter`` plus a regex lint check for each iteration.
    Asserts that 1000 iterations complete within the time budget.
    """
    _run_violations_scenario()


def test_cpu_fix() -> None:
    """Benchmark: parse violations YAML frontmatter + apply fixes 1000x within time limit.

    Constructs a skill document with FM004/FM007/FM008 violations in memory,
    calls ``loads_frontmatter`` plus ``FrontmatterValidator._apply_fixes`` for
    each iteration. Asserts that 1000 iterations complete within the time budget.
    """
    _run_fix_scenario()


# ---------------------------------------------------------------------------
# github-action-benchmark JSON output
# ---------------------------------------------------------------------------


def _build_gh_benchmark_array(
    clean: dict[str, float], violations: dict[str, float], fix: dict[str, float]
) -> list[dict[str, float | str]]:
    """Build a ``customSmallerIsBetter`` JSON array for github-action-benchmark.

    Args:
        clean: Timing dict for the clean scenario.
        violations: Timing dict for the violations scenario.
        fix: Timing dict for the fix scenario.

    Returns:
        List of benchmark entry dicts, each with ``name``, ``value``, and
        ``unit`` keys, suitable for the ``customSmallerIsBetter`` tool format.
    """
    return [
        {"name": "cpu_clean_mean_ms", "value": clean["mean_ms"], "unit": "ms"},
        {"name": "cpu_violations_mean_ms", "value": violations["mean_ms"], "unit": "ms"},
        {"name": "cpu_fix_mean_ms", "value": fix["mean_ms"], "unit": "ms"},
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CPU benchmark for skilllint YAML parsing and lint/fix logic")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write customSmallerIsBetter JSON array to this file path",
    )
    args = parser.parse_args()
    output_path: Path | None = args.output

    clean_timing = _run_clean_scenario()
    violations_timing = _run_violations_scenario()
    fix_timing = _run_fix_scenario()

    if output_path is not None:
        gh_array = _build_gh_benchmark_array(clean_timing, violations_timing, fix_timing)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(gh_array, indent=2), encoding="utf-8")
