"""Unit tests for NamespaceReferenceValidator.

Tests:
- Valid skill/agent/command references resolve correctly
- All 5 reference pattern types detected and validated
- Built-in agent names skipped (BUILTIN_AGENTS frozenset)
- Missing plugin directory detected (NR001)
- Broken references where plugin dir exists but file missing (NR001)
- Edge cases: no body, no frontmatter, frontmatter-only
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from skilllint.plugin_validator import NamespaceReferenceValidator

if TYPE_CHECKING:
    from pathlib import Path


def _make_plugins_root(tmp_path: Path) -> Path:
    """Create a plugins/ root directory for testing."""
    plugins_root = tmp_path / "plugins"
    plugins_root.mkdir()
    return plugins_root


def _make_plugin_dir(plugins_root: Path, plugin_name: str) -> Path:
    """Create a plugin directory inside plugins_root."""
    plugin_dir = plugins_root / plugin_name
    plugin_dir.mkdir()
    return plugin_dir


def _make_skill(plugin_dir: Path, skill_name: str) -> Path:
    """Create a skill directory with SKILL.md inside a plugin."""
    skill_dir = plugin_dir / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("---\ndescription: Test skill\n---\n\n# Test Skill\n")
    return skill_md


def _make_agent(plugin_dir: Path, agent_name: str) -> Path:
    """Create an agent .md file inside a plugin."""
    agents_dir = plugin_dir / "agents"
    agents_dir.mkdir(exist_ok=True)
    agent_md = agents_dir / f"{agent_name}.md"
    agent_md.write_text(f"---\nname: {agent_name}\ndescription: Test agent\n---\n\n# Test\n")
    return agent_md


def _make_skill_md_with_body(plugins_root: Path, plugin_name: str, body: str) -> Path:
    """Create a SKILL.md inside a plugin with given body, returning its path."""
    plugin_dir = plugins_root / plugin_name
    plugin_dir.mkdir(exist_ok=True)
    skill_dir = plugin_dir / "skills" / "source-skill"
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(f"---\ndescription: Source skill\n---\n\n{body}")
    return skill_md


class TestValidReferences:
    """Test that valid skill/agent/command references resolve without errors."""

    def test_valid_skill_command_reference(self, tmp_path: Path) -> None:
        """Test Skill(command: "plugin:name") resolves when SKILL.md exists.

        Tests: Valid skill command reference
        How: Create target SKILL.md, reference it from source file, validate
        Why: Ensure valid references do not produce NR001 errors
        """
        plugins_root = _make_plugins_root(tmp_path)

        # Create the target plugin and skill
        target_plugin = _make_plugin_dir(plugins_root, "target-plugin")
        _make_skill(target_plugin, "my-skill")

        # Create source SKILL.md inside the plugins tree
        body = 'Activate the skill: Skill(command: "target-plugin:my-skill")\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_valid_agent_reference(self, tmp_path: Path) -> None:
        """Test @plugin:agent-name resolves when agent file exists.

        Tests: Valid agent reference
        How: Create target agent, reference it via @-syntax, validate
        Why: Ensure valid agent references do not produce errors
        """
        plugins_root = _make_plugins_root(tmp_path)

        target_plugin = _make_plugin_dir(plugins_root, "target-plugin")
        _make_agent(target_plugin, "my-agent")

        body = "Use @target-plugin:my-agent for this task.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_valid_slash_command_reference(self, tmp_path: Path) -> None:
        """Test /plugin:skill-name resolves when SKILL.md exists.

        Tests: Valid slash command reference
        How: Create target skill, reference via /plugin:name syntax, validate
        Why: Ensure valid slash command references accepted
        """
        plugins_root = _make_plugins_root(tmp_path)

        target_plugin = _make_plugin_dir(plugins_root, "target-plugin")
        _make_skill(target_plugin, "my-skill")

        body = "Run /target-plugin:my-skill to activate.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_skill_resolves_via_git_pointer_file(self, tmp_path: Path) -> None:
        """Test Skill(command:) resolves when skill dir is a Git pointer file (Windows).

        Tests: _resolve_to_directory handles symlink-as-file (Git on Windows)
        How: Create plugin with pointer file containing target path, validate
        Why: Cross-platform validation; Linux uses symlinks, Windows uses pointer files
        """
        plugins_root = _make_plugins_root(tmp_path)

        # Create the actual skill in another plugin
        real_plugin = _make_plugin_dir(plugins_root, "real-plugin")
        _make_skill(real_plugin, "shared-skill")

        # Create wrapper plugin with pointer file (Git symlink on Windows)
        wrapper_plugin = _make_plugin_dir(plugins_root, "wrapper-plugin")
        skills_dir = wrapper_plugin / "skills"
        skills_dir.mkdir(parents=True)
        pointer_file = skills_dir / "shared-skill"
        pointer_file.write_text("../../real-plugin/skills/shared-skill")

        body = 'Load Skill(command: "wrapper-plugin:shared-skill").\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_can_fix_returns_false(self) -> None:
        """Test can_fix() returns False for NamespaceReferenceValidator.

        Tests: Auto-fix capability detection
        How: Call can_fix(), assert False
        Why: Namespace references require manual correction
        """
        validator = NamespaceReferenceValidator()
        assert validator.can_fix() is False

    def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
        """Test fix() raises NotImplementedError.

        Tests: Auto-fix raises correctly
        How: Create a file, call fix(), expect NotImplementedError
        Why: Namespace references cannot be auto-fixed
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\ndescription: Test\n---\n\nBody.\n")

        validator = NamespaceReferenceValidator()
        with pytest.raises(NotImplementedError):
            validator.fix(skill_md)


