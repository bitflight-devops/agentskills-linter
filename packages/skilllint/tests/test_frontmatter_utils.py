"""Tests for frontmatter_utils module.

Tests the shared frontmatter utility module backed by ruamel.yaml.
Covers the RuamelYAMLHandler, convenience API, and edge cases.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class TestRuamelYAMLHandler:
    """Tests for the RuamelYAMLHandler subclass."""

    def test_load_simple_frontmatter(self) -> None:
        """Handler parses simple frontmatter without quotes."""
        from skilllint.frontmatter_utils import loads_frontmatter

        text = "---\ndescription: A simple skill\ntools: Read, Write\n---\n\n# Body\n"
        post = loads_frontmatter(text)

        assert post.metadata["description"] == "A simple skill"
        assert post.metadata["tools"] == "Read, Write"

    def test_load_quoted_frontmatter(self) -> None:
        """Handler preserves quotes when YAML syntax requires them."""
        from skilllint.frontmatter_utils import loads_frontmatter

        text = '---\ndescription: "Has colon: in value"\n---\n\n# Body\n'
        post = loads_frontmatter(text)

        assert post.metadata["description"] == "Has colon: in value"

    def test_load_no_frontmatter(self) -> None:
        """Handler returns empty metadata for files without frontmatter."""
        from skilllint.frontmatter_utils import loads_frontmatter

        text = "# Just a heading\n\nSome content.\n"
        post = loads_frontmatter(text)

        assert post.metadata == {}
        assert "Just a heading" in post.content

    def test_roundtrip_preserves_unquoted(self) -> None:
        """Round-trip does not add unnecessary quotes."""
        from skilllint.frontmatter_utils import dump_frontmatter, loads_frontmatter

        text = "---\ndescription: Simple value\nname: test-skill\n---\n\n# Body\n"
        post = loads_frontmatter(text)
        result = dump_frontmatter(post)

        assert "description: Simple value" in result
        assert "name: test-skill" in result
        assert '"' not in result.split("---")[1]
        assert "'" not in result.split("---")[1]

    def test_roundtrip_preserves_required_quotes(self) -> None:
        """Round-trip keeps quotes where YAML demands them (colon-space)."""
        from skilllint.frontmatter_utils import dump_frontmatter, loads_frontmatter

        text = '---\ndescription: "Has colon: in value"\n---\n\n# Body\n'
        post = loads_frontmatter(text)
        result = dump_frontmatter(post)

        lines = result.split("\n")
        desc_line = next(line for line in lines if line.startswith("description:"))
        assert "Has colon: in value" in desc_line
        assert "'" in desc_line or '"' in desc_line

    def test_roundtrip_removes_unnecessary_quotes(self) -> None:
        """Round-trip strips quotes that YAML does not require."""
        from skilllint.frontmatter_utils import dump_frontmatter, loads_frontmatter

        text = '---\ndescription: "No special characters here"\n---\n\n# Body\n'
        post = loads_frontmatter(text)
        result = dump_frontmatter(post)

        lines = result.split("\n")
        desc_line = next(line for line in lines if line.startswith("description:"))
        assert desc_line == "description: No special characters here"


class TestConvenienceAPI:
    """Tests for the module-level convenience functions."""

    def test_loads_frontmatter_from_string(self) -> None:
        """Parse frontmatter from a string."""
        from skilllint.frontmatter_utils import loads_frontmatter

        text = "---\nname: my-skill\ndescription: A test\n---\n\nContent here.\n"
        post = loads_frontmatter(text)

        assert post.metadata["name"] == "my-skill"
        assert post.metadata["description"] == "A test"
        assert post.content == "Content here."

    def test_dumps_frontmatter_to_file(self, tmp_path: Path) -> None:
        """Write frontmatter post to a file."""
        from skilllint.frontmatter_utils import dumps_frontmatter, load_frontmatter, loads_frontmatter

        text = "---\nname: my-skill\n---\n\n# Body\n"
        post = loads_frontmatter(text)

        target = tmp_path / "output.md"
        dumps_frontmatter(post, target)

        assert target.exists()
        reloaded = load_frontmatter(target)
        assert reloaded.metadata["name"] == "my-skill"

    def test_update_field_existing(self, tmp_path: Path) -> None:
        """Update an existing field without re-serializing everything."""
        from skilllint.frontmatter_utils import load_frontmatter, update_field

        md_file = tmp_path / "test.md"
        md_file.write_text("---\nname: old-name\ndescription: Keep this\n---\n\n# Body\n")

        update_field(md_file, "name", "new-name")

        post = load_frontmatter(md_file)
        assert post.metadata["name"] == "new-name"
        assert post.metadata["description"] == "Keep this"

    def test_update_field_new(self, tmp_path: Path) -> None:
        """Add a new field that did not exist."""
        from skilllint.frontmatter_utils import load_frontmatter, update_field

        md_file = tmp_path / "test.md"
        md_file.write_text("---\nname: my-skill\n---\n\n# Body\n")

        update_field(md_file, "model", "sonnet")

        post = load_frontmatter(md_file)
        assert post.metadata["model"] == "sonnet"
        assert post.metadata["name"] == "my-skill"

    def test_body_content_preserved(self) -> None:
        """Markdown body with code blocks and special chars survives round-trip."""
        from skilllint.frontmatter_utils import dump_frontmatter, loads_frontmatter

        body = "# Title\n\n```python\ndef foo():\n    return 'bar: baz'\n```\n\n> Quote with special chars: <>&"
        text = f"---\nname: test\n---\n\n{body}\n"
        post = loads_frontmatter(text)
        result = dump_frontmatter(post)

        assert "def foo():" in result
        assert "return 'bar: baz'" in result
        assert "> Quote with special chars: <>&" in result


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty file does not crash."""
        from skilllint.frontmatter_utils import load_frontmatter

        md_file = tmp_path / "empty.md"
        md_file.write_text("")

        post = load_frontmatter(md_file)
        assert post.metadata == {}
        assert post.content == ""

    def test_frontmatter_with_boolean_values(self) -> None:
        """Boolean-like strings preserved as strings when quoted, actual booleans as True."""
        from skilllint.frontmatter_utils import loads_frontmatter

        text = '---\nuser-invocable: true\nquoted_bool: "true"\n---\n\n# Body\n'
        post = loads_frontmatter(text)

        assert post.metadata["user-invocable"] is True
        assert post.metadata["quoted_bool"] == "true"

    def test_frontmatter_with_list_values(self) -> None:
        """List values handled correctly."""
        from skilllint.frontmatter_utils import loads_frontmatter

        text = "---\nitems:\n  - one\n  - two\n  - three\n---\n\n# Body\n"
        post = loads_frontmatter(text)

        assert post.metadata["items"] == ["one", "two", "three"]

    def test_unicode_in_description(self) -> None:
        """Unicode characters survive round-trip (em-dashes, curly quotes)."""
        from skilllint.frontmatter_utils import dump_frontmatter, loads_frontmatter

        text = "---\ndescription: Uses em\u2014dash and \u201ccurly quotes\u201d\n---\n\n# Body\n"
        post = loads_frontmatter(text)
        result = dump_frontmatter(post)

        assert "\u2014" in result
        assert "\u201c" in result
        assert "\u201d" in result
