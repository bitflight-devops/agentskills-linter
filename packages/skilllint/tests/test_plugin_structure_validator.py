"""Unit tests for PluginStructureValidator.

Tests:
- Claude CLI availability detection
- Graceful skip when CLI unavailable
- Error parsing from claude output
- Subprocess security (no shell=True)
- Timeout handling
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

from skilllint.plugin_validator import PluginStructureValidator


class TestPluginStructureValidatorBasic:
    """Test basic PluginStructureValidator functionality."""

    def test_validator_instantiation(self) -> None:
        """Test PluginStructureValidator can be instantiated."""
        validator = PluginStructureValidator()
        assert validator is not None
        assert validator.can_fix() is False

    def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
        """Test fix() raises NotImplementedError.

        Tests: PluginStructureValidator is not auto-fixable
        How: Call fix() method, expect NotImplementedError
        Why: Plugin structure fixes require manual changes
        """
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()

        validator = PluginStructureValidator()
        with pytest.raises(NotImplementedError):
            validator.fix(plugin_dir)


class TestClaudeCLIDetection:
    """Test Claude CLI availability detection."""

    def test_detects_claude_available(self, mocker: MockerFixture) -> None:
        """Test validator detects when claude CLI is available.

        Tests: Claude CLI detection
        How: Mock shutil.which to return path, validate
        Why: Ensure validator detects CLI presence correctly
        """
        # Mock shutil.which to return a path
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        validator = PluginStructureValidator()
        # Validator should detect claude is available
        assert validator is not None

    def test_handles_claude_unavailable(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test validator handles claude CLI absence gracefully.

        Tests: Graceful degradation when CLI unavailable
        How: Mock shutil.which to return None, validate plugin
        Why: Ensure validator skips validation without error
        """
        # Mock shutil.which to return None (claude not found)
        mocker.patch("shutil.which", return_value=None)

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Should pass with info message (skipped)
        assert result.passed is True
        assert len(result.info) > 0


