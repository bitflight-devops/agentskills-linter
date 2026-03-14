"""Tests for bundled schema accessibility via importlib.resources."""

from __future__ import annotations

from importlib.resources import files

import msgspec.json
import pytest

from skilllint.schemas import get_provider_ids, load_provider_schema


class TestSchemaFileImportlibAccess:
    """Tests for schema file access via importlib.resources."""

    @pytest.mark.parametrize("provider", get_provider_ids())
    def test_schema_file_readable_via_importlib_resources(self, provider: str) -> None:
        """importlib.resources.files() can read v1.json from each provider."""
        ref = files(f"skilllint.schemas.{provider}").joinpath("v1.json")
        raw_bytes = ref.read_bytes()
        assert raw_bytes, f"{provider}/v1.json must not be empty"

    @pytest.mark.parametrize("provider", get_provider_ids())
    def test_schema_json_is_valid(self, provider: str) -> None:
        """Each provider's v1.json contains valid JSON."""
        ref = files(f"skilllint.schemas.{provider}").joinpath("v1.json")
        data = msgspec.json.decode(ref.read_bytes())
        assert isinstance(data, dict), f"{provider}: schema must be a JSON object"

    @pytest.mark.parametrize("provider", get_provider_ids())
    def test_schema_has_dollar_schema_key(self, provider: str) -> None:
        """Each provider's v1.json contains the '$schema' key."""
        ref = files(f"skilllint.schemas.{provider}").joinpath("v1.json")
        data = msgspec.json.decode(ref.read_bytes())
        assert "$schema" in data, f"{provider}: schema must have a '$schema' key"

    @pytest.mark.parametrize("provider", get_provider_ids())
    def test_schema_has_platform_key(self, provider: str) -> None:
        """Each provider's v1.json contains a 'platform' key matching the provider."""
        ref = files(f"skilllint.schemas.{provider}").joinpath("v1.json")
        data = msgspec.json.decode(ref.read_bytes())
        assert data.get("platform") == provider, f"{provider}: schema platform key must match provider name"


class TestLoadProviderSchema:
    """Tests for load_provider_schema function covering all providers."""

    @pytest.mark.parametrize("provider", get_provider_ids())
    def test_load_provider_schema_returns_dict(self, provider: str) -> None:
        """load_provider_schema returns a dict for each provider."""
        result = load_provider_schema(provider)
        assert isinstance(result, dict), f"{provider}: schema must be a dict"

    @pytest.mark.parametrize("provider", get_provider_ids())
    def test_load_provider_schema_platform_value(self, provider: str) -> None:
        """load_provider_schema returns dict with platform matching provider."""
        result = load_provider_schema(provider)
        assert result["platform"] == provider, f"{provider}: platform key must match provider name"

    @pytest.mark.parametrize("provider", get_provider_ids())
    def test_load_provider_schema_has_provenance(self, provider: str) -> None:
        """load_provider_schema returns dict with provenance object."""
        result = load_provider_schema(provider)
        assert "provenance" in result, f"{provider}: missing 'provenance' key"
        prov = result["provenance"]
        assert "authority_url" in prov, f"{provider}: missing authority_url in provenance"
        assert "last_verified" in prov, f"{provider}: missing last_verified in provenance"
        assert "provider_id" in prov, f"{provider}: missing provider_id in provenance"

    @pytest.mark.parametrize("provider", get_provider_ids())
    def test_load_provider_schema_version_param(self, provider: str) -> None:
        """load_provider_schema accepts an explicit version='v1' parameter."""
        result = load_provider_schema(provider, version="v1")
        assert isinstance(result, dict), f"{provider}: schema with version param must be a dict"


class TestBackwardsCompatibleAlias:
    """Tests for load_bundled_schema backwards-compatible alias."""

    def test_load_bundled_schema_importable(self) -> None:
        """load_bundled_schema is exported from the skilllint package."""
        from skilllint import load_bundled_schema

        assert callable(load_bundled_schema)

    def test_load_bundled_schema_returns_dict(self) -> None:
        """load_bundled_schema('claude_code') returns a dict."""
        from skilllint import load_bundled_schema

        result = load_bundled_schema("claude_code")
        assert isinstance(result, dict)

    def test_load_bundled_schema_platform_value(self) -> None:
        """load_bundled_schema('claude_code') returns dict with platform == 'claude_code'."""
        from skilllint import load_bundled_schema

        result = load_bundled_schema("claude_code")
        assert result["platform"] == "claude_code"

    def test_load_bundled_schema_version_param(self) -> None:
        """load_bundled_schema accepts an explicit version='v1' parameter."""
        from skilllint import load_bundled_schema

        result = load_bundled_schema("claude_code", version="v1")
        assert isinstance(result, dict)
