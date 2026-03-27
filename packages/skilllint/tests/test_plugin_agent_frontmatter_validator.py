"""Unit tests for plugin agent frontmatter fields validation (PA001).

Tests cover nuanced severity levels and cross-checking:
- Plugin agent with `permissionMode` in frontmatter produces error (TestProhibitedPermissionMode)
- Plugin agent with `hooks` in frontmatter produces warning (TestHooksWarning)
- Plugin agent with `hooks` always warns with varying guidance based on hooks.json coverage (TestHooksAlwaysWarns)
- Plugin agent with `mcpServers` inline definition produces warning (TestMcpServersInline)
- Plugin agent with `mcpServers` string reference found in .mcp.json is silenced (TestMcpServersResolved)
- Plugin agent with `mcpServers` string reference NOT in .mcp.json produces warning (TestMcpServersUnresolved)
- Plugin agent with mixed mcpServers warns only for missing ones (TestMcpServersMixed)
- Plugin agent with multiple restricted fields produces correct severity per field (TestMultipleRestrictedFields)
- Plugin agent with no restricted fields passes cleanly (TestCleanAgent)
- Non-plugin (standalone) agent with restricted fields produces no issues (TestStandaloneAgent)
- Error/warning messages include correct actionable guidance per field (TestGuidance)

Source: https://docs.anthropic.com/en/docs/claude-code/sub-agents.md#choose-the-subagent-scope
> "For security reasons, plugin subagents do not support the `hooks`,
> `mcpServers`, or `permissionMode` frontmatter fields."
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import msgspec.json
import pytest

from skilllint.rules.pa_series import PluginAgentFrontmatterValidator

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Helper factory functions
# ---------------------------------------------------------------------------


def _make_plugin(tmp_path: Path, plugin_name: str = "test-plugin", plugin_json_content: str | None = None) -> Path:
    """Create a plugin directory with .claude-plugin/plugin.json.

    Args:
        tmp_path: Pytest temporary directory
        plugin_name: Name of the plugin directory
        plugin_json_content: Raw JSON string for plugin.json; if None, a
            minimal valid JSON is written

    Returns:
        Path to the plugin root directory
    """
    plugin_dir = tmp_path / plugin_name
    plugin_dir.mkdir()
    claude_plugin = plugin_dir / ".claude-plugin"
    claude_plugin.mkdir()

    if plugin_json_content is not None:
        (claude_plugin / "plugin.json").write_text(plugin_json_content)
    else:
        default_config = {"name": plugin_name, "skills": [], "agents": [], "commands": []}
        (claude_plugin / "plugin.json").write_text(
            msgspec.json.format(msgspec.json.encode(default_config), indent=2).decode()
        )

    return plugin_dir


def _add_agent_with_frontmatter(plugin_dir: Path, agent_name: str, frontmatter_fields: dict[str, object]) -> Path:
    """Create an agent .md file with specified frontmatter fields.

    Args:
        plugin_dir: Plugin root directory
        agent_name: Agent file stem (without .md extension)
        frontmatter_fields: Dictionary of frontmatter key-value pairs

    Returns:
        Path to the new agent .md file
    """
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir(exist_ok=True)
    agent_md = agents_dir / f"{agent_name}.md"

    # Build YAML frontmatter from the fields dict
    yaml_lines = ["---"]
    for key, value in frontmatter_fields.items():
        if isinstance(value, dict):
            yaml_lines.append(f"{key}:")
            for sub_key, sub_value in value.items():
                yaml_lines.append(f"  {sub_key}: {sub_value}")
        elif isinstance(value, list):
            yaml_lines.append(f"{key}:")
            yaml_lines.extend(f"  - {item}" for item in value)
        elif isinstance(value, str):
            yaml_lines.append(f"{key}: {value}")
        else:
            yaml_lines.append(f"{key}: {value}")
    yaml_lines.extend(("---", f"\n# {agent_name}\n"))

    agent_md.write_text("\n".join(yaml_lines))
    return agent_md


def _add_mcp_json(plugin_dir: Path, servers: dict[str, dict]) -> Path:
    """Create a .mcp.json file at plugin root with given server definitions.

    Args:
        plugin_dir: Plugin root directory
        servers: Dict mapping server names to config objects

    Returns:
        Path to the .mcp.json file
    """
    mcp_path = plugin_dir / ".mcp.json"
    mcp_path.write_text(json.dumps({"mcpServers": servers}, indent=2))
    return mcp_path


def _add_hooks_json(plugin_dir: Path, events: dict[str, object]) -> Path:
    """Create a hooks/hooks.json file at plugin root with given event handlers.

    Args:
        plugin_dir: Plugin root directory
        events: Dict mapping event names to handler config

    Returns:
        Path to the hooks.json file
    """
    hooks_dir = plugin_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hooks_path = hooks_dir / "hooks.json"
    hooks_path.write_text(json.dumps({"hooks": events}, indent=2))
    return hooks_path


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestProhibitedPermissionMode:
    """Test error when plugin agent frontmatter contains permissionMode."""

    def test_plugin_agent_with_permission_mode_produces_error(self, tmp_path: Path) -> None:
        """Test that permissionMode in plugin agent frontmatter triggers an error.

        Tests: Prohibited field detection for permissionMode
        How: Create plugin agent with permissionMode in frontmatter, validate
        Why: Plugin subagents cannot use permissionMode per Claude Code spec
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(
            plugin_dir, "my-agent", {"name": "my-agent", "description": "Test agent", "permissionMode": "full"}
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is False
        assert len(result.errors) >= 1
        permission_errors = [e for e in result.errors if "permissionMode" in e.message]
        assert len(permission_errors) >= 1
        assert permission_errors[0].severity == "error"


class TestHooksWarning:
    """Test warning (not error) when plugin agent frontmatter contains hooks."""

    def test_plugin_agent_with_hooks_produces_warning(self, tmp_path: Path) -> None:
        """Test that hooks in plugin agent frontmatter triggers a warning, not error.

        Tests: hooks field produces warning severity
        How: Create plugin agent with hooks in frontmatter, validate
        Why: hooks is silently ignored in plugin agents — warning, not error
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(
            plugin_dir,
            "my-agent",
            {"name": "my-agent", "description": "Test agent", "hooks": {"preToolUse": "echo hello"}},
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        # hooks no longer causes failure — it's a warning
        assert result.passed is True
        assert len(result.errors) == 0
        hooks_warnings = [w for w in result.warnings if "hooks" in w.message]
        assert len(hooks_warnings) >= 1
        assert hooks_warnings[0].severity == "warning"


class TestHooksAlwaysWarns:
    """Test that hooks warning is always emitted with varying guidance."""

    def test_hooks_warns_with_coverage_note_when_plugin_hooks_json_covers_events(self, tmp_path: Path) -> None:
        """Test hooks warning emitted with 'already cover' guidance when plugin hooks.json covers same events.

        Tests: hooks always warns even when plugin hooks.json covers same events
        How: Create plugin agent with hooks, create hooks/hooks.json covering same events
        Why: The hooks field is ALWAYS ignored in plugin agents — silencing hid dead weight
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(
            plugin_dir,
            "my-agent",
            {"name": "my-agent", "description": "Test agent", "hooks": {"preToolUse": "echo hello"}},
        )
        _add_hooks_json(plugin_dir, {"preToolUse": [{"command": "echo hello"}]})

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0
        hooks_warnings = [w for w in result.warnings if "hooks" in w.message]
        assert len(hooks_warnings) >= 1
        assert hooks_warnings[0].severity == "warning"
        assert "already cover these events" in (hooks_warnings[0].suggestion or "")

    def test_hooks_warns_with_move_guidance_when_plugin_hooks_json_missing_events(self, tmp_path: Path) -> None:
        """Test hooks warning emitted with 'move to' guidance when plugin hooks.json doesn't cover all events.

        Tests: partial coverage produces 'move to' guidance
        How: Agent has preToolUse + postToolUse, plugin hooks.json only has preToolUse
        Why: Missing event coverage means the hooks need to be moved to plugin level
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(
            plugin_dir,
            "my-agent",
            {
                "name": "my-agent",
                "description": "Test agent",
                "hooks": {"preToolUse": "echo hello", "postToolUse": "echo bye"},
            },
        )
        _add_hooks_json(plugin_dir, {"preToolUse": [{"command": "echo hello"}]})

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        hooks_warnings = [w for w in result.warnings if "hooks" in w.message]
        assert len(hooks_warnings) >= 1
        assert "move to" in (hooks_warnings[0].suggestion or "").lower()


class TestMcpServersInline:
    """Test warning when plugin agent has inline mcpServers definitions."""

    def test_inline_mcp_definition_produces_warning(self, tmp_path: Path) -> None:
        """Test that inline mcpServers definition triggers a warning.

        Tests: Inline mcpServers detection
        How: Create plugin agent with mcpServers containing config objects, validate
        Why: Inline definitions should be moved to .mcp.json at plugin root
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(
            plugin_dir,
            "my-agent",
            {"name": "my-agent", "description": "Test agent", "mcpServers": {"my-server": "http://localhost:3000"}},
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        # mcpServers no longer causes failure — it's a warning
        assert result.passed is True
        assert len(result.errors) == 0
        mcp_warnings = [w for w in result.warnings if "mcpServers" in w.message]
        assert len(mcp_warnings) >= 1
        assert mcp_warnings[0].severity == "warning"


class TestMcpServersResolved:
    """Test that mcpServers string references found in .mcp.json are silenced."""

    def test_string_reference_found_in_mcp_json_silenced(self, tmp_path: Path) -> None:
        """Test mcpServers string reference is silenced when found in .mcp.json.

        Tests: mcpServers cross-checking against .mcp.json
        How: Create plugin agent with mcpServers list of strings, create .mcp.json with those servers
        Why: Agent is just documenting which plugin-level servers it uses — no warning needed
        """
        plugin_dir = _make_plugin(tmp_path)

        # Agent references servers by name (string references in list form)
        agents_dir = plugin_dir / "agents"
        agents_dir.mkdir(exist_ok=True)
        agent_md = agents_dir / "my-agent.md"
        agent_md.write_text(
            "---\nname: my-agent\ndescription: Test agent\nmcpServers:\n  - github\n  - slack\n---\n\n# my-agent\n"
        )

        # Plugin-level .mcp.json defines these servers
        _add_mcp_json(
            plugin_dir,
            {
                "github": {"type": "http", "url": "https://api.githubcopilot.com/mcp/"},
                "slack": {"type": "http", "url": "https://slack.example.com/mcp/"},
            },
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_string_reference_found_in_plugin_json_silenced(self, tmp_path: Path) -> None:
        """Test mcpServers string reference is silenced when found in plugin.json.

        Tests: mcpServers cross-checking against plugin.json mcpServers section
        How: Create plugin agent with string refs, define servers in plugin.json
        Why: plugin.json can also declare mcpServers at plugin level
        """
        plugin_dir = _make_plugin(tmp_path)

        # Write plugin.json with mcpServers section
        plugin_json = {
            "name": "test-plugin",
            "skills": [],
            "agents": [],
            "commands": [],
            "mcpServers": {"github": {"type": "http", "url": "https://api.githubcopilot.com/mcp/"}},
        }
        (plugin_dir / ".claude-plugin" / "plugin.json").write_text(json.dumps(plugin_json, indent=2))

        agents_dir = plugin_dir / "agents"
        agents_dir.mkdir(exist_ok=True)
        agent_md = agents_dir / "my-agent.md"
        agent_md.write_text(
            "---\nname: my-agent\ndescription: Test agent\nmcpServers:\n  - github\n---\n\n# my-agent\n"
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0


class TestMcpServersUnresolved:
    """Test warning when mcpServers string references are not found in plugin config."""

    def test_string_reference_not_in_mcp_json_produces_warning(self, tmp_path: Path) -> None:
        """Test mcpServers string reference not in .mcp.json produces warning.

        Tests: mcpServers unresolved reference detection
        How: Create plugin agent with string ref, no .mcp.json
        Why: Server not available at plugin level — user needs to add it
        """
        plugin_dir = _make_plugin(tmp_path)

        agents_dir = plugin_dir / "agents"
        agents_dir.mkdir(exist_ok=True)
        agent_md = agents_dir / "my-agent.md"
        agent_md.write_text(
            "---\nname: my-agent\ndescription: Test agent\nmcpServers:\n  - unknown-server\n---\n\n# my-agent\n"
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0
        mcp_warnings = [w for w in result.warnings if "unknown-server" in w.message]
        assert len(mcp_warnings) >= 1
        assert mcp_warnings[0].severity == "warning"


class TestMcpServersMixed:
    """Test mixed mcpServers — warns only for missing ones."""

    def test_mixed_mcp_servers_warns_only_for_missing(self, tmp_path: Path) -> None:
        """Test that mixed mcpServers warns only for unresolved references.

        Tests: Mixed resolved/unresolved mcpServers
        How: Agent has github (in .mcp.json) and unknown (not in .mcp.json)
        Why: Only unresolved references should produce warnings
        """
        plugin_dir = _make_plugin(tmp_path)

        _add_mcp_json(plugin_dir, {"github": {"type": "http", "url": "https://api.githubcopilot.com/mcp/"}})

        agents_dir = plugin_dir / "agents"
        agents_dir.mkdir(exist_ok=True)
        agent_md = agents_dir / "my-agent.md"
        agent_md.write_text(
            "---\n"
            "name: my-agent\n"
            "description: Test agent\n"
            "mcpServers:\n"
            "  - github\n"
            "  - unknown-server\n"
            "---\n"
            "\n# my-agent\n"
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0
        # Only one warning — for unknown-server, not github
        mcp_warnings = [w for w in result.warnings if "mcpServers" in w.message or "unknown-server" in w.message]
        assert len(mcp_warnings) == 1
        assert "unknown-server" in mcp_warnings[0].message


class TestMultipleRestrictedFields:
    """Test correct severity per field when multiple restricted fields present."""

    def test_multiple_fields_produce_correct_severity(self, tmp_path: Path) -> None:
        """Test that each restricted field generates the correct severity.

        Tests: Mixed severity for multiple fields
        How: Create plugin agent with all three restricted fields, validate
        Why: permissionMode=error, hooks=warning, mcpServers=warning
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(
            plugin_dir,
            "my-agent",
            {
                "name": "my-agent",
                "description": "Test agent",
                "hooks": {"preToolUse": "echo hello"},
                "mcpServers": {"my-server": "http://localhost:3000"},
                "permissionMode": "full",
            },
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        # permissionMode causes failure
        assert result.passed is False
        perm_errors = [e for e in result.errors if "permissionMode" in e.message]
        assert len(perm_errors) >= 1
        assert perm_errors[0].severity == "error"

        # hooks and mcpServers are warnings, not errors
        hooks_warnings = [w for w in result.warnings if "hooks" in w.message]
        mcp_warnings = [w for w in result.warnings if "mcpServers" in w.message]
        assert len(hooks_warnings) >= 1
        assert len(mcp_warnings) >= 1
        assert hooks_warnings[0].severity == "warning"
        assert mcp_warnings[0].severity == "warning"

        # No hooks or mcpServers in errors
        assert not any("hooks" in e.message for e in result.errors)
        assert not any("mcpServers" in e.message for e in result.errors)


class TestCleanAgent:
    """Test plugin agent with no restricted fields passes cleanly."""

    def test_plugin_agent_without_restricted_fields_passes(self, tmp_path: Path) -> None:
        """Test that a plugin agent with only allowed fields produces no issues.

        Tests: Clean agent happy path
        How: Create plugin agent with only name and description, validate
        Why: Agents without restricted fields should pass validation
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(plugin_dir, "my-agent", {"name": "my-agent", "description": "A well-behaved agent"})

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_plugin_with_no_agents_passes(self, tmp_path: Path) -> None:
        """Test that a plugin with no agent files produces no issues.

        Tests: No agents directory
        How: Create plugin with no agents/ directory, validate
        Why: Plugin without agents should pass with no issues
        """
        plugin_dir = _make_plugin(tmp_path)

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0


class TestStandaloneAgent:
    """Test that standalone agents (not in a plugin) are not flagged."""

    def test_standalone_agent_with_restricted_fields_produces_no_issue(self, tmp_path: Path) -> None:
        """Test that non-plugin agents can use hooks, mcpServers, permissionMode.

        Tests: Rule only applies in plugin context
        How: Create agent file without .claude-plugin/plugin.json parent, validate
        Why: Standalone agents in .claude/agents/ CAN use these fields
        """
        # Create a standalone agent directory (no .claude-plugin/plugin.json)
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        agent_md = agents_dir / "my-agent.md"
        agent_md.write_text(
            "---\n"
            "name: my-agent\n"
            "description: Standalone agent\n"
            "permissionMode: full\n"
            "hooks:\n"
            "  preToolUse: echo hello\n"
            "mcpServers:\n"
            "  my-server: http://localhost:3000\n"
            "---\n"
            "\n# my-agent\n"
        )

        validator = PluginAgentFrontmatterValidator()
        # Validate the parent directory (not a plugin -- no .claude-plugin/plugin.json)
        result = validator.validate(tmp_path)

        assert result.passed is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_non_plugin_directory_passes(self, tmp_path: Path) -> None:
        """Test that a directory without plugin.json produces no issues.

        Tests: Non-plugin directory detection
        How: Create plain directory without .claude-plugin/plugin.json, validate
        Why: Validator must skip non-plugin directories gracefully
        """
        regular_dir = tmp_path / "regular-dir"
        regular_dir.mkdir()

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(regular_dir)

        assert result.passed is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0


class TestGuidance:
    """Test that messages include correct actionable guidance per field."""

    def test_hooks_warning_suggests_hooks_json(self, tmp_path: Path) -> None:
        """Test hooks warning suggests moving to hooks/hooks.json.

        Tests: Actionable guidance for hooks field
        How: Create plugin agent with hooks, check warning suggestion text
        Why: Users need to know the correct alternative location
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(
            plugin_dir,
            "my-agent",
            {"name": "my-agent", "description": "Test agent", "hooks": {"preToolUse": "echo hello"}},
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        hooks_warnings = [w for w in result.warnings if "hooks" in w.message]
        assert len(hooks_warnings) >= 1
        for warning in hooks_warnings:
            combined_text = f"{warning.message} {warning.suggestion or ''}"
            assert "hooks.json" in combined_text or "hooks/hooks.json" in combined_text

    def test_mcp_servers_warning_suggests_mcp_json(self, tmp_path: Path) -> None:
        """Test mcpServers warning suggests moving to .mcp.json.

        Tests: Actionable guidance for mcpServers field
        How: Create plugin agent with mcpServers, check warning suggestion text
        Why: Users need to know the correct alternative location
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(
            plugin_dir,
            "my-agent",
            {"name": "my-agent", "description": "Test agent", "mcpServers": {"my-server": "http://localhost:3000"}},
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        mcp_warnings = [w for w in result.warnings if "mcpServers" in w.message or "my-server" in w.message]
        assert len(mcp_warnings) >= 1
        for warning in mcp_warnings:
            combined_text = f"{warning.message} {warning.suggestion or ''}"
            assert ".mcp.json" in combined_text

    def test_permission_mode_error_suggests_claude_agents(self, tmp_path: Path) -> None:
        """Test permissionMode error suggests copying agent to .claude/agents/.

        Tests: Actionable guidance for permissionMode field
        How: Create plugin agent with permissionMode, check error suggestion text
        Why: Users need to know the correct alternative for permissionMode
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(
            plugin_dir, "my-agent", {"name": "my-agent", "description": "Test agent", "permissionMode": "full"}
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        perm_errors = [e for e in result.errors if "permissionMode" in e.message]
        assert len(perm_errors) >= 1
        for error in perm_errors:
            combined_text = f"{error.message} {error.suggestion or ''}"
            assert ".claude/agents/" in combined_text
            assert "~/.claude/agents/" in combined_text
            assert "permissions.allow" in combined_text
            assert error.docs_url is not None
            assert "choose-the-subagent-scope" in error.docs_url

    def test_pa001_permission_mode_cites_ignored_policy(self, tmp_path: Path) -> None:
        """Messages state Anthropic's documented behavior (ignored at load), not vague 'prohibited'."""
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(
            plugin_dir, "my-agent", {"name": "my-agent", "description": "Test agent", "permissionMode": "full"}
        )
        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)
        perm_errors = [e for e in result.errors if "permissionMode" in e.message]
        assert len(perm_errors) >= 1
        assert "ignored" in perm_errors[0].message.lower()


class TestValidatorInterface:
    """Test PluginAgentFrontmatterValidator implements the Validator protocol."""

    def test_can_fix_returns_false(self) -> None:
        """Test can_fix() returns False.

        Tests: Auto-fix capability
        How: Call can_fix(), assert False
        Why: Restricted field removal requires manual review of alternatives
        """
        validator = PluginAgentFrontmatterValidator()
        assert validator.can_fix() is False

    def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
        """Test fix() raises NotImplementedError.

        Tests: Fix method contract
        How: Call fix() on a plugin directory, expect NotImplementedError
        Why: Restricted field fixes require manual changes
        """
        plugin_dir = _make_plugin(tmp_path)

        validator = PluginAgentFrontmatterValidator()
        with pytest.raises(NotImplementedError):
            validator.fix(plugin_dir)
