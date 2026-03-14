"""Schema loading utilities for bundled platform schema snapshots.

Provides package-safe loading of provider schema JSON files via importlib.resources.
Each schema contains provenance metadata (authority_url, last_verified, provider_id)
and field-level constraint_scope annotations for distinguishing shared vs provider-specific
constraints.
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def load_provider_schema(provider: str, version: str = "v1") -> dict[str, Any]:
    """Load a provider schema JSON file and return the parsed dict.

    Uses importlib.resources for package-safe loading, ensuring the schemas
    work correctly when the package is installed via pip or bundled.

    Args:
        provider: Provider ID (directory name), e.g., 'claude_code', 'cursor', 'codex'.
        version: Schema version string, defaults to 'v1'.

    Returns:
        Parsed schema dict with top-level 'provenance' key containing
        authority_url, last_verified, and provider_id.

    Raises:
        FileNotFoundError: If the provider/version combination doesn't exist.
        json.JSONDecodeError: If the schema file is malformed JSON.
    """
    try:
        schema_path = f"{provider}/{version}.json"
        schema_file = files("skilllint.schemas").joinpath(schema_path)
        content = schema_file.read_text(encoding="utf-8")
        return json.loads(content)
    except (FileNotFoundError, TypeError) as e:
        available = get_provider_ids()
        raise FileNotFoundError(
            f"Schema not found for provider='{provider}', version='{version}'. "
            f"Available providers: {available}"
        ) from e


def get_provider_ids() -> list[str]:
    """Return list of available provider directory names.

    Discovers provider directories by listing the schemas package.
    Each provider directory contains versioned schema JSON files.

    Returns:
        List of provider IDs (directory names), e.g., ['claude_code', 'cursor', 'codex'].
    """
    try:
        schemas_dir = files("skilllint.schemas")
        # Filter to only directories (providers) and exclude __pycache__
        providers = []
        for item in schemas_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                providers.append(item.name)
        return sorted(providers)
    except (FileNotFoundError, AttributeError):
        # Fallback for environments where iterdir isn't available
        return ["claude_code", "cursor", "codex"]


__all__ = ["load_provider_schema", "load_bundled_schema", "get_provider_ids"]


# Backwards-compatible alias for the brownfield loader migration.
# This matches the old _schema_loader.load_bundled_schema signature.
def load_bundled_schema(platform: str, version: str = "v1") -> dict[str, Any]:
    """Load a bundled platform schema snapshot.

    This is a backwards-compatible alias for load_provider_schema.
    The 'platform' parameter is equivalent to 'provider'.

    Args:
        platform: Platform identifier, e.g., 'claude_code', 'cursor', 'codex'.
        version: Schema version string, defaults to 'v1'.

    Returns:
        Parsed schema dict with top-level 'provenance' key.
    """
    return load_provider_schema(platform, version)
