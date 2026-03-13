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

from skilllint.plugin_validator import CLAUDE_TIMEOUT, get_staged_files, is_claude_available, validate_with_claude

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")

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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value=None)

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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value=None)

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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")

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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value=claude_path)
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
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


def test_get_staged_files_when_not_git_repo(mocker: MockerFixture) -> None:
    """Test get_staged_files returns empty list when not in git repo.

    Tests: Handling non-git directories
    How: Mock Repo to raise InvalidGitRepositoryError
    Why: Verify no crash when running outside git repository
    """
    from git.exc import InvalidGitRepositoryError

    # Arrange: Mock Repo to raise when not in a git repo
    mocker.patch("skilllint.plugin_validator.Repo", side_effect=InvalidGitRepositoryError("not a repo"))

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns empty list
    assert result == []


def test_get_staged_files_with_staged_files(mocker: MockerFixture) -> None:
    """Test get_staged_files returns Path objects for staged files.

    Tests: GitPython index diff parsing for staged files
    How: Mock Repo.index.diff to return diff items with a_path attributes
    Why: Verify correct extraction of staged file paths
    """
    # Arrange: Build mock diff items
    diff_item_1 = mocker.Mock()
    diff_item_1.a_path = "plugins/plugin-creator/SKILL.md"
    diff_item_2 = mocker.Mock()
    diff_item_2.a_path = "plugins/test/agent.md"

    mock_repo = mocker.Mock()
    mock_repo.index.diff.return_value = [diff_item_1, diff_item_2]
    mocker.patch("skilllint.plugin_validator.Repo", return_value=mock_repo)

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns list of Path objects
    assert len(result) == 2
    assert all(isinstance(p, Path) for p in result)
    assert result[0] == Path("plugins/plugin-creator/SKILL.md")
    assert result[1] == Path("plugins/test/agent.md")


def test_get_staged_files_with_no_staged_files(mocker: MockerFixture) -> None:
    """Test get_staged_files returns empty list when no files staged.

    Tests: Empty index diff handling
    How: Mock Repo.index.diff to return empty list
    Why: Verify correct handling of no staged changes
    """
    # Arrange: Mock repo with no staged files
    mock_repo = mocker.Mock()
    mock_repo.index.diff.return_value = []
    mocker.patch("skilllint.plugin_validator.Repo", return_value=mock_repo)

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns empty list
    assert result == []


def test_get_staged_files_handles_value_error(mocker: MockerFixture) -> None:
    """Test get_staged_files handles ValueError gracefully (e.g. empty/bare repo).

    Tests: Handling repos with no HEAD commit
    How: Mock Repo to raise ValueError
    Why: Verify graceful degradation for empty repositories
    """
    # Arrange: Mock Repo to raise ValueError (e.g. no HEAD)
    mocker.patch("skilllint.plugin_validator.Repo", side_effect=ValueError("no HEAD"))

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns empty list (graceful degradation)
    assert result == []


def test_get_staged_files_handles_diff_error(mocker: MockerFixture) -> None:
    """Test get_staged_files handles errors from index.diff gracefully.

    Tests: Handling GitPython diff failures
    How: Mock index.diff to raise an exception
    Why: Verify non-repo errors are handled gracefully
    """
    from git.exc import InvalidGitRepositoryError

    # Arrange: Mock repo where index.diff raises
    mock_repo = mocker.Mock()
    mock_repo.index.diff.side_effect = InvalidGitRepositoryError("error")
    mocker.patch("skilllint.plugin_validator.Repo", return_value=mock_repo)

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns empty list (graceful degradation)
    assert result == []


def test_get_staged_files_os_error(mocker: MockerFixture) -> None:
    """Test get_staged_files handles OSError gracefully.

    Tests: Handling general OS-level git errors
    How: Mock Repo to raise OSError
    Why: Verify non-git OS failures handled gracefully
    """
    # Arrange: Mock Repo to raise OSError
    mocker.patch("skilllint.plugin_validator.Repo", side_effect=OSError("Permission denied"))

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Returns empty list (graceful degradation)
    assert result == []


def test_get_staged_files_uses_index_diff_against_head(mocker: MockerFixture) -> None:
    """Test get_staged_files calls index.diff with the HEAD commit.

    Tests: GitPython API usage — staged files are index diff vs HEAD
    How: Mock Repo, verify index.diff is called with head commit
    Why: Confirm the correct GitPython pattern is used for staged files
    """
    # Arrange: Mock repo with no staged files
    mock_repo = mocker.Mock()
    mock_repo.index.diff.return_value = []
    mocker.patch("skilllint.plugin_validator.Repo", return_value=mock_repo)

    # Act: Get staged files
    get_staged_files()

    # Assert: index.diff called with the HEAD commit object
    mock_repo.index.diff.assert_called_once_with(mock_repo.head.commit)


def test_get_staged_files_filters_items_without_path(mocker: MockerFixture) -> None:
    """Test get_staged_files skips diff items that have no a_path.

    Tests: Defensive filtering of diff items with empty paths
    How: Mock index.diff to return items with and without a_path
    Why: Verify only items with actual paths are returned
    """
    # Arrange: Mix of items with and without a_path
    item_with_path = mocker.Mock()
    item_with_path.a_path = "plugins/test/file1.md"
    item_empty_path = mocker.Mock()
    item_empty_path.a_path = ""

    mock_repo = mocker.Mock()
    mock_repo.index.diff.return_value = [item_with_path, item_empty_path]
    mocker.patch("skilllint.plugin_validator.Repo", return_value=mock_repo)

    # Act: Get staged files
    result = get_staged_files()

    # Assert: Only non-empty paths returned
    assert len(result) == 1
    assert result[0] == Path("plugins/test/file1.md")


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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
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
    mocker.patch("skilllint.plugin_validator.shutil.which", return_value="/usr/local/bin/claude")
    mock_run = mocker.patch("skilllint.plugin_validator.subprocess.run")
    mock_run.return_value = mocker.Mock(
        returncode=1, stdout="Additional context", stderr="Error: Invalid configuration"
    )

    # Act: Validate plugin
    _, output = validate_with_claude(sample_plugin_dir)

    # Assert: Output contains both stderr and stdout
    assert "Error: Invalid configuration" in output
    assert "Additional context" in output
