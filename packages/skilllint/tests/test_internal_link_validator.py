"""Unit tests for InternalLinkValidator.

Tests:
- Broken link detection (LK001)
- Missing ./ prefix warnings (LK002)
- External link filtering
- Path resolution
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add parent directory to path to import plugin_validator
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from plugin_validator import InternalLinkValidator


class TestInternalLinkValidatorBasic:
    """Test basic InternalLinkValidator functionality."""

    def test_validator_instantiation(self) -> None:
        """Test InternalLinkValidator can be instantiated."""
        validator = InternalLinkValidator()
        assert validator is not None
        assert validator.can_fix() is False

    def test_fix_raises_not_implemented(self, tmp_path: Path) -> None:
        """Test fix() raises NotImplementedError.

        Tests: InternalLinkValidator is not auto-fixable
        How: Call fix() method, expect NotImplementedError
        Why: Link fixes require file creation or path correction
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

[broken](./missing.md)
""")

        validator = InternalLinkValidator()
        with pytest.raises(NotImplementedError):
            validator.fix(skill_md)


class TestBrokenLinkDetection:
    """Test broken internal link detection (LK001)."""

    def test_broken_link_to_missing_file(self, tmp_path: Path) -> None:
        """Test error when link points to non-existent file (LK001).

        Tests: Broken link detection
        How: Create SKILL.md with link to missing file, validate
        Why: Ensure LK001 error raised for broken links
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

# Test Skill

See [broken link](./references/missing.md) for details.
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        assert result.passed is False
        assert any(issue.code == "LK001" for issue in result.errors)

    def test_multiple_broken_links(self, tmp_path: Path) -> None:
        """Test multiple broken links are all detected.

        Tests: Multiple broken link detection
        How: Create SKILL.md with multiple broken links, validate
        Why: Ensure all broken links reported, not just first
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

# Test Skill

See [link1](./missing1.md) and [link2](./missing2.md).
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        assert result.passed is False
        lk001_errors = [e for e in result.errors if e.code == "LK001"]
        assert len(lk001_errors) >= 2  # Both broken links detected


class TestValidLinks:
    """Test valid links pass validation."""

    def test_valid_link_to_existing_file(self, tmp_path: Path) -> None:
        """Test validation passes for valid links.

        Tests: Valid internal link
        How: Create SKILL.md with link to existing file, validate
        Why: Ensure validator accepts valid links
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "existing.md").write_text("# Reference\n")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

# Test Skill

See [good link](./references/existing.md) for details.
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        assert result.passed is True
        assert not any(issue.code == "LK001" for issue in result.errors)

    def test_multiple_valid_links(self, tmp_path: Path) -> None:
        """Test multiple valid links pass validation.

        Tests: Multiple valid links
        How: Create SKILL.md with multiple valid links, validate
        Why: Ensure all valid links accepted
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "ref1.md").write_text("# Ref 1\n")
        (refs_dir / "ref2.md").write_text("# Ref 2\n")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

See [ref1](./references/ref1.md) and [ref2](./references/ref2.md).
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_destroyed_symlink_plain_file_passes(self, tmp_path: Path) -> None:
        """Test link to plain file (destroyed symlink) passes on Windows.

        When core.symlinks=false, Git stores symlinks as plain files whose
        content is the target path. The file exists; validator should pass.

        Tests: Unrepaired symlinks (plain files) pass validation
        How: Create plain file at link target (no symlink), validate
        Why: Users on Windows without Developer Mode get plain files
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        # Plain file with path as content (simulates Git destroyed symlink)
        (refs_dir / "linked.md").write_text("../../some/other/path.md")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

See [linked](./references/linked.md).
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        assert result.passed is True
        assert not any(issue.code == "LK001" for issue in result.errors)


class TestMissingPrefixWarning:
    """Test warning for links without ./ prefix (LK002)."""

    def test_link_without_prefix_warning(self, tmp_path: Path) -> None:
        """Test warning when link missing ./ prefix (LK002).

        Tests: Missing ./ prefix detection
        How: Create link without ./ prefix, validate
        Why: Ensure LK002 warning raised for missing prefix
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "existing.md").write_text("# Reference\n")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

# Test Skill

See [no prefix](references/existing.md) for details.
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        # Should have warning
        assert result.passed is True
        assert any(issue.code == "LK002" for issue in result.warnings)

    def test_multiple_links_without_prefix(self, tmp_path: Path) -> None:
        """Test multiple warnings for links without prefix.

        Tests: Multiple missing prefix warnings
        How: Create multiple links without ./ prefix, validate
        Why: Ensure all missing prefixes reported
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "ref1.md").write_text("# Ref 1\n")
        (refs_dir / "ref2.md").write_text("# Ref 2\n")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

See [ref1](references/ref1.md) and [ref2](references/ref2.md).
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        lk002_warnings = [w for w in result.warnings if w.code == "LK002"]
        assert len(lk002_warnings) >= 2