class TestSkillCommandPattern:
    """Test Skill(command: "plugin:skill-name") pattern detection."""

    def test_skill_command_pattern_detected(self, tmp_path: Path) -> None:
        """Test Skill(command: "plugin:name") pattern is found and validated.

        Tests: SKILL_COMMAND_PATTERN regex detection
        How: Write file with Skill(command:) syntax, validate against missing target
        Why: Ensure pattern extraction works and produces NR001 for missing target
        """
        plugins_root = _make_plugins_root(tmp_path)

        # Source exists, target plugin directory is missing
        body = 'Invoke Skill(command: "missing-plugin:some-skill") here.\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1

    def test_skill_command_pattern_with_spaces(self, tmp_path: Path) -> None:
        """Test Skill(command: "plugin:name") with spaces after colon.

        Tests: SKILL_COMMAND_PATTERN handles optional spaces
        How: Use extra space in pattern, validate
        Why: Pattern uses \\s* for spaces after colon
        """
        plugins_root = _make_plugins_root(tmp_path)
        body = 'Invoke Skill(command:  "missing-plugin:some-skill") here.\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        # Should detect the reference (even though plugin is missing)
        assert result.passed is False

    def test_skill_command_resolves_via_category(self, tmp_path: Path) -> None:
        """Test Skill(command:) resolves skill nested inside category directory.

        Tests: Nested (category) skill resolution
        How: Create plugin/skills/category/name/SKILL.md, reference via command
        Why: _resolve_skill_reference checks nested paths
        """
        plugins_root = _make_plugins_root(tmp_path)
        target_plugin = _make_plugin_dir(plugins_root, "target-plugin")

        # Nested skill: skills/category/my-skill/SKILL.md
        nested_dir = target_plugin / "skills" / "category" / "my-skill"
        nested_dir.mkdir(parents=True)
        (nested_dir / "SKILL.md").write_text("---\ndescription: Nested skill\n---\n\n# Nested\n")

        body = 'Invoke Skill(command: "target-plugin:my-skill").\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is True
        assert len(result.errors) == 0


class TestSkillSkillPattern:
    """Test Skill(skill="plugin:skill-name") pattern detection."""

    def test_skill_skill_pattern_detected(self, tmp_path: Path) -> None:
        """Test Skill(skill="plugin:name") pattern is found.

        Tests: SKILL_SKILL_PATTERN regex detection
        How: Write file with Skill(skill=) syntax, validate against missing target
        Why: Ensure SKILL_SKILL_PATTERN extracts references correctly
        """
        plugins_root = _make_plugins_root(tmp_path)
        body = 'Load Skill(skill="missing-plugin:my-skill") now.\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1

    def test_skill_skill_pattern_valid_resolves(self, tmp_path: Path) -> None:
        """Test Skill(skill="plugin:name") resolves when target exists.

        Tests: SKILL_SKILL_PATTERN with valid target
        How: Create target, write Skill(skill=) reference, validate
        Why: Ensure valid Skill(skill=) does not produce errors
        """
        plugins_root = _make_plugins_root(tmp_path)
        target_plugin = _make_plugin_dir(plugins_root, "target-plugin")
        _make_skill(target_plugin, "my-skill")

        body = 'Load Skill(skill="target-plugin:my-skill") now.\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is True
        assert len(result.errors) == 0


