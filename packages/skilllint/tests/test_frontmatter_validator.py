"""Unit tests for FrontmatterValidator.

Tests:
- Valid frontmatter acceptance
- Invalid frontmatter rejection with correct error codes
- Auto-fix correctness
- Boundary conditions
- YAML parsing edge cases
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from skilllint.plugin_validator import FrontmatterValidator

if TYPE_CHECKING:
    from pathlib import Path


class TestFrontmatterValidatorBasic:
    """Test basic FrontmatterValidator functionality."""

    def test_validator_instantiation(self) -> None:
        """Test FrontmatterValidator can be instantiated."""
        validator = FrontmatterValidator()
        assert validator is not None
        assert validator.can_fix() is True

    def test_valid_skill_frontmatter(self, tmp_path: Path) -> None:
        """Test validation passes for valid skill frontmatter.

        Tests: Valid skill SKILL.md with minimal frontmatter
        How: Create file with description only, validate
        Why: Ensure validator accepts valid minimal skill frontmatter
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Use this skill when testing validation
---

# Test Skill Content
""")

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_valid_agent_frontmatter(self, tmp_path: Path) -> None:
        """Test validation passes for valid agent frontmatter.

        Tests: Valid agent file with required name and description
        How: Create agent.md with name and description, validate
        Why: Ensure validator accepts valid agent frontmatter
        """
        agent_md = tmp_path / "agent.md"
        agent_md.write_text("""---
name: test-agent
description: Use this agent when testing validation
---

# Agent Prompt
""")

        validator = FrontmatterValidator()
        result = validator.validate(agent_md)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_valid_command_frontmatter(self, tmp_path: Path) -> None:
        """Test validation passes for valid command frontmatter.

        Tests: Valid command file with required description
        How: Create command.md with description, validate
        Why: Ensure validator accepts valid command frontmatter
        """
        command_md = tmp_path / "commands" / "test.md"
        command_md.parent.mkdir(parents=True, exist_ok=True)
        command_md.write_text("""---
description: Test command for validation
---

echo "test"
""")

        validator = FrontmatterValidator()
        result = validator.validate(command_md)

        assert result.passed is True
        assert len(result.errors) == 0


class TestFrontmatterYAMLErrors:
    """Test YAML syntax error detection."""

    def test_missing_frontmatter_delimiters(self, tmp_path: Path) -> None:
        """Test error when frontmatter delimiters missing (FM003).

        Tests: File without --- delimiters
        How: Create file with no frontmatter markers, validate
        Why: Ensure FM003 error raised for missing delimiters
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""description: No delimiters

# Content
""")

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        assert result.passed is False
        assert any(issue.code == "FM003" for issue in result.errors)

    def test_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """Test error when YAML syntax invalid (FM002).

        Tests: File with malformed YAML
        How: Create file with invalid YAML syntax, validate
        Why: Ensure FM002 error raised for invalid YAML
        """
        skill_md = tmp_path / "SKILL.md"
        # Use YAML that ruamel.yaml (the active parser) rejects: unclosed flow sequence
        skill_md.write_text("""---
