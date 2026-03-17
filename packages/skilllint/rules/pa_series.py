"""PA-series rule validation for plugin agent frontmatter.

Rule PA001 fires when a plugin agent SKILL.md uses prohibited frontmatter
fields (hooks, mcpServers, permissionMode) that are not available to
sub-agents.

Entry point: check_pa001(path: Path) -> ValidationResult

Source: https://docs.anthropic.com/en/docs/claude-code/sub-agents
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruamel.yaml import YAML

from skilllint.frontmatter_core import extract_frontmatter
from skilllint.rule_registry import skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue, ValidationResult


# Prohibited frontmatter fields for plugin agents.
# Source: https://docs.anthropic.com/en/docs/claude-code/sub-agents
# "For security reasons, plugin subagents do not support the `hooks`,
# `mcpServers`, or `permissionMode` frontmatter fields."
_PROHIBITED_AGENT_FIELDS: dict[str, str] = {
    "hooks": "Plugin agents cannot define hooks in frontmatter — move to `hooks/hooks.json` at plugin root",
    "mcpServers": "Plugin agents cannot define mcpServers in frontmatter — move to `.mcp.json` at plugin root",
    "permissionMode": "Plugin agents cannot use permissionMode — copy agent to `.claude/agents/` if needed",
}


def _find_plugin_dir(path: Path) -> Path | None:
    """Find the plugin directory containing .claude-plugin/plugin.json.

    Args:
        path: Path to start searching from.

    Returns:
        Plugin directory path, or None if not found.
    """
    search_path = path.parent if path.is_file() else path
    for parent in [search_path, *search_path.parents]:
        if (parent / ".claude-plugin" / "plugin.json").exists():
            return parent
    return None


def _safe_load_yaml(text: str) -> object:
    """Load YAML text safely using ruamel.yaml.

    Args:
        text: YAML text to parse.

    Returns:
        Parsed YAML value.
    """
    yaml_loader = YAML(typ="safe")
    return yaml_loader.load(text)


@skilllint_rule(
    "PA001",
    severity="error",
    category="plugin",
    authority={"origin": "anthropic.com", "reference": "https://docs.anthropic.com/en/docs/claude-code/sub-agents"},
)
def check_pa001(path: Path) -> ValidationResult:
    """PA001 — Prohibited frontmatter field in plugin agent.

    Plugin agents (sub-agents) cannot use ``hooks``, ``mcpServers``, or
    ``permissionMode`` in their SKILL.md frontmatter. These fields are
    silently ignored by Claude Code at runtime, so their presence is
    almost certainly a mistake.

    Sub-agents inherit their tool and permission configuration from the
    parent agent and cannot override it. For security reasons, plugin
    subagents do not support these frontmatter fields.

    Source: https://docs.anthropic.com/en/docs/claude-code/sub-agents

    Args:
        path: Path to plugin directory (must contain .claude-plugin/plugin.json).

    Returns:
        ValidationResult with errors for each prohibited field found.

    Fix: Remove the prohibited field from the agent's frontmatter.
    - ``hooks`` → move to ``hooks/hooks.json`` at plugin root
    - ``mcpServers`` → move to ``.mcp.json`` at plugin root
    - ``permissionMode`` → copy agent to ``.claude/agents/`` if needed
    """
    from skilllint.plugin_validator import (  # noqa: PLC0415 — deferred to break circular import
        PA001 as PA001_CODE,
        ValidationIssue,
        ValidationResult,
    )

    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    info: list[ValidationIssue] = []

    plugin_dir = _find_plugin_dir(path)
    if plugin_dir is None:
        return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

    agents_dir = plugin_dir / "agents"
    if not agents_dir.is_dir():
        return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

    for agent_md in sorted(agents_dir.glob("*.md")):
        content = agent_md.read_text(encoding="utf-8")
        fm_text, _start, _end = extract_frontmatter(content)
        if fm_text is None:
            continue

        parsed = _safe_load_yaml(fm_text)
        if not isinstance(parsed, dict):
            continue

        for field, guidance in _PROHIBITED_AGENT_FIELDS.items():
            if field in parsed:
                rel_path = agent_md.relative_to(plugin_dir)
                errors.append(
                    ValidationIssue(
                        field=str(rel_path),
                        severity="error",
                        message=f"Prohibited frontmatter field `{field}` in plugin agent",
                        code=PA001_CODE,
                        suggestion=guidance,
                        docs_url="https://docs.anthropic.com/en/docs/claude-code/sub-agents",
                    )
                )

    return ValidationResult(passed=len(errors) == 0, errors=errors, warnings=warnings, info=info)


class PluginAgentFrontmatterValidator:
    """Adapter class exposing check_pa001 via the Validator protocol interface.

    The validation pipeline (_get_validators_for_path) expects objects implementing
    the Validator protocol (validate/can_fix/fix methods). This class adapts the
    rule-decorated check_pa001 function to that interface.

    The real validation logic lives in check_pa001 above.
    """

    def validate(self, path: Path) -> ValidationResult:
        """Validate plugin agent .md files for prohibited frontmatter fields.

        Args:
            path: Path to plugin directory (must contain .claude-plugin/plugin.json).

        Returns:
            ValidationResult with errors for each prohibited field found.
        """
        return check_pa001(path)

    def can_fix(self) -> bool:
        """Whether this validator supports auto-fixing.

        Returns:
            False — prohibited field removal requires manual review.
        """
        return False

    def fix(self, path: Path) -> list[str]:
        """Auto-fix is not supported for prohibited frontmatter fields.

        Args:
            path: Path to plugin directory.

        Raises:
            NotImplementedError: Always raised; manual review required.
        """
        raise NotImplementedError("Plugin agent prohibited frontmatter fields require manual fixes.")


__all__ = ["PluginAgentFrontmatterValidator", "check_pa001"]
