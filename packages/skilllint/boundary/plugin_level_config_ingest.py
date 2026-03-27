"""Ingest plugin-level JSON (``hooks/hooks.json``, ``.mcp.json``, ``plugin.json``) for PA001.

Parsed JSON is untrusted; Pydantic validates shape before exposing names to rules.
See ``docs/TYPING_POLICY.md``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from skilllint.scan_runtime import _load_plugin_json

if TYPE_CHECKING:
    from pathlib import Path


class HooksJsonDocument(BaseModel):
    """``hooks/hooks.json`` — PA001 only needs hook event names (keys of ``hooks``)."""

    model_config = ConfigDict(extra="ignore", strict=True)

    hooks: dict[str, JsonValue] = Field(default_factory=dict)


class McpServersJsonDocument(BaseModel):
    """``mcpServers`` object shape in ``.mcp.json`` or ``plugin.json``."""

    model_config = ConfigDict(extra="ignore", strict=True, populate_by_name=True)

    mcp_servers: dict[str, JsonValue] = Field(default_factory=dict, alias="mcpServers")


def hook_event_names_from_raw_hooks_json(raw: object) -> frozenset[str]:
    """Validate parsed JSON and return ``hooks`` mapping keys, or empty if invalid.

    Args:
        raw: Value produced by ``json.loads`` (or equivalent).

    Returns:
        Frozenset of hook event names; empty when the document is not a valid mapping
        or does not match the expected shape.
    """
    try:
        doc = HooksJsonDocument.model_validate(raw)
    except ValidationError:
        return frozenset()
    return frozenset(str(k) for k in doc.hooks)


def ingest_plugin_hook_event_names(hooks_json_path: Path) -> frozenset[str]:
    """Load ``hooks/hooks.json`` and return declared hook event names.

    Args:
        hooks_json_path: Path to ``hooks.json`` (typically ``plugin_dir / "hooks" / "hooks.json"``).

    Returns:
        Hook event names from the ``hooks`` object; empty if the file is missing,
        unreadable, or not valid JSON / shape.
    """
    if not hooks_json_path.is_file():
        return frozenset()
    try:
        raw = json.loads(hooks_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return frozenset()
    return hook_event_names_from_raw_hooks_json(raw)


def mcp_server_names_from_mcp_servers_document(raw: object) -> frozenset[str]:
    """Extract ``mcpServers`` keys from a parsed ``.mcp.json`` or full ``plugin.json`` payload.

    Args:
        raw: Root object from ``json.loads``.

    Returns:
        Server names; empty when validation fails or ``mcpServers`` is absent.
    """
    try:
        doc = McpServersJsonDocument.model_validate(raw)
    except ValidationError:
        return frozenset()
    return frozenset(str(k) for k in doc.mcp_servers)


def ingest_plugin_level_mcp_server_names(plugin_dir: Path) -> frozenset[str]:
    """Union MCP server names from plugin-root ``.mcp.json`` and ``.claude-plugin/plugin.json``.

    Uses the cached manifest loader in ``scan_runtime`` for ``plugin.json`` so PA001
    shares one disk read with other callers.

    Args:
        plugin_dir: Plugin root directory.

    Returns:
        All declared server names from both sources; empty for missing or invalid files.
    """
    names: set[str] = set()
    mcp_path = plugin_dir / ".mcp.json"
    if mcp_path.is_file():
        try:
            raw_mcp = json.loads(mcp_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
        else:
            names.update(mcp_server_names_from_mcp_servers_document(raw_mcp))
    manifest = _load_plugin_json(plugin_dir)
    if manifest is not None:
        names.update(mcp_server_names_from_mcp_servers_document(manifest))
    return frozenset(names)


__all__ = [
    "HooksJsonDocument",
    "McpServersJsonDocument",
    "hook_event_names_from_raw_hooks_json",
    "ingest_plugin_hook_event_names",
    "ingest_plugin_level_mcp_server_names",
    "mcp_server_names_from_mcp_servers_document",
]
