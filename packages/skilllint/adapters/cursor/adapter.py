"""Cursor platform adapter.

Data provider and file-type validator for Cursor platform files.
Validates .mdc frontmatter against the provider cursor v1.json schema.
No rule-series logic lives here — rule series fire from the core validator.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from skilllint.frontmatter import load_frontmatter
from skilllint.rules.cu_series import validate_mdc_frontmatter
from skilllint.schemas import load_provider_schema

if TYPE_CHECKING:
    import pathlib

_logger = logging.getLogger(__name__)


class CursorAdapter:
    """Adapter for Cursor **/*.mdc rule files and skill Markdown."""

    def id(self) -> str:
        """Return the adapter ID."""
        return "cursor"

    def path_patterns(self) -> list[str]:
        """Return the glob patterns for files this adapter handles."""
        # NOT ".cursor/**/*.md" — too broad (Pitfall 3 in RESEARCH.md)
        return ["**/*.mdc", ".cursor/skills/**/*.md", ".claude/skills/**/*.md", ".agents/skills/**/*.md"]

    def applicable_rules(self) -> set[str]:
        """Return the set of rule prefixes applicable to this adapter."""
        return {"AS", "CU"}

    def constraint_scopes(self) -> set[str]:
        """Return the set of constraint_scope values from the provider schema.

        These are extracted from the field-level constraint_scope annotations
        in the loaded schema (values: 'shared' or 'provider_specific').

        Returns:
            Set of constraint_scope strings, defaulting to {'shared'} if schema
            cannot be loaded or has no constraint_scope annotations.
        """
        try:
            schema = load_provider_schema("cursor")
        except FileNotFoundError:
            _logger.debug("Schema not found for cursor, defaulting to 'shared' scope")
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
        schema = load_provider_schema("cursor")
        return schema.get("file_types", {}).get(file_type)

    def validate(self, path: pathlib.Path) -> list[dict]:
        """Validate .mdc files against the cursor mdc JSON Schema.

        Returns a list of violation dicts with keys: code, severity, message.
        Non-.mdc files are not validated here (rule series handle them).

        Returns:
            List of violation dicts.
        """
        if path.suffix != ".mdc":
            return []

        schema = self.get_schema("mdc")
        mdc_schema: dict[str, object] | None = schema if isinstance(schema, dict) else None
        if mdc_schema is None:
            return []

        post = load_frontmatter(path)
        fm: dict[str, object] = dict(post.metadata)

        issues = validate_mdc_frontmatter(fm, mdc_schema)
        return [{"code": i.code, "severity": i.severity, "message": i.message} for i in issues]
