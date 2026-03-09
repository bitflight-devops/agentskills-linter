"""
Cursor platform adapter.

Validates **/*.mdc rule files against the Cursor schema.
Full implementation in plan 02-04; this stub satisfies Protocol compliance
and entry_points registration required by plan 02-02 tests.
"""

from __future__ import annotations

import pathlib


class CursorAdapter:
    """Adapter for Cursor **/*.mdc rule files."""

    def id(self) -> str:
        return "cursor"

    def path_patterns(self) -> list[str]:
        return ["**/*.mdc"]

    def applicable_rules(self) -> set[str]:
        return {"AS", "CUR"}

    def validate(self, path: pathlib.Path) -> list[dict]:
        # Full validation implemented in plan 02-04
        return []