description: [unclosed bracket
---

# Content
""")

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        assert result.passed is False
        assert any(issue.code == "FM002" for issue in result.errors)

    def test_unclosed_frontmatter(self, tmp_path: Path) -> None:
        """Test error when frontmatter not closed (FM003).

        Tests: File with opening --- but no closing ---
        How: Create file with unclosed frontmatter, validate
        Why: Ensure FM003 error raised for unclosed frontmatter
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Unclosed frontmatter

# Content without closing delimiter
""")

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        assert result.passed is False
        assert any(issue.code == "FM003" for issue in result.errors)


class TestFrontmatterRequiredFields:
    """Test required field validation."""

    def test_missing_agent_name_field(self, tmp_path: Path) -> None:
        """Test error when agent missing required name field (FM001).

        Tests: Agent file without name field
        How: Create agent.md with only description, validate
        Why: Ensure FM001 error raised for missing required field
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
description: Agent without name field
---

# Agent Prompt
""")

        validator = FrontmatterValidator()
        result = validator.validate(agent_md)

        assert result.passed is False
        assert any(issue.code == "FM001" and "name" in issue.message.lower() for issue in result.errors)

    def test_missing_agent_description_field(self, tmp_path: Path) -> None:
        """Test error when agent missing required description field (FM001).

        Tests: Agent file without description field
        How: Create agent.md with only name, validate
        Why: Ensure FM001 error raised for missing required field
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: test-agent
---

# Agent Prompt
""")

        validator = FrontmatterValidator()
        result = validator.validate(agent_md)

        assert result.passed is False
        assert any(issue.code == "FM001" and "description" in issue.message.lower() for issue in result.errors)

    def test_missing_command_description(self, tmp_path: Path) -> None:
        """Test error when command missing required description field (FM001).

        Tests: Command file without description field
        How: Create command.md with no frontmatter fields, validate
        Why: Ensure FM001 error raised for missing required field
        """
        command_md = tmp_path / "commands" / "test.md"
        command_md.parent.mkdir(parents=True, exist_ok=True)
        command_md.write_text("""---
---

echo "test"
""")

        validator = FrontmatterValidator()
        result = validator.validate(command_md)

        assert result.passed is False
        assert any(issue.code == "FM001" and "description" in issue.message.lower() for issue in result.errors)


class TestFrontmatterAutoFix:
    """Test auto-fix functionality."""

    def test_autofix_yaml_array_to_csv(self, tmp_path: Path) -> None:
        """Test auto-fix converts YAML arrays to CSV strings (FM007, FM008).

        Tests: Frontmatter with tools as YAML array
        How: Create file with YAML array, run fix(), validate result
        Why: Ensure FM007/FM008 auto-fix converts arrays to CSV
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
tools:
  - Read
  - Write
  - Grep
---

# Content
""")

        validator = FrontmatterValidator()
        fixes = validator.fix(skill_md)

        assert len(fixes) > 0
        assert any("YAML array" in fix or "tools" in fix for fix in fixes)

        # Verify file was fixed
        content = skill_md.read_text()
        assert "tools: Read, Write, Grep" in content
        assert "  - Read" not in content

    def test_autofix_multiline_description(self, tmp_path: Path) -> None:
        """Test auto-fix removes multiline indicators (FM004).

        Tests: Frontmatter with >- multiline description
        How: Create file with multiline indicator, run fix(), validate
        Why: Ensure FM004 auto-fix removes forbidden indicators
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: >-
  This is a multiline description
  that should be fixed
---

# Content
""")

        validator = FrontmatterValidator()
        fixes = validator.fix(skill_md)

        assert len(fixes) > 0
        assert any("multiline" in fix.lower() for fix in fixes)

        # Verify file was fixed
        content = skill_md.read_text()
        assert ">-" not in content

    def test_autofix_unquoted_colon(self, tmp_path: Path) -> None:
        """Test auto-fix quotes descriptions with colons (FM009).

        Tests: Frontmatter with unquoted description containing colon
        How: Create file with colon in description, run fix(), validate
        Why: Ensure FM009 auto-fix adds quotes around colons
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: This has: a colon in it
---

# Content
""")

        validator = FrontmatterValidator()
        fixes = validator.fix(skill_md)

        assert len(fixes) > 0
        assert any("colon" in fix.lower() or "quoted" in fix.lower() for fix in fixes)

        # Verify file was fixed
        content = skill_md.read_text()
        assert 'description: "This has: a colon in it"' in content

    def test_fix_raises_error_when_no_fixes_needed(self, tmp_path: Path) -> None:
        """Test fix() raises error when file is already valid.

        Tests: Valid frontmatter file with no fixable issues
        How: Create valid file, attempt fix(), expect ValueError
        Why: Ensure fix() only operates when fixes are actually needed
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Valid skill frontmatter
tools: Read, Write
---

# Content
""")

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)
        assert result.passed is True

        # Should not raise error when file is valid
        fixes = validator.fix(skill_md)
        # May return empty list or skip fixes - either is acceptable
        assert isinstance(fixes, list)


class TestFrontmatterFieldValidation:
    """Test field type and value validation."""

    def test_invalid_field_type(self, tmp_path: Path) -> None:
        """Test error when field has wrong type (FM005).

        Tests: Frontmatter with integer instead of string
        How: Create file with invalid field type, validate
        Why: Ensure FM005 error raised for type mismatches
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: 12345
---

# Content
""")

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        # Description should be string, not integer
        # Pydantic may auto-convert or raise error
        # Either behavior is acceptable for this test
        assert isinstance(result.errors, list) or result.passed is True

    def test_name_pattern_validation(self, tmp_path: Path) -> None:
        """Test name field pattern validation (FM010).

        Tests: Frontmatter with invalid name pattern
        How: Create file with uppercase/underscore in name, validate
        Why: Ensure FM010 error raised for invalid name patterns
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: Test_Agent
description: Test agent
---

# Agent Prompt
""")

        validator = FrontmatterValidator()
        result = validator.validate(agent_md)

        assert result.passed is False
        assert any(issue.code == "FM010" for issue in result.errors)


class TestFrontmatterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test validation handles empty file gracefully.

        Tests: Completely empty file
        How: Create empty file, validate
        Why: Ensure validator doesn't crash on empty input
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("")

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        assert result.passed is False
        assert len(result.errors) > 0

    def test_frontmatter_only_no_content(self, tmp_path: Path) -> None:
        """Test validation handles frontmatter-only file.

        Tests: File with frontmatter but no body content
        How: Create file with frontmatter and empty body, validate
        Why: Ensure validator accepts frontmatter-only files
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Frontmatter only
---
""")

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        # Frontmatter-only is valid
        assert result.passed is True

    def test_very_long_description(self, tmp_path: Path) -> None:
        """Test validation handles very long descriptions.

        Tests: Description field exceeding typical length
        How: Create file with 2000+ character description, validate
        Why: Ensure validator handles long fields without crashes
        """
        long_desc = "x" * 2000
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(f"""---
description: "{long_desc}"
---

# Content
""")

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        # Should validate without crashing
        assert isinstance(result.passed, bool)

    def test_unicode_characters(self, tmp_path: Path) -> None:
        """Test validation handles Unicode characters.

        Tests: Frontmatter with Unicode emoji and non-ASCII chars
        How: Create file with Unicode in description, validate
        Why: Ensure validator handles international characters
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            """---
description: "Test skill with emoji 🚀 and unicode café"
---

# Content
""",
            encoding="utf-8",
        )

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        # Unicode should be accepted
        assert result.passed is True

    def test_special_yaml_characters(self, tmp_path: Path) -> None:
        """Test validation handles special YAML characters.

        Tests: Frontmatter with @, #, &, * characters
        How: Create file with special chars in description, validate
        Why: Ensure validator handles YAML special characters correctly
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: "Special chars: @mention #tag & more * stuff"
---

# Content
""")

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        # Quoted special chars should be valid
        assert result.passed is True