class TestTaskAgentPattern:
    """Test Task(agent="plugin:agent-name") and Task(agent: "plugin:agent-name") patterns."""

    def test_task_agent_equals_syntax(self, tmp_path: Path) -> None:
        """Test Task(agent="plugin:name") pattern detected.

        Tests: TASK_AGENT_PATTERN with equals separator
        How: Write file with Task(agent=) syntax, validate against missing agent
        Why: Pattern uses agent[=:] to handle both separators
        """
        plugins_root = _make_plugins_root(tmp_path)
        body = 'Delegate Task(agent="missing-plugin:my-agent") to handle this.\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1

    def test_task_agent_colon_syntax(self, tmp_path: Path) -> None:
        """Test Task(agent: "plugin:name") pattern with colon separator detected.

        Tests: TASK_AGENT_PATTERN with colon separator
        How: Write file with Task(agent:) syntax, validate
        Why: Both = and : separators must be handled
        """
        plugins_root = _make_plugins_root(tmp_path)
        body = 'Delegate Task(agent: "missing-plugin:my-agent") here.\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1

    def test_task_agent_valid_resolves(self, tmp_path: Path) -> None:
        """Test Task(agent=) resolves when agent file exists.

        Tests: TASK_AGENT_PATTERN with valid target
        How: Create agent file, write Task(agent=) reference, validate
        Why: Ensure valid Task agent references accepted
        """
        plugins_root = _make_plugins_root(tmp_path)
        target_plugin = _make_plugin_dir(plugins_root, "target-plugin")
        _make_agent(target_plugin, "my-agent")

        body = 'Delegate Task(agent="target-plugin:my-agent") to handle this.\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is True
        assert len(result.errors) == 0


class TestAtAgentPattern:
    """Test @plugin:agent-name prose references."""

    def test_at_agent_pattern_detected(self, tmp_path: Path) -> None:
        """Test @plugin:agent-name pattern detected and validated.

        Tests: AT_AGENT_PATTERN regex detection
        How: Write file with @plugin:agent syntax, validate against missing target
        Why: Ensure @ references are extracted and checked
        """
        plugins_root = _make_plugins_root(tmp_path)
        body = "Use @missing-plugin:my-agent to perform this task.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1

    def test_at_agent_valid_resolves(self, tmp_path: Path) -> None:
        """Test @plugin:agent-name resolves when agent file exists.

        Tests: AT_AGENT_PATTERN with valid target
        How: Create agent, write @-syntax reference, validate
        Why: Ensure valid @-references do not produce errors
        """
        plugins_root = _make_plugins_root(tmp_path)
        target_plugin = _make_plugin_dir(plugins_root, "target-plugin")
        _make_agent(target_plugin, "my-agent")

        body = "Use @target-plugin:my-agent for this task.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_multiple_at_references(self, tmp_path: Path) -> None:
        """Test multiple @plugin:agent references are all validated.

        Tests: Multiple AT_AGENT_PATTERN matches
        How: Write two @-references to missing agents, validate
        Why: All references must be reported, not just first
        """
        plugins_root = _make_plugins_root(tmp_path)
        # Create one plugin dir but no agents in it
        _make_plugin_dir(plugins_root, "plugin-a")
        _make_plugin_dir(plugins_root, "plugin-b")

        body = "Use @plugin-a:agent-one and also @plugin-b:agent-two here.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 2


