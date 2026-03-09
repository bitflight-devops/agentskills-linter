"""
Claude Code platform adapter.

Validates .claude/**/*.md skill files against the Claude Code schema.
Full implementation in plan 02-04; this stub satisfies Protocol compliance
and entry_points registration required by plan 02-02 tests.
"""

from __future__ import annotations

import pathlib


class ClaudeCodeAdapter:
    """Adapter for Claude Code .claude/**/*.md skill files."""

    def id(self) -> str:
        return "claude_code"

    def path_patterns(self) -> list[str]:
        return [".claude/**/*.md"]

    def applicable_rules(self) -> set[str]:
        return {"AS", "CC"}

    def validate(self, path: pathlib.Path) -> list[dict]:
        # Full validation implemented in plan 02-04
        return []
