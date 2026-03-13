"""Generate a benchmark fixture zip containing skill files with fixable frontmatter violations.

Creates ``tests/fixtures/benchmark-plugin-violations.zip`` (or a custom path via
``--output``) with 200 skills that exercise the linter's auto-fixable rules:

- FM004: multiline YAML indicator in description (``>-`` / ``|-``)
- FM007: ``tools:`` as a YAML list instead of a CSV string
- FM008: ``skills:`` as a YAML list instead of a CSV string
- FM009: unquoted colon in description value
- FM007+FM008 combined: both ``tools:`` and ``skills:`` as lists

Usage::

    uv run python scripts/generate_violations_fixture.py
    uv run python scripts/generate_violations_fixture.py --output path/to/out.zip --count 50
"""

from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT: Final[Path] = Path("tests/fixtures/benchmark-plugin-violations.zip")
DEFAULT_COUNT: Final[int] = 200

SKILL_BODY: Final[str] = """\
# {title}

## Overview

This skill demonstrates violation pattern **{violation}** for benchmark testing.
It contains realistic markdown body content so that the linter processes a
representative file size when scanning the plugin.

## Role Identification (Mandatory)

The model must identify its ROLE_TYPE before proceeding with any task.

## When to Use This Skill

Use this skill when you need to:

- Perform the primary task associated with {title}
- Coordinate related sub-tasks across multiple agents
- Validate outputs against acceptance criteria
- Report results in a structured format

## Core Behaviour

1. Receive the task description from the orchestrator.
2. Analyse the inputs and identify required resources.
3. Execute the task using available tools.
4. Return structured results with clear success/failure indicators.

## Output Format

Results are always returned as a structured summary containing:

- Status: success or failure
- Details: human-readable explanation
- Artifacts: any files or data produced

## Notes

- Always verify inputs before processing.
- Prefer idempotent operations where possible.
- Log progress at each major step.
- This file is intentionally verbose for benchmark purposes.
"""


# ---------------------------------------------------------------------------
# Violation types
# ---------------------------------------------------------------------------


class ViolationType(StrEnum):
    """Enumeration of the supported violation types."""

    FM004 = "FM004"
    FM007 = "FM007"
    FM008 = "FM008"
    FM009 = "FM009"
    FM007_FM008 = "FM007+FM008"


# Cycle order matches the task specification (1-indexed skill numbering).
VIOLATION_CYCLE: Final[list[ViolationType]] = [
    ViolationType.FM004,
    ViolationType.FM007,
    ViolationType.FM008,
    ViolationType.FM009,
    ViolationType.FM007_FM008,
]


# ---------------------------------------------------------------------------
# Frontmatter builders
# ---------------------------------------------------------------------------


def _fm004_frontmatter(n: int) -> str:
    """Return frontmatter with a multiline YAML indicator in description (FM004).

    Args:
        n: Skill number (1-based).

    Returns:
        YAML frontmatter string without surrounding ``---`` delimiters.
    """
    return f"""\
name: violations--{n}
description: >-
  A multiline description for skill {n}
version: 1.0.0
triggers:
  - when working on violations skill {n}"""


def _fm007_frontmatter(n: int) -> str:
    """Return frontmatter with ``tools:`` as a YAML list instead of CSV (FM007).

    Args:
        n: Skill number (1-based).

    Returns:
        YAML frontmatter string without surrounding ``---`` delimiters.
    """
    return f"""\
name: violations--{n}
description: Benchmark violation skill number {n} for FM007 testing
version: 1.0.0
triggers:
  - when working on violations skill {n}
tools:
  - Read
  - Write
  - Edit"""


def _fm008_frontmatter(n: int) -> str:
    """Return frontmatter with ``skills:`` as a YAML list instead of CSV (FM008).

    Args:
        n: Skill number (1-based).

    Returns:
        YAML frontmatter string without surrounding ``---`` delimiters.
    """
    return f"""\
name: violations--{n}
description: Benchmark violation skill number {n} for FM008 testing
version: 1.0.0
triggers:
  - when working on violations skill {n}
skills:
  - skill-a
  - skill-b"""


def _fm009_frontmatter(n: int) -> str:
    """Return frontmatter with an unquoted colon in the description value (FM009).

    Args:
        n: Skill number (1-based).

    Returns:
        YAML frontmatter string without surrounding ``---`` delimiters.
    """
    return f"""\
name: violations--{n}
description: Skill purpose: handle task {n}
version: 1.0.0
triggers:
  - when working on violations skill {n}"""


