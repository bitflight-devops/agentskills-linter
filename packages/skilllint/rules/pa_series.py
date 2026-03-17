"""PA-series rule validation for plugin agent frontmatter.

Rule PA001 fires when a plugin agent SKILL.md uses frontmatter fields
(hooks, mcpServers, permissionMode) that are not available to sub-agents.

Severity is nuanced per field:
- ``permissionMode`` → **error** — causes agent to not appear in the plugin
- ``hooks`` → **warning** — always emitted; guidance varies based on whether
  plugin hooks.json covers the same events
- ``mcpServers`` → **warning** with cross-checking:
  - inline definitions (config objects) → warn, suggest ``.mcp.json``
  - string references found in plugin ``.mcp.json`` / ``plugin.json`` → silenced
  - string references NOT found → warn

Entry point: check_pa001(path: Path) -> ValidationResult

Source: https://docs.anthropic.com/en/docs/claude-code/sub-agents
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from skilllint.frontmatter_core import extract_frontmatter
from skilllint.rule_registry import skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ErrorCode, ValidationIssue, ValidationResult


_DOCS_URL = "https://docs.anthropic.com/en/docs/claude-code/sub-agents"


def _load_json_file(path: Path) -> dict | None:
    """Load a JSON file, returning None on any failure.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed dict, or None if file missing or invalid.
    """
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _get_plugin_level_hooks_events(plugin_dir: Path) -> set[str]:
    """Extract hook event names from plugin-level hooks/hooks.json.

    Args:
        plugin_dir: Plugin root directory.

    Returns:
        Set of event names (e.g. ``{"preToolUse", "postToolUse"}``).
    """
    data = _load_json_file(plugin_dir / "hooks" / "hooks.json")
    if isinstance(data, dict):
        return set(data.keys())
    return set()


def _get_plugin_level_mcp_servers(plugin_dir: Path) -> set[str]:
    """Extract MCP server names declared at the plugin level.

    Checks both ``.mcp.json`` and ``.claude-plugin/plugin.json`` for
    an ``mcpServers`` mapping.

    Args:
        plugin_dir: Plugin root directory.

    Returns:
        Set of server names available at plugin level.
    """
    names: set[str] = set()
    # .mcp.json at plugin root
    mcp_data = _load_json_file(plugin_dir / ".mcp.json")
    if isinstance(mcp_data, dict) and isinstance(mcp_data.get("mcpServers"), dict):
        names.update(mcp_data["mcpServers"].keys())

    # .claude-plugin/plugin.json mcpServers section
    plugin_data = _load_json_file(plugin_dir / ".claude-plugin" / "plugin.json")
    if isinstance(plugin_data, dict) and isinstance(plugin_data.get("mcpServers"), dict):
        names.update(plugin_data["mcpServers"].keys())

    return names


def _is_inline_mcp_definition(entry: object) -> bool:
    """Determine if an mcpServers list entry is an inline definition.

    Inline definitions are dicts with server config (e.g. ``{name: {type: ..., command: ...}}``).
    String references are plain strings (just a server name).

    Args:
        entry: A single element from the ``mcpServers`` list.

    Returns:
        True if the entry is an inline definition (dict), False if string reference.
    """
    return isinstance(entry, dict)


def _check_hooks(
    parsed: dict, rel_path: str, plugin_events: set[str], code: ErrorCode, issue_cls: type[ValidationIssue]
) -> list[ValidationIssue]:
    """Check hooks field — always warns, varies guidance based on plugin hooks.json coverage.

    Args:
        parsed: Parsed frontmatter dict.
        rel_path: Relative path of the agent file.
        plugin_events: Hook event names from plugin-level hooks/hooks.json.
        code: The PA001 error code.
        issue_cls: ValidationIssue class.

    Returns:
        List of warning issues (always emitted when hooks field is present).
    """
    hooks_value = parsed.get("hooks")
    if hooks_value is None:
        return []

    # Extract event names from agent frontmatter hooks
    agent_events: set[str] = set()
    if isinstance(hooks_value, dict):
        agent_events = set(hooks_value.keys())

    # Check if plugin-level hooks.json covers the same events
    if agent_events and agent_events <= plugin_events:
        # All agent hook events are covered by plugin hooks.json — warn with coverage note
        suggestion = "This field is ignored — plugin-level hooks at `hooks/hooks.json` already cover these events"
    else:
        suggestion = "This field is ignored — move to `hooks/hooks.json` at plugin root"

    return [
        issue_cls(
            field=rel_path,
            severity="warning",
            message="Frontmatter field `hooks` in plugin agent is silently ignored",
            code=code,
            suggestion=suggestion,
            docs_url=_DOCS_URL,
        )
    ]


def _check_mcp_servers(
    parsed: dict, rel_path: str, plugin_servers: set[str], code: ErrorCode, issue_cls: type[ValidationIssue]
) -> list[ValidationIssue]:
    """Check mcpServers field — warning severity with cross-checking.

    Args:
        parsed: Parsed frontmatter dict.
        rel_path: Relative path of the agent file.
        plugin_servers: MCP server names from plugin-level config.
        code: The PA001 error code.
        issue_cls: ValidationIssue class.

    Returns:
        List of warning issues for inline definitions or unresolved references.
    """
    mcp_value = parsed.get("mcpServers")
    if mcp_value is None:
        return []
    issues: list[ValidationIssue] = []

    # mcpServers can be a list or a dict
    entries: list[object] = []
    if isinstance(mcp_value, list):
        entries = mcp_value
    elif isinstance(mcp_value, dict):
        # Dict form: keys are server names, values are config objects or simple values
        for name, config in mcp_value.items():
            if isinstance(config, dict):
                # Inline definition as dict value
                entries.append({name: config})
            else:
                # Simple value — treat as string reference
                entries.append(name)

    for entry in entries:
        if _is_inline_mcp_definition(entry):
            # Inline definition — always warn
            server_name = next(iter(entry.keys()), "<unknown>") if isinstance(entry, dict) else str(entry)
            issues.append(
                issue_cls(
                    field=rel_path,
                    severity="warning",
                    message=f"Inline mcpServers definition `{server_name}` in plugin agent frontmatter",
                    code=code,
                    suggestion=(
                        "Plugin agents cannot define mcpServers inline — move server "
                        "configuration to `.mcp.json` at plugin root"
                    ),
                    docs_url=_DOCS_URL,
                )
            )
        else:
            # String reference — cross-check against plugin-level config
            server_name = str(entry)
            if server_name not in plugin_servers:
                issues.append(
                    issue_cls(
                        field=rel_path,
                        severity="warning",
                        message=f"mcpServers reference `{server_name}` not found in plugin-level config",
                        code=code,
                        suggestion=(
                            f"Server `{server_name}` is not defined in `.mcp.json` or "
                            "`plugin.json` — add it to `.mcp.json` at plugin root"
                        ),
                        docs_url=_DOCS_URL,
                    )
                )
            # else: found in plugin config — silenced

    return issues


def _check_permission_mode(
    parsed: dict, rel_path: str, code: ErrorCode, issue_cls: type[ValidationIssue]
) -> list[ValidationIssue]:
    """Check permissionMode field — always error severity.

    Args:
        parsed: Parsed frontmatter dict.
        rel_path: Relative path of the agent file.
        code: The PA001 error code.
        issue_cls: ValidationIssue class.

    Returns:
        List of error issues.
    """
    if "permissionMode" not in parsed:
        return []

    return [
        issue_cls(
            field=rel_path,
            severity="error",
            message="Prohibited frontmatter field `permissionMode` in plugin agent",
            code=code,
            suggestion="Plugin agents cannot use permissionMode — copy agent to `.claude/agents/` if needed",
            docs_url=_DOCS_URL,
        )
    ]


def _try_parse_agent_yaml(fm_text: str, agent_md: Path, plugin_dir: Path, errors: list, warnings: list) -> dict | None:
    """Parse agent frontmatter YAML, attempting colon auto-fix on failure.

    Args:
        fm_text: Raw YAML frontmatter text (no ``---`` delimiters).
        agent_md: Path to the agent markdown file.
        plugin_dir: Plugin root directory for relative path display.
        errors: Mutable error list — FM002 appended on unrecoverable failure.
        warnings: Mutable warning list — AS004 appended on colon auto-fix.

    Returns:
        Parsed dict on success, or None on unrecoverable YAML error.
    """
    from skilllint.plugin_validator import (  # noqa: PLC0415 — deferred to break circular import
        FM002,
        ErrorCode,
        ValidationIssue,
        generate_docs_url,
        safe_load_yaml_with_colon_fix,
    )

    parsed, yaml_err, colon_fields, _used_text = safe_load_yaml_with_colon_fix(fm_text)

    if colon_fields:
        rel = str(agent_md.relative_to(plugin_dir))
        warnings.append(
            ValidationIssue(
                field="description",
                severity="warning",
                message=f"{rel}: Description contains unquoted colons that break YAML — quote the following fields: {', '.join(colon_fields)}",
                code=ErrorCode.AS004,
                docs_url=generate_docs_url(ErrorCode.AS004),
            )
        )

    if yaml_err is not None:
        rel = str(agent_md.relative_to(plugin_dir))
        errors.append(
            ValidationIssue(
                field="(yaml)",
                severity="error",
                message=f"{rel}: Invalid YAML frontmatter: {yaml_err}",
                code=FM002,
                docs_url=generate_docs_url(FM002),
            )
        )
        return None

    return parsed if isinstance(parsed, dict) else None


@skilllint_rule(
    "PA001", severity="error", category="plugin", authority={"origin": "anthropic.com", "reference": _DOCS_URL}
)
def check_pa001(path: Path) -> ValidationResult:
    """PA001 — Restricted frontmatter fields in plugin agent.

    Plugin agents (sub-agents) have restrictions on ``hooks``, ``mcpServers``,
    and ``permissionMode`` in their SKILL.md frontmatter:

    - ``permissionMode`` → **error**: causes agent to not appear in the plugin.
      No plugin-level equivalent exists.
    - ``hooks`` → **warning**: always emitted (field is ignored at runtime).
      Guidance varies based on plugin ``hooks/hooks.json`` coverage.
    - ``mcpServers`` → **warning** with cross-checking against plugin-level
      ``.mcp.json`` and ``plugin.json``:
      - inline definitions → warn, suggest ``.mcp.json``
      - string references found in plugin config → silenced
      - string references not found → warn

    Source: https://docs.anthropic.com/en/docs/claude-code/sub-agents

    Args:
        path: Path to plugin directory (must contain .claude-plugin/plugin.json).

    Returns:
        ValidationResult with errors/warnings for restricted fields found.

    Fix:
    - ``hooks`` → move to ``hooks/hooks.json`` at plugin root
    - ``mcpServers`` → move to ``.mcp.json`` at plugin root
    - ``permissionMode`` → copy agent to ``.claude/agents/`` if needed
    """
    from skilllint.plugin_validator import (  # noqa: PLC0415 — deferred to break circular import
        FRONTMATTER_EXEMPT_FILENAMES,
        PA001 as PA001_CODE,
        ValidationIssue,
        ValidationResult,
        find_plugin_dir,
    )

    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    info: list[ValidationIssue] = []

    plugin_dir = find_plugin_dir(path)
    if plugin_dir is None:
        return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

    agents_dir = plugin_dir / "agents"
    if not agents_dir.is_dir():
        return ValidationResult(passed=True, errors=errors, warnings=warnings, info=info)

    # Hoist plugin-level JSON reads above the loop to avoid N+1 I/O
    plugin_hooks_events = _get_plugin_level_hooks_events(plugin_dir)
    plugin_mcp_servers = _get_plugin_level_mcp_servers(plugin_dir)

    for agent_md in sorted(agents_dir.glob("*.md")):
        if agent_md.name in FRONTMATTER_EXEMPT_FILENAMES:
            continue
        content = agent_md.read_text(encoding="utf-8")
        fm_text, _start, _end = extract_frontmatter(content)
        if fm_text is None:
            continue

        parsed = _try_parse_agent_yaml(fm_text, agent_md, plugin_dir, errors, warnings)
        if not isinstance(parsed, dict):
            continue

        rel_path = str(agent_md.relative_to(plugin_dir))

        # permissionMode — always error
        errors.extend(_check_permission_mode(parsed, rel_path, PA001_CODE, ValidationIssue))

        # hooks — warning, silenced if plugin hooks.json covers same events
        warnings.extend(_check_hooks(parsed, rel_path, plugin_hooks_events, PA001_CODE, ValidationIssue))

        # mcpServers — warning with cross-checking
        warnings.extend(_check_mcp_servers(parsed, rel_path, plugin_mcp_servers, PA001_CODE, ValidationIssue))

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
