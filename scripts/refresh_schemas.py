"""Refresh provider schemas with updated provenance and version bumps.

Reads each provider's current latest schema, bumps the version (v1→v2),
updates provenance.last_verified to current timestamp, preserves all
constraint_scope annotations, and writes the new versioned file.

Usage:
    python scripts/refresh_schemas.py --dry-run      # Show proposed changes
    python scripts/refresh_schemas.py --bump        # Write new versions
    python scripts/refresh_schemas.py --bump --provider claude_code  # Single provider
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add package to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SCHEMAS_DIR = PROJECT_ROOT / "packages" / "skilllint" / "schemas"


def get_provider_ids() -> list[str]:
    """Return list of available provider directory names.

    Discovers provider directories by listing the schemas package.
    Each provider directory contains versioned schema JSON files.

    Returns:
        List of provider IDs (directory names), e.g., ['claude_code', 'cursor', 'codex'].
    """
    providers = [item.name for item in SCHEMAS_DIR.iterdir() if item.is_dir() and not item.name.startswith("_")]
    return sorted(providers)


def get_latest_version(provider: str) -> int | None:
    """Get the highest version number for a provider.

    Args:
        provider: Provider ID (directory name).

    Returns:
        Highest version number found, or None if no versions exist.
    """
    provider_dir = SCHEMAS_DIR / provider
    if not provider_dir.is_dir():
        return None

    max_version = 0
    for item in provider_dir.iterdir():
        if item.is_file() and item.suffix == ".json":
            name = item.stem
            if name.startswith("v") and name[1:].isdigit():
                version = int(name[1:])
                max_version = max(max_version, version)

    return max_version if max_version > 0 else None


def load_schema(provider: str, version: int) -> dict[str, Any] | None:
    """Load a schema file.

    Args:
        provider: Provider ID.
        version: Version number.

    Returns:
        Parsed schema dict, or None if file doesn't exist.
    """
    schema_path = SCHEMAS_DIR / provider / f"v{version}.json"
    if not schema_path.is_file():
        return None

    content = schema_path.read_text(encoding="utf-8")
    return json.loads(content)


def validate_provenance(schema: dict[str, Any], provider: str) -> list[str]:
    """Validate that a schema has required provenance fields.

    Args:
        schema: Parsed schema dict.
        provider: Provider ID for error messages.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []

    provenance = schema.get("provenance")
    if provenance is None:
        errors.append(f"provider '{provider}': missing top-level 'provenance' field")
        return errors

    if not isinstance(provenance, dict):
        errors.append(f"provider '{provider}': 'provenance' must be an object")
        return errors

    required_fields = ["authority_url", "last_verified", "provider_id"]
    for field in required_fields:
        if field not in provenance:
            errors.append(f"provider '{provider}': provenance.{field} is required")
        elif not isinstance(provenance[field], str):
            errors.append(f"provider '{provider}': provenance.{field} must be a string")

    return errors


def create_refreshed_schema(schema: dict[str, Any], new_version: int, provider: str) -> dict[str, Any]:
    """Create a refreshed schema with updated version and provenance.

    Args:
        schema: Original schema dict.
        new_version: New version number.
        provider: Provider ID.

    Returns:
        New schema dict with updated provenance.
    """
    new_schema = copy.deepcopy(schema)

    # Update version in $id
    if "$id" in new_schema:
        new_schema["$id"] = f"skilllint/schemas/{provider}/v{new_version}.json"

    # Update title if present
    if "title" in new_schema:
        old_title = new_schema["title"]
        if old_title.endswith(f"v{new_version - 1}"):
            new_schema["title"] = old_title.replace(f"v{new_version - 1}", f"v{new_version}")
        else:
            new_schema["title"] = f"{provider.title()} Platform Schema v{new_version}"

    # Update provenance
    if "provenance" in new_schema:
        new_schema["provenance"]["last_verified"] = datetime.now(UTC).strftime("%Y-%m-%d")
        new_schema["provenance"]["provider_id"] = provider

    return new_schema


