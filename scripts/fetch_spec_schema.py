#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx>=0.27.0",
#   "beautifulsoup4>=4.12.0",
#   "skilllint",
# ]
#
# [tool.uv.sources]
# skilllint = { path = ".." }
# ///

"""Fetch agentskills.io specification and generate JSON Schema.

Downloads the official spec, extracts frontmatter field constraints,
and generates a machine-readable JSON Schema for validation.

Drift detection compares new schema against previous to detect:
- New fields added
- Constraints changed (maxLength, pattern, etc.)
- Fields removed
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx
from bs4 import BeautifulSoup

from skilllint.vendor_io import PROJECT_ROOT, load_json_or_none, sha256_hex, utc_now_iso, write_json

if TYPE_CHECKING:
    from pathlib import Path

SPEC_URL = "https://agentskills.io/specification"
SCHEMA_DIR = PROJECT_ROOT / "packages" / "skilllint" / "schemas" / "agentskills_io"
OUTPUT_FILE = SCHEMA_DIR / "v1.json"
PREVIOUS_FILE = SCHEMA_DIR / ".previous_v1.json"


@dataclass
class SchemaFieldConstraint:
    """Constraint for a single field."""

    field_name: str
    max_length: int | None = None
    min_length: int | None = None
    pattern: str | None = None
    required: bool = False


@dataclass
class SchemaDrift:
    """Represents detected drift between schema versions."""

    added_fields: list[str] = field(default_factory=list)
    removed_fields: list[str] = field(default_factory=list)
    changed_constraints: dict[str, dict[str, tuple[Any, Any]]] = field(default_factory=dict)
    no_changes: bool = True


def fetch_spec_page() -> str:
    """Fetch the specification page HTML.

    Returns:
        The raw HTML content for the specification page.
    """
    response = httpx.get(SPEC_URL, timeout=30.0)
    response.raise_for_status()
    return response.text


def parse_frontmatter_constraints(html: str) -> dict[str, Any]:
    """Parse frontmatter field constraints from the spec page.

    The spec page has a table with Field, Required, and Constraints columns.

    Returns:
        A mapping of field name to parsed constraint metadata.
    """
    soup = BeautifulSoup(html, "html.parser")
    constraints: dict[str, dict[str, Any]] = {}

    tables = soup.find_all("table")
    for table in tables:
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if "field" not in headers or "constraints" not in headers:
            continue

        field_idx = headers.index("field")
        required_idx = headers.index("required") if "required" in headers else None
        constraints_idx = headers.index("constraints")

        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(field_idx, constraints_idx):
                continue

            field_name = cells[field_idx].get_text(strip=True).strip("`")
            if field_name.lower() == "field":
                continue

            constraints_text = cells[constraints_idx].get_text(strip=True) if constraints_idx < len(cells) else ""

            is_required = False
            if required_idx is not None and required_idx < len(cells):
                required_text = cells[required_idx].get_text(strip=True).lower()
                is_required = "yes" in required_text or "required" in required_text

            parsed_constraints = _parse_field_constraints(field_name, constraints_text)
            parsed_constraints["required"] = is_required
            constraints[field_name] = parsed_constraints
        break

    return constraints


def _parse_field_constraints(field_name: str, constraints_text: str) -> dict[str, Any]:
    """Parse constraints text for a specific field.

    Args:
        field_name: The spec field name being parsed.
        constraints_text: The human-readable constraints text from the spec table.

    Returns:
        Parsed constraint metadata suitable for JSON Schema generation.
    """
    del field_name
    constraints: dict[str, Any] = {}

    max_length_match = re.search(r"max\s+(\d+)\s+characters?", constraints_text, re.IGNORECASE)
    if max_length_match:
        constraints["maxLength"] = int(max_length_match.group(1))

    min_length_match = re.search(r"(\d+)\s*-\s*(\d+)\s+characters", constraints_text, re.IGNORECASE)
    if min_length_match:
        constraints["minLength"] = int(min_length_match.group(1))
        constraints["maxLength"] = int(min_length_match.group(2))
    else:
        single_match = re.search(r"must be\s+(\d+)\s+characters", constraints_text, re.IGNORECASE)
        if single_match:
            constraints["minLength"] = int(single_match.group(1))

    if "lowercase" in constraints_text and "hyphen" in constraints_text:
        constraints["pattern"] = r"^[a-z0-9]+(-[a-z0-9]+)*$"

    if "must not start or end with a hyphen" in constraints_text:
        constraints["noLeadingTrailingHyphen"] = True

    if "consecutive hyphens" in constraints_text:
        constraints["noConsecutiveHyphens"] = True

    if "non-empty" in constraints_text.lower():
        constraints["minLength"] = max(constraints.get("minLength", 0), 1)

    if "should describe" in constraints_text or "use when" in constraints_text.lower():
        constraints["shouldInclude"] = "Use when"

    return constraints


def build_json_schema(constraints: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build a JSON Schema from parsed constraints.

    Returns:
        A JSON-serializable schema document for the parsed constraints.
    """
    properties: dict[str, dict[str, Any]] = {}
    required_fields: list[str] = []

    for field_name, field_constraints in constraints.items():
        json_prop: dict[str, Any] = {"type": "string"}

        if "maxLength" in field_constraints:
            json_prop["maxLength"] = field_constraints["maxLength"]
        if "minLength" in field_constraints:
            json_prop["minLength"] = field_constraints["minLength"]
        if "pattern" in field_constraints:
            json_prop["pattern"] = field_constraints["pattern"]

        description_parts = ["(Required)" if field_constraints.get("required") else "(Optional)"]
        if "maxLength" in field_constraints:
            description_parts.append(f"Max {field_constraints['maxLength']} chars")
        if "shouldInclude" in field_constraints:
            description_parts.append(f"Should include: {field_constraints['shouldInclude']}")

        json_prop["description"] = " ".join(description_parts)
        properties[field_name] = json_prop

        if field_constraints.get("required"):
            required_fields.append(field_name)

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "skilllint/schemas/agentskills_io/v1.json",
        "title": "Agent Skills Specification v1",
        "description": "JSON Schema for agentskills.io skill frontmatter. Generated from https://agentskills.io/specification",
        "version": "1.0.0",
        "type": "object",
        "properties": properties,
        "required": required_fields,
        "additionalProperties": True,
        "x-source": {"url": SPEC_URL, "fetched_at": utc_now_iso()},
    }


