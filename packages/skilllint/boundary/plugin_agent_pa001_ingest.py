"""Ingest YAML plugin-agent frontmatter into a concrete PA001 snapshot.

YAML loader output is untyped; narrowing stays in this module. See
``docs/TYPING_POLICY.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class McpServerNameRef:
    """String entry in ``mcpServers`` list — references a plugin-level server name."""

    name: str


@dataclass(frozen=True, slots=True)
class McpInlineServerDefinition:
    """Dict-shaped MCP entry in frontmatter (inline config; ignored at load for plugin agents)."""

    server_name: str


@dataclass(frozen=True, slots=True)
class PluginAgentPa001Snapshot:
    """Validated view of PA001-relevant frontmatter fields."""

    permission_mode_key_present: bool
    hooks_nonempty: bool
    hooks_event_names: frozenset[str]
    mcp_entries: tuple[McpServerNameRef | McpInlineServerDefinition, ...]


@dataclass(frozen=True, slots=True)
class Pa001YamlIngestOutcome:
    """Result of parsing frontmatter YAML for PA001."""

    snapshot: PluginAgentPa001Snapshot | None
    yaml_error: str | None
    colon_fields_fixed: tuple[str, ...]


def _mapping_string_keys_only(root: dict) -> dict[str, object]:
    """Keep only string keys; other keys are ignored for PA001 field lookup.

    Returns:
        Mapping with only ``str`` keys preserved from ``root``.
    """
    out: dict[str, object] = {k: v for k, v in root.items() if isinstance(k, str)}
    return out


def _mcp_list_item_to_entry(item: object) -> McpServerNameRef | McpInlineServerDefinition | None:
    if isinstance(item, dict):
        if not item:
            return None
        first_key = next(iter(item.keys()))
        server_name = first_key if isinstance(first_key, str) else str(first_key)
        return McpInlineServerDefinition(server_name=server_name)
    return McpServerNameRef(name=str(item))


def _build_mcp_entries(mcp_raw: object) -> tuple[McpServerNameRef | McpInlineServerDefinition, ...]:
    entries: list[McpServerNameRef | McpInlineServerDefinition] = []
    if isinstance(mcp_raw, list):
        for item in mcp_raw:
            ent = _mcp_list_item_to_entry(item)
            if ent is not None:
                entries.append(ent)
    elif isinstance(mcp_raw, dict):
        entries.extend(McpInlineServerDefinition(server_name=str(name)) for name in mcp_raw)
    return tuple(entries)


def parse_plugin_agent_pa001_snapshot_from_mapping(mapping: Mapping[str, object]) -> PluginAgentPa001Snapshot:
    """Build a PA001 snapshot from a string-keyed YAML mapping (already narrowed).

    Returns:
        Frozen snapshot of permission mode, hooks, and MCP entries for PA001.
    """
    permission_mode_key_present = "permissionMode" in mapping

    hooks_raw = mapping.get("hooks")
    hooks_nonempty = hooks_raw is not None
    hooks_event_names: frozenset[str] = frozenset()
    if isinstance(hooks_raw, dict):
        hooks_event_names = frozenset(str(k) for k in hooks_raw)

    mcp_entries = _build_mcp_entries(mapping.get("mcpServers"))

    return PluginAgentPa001Snapshot(
        permission_mode_key_present=permission_mode_key_present,
        hooks_nonempty=hooks_nonempty,
        hooks_event_names=hooks_event_names,
        mcp_entries=mcp_entries,
    )


def ingest_plugin_agent_frontmatter_for_pa001(fm_text: str) -> Pa001YamlIngestOutcome:
    """Parse frontmatter text via the shared YAML loader and return a typed outcome.

    Imports ``safe_load_yaml_with_colon_fix`` lazily to avoid an import cycle with
    ``plugin_validator`` (which loads rule modules).

    Returns:
        Outcome with optional snapshot, YAML error string, and colon-fix field names.
    """
    from skilllint.plugin_validator import safe_load_yaml_with_colon_fix  # noqa: PLC0415 — breaks import cycle

    parsed, yaml_err, colon_fields, _used_text = safe_load_yaml_with_colon_fix(fm_text)
    fixed = tuple(colon_fields)

    if yaml_err is not None:
        return Pa001YamlIngestOutcome(snapshot=None, yaml_error=yaml_err, colon_fields_fixed=fixed)

    if not isinstance(parsed, dict):
        return Pa001YamlIngestOutcome(snapshot=None, yaml_error=None, colon_fields_fixed=fixed)

    mapping = _mapping_string_keys_only(parsed)
    snapshot = parse_plugin_agent_pa001_snapshot_from_mapping(mapping)
    return Pa001YamlIngestOutcome(snapshot=snapshot, yaml_error=None, colon_fields_fixed=fixed)


__all__ = [
    "McpInlineServerDefinition",
    "McpServerNameRef",
    "Pa001YamlIngestOutcome",
    "PluginAgentPa001Snapshot",
    "ingest_plugin_agent_frontmatter_for_pa001",
    "parse_plugin_agent_pa001_snapshot_from_mapping",
]
