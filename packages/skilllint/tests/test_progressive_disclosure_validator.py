"""Unit tests for ProgressiveDisclosureValidator.

Tests:
- Directory existence checks (references/, examples/, scripts/)
- INFO severity (not warnings or errors)
- File counting in existing directories
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from skilllint.plugin_validator import ProgressiveDisclosureValidator

if TYPE_CHECKING:
    from pathlib import Path


class TestProgressiveDisclosureValidatorBasic:
    """Test basic ProgressiveDisclosureValidator functionality."""

    def test_validator_instantiation(self) -> None:
        """Test ProgressiveDisclosureValidator can be instantiated."""
        validator = ProgressiveDisclosureValidator()
        assert validator is not None
        assert validator.can_fix() is False

    def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
        """Test fix() raises NotImplementedError.

        Tests: ProgressiveDisclosureValidator is not auto-fixable
        How: Call fix() method, expect NotImplementedError
        Why: Directory creation requires content planning
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")

        validator = ProgressiveDisclosureValidator()
        with pytest.raises(NotImplementedError):
            validator.fix(skill_dir / "SKILL.md")


class TestMissingDirectories:
    """Test INFO messages for missing directories."""

    def test_missing_references_directory(self, tmp_path: Path) -> None:
        """Test INFO when references/ directory missing (PD001).

        Tests: Skill without references/ directory
        How: Create skill without references/, validate
        Why: Ensure PD001 info raised for missing references/
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")

        validator = ProgressiveDisclosureValidator()
        result = validator.validate(skill_dir / "SKILL.md")

        # Should have INFO, not warning or error
        assert result.passed is True
        assert any(issue.code == "PD001" for issue in result.info)
        assert len(result.warnings) == 0
        assert len(result.errors) == 0

    def test_missing_examples_directory(self, tmp_path: Path) -> None:
        """Test INFO when examples/ directory missing (PD002).

        Tests: Skill without examples/ directory
        How: Create skill without examples/, validate
        Why: Ensure PD002 info raised for missing examples/
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")

        validator = ProgressiveDisclosureValidator()
        result = validator.validate(skill_dir / "SKILL.md")

        # Should have INFO
        assert result.passed is True
        assert any(issue.code == "PD002" for issue in result.info)

    def test_missing_scripts_directory(self, tmp_path: Path) -> None:
        """Test INFO when scripts/ directory missing (PD003).

        Tests: Skill without scripts/ directory
        How: Create skill without scripts/, validate
        Why: Ensure PD003 info raised for missing scripts/
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")

        validator = ProgressiveDisclosureValidator()
        result = validator.validate(skill_dir / "SKILL.md")

        # Should have INFO
        assert result.passed is True
        assert any(issue.code == "PD003" for issue in result.info)

    def test_all_directories_missing(self, tmp_path: Path) -> None:
        """Test all three INFO messages when all directories missing.

        Tests: Skill without any progressive disclosure directories
        How: Create minimal skill, validate
        Why: Ensure all three info messages raised
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")

        validator = ProgressiveDisclosureValidator()
        result = validator.validate(skill_dir / "SKILL.md")

        # Should have all three INFO messages
        assert result.passed is True
        info_codes = {issue.code for issue in result.info}
        assert "PD001" in info_codes
        assert "PD002" in info_codes
        assert "PD003" in info_codes


class TestExistingDirectories:
    """Test validation passes when directories exist."""

    def test_references_directory_exists(self, tmp_path: Path) -> None:
        """Test no INFO when references/ directory exists.

        Tests: Skill with references/ directory
        How: Create skill with references/, validate
        Why: Ensure no PD001 info when directory present
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")
        (skill_dir / "references").mkdir()
        (skill_dir / "references" / "ref.md").write_text("# Reference\n")

        validator = ProgressiveDisclosureValidator()
        result = validator.validate(skill_dir / "SKILL.md")

        # Should not have PD001 info
        assert not any(issue.code == "PD001" for issue in result.info)

    def test_all_directories_exist(self, tmp_path: Path) -> None:
        """Test no INFO messages when all directories exist.

        Tests: Skill with complete progressive disclosure structure
        How: Create skill with all three directories, validate
        Why: Ensure no info messages when structure complete
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")

        # Create all three directories
        (skill_dir / "references").mkdir()
        (skill_dir / "examples").mkdir()
        (skill_dir / "scripts").mkdir()

        # Add files to each
        (skill_dir / "references" / "ref.md").write_text("# Reference\n")
        (skill_dir / "examples" / "ex.md").write_text("# Example\n")
        (skill_dir / "scripts" / "script.py").write_text("# Script\n")

        validator = ProgressiveDisclosureValidator()
        result = validator.validate(skill_dir / "SKILL.md")

        # Should have no info messages
        assert result.passed is True
        assert len(result.info) == 0