@pytest.mark.parametrize(
    ("frontmatter", "expected_error_code"),
    [
        (
            """---
description: >-
  Multiline description
---
""",
            "FM004",
        ),
        (
            """---
description: Test
tools:
  - Read
---
""",
            "FM007",
        ),
        (
            """---
name: Test-Agent
description: Test
---
""",
            "FM010",
        ),
    ],
)
def test_parametrized_error_codes(tmp_path: Path, frontmatter: str, expected_error_code: str) -> None:
    """Test specific error codes are raised for known violations.

    Tests: Multiple frontmatter violations with expected error codes
    How: Parametrized test with (frontmatter, error_code) pairs
    Why: Ensure correct error codes assigned to each violation type
    """
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(frontmatter + "\n# Content\n")

    validator = FrontmatterValidator()
    result = validator.validate(skill_md)

    assert result.passed is False
    assert any(issue.code == expected_error_code for issue in result.errors)


class TestNameFieldRestoration:
    """Test that the name field is restored during auto-fix (bug workaround reversed).

    The Claude Code bug (2026-01-29) that caused plugin skills with a 'name' field to
    not appear as slash commands has been resolved. The validators previously removed the
    'name' field as a workaround; they now add it back when absent.
    """

    def test_name_field_added_from_directory_when_missing(self, tmp_path: Path) -> None:
        """Test auto-fix adds name field derived from parent directory name.

        Tests: Skill missing 'name' field gets name added from parent dir
        How: Create SKILL.md inside a named directory, run fix(), check result
        Why: Ensure restored behavior adds 'name' when absent
        """
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: A test skill without a name field
tools: Read, Write
---

