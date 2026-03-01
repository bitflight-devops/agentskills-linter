"""Integration tests for external tool integration layer.

Tests Claude CLI detection, subprocess security, timeout handling, and git integration
WITHOUT mocking the actual Claude CLI - tests the integration layer implementation.

Architecture: Task T17 (lines 1882-1958 of plugin-validator-tasks.md)
Implementation: plugin_validator.py lines 1936-2074
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Import from plugin_validator module (loaded by conftest.py)
from plugin_validator import CLAUDE_TIMEOUT, get_staged_files, is_claude_available, validate_with_claude

# ============================================================================
# Claude CLI Detection Tests
# ============================================================================


def test_is_claude_available_when_installed(mocker: MockerFixture) -> None:
    """Test is_claude_available returns True when claude CLI is in PATH.

    Tests: Claude CLI detection using shutil.which()
    How: Mock shutil.which to return a path
    Why: Verify detection works without requiring actual claude installation
    """
    # Arrange: Mock shutil.which to return a claude path
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")

    # Act: Check availability
    result = is_claude_available()

    # Assert: Returns True when claude found
    assert result is True


def test_is_claude_available_when_not_installed(mocker: MockerFixture) -> None:
    """Test is_claude_available returns False when claude CLI not in PATH.

    Tests: Claude CLI detection returns False when missing
    How: Mock shutil.which to return None
    Why: Verify graceful degradation when claude not installed
    """
    # Arrange: Mock shutil.which to return None (not found)
    mocker.patch("plugin_validator.shutil.which", return_value=None)

    # Act: Check availability
    result = is_claude_available()

    # Assert: Returns False when claude not found
    assert result is False


# ============================================================================
# Claude CLI Validation Tests
# ============================================================================


def test_validate_with_claude_when_not_available(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude skips gracefully when claude not available.

    Tests: Graceful degradation when claude CLI missing
    How: Mock shutil.which to return None, call validate_with_claude
    Why: Ensure validation doesn't fail when claude absent
    """
    # Arrange: Mock claude as unavailable
    mocker.patch("plugin_validator.shutil.which", return_value=None)

    # Act: Attempt validation
    success, output = validate_with_claude(sample_plugin_dir)

    # Assert: Returns success with skip message
    assert success is True
    assert "claude CLI not available" in output
    assert "skipped" in output.lower()


def test_validate_with_claude_when_not_plugin_directory(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test validate_with_claude skips when directory is not a plugin.

    Tests: Validation skips non-plugin directories
    How: Mock claude available but use directory without plugin.json
    Why: Ensure validator only runs on plugin directories
    """
    # Arrange: Mock claude available but use non-plugin directory
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")

    # Act: Attempt validation on non-plugin directory
    success, output = validate_with_claude(tmp_path)

    # Assert: Returns success with skip message
    assert success is True
    assert "Not a plugin directory" in output
    assert "skipped" in output.lower()


def test_validate_with_claude_success(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude returns success when validation passes.

    Tests: Successful claude plugin validation
    How: Mock subprocess.run to return exit code 0
    Why: Verify success path returns correct status and output
    """
    # Arrange: Mock claude available and successful validation
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="Plugin validation passed", stderr="")

    # Act: Validate plugin
    success, output = validate_with_claude(sample_plugin_dir)

    # Assert: Returns success with stdout
    assert success is True
    assert "Plugin validation passed" in output

    # Verify subprocess called correctly
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert call_args[0] == "/usr/local/bin/claude"
    assert call_args[1] == "plugin"
    assert call_args[2] == "validate"
    assert call_args[3] == str(sample_plugin_dir)


def test_validate_with_claude_failure(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude returns failure when validation fails.

    Tests: Failed claude plugin validation
    How: Mock subprocess.run to return non-zero exit code
    Why: Verify failure path returns correct status and error details
    """
    # Arrange: Mock claude available but validation fails
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=1, stdout="Validation output", stderr="Error: Invalid plugin.json")

    # Act: Validate plugin
    success, output = validate_with_claude(sample_plugin_dir)

    # Assert: Returns failure with stderr + stdout
    assert success is False
    assert "Error: Invalid plugin.json" in output
    assert "Validation output" in output


def test_validate_with_claude_timeout(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude handles timeout gracefully.

    Tests: Timeout handling for claude CLI
    How: Mock subprocess.run to raise TimeoutExpired
    Why: Verify timeout doesn't crash, returns meaningful error
    """
    # Arrange: Mock claude available but times out
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["claude", "plugin", "validate"], timeout=CLAUDE_TIMEOUT)

    # Act: Validate plugin
    success, output = validate_with_claude(sample_plugin_dir)

    # Assert: Returns failure with timeout message
    assert success is False
    assert "timed out" in output.lower()
    assert str(CLAUDE_TIMEOUT) in output


