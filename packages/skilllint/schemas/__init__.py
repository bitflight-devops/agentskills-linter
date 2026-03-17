"""Schema loading utilities for bundled platform schema snapshots.

Provides package-safe loading of provider schema JSON files via importlib.resources.
Each schema contains provenance metadata (authority_url, last_verified, provider_id)
and field-level constraint_scope annotations for distinguishing shared vs provider-specific
constraints.
"""

from __future__ import annotations

from skilllint.schemas._loader import get_provider_ids, load_bundled_schema, load_provider_schema

__all__ = ["get_provider_ids", "load_bundled_schema", "load_provider_schema"]
