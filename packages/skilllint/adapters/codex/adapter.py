"""
Codex (OpenAI) platform adapter.

Validates AGENTS.md and .rules files against the Codex schema.
Full implementation in plan 02-04; this stub satisfies Protocol compliance
and entry_points registration required by plan 02-02 tests.
"""

from __future__ import annotations

import pathlib


class CodexAdapter:
    """Adapter for Codex AGENTS.md and .rules files."""

    def id(self) -> str:
        return "codex"

    def path_patterns(self) -> list[str]:
        return ["AGENTS.md", "**/*.rules"]

    def applicable_rules(self) -> set[str]:
        return {"AS", "CDX"}

    def validate(self, path: pathlib.Path) -> list[dict]:
        # Full validation implemented in plan 02-04
        return []
