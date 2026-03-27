"""Boundary layer: parse untrusted external input into concrete typed models.

YAML, JSON, env, and similar sources are handled only here (or in future sibling
``boundary`` modules). See ``docs/TYPING_POLICY.md``.
"""

from __future__ import annotations

from skilllint.boundary.plugin_agent_pa001_ingest import (
    McpInlineServerDefinition,
    McpServerNameRef,
    Pa001YamlIngestOutcome,
    PluginAgentPa001Snapshot,
    ingest_plugin_agent_frontmatter_for_pa001,
    parse_plugin_agent_pa001_snapshot_from_mapping,
)
from skilllint.boundary.plugin_level_config_ingest import (
    HooksJsonDocument,
    McpServersJsonDocument,
    hook_event_names_from_raw_hooks_json,
    ingest_plugin_hook_event_names,
    ingest_plugin_level_mcp_server_names,
    mcp_server_names_from_mcp_servers_document,
)

__all__ = [
    "HooksJsonDocument",
    "McpInlineServerDefinition",
    "McpServerNameRef",
    "McpServersJsonDocument",
    "Pa001YamlIngestOutcome",
    "PluginAgentPa001Snapshot",
    "hook_event_names_from_raw_hooks_json",
    "ingest_plugin_agent_frontmatter_for_pa001",
    "ingest_plugin_hook_event_names",
    "ingest_plugin_level_mcp_server_names",
    "mcp_server_names_from_mcp_servers_document",
    "parse_plugin_agent_pa001_snapshot_from_mapping",
]