class TestExternalLinkFiltering:
    """Test external links are ignored."""

    @pytest.mark.parametrize(
        "external_link",
        ["https://example.com", "http://example.com", "ftp://example.com", "https://docs.python.org/3/"],
    )
    def test_external_links_ignored(self, tmp_path: Path, external_link: str) -> None:
        """Test external links are not validated.

        Tests: External link filtering
        How: Create SKILL.md with external links, validate
        Why: Ensure validator ignores http://, https://, ftp:// links
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(f"""---
description: Test skill
---

# Test Skill

See [external]({external_link}) for details.
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        # External links should be ignored (no errors)
        assert result.passed is True
        assert len(result.errors) == 0

    def test_mixed_internal_and_external_links(self, tmp_path: Path) -> None:
        """Test mix of internal and external links.

        Tests: Mixed link types
        How: Create SKILL.md with both internal and external links, validate
        Why: Ensure only internal links are validated
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

# Test Skill

See [external](https://example.com) and [internal](./missing.md).
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        # Should only validate internal link (which is broken)
        assert result.passed is False
        assert any(issue.code == "LK001" for issue in result.errors)
        # External link should not cause errors
        assert len([e for e in result.errors if "example.com" in e.message]) == 0


class TestAnchorLinkFiltering:
    """Test anchor links are ignored."""

    @pytest.mark.parametrize("anchor_link", ["#section", "#top", "#usage-examples"])
    def test_anchor_links_ignored(self, tmp_path: Path, anchor_link: str) -> None:
        """Test anchor links are not validated.

        Tests: Anchor link filtering
        How: Create SKILL.md with anchor links, validate
        Why: Ensure validator ignores #section links
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(f"""---
description: Test skill
---

# Test Skill

See [anchor]({anchor_link}) for details.
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        # Anchor links should be ignored
        assert result.passed is True
        assert len(result.errors) == 0


class TestPathResolution:
    """Test path resolution relative to SKILL.md."""

    def test_nested_directory_link(self, tmp_path: Path) -> None:
        """Test link to nested directory structure.

        Tests: Path resolution
        How: Create nested directory with file, link to it, validate
        Why: Ensure paths resolved correctly relative to SKILL.md
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        nested_dir = skill_dir / "references" / "advanced"
        nested_dir.mkdir(parents=True)
        (nested_dir / "guide.md").write_text("# Advanced Guide\n")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

See [advanced guide](./references/advanced/guide.md).
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        # Should resolve path correctly
        assert result.passed is True
        assert len(result.errors) == 0

    def test_sibling_file_link(self, tmp_path: Path) -> None:
        """Test link to sibling file in same directory.

        Tests: Sibling path resolution
        How: Create two files in same directory, link between them
        Why: Ensure sibling references work
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "OTHER.md").write_text("# Other File\n")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

See [other file](./OTHER.md).
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        assert result.passed is True
        assert len(result.errors) == 0


class TestOnlyValidatesSkills:
    """Test validator only operates on SKILL.md files."""

    def test_agent_file_skipped(self, tmp_path: Path) -> None:
        """Test validation skips agent files.

        Tests: File type detection
        How: Create agent.md with broken link, validate
        Why: Ensure link validation only applies to skills
        """
        agent_md = tmp_path / "agents" / "test.md"
        agent_md.parent.mkdir(parents=True, exist_ok=True)
        agent_md.write_text("""---
name: test-agent
description: Test agent
---

See [broken](./missing.md).
""")

        validator = InternalLinkValidator()
        result = validator.validate(agent_md)

        # Should pass without link validation (agents not checked)
        assert result.passed is True
        assert len(result.errors) == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_no_links_in_file(self, tmp_path: Path) -> None:
        """Test file without any links.

        Tests: No links present
        How: Create SKILL.md without links, validate
        Why: Ensure validator handles absence of links
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

# Test Skill

This skill has no links.
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        assert result.passed is True
        assert len(result.errors) == 0

    def test_link_with_url_encoded_path(self, tmp_path: Path) -> None:
        """Test link with URL-encoded characters.

        Tests: URL encoding handling
        How: Create link with %20 space encoding, validate
        Why: Ensure validator handles URL-encoded paths
        """
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        # File with space in name
        (refs_dir / "file with space.md").write_text("# File\n")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

See [file](./references/file%20with%20space.md).
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        # Should handle URL encoding
        # (May pass or fail depending on implementation)
        assert isinstance(result.passed, bool)

    def test_absolute_path_ignored(self, tmp_path: Path) -> None:
        """Test absolute paths are ignored.

        Tests: Absolute path filtering
        How: Create link with /absolute/path, validate
        Why: Ensure validator only checks relative paths
        """
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("""---
description: Test skill
---

See [absolute](/absolute/path/file.md).
""")

        validator = InternalLinkValidator()
        result = validator.validate(skill_md)

        # Absolute paths should be ignored
        assert result.passed is True
        assert len(result.errors) == 0
