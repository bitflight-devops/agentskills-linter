"""Codex (OpenAI) platform adapter.

Data provider and file-type validator for Codex platform files.
Validation logic for CX001 (AGENTS.md non-empty) and CX002 (prefix_rule()
field names) now lives in rules/cx_series.py and is imported here.
No rule-series logic lives here — rule series fire from the core validator.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from skilllint.rules.cx_series import validate_codex_content
from skilllint.schemas import load_provider_schema

if TYPE_CHECKING:
    import pathlib

_logger = logging.getLogger(__name__)


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
        return {"AS", "CX"}

    def constraint_scopes(self) -> set[str]:
        """Return the set of constraint_scope values from the provider schema.

        These are extracted from the field-level constraint_scope annotations
        in the loaded schema (values: 'shared' or 'provider_specific').

        Returns:
            Set of constraint_scope strings, defaulting to {'shared'} if schema
            cannot be loaded or has no constraint_scope annotations.
        """
        try:
            schema = load_provider_schema("codex")
        except FileNotFoundError:
            _logger.debug("Schema not found for codex, defaulting to 'shared' scope")
            return {"shared"}

        scopes: set[str] = set()
        for file_type_data in schema.get("file_types", {}).values():
            for field_meta in file_type_data.get("fields", {}).values():
                scope = field_meta.get("constraint_scope")
                if scope:
                    scopes.add(scope)
        return scopes or {"shared"}

    def get_schema(self, file_type: str) -> dict | None:
        """Return the provider schema sub-object for the given file_type."""
        schema = load_provider_schema("codex")
        return schema.get("file_types", {}).get(file_type)

    # ------------------------------------------------------------------
    # PlatformAdapter.validate()
    # ------------------------------------------------------------------

    def validate(self, path: pathlib.Path) -> list[dict]:
        """Validate AGENTS.md and .rules files.

        Returns violation dicts with keys: code, severity, message.

        Returns:
            List of violation dicts.
        """
        if path.name == "AGENTS.md":
            content = path.read_text(encoding="utf-8")
            issues = validate_codex_content(content, "agents_md")
            return [{"code": i.code, "severity": i.severity, "message": i.message} for i in issues]

        if path.suffix == ".rules":
            content = path.read_text(encoding="utf-8")
            schema = self.get_schema("prefix_rule")
            prefix_rule_schema: dict[str, object] | None = schema if isinstance(schema, dict) else None
            issues = validate_codex_content(content, "prefix_rule", prefix_rule_schema)
            return [{"code": i.code, "severity": i.severity, "message": i.message} for i in issues]

        return []
