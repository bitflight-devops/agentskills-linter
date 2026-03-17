"""Unit tests for plugin agent prohibited frontmatter fields validation.

Tests:
- Plugin agent with `permissionMode` in frontmatter produces error (TestProhibitedPermissionMode)
- Plugin agent with `hooks` in frontmatter produces error (TestProhibitedHooks)
- Plugin agent with `mcpServers` in frontmatter produces error (TestProhibitedMcpServers)
- Plugin agent with multiple prohibited fields produces one error per field (TestMultipleProhibitedFields)
- Plugin agent with no prohibited fields passes cleanly (TestCleanAgent)
- Non-plugin (standalone) agent with prohibited fields produces no error (TestStandaloneAgent)
- Error messages include correct actionable guidance per field (TestErrorGuidance)

Source: https://docs.anthropic.com/en/docs/claude-code/sub-agents
> "For security reasons, plugin subagents do not support the `hooks`,
> `mcpServers`, or `permissionMode` frontmatter fields."
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import msgspec.json
import pytest

from skilllint.plugin_validator import PluginAgentFrontmatterValidator

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


class TestProhibitedHooks:
    """Test error when plugin agent frontmatter contains hooks."""

    def test_plugin_agent_with_hooks_produces_error(self, tmp_path: Path) -> None:
        """Test that hooks in plugin agent frontmatter triggers an error.

        Tests: Prohibited field detection for hooks
        How: Create plugin agent with hooks in frontmatter, validate
        Why: Plugin subagents cannot define hooks per Claude Code spec
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(
            plugin_dir,
            "my-agent",
            {"name": "my-agent", "description": "Test agent", "hooks": {"preToolUse": "echo hello"}},
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is False
        assert len(result.errors) >= 1
        hooks_errors = [e for e in result.errors if "hooks" in e.message]
        assert len(hooks_errors) >= 1


class TestProhibitedMcpServers:
    """Test error when plugin agent frontmatter contains mcpServers."""

    def test_plugin_agent_with_mcp_servers_produces_error(self, tmp_path: Path) -> None:
        """Test that mcpServers in plugin agent frontmatter triggers an error.

        Tests: Prohibited field detection for mcpServers
        How: Create plugin agent with mcpServers in frontmatter, validate
        Why: Plugin subagents cannot define mcpServers per Claude Code spec
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(
            plugin_dir,
            "my-agent",
            {"name": "my-agent", "description": "Test agent", "mcpServers": {"my-server": "http://localhost:3000"}},
        )

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is False
        assert len(result.errors) >= 1
        mcp_errors = [e for e in result.errors if "mcpServers" in e.message]
        assert len(mcp_errors) >= 1


class TestMultipleProhibitedFields:
    """Test one error per prohibited field when multiple are present."""

    def test_multiple_prohibited_fields_produce_separate_errors(self, tmp_path: Path) -> None:
        """Test that each prohibited field generates its own error.

        Tests: One error per prohibited field
        How: Create plugin agent with all three prohibited fields, validate
        Why: Each field needs its own error with field-specific guidance
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

        assert result.passed is False
        # Must have at least 3 errors -- one per prohibited field
        hooks_errors = [e for e in result.errors if "hooks" in e.message]
        mcp_errors = [e for e in result.errors if "mcpServers" in e.message]
        perm_errors = [e for e in result.errors if "permissionMode" in e.message]
        assert len(hooks_errors) >= 1
        assert len(mcp_errors) >= 1
        assert len(perm_errors) >= 1


class TestCleanAgent:
    """Test plugin agent with no prohibited fields passes cleanly."""

    def test_plugin_agent_without_prohibited_fields_passes(self, tmp_path: Path) -> None:
        """Test that a plugin agent with only allowed fields produces no errors.

        Tests: Clean agent happy path
        How: Create plugin agent with only name and description, validate
        Why: Agents without prohibited fields should pass validation
        """
        plugin_dir = _make_plugin(tmp_path)
        _add_agent_with_frontmatter(plugin_dir, "my-agent", {"name": "my-agent", "description": "A well-behaved agent"})

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_plugin_with_no_agents_passes(self, tmp_path: Path) -> None:
        """Test that a plugin with no agent files produces no errors.

        Tests: No agents directory
        How: Create plugin with no agents/ directory, validate
        Why: Plugin without agents should pass with no errors
        """
        plugin_dir = _make_plugin(tmp_path)

        validator = PluginAgentFrontmatterValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0


class TestStandaloneAgent:
    """Test that standalone agents (not in a plugin) are not flagged."""

    def test_standalone_agent_with_prohibited_fields_produces_no_error(self, tmp_path: Path) -> None:
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

    def test_non_plugin_directory_passes(self, tmp_path: Path) -> None:
        """Test that a directory without plugin.json produces no errors.

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


class TestErrorGuidance:
    """Test that error messages include correct actionable guidance per field."""

    def test_hooks_error_suggests_hooks_json(self, tmp_path: Path) -> None:
        """Test hooks error message suggests moving to hooks/hooks.json.

        Tests: Actionable guidance for hooks field
        How: Create plugin agent with hooks, check error suggestion text
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

        hooks_errors = [e for e in result.errors if "hooks" in e.message]
        assert len(hooks_errors) >= 1
        # Check that the error or suggestion mentions the alternative location
        for error in hooks_errors:
            combined_text = f"{error.message} {error.suggestion or ''}"
            assert "hooks.json" in combined_text or "hooks/hooks.json" in combined_text

    def test_mcp_servers_error_suggests_mcp_json(self, tmp_path: Path) -> None:
        """Test mcpServers error message suggests moving to .mcp.json.

        Tests: Actionable guidance for mcpServers field
        How: Create plugin agent with mcpServers, check error suggestion text
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

        mcp_errors = [e for e in result.errors if "mcpServers" in e.message]
        assert len(mcp_errors) >= 1
        for error in mcp_errors:
            combined_text = f"{error.message} {error.suggestion or ''}"
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


class TestValidatorInterface:
    """Test PluginAgentFrontmatterValidator implements the Validator protocol."""

    def test_can_fix_returns_false(self) -> None:
        """Test can_fix() returns False.

        Tests: Auto-fix capability
        How: Call can_fix(), assert False
        Why: Prohibited field removal requires manual review of alternatives
        """
        validator = PluginAgentFrontmatterValidator()
        assert validator.can_fix() is False

    def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
        """Test fix() raises NotImplementedError.

        Tests: Fix method contract
        How: Call fix() on a plugin directory, expect NotImplementedError
        Why: Prohibited field fixes require manual changes
        """
        plugin_dir = _make_plugin(tmp_path)

        validator = PluginAgentFrontmatterValidator()
        with pytest.raises(NotImplementedError):
            validator.fix(plugin_dir)