def main() -> None:
    """Fetch spec and generate schema."""
    print(f"Fetching {SPEC_URL}...")
    html = fetch_spec_page()

    print("Parsing frontmatter constraints...")
    constraints = parse_frontmatter_constraints(html)

    print(f"Found constraints for {len(constraints)} fields:")
    for field_name, constraint in constraints.items():
        required = "required" if constraint.get("required") else "optional"
        print(f"  - {field_name}: {required}")

    print("Building JSON Schema...")
    schema = build_json_schema(constraints)
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

    previous = load_previous_schema()
    if previous:
        drift = detect_drift(previous, schema)
        if drift.no_changes:
            print("No schema changes detected since last run.")
        else:
            print("\n⚠️  Schema drift detected:")
            if drift.added_fields:
                print(f"  + New fields: {drift.added_fields}")
            if drift.removed_fields:
                print(f"  - Removed fields: {drift.removed_fields}")
            if drift.changed_constraints:
                print("  ~ Changed constraints:")
                for field_name, changes in drift.changed_constraints.items():
                    for attr, (old_val, new_val) in changes.items():
                        print(f"      {field_name}.{attr}: {old_val} -> {new_val}")
    else:
        print("First run - no previous schema to compare.")

    OUTPUT_FILE.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"\nWritten to {OUTPUT_FILE}")

    save_previous_schema(schema)
    _emit_python_constants(constraints, PROJECT_ROOT / "packages" / "skilllint" / "_spec_constants.py")


def _emit_python_constants(constraints: dict[str, dict[str, Any]], output_path: Path) -> None:
    """Emit Python constants from constraints for easy importing."""
    lines = [
        "# Auto-generated from agentskills.io specification",
        "# Do not edit manually - run scripts/fetch_spec_schema.py to update",
        "",
        "from typing import Final",
        "",
    ]

    for field_name, constraint in constraints.items():
        field_upper = field_name.replace("-", "_").upper()

        if "maxLength" in constraint:
            lines.append(f"MAX_{field_upper}_LENGTH: Final[int] = {constraint['maxLength']}")
        if "minLength" in constraint:
            lines.append(f"MIN_{field_upper}_LENGTH: Final[int] = {constraint['minLength']}")
        if "pattern" in constraint:
            lines.append(f'PATTERN_{field_upper}: Final[str] = r"{constraint["pattern"]}"')

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Python constants written to {output_path}")


def compute_content_hash(schema: dict[str, Any]) -> str:
    """Compute a hash of the schema content (excluding metadata).

    Returns:
        A short stable hash of the schema payload.
    """
    stable = {key: value for key, value in schema.items() if key != "x-source"}
    return sha256_hex(json.dumps(stable, sort_keys=True))[:12]


def load_previous_schema() -> dict[str, Any] | None:
    """Load the previously saved schema if it exists.

    Returns:
        The previously saved schema, or None when no prior snapshot exists.
    """
    return load_json_or_none(PREVIOUS_FILE)


def detect_drift(old_schema: dict[str, Any], new_schema: dict[str, Any]) -> SchemaDrift:
    """Compare two schemas and detect drift.

    Returns:
        A drift summary describing added, removed, and changed fields.
    """
    drift = SchemaDrift()

    old_props = old_schema.get("properties", {})
    new_props = new_schema.get("properties", {})

    old_fields = set(old_props.keys())
    new_fields = set(new_props.keys())

    drift.added_fields = sorted(new_fields - old_fields)
    drift.removed_fields = sorted(old_fields - new_fields)

    for field_name in old_fields & new_fields:
        old_field = old_props[field_name]
        new_field = new_props[field_name]

        changes: dict[str, tuple[Any, Any]] = {}
        for attr in ["maxLength", "minLength", "pattern", "type"]:
            old_val = old_field.get(attr)
            new_val = new_field.get(attr)
            if old_val != new_val:
                changes[attr] = (old_val, new_val)

        if changes:
            drift.changed_constraints[field_name] = changes

    drift.no_changes = not (drift.added_fields or drift.removed_fields or drift.changed_constraints)
    return drift


def save_previous_schema(schema: dict[str, Any]) -> None:
    """Save current schema as previous for next comparison."""
    write_json(PREVIOUS_FILE, schema)


if __name__ == "__main__":
    main()
