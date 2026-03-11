"""Unit tests for NameFormatValidator.

Tests:
- Valid name acceptance
- Invalid name rejection with correct error codes
- Boundary conditions
- Edge character patterns
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from skilllint.plugin_validator import NameFormatValidator

if TYPE_CHECKING:
    from pathlib import Path


class TestNameFormatValidatorBasic:
    """Test basic NameFormatValidator functionality."""

    def test_validator_instantiation(self) -> None:
        """Test NameFormatValidator can be instantiated."""
        validator = NameFormatValidator()
        assert validator is not None
        assert validator.can_fix() is True

    def test_fix_normalizes_uppercase_name(self, tmp_path: Path) -> None:
        """Test fix() normalizes uppercase name in frontmatter.

        Tests: NameFormatValidator auto-fixes SK001 (uppercase)
        How: Create skill with name: Test-Skill, run fix(), verify name is test-skill
        Why: Name format is auto-fixable on case-sensitive filesystems
        """
        skill_dir = tmp_path / "Test-Skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: Test-Skill
description: Test skill
---
""")

        validator = NameFormatValidator()
        fixes = validator.fix(skill_md)
        assert len(fixes) >= 1
        assert "Normalized name" in fixes[0]

        # fix() renames the directory from Test-Skill to test-skill,
        # so we must read from the new path
        fixed_skill_md = tmp_path / "test-skill" / "SKILL.md"
        content = fixed_skill_md.read_text()
        assert "name: test-skill" in content or 'name: "test-skill"' in content


class TestValidNames:
    """Test validation passes for valid name patterns."""

    @pytest.mark.parametrize(
        "valid_name",
        [
            "test-skill",  # Lowercase with hyphen
            "my-agent-v2",  # Multiple hyphens
            "agent",  # Single word
            "a",  # Single character
            "skill-123",  # With numbers
            "test-123-skill",  # Numbers in middle
            "x-y-z",  # Multiple single chars
        ],
    )
    def test_valid_name_patterns(self, tmp_path: Path, valid_name: str) -> None:
        """Test validation passes for valid name patterns.

        Tests: Various valid name formats
        How: Parametrized test with multiple valid names
        Why: Ensure validator accepts all valid naming patterns
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text(f"""---
name: {valid_name}
description: Test agent
---
""")

        validator = NameFormatValidator()
        result = validator.validate(agent_md)

        assert result.passed is True, f"Valid name '{valid_name}' failed validation"
        assert len(result.errors) == 0


class TestInvalidNamesUppercase:
    """Test uppercase character detection (SK001)."""

    @pytest.mark.parametrize(
        "invalid_name",
        [
            "Test-Skill",  # Title case
            "TEST-SKILL",  # All uppercase
            "test-Skill",  # Mixed case
            "testSkill",  # CamelCase
            "test-SkiLl",  # Random caps
        ],
    )
    def test_uppercase_detection(self, tmp_path: Path, invalid_name: str) -> None:
        """Test error when name contains uppercase characters (SK001).

        Tests: Names with uppercase letters
        How: Parametrized test with various uppercase patterns
        Why: Ensure SK001 error raised for any uppercase character
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text(f"""---
name: {invalid_name}
description: Test agent
---
""")

        validator = NameFormatValidator()
        result = validator.validate(agent_md)

        assert result.passed is False
        assert any(issue.code == "SK001" for issue in result.errors), (
            f"SK001 not found for '{invalid_name}', errors: {result.errors}"
        )