def test_validate_with_claude_file_not_found(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude handles FileNotFoundError gracefully.

    Tests: Handling when claude executable not found despite shutil.which
    How: Mock subprocess.run to raise FileNotFoundError
    Why: Verify edge case where claude path becomes invalid between check and execution
    """
    # Arrange: Mock claude available but subprocess fails with FileNotFoundError
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.side_effect = FileNotFoundError("claude not found")

    # Act: Validate plugin
    success, output = validate_with_claude(sample_plugin_dir)

    # Assert: Returns success (skip) with message
    assert success is True
    assert "Claude CLI not found in PATH" in output
    assert "skipped" in output.lower()


def test_validate_with_claude_os_error(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude handles OSError gracefully.

    Tests: Handling general subprocess errors (permission denied, etc.)
    How: Mock subprocess.run to raise OSError
    Why: Verify non-timeout subprocess failures return meaningful errors
    """
    # Arrange: Mock claude available but subprocess fails with OSError
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.side_effect = OSError("Permission denied")

    # Act: Validate plugin
    success, output = validate_with_claude(sample_plugin_dir)

    # Assert: Returns failure with error message
    assert success is False
    assert "Failed to run claude plugin validate" in output
    assert "Permission denied" in output


# ============================================================================
# Subprocess Security Tests
# ============================================================================


def test_validate_with_claude_no_shell_true(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude never uses shell=True.

    Tests: Subprocess security - no shell injection risk
    How: Mock subprocess.run, verify shell parameter
    Why: Security requirement - shell=True enables command injection
    """
    # Arrange: Mock claude available
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="OK", stderr="")

    # Act: Validate plugin
    validate_with_claude(sample_plugin_dir)

    # Assert: subprocess.run called without shell=True
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args[1]
    # shell parameter should be absent (defaults to False)
    assert "shell" not in call_kwargs or call_kwargs["shell"] is False


def test_validate_with_claude_uses_list_arguments(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude passes command as list, not string.

    Tests: Subprocess security - list arguments prevent shell injection
    How: Mock subprocess.run, verify first argument is list
    Why: Security requirement - list arguments are safer than shell strings
    """
    # Arrange: Mock claude available
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="OK", stderr="")

    # Act: Validate plugin
    validate_with_claude(sample_plugin_dir)

    # Assert: First argument is list, not string
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert isinstance(call_args, list), "Command must be list, not string"
    assert len(call_args) == 4  # [claude_path, "plugin", "validate", plugin_dir]


def test_validate_with_claude_uses_full_path(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude uses full path from shutil.which.

    Tests: Subprocess security - uses full command path
    How: Mock shutil.which, verify subprocess.run uses returned path
    Why: Security requirement - prevents PATH manipulation attacks
    """
    # Arrange: Mock claude at specific path
    claude_path = "/opt/custom/bin/claude"
    mocker.patch("plugin_validator.shutil.which", return_value=claude_path)
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="OK", stderr="")

    # Act: Validate plugin
    validate_with_claude(sample_plugin_dir)

    # Assert: Uses full path from shutil.which
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert call_args[0] == claude_path


def test_validate_with_claude_sets_timeout(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude sets timeout parameter.

    Tests: Subprocess timeout configuration
    How: Mock subprocess.run, verify timeout parameter set
    Why: Prevent hanging on stuck commands
    """
    # Arrange: Mock claude available
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="OK", stderr="")

    # Act: Validate plugin
    validate_with_claude(sample_plugin_dir)

    # Assert: Timeout parameter set to CLAUDE_TIMEOUT
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args[1]
    assert "timeout" in call_kwargs
    assert call_kwargs["timeout"] == CLAUDE_TIMEOUT


# ============================================================================
# Git Integration Tests
# ============================================================================


def test_get_staged_files_when_git_not_available(mocker: MockerFixture) -> None:
    """Test get_staged_files returns empty list when git not available.

    Tests: Git detection using shutil.which
    How: Mock shutil.which to return None
    Why: Verify graceful degradation when git not installed
    """
    # Arrange: Mock git as unavailable
    mocker.patch("plugin_validator.shutil.which", return_value=None)

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns empty list
    assert result == []


def test_get_staged_files_when_not_git_repo(mocker: MockerFixture) -> None:
    """Test get_staged_files returns empty list when not in git repo.

    Tests: Handling non-git directories
    How: Mock subprocess.run to return non-zero exit code
    Why: Verify no crash when running outside git repository
    """
    # Arrange: Mock git available but not in repo
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/bin/git")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=128, stdout="", stderr="Not a git repository")

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns empty list
    assert result == []


def test_get_staged_files_with_staged_files(mocker: MockerFixture) -> None:
    """Test get_staged_files returns Path objects for staged files.

    Tests: Git diff parsing for staged files
    How: Mock subprocess.run to return file list
    Why: Verify correct parsing of git diff output
    """
    # Arrange: Mock git available with staged files
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/bin/git")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(
        returncode=0, stdout="plugins/plugin-creator/SKILL.md\nplugins/test/agent.md\n", stderr=""
    )

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns list of Path objects
    assert len(result) == 2
    assert all(isinstance(p, Path) for p in result)
    assert result[0] == Path("plugins/plugin-creator/SKILL.md")
    assert result[1] == Path("plugins/test/agent.md")


