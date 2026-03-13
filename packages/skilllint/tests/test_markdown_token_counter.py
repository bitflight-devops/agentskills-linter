"""Tests for markdown token counting and FileType enum extensions.

Tests: FileType detection for CLAUDE_MD, REFERENCE, MARKDOWN types,
       MarkdownTokenCounter validation and programmatic counting,
       --tokens-only CLI flag behavior.
How: Uses pytest fixtures and Typer CliRunner to verify behavior.
Why: Ensures plugin-validator correctly handles general markdown files
     and provides programmatic token counting for optimization workflows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import skilllint.plugin_validator as plugin_validator

if TYPE_CHECKING:
    from pathlib import Path

    from typer.testing import CliRunner


class TestFileTypeDetection:
    """Test FileType enum detection for new markdown types."""

    def test_claude_md_detected(self, tmp_path: Path) -> None:
        """Verify CLAUDE.md files are detected as CLAUDE_MD type.

        Tests: FileType.detect_file_type returns CLAUDE_MD for CLAUDE.md
        How: Create a CLAUDE.md file and check detection
        Why: CLAUDE.md files need token counting support
        """
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Instructions\n\nSome content.\n")

        result = plugin_validator.FileType.detect_file_type(claude_md)

        assert result == plugin_validator.FileType.CLAUDE_MD

    def test_reference_md_detected(self, tmp_path: Path) -> None:
        """Verify .md files in references/ directories are detected as REFERENCE type.

        Tests: FileType.detect_file_type returns REFERENCE for references/*.md
        How: Create a references/ directory with .md file and check detection
        Why: Reference docs need token counting without skill-specific validation
        """
        refs_dir = tmp_path / "references"
        refs_dir.mkdir()
        ref_md = refs_dir / "guide.md"
        ref_md.write_text("# Reference Guide\n\nContent.\n")

        result = plugin_validator.FileType.detect_file_type(ref_md)

        assert result == plugin_validator.FileType.REFERENCE

    def test_generic_markdown_detected(self, tmp_path: Path) -> None:
        """Verify generic .md files are detected as MARKDOWN type.

        Tests: FileType.detect_file_type returns MARKDOWN for any .md not matching other types
        How: Create a README.md file outside special directories
        Why: General markdown files should be counted, not rejected as UNKNOWN
        """
        readme = tmp_path / "README.md"
        readme.write_text("# README\n\nProject docs.\n")

        result = plugin_validator.FileType.detect_file_type(readme)

        assert result == plugin_validator.FileType.MARKDOWN

    def test_skill_md_still_detected_as_skill(self, tmp_path: Path) -> None:
        """Verify SKILL.md files still detected as SKILL type (not MARKDOWN).

        Tests: SKILL.md detection takes priority over generic .md detection
        How: Create a SKILL.md file and verify it is classified as SKILL
        Why: Ensures new MARKDOWN type doesn't shadow existing SKILL detection
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\ndescription: Test\n---\n\n# Skill\n")

        result = plugin_validator.FileType.detect_file_type(skill_md)

        assert result == plugin_validator.FileType.SKILL

    def test_agent_md_still_detected_as_agent(self, tmp_path: Path) -> None:
        """Verify .md files in agents/ still detected as AGENT type (not MARKDOWN).

        Tests: AGENT detection takes priority over generic .md detection
        How: Create agents/test.md and verify classification
        Why: Ensures new types don't shadow existing AGENT detection
        """
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_md = agents_dir / "test-agent.md"
        agent_md.write_text("---\nname: test\ndescription: Test\n---\n\n# Agent\n")

        result = plugin_validator.FileType.detect_file_type(agent_md)

        assert result == plugin_validator.FileType.AGENT

    def test_command_md_still_detected_as_command(self, tmp_path: Path) -> None:
        """Verify .md files in commands/ still detected as COMMAND type (not MARKDOWN).

        Tests: COMMAND detection takes priority over generic .md detection
        How: Create commands/test.md and verify classification
        Why: Ensures new types don't shadow existing COMMAND detection
        """
        cmds_dir = tmp_path / "commands"
        cmds_dir.mkdir()
        cmd_md = cmds_dir / "test-cmd.md"
        cmd_md.write_text("---\ndescription: Test\n---\n\n# Command\n")

        result = plugin_validator.FileType.detect_file_type(cmd_md)

        assert result == plugin_validator.FileType.COMMAND

    def test_non_md_file_still_unknown(self, tmp_path: Path) -> None:
        """Verify non-.md files still return UNKNOWN.

        Tests: Files without .md extension are not affected by new types
        How: Create a .txt file and verify classification
        Why: Only markdown files should match the new types
        """
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Some text notes.\n")

        result = plugin_validator.FileType.detect_file_type(txt_file)

        assert result == plugin_validator.FileType.UNKNOWN

    def test_nested_reference_md_detected(self, tmp_path: Path) -> None:
        """Verify .md files in nested references/ directories are detected.

        Tests: 'references' anywhere in path parts triggers REFERENCE type
        How: Create deeply nested references/subdir/file.md
        Why: Reference files may be in subdirectories
        """
        nested = tmp_path / "skill" / "references" / "subdir"
        nested.mkdir(parents=True)
        ref_md = nested / "deep-ref.md"
        ref_md.write_text("# Deep Reference\n\nContent.\n")

        result = plugin_validator.FileType.detect_file_type(ref_md)

        assert result == plugin_validator.FileType.REFERENCE


class TestMarkdownTokenCounter:
    """Test MarkdownTokenCounter validation and counting."""

    def test_counts_tokens_for_plain_markdown(self, tmp_path: Path) -> None:
        """Verify token counting works for plain markdown (no frontmatter).

        Tests: MarkdownTokenCounter produces token count info for plain .md
        How: Create .md without frontmatter, run validate()
        Why: Many markdown files (CLAUDE.md, README.md) lack frontmatter
        """
        md_file = tmp_path / "plain.md"
        md_file.write_text("# Hello World\n\nThis is a test document.\n")

        counter = plugin_validator.MarkdownTokenCounter()
        result = counter.validate(md_file)

        assert result.passed is True
        assert len(result.errors) == 0
        assert len(result.info) == 1
        assert "TC001" in result.info[0].code
        assert "tokens" in result.info[0].message

    def test_counts_tokens_with_frontmatter(self, tmp_path: Path) -> None:
        """Verify token counting handles files with frontmatter.

        Tests: MarkdownTokenCounter correctly splits frontmatter from body
        How: Create .md with frontmatter, verify frontmatter tokens reported
        Why: Some markdown files (like CLAUDE.md in projects) may have frontmatter
        """
        md_file = tmp_path / "CLAUDE.md"
        md_file.write_text("---\ntitle: Test\nversion: 1.0\n---\n\n# Content\n\nBody text here.\n")

        counter = plugin_validator.MarkdownTokenCounter()
        result = counter.validate(md_file)

        assert result.passed is True
        assert len(result.info) == 1
        info_msg = result.info[0].message
        assert "frontmatter:" in info_msg
        assert "body:" in info_msg

    def test_count_file_tokens_returns_integer(self, tmp_path: Path) -> None:
        """Verify count_file_tokens returns an integer for programmatic use.

        Tests: count_file_tokens returns int token count
        How: Create a file and call count_file_tokens()
        Why: --tokens-only flag depends on this method
        """
        md_file = tmp_path / "test.md"
        md_file.write_text("Hello world.\n")

        counter = plugin_validator.MarkdownTokenCounter()
        count = counter.count_file_tokens(md_file)

        assert isinstance(count, int)
        assert count > 0

    def test_count_file_tokens_nonexistent_file(self, tmp_path: Path) -> None:
        """Verify count_file_tokens returns None for nonexistent files.

        Tests: count_file_tokens handles missing files gracefully
        How: Call with path to nonexistent file
        Why: Programmatic callers need to handle failure
        """
        counter = plugin_validator.MarkdownTokenCounter()
        count = counter.count_file_tokens(tmp_path / "nonexistent.md")

        assert count is None

    def test_validate_nonexistent_file_returns_error(self, tmp_path: Path) -> None:
        """Verify validate() returns error for nonexistent files.

        Tests: validate() handles missing files with error
        How: Call with path to nonexistent file
        Why: Rich output mode needs clean error handling
        """
        counter = plugin_validator.MarkdownTokenCounter()
        result = counter.validate(tmp_path / "nonexistent.md")

        assert result.passed is False
        assert len(result.errors) == 1

    def test_can_fix_returns_false(self) -> None:
        """Verify can_fix() returns False (token counting is read-only).

        Tests: MarkdownTokenCounter is read-only
        How: Call can_fix()
        Why: Implements Validator protocol correctly
        """
        counter = plugin_validator.MarkdownTokenCounter()
        assert counter.can_fix() is False

    def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
        """Verify fix() raises NotImplementedError.

        Tests: fix() correctly reports unsupported operation
        How: Call fix() and expect exception
        Why: Implements Validator protocol correctly
        """
        counter = plugin_validator.MarkdownTokenCounter()
        with pytest.raises(NotImplementedError):
            counter.fix(tmp_path / "test.md")

    def test_empty_file_returns_zero_tokens(self, tmp_path: Path) -> None:
        """Verify token counting handles empty files.

        Tests: Empty file produces 0 tokens
        How: Create empty file and count tokens
        Why: Edge case - should not crash
        """
        md_file = tmp_path / "empty.md"
        md_file.write_text("")

        counter = plugin_validator.MarkdownTokenCounter()
        count = counter.count_file_tokens(md_file)

        assert count == 0


class TestTokensOnlyCLIFlag:
    """Test --tokens-only CLI flag behavior."""

    def test_tokens_only_outputs_integer(self, cli_runner: CliRunner, tmp_path: Path, no_color_env: None) -> None:
        """Verify --tokens-only outputs just an integer.

        Tests: --tokens-only produces clean integer output
        How: Run CLI with --tokens-only flag, verify output is integer
        Why: Programmatic consumers need parseable output
        """
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\n\nSome content for token counting.\n")

        result = cli_runner.invoke(plugin_validator.app, ["check", "--tokens-only", str(md_file)])

        assert result.exit_code == 0
        # Output should be a single integer (possibly with trailing newline)
        output = result.stdout.strip()
        assert output.isdigit(), f"Expected integer output, got: {output!r}"
        assert int(output) > 0

    def test_tokens_only_exit_code_0(self, cli_runner: CliRunner, tmp_path: Path, no_color_env: None) -> None:
        """Verify --tokens-only exits with code 0 on success.

        Tests: Exit code 0 for successful token counting
        How: Run CLI with --tokens-only on valid file
        Why: Scripts need reliable exit codes
        """
        md_file = tmp_path / "test.md"
        md_file.write_text("Content.\n")

        result = cli_runner.invoke(plugin_validator.app, ["check", "--tokens-only", str(md_file)])

        assert result.exit_code == 0

    def test_tokens_only_exit_code_2_missing_file(self, cli_runner: CliRunner, no_color_env: None) -> None:
        """Verify --tokens-only exits with code 2 for missing files.

        Tests: Exit code 2 for nonexistent file
        How: Run CLI with --tokens-only on nonexistent path
        Why: Scripts need to detect errors
        """
        result = cli_runner.invoke(plugin_validator.app, ["check", "--tokens-only", "/nonexistent/file.md"])

        assert result.exit_code == 2

    def test_tokens_only_no_rich_formatting(self, cli_runner: CliRunner, tmp_path: Path, no_color_env: None) -> None:
        """Verify --tokens-only produces no Rich formatting.

        Tests: Output contains no ANSI escape codes or Rich markup
        How: Run --tokens-only and check for ANSI codes
        Why: Programmatic consumers need raw integer output
        """
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\n\nBody content.\n")

        result = cli_runner.invoke(plugin_validator.app, ["check", "--tokens-only", str(md_file)])

        assert "\x1b[" not in result.stdout  # No ANSI escape codes
        assert "Validation" not in result.stdout  # No summary panel
        assert "PASSED" not in result.stdout  # No status text

    def test_tokens_only_works_with_skill_md(
        self, cli_runner: CliRunner, sample_skill_dir: Path, no_color_env: None
    ) -> None:
        """Verify --tokens-only works for SKILL.md files too.

        Tests: Token counting is not limited to specific file types
        How: Run --tokens-only on a SKILL.md file
        Why: Users may want token counts for any markdown file
        """
        skill_file = sample_skill_dir / "SKILL.md"
        result = cli_runner.invoke(plugin_validator.app, ["check", "--tokens-only", str(skill_file)])

        assert result.exit_code == 0
        output = result.stdout.strip()
        assert output.isdigit()
        assert int(output) > 0

    def test_tokens_only_multiple_files(self, cli_runner: CliRunner, tmp_path: Path, no_color_env: None) -> None:
        """Verify --tokens-only handles multiple files (one count per line).

        Tests: Multiple files produce one integer per line
        How: Run --tokens-only with two files
        Why: Batch processing support
        """
        file_a = tmp_path / "a.md"
        file_b = tmp_path / "b.md"
        file_a.write_text("Short.\n")
        file_b.write_text("Also short content.\n")

        result = cli_runner.invoke(plugin_validator.app, ["check", "--tokens-only", str(file_a), str(file_b)])

        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 2
        assert all(line.strip().isdigit() for line in lines)

    def test_tokens_only_shown_in_help(self, cli_runner: CliRunner) -> None:
        """Verify --tokens-only appears in check subcommand help output.

        Tests: Help documents the new flag on check command
        How: Run check --help and check for flag
        Why: Users need to discover the feature
        """
        result = cli_runner.invoke(plugin_validator.app, ["check", "--help"])

        assert result.exit_code == 0
        assert "--tokens-only" in result.stdout


class TestCLIMarkdownValidation:
    """Test CLI integration for general markdown file validation."""

    def test_claude_md_validation_passes(self, cli_runner: CliRunner, tmp_path: Path, no_color_env: None) -> None:
        """Verify CLAUDE.md files pass validation (no skill-specific checks).

        Tests: CLAUDE.md validation runs token counting only
        How: Create CLAUDE.md, validate with CLI
        Why: Previously CLAUDE.md was rejected as unknown file type
        """
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Project Instructions\n\nDo things.\n")

        result = cli_runner.invoke(plugin_validator.app, ["check", "--no-color", str(claude_md)])

        assert result.exit_code == 0

    def test_reference_md_validation_passes(self, cli_runner: CliRunner, tmp_path: Path, no_color_env: None) -> None:
        """Verify reference .md files pass validation.

        Tests: Reference docs validate with token counting
        How: Create references/doc.md, validate with CLI
        Why: Reference files should be countable without errors
        """
        refs_dir = tmp_path / "references"
        refs_dir.mkdir()
        ref_md = refs_dir / "guide.md"
        ref_md.write_text("# Guide\n\nReference content.\n")

        result = cli_runner.invoke(plugin_validator.app, ["check", "--no-color", str(ref_md)])

        assert result.exit_code == 0

    def test_readme_md_validation_passes(self, cli_runner: CliRunner, tmp_path: Path, no_color_env: None) -> None:
        """Verify README.md files pass validation.

        Tests: Generic markdown files validate correctly
        How: Create README.md, validate with CLI
        Why: General .md files should not be rejected
        """
        readme = tmp_path / "README.md"
        readme.write_text("# My Project\n\nProject documentation.\n")

        result = cli_runner.invoke(plugin_validator.app, ["check", "--no-color", str(readme)])

        assert result.exit_code == 0

    def test_verbose_shows_token_count_for_claude_md(
        self, cli_runner: CliRunner, tmp_path: Path, no_color_env: None
    ) -> None:
        """Verify verbose mode shows token count info for CLAUDE.md.

        Tests: Token count info visible in verbose output
        How: Validate CLAUDE.md with --verbose --no-color, check for token info
        Why: Users need to see token counts in verbose mode
        """
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Instructions\n\nContent for counting.\n")

        result = cli_runner.invoke(plugin_validator.app, ["check", "--verbose", "--no-color", str(claude_md)])

        assert result.exit_code == 0
        assert "tokens" in result.stdout.lower()

    def test_markdown_file_no_skill_validators(self, cli_runner: CliRunner, tmp_path: Path, no_color_env: None) -> None:
        """Verify markdown files don't run skill-specific validators.

        Tests: No description/trigger/complexity validators on generic markdown
        How: Create CLAUDE.md without frontmatter, ensure no SK* errors
        Why: Skill validators should only run on SKILL.md files
        """
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# No frontmatter here\n\nJust content.\n")

        result = cli_runner.invoke(plugin_validator.app, ["check", "--verbose", "--no-color", str(claude_md)])

        assert result.exit_code == 0
        # Should NOT contain skill-specific validator names
        assert "DescriptionValidator" not in result.stdout
        assert "ComplexityValidator" not in result.stdout
        assert "FrontmatterValidator" not in result.stdout
        # SHOULD contain the markdown token counter
        assert "MarkdownTokenCounter" in result.stdout