def show_diff(old_schema: dict[str, Any], new_schema: dict[str, Any], provider: str) -> None:
    """Show a summary of changes between old and new schema.

    Args:
        old_schema: Original schema.
        new_schema: Refreshed schema.
        provider: Provider ID.
    """
    old_prov = old_schema.get("provenance", {})
    new_prov = new_schema.get("provenance", {})

    print(f"\n  {provider}:")
    print(f"    $id: {old_schema.get('$id', 'N/A')}")
    print(f"     → {new_schema.get('$id', 'N/A')}")
    print(f"    provenance.last_verified: {old_prov.get('last_verified', 'N/A')}")
    print(f"     → {new_prov.get('last_verified', 'N/A')}")


def refresh_provider(provider: str, *, dry_run: bool, verbose: bool) -> tuple[bool, str]:
    """Refresh a single provider's schema.

    Args:
        provider: Provider ID.
        dry_run: If True, show changes without writing.
        verbose: If True, show more details.

    Returns:
        Tuple of (success, message).
    """
    # Get current version
    current_version = get_latest_version(provider)
    if current_version is None:
        return False, f"provider '{provider}': no schema versions found"

    # Load current schema
    schema = load_schema(provider, current_version)
    if schema is None:
        return False, f"provider '{provider}': failed to load v{current_version}.json"

    # Validate provenance
    errors = validate_provenance(schema, provider)
    if errors:
        return False, "; ".join(errors)

    # Create new version
    new_version = current_version + 1
    new_schema = create_refreshed_schema(schema, new_version, provider)

    if dry_run:
        show_diff(schema, new_schema, provider)
        if verbose:
            # Show constraint_scope preservation
            old_scopes = count_constraint_scopes(schema)
            new_scopes = count_constraint_scopes(new_schema)
            print(f"    constraint_scope fields: {old_scopes} → {new_scopes} (preserved)")
        return True, f"would create {provider}/v{new_version}.json"

    # Write new schema
    new_path = SCHEMAS_DIR / provider / f"v{new_version}.json"
    try:
        content = json.dumps(new_schema, indent=2, ensure_ascii=False) + "\n"
        new_path.write_text(content, encoding="utf-8")
    except OSError as e:
        return False, f"provider '{provider}': failed to write v{new_version}.json: {e}"

    show_diff(schema, new_schema, provider)
    return True, f"created {provider}/v{new_version}.json"


def count_constraint_scopes(schema: dict[str, Any]) -> int:
    """Count constraint_scope annotations in a schema.

    Args:
        schema: Parsed schema dict.

    Returns:
        Number of constraint_scope fields found.
    """
    count = 0

    def walk(obj: object) -> None:
        nonlocal count
        if isinstance(obj, dict):
            if "constraint_scope" in obj:
                count += 1
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(schema)
    return count


def main() -> int:
    """Main entry point for schema refresh script.

    Returns:
        Exit code: 0 on success, 1 on validation error, 2 on write failure.
    """
    parser = argparse.ArgumentParser(
        description="Refresh provider schemas with updated provenance and version bumps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit codes:
  0  Success (or dry-run completed)
  1  Validation error (provider not found, schema validation failed)
  2  Write failure
""",
    )
    parser.add_argument("--bump", action="store_true", help="Write new schema versions (default is dry-run)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show proposed changes without writing (default behavior)"
    )
    parser.add_argument("--provider", metavar="NAME", help="Refresh only the specified provider")
    parser.add_argument("--verbose", action="store_true", help="Show detailed constraint_scope preservation status")
    args = parser.parse_args()

    # Get providers to process
    if args.provider:
        available = get_provider_ids()
        if args.provider not in available:
            print(f"error: provider '{args.provider}' not found. Available: {available}", file=sys.stderr)
            return 1
        providers = [args.provider]
    else:
        providers = get_provider_ids()

    if not providers:
        print("error: no providers found", file=sys.stderr)
        return 1

    # Determine mode
    dry_run = not args.bump

    if dry_run:
        print("Dry-run mode: showing proposed changes without writing\n")
    else:
        print("Bump mode: writing new schema versions\n")

    print("Processing providers:")
    success_count = 0
    failure_count = 0

    for provider in providers:
        success, message = refresh_provider(provider, dry_run=dry_run, verbose=args.verbose)
        if success:
            success_count += 1
            if dry_run:
                print(f"  [dry-run] {message}")
            else:
                print(f"  ✓ {message}")
        else:
            failure_count += 1
            print(f"  ✗ {message}", file=sys.stderr)

    print(f"\nSummary: {success_count} succeeded, {failure_count} failed")

    if failure_count > 0:
        return 2 if not dry_run else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
