"""Timing benchmark tests for the skilllint CLI against the 1000-skill fixture."""

from __future__ import annotations

import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _get_git_info() -> tuple[str, str]:
    """Return the current git SHA and branch name.

    Returns:
        A 2-tuple of (short_sha, branch_name).  Falls back to ``"unknown"``
        strings if git is not available or the repository has no commits.
    """
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sha = "unknown"

    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        branch = "unknown"

    return sha, branch


def _write_result(results_path: Path, record: dict[str, Any]) -> None:
    """Append *record* to the JSON results file, creating it when absent.

    Each call appends a new entry to a top-level JSON array, preserving
    earlier results.  The parent directory is created on demand.

    Args:
        results_path: Path to the ``benchmark_results.json`` file.
        record: Dictionary to append to the results list.
    """
    results_path.parent.mkdir(parents=True, exist_ok=True)

    existing: list[dict[str, Any]] = []
    try:
        existing = json.loads(results_path.read_text(encoding="utf-8"))
        if not isinstance(existing, list):
            existing = []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        existing = []

    existing.append(record)
    results_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


_RESULTS_FILE = Path(__file__).parent.parent.parent / "scripts" / "results" / "benchmark_results.json"
_TIME_LIMIT_SECONDS = 120.0


def test_io_scan_1000_skills_timing(extracted_plugin_dir: Path, plugin_file_count: int) -> None:
    """Run skilllint against the 1000-skill fixture and record timing.

    Executes ``skilllint`` (or ``agentlint``) via subprocess, measures
    wall-clock duration, writes the result to
    ``scripts/results/benchmark_results.json``, then asserts completion
    within 120 seconds.

    Args:
        extracted_plugin_dir: Path to the extracted benchmark plugin tree.
        plugin_file_count: Number of ``SKILL.md`` files found (from fixture).
    """
    start = time.perf_counter()
    result = subprocess.run(
        ["skilllint", "check", str(extracted_plugin_dir)], capture_output=True, text=True, check=False
    )
    duration = time.perf_counter() - start

    # skilllint exits 0 (no issues) or 1 (lint issues found) — both are valid.
    assert result.returncode in (0, 1), (
        f"skilllint failed unexpectedly (exit {result.returncode}):\n"
        f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
    )

    skill_count = plugin_file_count
    skills_per_second = skill_count / duration if duration > 0 else 0.0

    git_sha, branch = _get_git_info()

    record: dict[str, Any] = {
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "skill_count": skill_count,
        "duration_seconds": round(duration, 4),
        "skills_per_second": round(skills_per_second, 2),
        "git_sha": git_sha,
        "branch": branch,
    }

    _write_result(_RESULTS_FILE, record)

    print(f"\nBENCHMARK: {skill_count} skills scanned in {duration:.2f}s ({skills_per_second:.1f} skills/sec)")

    assert duration < _TIME_LIMIT_SECONDS, (
        f"Benchmark exceeded {_TIME_LIMIT_SECONDS}s limit: {duration:.2f}s "
        f"for {skill_count} skills ({skills_per_second:.1f} skills/sec)"
    )


def test_io_scan_timing_report() -> None:
    """Read the most recent benchmark result from the JSON file and log it.

    This is a reporting-only test that always passes.  It reads the last
    entry written by ``test_io_scan_1000_skills_timing`` (if the file
    exists) and prints a human-readable summary for CI log inspection.
    """
    if not _RESULTS_FILE.exists():
        print(f"\nNo benchmark results file found at: {_RESULTS_FILE}")
        return

    try:
        data = json.loads(_RESULTS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"\nCould not read benchmark results: {exc}")
        return

    if not isinstance(data, list) or not data:
        print("\nBenchmark results file is empty or malformed.")
        return

    latest = data[-1]
    print(
        f"\nLATEST BENCHMARK RESULT:\n"
        f"  timestamp      : {latest.get('timestamp', 'n/a')}\n"
        f"  skill_count    : {latest.get('skill_count', 'n/a')}\n"
        f"  duration       : {latest.get('duration_seconds', 'n/a')}s\n"
        f"  skills/sec     : {latest.get('skills_per_second', 'n/a')}\n"
        f"  git_sha        : {latest.get('git_sha', 'n/a')}\n"
        f"  branch         : {latest.get('branch', 'n/a')}\n"
    )
