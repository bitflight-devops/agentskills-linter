"""Tests for bundled schema accessibility via importlib.resources."""

from __future__ import annotations

import msgspec.json
from importlib.resources import files


def test_schema_file_readable_via_importlib_resources() -> None:
    """importlib.resources.files() can read v1.json from skilllint.schemas.claude_code."""
    ref = files("skilllint.schemas.claude_code").joinpath("v1.json")
    raw_bytes = ref.read_bytes()
    assert raw_bytes, "v1.json must not be empty"


def test_schema_json_is_valid() -> None:
    """v1.json contains valid JSON."""
    ref = files("skilllint.schemas.claude_code").joinpath("v1.json")
    data = msgspec.json.decode(ref.read_bytes())
    assert isinstance(data, dict), "Schema must be a JSON object"


def test_schema_has_dollar_schema_key() -> None:
    """v1.json contains the '$schema' key required by must_haves."""
    ref = files("skilllint.schemas.claude_code").joinpath("v1.json")
    data = msgspec.json.decode(ref.read_bytes())
    assert "$schema" in data, "Schema must have a '$schema' key"


def test_schema_has_platform_key() -> None:
    """v1.json contains a 'platform' key identifying the target platform."""
    ref = files("skilllint.schemas.claude_code").joinpath("v1.json")
    data = msgspec.json.decode(ref.read_bytes())
    assert data.get("platform") == "claude_code"


def test_load_bundled_schema_importable() -> None:
    """load_bundled_schema is exported from the skilllint package."""
    from skilllint import load_bundled_schema

    assert callable(load_bundled_schema)


def test_load_bundled_schema_returns_dict() -> None:
    """load_bundled_schema('claude_code') returns a dict."""
    from skilllint import load_bundled_schema

    result = load_bundled_schema("claude_code")
    assert isinstance(result, dict)


def test_load_bundled_schema_platform_value() -> None:
    """load_bundled_schema('claude_code') returns dict with platform == 'claude_code'."""
    from skilllint import load_bundled_schema

    result = load_bundled_schema("claude_code")
    assert result["platform"] == "claude_code"


def test_load_bundled_schema_version_param() -> None:
    """load_bundled_schema accepts an explicit version='v1' parameter."""
    from skilllint import load_bundled_schema

    result = load_bundled_schema("claude_code", version="v1")
    assert isinstance(result, dict)
