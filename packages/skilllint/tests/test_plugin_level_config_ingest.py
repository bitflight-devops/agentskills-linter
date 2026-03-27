"""Property and unit tests for plugin-level JSON boundary ingest (PA001 helpers)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from hypothesis import given, strategies as st

from skilllint.boundary.plugin_level_config_ingest import (
    hook_event_names_from_raw_hooks_json,
    ingest_plugin_hook_event_names,
    ingest_plugin_level_mcp_server_names,
    mcp_server_names_from_mcp_servers_document,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_hook_event_names_valid_mapping() -> None:
    assert hook_event_names_from_raw_hooks_json({"hooks": {"preToolUse": [], "postToolUse": {}}}) == frozenset({
        "preToolUse",
        "postToolUse",
    })


def test_hook_event_names_hooks_not_object_fails_open_to_empty() -> None:
    assert hook_event_names_from_raw_hooks_json({"hooks": "broken"}) == frozenset()


def test_hook_event_names_non_dict_root() -> None:
    assert hook_event_names_from_raw_hooks_json([]) == frozenset()
    assert hook_event_names_from_raw_hooks_json("x") == frozenset()


def test_mcp_names_from_document() -> None:
    assert mcp_server_names_from_mcp_servers_document({"mcpServers": {"a": {}, "b": {}}}) == frozenset({"a", "b"})


def test_mcp_names_invalid_mcp_servers_type() -> None:
    assert mcp_server_names_from_mcp_servers_document({"mcpServers": []}) == frozenset()


@given(st.dictionaries(st.text(max_size=24), st.integers(), max_size=12))
def test_hook_event_names_arbitrary_dict_never_raises(d: dict[str, int]) -> None:
    hook_event_names_from_raw_hooks_json(d)


@given(st.dictionaries(st.text(max_size=24), st.integers(), max_size=12))
def test_mcp_names_arbitrary_dict_never_raises(d: dict[str, int]) -> None:
    mcp_server_names_from_mcp_servers_document(d)


def test_ingest_plugin_hook_event_names_missing_file(tmp_path: Path) -> None:
    assert ingest_plugin_hook_event_names(tmp_path / "nope.json") == frozenset()


def test_ingest_plugin_level_mcp_empty_dir(tmp_path: Path) -> None:
    assert ingest_plugin_level_mcp_server_names(tmp_path) == frozenset()


@pytest.fixture
def plugin_with_mcp_and_hooks(tmp_path: Path) -> Path:
    root = tmp_path / "plugin"
    (root / "hooks").mkdir(parents=True)
    (root / "hooks" / "hooks.json").write_text('{"hooks": {"SessionStart": {}}}', encoding="utf-8")
    (root / ".mcp.json").write_text('{"mcpServers": {"srv1": {}}}', encoding="utf-8")
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "plugin.json").write_text('{"name": "p", "mcpServers": {"srv2": {}}}', encoding="utf-8")
    return root


def test_ingest_plugin_hook_event_names_reads_file(plugin_with_mcp_and_hooks: Path) -> None:
    p = plugin_with_mcp_and_hooks / "hooks" / "hooks.json"
    assert ingest_plugin_hook_event_names(p) == frozenset({"SessionStart"})


def test_ingest_plugin_level_mcp_unions_sources(plugin_with_mcp_and_hooks: Path) -> None:
    assert ingest_plugin_level_mcp_server_names(plugin_with_mcp_and_hooks) == frozenset({"srv1", "srv2"})
