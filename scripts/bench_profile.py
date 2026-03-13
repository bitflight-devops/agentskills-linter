"""Profiling companion for skilllint benchmark scenarios.

Profiles the same three in-process scenarios as bench_cpu.py using cProfile +
pstats, then prints a sorted cumtime table (top N functions) for each scenario.
Optionally writes ``.prof`` files for external inspection and prints a diff
summary showing functions that appear in the ``violations`` scenario but not
``clean``, sorted by cumtime delta.

Scenarios
---------
1. ``clean``      — scan 1000 well-formed skill documents (no violations)
2. ``violations`` — scan 200 skills containing FM004/FM007/FM008/FM009 patterns
3. ``fix``        — apply ``--fix`` logic to the violations document in-process

Usage::

    python scripts/bench_profile.py
    python scripts/bench_profile.py --top 20
    python scripts/bench_profile.py --output /tmp/profiles
    python scripts/bench_profile.py --no-diff
    python scripts/bench_profile.py --output /tmp/profiles --top 15 --no-diff
"""

from __future__ import annotations

import argparse
import cProfile
import io
import operator
import pstats
import re
from pathlib import Path
from typing import NamedTuple

from skilllint.frontmatter_utils import loads_frontmatter
from skilllint.plugin_validator import FileType, FrontmatterValidator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures"
_CLEAN_FIXTURE = _FIXTURES_DIR / "benchmark-plugin-1000-skills.zip"
_VIOLATIONS_FIXTURE = _FIXTURES_DIR / "benchmark-plugin-violations.zip"

# Minimum cumtime threshold (seconds) for a stdlib-only function to appear in
# the filtered output.  Functions from the skilllint package are always shown
# regardless of this threshold.
_STDLIB_CUMTIME_THRESHOLD_S = 0.001  # 1 ms

_ITERATIONS = 200  # kept low enough for profiling overhead to stay manageable

# ---------------------------------------------------------------------------
# Document builders (mirrors bench_cpu.py patterns)
# ---------------------------------------------------------------------------


def _build_clean_document() -> str:
    """Build a well-formed skill frontmatter document with no violations.

    Returns:
        Complete markdown string with valid YAML frontmatter and a short body.
    """
    return """\
---
name: my-benchmark-skill
description: A realistic benchmark skill used for profiling
version: 1.0.0
tools: Read, Write, Edit
skills: helper-skill, utility-skill
---

# My Benchmark Skill

This is the body of the synthetic skill document used for profiling.
"""


def _build_violations_document() -> str:
    """Build a skill frontmatter document containing FM004/FM007/FM008 violations.

    Returns:
        Complete markdown string with violating YAML frontmatter and a short body.
    """
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

