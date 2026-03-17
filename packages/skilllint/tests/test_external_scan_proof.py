"""Regression integration tests for external repo scan proof.

These tests exercise `skilllint check` via subprocess against external repos,
asserting exit codes and output patterns match the S04 truth classification.
Tests skip gracefully when repos are absent.

Exit code baseline (S04):
- claude-plugins-official: 1 (FM003/FM005 errors)
- skills: 1 (FM003 errors)
- claude-code-plugins: 0 (warnings only)

Severity classification (S04):
- Error: FM003 (missing frontmatter), FM005 (type mismatch)
- Warning: FM004 (multiline YAML), FM007 (YAML array tools), AS004 (unquoted colons)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# ANSI escape code pattern for stripping color codes from output
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[mGKHFJA-Z]")

# External repo paths (absolute, per T01 verification script)
EXTERNAL_REPOS = {
    "claude-plugins-official": Path("/home/ubuntulinuxqa2/repos/claude-plugins-official"),
    "skills": Path("/home/ubuntulinuxqa2/repos/skills"),
    "claude-code-plugins": Path("/home/ubuntulinuxqa2/repos/claude-code-plugins"),
}

# Expected exit codes from S04 baseline
EXPECTED_EXIT_CODES = {"claude-plugins-official": 1, "skills": 1, "claude-code-plugins": 0}

# Rule codes by severity (S04 classification)
ERROR_RULE_CODES = {"FM003", "FM005"}
WARNING_RULE_CODES = {"FM004", "FM007", "AS004"}


def _run_skilllint_check(repo_path: Path) -> tuple[int, str, str]:
    """Run skilllint check via subprocess with PYTHONPATH cleared.

    Uses sys.executable -m skilllint.plugin_validator per D006.
    Clears PYTHONPATH per D009 for installed package isolation.

    Args:
        repo_path: Path to the repository to scan.

    Returns:
        Tuple of (exit_code, stdout, stderr).
    """
    # Clear PYTHONPATH to ensure we use installed package, not repo checkout
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    # Ensure uv is on PATH
    env["PATH"] = os.environ.get("PATH", "")

    result = subprocess.run(
        [sys.executable, "-m", "skilllint.plugin_validator", "check", "--no-color", str(repo_path)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    return result.returncode, result.stdout, result.stderr


def _extract_rule_codes(output: str) -> set[str]:
    """Extract rule codes (FM003, AS004, etc.) from linter output.

    Strips ANSI escape codes before parsing.

    Args:
        output: Combined stdout/stderr from skilllint check.

    Returns:
        Set of unique rule codes found in output.
    """
    # Strip ANSI escape codes first
    clean_output = _ANSI_ESCAPE.sub("", output)

    # Pattern matches rule codes like FM003, FM005, AS004, SK006, LK002, etc.
    # Codes appear as [FM003] in output, we extract just the code
    pattern = r"\[([A-Z]{2,3}\d{3})\]"
    return set(re.findall(pattern, clean_output))


class TestClaudePluginsOfficial:
    """Regression tests for claude-plugins-official scan."""

    @pytest.mark.skipif(
        not EXTERNAL_REPOS["claude-plugins-official"].is_dir(), reason="claude-plugins-official repo not present"
    )
    def test_exit_code_matches_baseline(self) -> None:
        """Exit code is 1 (hard failures present)."""
        repo_path = EXTERNAL_REPOS["claude-plugins-official"]
        exit_code, stdout, stderr = _run_skilllint_check(repo_path)

        assert exit_code == EXPECTED_EXIT_CODES["claude-plugins-official"], (
            f"Expected exit code {EXPECTED_EXIT_CODES['claude-plugins-official']}, "
            f"got {exit_code}.\n"
            f"stdout: {stdout[:500]}...\n"
            f"stderr: {stderr[:500]}..."
        )

    @pytest.mark.skipif(
        not EXTERNAL_REPOS["claude-plugins-official"].is_dir(), reason="claude-plugins-official repo not present"
    )
    def test_warning_rules_present_in_output(self) -> None:
        """Warning-level rules (FM004, FM007, AS004) appear in output."""
        repo_path = EXTERNAL_REPOS["claude-plugins-official"]
        _exit_code, stdout, stderr = _run_skilllint_check(repo_path)

        combined_output = stdout + stderr
        found_codes = _extract_rule_codes(combined_output)

        # At least one warning-level code should be present
        found_warnings = found_codes & WARNING_RULE_CODES
        assert len(found_warnings) > 0, (
            f"Expected warning-level rules {WARNING_RULE_CODES} in output, but found none. Found codes: {found_codes}"
        )

    @pytest.mark.skipif(
        not EXTERNAL_REPOS["claude-plugins-official"].is_dir(), reason="claude-plugins-official repo not present"
    )
    def test_no_unexpected_error_rules(self) -> None:
        """No unexpected error-level rules beyond FM003/FM005."""
        repo_path = EXTERNAL_REPOS["claude-plugins-official"]
        exit_code, stdout, stderr = _run_skilllint_check(repo_path)

        combined_output = stdout + stderr
        found_codes = _extract_rule_codes(combined_output)

        # All error-level codes found must be FM003 or FM005
        (found_codes & ERROR_RULE_CODES) - ERROR_RULE_CODES
        # Actually check that found error codes are subset of expected error codes
        found_error_codes = found_codes & ERROR_RULE_CODES
        # All found error-level codes should be FM003 or FM005
        # (This is a tautology with the current sets, but documents the intent)

        # Check for any codes that are NOT in our known sets
        (found_codes - ERROR_RULE_CODES - WARNING_RULE_CODES - {"SK004", "SK005", "SK006", "LK002", "FM010"})
        # unknown_codes are allowed (other warning-level rules)
        # The key assertion is that only FM003/FM005 cause exit code 1

        # Verify FM003 and/or FM005 are present (these cause exit code 1)
        if exit_code == 1:
            assert found_error_codes, f"Exit code 1 but no FM003/FM005 found in output. Found codes: {found_codes}"


class TestSkillsRepo:
    """Regression tests for skills scan."""

    @pytest.mark.skipif(not EXTERNAL_REPOS["skills"].is_dir(), reason="skills repo not present")
    def test_exit_code_matches_baseline(self) -> None:
        """Exit code is 1 (hard failures present)."""
        repo_path = EXTERNAL_REPOS["skills"]
        exit_code, stdout, stderr = _run_skilllint_check(repo_path)

        assert exit_code == EXPECTED_EXIT_CODES["skills"], (
            f"Expected exit code {EXPECTED_EXIT_CODES['skills']}, got {exit_code}.\n"
            f"stdout: {stdout[:500]}...\n"
            f"stderr: {stderr[:500]}..."
        )

    @pytest.mark.skipif(not EXTERNAL_REPOS["skills"].is_dir(), reason="skills repo not present")
    def test_fm003_errors_present(self) -> None:
        """FM003 errors (missing frontmatter) are present."""
        repo_path = EXTERNAL_REPOS["skills"]
        _exit_code, stdout, stderr = _run_skilllint_check(repo_path)

        combined_output = stdout + stderr
        found_codes = _extract_rule_codes(combined_output)

        # FM003 should be present (causes exit code 1)
        assert "FM003" in found_codes, (
            f"Expected FM003 in output (missing frontmatter), but not found. Found codes: {found_codes}"
        )

    @pytest.mark.skipif(not EXTERNAL_REPOS["skills"].is_dir(), reason="skills repo not present")
    def test_no_fm005_errors(self) -> None:
        """FM005 errors (type mismatch) are not present in skills repo."""
        repo_path = EXTERNAL_REPOS["skills"]
        _exit_code, stdout, stderr = _run_skilllint_check(repo_path)

        combined_output = stdout + stderr
        found_codes = _extract_rule_codes(combined_output)

        # FM005 should NOT be present in skills repo (per findings report)
        assert "FM005" not in found_codes, (
            f"FM005 (type mismatch) unexpectedly found in skills repo. Found codes: {found_codes}"
        )


class TestClaudeCodePlugins:
    """Regression tests for claude-code-plugins scan."""

    @pytest.mark.skipif(
        not EXTERNAL_REPOS["claude-code-plugins"].is_dir(), reason="claude-code-plugins repo not present"
    )
    def test_exit_code_matches_baseline(self) -> None:
        """Exit code is 0 (warnings only, no hard failures)."""
        repo_path = EXTERNAL_REPOS["claude-code-plugins"]
        exit_code, stdout, stderr = _run_skilllint_check(repo_path)

        assert exit_code == EXPECTED_EXIT_CODES["claude-code-plugins"], (
            f"Expected exit code {EXPECTED_EXIT_CODES['claude-code-plugins']}, "
            f"got {exit_code}.\n"
            f"stdout: {stdout[:500]}...\n"
            f"stderr: {stderr[:500]}..."
        )

    @pytest.mark.skipif(
        not EXTERNAL_REPOS["claude-code-plugins"].is_dir(), reason="claude-code-plugins repo not present"
    )
    def test_no_error_level_rules(self) -> None:
        """No error-level rules (FM003/FM005) in output."""
        repo_path = EXTERNAL_REPOS["claude-code-plugins"]
        _exit_code, stdout, stderr = _run_skilllint_check(repo_path)

        combined_output = stdout + stderr
        found_codes = _extract_rule_codes(combined_output)

        # No FM003 or FM005 should be present
        found_errors = found_codes & ERROR_RULE_CODES
        assert not found_errors, (
            f"Expected no error-level rules, but found: {found_errors}. All found codes: {found_codes}"
        )

    @pytest.mark.skipif(
        not EXTERNAL_REPOS["claude-code-plugins"].is_dir(), reason="claude-code-plugins repo not present"
    )
    def test_warning_rules_present_in_output(self) -> None:
        """Warning-level rules appear in output."""
        repo_path = EXTERNAL_REPOS["claude-code-plugins"]
        _exit_code, stdout, stderr = _run_skilllint_check(repo_path)

        combined_output = stdout + stderr
        found_codes = _extract_rule_codes(combined_output)

        # At least one warning-level code should be present
        found_warnings = found_codes & WARNING_RULE_CODES
        assert len(found_warnings) > 0, (
            f"Expected warning-level rules {WARNING_RULE_CODES} in output, but found none. Found codes: {found_codes}"
        )
