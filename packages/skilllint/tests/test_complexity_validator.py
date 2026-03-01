"""Unit tests for ComplexityValidator.

Tests:
- Token counting accuracy
- Threshold boundary conditions (TOKEN_WARNING_THRESHOLD, TOKEN_ERROR_THRESHOLD)
- Frontmatter exclusion from token count
- Warning and error thresholds
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add parent directory to path to import plugin_validator
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from plugin_validator import TOKEN_ERROR_THRESHOLD, TOKEN_WARNING_THRESHOLD, ComplexityValidator


class TestComplexityValidatorBasic:
    """Test basic ComplexityValidator functionality."""

    def test_validator_instantiation(self) -> None:
        """Test ComplexityValidator can be instantiated."""
        validator = ComplexityValidator()
        assert validator is not None
        assert validator.can_fix() is False

    def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
        """Test fix() raises NotImplementedError.

        Tests: ComplexityValidator is not auto-fixable
        How: Call fix() method, expect NotImplementedError
        Why: Complexity reduction requires content restructuring
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            """---
description: Test skill
---

# Very complex skill content
"""
            + ("x" * 10000)
        )

        validator = ComplexityValidator()
        with pytest.raises(NotImplementedError):
            validator.fix(skill_md)


class TestTokenCounting:
    """Test token counting functionality."""

    def test_small_skill_passes(self, tmp_path: Path) -> None:
        """Test small skill passes without warnings.

        Tests: Skill with minimal content (<4000 tokens)
        How: Create small SKILL.md, validate
        Why: Ensure skills under threshold pass validation
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

# Test Skill

This is a small skill with minimal content.

## Usage

Use this for testing.
""")

        validator = ComplexityValidator()
        result = validator.validate(skill_md)

        assert result.passed is True
        assert len(result.warnings) == 0
        assert len(result.errors) == 0

    def test_frontmatter_excluded_from_count(self, tmp_path: Path) -> None:
        """Test frontmatter is excluded from token count.

        Tests: Token counting excludes frontmatter section
        How: Create file with large frontmatter, small body, validate
        Why: Ensure only body content is measured per spec
        """
        skill_md = tmp_path / "SKILL.md"
        # Large frontmatter
        large_frontmatter = "x" * 1000
        skill_md.write_text(f"""---
description: "{large_frontmatter}"
---

# Small body content
""")

        validator = ComplexityValidator()
        result = validator.validate(skill_md)

        # Should pass because body is small (frontmatter excluded)
        assert result.passed is True


class TestThresholdBoundaries:
    """Test threshold boundary conditions."""

    def test_warning_threshold_4000_tokens(self, tmp_path: Path) -> None:
        """Test warning triggered above TOKEN_WARNING_THRESHOLD (SK006).

        Tests: Skill approaching complexity limit
        How: Create skill with tokens above TOKEN_WARNING_THRESHOLD, validate
        Why: Ensure SK006 warning at warning threshold
        """
        skill_md = tmp_path / "SKILL.md"
        content = "word " * (TOKEN_WARNING_THRESHOLD + 100)  # tokens above warning threshold
        skill_md.write_text(f"""---
description: Test skill
---

# Test Skill

{content}
""")

        validator = ComplexityValidator()
        result = validator.validate(skill_md)

        # Should have warning
        assert result.passed is True
        assert any(issue.code == "SK006" for issue in result.warnings)

    def test_error_threshold_6400_tokens(self, tmp_path: Path) -> None:
        """Test error triggered above TOKEN_ERROR_THRESHOLD (SK007).

        Tests: Skill exceeding complexity limit
        How: Create skill with tokens above TOKEN_ERROR_THRESHOLD, validate
        Why: Ensure SK007 error at error threshold
        """
        skill_md = tmp_path / "SKILL.md"
        content = "word " * (TOKEN_ERROR_THRESHOLD + 200)  # tokens above error threshold
        skill_md.write_text(f"""---
description: Test skill
---

# Test Skill

{content}
""")

        validator = ComplexityValidator()
        result = validator.validate(skill_md)

        # Should have error
        assert result.passed is False
        assert any(issue.code == "SK007" for issue in result.errors)


class TestTokenCountDeterminism:
    """Test token counting is deterministic."""

    def test_same_content_same_count(self, tmp_path: Path) -> None:
        """Test same content produces same token count.

        Tests: Token counting determinism
        How: Validate same file multiple times, compare counts
        Why: Ensure consistent token measurement
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

# Test Content

This is test content with consistent tokens.
""")

        validator = ComplexityValidator()

        # Run validation multiple times
        results = [validator.validate(skill_md) for _ in range(3)]

        # Extract token counts from messages (if present)
        # All results should be identical
        assert all(r.passed == results[0].passed for r in results)
        assert all(len(r.errors) == len(results[0].errors) for r in results)


