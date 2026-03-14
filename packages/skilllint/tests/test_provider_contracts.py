"""Contract tests for provider schemas and rule authority metadata.

These tests lock the metadata shape as a contract boundary for S02 and S03.
Any change to the provenance structure or constraint_scope values will fail
these tests, signalling a breaking change that needs explicit review.
"""

import pytest

from skilllint.rule_registry import RuleAuthority, RuleEntry, skilllint_rule
from skilllint.schemas import get_provider_ids, load_provider_schema


class TestProviderSchemaProvenance:
    """Tests for provider schema provenance metadata."""

    @pytest.mark.parametrize("provider", get_provider_ids())
    def test_provider_schema_has_provenance(self, provider: str) -> None:
        """Each provider schema must have a provenance object with required keys."""
        schema = load_provider_schema(provider)

        assert "provenance" in schema, f"{provider}: missing 'provenance' key"
        provenance = schema["provenance"]

        required_keys = ["authority_url", "last_verified", "provider_id"]
        for key in required_keys:
            assert key in provenance, f"{provider}: provenance missing '{key}'"
            assert provenance[key], f"{provider}: provenance['{key}'] is empty"

    @pytest.mark.parametrize("provider", get_provider_ids())
    def test_provider_schema_constraint_scopes(self, provider: str) -> None:
        """All field entries must have valid constraint_scope values."""
        schema = load_provider_schema(provider)
        valid_scopes = {"shared", "provider_specific"}

        # Check file_types section
        if "file_types" in schema:
            for file_type, file_type_def in schema["file_types"].items():
                if "fields" in file_type_def:
                    for field_name, field_def in file_type_def["fields"].items():
                        if "constraint_scope" in field_def:
                            scope = field_def["constraint_scope"]
                            assert scope in valid_scopes, (
                                f"{provider}: file_types.{file_type}.{field_name} "
                                f"has invalid constraint_scope '{scope}'"
                            )


class TestProviderSchemaLoader:
    """Tests for the schema loading utilities."""

    def test_load_provider_schema_all_providers(self) -> None:
        """load_provider_schema should successfully load each provider."""
        providers = get_provider_ids()
        assert len(providers) >= 3, "Expected at least 3 providers"

        for provider in providers:
            schema = load_provider_schema(provider)
            assert isinstance(schema, dict), f"{provider}: schema is not a dict"
            assert "provenance" in schema, f"{provider}: missing provenance"

    def test_load_provider_schema_invalid_provider(self) -> None:
        """Loading a non-existent provider should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_provider_schema("nonexistent_provider")

        assert "Schema not found" in str(exc_info.value)
        assert "Available providers" in str(exc_info.value)

    def test_get_provider_ids_returns_sorted_list(self) -> None:
        """get_provider_ids should return a sorted list of provider IDs."""
        providers = get_provider_ids()
        assert providers == sorted(providers), "Provider IDs should be sorted"


class TestRuleAuthority:
    """Tests for RuleAuthority dataclass and RuleEntry integration."""

    def test_rule_authority_dataclass_fields(self) -> None:
        """RuleAuthority should have origin and reference fields."""
        authority = RuleAuthority(origin="agent-skills.io", reference="/rules/SK001")

        assert authority.origin == "agent-skills.io"
        assert authority.reference == "/rules/SK001"

    def test_rule_authority_reference_optional(self) -> None:
        """RuleAuthority.reference should be optional."""
        authority = RuleAuthority(origin="anthropic.com")

        assert authority.origin == "anthropic.com"
        assert authority.reference is None

    def test_rule_entry_authority_structured(self) -> None:
        """RuleEntry should accept and expose structured authority."""
        # Create a test function
        def test_validator(frontmatter: dict) -> list:
            return []

        # Create a RuleEntry with authority
        authority = RuleAuthority(origin="test-origin", reference="https://example.com/rules/TEST001")
        entry = RuleEntry(
            id="TEST001",
            fn=test_validator,
            severity="error",
            category="test",
            platforms=["agentskills"],
            docstring="Test rule",
            authority=authority,
        )

        assert entry.authority is not None
        assert entry.authority.origin == "test-origin"
        assert entry.authority.reference == "https://example.com/rules/TEST001"

    def test_rule_entry_authority_optional(self) -> None:
        """RuleEntry.authority should be optional (default None)."""
        # Create a test function
        def test_validator(frontmatter: dict) -> list:
            return []

        # Create a RuleEntry without authority
        entry = RuleEntry(
            id="TEST002",
            fn=test_validator,
            severity="warning",
            category="test",
            platforms=["agentskills"],
            docstring="Test rule without authority",
        )

        assert entry.authority is None

    def test_skilllint_rule_decorator_accepts_authority(self) -> None:
        """skilllint_rule decorator should accept and convert authority kwarg."""
        # Clear any existing test rule
        from skilllint.rule_registry import RULE_REGISTRY

        # Register a rule with authority
        @skilllint_rule(
            "TEST_AUTH_001",
            severity="error",
            category="test",
            authority={"origin": "test-origin", "reference": "/test/rules/TEST_AUTH_001"},
        )
        def test_rule_with_authority(frontmatter: dict) -> list:
            """Test rule with authority."""
            return []

        # Verify the rule was registered with authority
        entry = RULE_REGISTRY.get("TEST_AUTH_001")
        assert entry is not None, "Rule should be registered"
        assert entry.authority is not None, "Rule should have authority"
        assert entry.authority.origin == "test-origin"
        assert entry.authority.reference == "/test/rules/TEST_AUTH_001"

    def test_skilllint_rule_decorator_without_authority(self) -> None:
        """skilllint_rule decorator should work without authority kwarg."""
        from skilllint.rule_registry import RULE_REGISTRY

        @skilllint_rule(
            "TEST_NO_AUTH_001",
            severity="info",
            category="test",
        )
        def test_rule_without_authority(frontmatter: dict) -> list:
            """Test rule without authority."""
            return []

        entry = RULE_REGISTRY.get("TEST_NO_AUTH_001")
        assert entry is not None
        assert entry.authority is None