def _fm007_fm008_frontmatter(n: int) -> str:
    """Return frontmatter with both ``tools:`` and ``skills:`` as YAML lists (FM007+FM008).

    Args:
        n: Skill number (1-based).

    Returns:
        YAML frontmatter string without surrounding ``---`` delimiters.
    """
    return f"""\
name: violations--{n}
description: Benchmark violation skill number {n} for FM007+FM008 testing
version: 1.0.0
triggers:
  - when working on violations skill {n}
tools:
  - Read
  - Write
  - Edit
skills:
  - skill-a
  - skill-b"""


_FRONTMATTER_BUILDERS = {
    ViolationType.FM004: _fm004_frontmatter,
    ViolationType.FM007: _fm007_frontmatter,
    ViolationType.FM008: _fm008_frontmatter,
    ViolationType.FM009: _fm009_frontmatter,
    ViolationType.FM007_FM008: _fm007_fm008_frontmatter,
}


# ---------------------------------------------------------------------------
# Skill content assembly
# ---------------------------------------------------------------------------


def build_skill_md(n: int, violation: ViolationType) -> str:
    """Assemble a complete ``SKILL.md`` file for the given skill number and violation.

    Args:
        n: Skill number (1-based).
        violation: The violation type to inject into the frontmatter.

    Returns:
        Full file content including YAML frontmatter and markdown body.
    """
    frontmatter = _FRONTMATTER_BUILDERS[violation](n)
    title = f"Violations Skill {n}"
    body = SKILL_BODY.format(title=title, violation=violation.value)
    return f"---\n{frontmatter}\n---\n\n{body}"


# ---------------------------------------------------------------------------
# Plugin JSON
# ---------------------------------------------------------------------------


def build_plugin_json(count: int) -> str:
    """Build the ``plugin.json`` content listing all generated skills.

    The schema matches the existing benchmark fixture exactly.

    Args:
        count: Total number of skills in the plugin.

    Returns:
        JSON string for the ``plugin.json`` file.
    """
    data = {
        "name": "benchmark-violations-plugin",
        "version": "1.0.0",
        "description": f"Synthetic plugin with {count} skills containing fixable frontmatter violations for benchmarking skilllint auto-fix performance",
    }
    return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Zip generation
# ---------------------------------------------------------------------------


@dataclass
class ViolationSummary:
    """Summary of injected violations produced during zip generation.

    Attributes:
        total_skills: Total number of skills written.
        counts: Per-violation count mapping.
    """

    total_skills: int = 0
    counts: dict[ViolationType, int] = field(default_factory=dict)

    def record(self, violation: ViolationType) -> None:
        """Record one occurrence of *violation*.

        Args:
            violation: The violation type that was injected.
        """
        self.total_skills += 1
        self.counts[violation] = self.counts.get(violation, 0) + 1


def generate_zip(output: Path, count: int) -> ViolationSummary:
    """Generate the violations benchmark fixture zip file.

    Args:
        output: Destination path for the zip file.
        count: Number of skills to generate.

    Returns:
        Summary of injected violations.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = ViolationSummary()

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("plugin.json", build_plugin_json(count))

        for n in range(1, count + 1):
            violation = VIOLATION_CYCLE[(n - 1) % len(VIOLATION_CYCLE)]
            skill_content = build_skill_md(n, violation)
            zf.writestr(f"skills/violations--{n}/SKILL.md", skill_content)
            summary.record(violation)

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="Generate a benchmark fixture zip with fixable frontmatter violations.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="Destination path for the generated zip file."
    )
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Number of skills to generate.")
    return parser.parse_args()


def main() -> None:
    """Entry point: parse arguments, generate the zip, and print a summary."""
    args = _parse_args()
    output: Path = args.output
    count: int = args.count

    print(f"Generating {count} skills -> {output}")
    summary = generate_zip(output, count)

    print(f"\nDone. Wrote {output} ({output.stat().st_size:,} bytes)")
    print(f"Total skills: {summary.total_skills}")
    print("\nViolation breakdown:")
    for violation_type in VIOLATION_CYCLE:
        n = summary.counts.get(violation_type, 0)
        print(f"  {violation_type.value:<12} {n:>4} skills")


if __name__ == "__main__":
    main()
