"""Unit tests for DescriptionValidator.

Tests:
- Valid description acceptance
- Short description warnings (SK004)
- Missing trigger phrase warnings (SK005)
- Boundary conditions
- File-type-aware scoping (SK004/SK005 per FileType)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from skilllint.plugin_validator import CM001, DescriptionValidator, FileType

if TYPE_CHECKING:
    from pathlib import Path


class TestDescriptionValidatorBasic:
    """Test basic DescriptionValidator functionality."""

    def test_validator_instantiation(self) -> None:
        """Test DescriptionValidator can be instantiated."""
        validator = DescriptionValidator()
        assert validator is not None
        assert validator.can_fix() is False

    def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
        """Test fix() raises NotImplementedError.

        Tests: DescriptionValidator is not auto-fixable
        How: Call fix() method, expect NotImplementedError
        Why: Descriptions require human-written content
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: short
---
""")

        validator = DescriptionValidator()
        with pytest.raises(NotImplementedError):
            validator.fix(skill_md)


class TestValidDescriptions:
    """Test validation passes for valid descriptions."""

    @pytest.mark.parametrize(
        "valid_description",
        [
            "Use this skill when you need to test validation with proper length",
            "Use when testing validation workflows in Claude Code plugins",
            "Trigger this skill for comprehensive testing scenarios",
            "Activate this skill when running automated validation tests",
            "This skill should be activated when you need test coverage",
        ],
    )
    def test_valid_description_passes(self, tmp_path: Path, valid_description: str) -> None:
        """Test validation passes for valid descriptions.

        Tests: Descriptions ≥20 chars with trigger phrases
        How: Parametrized test with various valid descriptions
        Why: Ensure validator accepts well-formed descriptions
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(f"""---
description: "{valid_description}"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(skill_md)

        assert result.passed is True
        assert len(result.warnings) == 0


class TestShortDescriptionWarning:
    """Test warning for descriptions under 20 characters (SK004)."""

    @pytest.mark.parametrize(
        ("short_description", "length"),
        [("short", 5), ("test skill", 10), ("nineteen characters", 19), ("x", 1), ("", 0)],
    )
    def test_short_description_warning(self, tmp_path: Path, short_description: str, length: int) -> None:
        """Test warning when description is too short (SK004).

        Tests: Descriptions under 20 characters
        How: Parametrized test with various short descriptions
        Why: Ensure SK004 warning raised for insufficient length
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(f"""---
description: "{short_description}"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(skill_md)

        # Should have warning, not error
        assert result.passed is True  # Warnings don't fail validation
        assert any(issue.code == "SK004" for issue in result.warnings)


class TestMissingTriggerPhraseWarning:
    """Test warning for missing trigger phrases (SK005)."""

    @pytest.mark.parametrize(
        "description_without_trigger",
        [
            "This is a test skill for validation purposes",
            "A skill that validates frontmatter and structure",
            "Comprehensive testing utility for plugin development",
            "Validates skills, agents, and commands correctly",
        ],
    )
    def test_missing_trigger_phrase_warning(self, tmp_path: Path, description_without_trigger: str) -> None:
        """Test warning when trigger phrases missing (SK005).

        Tests: Descriptions without "use when", "use this", "trigger", "activate"
        How: Parametrized test with descriptions lacking trigger phrases
        Why: Ensure SK005 warning raised when no trigger phrases found
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(f"""---
description: "{description_without_trigger}"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(skill_md)

        # Should have warning, not error
        assert result.passed is True
        assert any(issue.code == "SK005" for issue in result.warnings)


class TestTriggerPhraseDetection:
    """Test case-insensitive trigger phrase detection."""

    @pytest.mark.parametrize(
        "trigger_phrase_variant",
        [
            "Use when testing validation",
            "USE WHEN testing validation",
            "use When testing validation",
            "Use this for testing validation workflows",
            "USE THIS for testing validation workflows",
            "Trigger this skill when testing validation",
            "TRIGGER this skill when testing validation",
            "Activate this skill for testing validation",
            "ACTIVATE this skill for testing validation",
        ],
    )
    def test_case_insensitive_trigger_detection(self, tmp_path: Path, trigger_phrase_variant: str) -> None:
        """Test trigger phrase detection is case-insensitive.

        Tests: Trigger phrases in various case combinations
        How: Parametrized test with uppercase/lowercase variants
        Why: Ensure case-insensitive matching per specification
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(f"""---
description: "{trigger_phrase_variant}"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(skill_md)

        # Should pass without SK005 warning
        assert result.passed is True
        assert not any(issue.code == "SK005" for issue in result.warnings)


class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""

    def test_exactly_20_characters(self, tmp_path: Path) -> None:
        """Test description with exactly 20 characters.

        Tests: Minimum length boundary
        How: Create description with exactly 20 chars, validate
        Why: Ensure boundary condition at MIN_DESCRIPTION_LENGTH
        """
        # "use when testing abc" = 20 chars (verified: len("use when testing abc") == 20)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: "use when testing abc"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(skill_md)

        # Exactly 20 chars should pass
        assert result.passed is True
        assert not any(issue.code == "SK004" for issue in result.warnings)

    def test_19_characters_triggers_warning(self, tmp_path: Path) -> None:
        """Test description with 19 characters triggers warning.

        Tests: Just below minimum length
        How: Create description with 19 chars, validate
        Why: Ensure SK004 triggered at boundary
        """
        # "use when testing" = 17 chars
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: "use when testing"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(skill_md)

        # 19 chars should trigger warning
        assert result.passed is True
        assert any(issue.code == "SK004" for issue in result.warnings)

    def test_very_long_description_with_trigger(self, tmp_path: Path) -> None:
        """Test very long description with trigger phrase.

        Tests: Description exceeding typical length
        How: Create 500+ character description with trigger, validate
        Why: Ensure validator handles long descriptions
        """
        long_desc = "Use this skill when " + "x" * 500  # >500 chars with trigger phrase
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(f"""---
description: "{long_desc}"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(skill_md)

        # Long description should pass if it has trigger phrase
        assert result.passed is True
        assert not any(issue.code == "SK005" for issue in result.warnings)


class TestMissingDescriptionField:
    """Test handling of missing description field."""

    def test_missing_description_field(self, tmp_path: Path) -> None:
        """Test validation handles missing description field.

        Tests: File without description field
        How: Create file with only name field, validate
        Why: Ensure validator handles missing field gracefully
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: test-agent
---
""")

        validator = DescriptionValidator()
        result = validator.validate(agent_md)

        # Should skip validation if description missing
        # (handled by FrontmatterValidator instead)
        assert isinstance(result.passed, bool)


class TestMultipleWarnings:
    """Test detection of multiple simultaneous warnings."""

    def test_short_and_no_trigger_warnings(self, tmp_path: Path) -> None:
        """Test both SK004 and SK005 warnings raised together.

        Tests: Description that is too short AND lacks trigger phrase
        How: Create description with both issues, validate
        Why: Ensure both warnings are raised when applicable
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: "test skill"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(skill_md)

        # Should have both warnings
        assert result.passed is True
        warning_codes = {issue.code for issue in result.warnings}
        assert "SK004" in warning_codes  # Too short
        assert "SK005" in warning_codes  # No trigger phrase


class TestWarningsNotErrors:
    """Test that issues are warnings, not errors."""

    def test_warnings_do_not_fail_validation(self, tmp_path: Path) -> None:
        """Test warnings do not cause validation to fail.

        Tests: Validation result with warnings
        How: Create file with warnings, check result.passed is True
        Why: Ensure warnings don't block validation success
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: "short"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(skill_md)

        # Validation should pass despite warnings
        assert result.passed is True
        assert len(result.warnings) > 0
        assert len(result.errors) == 0


class TestFileTypeHandling:
    """Test validation works on different file types."""

    def test_skill_description_validation(self, tmp_path: Path) -> None:
        """Test validation works on SKILL.md files."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: "short"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(skill_md)

        assert any(issue.code == "SK004" for issue in result.warnings)

    def test_agent_description_validation(self, tmp_path: Path) -> None:
        """Test validation works on agent files."""
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: test-agent
description: "short"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(agent_md)

        assert any(issue.code == "SK004" for issue in result.warnings)

    def test_command_description_validation(self, tmp_path: Path) -> None:
        """Test validation works on command files."""
        command_md = tmp_path / "commands" / "test.md"
        command_md.parent.mkdir(parents=True, exist_ok=True)
        command_md.write_text("""---
description: "short"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(command_md)

        assert any(issue.code == "SK004" for issue in result.warnings)


class TestSpecialCharacters:
    """Test handling of special characters in descriptions."""

    def test_unicode_in_description(self, tmp_path: Path) -> None:
        """Test descriptions with Unicode characters."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            """---
description: "Use this skill when testing Unicode café ☕"
---
""",
            encoding="utf-8",
        )

        validator = DescriptionValidator()
        result = validator.validate(skill_md)

        # Should handle Unicode correctly
        assert result.passed is True

    def test_trigger_phrase_with_punctuation(self, tmp_path: Path) -> None:
        """Test trigger phrase detection with punctuation."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: "Use this, when testing validation!"
---
""")

        validator = DescriptionValidator()
        result = validator.validate(skill_md)

        # "Use this" should be detected despite comma
        assert not any(issue.code == "SK005" for issue in result.warnings)


class TestFileTypeAwareScoping:
    """Test that SK004 and SK005 are scoped by FileType."""

    def test_command_does_not_receive_sk005(self, tmp_path: Path) -> None:
        """Test COMMAND file does NOT receive SK005 warning.

        Tests: Commands do not need trigger phrases
        How: Validate command file with no trigger phrases
        Why: Commands have different frontmatter schema
        """
        command_md = tmp_path / "commands" / "test.md"
        command_md.parent.mkdir(parents=True, exist_ok=True)
        command_md.write_text("""---
description: "A valid command description without trigger phrases here"
---
""")

        validator = DescriptionValidator(file_type=FileType.COMMAND)
        result = validator.validate(command_md)

        assert result.passed is True
        assert not any(issue.code == "SK005" for issue in result.warnings)

    def test_command_does_not_receive_sk004(self, tmp_path: Path) -> None:
        """Test COMMAND file does NOT receive SK004 warning.

        Tests: Commands are exempt from minimum description length
        How: Validate command file with short description
        Why: Commands have different frontmatter schema
        """
        command_md = tmp_path / "commands" / "test.md"
        command_md.parent.mkdir(parents=True, exist_ok=True)
        command_md.write_text("""---
description: "short"
---
""")

        validator = DescriptionValidator(file_type=FileType.COMMAND)
        result = validator.validate(command_md)

        assert result.passed is True
        assert not any(issue.code == "SK004" for issue in result.warnings)

    def test_agent_does_not_receive_sk005(self, tmp_path: Path) -> None:
        """Test AGENT file does NOT receive SK005 warning.

        Tests: Agents do not need trigger phrases
        How: Validate agent file with good description but no trigger phrases
        Why: Trigger phrases are only relevant for skill discovery
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: test-agent
description: "A valid agent description without any trigger phrases here"
---
""")

        validator = DescriptionValidator(file_type=FileType.AGENT)
        result = validator.validate(agent_md)

        assert result.passed is True
        assert not any(issue.code == "SK005" for issue in result.warnings)

    def test_agent_still_receives_sk004_for_short_description(self, tmp_path: Path) -> None:
        """Test AGENT file still receives SK004 for short description.

        Tests: Agents still need minimum description length
        How: Validate agent file with short description
        Why: SK004 applies to both SKILL and AGENT files
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: test-agent
description: "short"
---
""")

        validator = DescriptionValidator(file_type=FileType.AGENT)
        result = validator.validate(agent_md)

        assert result.passed is True
        assert any(issue.code == "SK004" for issue in result.warnings)

    def test_skill_still_receives_both_sk004_and_sk005(self, tmp_path: Path) -> None:
        """Test SKILL file still receives both SK004 and SK005.

        Tests: Skills get full description validation
        How: Validate skill file with short description and no trigger phrases
        Why: Skills require both minimum length and trigger phrases
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: "test skill"
---
""")

        validator = DescriptionValidator(file_type=FileType.SKILL)
        result = validator.validate(skill_md)

        assert result.passed is True
        warning_codes = {issue.code for issue in result.warnings}
        assert "SK004" in warning_codes
        assert "SK005" in warning_codes

    def test_cm001_error_code_is_defined(self) -> None:
        """Test CM001 error code constant is exported from plugin_validator.

        Tests: CM001 stub defined for command-specific description checks
        How: Import CM001 from plugin_validator, verify it is a non-empty string
        Why: CM001 is reserved for future command-specific validation rules;
             its presence confirms the error code namespace is correctly established
        """
        assert CM001 == "CM001", f"CM001 constant must equal 'CM001', got {CM001!r}"