def test_get_staged_files_with_no_staged_files(mocker: MockerFixture) -> None:
    """Test get_staged_files returns empty list when no files staged.

    Tests: Empty git diff output handling
    How: Mock subprocess.run to return empty stdout
    Why: Verify correct handling of empty diff output
    """
    # Arrange: Mock git available but no staged files
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/bin/git")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="", stderr="")

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns empty list
    assert result == []


def test_get_staged_files_timeout(mocker: MockerFixture) -> None:
    """Test get_staged_files handles timeout gracefully.

    Tests: Timeout handling for git diff
    How: Mock subprocess.run to raise TimeoutExpired
    Why: Verify timeout doesn't crash, returns empty list
    """
    # Arrange: Mock git available but times out
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/bin/git")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["git", "diff", "--cached", "--name-only"], timeout=10)

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns empty list (graceful degradation)
    assert result == []


def test_get_staged_files_file_not_found(mocker: MockerFixture) -> None:
    """Test get_staged_files handles FileNotFoundError gracefully.

    Tests: Handling when git executable not found despite shutil.which
    How: Mock subprocess.run to raise FileNotFoundError
    Why: Verify edge case where git path becomes invalid
    """
    # Arrange: Mock git available but subprocess fails
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/bin/git")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.side_effect = FileNotFoundError("git not found")

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns empty list (graceful degradation)
    assert result == []


def test_get_staged_files_os_error(mocker: MockerFixture) -> None:
    """Test get_staged_files handles OSError gracefully.

    Tests: Handling general subprocess errors
    How: Mock subprocess.run to raise OSError
    Why: Verify non-timeout subprocess failures handled gracefully
    """
    # Arrange: Mock git available but subprocess fails
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/bin/git")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.side_effect = OSError("Permission denied")

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns empty list (graceful degradation)
    assert result == []


def test_get_staged_files_no_shell_true(mocker: MockerFixture) -> None:
    """Test get_staged_files never uses shell=True.

    Tests: Subprocess security - no shell injection risk
    How: Mock subprocess.run, verify shell parameter
    Why: Security requirement - shell=True enables command injection
    """
    # Arrange: Mock git available
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/bin/git")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="", stderr="")

    # Act: Get staged files
    get_staged_files()

    # Assert: subprocess.run called without shell=True
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args[1]
    # shell parameter should be absent (defaults to False)
    assert "shell" not in call_kwargs or call_kwargs["shell"] is False


def test_get_staged_files_uses_list_arguments(mocker: MockerFixture) -> None:
    """Test get_staged_files passes command as list, not string.

    Tests: Subprocess security - list arguments prevent shell injection
    How: Mock subprocess.run, verify first argument is list
    Why: Security requirement - list arguments are safer than shell strings
    """
    # Arrange: Mock git available
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/bin/git")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="", stderr="")

    # Act: Get staged files
    get_staged_files()

    # Assert: First argument is list, not string
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert isinstance(call_args, list), "Command must be list, not string"
    assert len(call_args) == 4  # [git_path, "diff", "--cached", "--name-only"]