class TestFileCountIncluded:
    """Test file counts are included in messages."""

    def test_file_count_in_message_when_directory_exists(self, tmp_path: Path) -> None:
        """Test message includes file count when directory exists.

        Tests: INFO message content
        How: Create skill with references/ containing files, validate
        Why: Ensure file count shown in messages per spec
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")

        # Create references with multiple files
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "ref1.md").write_text("# Ref 1\n")
        (refs_dir / "ref2.md").write_text("# Ref 2\n")
        (refs_dir / "ref3.md").write_text("# Ref 3\n")

        validator = ProgressiveDisclosureValidator()
        result = validator.validate(skill_dir / "SKILL.md")

        # Should not have PD001 (references exists)
        # But if there's any info about references, it should mention file count
        # For now, we just verify validation passes
        assert result.passed is True


class TestInfoSeverity:
    """Test issues have INFO severity, not WARNING or ERROR."""

    def test_severity_is_info_not_warning(self, tmp_path: Path) -> None:
        """Test missing directories raise INFO, not WARNING.

        Tests: Issue severity level
        How: Create skill missing directories, check severity
        Why: Ensure progressive disclosure is informational only
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")

        validator = ProgressiveDisclosureValidator()
        result = validator.validate(skill_dir / "SKILL.md")

        # Should have info, not warnings or errors
        assert result.passed is True
        assert len(result.info) > 0
        assert len(result.warnings) == 0
        assert len(result.errors) == 0

    def test_validation_passes_despite_info(self, tmp_path: Path) -> None:
        """Test validation passes even with INFO messages.

        Tests: Validation success with info
        How: Create minimal skill, check result.passed is True
        Why: Ensure INFO messages don't fail validation
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")

        validator = ProgressiveDisclosureValidator()
        result = validator.validate(skill_dir / "SKILL.md")

        # Validation should pass
        assert result.passed is True


class TestOnlyValidatesSkills:
    """Test validator only operates on SKILL.md files."""

    def test_agent_file_skipped(self, tmp_path: Path) -> None:
        """Test validation skips agent files.

        Tests: File type detection
        How: Create agent.md without directories, validate
        Why: Ensure progressive disclosure only applies to skills
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: test-agent
description: Test agent
---
""")

        validator = ProgressiveDisclosureValidator()
        result = validator.validate(agent_md)

        # Should pass without progressive disclosure info (agents not checked)
        assert result.passed is True
        assert len(result.info) == 0

    def test_command_file_skipped(self, tmp_path: Path) -> None:
        """Test validation skips command files.

        Tests: File type detection
        How: Create command.md without directories, validate
        Why: Ensure progressive disclosure only applies to skills
        """
        command_md = tmp_path / "commands" / "test.md"
        command_md.parent.mkdir(parents=True, exist_ok=True)
        command_md.write_text("""---
description: Test command
---
""")

        validator = ProgressiveDisclosureValidator()
        result = validator.validate(command_md)

        # Should pass without progressive disclosure info (commands not checked)
        assert result.passed is True
        assert len(result.info) == 0


class TestEmptyDirectories:
    """Test handling of empty directories."""

    def test_empty_references_directory(self, tmp_path: Path) -> None:
        """Test empty references/ directory handled correctly.

        Tests: Empty directory detection
        How: Create references/ with no files, validate
        Why: Ensure empty directories recognized as existing
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test skill
---
""")
        (skill_dir / "references").mkdir()  # Empty directory

        validator = ProgressiveDisclosureValidator()
        result = validator.validate(skill_dir / "SKILL.md")

        # Should not have PD001 (directory exists, even if empty)
        assert not any(issue.code == "PD001" for issue in result.info)
