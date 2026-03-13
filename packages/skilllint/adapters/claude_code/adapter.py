"""Claude Code platform adapter.

Data provider for Claude Code platform files. Returns platform metadata
and delegates schema loading to load_bundled_schema(). No validation
logic lives here — the core validator (plan 02-05) runs the checks.
"""

from __future__ import annotations

import msgspec.json
from typing import TYPE_CHECKING

from skilllint import load_bundled_schema

if TYPE_CHECKING:
    import pathlib


class ClaudeCodeAdapter:
    """Adapter for Claude Code .claude/**/*.md skill files."""

    def id(self) -> str:
        """Return the adapter ID."""
        return "claude_code"

    def path_patterns(self) -> list[str]:
        """Return the glob patterns for files this adapter handles."""
        return [".claude/**/*.md", "plugin.json", "hooks.json", "agents/**/*.md", "commands/**/*.md"]

    def applicable_rules(self) -> set[str]:
        """Return the set of rule prefixes applicable to this adapter."""
        return {"SK", "PR", "HK", "AS"}

    def get_schema(self, file_type: str) -> dict | None:
        """Return the bundled schema for the given file_type, or None if unrecognized."""
        schema = load_bundled_schema("claude_code", "v1")
        file_types = schema.get("file_types", {})
        if file_type in file_types:
            return file_types[file_type]
        # Top-level schema for plugin_json maps to root schema object
        if file_type == "plugin_json":
            return schema
        return None

    def validate(self, path: pathlib.Path) -> list[dict]:
        """Platform-level validation for files outside the core SK/PR/HK pipeline.

        Validates JSON files (plugin.json variants) against the bundled schema's
        fields object (required=true entries).  SKILL.md / agent .md / hooks.json are still
        handled by the existing _validate_single_path pipeline in
        plugin_validator.py; this method is the fallback for file types that
        pipeline does not recognise.

        Returns:
            List of violation dicts with keys: code, severity, message.
        """
        if path.suffix != ".json":
            return []

        try:
            data = msgspec.json.decode(path.read_bytes())
        except (msgspec.DecodeError, OSError) as exc:
            return [{"code": "PL002", "severity": "error", "message": f"Invalid JSON: {exc}"}]

        schema = self.get_schema("plugin")
        if schema is None:
            return []

        fields: dict = schema.get("fields", {})
        required: list[str] = [name for name, meta in fields.items() if meta.get("required", False)]
        violations: list[dict] = [
            {"code": "PL003", "severity": "error", "message": f"Missing required field '{field}' in plugin manifest"}
            for field in required
            if field not in data
        ]
        return violations
