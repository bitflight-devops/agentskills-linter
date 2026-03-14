"""Rule registry and @skilllint_rule decorator.

Each validator function is decorated with @skilllint_rule:

    @skilllint_rule(
        "SK001",
        severity="error",
        category="skill",
        platforms=["agentskills"],
        authority={"origin": "agent-skills.io", "reference": "/rules/SK001"},
    )
    def check_name_field(frontmatter: dict, path: Path) -> list[ValidationIssue]:
        \"\"\"
        ## SK001 — Missing `name` field

        Every SKILL.md must declare a `name` field in its frontmatter.

        **Fix:** Add `name: your-skill-name` to the frontmatter block.
        \"\"\"

The decorator registers the rule in RULE_REGISTRY for `skilllint rule <ID>` lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class RuleAuthority:
    """Structured authority metadata for a validation rule.

    Captures where a rule originates and where its documentation lives.
    This enables tracing any validation back to its source authority.
    """

    origin: str  # e.g., "agent-skills.io", "anthropic.com"
    reference: str | None = None  # URL or doc path, e.g., "/rules/SK001"


@dataclass
class RuleEntry:
    """Registry entry for a single validation rule."""

    id: str
    fn: Callable
    severity: str  # "error", "warning", "info"
    category: str  # "frontmatter", "skill", "plugin", "hook", etc.
    platforms: list[str]  # ["agentskills"] = all platforms, or specific like ["claude-code"]
    docstring: str
    authority: RuleAuthority | None = None


# Global registry: rule ID → RuleEntry
RULE_REGISTRY: dict[str, RuleEntry] = {}


def skilllint_rule(
    rule_id: str,
    *,
    severity: str,
    category: str,
    platforms: list[str] | None = None,
    authority: dict | None = None,
) -> Callable[[Callable], Callable]:
    """Decorator to register a validator function as a rule.

    Args:
        rule_id: Rule identifier (e.g., "SK001", "FM002")
        severity: One of "error", "warning", "info"
        category: Rule category (e.g., "frontmatter", "skill", "plugin")
        platforms: List of platforms this rule applies to. ["agentskills"] means all platforms.
                   Defaults to ["agentskills"].
        authority: Optional authority metadata dict with 'origin' and optional 'reference' keys.
                   Converted to RuleAuthority dataclass.

    Returns:
        Decorated function (unchanged) that's registered in RULE_REGISTRY.

    Example:
        @skilllint_rule(
            "SK001",
            severity="error",
            category="skill",
            authority={"origin": "agent-skills.io", "reference": "/rules/SK001"},
        )
        def check_name(frontmatter: dict) -> list[ValidationIssue]:
            '''## SK001 — Missing name field

            Every skill must have a name.
            '''
            ...
    """
    if platforms is None:
        platforms = ["agentskills"]

    # Convert authority dict to RuleAuthority if provided
    rule_authority: RuleAuthority | None = None
    if authority is not None:
        rule_authority = RuleAuthority(
            origin=authority.get("origin", ""),
            reference=authority.get("reference"),
        )

    def decorator(fn: Callable) -> Callable:
        entry = RuleEntry(
            id=rule_id.upper(),
            fn=fn,
            severity=severity,
            category=category,
            platforms=platforms,
            docstring=fn.__doc__ or f"Rule {rule_id}",
            authority=rule_authority,
        )
        RULE_REGISTRY[rule_id.upper()] = entry
        return fn

    return decorator


def get_rule(rule_id: str) -> RuleEntry | None:
    """Look up a rule by ID (case-insensitive).

    Args:
        rule_id: Rule identifier (e.g., "SK001", "sk001")

    Returns:
        RuleEntry if found, None otherwise.
    """
    return RULE_REGISTRY.get(rule_id.upper())


def list_rules(
    *, platform: str | None = None, category: str | None = None, severity: str | None = None
) -> list[RuleEntry]:
    """List rules, optionally filtered.

    Args:
        platform: Filter to rules that apply to this platform
        category: Filter to rules in this category
        severity: Filter to rules with this severity

    Returns:
        List of matching RuleEntry objects, sorted by ID.
    """
    rules = list(RULE_REGISTRY.values())

    if platform:
        rules = [r for r in rules if "agentskills" in r.platforms or platform in r.platforms]

    if category:
        rules = [r for r in rules if r.category == category]

    if severity:
        rules = [r for r in rules if r.severity == severity]

    return sorted(rules, key=lambda r: r.id)


__all__ = ["RULE_REGISTRY", "RuleAuthority", "RuleEntry", "get_rule", "list_rules", "skilllint_rule"]
