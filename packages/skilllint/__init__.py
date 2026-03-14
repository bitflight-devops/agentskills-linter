"""skilllint — static analysis linter for Claude Code plugins, skills, and agents."""

from __future__ import annotations

from skilllint.schemas import load_bundled_schema
from skilllint.version import __version__

__all__ = ["__version__", "load_bundled_schema"]