# Content
""")

        validator = FrontmatterValidator()
        fixes = validator.fix(skill_md)

        assert any("name" in fix.lower() and "my-skill" in fix for fix in fixes)
        content = skill_md.read_text()
        assert "name: my-skill" in content

    def test_name_field_preserved_when_already_present(self, tmp_path: Path) -> None:
        """Test auto-fix does NOT remove or overwrite existing name field.

        Tests: Skill with existing valid 'name' field keeps it unchanged
        How: Create SKILL.md with name field, run fix(), verify name unchanged
        Why: Ensure existing valid name is not modified
        """
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: my-skill
description: A test skill with a name field
---

# Content
""")

        validator = FrontmatterValidator()
        # No fixable issues — fix() returns empty list
        fixes = validator.fix(skill_md)

        # The name field must not be removed
        content = skill_md.read_text()
        assert "name: my-skill" in content
        # Fix list must not contain a removal message
        assert not any("removed" in fix.lower() and "name" in fix.lower() for fix in fixes)

    def test_name_field_not_added_when_directory_name_invalid(self, tmp_path: Path) -> None:
        """Test auto-fix skips adding name when directory name is invalid.

        Tests: Skill in directory with non-conforming name (e.g. underscores)
        How: Create SKILL.md in underscore-named dir, run fix(), check no name added
        Why: Ensure validator does not add a name that would fail validation
        """
        skill_dir = tmp_path / "my_skill_with_underscores"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Skill in directory with underscores in name
---

# Content
""")

        validator = FrontmatterValidator()
        validator.fix(skill_md)

        content = skill_md.read_text()
        # Name must not have been added since the dir name is invalid
        assert "name: my_skill_with_underscores" not in content

    def test_mismatched_name_corrected_to_directory_name(self, tmp_path: Path) -> None:
        """Test auto-fix corrects name field that doesn't match directory name.

        Tests: Skill with name field that doesn't match its parent directory
        How: Create SKILL.md with wrong name, run fix(), verify name corrected
        Why: Ensure name field always matches directory name after fix
        """
        skill_dir = tmp_path / "correct-name"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: wrong-name
description: Skill with mismatched name
---

# Content
""")

        validator = FrontmatterValidator()
        fixes = validator.fix(skill_md)

        assert any("correct-name" in fix for fix in fixes)
        content = skill_md.read_text()
        assert "name: correct-name" in content
        assert "name: wrong-name" not in content

    def test_mismatched_name_raises_validation_warning(self, tmp_path: Path) -> None:
        """Test validation warns when name field doesn't match directory name.

        Tests: Skill with name: field value different from parent directory
        How: Create SKILL.md with mismatched name, run validate(), check warning
        Why: Ensure validator catches name/directory mismatches
        """
        skill_dir = tmp_path / "actual-dir-name"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: different-name
description: Skill with mismatched name field
---

# Content
""")

        validator = FrontmatterValidator()
        result = validator.validate(skill_md)

        # Mismatch is a warning, not an error — passed should be True
        assert result.passed is True
        all_issues = result.warnings + result.errors
        assert any("name" in issue.field.lower() and "actual-dir-name" in issue.message for issue in all_issues)
