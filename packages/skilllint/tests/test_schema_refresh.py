"""Tests for schema refresh script functionality.

These tests verify the refresh contract:
- Generated schemas have valid provenance fields
- Version bumping produces correct filenames
- Dry-run mode doesn't write files
- constraint_scope annotations are preserved
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add scripts directory to path for imports
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import refresh_schemas as rs


class TestRefreshGeneratesValidJSON:
    """Tests for valid schema generation."""

    def test_create_refreshed_schema_has_required_provenance(self) -> None:
        """create_refreshed_schema produces schema with all required provenance fields."""
        original = {
            "$id": "skilllint/schemas/test_provider/v1.json",
            "title": "Test Provider Schema v1",
            "provenance": {
                "authority_url": "https://example.com",
                "last_verified": "2024-01-01",
                "provider_id": "test_provider",
            },
            "file_types": {},
        }

        refreshed = rs.create_refreshed_schema(original, 2, "test_provider")

        # Check provenance structure
        assert "provenance" in refreshed
        prov = refreshed["provenance"]
        assert "authority_url" in prov
        assert "last_verified" in prov
        assert "provider_id" in prov
        assert prov["provider_id"] == "test_provider"

    def test_create_refreshed_schema_updates_version_in_id(self) -> None:
        """create_refreshed_schema updates $id to new version."""
        original = {
            "$id": "skilllint/schemas/claude_code/v1.json",
            "title": "Claude Code Schema v1",
            "provenance": {
                "authority_url": "https://anthropic.com",
                "last_verified": "2024-01-01",
                "provider_id": "claude_code",
            },
        }

        refreshed = rs.create_refreshed_schema(original, 2, "claude_code")

        assert refreshed["$id"] == "skilllint/schemas/claude_code/v2.json"

    def test_create_refreshed_schema_updates_title(self) -> None:
        """create_refreshed_schema updates title with new version."""
        original = {
            "$id": "skilllint/schemas/claude_code/v1.json",
            "title": "Claude Code Platform Schema v1",
            "provenance": {
                "authority_url": "https://anthropic.com",
                "last_verified": "2024-01-01",
                "provider_id": "claude_code",
            },
        }

        refreshed = rs.create_refreshed_schema(original, 2, "claude_code")

        assert "v2" in refreshed["title"]

    def test_validate_provenance_accepts_valid_schema(self) -> None:
        """validate_provenance returns no errors for valid schema."""
        schema = {
            "provenance": {
                "authority_url": "https://example.com",
                "last_verified": "2024-01-01",
                "provider_id": "test_provider",
            }
        }

        errors = rs.validate_provenance(schema, "test_provider")
        assert errors == []

    def test_validate_provenance_rejects_missing_provenance(self) -> None:
        """validate_provenance errors on missing provenance field."""
        schema = {}

        errors = rs.validate_provenance(schema, "test_provider")
        assert len(errors) == 1
        assert "missing top-level 'provenance'" in errors[0]

    def test_validate_provenance_rejects_missing_required_field(self) -> None:
        """validate_provenance errors on missing required provenance fields."""
        schema = {
            "provenance": {
                "authority_url": "https://example.com",
                # missing last_verified
                "provider_id": "test_provider",
            }
        }

        errors = rs.validate_provenance(schema, "test_provider")
        assert len(errors) >= 1
        assert any("last_verified" in e for e in errors)


class TestVersionBumpCorrectFilename:
    """Tests for version bumping logic."""

    def test_get_latest_version_finds_highest(self, tmp_path: Path) -> None:
        """get_latest_version returns the highest version number."""
        # Create test provider directory with version files
        provider_dir = tmp_path / "test_provider"
        provider_dir.mkdir()
        (provider_dir / "v1.json").write_text("{}")
        (provider_dir / "v2.json").write_text("{}")
        (provider_dir / "v3.json").write_text("{}")

        # Monkey-patch the schemas directory
        original_schemas_dir = rs.SCHEMAS_DIR
        rs.SCHEMAS_DIR = tmp_path

        try:
            version = rs.get_latest_version("test_provider")
            assert version == 3
        finally:
            rs.SCHEMAS_DIR = original_schemas_dir

    def test_get_latest_version_returns_none_for_empty(self, tmp_path: Path) -> None:
        """get_latest_version returns None for provider with no versions."""
        provider_dir = tmp_path / "empty_provider"
        provider_dir.mkdir()

        original_schemas_dir = rs.SCHEMAS_DIR
        rs.SCHEMAS_DIR = tmp_path

        try:
            version = rs.get_latest_version("empty_provider")
            assert version is None
        finally:
            rs.SCHEMAS_DIR = original_schemas_dir

    def test_version_bump_creates_correct_next_version(self) -> None:
        """Version bump from N should create N+1."""
        original = {
            "$id": "skilllint/schemas/test/v5.json",
            "title": "Test Schema v5",
            "provenance": {
                "authority_url": "https://example.com",
                "last_verified": "2024-01-01",
                "provider_id": "test",
            },
        }

        refreshed = rs.create_refreshed_schema(original, 6, "test")

        assert "v6.json" in refreshed["$id"]
        assert "v6" in refreshed["title"]


class TestDryRunNoWrite:
    """Tests for dry-run safety."""

    def test_dry_run_returns_would_create_message(self) -> None:
        """refresh_provider with dry_run=True returns would-create message."""
        # Use an existing provider
        success, message = rs.refresh_provider("claude_code", dry_run=True, verbose=False)

        assert success is True
        assert "would create" in message
        assert "v" in message  # Version mentioned

    def test_dry_run_does_not_write_files(self, tmp_path: Path) -> None:
        """dry_run=True should not create new files."""
        # Create test provider with v1
        provider_dir = tmp_path / "test_dry"
        provider_dir.mkdir()
        v1_content = json.dumps({
            "$id": "skilllint/schemas/test_dry/v1.json",
            "title": "Test Dry Schema v1",
            "provenance": {
                "authority_url": "https://example.com",
                "last_verified": "2024-01-01",
                "provider_id": "test_dry",
            },
        })
        (provider_dir / "v1.json").write_text(v1_content)

        original_schemas_dir = rs.SCHEMAS_DIR
        rs.SCHEMAS_DIR = tmp_path

        try:
            # Run dry-run refresh
            success, _ = rs.refresh_provider("test_dry", dry_run=True, verbose=False)

            # Verify no v2.json was created
            v2_path = provider_dir / "v2.json"
            assert not v2_path.exists(), "dry-run should not create v2.json"
            assert success is True
        finally:
            rs.SCHEMAS_DIR = original_schemas_dir


class TestConstraintScopePreserved:
    """Tests for constraint_scope annotation preservation."""

    def test_count_constraint_scopes_counts_fields(self) -> None:
        """count_constraint_scopes correctly counts constraint_scope fields."""
        schema = {
            "file_types": {
                "skill": {
                    "fields": {
                        "name": {"constraint_scope": "shared"},
                        "description": {"constraint_scope": "shared"},
                        "priority": {"constraint_scope": "provider_specific"},
                    }
                }
            }
        }

        count = rs.count_constraint_scopes(schema)
        assert count == 3

    def test_create_refreshed_schema_preserves_constraint_scopes(self) -> None:
        """create_refreshed_schema preserves all constraint_scope annotations."""
        original = {
            "$id": "skilllint/schemas/test/v1.json",
            "title": "Test Schema v1",
            "provenance": {
                "authority_url": "https://example.com",
                "last_verified": "2024-01-01",
                "provider_id": "test",
            },
            "file_types": {
                "skill": {
                    "fields": {
                        "name": {"type": "string", "constraint_scope": "shared"},
                        "priority": {"type": "integer", "constraint_scope": "provider_specific"},
                    }
                }
            },
        }

        refreshed = rs.create_refreshed_schema(original, 2, "test")

        # Verify constraint_scope fields preserved
        original_scopes = rs.count_constraint_scopes(original)
        refreshed_scopes = rs.count_constraint_scopes(refreshed)
        assert original_scopes == refreshed_scopes == 2

        # Verify actual values preserved
        skill_fields = refreshed["file_types"]["skill"]["fields"]
        assert skill_fields["name"]["constraint_scope"] == "shared"
        assert skill_fields["priority"]["constraint_scope"] == "provider_specific"

    def test_deeply_nested_constraint_scopes_preserved(self) -> None:
        """create_refreshed_schema preserves constraint_scopes in deep nesting."""
        original = {
            "$id": "skilllint/schemas/test/v1.json",
            "title": "Test Schema v1",
            "provenance": {
                "authority_url": "https://example.com",
                "last_verified": "2024-01-01",
                "provider_id": "test",
            },
            "definitions": {"nested": {"properties": {"deep_field": {"constraint_scope": "shared"}}}},
        }

        refreshed = rs.create_refreshed_schema(original, 2, "test")

        assert refreshed["definitions"]["nested"]["properties"]["deep_field"]["constraint_scope"] == "shared"


class TestProviderDiscovery:
    """Tests for provider discovery functionality."""

    def test_get_provider_ids_returns_list(self) -> None:
        """get_provider_ids returns a list of provider IDs."""
        providers = rs.get_provider_ids()

        assert isinstance(providers, list)
        assert len(providers) >= 1  # At least claude_code

    def test_get_provider_ids_includes_known_providers(self) -> None:
        """get_provider_ids includes expected providers."""
        providers = rs.get_provider_ids()

        # These should always be present
        assert "claude_code" in providers
        assert "cursor" in providers
        assert "codex" in providers

    def test_get_provider_ids_sorted(self) -> None:
        """get_provider_ids returns sorted list."""
        providers = rs.get_provider_ids()

        assert providers == sorted(providers)


class TestRefreshProvider:
    """Tests for refresh_provider function."""

    def test_refresh_provider_invalid_provider_returns_failure(self) -> None:
        """refresh_provider returns failure for non-existent provider."""
        # Temporarily patch SCHEMAS_DIR to an empty directory
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            original_schemas_dir = rs.SCHEMAS_DIR
            rs.SCHEMAS_DIR = Path(tmpdir)

            try:
                success, message = rs.refresh_provider("nonexistent", dry_run=True, verbose=False)
                assert success is False
                assert "no schema versions found" in message
            finally:
                rs.SCHEMAS_DIR = original_schemas_dir

    def test_refresh_provider_valid_provider_succeeds(self) -> None:
        """refresh_provider succeeds for valid provider."""
        success, message = rs.refresh_provider("claude_code", dry_run=True, verbose=False)

        assert success is True
        assert "claude_code" in message