class TestSlashCommandPattern:
    """Test /plugin:skill-name slash command references."""

    def test_slash_command_pattern_detected(self, tmp_path: Path) -> None:
        """Test /plugin:skill-name pattern detected and validated.

        Tests: SLASH_COMMAND_PATTERN regex detection
        How: Write file with /plugin:name syntax, validate against missing target
        Why: Ensure slash command references are extracted and checked
        """
        plugins_root = _make_plugins_root(tmp_path)
        body = "Run /missing-plugin:my-skill to activate.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1

    def test_slash_command_resolves_via_commands_dir(self, tmp_path: Path) -> None:
        """Test /plugin:name resolves to commands/{name}.md when it exists.

        Tests: Command resolution fallback to commands/ directory
        How: Create commands/name.md, reference via /plugin:name, validate
        Why: _resolve_command_reference checks commands/ as fallback
        """
        plugins_root = _make_plugins_root(tmp_path)
        target_plugin = _make_plugin_dir(plugins_root, "target-plugin")

        commands_dir = target_plugin / "commands"
        commands_dir.mkdir()
        (commands_dir / "my-cmd.md").write_text("---\ndescription: Test command\n---\n\n# Command\n")

        body = "Run /target-plugin:my-cmd to execute.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_slash_in_url_not_matched(self, tmp_path: Path) -> None:
        """Test that slashes in URLs are not treated as slash commands.

        Tests: URL false-positive avoidance
        How: Include http://host:port pattern, verify it is not matched
        Why: _strip_urls_and_code removes URLs before SLASH_COMMAND_PATTERN matching
        """
        plugins_root = _make_plugins_root(tmp_path)
        # URL with colon should not produce a slash-command match
        body = "See https://example.com/path:thing for details.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        # Should not produce NR001 errors from the URL
        assert result.passed is True


class TestBuiltinAgentSkip:
    """Test built-in agent names are not reported as broken references."""

    @pytest.mark.parametrize(
        "builtin_name", ["Explore", "general-purpose", "Plan", "Bash", "context-gathering", "code-review"]
    )
    def test_builtin_agents_skipped_in_at_pattern(self, tmp_path: Path, builtin_name: str) -> None:
        """Test @builtin:name references are skipped without NR001 errors.

        Tests: BUILTIN_AGENTS frozenset filtering
        How: Write @builtin-name:something reference, validate
        Why: Built-in agents are not plugin agents; skipping prevents false positives
        """
        plugins_root = _make_plugins_root(tmp_path)
        body = f"Use @{builtin_name}:something for this.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        # Built-in agents must not produce NR001 errors
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) == 0

    @pytest.mark.parametrize("builtin_name", ["Explore", "general-purpose", "context-gathering", "code-review"])
    def test_builtin_agents_skipped_in_task_agent_pattern(self, tmp_path: Path, builtin_name: str) -> None:
        """Test Task(agent="builtin:name") references are skipped.

        Tests: BUILTIN_AGENTS check inside agent ref_type handling
        How: Write Task(agent="builtin:name") reference, validate
        Why: BUILTIN_AGENTS check applies to both plugin and name fields
        """
        plugins_root = _make_plugins_root(tmp_path)
        body = f'Delegate Task(agent="{builtin_name}:worker") to handle.\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) == 0

    def test_non_builtin_agent_not_skipped(self, tmp_path: Path) -> None:
        """Test non-built-in agents are not skipped and produce NR001 when missing.

        Tests: BUILTIN_AGENTS does not suppress real plugin references
        How: Write @custom-plugin:agent reference, validate without creating target
        Why: Only built-in agents should be exempt
        """
        plugins_root = _make_plugins_root(tmp_path)
        body = "Use @custom-plugin:my-agent for this task.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1


class TestMissingPluginDirectory:
    """Test NR001 errors when the plugin directory itself is missing."""

    def test_missing_plugin_directory_produces_nr001(self, tmp_path: Path) -> None:
        """Test NR001 error when referenced plugin directory does not exist.

        Tests: Plugin directory existence check
        How: Write reference to non-existent plugin directory, validate
        Why: NR001 produced when plugin_dir / plugin is not a directory
        """
        plugins_root = _make_plugins_root(tmp_path)
        # No plugin directory created -- only the source
        body = 'Invoke Skill(command: "nonexistent-plugin:my-skill").\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1
        # Error message should mention the plugin directory
        assert any("nonexistent-plugin" in e.message for e in nr001_errors)

    def test_missing_plugin_directory_suggestion_present(self, tmp_path: Path) -> None:
        """Test NR001 error includes suggestion for missing plugin directory.

        Tests: Suggestion field populated for missing plugin directory
        How: Validate file with missing plugin reference
        Why: Suggestion guides user to create the plugin or fix the prefix
        """
        plugins_root = _make_plugins_root(tmp_path)
        body = 'Invoke Skill(command: "ghost-plugin:skill").\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1
        assert all(e.suggestion is not None for e in nr001_errors)


