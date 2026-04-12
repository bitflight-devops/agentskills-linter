#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "skilllint",
# ]
#
# [tool.uv.sources]
# skilllint = { path = ".." }
# ///
"""CI assertion script: verify that skilllint rules output meets MIN_REGISTERED_SERIES.

Invokes ``skilllint rules`` via subprocess, counts distinct two-letter series
prefixes in the table output, and exits non-zero if the count is below
MIN_REGISTERED_SERIES.

Usage::

    uv run --script scripts/assert_rules_completeness.py

Exit codes:
    0 -- rule series count meets or exceeds the minimum
    1 -- rule series count is below the minimum (pre-migration state)
    2 -- subprocess invocation of 'skilllint rules' failed unexpectedly
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys

# MIN_REGISTERED_SERIES is re-exported from skilllint.rules._constants.
# Source: P038 architect spec section 8 -- 14 series total.
from skilllint.rules import MIN_REGISTERED_SERIES


def _count_series(output: str) -> set[str]:
    """Return the set of two-letter series prefixes found in rules table output.

    Parses lines from ``skilllint rules`` table for rule IDs such as
    ``AS001``, ``FM002``, ``SK003``, extracting the two-letter prefix.

    Args:
        output: Combined stdout text from ``skilllint rules``.

    Returns:
        Set of two-letter series prefix strings.
    """
    matches = re.findall(r"\b([A-Z]{2})\d{3}\b", output)
    return set(matches)


def main() -> int:
    """Run the completeness assertion.

    Returns:
        Exit code: 0 if count meets minimum, 1 if below, 2 on invocation error.
    """
    skilllint_exe = shutil.which("skilllint")
    if skilllint_exe is None:
        print("ERROR: 'skilllint' executable not found on PATH.", file=sys.stderr)
        return 2

    proc = subprocess.run([skilllint_exe, "rules"], capture_output=True, text=True, check=False)

    if proc.returncode not in {0, 1}:
        # Any non-zero exit that is not a normal "no rules" scenario is unexpected.
        print(f"ERROR: 'skilllint rules' exited with unexpected code {proc.returncode}.", file=sys.stderr)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        return 2

    prefixes = _count_series(proc.stdout)
    count = len(prefixes)

    if count < MIN_REGISTERED_SERIES:
        print(
            f"FAIL: 'skilllint rules' reports {count} series prefix(es) "
            f"but requires at least {MIN_REGISTERED_SERIES}. "
            f"Found: {sorted(prefixes)}.",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: 'skilllint rules' reports {count} series prefix(es) "
        f"(minimum {MIN_REGISTERED_SERIES}). Found: {sorted(prefixes)}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Refs #38
