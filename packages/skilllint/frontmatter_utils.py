"""Frontmatter utilities (compatibility shim).

This module re-exports the new frontmatter API from frontmatter.py for
backward compatibility. The implementation no longer depends on python-frontmatter.
"""

from __future__ import annotations

from .frontmatter import (
    FrontmatterValue,
    Post,
    dump_frontmatter,
    dumps_frontmatter,
    load_frontmatter,
    loads_frontmatter,
    update_field,
)

__all__ = [
    "FrontmatterValue",
    "Post",
    "dump_frontmatter",
    "dumps_frontmatter",
    "load_frontmatter",
    "loads_frontmatter",
    "update_field",
]
