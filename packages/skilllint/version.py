# /// script
# List dependencies for linting only
# dependencies = [
#   "hatchling>=1.14.0",
# ]
# ///
"""Compute the version number and store it in the `__version__` variable.

Based on <https://github.com/maresb/hatch-vcs-footgun-example>.
"""

from __future__ import annotations

import pathlib
from importlib.metadata import version as _metadata_version

try:
    from hatchling.metadata.core import ProjectMetadata
    from hatchling.plugin.manager import PluginManager
    from hatchling.utils.fs import locate_file

    _HAS_HATCHLING = True
except ImportError:
    _HAS_HATCHLING = False


def _get_hatch_version() -> str | None:
    if not _HAS_HATCHLING:
        return None

    pyproject_toml = locate_file(__file__, "pyproject.toml")
    if pyproject_toml is None:
        raise RuntimeError("pyproject.toml not found although hatchling is installed")
    root = pathlib.Path(pyproject_toml).parent
    metadata = ProjectMetadata(root=str(root), plugin_manager=PluginManager())
    return str(metadata.core.version or metadata.hatch.version.cached)


def _get_importlib_metadata_version() -> str:
    return _metadata_version(__package__ or __name__)


__version__ = _get_hatch_version() or _get_importlib_metadata_version()