class TestBrokenReference:
    """Test NR001 errors when plugin directory exists but referenced file is missing."""

    def test_skill_file_missing_in_existing_plugin(self, tmp_path: Path) -> None:
        """Test NR001 when plugin exists but referenced skill SKILL.md is absent.

        Tests: Skill file existence check inside existing plugin
        How: Create plugin dir without skills/, reference missing skill
        Why: NR001 produced when skill SKILL.md does not exist
        """
        plugins_root = _make_plugins_root(tmp_path)
        # Plugin directory exists but no skills inside
        _make_plugin_dir(plugins_root, "target-plugin")

        body = 'Invoke Skill(command: "target-plugin:missing-skill").\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1

    def test_agent_file_missing_in_existing_plugin(self, tmp_path: Path) -> None:
        """Test NR001 when plugin exists but referenced agent .md is absent.

        Tests: Agent file existence check inside existing plugin
        How: Create plugin dir with agents/ but no matching agent file
        Why: NR001 produced when agents/{name}.md does not exist
        """
        plugins_root = _make_plugins_root(tmp_path)
        target_plugin = _make_plugin_dir(plugins_root, "target-plugin")
        # Create agents dir but leave it empty
        (target_plugin / "agents").mkdir()

        body = "Use @target-plugin:missing-agent to handle this.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1

    def test_broken_reference_has_suggestion(self, tmp_path: Path) -> None:
        """Test NR001 for broken references includes expected path in suggestion.

        Tests: Suggestion populated for broken reference (not missing directory)
        How: Create plugin dir, reference missing skill, check suggestion
        Why: Suggestion should show expected file path to help user
        """
        plugins_root = _make_plugins_root(tmp_path)
        _make_plugin_dir(plugins_root, "target-plugin")

        body = 'Activate Skill(command: "target-plugin:ghost-skill").\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1
        assert all(e.suggestion is not None for e in nr001_errors)

    def test_broken_skill_suggestion_uses_category_placeholder_not_wildcard(self, tmp_path: Path) -> None:
        """Test NR001 suggestion for broken skill ref uses {category} not */ wildcard.

        Tests: Error message clarity — no glob wildcards in user-facing strings
        How: Break a skill reference, inspect the suggestion text
        Why: Suggestion must show concrete placeholder paths, not shell globs
        """
        plugins_root = _make_plugins_root(tmp_path)
        _make_plugin_dir(plugins_root, "target-plugin")

        body = 'Activate Skill(command: "target-plugin:missing-skill").\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is False
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) >= 1
        # Suggestion must not contain shell glob wildcard (*/)
        for err in nr001_errors:
            if err.suggestion:
                assert "*/" not in err.suggestion, f"Suggestion contains shell glob wildcard '*/': {err.suggestion!r}"
            # Suggestion should use {category} placeholder for nested paths
            if err.suggestion and "or" in err.suggestion:
                assert "{category}" in err.suggestion, (
                    f"Expected '{{category}}' placeholder in multi-path suggestion: {err.suggestion!r}"
                )


