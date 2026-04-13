"""CU-series Cursor .mdc frontmatter validation rules (CU001-CU002).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects. The validator logic was previously inlined in
packages/skilllint/adapters/cursor/adapter.py as raw dict construction,
bypassing @skilllint_rule registration entirely. This module lifts that
logic into the registry so CU001 and CU002 are discoverable via
``skilllint rule CU001`` and appear in RULE_REGISTRY.

Architectural note — adapter-backed series:
    CU is one of two rule series (the other is CX) where detection was
    originally owned by a platform adapter rather than the core validator.
    Per architect spec §3.3, the resolution is: this series module OWNS the
    validator logic and the @skilllint_rule registration; the cursor adapter
    imports ``validate_mdc_frontmatter`` and converts its output to
    ``list[dict]`` at the adapter boundary.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | CU001 | Required field missing from .mdc frontmatter              | error     |
    | CU002 | Unknown field in .mdc frontmatter                         | error     |
    +-------+-----------------------------------------------------------+-----------+

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skilllint.rule_registry import skilllint_rule

if TYPE_CHECKING:
    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

_CURSOR_DOCS_URL = "https://docs.cursor.com/context/rules-for-ai"
_CU_DOCS_BASE = "https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md"


def _docs_url(code: str) -> str:
    """Return the documentation URL for a CU rule code.

    Args:
        code: Rule code string (e.g., "CU001").

    Returns:
        Full URL with anchor for the error code documentation.
    """
    return f"{_CU_DOCS_BASE}#{code.lower()}"


# ---------------------------------------------------------------------------
# CU001 — Required field missing from .mdc frontmatter
# ---------------------------------------------------------------------------


@skilllint_rule(
    "CU001",
    severity="error",
    category="cursor",
    platforms=["cursor"],
    authority={"origin": "cursor.com", "reference": _CURSOR_DOCS_URL},
)
def check_cu001(frontmatter: dict[str, object], mdc_schema: dict[str, object]) -> list[ValidationIssue]:
    """## CU001 — Required field missing from .mdc frontmatter

    The `.mdc` frontmatter is missing a field declared as required in the
    Cursor provider schema. Each required field must be present for the rule
    file to be valid.

    **Source:** Cursor provider schema `cursor v1.json` — `required` array
    in the `mdc` file-type definition.

    **Fix:** Add the missing required field to the frontmatter block:

    ```yaml
    ---
    description: What this rule does
    globs: "**/*.ts"
    alwaysApply: false
    ---
    ```

    Returns:
        List of error issues, one per missing required field; empty when all
        required fields are present or when the schema has no required fields.

    <!-- examples: CU001 -->
    """
    # Deferred import to break circular dependency:
    # plugin_validator imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    required_val: object = mdc_schema.get("required", [])
    required_fields: list[str] = (
        [f for f in required_val if isinstance(f, str)] if isinstance(required_val, list) else []
    )
    return [
        ValidationIssue(
            field=field,
            severity="error",
            message=f"Required field '{field}' is missing from .mdc frontmatter",
            code="CU001",
            docs_url=_docs_url("CU001"),
        )
        for field in required_fields
        if field not in frontmatter
    ]


# ---------------------------------------------------------------------------
# CU002 — Unknown field in .mdc frontmatter
# ---------------------------------------------------------------------------


@skilllint_rule(
    "CU002",
    severity="error",
    category="cursor",
    platforms=["cursor"],
    authority={"origin": "cursor.com", "reference": _CURSOR_DOCS_URL},
)
def check_cu002(frontmatter: dict[str, object], mdc_schema: dict[str, object]) -> list[ValidationIssue]:
    """## CU002 — Unknown field in .mdc frontmatter

    The `.mdc` frontmatter contains a field that is not defined in the
    Cursor provider schema, and the schema disallows additional properties
    (`additionalProperties: false`). Unknown fields are rejected by Cursor
    when strict schema validation is enforced.

    **Source:** Cursor provider schema `cursor v1.json` — `additionalProperties`
    flag in the `mdc` file-type definition.

    **Fix:** Remove the unknown field from the frontmatter, or verify that
    the field name is spelled correctly:

    ```yaml
    ---
    # Before (unknown field)
    description: My rule
    unknown_key: value

    # After
    description: My rule
    ---
    ```

    Returns:
        List of error issues, one per unknown field; empty when
        ``additionalProperties`` is not ``false`` or all fields are known.

    <!-- examples: CU002 -->
    """
    # Deferred import to break circular dependency:
    # plugin_validator imports rules/, so rules/ cannot import plugin_validator at module level.
    from skilllint.plugin_validator import ValidationIssue  # noqa: PLC0415

    additional_properties: object = mdc_schema.get("additionalProperties", True)
    if additional_properties is not False:
        return []

    properties_val: object = mdc_schema.get("properties", {})
    known_fields: set[str] = (
        {k for k in properties_val if isinstance(k, str)} if isinstance(properties_val, dict) else set()
    )
    return [
        ValidationIssue(
            field=field,
            severity="error",
            message=f"Unknown field '{field}' in .mdc frontmatter (additionalProperties is false)",
            code="CU002",
            docs_url=_docs_url("CU002"),
        )
        for field in frontmatter
        if field not in known_fields
    ]


# ---------------------------------------------------------------------------
# Public entry point for the cursor adapter
# ---------------------------------------------------------------------------


def validate_mdc_frontmatter(frontmatter: dict[str, object], mdc_schema: dict[str, object]) -> list[ValidationIssue]:
    """Public entry point for the cursor adapter. Covers CU001 and CU002.

    Args:
        frontmatter: Parsed frontmatter dict from the .mdc file.
        mdc_schema: The provider schema sub-object for the ``mdc`` file type.

    Returns:
        Combined list of ValidationIssue objects from CU001 and CU002 checks.
    """
    issues: list[ValidationIssue] = []
    issues.extend(check_cu001(frontmatter, mdc_schema))
    issues.extend(check_cu002(frontmatter, mdc_schema))
    return issues


__all__ = ["check_cu001", "check_cu002", "validate_mdc_frontmatter"]