def test_get_staged_files_uses_full_path(mocker: MockerFixture) -> None:
    """Test get_staged_files uses full path from shutil.which.

    Tests: Subprocess security - uses full command path
    How: Mock shutil.which, verify subprocess.run uses returned path
    Why: Security requirement - prevents PATH manipulation attacks
    """
    # Arrange: Mock git at specific path
    git_path = "/opt/custom/bin/git"
    mocker.patch("plugin_validator.shutil.which", return_value=git_path)
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="", stderr="")

    # Act: Get staged files
    get_staged_files()

    # Assert: Uses full path from shutil.which
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert call_args[0] == git_path


def test_get_staged_files_sets_timeout(mocker: MockerFixture) -> None:
    """Test get_staged_files sets timeout parameter.

    Tests: Subprocess timeout configuration
    How: Mock subprocess.run, verify timeout parameter set
    Why: Prevent hanging on stuck git commands
    """
    # Arrange: Mock git available
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/bin/git")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="", stderr="")

    # Act: Get staged files
    get_staged_files()

    # Assert: Timeout parameter set to 10 seconds
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args[1]
    assert "timeout" in call_kwargs
    assert call_kwargs["timeout"] == 10


def test_get_staged_files_filters_empty_lines(mocker: MockerFixture) -> None:
    """Test get_staged_files filters out empty lines from git output.

    Tests: Empty line filtering in git diff output
    How: Mock subprocess.run to return output with empty lines
    Why: Verify only actual file paths returned, not empty strings
    """
    # Arrange: Mock git with empty lines in output
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/bin/git")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(
        returncode=0, stdout="\nplugins/test/file1.md\n\n\nplugins/test/file2.md\n\n", stderr=""
    )

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Only non-empty paths returned
    assert len(result) == 2
    assert result[0] == Path("plugins/test/file1.md")
    assert result[1] == Path("plugins/test/file2.md")


# ============================================================================
# Exit Code Mapping Tests
# ============================================================================


def test_validate_with_claude_maps_zero_exit_to_success(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude maps exit code 0 to success=True.

    Tests: Exit code mapping for success
    How: Mock subprocess.run with returncode=0
    Why: Verify correct success status from exit code
    """
    # Arrange: Mock claude with exit code 0
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="OK", stderr="")

    # Act: Validate plugin
    success, _ = validate_with_claude(sample_plugin_dir)

    # Assert: Maps to success=True
    assert success is True


def test_validate_with_claude_maps_nonzero_exit_to_failure(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude maps non-zero exit code to success=False.

    Tests: Exit code mapping for failure
    How: Mock subprocess.run with returncode=1
    Why: Verify correct failure status from exit code
    """
    # Arrange: Mock claude with exit code 1
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=1, stdout="", stderr="Error")

    # Act: Validate plugin
    success, _ = validate_with_claude(sample_plugin_dir)

    # Assert: Maps to success=False
    assert success is False


def test_validate_with_claude_includes_stdout_on_success(mocker: MockerFixture, sample_plugin_dir: Path) -> None:
    """Test validate_with_claude includes stdout in output on success.

    Tests: Output content on success
    How: Mock subprocess.run with stdout content
    Why: Verify success output comes from stdout
    """
    # Arrange: Mock claude success with stdout
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(returncode=0, stdout="Validation passed successfully", stderr="")

    # Act: Validate plugin
    _, output = validate_with_claude(sample_plugin_dir)

    # Assert: Output contains stdout
    assert "Validation passed successfully" in output


def test_validate_with_claude_includes_stderr_and_stdout_on_failure(
    mocker: MockerFixture, sample_plugin_dir: Path
) -> None:
    """Test validate_with_claude includes stderr+stdout in output on failure.

    Tests: Output content on failure
    How: Mock subprocess.run with both stderr and stdout
    Why: Verify failure output includes all diagnostic information
    """
    # Arrange: Mock claude failure with stderr and stdout
    mocker.patch("plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(
        returncode=1, stdout="Additional context", stderr="Error: Invalid configuration"
    )

    # Act: Validate plugin
    _, output = validate_with_claude(sample_plugin_dir)

    # Assert: Output contains both stderr and stdout
    assert "Error: Invalid configuration" in output
    assert "Additional context" in output
