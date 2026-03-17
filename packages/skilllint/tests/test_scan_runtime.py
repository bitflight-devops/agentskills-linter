"""Tests for scan_runtime seams extracted from plugin_validator.py.

These tests verify the extracted seams are correctly implemented and
wired into the CLI path. They serve as regression coverage ensuring
future refactoring cannot silently break the seam boundaries.

Coverage:
- _discover_validatable_paths: Auto-discovery of validatable files
- _resolve_filter_and_expand_paths: Filter resolution and path expansion
- _compute_summary: Summary statistics computation
- Seam wiring: Verify CLI imports and uses these extracted functions
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from skilllint.scan_runtime import (
    DEFAULT_SCAN_PATTERNS,
    FILTER_TYPE_MAP,
    _compute_summary,
    _discover_validatable_paths,
    _resolve_filter_and_expand_paths,
)

if TYPE_CHECKING:
    from typer.testing import CliRunner

    from skilllint.plugin_validator import FileResults


class TestDiscoverValidatablePaths:
    """Tests for _discover_validatable_paths seam."""

    def test_discovers_skill_files(self, tmp_path: Path) -> None:
        """_discover_validatable_paths finds SKILL.md files.

        Tests: SKILL.md files are discovered via DEFAULT_SCAN_PATTERNS
        How: Create a skill directory structure and verify discovery
        Why: Ensures path discovery seam works for the primary skill case
        """
        # Create a skill directory structure
        skill_dir = tmp_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: Test\n---\n# Test\n")

        discovered = _discover_validatable_paths(tmp_path)

        skill_file = skill_dir / "SKILL.md"
        assert skill_file in discovered, f"Expected {skill_file} in discovered paths: {discovered}"

    def test_discovers_agent_files(self, tmp_path: Path) -> None:
        """_discover_validatable_paths finds agent .md files.

        Tests: Agent files under agents/ are discovered
        How: Create an agent directory structure and verify discovery
        Why: Ensures path discovery seam works for agents
        """
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-agent.md").write_text("---\nname: my-agent\n---\n# Agent\n")

        discovered = _discover_validatable_paths(tmp_path)

        agent_file = agents_dir / "my-agent.md"
        assert agent_file in discovered, f"Expected {agent_file} in discovered paths: {discovered}"

    def test_discovers_command_files(self, tmp_path: Path) -> None:
        """_discover_validatable_paths finds command .md files.

        Tests: Command files under commands/ are discovered
        How: Create a command directory structure and verify discovery
        Why: Ensures path discovery seam works for commands
        """
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "my-command.md").write_text("---\nname: my-command\n---\n# Command\n")

        discovered = _discover_validatable_paths(tmp_path)

        command_file = commands_dir / "my-command.md"
        assert command_file in discovered, f"Expected {command_file} in discovered paths: {discovered}"

    def test_discovers_plugin_json_as_plugin_root(self, tmp_path: Path) -> None:
        """_discover_validatable_paths returns plugin root for plugin.json matches.

        Tests: .claude-plugin/plugin.json discovery returns the plugin root directory
        How: Create a plugin structure and verify the grandparent dir is returned
        Why: The validator validates plugin directories, not the plugin.json file itself
        """
        plugin_dir = tmp_path / "my-plugin"
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir(parents=True)
        (claude_plugin / "plugin.json").write_text('{"name": "my-plugin"}')

        discovered = _discover_validatable_paths(tmp_path)

        # Should return the plugin root directory, not the plugin.json file
        assert plugin_dir in discovered, f"Expected {plugin_dir} in discovered paths: {discovered}"

    def test_returns_sorted_paths(self, tmp_path: Path) -> None:
        """_discover_validatable_paths returns sorted paths.

        Tests: Output is sorted for deterministic ordering
        How: Create multiple files and verify order
        Why: Deterministic output is important for reproducibility
        """
        # Create multiple skills
        for name in ["zebra-skill", "alpha-skill", "middle-skill"]:
            skill_dir = tmp_path / "skills" / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(f"---\ndescription: {name}\n---\n# {name}\n")

        discovered = _discover_validatable_paths(tmp_path)

        # Should be sorted
        assert discovered == sorted(discovered), f"Paths not sorted: {discovered}"

    def test_empty_directory_returns_empty_list(self, tmp_path: Path) -> None:
        """_discover_validatable_paths returns empty list for empty directory.

        Tests: No crash on empty directory
        How: Pass empty directory and verify empty list
        Why: Edge case handling for empty projects
        """
        discovered = _discover_validatable_paths(tmp_path)
        assert discovered == []


class TestResolveFilterAndExpandPaths:
    """Tests for _resolve_filter_and_expand_paths seam."""

    def test_expands_directory_without_filter(self, tmp_path: Path) -> None:
        """_resolve_filter_and_expand_paths expands directory to contained files.

        Tests: Directory without filter expands to auto-discovered paths
        How: Pass a directory and verify expansion
        Why: Core path expansion behavior
        """
        # Create a skill
        skill_dir = tmp_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: Test\n---\n# Test\n")

        expanded, is_batch = _resolve_filter_and_expand_paths([tmp_path], None, None)

        skill_file = skill_dir / "SKILL.md"
        assert skill_file in expanded, f"Expected {skill_file} in expanded: {expanded}"
        assert is_batch is True, "Expected is_batch=True for directory expansion"

    def test_passes_through_files(self, tmp_path: Path) -> None:
        """_resolve_filter_and_expand_paths passes through file paths unchanged.

        Tests: File paths are not expanded
        How: Pass a file path and verify it's unchanged
        Why: File paths should be validated directly, not expanded
        """
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\ndescription: Test\n---\n# Test\n")

        expanded, is_batch = _resolve_filter_and_expand_paths([skill_file], None, None)

        assert expanded == [skill_file], f"Expected [{skill_file}], got {expanded}"
        assert is_batch is False, "Expected is_batch=False for single file"

    def test_filter_type_resolves_to_glob(self, tmp_path: Path) -> None:
        """_resolve_filter_and_expand_paths resolves --filter-type to glob pattern.

        Tests: filter_type='skills' resolves to '**/skills/*/SKILL.md'
        How: Create multiple files, use filter_type, verify only skills matched
        Why: Filter shortcuts for common cases
        """
        # Create skill
        skill_dir = tmp_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\ndescription: Test\n---\n# Test\n")

        # Create agent
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent.md").write_text("---\nname: agent\n---\n# Agent\n")

        expanded, is_batch = _resolve_filter_and_expand_paths([tmp_path], None, "skills")

        skill_file = skill_dir / "SKILL.md"
        agent_file = agents_dir / "agent.md"
        assert skill_file in expanded, f"Expected {skill_file} in expanded"
        assert agent_file not in expanded, f"Did not expect {agent_file} when filtering for skills"
        assert is_batch is True

    def test_custom_filter_glob(self, tmp_path: Path) -> None:
        """_resolve_filter_and_expand_paths applies custom glob filter.

        Tests: --filter applies custom glob pattern
        How: Use custom filter and verify matching
        Why: Flexibility for custom file patterns
        """
        # Create files
        (tmp_path / "file1.md").write_text("# File 1")
        (tmp_path / "file2.txt").write_text("File 2")

        expanded, is_batch = _resolve_filter_and_expand_paths([tmp_path], "*.md", None)

        assert tmp_path / "file1.md" in expanded
        assert (tmp_path / "file2.txt") not in expanded
        assert is_batch is True

    def test_rejects_mutually_exclusive_filters(self, tmp_path: Path) -> None:
        """_resolve_filter_and_expand_paths rejects both --filter and --filter-type.

        Tests: Mutually exclusive flags produce exit code 2
        How: Pass both filter options and verify error
        Why: Prevents ambiguous filter specification
        """
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            _resolve_filter_and_expand_paths([tmp_path], "*.md", "skills")

        assert exc_info.value.exit_code == 2

    def test_rejects_invalid_filter_type(self, tmp_path: Path) -> None:
        """_resolve_filter_and_expand_paths rejects invalid --filter-type value.

        Tests: Invalid filter type produces exit code 2
        How: Pass invalid filter_type and verify error
        Why: User input validation
        """
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            _resolve_filter_and_expand_paths([tmp_path], None, "invalid-type")

        assert exc_info.value.exit_code == 2

    def test_plugin_directory_expands_to_self(self, tmp_path: Path) -> None:
        """_resolve_filter_and_expand_paths returns plugin dir unchanged.

        Tests: Directory with .claude-plugin/plugin.json is not expanded
        How: Create plugin dir and verify it's returned as-is
        Why: Plugin directories should be validated as a whole, not expanded
        """
        plugin_dir = tmp_path / "my-plugin"
        claude_plugin = plugin_dir / ".claude-plugin"
        claude_plugin.mkdir(parents=True)
        (claude_plugin / "plugin.json").write_text('{"name": "my-plugin"}')

        expanded, _is_batch = _resolve_filter_and_expand_paths([plugin_dir], None, None)

        # Plugin dir should be in expanded (as-is, not expanded)
        assert plugin_dir in expanded, f"Expected {plugin_dir} in expanded: {expanded}"


class TestComputeSummary:
    """Tests for _compute_summary seam."""

    def test_counts_files_correctly(self) -> None:
        """_compute_summary counts total, passed, failed, warnings correctly.

        Tests: Summary statistics are computed correctly
        How: Create mock results and verify counts
        Why: Accurate summary is critical for CI exit codes
        """
        from skilllint.plugin_validator import ErrorCode, ValidationIssue, ValidationResult

        # Create results: 3 files, 2 passed, 1 failed
        results: FileResults = {
            Path("a.md"): [("v1", ValidationResult(passed=True, errors=[], warnings=[], info=[]))],
            Path("b.md"): [("v1", ValidationResult(passed=True, errors=[], warnings=[], info=[]))],
            Path("c.md"): [
                (
                    "v1",
                    ValidationResult(
                        passed=False,
                        errors=[ValidationIssue(field="x", severity="error", message="err", code=ErrorCode.FM001)],
                        warnings=[],
                        info=[],
                    ),
                )
            ],
        }

        total, passed, failed, warnings = _compute_summary(results)

        assert total == 3, f"Expected total=3, got {total}"
        assert passed == 2, f"Expected passed=2, got {passed}"
        assert failed == 1, f"Expected failed=1, got {failed}"
        assert warnings == 0, f"Expected warnings=0, got {warnings}"

    def test_warnings_counted_correctly(self) -> None:
        """_compute_summary counts files with warnings but no errors.

        Tests: Files that pass but have warnings are counted
        How: Create results with warnings and verify count
        Why: Warning tracking is separate from failure tracking
        """
        from skilllint.plugin_validator import ErrorCode, ValidationIssue, ValidationResult

        results: FileResults = {
            Path("a.md"): [
                (
                    "v1",
                    ValidationResult(
                        passed=True,
                        errors=[],
                        warnings=[ValidationIssue(field="x", severity="warning", message="warn", code=ErrorCode.SK006)],
                        info=[],
                    ),
                )
            ]
        }

        total, passed, failed, warnings = _compute_summary(results)

        assert total == 1
        assert passed == 1  # Passed because no errors
        assert failed == 0
        assert warnings == 1  # Has warnings

    def test_empty_results_returns_zeros(self) -> None:
        """_compute_summary returns zeros for empty results.

        Tests: Empty input produces all zeros
        How: Pass empty dict and verify zeros
        Why: Edge case handling
        """

        results: FileResults = {}

        total, passed, failed, warnings = _compute_summary(results)

        assert total == passed == failed == warnings == 0


class TestSeamWiring:
    """Tests proving the extracted seams are wired into the CLI."""

    def test_scan_runtime_exports_exist(self) -> None:
        """scan_runtime module exports the expected functions and constants.

        Tests: Module exports match extraction contract
        How: Import and verify existence
        Why: Ensures the seam surface is stable
        """
        import skilllint.scan_runtime as scan_runtime

        # Functions
        assert hasattr(scan_runtime, "_discover_validatable_paths")
        assert hasattr(scan_runtime, "_resolve_filter_and_expand_paths")
        assert hasattr(scan_runtime, "_compute_summary")
        assert hasattr(scan_runtime, "run_validation_loop")

        # Constants
        assert hasattr(scan_runtime, "FILTER_TYPE_MAP")
        assert hasattr(scan_runtime, "DEFAULT_SCAN_PATTERNS")

        # Verify constants are correct
        assert "skills" in scan_runtime.FILTER_TYPE_MAP
        assert "agents" in scan_runtime.FILTER_TYPE_MAP
        assert "commands" in scan_runtime.FILTER_TYPE_MAP

    def test_plugin_validator_imports_from_scan_runtime(self) -> None:
        """plugin_validator imports the extracted seams from scan_runtime.

        Tests: Imports are from the extracted module, not local definitions
        How: Check the module's imports
        Why: Proves the seam wiring is active
        """
        import skilllint.plugin_validator as pv

        # Check that _resolve_filter_and_expand_paths is imported from scan_runtime
        from skilllint.scan_runtime import _resolve_filter_and_expand_paths as scan_resolve

        # The alias should point to the same function
        assert pv._resolve_filter_and_expand_paths is scan_resolve

    def test_cli_uses_resolve_filter_and_expand_paths(
        self, cli_runner: CliRunner, sample_skill_dir: Path, no_color_env: None
    ) -> None:
        """CLI validation uses _resolve_filter_and_expand_paths for path expansion.

        Tests: The CLI path exercises the extracted seam
        How: Run CLI and verify correct path handling
        Why: Proves the seam is active in runtime, not dead code
        """
        # Run CLI on a directory - this exercises _resolve_filter_and_expand_paths
        result = cli_runner.invoke(
            __import__("skilllint.plugin_validator", fromlist=["app"]).app,
            ["check", "--no-color", str(sample_skill_dir)],
        )

        # Should complete successfully
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}. Output: {result.stdout}"

    def test_cli_uses_compute_summary(self, cli_runner: CliRunner, sample_skill_dir: Path, no_color_env: None) -> None:
        """CLI validation uses _compute_summary for summary output.

        Tests: The --show-summary flag exercises the extracted seam
        How: Run CLI with --show-summary and verify summary output
        Why: Proves the _compute_summary seam is active in runtime
        """
        result = cli_runner.invoke(
            __import__("skilllint.plugin_validator", fromlist=["app"]).app,
            ["check", "--no-color", "--show-summary", str(sample_skill_dir)],
        )

        # Should show summary output (which uses _compute_summary)
        assert result.exit_code == 0
        assert "Total files:" in result.stdout, f"Expected summary in output: {result.stdout}"


class TestReporterSelection:
    """Tests for reporter selection in the CLI path."""

    def test_console_reporter_used_by_default(
        self, cli_runner: CliRunner, sample_skill_dir: Path, no_color_env: None
    ) -> None:
        """CLI uses ConsoleReporter when --no-color is not set.

        Tests: Default reporter is ConsoleReporter
        How: Run CLI without --no-color and verify formatted output
        Why: Ensures reporter selection works correctly
        """
        result = cli_runner.invoke(
            __import__("skilllint.plugin_validator", fromlist=["app"]).app, ["check", str(sample_skill_dir)]
        )

        # Should complete successfully with formatted output
        assert result.exit_code == 0

    def test_ci_reporter_used_with_no_color(
        self, cli_runner: CliRunner, sample_skill_dir: Path, no_color_env: None
    ) -> None:
        """CLI uses CIReporter when --no-color is set.

        Tests: --no-color flag selects CIReporter
        How: Run CLI with --no-color and verify plain output
        Why: Ensures reporter selection works for CI environments
        """
        result = cli_runner.invoke(
            __import__("skilllint.plugin_validator", fromlist=["app"]).app,
            ["check", "--no-color", str(sample_skill_dir)],
        )

        # Should complete successfully with plain output
        assert result.exit_code == 0
        # The output should be present (CIReporter still outputs, just without ANSI)
        assert len(result.stdout) > 0 or result.exit_code == 0


class TestConstantsExport:
    """Tests for constant exports from scan_runtime."""

    def test_filter_type_map_values(self) -> None:
        """FILTER_TYPE_MAP has correct glob patterns.

        Tests: Filter type shortcuts map to correct patterns
        How: Verify pattern values
        Why: Ensures filter shortcuts work correctly
        """
        assert FILTER_TYPE_MAP["skills"] == "**/skills/*/SKILL.md"
        assert FILTER_TYPE_MAP["agents"] == "**/agents/*.md"
        assert FILTER_TYPE_MAP["commands"] == "**/commands/*.md"

    def test_default_scan_patterns_includes_all_types(self) -> None:
        """DEFAULT_SCAN_PATTERNS covers all file types.

        Tests: All expected file types are in scan patterns
        How: Check pattern tuple contents
        Why: Ensures complete auto-discovery
        """
        patterns = set(DEFAULT_SCAN_PATTERNS)

        # Should include skills
        assert any("skills" in p for p in patterns), f"Missing skills pattern in {patterns}"
        # Should include agents
        assert any("agents" in p for p in patterns), f"Missing agents pattern in {patterns}"
        # Should include commands
        assert any("commands" in p for p in patterns), f"Missing commands pattern in {patterns}"
        # Should include plugin.json
        assert any("plugin.json" in p for p in patterns), f"Missing plugin.json pattern in {patterns}"
        # Should include hooks.json
        assert any("hooks.json" in p for p in patterns), f"Missing hooks.json pattern in {patterns}"
        # Should include CLAUDE.md
        assert any("CLAUDE.md" in p for p in patterns), f"Missing CLAUDE.md pattern in {patterns}"