class TestEdgeCases:
    """Test edge cases: no body, no frontmatter, frontmatter-only, template placeholders."""

    def test_file_with_no_body_passes(self, tmp_path: Path) -> None:
        """Test file with frontmatter only (empty body) passes validation.

        Tests: Empty body handling
        How: Create file with only frontmatter delimiters, validate
        Why: No body means no references to check -- result should pass
        """
        plugins_root = _make_plugins_root(tmp_path)
        plugin_dir = plugins_root / "source-plugin"
        plugin_dir.mkdir()
        skill_dir = plugin_dir / "skills" / "source-skill"
        skill_dir.mkdir(parents=True)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("---\ndescription: Minimal\n---\n")

        validator = NamespaceReferenceValidator()
        result = validator.validate(skill_md)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_file_without_frontmatter_scanned_as_body(self, tmp_path: Path) -> None:
        """Test file without frontmatter treats entire content as body.

        Tests: No-frontmatter handling (_extract_body returns full content)
        How: Create file without --- delimiters, include valid reference, validate
        Why: Files without frontmatter should still be scanned for references
        """
        plugins_root = _make_plugins_root(tmp_path)
        target_plugin = _make_plugin_dir(plugins_root, "target-plugin")
        _make_skill(target_plugin, "my-skill")

        plugin_dir = plugins_root / "source-plugin"
        plugin_dir.mkdir()
        skill_dir = plugin_dir / "skills" / "source-skill"
        skill_dir.mkdir(parents=True)
        skill_md = skill_dir / "SKILL.md"
        # No frontmatter -- entire content is treated as body
        skill_md.write_text('No frontmatter here. Skill(command: "target-plugin:my-skill").\n')

        validator = NamespaceReferenceValidator()
        result = validator.validate(skill_md)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_template_placeholder_references_skipped(self, tmp_path: Path) -> None:
        """Test references containing { or } placeholders are skipped.

        Tests: Template placeholder filtering
        How: Write Skill(command: "{plugin}:name"), validate
        Why: Placeholders indicate template text, not real references
        """
        plugins_root = _make_plugins_root(tmp_path)
        body = 'Use Skill(command: "{plugin-name}:my-skill") as template.\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        # Template references must not produce NR001 errors
        nr001_errors = [e for e in result.errors if e.code == "NR001"]
        assert len(nr001_errors) == 0

    def test_file_outside_plugins_tree_skips_validation(self, tmp_path: Path) -> None:
        """Test file not inside a plugins/ directory skips validation.

        Tests: plugins root detection (_find_plugins_root)
        How: Create SKILL.md outside any plugins/ directory, validate
        Why: Validator skips when not inside plugins directory structure
        """
        # No plugins/ directory anywhere -- just a bare tmp_path SKILL.md
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\ndescription: Orphan skill\n---\n\n@some-plugin:some-agent usage here.\n")

        validator = NamespaceReferenceValidator()
        result = validator.validate(skill_md)

        # Should pass because file is not inside plugins/ tree
        assert result.passed is True