class TestInvalidNamesUnderscores:
    """Test underscore detection (SK002)."""

    @pytest.mark.parametrize(
        "invalid_name",
        [
            "test_skill",  # Single underscore
            "test__skill",  # Double underscore
            "test_skill_v2",  # Multiple underscores
            "_test",  # Leading underscore
            "test_",  # Trailing underscore
            "test-skill_name",  # Mixed hyphen and underscore
        ],
    )
    def test_underscore_detection(self, tmp_path: Path, invalid_name: str) -> None:
        """Test error when name contains underscores (SK002).

        Tests: Names with underscore characters
        How: Parametrized test with various underscore patterns
        Why: Ensure SK002 error raised for any underscore
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text(f"""---
name: {invalid_name}
description: Test agent
---
""")

        validator = NameFormatValidator()
        result = validator.validate(agent_md)

        assert result.passed is False
        assert any(issue.code == "SK002" for issue in result.errors), (
            f"SK002 not found for '{invalid_name}', errors: {result.errors}"
        )


class TestInvalidNamesHyphens:
    """Test hyphen placement detection (SK003)."""

    @pytest.mark.parametrize(
        ("invalid_name", "yaml_repr"),
        [
            ("-test", "-test"),  # Leading hyphen
            ("test-", "test-"),  # Trailing hyphen
            ("-test-", "-test-"),  # Both leading and trailing
            ("test--skill", "test--skill"),  # Consecutive hyphens
            ("test---skill", "test---skill"),  # Multiple consecutive hyphens
            ("-", '"-"'),  # Single hyphen only — must be quoted in YAML
            ("--test", "--test"),  # Multiple leading hyphens
            ("test--", "test--"),  # Multiple trailing hyphens
        ],
    )
    def test_hyphen_placement_detection(self, tmp_path: Path, invalid_name: str, yaml_repr: str) -> None:
        """Test error when name has invalid hyphen placement (SK003).

        Tests: Names with leading/trailing/consecutive hyphens
        How: Parametrized test with various hyphen patterns
        Why: Ensure SK003 error raised for invalid hyphen usage
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text(f"""---
name: {yaml_repr}
description: Test agent
---
""")

        validator = NameFormatValidator()
        result = validator.validate(agent_md)

        assert result.passed is False
        assert any(issue.code == "SK003" for issue in result.errors), (
            f"SK003 not found for '{invalid_name}', errors: {result.errors}"
        )


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_missing_name_field_skips_validation(self, tmp_path: Path) -> None:
        """Test validation skips when name field is missing.

        Tests: File without name field
        How: Create file with only description, validate
        Why: Ensure validator handles missing name gracefully (no crash)
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Test skill without name
---
""")

        validator = NameFormatValidator()
        result = validator.validate(skill_md)

        # Should pass since name field is optional for skills
        assert result.passed is True
        assert len(result.errors) == 0

    def test_empty_name_field(self, tmp_path: Path) -> None:
        """Test validation handles empty name field.

        Tests: Name field present but empty string
        How: Create file with name: "", validate
        Why: Ensure validator handles empty values gracefully
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: ""
description: Test agent
---
""")

        validator = NameFormatValidator()
        result = validator.validate(agent_md)

        # Empty name should fail validation
        assert result.passed is False

    def test_numeric_only_name(self, tmp_path: Path) -> None:
        """Test validation accepts numeric-only names.

        Tests: Name field with only numbers
        How: Create file with name: "123", validate
        Why: Ensure numeric names are valid per pattern
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: "123"
description: Test agent
---
""")

        validator = NameFormatValidator()
        result = validator.validate(agent_md)

        # Numeric-only names are valid
        assert result.passed is True

    def test_special_characters(self, tmp_path: Path) -> None:
        """Test validation rejects special characters.

        Tests: Name with @, #, $, %, etc.
        How: Create file with special char in name, validate
        Why: Ensure only alphanumeric and hyphens allowed
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: "test@skill"
description: Test agent
---
""")

        validator = NameFormatValidator()
        result = validator.validate(agent_md)

        # Special characters should fail
        assert result.passed is False

    def test_whitespace_in_name(self, tmp_path: Path) -> None:
        """Test validation rejects whitespace in names.

        Tests: Name with spaces
        How: Create file with "test skill" name, validate
        Why: Ensure spaces are not allowed in names
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: "test skill"
description: Test agent
---
""")

        validator = NameFormatValidator()
        result = validator.validate(agent_md)

        # Whitespace should fail
        assert result.passed is False


class TestFileTypeHandling:
    """Test validation works on different file types."""

    def test_skill_name_validation(self, tmp_path: Path) -> None:
        """Test validation works on SKILL.md files.

        Tests: Name validation in skill context
        How: Create SKILL.md with invalid name, validate
        Why: Ensure validator handles skill files correctly
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: Test_Skill
description: Test skill
---
""")

        validator = NameFormatValidator()
        result = validator.validate(skill_md)

        assert result.passed is False
        assert any(issue.code == "SK002" for issue in result.errors)

    def test_agent_name_validation(self, tmp_path: Path) -> None:
        """Test validation works on agent files.

        Tests: Name validation in agent context
        How: Create agent.md with invalid name, validate
        Why: Ensure validator handles agent files correctly
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: Test-Agent
description: Test agent
---
""")

        validator = NameFormatValidator()
        result = validator.validate(agent_md)

        assert result.passed is False
        assert any(issue.code == "SK001" for issue in result.errors)

    def test_command_name_validation(self, tmp_path: Path) -> None:
        """Test validation works on command files.

        Tests: Name validation in command context
        How: Create command.md with invalid name, validate
        Why: Ensure validator handles command files correctly
        """
        command_md = tmp_path / "commands" / "test.md"
        command_md.parent.mkdir(parents=True, exist_ok=True)
        command_md.write_text("""---
name: test_command
description: Test command
---
""")

        validator = NameFormatValidator()
        result = validator.validate(command_md)

        assert result.passed is False
        assert any(issue.code == "SK002" for issue in result.errors)


class TestMultipleErrors:
    """Test detection of multiple simultaneous violations."""

    def test_multiple_violations_reported(self, tmp_path: Path) -> None:
        """Test multiple name violations are all reported.

        Tests: Name with uppercase AND underscore
        How: Create file with multiple violations, validate
        Why: Ensure all violations are detected, not just first
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: Test_Agent-Name
description: Test agent
---
""")

        validator = NameFormatValidator()
        result = validator.validate(agent_md)

        assert result.passed is False
        # Should have both SK001 (uppercase) and SK002 (underscore)
        error_codes = {issue.code for issue in result.errors}
        assert "SK001" in error_codes or "SK002" in error_codes

    def test_leading_trailing_hyphens_with_uppercase(self, tmp_path: Path) -> None:
        """Test combination of hyphen and uppercase violations.

        Tests: Name with -Test- pattern
        How: Create file with leading hyphen and uppercase, validate
        Why: Ensure multiple error types detected together
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: -Test-
description: Test agent
---
""")

        validator = NameFormatValidator()
        result = validator.validate(agent_md)

        assert result.passed is False
        # Should detect multiple issues
        assert len(result.errors) >= 1