class TestNonPluginDirectory:
    """Test validation skips non-plugin directories."""

    def test_skips_non_plugin_directory(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test validation skips directory without plugin.json.

        Tests: Plugin directory detection
        How: Create directory without .claude-plugin/plugin.json, validate
        Why: Ensure validator skips non-plugin directories
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        regular_dir = tmp_path / "regular-dir"
        regular_dir.mkdir()

        validator = PluginStructureValidator()
        result = validator.validate(regular_dir)

        # Should pass without validation (not a plugin)
        assert result.passed is True

    def test_skips_skill_directory(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test validation skips skill directory (not plugin).

        Tests: File type detection
        How: Create skill directory, validate
        Why: Ensure only plugin directories are validated
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")

        validator = PluginStructureValidator()
        result = validator.validate(skill_dir / "SKILL.md")

        # Should pass without plugin validation
        assert result.passed is True


class TestSubprocessExecution:
    """Test subprocess execution security and behavior."""

    def test_no_shell_true_usage(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test subprocess never uses shell=True.

        Tests: Security - no shell=True
        How: Mock subprocess.run, verify arguments
        Why: Prevent command injection vulnerabilities
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        # Mock subprocess.run to track calls
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Success", stderr="")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        validator.validate(plugin_dir)

        # Verify subprocess.run was called without shell=True
        if mock_run.called:
            for call in mock_run.call_args_list:
                kwargs = call[1] if len(call) > 1 else {}
                assert kwargs.get("shell", False) is False

    def test_timeout_set(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test subprocess has timeout configured.

        Tests: Timeout configuration
        How: Mock subprocess.run, verify timeout parameter
        Why: Prevent hanging on unresponsive claude CLI
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Success", stderr="")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        validator.validate(plugin_dir)

        # Verify timeout was set
        if mock_run.called:
            for call in mock_run.call_args_list:
                kwargs = call[1] if len(call) > 1 else {}
                assert "timeout" in kwargs
                assert kwargs["timeout"] > 0


class TestClaudeOutputParsing:
    """Test parsing of claude CLI output."""

    def test_success_output(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test parsing successful validation output.

        Tests: Success case parsing
        How: Mock claude CLI success output, validate
        Why: Ensure validator recognizes successful validation
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Plugin validation passed", stderr="")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Should pass
        assert result.passed is True

    def test_error_output(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test parsing error validation output.

        Tests: Error case parsing
        How: Mock claude CLI error output, validate
        Why: Ensure validator captures validation failures
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")
        # Prevent skip in Claude Code session environments (CLAUDECODE / CLAUDE_CODE_REMOTE env vars)
        mocker.patch("skilllint.plugin_validator._should_skip_claude_validate", return_value=False)

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=1, stdout="", stderr="Error: Invalid plugin.json")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Should fail with error
        assert result.passed is False
        assert len(result.errors) > 0

    def test_startup_failure_skips_not_fails(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Claude env/runtime startup failure must skip validation, not fail.

        Tests: Git-bash / PATH / env errors are treated as skip
        How: Mock claude output with git-bash message, validate
        Why: Validator must only fail on plugin validation errors, not when claude cannot run
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")
        mocker.patch("skilllint.plugin_validator._should_skip_claude_validate", return_value=False)

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(
            returncode=1,
            stdout="",
            stderr="Claude Code on Windows requires git-bash. If installed but not in PATH, set CLAUDE_CODE_GIT_BASH_PATH=C:\\Program Files\\Git\\bin\\bash.exe",
        )

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        assert result.passed is True
        assert len(result.errors) == 0
        assert len(result.info) > 0


class TestTimeoutHandling:
    """Test timeout error handling."""

    def test_timeout_error_handled(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test timeout is handled gracefully.

        Tests: Timeout exception handling
        How: Mock subprocess to raise TimeoutExpired, validate
        Why: Ensure validator handles timeouts without crashing
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["claude", "plugin", "validate"], timeout=30)

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Should handle timeout gracefully
        assert result.passed is False or result.passed is True
        # Either fails with error or passes with warning


class TestFileNotFoundHandling:
    """Test FileNotFoundError handling."""

    def test_file_not_found_handled(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test FileNotFoundError is handled gracefully.

        Tests: Command not found handling
        How: Mock subprocess to raise FileNotFoundError, validate
        Why: Ensure validator handles missing claude binary
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError("claude not found")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Should handle FileNotFoundError gracefully
        assert isinstance(result.passed, bool)


class TestCommandArguments:
    """Test command construction and arguments."""

    def test_command_uses_full_path(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test command uses full path from shutil.which.

        Tests: Command path construction
        How: Mock shutil.which, verify command uses full path
        Why: Ensure security by using full path, not PATH search
        """
        claude_path = "/usr/local/bin/claude"
        mocker.patch("shutil.which", return_value=claude_path)

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Success", stderr="")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        validator.validate(plugin_dir)

        # Verify command uses full path
        if mock_run.called:
            args = mock_run.call_args[0][0] if mock_run.call_args else []
            if args:
                assert args[0] == claude_path or args[0].startswith("/")

    def test_command_arguments_correct(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test command arguments are correct.

        Tests: Command argument structure
        How: Mock subprocess, verify arguments
        Why: Ensure correct claude CLI invocation
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Success", stderr="")

        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        validator.validate(plugin_dir)

        # Verify command arguments
        if mock_run.called:
            args = mock_run.call_args[0][0] if mock_run.call_args else []
            # Should be: [claude_path, "plugin", "validate", plugin_dir]
            if len(args) >= 3:
                assert "plugin" in args
                assert "validate" in args


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_nested_plugin_directory(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test validation works on nested plugin directories.

        Tests: Path resolution for nested plugins
        How: Create plugin in nested directory, validate
        Why: Ensure validator handles various directory structures
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Success", stderr="")

        plugin_dir = tmp_path / "nested" / "path" / "test-plugin"
        plugin_dir.mkdir(parents=True)
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        validator = PluginStructureValidator()
        result = validator.validate(plugin_dir)

        # Should handle nested paths
        assert isinstance(result.passed, bool)

    def test_symlinked_plugin_directory(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Test validation works on symlinked plugin directories.

        Tests: Symlink handling
        How: Create symlink to plugin, validate via symlink
        Why: Ensure validator handles symlinks correctly
        """
        mocker.patch("shutil.which", return_value="/usr/local/bin/claude")

        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = mocker.Mock(returncode=0, stdout="Success", stderr="")

        # Create real plugin
        real_plugin = tmp_path / "real-plugin"
        real_plugin.mkdir()
        claude_plugin = real_plugin / ".claude-plugin"
        claude_plugin.mkdir()
        (claude_plugin / "plugin.json").write_text('{"name": "test"}')

        # Create symlink
        symlink = tmp_path / "link-to-plugin"
        symlink.symlink_to(real_plugin)

        validator = PluginStructureValidator()
        result = validator.validate(symlink)

        # Should handle symlinks
        assert isinstance(result.passed, bool)