This document contains FM004, FM007, and FM008 violations for profiling.
"""


# ---------------------------------------------------------------------------
# Scenario runners — each returns the cProfile.Profile object after the run
# ---------------------------------------------------------------------------


def _profile_clean() -> cProfile.Profile:
    """Profile the 'clean' scenario.

    Calls ``loads_frontmatter`` :data:`_ITERATIONS` times on a well-formed
    document with no violations.

    Returns:
        Populated ``cProfile.Profile`` instance.
    """
    document = _build_clean_document()
    profiler = cProfile.Profile()

    profiler.enable()
    for _ in range(_ITERATIONS):
        post = loads_frontmatter(document)
        if post is None:
            raise RuntimeError("loads_frontmatter returned None for clean document")
    profiler.disable()

    return profiler


def _profile_violations() -> cProfile.Profile:
    """Profile the 'violations' scenario.

    Calls ``loads_frontmatter`` plus an FM004 regex check
    :data:`_ITERATIONS` times, mirroring ``FrontmatterValidator.validate``
    internals.

    Returns:
        Populated ``cProfile.Profile`` instance.
    """
    document = _build_violations_document()
    fm004_pattern = re.compile(r"description:\s*[|>][-+]?\s*\n")
    profiler = cProfile.Profile()

    profiler.enable()
    for _ in range(_ITERATIONS):
        post = loads_frontmatter(document)
        raw_fm = document.split("---", 2)[1] if "---" in document else ""
        fm004_pattern.search(raw_fm)
        if post is None:
            raise RuntimeError("loads_frontmatter returned None for violations document")
    profiler.disable()

    return profiler


def _profile_fix() -> cProfile.Profile:
    """Profile the 'fix' scenario.

    Calls ``loads_frontmatter`` then ``FrontmatterValidator._apply_fixes``
    :data:`_ITERATIONS` times on the violations document.

    Returns:
        Populated ``cProfile.Profile`` instance.
    """
    document = _build_violations_document()
    validator = FrontmatterValidator()
    profiler = cProfile.Profile()

    profiler.enable()
    for _ in range(_ITERATIONS):
        post = loads_frontmatter(document)
        validator._apply_fixes(document, FileType.SKILL)  # noqa: SLF001
        if post is None:
            raise RuntimeError("loads_frontmatter returned None for fix document")
    profiler.disable()

    return profiler


# ---------------------------------------------------------------------------
# pstats helpers
# ---------------------------------------------------------------------------


class FunctionStat(NamedTuple):
    """Parsed representation of a single pstats row.

    Attributes:
        filename: Source file path (may be abbreviated).
        lineno: Line number of the function definition.
        funcname: Function name.
        ncalls: Number of calls (includes recursive calls).
        cumtime: Cumulative time in seconds.
        tottime: Total time in seconds (excluding sub-calls).
    """

    filename: str
    lineno: int
    funcname: str
    ncalls: int
    cumtime: float
    tottime: float


# pstats output lines after the header look like:
#   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
_PSTATS_LINE_RE = re.compile(
    r"^\s*(\d+(?:/\d+)?)"  # ncalls (may be "1/100")
    r"\s+([\d.]+)"  # tottime
    r"\s+([\d.]+)"  # percall (tottime)
    r"\s+([\d.]+)"  # cumtime
    r"\s+([\d.]+)"  # percall (cumtime)
    r"\s+(.+):(\d+)\((.+)\)\s*$"  # filename:lineno(funcname)
)


def _match_to_stat(m: re.Match[str]) -> FunctionStat:
    """Convert a regex match from a pstats output line into a :class:`FunctionStat`.

    Args:
        m: A successful match from :data:`_PSTATS_LINE_RE`.

    Returns:
        Populated :class:`FunctionStat` instance.
    """
    ncalls_raw, tottime_s, _pt, cumtime_s, _pc, filename, lineno_s, funcname = m.groups()
    return FunctionStat(
        filename=filename,
        lineno=int(lineno_s),
        funcname=funcname,
        ncalls=int(ncalls_raw.split("/")[-1]),
        cumtime=float(cumtime_s),
        tottime=float(tottime_s),
    )


def _parse_stats(profiler: cProfile.Profile, top: int) -> list[FunctionStat]:
    """Extract and filter pstats rows from a completed profiler run.

    Only rows satisfying at least one of the following are returned:
    - The function is from the ``skilllint`` package.
    - ``cumtime`` is at least :data:`_STDLIB_CUMTIME_THRESHOLD_S`.

    Results are sorted by ``cumtime`` descending, then truncated to *top*.

    Args:
        profiler: A disabled ``cProfile.Profile`` populated by a scenario run.
        top: Maximum number of rows to return.

    Returns:
        List of :class:`FunctionStat` tuples, at most *top* entries.
    """
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative")
    stats.print_stats()
    raw = stream.getvalue()

    rows: list[FunctionStat] = []
    for line in raw.splitlines():
        m = _PSTATS_LINE_RE.match(line)
        if not m:
            continue
        stat = _match_to_stat(m)
        if "skilllint" not in stat.filename and stat.cumtime < _STDLIB_CUMTIME_THRESHOLD_S:
            continue
        rows.append(stat)

    rows.sort(key=lambda r: r.cumtime, reverse=True)
    return rows[:top]


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

_COL_FILE = 50
_COL_FUNC = 35
_COL_CALLS = 8
_COL_CUM = 10
_COL_TOT = 10


def _print_table(title: str, rows: list[FunctionStat]) -> None:
    """Print a human-readable pstats table to stdout.

    Args:
        title: Section heading printed above the table.
        rows: Function stats to display, already sorted and filtered.
    """
    sep = "-" * (_COL_FILE + _COL_FUNC + _COL_CALLS + _COL_CUM + _COL_TOT + 6)
    header = (
        f"{'filename':<{_COL_FILE}}  "
        f"{'function':<{_COL_FUNC}}  "
        f"{'ncalls':>{_COL_CALLS}}  "
        f"{'cumtime':>{_COL_CUM}}  "
        f"{'tottime':>{_COL_TOT}}"
    )

    print(f"\n{'=' * len(sep)}")
    print(f"  {title}")
    print(f"{'=' * len(sep)}")
    print(header)
    print(sep)

    for row in rows:
        # Abbreviate long filenames — keep tail of the path
        fname = row.filename
        if len(fname) > _COL_FILE:
            fname = "..." + fname[-(_COL_FILE - 3) :]
        print(
            f"{fname:<{_COL_FILE}}  "
            f"{row.funcname:<{_COL_FUNC}}  "
            f"{row.ncalls:>{_COL_CALLS}}  "
            f"{row.cumtime:>{_COL_CUM}.6f}  "
            f"{row.tottime:>{_COL_TOT}.6f}"
        )

    if not rows:
        print("  (no entries above threshold)")

    print(sep)


def _print_diff(clean_rows: list[FunctionStat], violations_rows: list[FunctionStat]) -> None:
    """Print functions present in violations but absent in clean, by cumtime delta.

    A function "appears in violations but not clean" when it either does not
    occur in the clean stats at all, or its cumtime in violations exceeds its
    clean cumtime by more than :data:`_STDLIB_CUMTIME_THRESHOLD_S`.

    Args:
        clean_rows: Filtered stats from the clean scenario.
        violations_rows: Filtered stats from the violations scenario.
    """
    # Build lookup: (filename, funcname) -> cumtime for clean
    clean_index: dict[tuple[str, str], float] = {(r.filename, r.funcname): r.cumtime for r in clean_rows}

    diff_rows: list[tuple[float, FunctionStat]] = []
    for row in violations_rows:
        key = (row.filename, row.funcname)
        clean_cumtime = clean_index.get(key, 0.0)
        delta = row.cumtime - clean_cumtime
        if delta > _STDLIB_CUMTIME_THRESHOLD_S:
            diff_rows.append((delta, row))

    diff_rows.sort(key=operator.itemgetter(0), reverse=True)

    sep = "-" * 90
    print(f"\n{'=' * 90}")
    print("  DIFF SUMMARY: functions in 'violations' not present (or heavier) in 'clean'")
    print("  Sorted by cumtime delta (violations - clean), descending")
    print(f"{'=' * 90}")
    print(f"{'filename':<{_COL_FILE}}  {'function':<{_COL_FUNC}}  {'delta_s':>10}  {'viol_cum':>10}")
    print(sep)

    for delta, row in diff_rows:
        fname = row.filename
        if len(fname) > _COL_FILE:
            fname = "..." + fname[-(_COL_FILE - 3) :]
        print(f"{fname:<{_COL_FILE}}  {row.funcname:<{_COL_FUNC}}  {delta:>10.6f}  {row.cumtime:>10.6f}")

    if not diff_rows:
        print("  (no significant overhead difference detected)")

    print(sep)


# ---------------------------------------------------------------------------
# .prof file dump
# ---------------------------------------------------------------------------


def _dump_prof(profiler: cProfile.Profile, output_dir: Path, scenario: str) -> Path:
    """Write a ``.prof`` file for *scenario* into *output_dir*.

    Args:
        profiler: Completed profiler for the scenario.
        output_dir: Directory to write the file into (created if absent).
        scenario: Scenario name used as the filename stem.

    Returns:
        Path to the written ``.prof`` file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / f"{scenario}.prof"
    profiler.dump_stats(str(dest))
    return dest


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse CLI args, run profiling scenarios, and print results.

    Three in-process scenarios are profiled sequentially:
    ``clean``, ``violations``, and ``fix``.  For each, the top *N* functions
    (by cumtime) are printed.  If ``--no-diff`` is not set, a diff summary
    comparing ``violations`` vs ``clean`` is printed last.

    When ``--output DIR`` is provided, one ``.prof`` file per scenario is
    written to *DIR*.
    """
    parser = argparse.ArgumentParser(
        description=("Profile skilllint in-process scenarios (clean / violations / fix) using cProfile + pstats."),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output", type=Path, default=None, metavar="DIR", help="Dump .prof files to this directory (one per scenario)"
    )
    parser.add_argument(
        "--top", type=int, default=30, metavar="N", help="Number of functions to show per scenario table"
    )
    parser.add_argument(
        "--no-diff", action="store_true", default=False, help="Skip the violations-vs-clean diff summary"
    )
    args = parser.parse_args()

    output_dir: Path | None = args.output
    top: int = args.top
    no_diff: bool = args.no_diff

    print(f"Profiling skilllint — {_ITERATIONS} iterations per scenario")
    print(
        f"Filter: skilllint functions always shown; stdlib shown only if cumtime >= {_STDLIB_CUMTIME_THRESHOLD_S * 1000:.0f}ms"
    )

    # --- clean ---
    print("\nRunning scenario: clean ...")
    clean_profiler = _profile_clean()
    clean_rows = _parse_stats(clean_profiler, top)
    _print_table(f"SCENARIO: clean  (top {top} by cumtime, {_ITERATIONS} iterations)", clean_rows)
    if output_dir is not None:
        dest = _dump_prof(clean_profiler, output_dir, "clean")
        print(f"  .prof written -> {dest}")

    # --- violations ---
    print("\nRunning scenario: violations ...")
    violations_profiler = _profile_violations()
    violations_rows = _parse_stats(violations_profiler, top)
    _print_table(f"SCENARIO: violations  (top {top} by cumtime, {_ITERATIONS} iterations)", violations_rows)
    if output_dir is not None:
        dest = _dump_prof(violations_profiler, output_dir, "violations")
        print(f"  .prof written -> {dest}")

    # --- fix ---
    print("\nRunning scenario: fix ...")
    fix_profiler = _profile_fix()
    fix_rows = _parse_stats(fix_profiler, top)
    _print_table(f"SCENARIO: fix  (top {top} by cumtime, {_ITERATIONS} iterations)", fix_rows)
    if output_dir is not None:
        dest = _dump_prof(fix_profiler, output_dir, "fix")
        print(f"  .prof written -> {dest}")

    # --- diff summary ---
    if not no_diff:
        _print_diff(clean_rows, violations_rows)


if __name__ == "__main__":
    main()