class TestNR001NamespaceFromPluginJson:
    """Test NR001 uses plugin.json 'name' field -- not directory name -- as namespace.

    Bug: The current implementation derives the plugin namespace from the
    directory name on disk (``plugins_root / plugin``).  The correct behavior
    is to read the ``"name"`` field from ``.claude-plugin/plugin.json`` (or
    ``plugin.json`` at the plugin root) and match namespace references against
    that value.

    When the directory name differs from the ``"name"`` field, NR001 fires
    incorrectly because it cannot find a directory whose name matches the
    namespace prefix in the reference.
    """

    @staticmethod
    def _make_plugin_with_json_name(plugins_root: Path, dir_name: str, json_name: str) -> Path:
        """Create a plugin whose directory name differs from its plugin.json name.

        Args:
            plugins_root: The ``plugins/`` directory
            dir_name: Name of the directory on disk
            json_name: Value of the ``"name"`` field in plugin.json

        Returns:
            Path to the plugin directory
        """
        import json as _json

        plugin_dir = plugins_root / dir_name
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # .claude-plugin/plugin.json is the canonical location
        claude_plugin_dir = plugin_dir / ".claude-plugin"
        claude_plugin_dir.mkdir(exist_ok=True)
        plugin_json = claude_plugin_dir / "plugin.json"
        plugin_json.write_text(_json.dumps({"name": json_name}))

        return plugin_dir

    def test_skill_reference_uses_plugin_json_name_not_dir_name(self, tmp_path: Path) -> None:
        """NR001 must resolve namespace via plugin.json name, not directory name.

        Tests: NR001 namespace derivation for skill references
        How: Create plugin directory ``my-plugin-dir`` with plugin.json
             ``{"name": "my-actual-plugin"}``, create a skill inside it,
             then reference it as ``Skill(command: "my-actual-plugin:my-skill")``.
             The validator should find the skill because the namespace
             ``my-actual-plugin`` maps to the directory via plugin.json.
        Why: The namespace in references must match the plugin.json name field,
             not the on-disk directory name.  Directory names are an
             implementation detail; plugin.json is the source of truth.

        Expected: PASS (no NR001 errors)
        Current (buggy): FAIL (NR001 fires because no directory named
        ``my-actual-plugin`` exists -- only ``my-plugin-dir`` exists)
        """
        plugins_root = _make_plugins_root(tmp_path)

        # Directory name != plugin.json name
        plugin_dir = self._make_plugin_with_json_name(
            plugins_root, dir_name="my-plugin-dir", json_name="my-actual-plugin"
        )

        # Create a valid skill inside this plugin
        _make_skill(plugin_dir, "my-skill")

        # Source file references the plugin by its plugin.json name
        body = 'Invoke Skill(command: "my-actual-plugin:my-skill") here.\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        # Arrange complete -- Act
        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        # Assert: the reference should resolve successfully
        assert result.passed is True, (
            f"NR001 incorrectly fired.  The validator used the directory name "
            f"'my-plugin-dir' instead of the plugin.json name 'my-actual-plugin' "
            f"as the namespace.  Errors: {[e.message for e in result.errors]}"
        )
        assert len(result.errors) == 0

    def test_agent_reference_uses_plugin_json_name_not_dir_name(self, tmp_path: Path) -> None:
        """NR001 must resolve namespace via plugin.json name for agent references.

        Tests: NR001 namespace derivation for agent references
        How: Create plugin directory ``agent-plugin-dir`` with plugin.json
             ``{"name": "agent-plugin"}``, create an agent inside it,
             then reference it as ``@agent-plugin:my-agent``.
        Why: Agent references use the same namespace resolution as skills.

        Expected: PASS (no NR001 errors)
        Current (buggy): FAIL (NR001 fires -- directory ``agent-plugin``
        does not exist)
        """
        plugins_root = _make_plugins_root(tmp_path)

        plugin_dir = self._make_plugin_with_json_name(
            plugins_root, dir_name="agent-plugin-dir", json_name="agent-plugin"
        )

        _make_agent(plugin_dir, "my-agent")

        body = "Delegate to @agent-plugin:my-agent for this task.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is True, (
            f"NR001 incorrectly fired for agent reference.  The validator used "
            f"the directory name 'agent-plugin-dir' instead of the plugin.json "
            f"name 'agent-plugin'.  Errors: {[e.message for e in result.errors]}"
        )
        assert len(result.errors) == 0

    def test_slash_command_reference_uses_plugin_json_name_not_dir_name(self, tmp_path: Path) -> None:
        """NR001 must resolve namespace via plugin.json name for slash commands.

        Tests: NR001 namespace derivation for slash command references
        How: Create plugin directory ``cmd-plugin-dir`` with plugin.json
             ``{"name": "cmd-plugin"}``, create a skill inside it,
             then reference it as ``/cmd-plugin:my-skill``.
        Why: Slash command references use the same namespace resolution.

        Expected: PASS (no NR001 errors)
        Current (buggy): FAIL (NR001 fires)
        """
        plugins_root = _make_plugins_root(tmp_path)

        plugin_dir = self._make_plugin_with_json_name(plugins_root, dir_name="cmd-plugin-dir", json_name="cmd-plugin")

        _make_skill(plugin_dir, "my-skill")

        body = "Run /cmd-plugin:my-skill to activate.\n"
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is True, (
            f"NR001 incorrectly fired for slash command reference.  The validator "
            f"used the directory name 'cmd-plugin-dir' instead of the plugin.json "
            f"name 'cmd-plugin'.  Errors: {[e.message for e in result.errors]}"
        )
        assert len(result.errors) == 0

    def test_dir_name_reference_still_works_when_matching_json_name(self, tmp_path: Path) -> None:
        """When directory name equals plugin.json name, references still resolve.

        Tests: Backward compatibility -- matching names still work
        How: Create plugin where dir name == plugin.json name, validate reference
        Why: Regression guard -- the fix must not break the common case where
             directory name and plugin.json name are identical.

        Expected: PASS (always -- this is the common case)
        """
        plugins_root = _make_plugins_root(tmp_path)

        plugin_dir = self._make_plugin_with_json_name(
            plugins_root, dir_name="same-name-plugin", json_name="same-name-plugin"
        )

        _make_skill(plugin_dir, "my-skill")

        body = 'Invoke Skill(command: "same-name-plugin:my-skill") here.\n'
        source_skill = _make_skill_md_with_body(plugins_root, "source-plugin", body)

        validator = NamespaceReferenceValidator()
        result = validator.validate(source_skill)

        assert result.passed is True
        assert len(result.errors) == 0
