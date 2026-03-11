"""Internal module for loading bundled platform schemas."""

from __future__ import annotations

import json
from importlib.resources import files


def load_bundled_schema(platform: str, version: str = "v1") -> dict:
    """Load a bundled platform schema snapshot.

    Args:
        platform: Platform identifier, e.g. 'claude_code'
        version: Schema version, defaults to 'v1'

    Returns:
        Parsed JSON schema as a dict
    """
    ref = files(f"skilllint.schemas.{platform}").joinpath(f"{version}.json")
    return json.loads(ref.read_bytes())
