"""Cursor platform adapter.

Data provider and file-type validator for Cursor platform files.
Validates .mdc frontmatter against the bundled cursor v1.json schema.
No rule-series logic lives here — rule series fire from the core validator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import frontmatter

from skilllint import load_bundled_schema

if TYPE_CHECKING:
    import pathlib


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
        return {"AS"}

    def get_schema(self, file_type: str) -> dict | None:
        """Return the bundled schema sub-object for the given file_type."""
        schema = load_bundled_schema("cursor", "v1")
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

        mdc_schema = self.get_schema("mdc")
        if mdc_schema is None:
            return []

        post = frontmatter.load(str(path))
        fm: dict = dict(post.metadata)

        known_fields: set[str] = set(mdc_schema.get("properties", {}).keys())
        required_fields: list[str] = mdc_schema.get("required", [])
        additional_properties: bool = mdc_schema.get("additionalProperties", True)

        # Check required fields
        violations: list[dict] = [
            {
                "code": "cursor-mdc-missing-required",
                "severity": "error",
                "message": f"Required field '{field}' is missing from .mdc frontmatter",
            }
            for field in required_fields
            if field not in fm
        ]

        # Check for unknown fields when additionalProperties is false
        if not additional_properties:
            violations.extend(
                {
                    "code": "cursor-mdc-unknown-field",
                    "severity": "error",
                    "message": (f"Unknown field '{field}' in .mdc frontmatter (additionalProperties is false)"),
                }
                for field in fm
                if field not in known_fields
            )

        return violations
