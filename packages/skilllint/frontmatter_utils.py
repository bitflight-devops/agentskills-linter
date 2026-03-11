"""Shared frontmatter utilities backed by ruamel.yaml.

Provides load/dump functions for YAML frontmatter files using
python-frontmatter with a ruamel.yaml round-trip handler.
The round-trip handler preserves formatting and only adds quotes
where YAML syntax demands them (e.g. colon-space in values).

Public API:
    load_frontmatter  -- Load frontmatter from a file path.
    loads_frontmatter -- Parse frontmatter from a string.
    dump_frontmatter  -- Serialize a Post object to a string.
    dumps_frontmatter -- Write a Post object to a file.
    update_field      -- Load a file, update one key, write back.
"""

from __future__ import annotations

import re
from io import StringIO
from typing import TYPE_CHECKING, TypeAlias

from frontmatter import Post, dump, dumps, load, loads
from frontmatter.default_handlers import BaseHandler
from ruamel.yaml import YAML

if TYPE_CHECKING:
    from pathlib import Path

# Recursive type for YAML/JSON-serializable frontmatter values. More specific than Any.
FrontmatterValue: TypeAlias = dict[str, "FrontmatterValue"] | list["FrontmatterValue"] | str | int | float | bool | None


class RuamelYAMLHandler(BaseHandler):
    """Frontmatter handler using ruamel.yaml in round-trip mode.

    Subclasses BaseHandler directly (not YAMLHandler) to avoid an upstream
    LSP conflict: YAMLHandler.load adds **kwargs that BaseHandler.load
    does not declare, making it impossible for a subclass to satisfy both
    signatures simultaneously under strict type checking.

    Overrides the default pyyaml-based handler so that:
    - Values without special YAML characters stay unquoted.
    - Values requiring quotes (colon-space) get single-quoted.
    - Unnecessary quotes from the source are stripped on round-trip.
    """

    FM_BOUNDARY = re.compile(r"^-{3,}\s*$", re.MULTILINE)
    START_DELIMITER = "---"
    END_DELIMITER = "---"

    def __init__(self) -> None:
        """Initialize handler with ruamel.yaml round-trip instance."""
        super().__init__()
        self._yaml = YAML(typ="rt")
        self._yaml.preserve_quotes = False
        # Prevent ruamel.yaml from wrapping long scalar values into block scalars.
        # Without this, descriptions longer than ~80 chars become multi-line
        # block scalars which break downstream validators expecting single-line strings.
        self._yaml.width = 2147483647

    @property
    def yaml(self) -> YAML:
        """Round-trip YAML instance for load/dump. Public for plugin_validator._dump_yaml."""
        return self._yaml

    def load(self, fm: str) -> dict[str, FrontmatterValue]:
        """Parse YAML frontmatter string using ruamel.yaml round-trip loader.

        Args:
            fm: Raw YAML frontmatter string (without delimiters).

        Returns:
            Parsed YAML data as a CommentedMap or None for empty input.
        """
        return self._yaml.load(fm)

    def export(self, metadata: dict[str, object], **kwargs: object) -> str:
        """Serialize metadata dict to YAML string using ruamel.yaml.

        Args:
            metadata: Frontmatter metadata dictionary.
            **kwargs: Accepted for API compatibility with BaseHandler; not used.

        Returns:
            YAML-formatted string without trailing newline.
        """
        buf = StringIO()
        self._yaml.dump(metadata, buf)
        return buf.getvalue().strip()


_handler = RuamelYAMLHandler()


def load_frontmatter(path: str | Path) -> Post:
    """Load frontmatter from a file path.

    Args:
        path: Path to a markdown file with YAML frontmatter.

    Returns:
        A frontmatter.Post with metadata and content attributes.
    """
    return load(str(path), handler=_handler)


def loads_frontmatter(text: str) -> Post:
    """Parse frontmatter from a string.

    Args:
        text: Markdown string potentially containing YAML frontmatter.

    Returns:
        A frontmatter.Post with metadata and content attributes.
    """
    return loads(text, handler=_handler)


def dump_frontmatter(post: Post) -> str:
    """Serialize a Post object to a string.

    Args:
        post: A frontmatter.Post object.

    Returns:
        Full markdown string with YAML frontmatter delimiters and body.
    """
    return dumps(post, handler=_handler)


def dumps_frontmatter(post: Post, path: str | Path) -> None:
    """Write a Post object to a file.

    Args:
        post: A frontmatter.Post object.
        path: Destination file path.
    """
    dump(post, str(path), handler=_handler)


def update_field(path: str | Path, key: str, value: FrontmatterValue) -> None:
    """Load a file, update one key, and write back.

    Args:
        path: Path to the markdown file.
        key: Frontmatter field name to set.
        value: New value for the field.
    """
    post = load_frontmatter(path)
    post.metadata[key] = value
    dumps_frontmatter(post, path)
