"""Tests for validator ownership routing (S02).

These tests verify:
1. ValidatorOwnership enum and mapping work correctly
2. get_validator_ownership() returns correct ownership for each validator
3. filter_validators_by_constraint_scopes() filters validators based on provider scopes
"""

from __future__ import annotations

from skilllint.plugin_validator import (
    VALIDATOR_OWNERSHIP,
    ComplexityValidator,
    DescriptionValidator,
    FrontmatterValidator,
    HookValidator,
    InternalLinkValidator,
    MarkdownTokenCounter,
    NameFormatValidator,
    NamespaceReferenceValidator,
    PluginRegistrationValidator,
    PluginStructureValidator,
    ProgressiveDisclosureValidator,
    SymlinkTargetValidator,
    ValidatorOwnership,
    filter_validators_by_constraint_scopes,
    get_validator_constraint_scopes,
    get_validator_ownership,
)


class TestValidatorOwnership:
    """Tests for ValidatorOwnership enum and mapping."""

    def test_schema_validators_have_schema_ownership(self):
        """Schema-backed validators should have SCHEMA ownership."""
        schema_validators = [
            FrontmatterValidator(),
            PluginStructureValidator(),
            PluginRegistrationValidator(),
            HookValidator(),
            SymlinkTargetValidator(),
        ]
        for validator in schema_validators:
            ownership = get_validator_ownership(validator)
            assert ownership == ValidatorOwnership.SCHEMA, f"{type(validator).__name__} should be SCHEMA"

    def test_lint_validators_have_lint_ownership(self):
        """Lint-rule validators should have LINT ownership."""
        lint_validators = [
            NameFormatValidator(),
            DescriptionValidator(),
            ComplexityValidator(),
            InternalLinkValidator(),
            ProgressiveDisclosureValidator(),
            NamespaceReferenceValidator(),
            MarkdownTokenCounter(),
        ]
        for validator in lint_validators:
            ownership = get_validator_ownership(validator)
            assert ownership == ValidatorOwnership.LINT, f"{type(validator).__name__} should be LINT"

    def test_all_known_validators_mapped(self):
        """All known validators should be in the VALIDATOR_OWNERSHIP dict."""
        known_validators = {
            "FrontmatterValidator": FrontmatterValidator(),
            "PluginStructureValidator": PluginStructureValidator(),
            "PluginRegistrationValidator": PluginRegistrationValidator(),
            "HookValidator": HookValidator(),
            "SymlinkTargetValidator": SymlinkTargetValidator(),
            "NameFormatValidator": NameFormatValidator(),
            "DescriptionValidator": DescriptionValidator(),
            "ComplexityValidator": ComplexityValidator(),
            "InternalLinkValidator": InternalLinkValidator(),
            "ProgressiveDisclosureValidator": ProgressiveDisclosureValidator(),
            "NamespaceReferenceValidator": NamespaceReferenceValidator(),
            "MarkdownTokenCounter": MarkdownTokenCounter(),
        }
        for class_name in known_validators:
            assert class_name in VALIDATOR_OWNERSHIP, f"{class_name} not in VALIDATOR_OWNERSHIP"


class TestValidatorConstraintScopes:
    """Tests for constraint scope filtering."""

    def test_all_validators_have_constraint_scopes(self):
        """All known validators should have constraint scope mappings."""
        for class_name in VALIDATOR_OWNERSHIP:
            scopes = get_validator_constraint_scopes(class_name)
            assert isinstance(scopes, set), f"{class_name} should return a set"
            assert scopes, f"{class_name} should have at least one scope"

    def test_filter_with_shared_only(self):
        """Filtering with shared scope should include validators that support shared."""
        validators = [FrontmatterValidator(), ComplexityValidator()]
        # If provider only claims "shared", validators that support both should still run
        filtered = filter_validators_by_constraint_scopes(validators, {"shared"})
        # All validators in our map support both shared and provider_specific
        # so they should all be included
        assert len(filtered) == len(validators)

    def test_filter_with_provider_specific_only(self):
        """Filtering with provider_specific scope should include validators that support it."""
        validators = [FrontmatterValidator(), ComplexityValidator()]
        filtered = filter_validators_by_constraint_scopes(validators, {"provider_specific"})
        assert len(filtered) == len(validators)

    def test_filter_excludes_mismatched_scopes(self):
        """If a validator only supports 'shared' but provider only has 'provider_specific', exclude it."""

        # Create a mock validator with limited scope
        class MockValidator:
            pass

        # Temporarily add a mock validator with limited scope
        from skilllint.plugin_validator import VALIDATOR_CONSTRAINT_SCOPES

        original = VALIDATOR_CONSTRAINT_SCOPES.copy()
        try:
            # Add mock validator that only supports shared
            VALIDATOR_CONSTRAINT_SCOPES["MockValidator"] = {"shared"}

            from skilllint.plugin_validator import filter_validators_by_constraint_scopes

            validators = [MockValidator()]
            # Provider only has provider_specific
            filtered = filter_validators_by_constraint_scopes(validators, {"provider_specific"})  # type: ignore[arg-type]  # intentional non-Validator mock
            # Should be filtered out
            assert len(filtered) == 0
        finally:
            VALIDATOR_CONSTRAINT_SCOPES.clear()
            VALIDATOR_CONSTRAINT_SCOPES.update(original)

    def test_unknown_validator_included_by_default(self):
        """Unknown validators should be included by default (conservative)."""
        from skilllint.plugin_validator import filter_validators_by_constraint_scopes

        class UnknownValidator:
            pass

        validators = [UnknownValidator()]
        filtered = filter_validators_by_constraint_scopes(validators, {"shared"})  # type: ignore[arg-type]  # intentional non-Validator mock
        # Unknown validators default to both scopes, so included
        assert len(filtered) == 1
