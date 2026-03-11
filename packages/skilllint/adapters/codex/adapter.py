"""Codex (OpenAI) platform adapter.

Data provider and file-type validator for Codex platform files.
Validates AGENTS.md non-empty and .rules prefix_rule() field names
against the bundled codex v1.json fields object.
No rule-series logic lives here — rule series fire from the core validator.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from skilllint import load_bundled_schema

if TYPE_CHECKING:
    import pathlib

# Matches: prefix_rule(\n    key = value,\n    ...\n)
# Captures the body between the outer parentheses.
_PREFIX_RULE_RE = re.compile(r"prefix_rule\s*\(([^)]*)\)", re.DOTALL)
# Matches individual key = value pairs inside a prefix_rule() body.
_FIELD_RE = re.compile(r"^\s*(\w+)\s*=", re.MULTILINE)


class CodexAdapter:
    """Adapter for Codex AGENTS.md and .rules files."""

    def id(self) -> str:
        """Return the adapter ID."""
        return "codex"

    def path_patterns(self) -> list[str]:
        """Return the glob patterns for files this adapter handles."""
        return [".agents/skills/**/*.md", "AGENTS.md", "**/*.rules", ".codex/**"]

    def applicable_rules(self) -> set[str]:
        """Return the set of rule prefixes applicable to this adapter."""
        return {"AS"}

    def get_schema(self, file_type: str) -> dict | None:
        """Return the bundled schema sub-object for the given file_type."""
        schema = load_bundled_schema("codex", "v1")
        return schema.get("file_types", {}).get(file_type)

    # ------------------------------------------------------------------
    # Concrete validation helpers (used by validate() and plan 02-05)
    # ------------------------------------------------------------------

    def validate_agents_md(self, content: str) -> list[str]:
        """Return violation messages for empty AGENTS.md content."""
        if not content.strip():
            return ["AGENTS.md is empty"]
        return []

    def validate_rules_file(self, content: str) -> list[str]:
        """Validate prefix_rule() calls in a .rules file.

        Returns violation messages for:
        - Fields not in the fields object from the codex v1.json schema

        Returns:
            List of violation messages.
        """
        schema = self.get_schema("prefix_rule")
        if schema is None:
            return []

        known: set[str] = set(schema.get("fields", {}).keys())
        violations: list[str] = []

        for match in _PREFIX_RULE_RE.finditer(content):
            body = match.group(1)
            for field_match in _FIELD_RE.finditer(body):
                field = field_match.group(1)
                if field not in known:
                    violations.append(f"Unknown field '{field}' in prefix_rule() (known fields: {sorted(known)})")

        return violations

    # ------------------------------------------------------------------
    # PlatformAdapter.validate()
    # ------------------------------------------------------------------

    def validate(self, path: pathlib.Path) -> list[dict]:
        """Validate AGENTS.md and .rules files.

        Returns violation dicts with keys: code, severity, message.

        Returns:
            List of violation dicts.
        """
        violations: list[dict] = []

        if path.suffix == ".md":
            content = path.read_text(encoding="utf-8")
            violations.extend(
                {"code": "codex-agents-md-empty", "severity": "error", "message": msg}
                for msg in self.validate_agents_md(content)
            )

        elif path.suffix == ".rules":
            content = path.read_text(encoding="utf-8")
            violations.extend(
                {"code": "codex-rules-unknown-field", "severity": "error", "message": msg}
                for msg in self.validate_rules_file(content)
            )

        return violations