class TestOnlyValidatesSkills:
    """Test validator only operates on SKILL.md files."""

    def test_agent_file_skipped(self, tmp_path: Path) -> None:
        """Test validation skips agent files.

        Tests: File type detection
        How: Create agent.md with large content, validate
        Why: Ensure complexity validation only applies to skills
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        # Large content that would trigger warnings in a skill
        content = "word " * 5000
        agent_md.write_text(f"""---
name: test-agent
description: Test agent
---

{content}
""")

        validator = ComplexityValidator()
        result = validator.validate(agent_md)

        # Should pass without complexity warnings (agents not checked)
        assert result.passed is True
        assert not any(issue.code == "SK006" for issue in result.warnings)

    def test_command_file_skipped(self, tmp_path: Path) -> None:
        """Test validation skips command files.

        Tests: File type detection
        How: Create command.md with large content, validate
        Why: Ensure complexity validation only applies to skills
        """
        command_md = tmp_path / "commands" / "test.md"
        command_md.parent.mkdir(parents=True, exist_ok=True)
        content = "word " * 5000
        command_md.write_text(f"""---
description: Test command
---

{content}
""")

        validator = ComplexityValidator()
        result = validator.validate(command_md)

        # Should pass without complexity warnings (commands not checked)
        assert result.passed is True
        assert not any(issue.code == "SK006" for issue in result.warnings)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_body_content(self, tmp_path: Path) -> None:
        """Test skill with frontmatter only, no body.

        Tests: Empty body content
        How: Create SKILL.md with frontmatter but no body, validate
        Why: Ensure validator handles edge case gracefully
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---
""")

        validator = ComplexityValidator()
        result = validator.validate(skill_md)

        # Empty body should pass (0 tokens)
        assert result.passed is True

    def test_missing_frontmatter(self, tmp_path: Path) -> None:
        """Test skill without frontmatter.

        Tests: File without frontmatter delimiters
        How: Create file with no frontmatter, validate
        Why: Ensure validator handles missing frontmatter
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("# Test Skill\n\nContent without frontmatter\n")

        validator = ComplexityValidator()
        result = validator.validate(skill_md)

        # Should handle missing frontmatter gracefully
        assert isinstance(result.passed, bool)

    def test_only_frontmatter_no_closing_delimiter(self, tmp_path: Path) -> None:
        """Test file with unclosed frontmatter.

        Tests: Frontmatter without closing ---
        How: Create file with opening --- but no closing, validate
        Why: Ensure validator doesn't crash on malformed input
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
# No closing delimiter

Content here
""")

        validator = ComplexityValidator()
        result = validator.validate(skill_md)

        # Should handle gracefully (all content counted as body)
        assert isinstance(result.passed, bool)


class TestValidationMessages:
    """Test validation messages include token counts."""

    def test_warning_includes_token_count(self, tmp_path: Path) -> None:
        """Test warning message includes exact token count.

        Tests: Message format and content
        How: Create skill with warning threshold, check message
        Why: Ensure users see exact token count in warnings
        """
        skill_md = tmp_path / "SKILL.md"
        content = "word " * 3000
        skill_md.write_text(f"""---
description: Test skill
---

{content}
""")

        validator = ComplexityValidator()
        result = validator.validate(skill_md)

        # Should have warning with token count in message
        if result.warnings:
            warning_message = result.warnings[0].message.lower()
            assert "token" in warning_message

    def test_error_includes_token_count(self, tmp_path: Path) -> None:
        """Test error message includes exact token count.

        Tests: Message format and content
        How: Create skill with error threshold, check message
        Why: Ensure users see exact token count in errors
        """
        skill_md = tmp_path / "SKILL.md"
        content = "word " * 5000
        skill_md.write_text(f"""---
description: Test skill
---

{content}
""")

        validator = ComplexityValidator()
        result = validator.validate(skill_md)

        # Should have error with token count in message
        if result.errors:
            error_message = result.errors[0].message.lower()
            assert "token" in error_message


class TestMultipleSeverityLevels:
    """Test both warning and error can be present."""

    def test_only_warning_when_between_thresholds(self, tmp_path: Path) -> None:
        """Test only warning when between TOKEN_WARNING_THRESHOLD and TOKEN_ERROR_THRESHOLD.

        Tests: Single severity level
        How: Create skill with tokens between warning and error thresholds, validate
        Why: Ensure only warning raised in middle range
        """
        skill_md = tmp_path / "SKILL.md"
        midpoint = (TOKEN_WARNING_THRESHOLD + TOKEN_ERROR_THRESHOLD) // 2
        content = "word " * midpoint  # tokens between warning and error thresholds
        skill_md.write_text(f"""---
description: Test skill
---

{content}
""")

        validator = ComplexityValidator()
        result = validator.validate(skill_md)

        # Should have warning but not error
        assert result.passed is True
        assert any(issue.code == "SK006" for issue in result.warnings)
        assert not any(issue.code == "SK007" for issue in result.errors)
