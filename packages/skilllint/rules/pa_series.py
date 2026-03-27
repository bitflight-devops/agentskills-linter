"""PA-series rule validation for plugin agent frontmatter.

Rule PA001 fires when a plugin agent uses frontmatter fields that Anthropic does
not support on **plugin-packaged** subagents.

**Authoritative policy** (Anthropic, *Create custom subagents* → *Choose the subagent scope*):

    For security reasons, plugin subagents do not support the ``hooks``, ``mcpServers``,
    or ``permissionMode`` frontmatter fields. These fields are ignored when loading
    agents from a plugin. If you need them, copy the agent file into ``.claude/agents/``
    or ``~/.claude/agents/``. You can also add rules to ``permissions.allow`` in
    ``settings.json`` or ``settings.local.json``, but these rules apply to the entire
    session, not just the plugin subagent.

Severity in skilllint (lint UX on top of the same source text):

- ``permissionMode`` → **error** — leaving it in place misleads authors; the runtime
  ignores it for plugin agents, so the declared mode never applies.
- ``hooks`` / ``mcpServers`` → **warning** — same source: ignored at load; we add
  cross-checks so authors can move config to plugin-level ``hooks/hooks.json`` and
  ``.mcp.json`` / ``plugin.json`` where supported.

Entry point: ``check_pa001(path: Path) -> ValidationResult``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skilllint.boundary.plugin_agent_pa001_ingest import (
    McpInlineServerDefinition,
    McpServerNameRef,
    PluginAgentPa001Snapshot,
    ingest_plugin_agent_frontmatter_for_pa001,
)
from skilllint.boundary.plugin_level_config_ingest import (
    ingest_plugin_hook_event_names,
    ingest_plugin_level_mcp_server_names,
)
from skilllint.frontmatter_core import extract_frontmatter
from skilllint.rule_registry import skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue, ValidationResult


# Deep link to the table + security paragraph on plugin-packaged subagents.
_DOCS_SUBAGENTS_PLUGIN_SCOPE = "https://docs.anthropic.com/en/docs/claude-code/sub-agents.md#choose-the-subagent-scope"
_DOCS_PLUGIN_AGENTS_COMPONENT = "https://code.claude.com/docs/en/plugins-reference.md#agents"
_DOCS_SETTINGS_PERMISSIONS = "https://docs.anthropic.com/en/settings.md#permission-settings"


def _check_hooks(
    snap: PluginAgentPa001Snapshot,
    rel_path: str,
    plugin_events: frozenset[str],
    code: str,
    issue_cls: type[ValidationIssue],
) -> list[ValidationIssue]:
    """Check hooks field — always warns, varies guidance based on plugin hooks.json coverage.

    Args:
        snap: Parsed agent frontmatter snapshot for PA001.
        rel_path: Relative path of the agent file.
        plugin_events: Hook event names from plugin-level ``hooks/hooks.json`` (validated).
        code: The PA001 error code.
        issue_cls: ValidationIssue class.

    Returns:
        List of warning issues (always emitted when hooks field is present).
    """
    if not snap.hooks_nonempty:
        return []

    agent_events = set(snap.hooks_event_names)

    # Check if plugin-level hooks.json covers the same events
    if agent_events and agent_events <= plugin_events:
        # All agent hook events are covered by plugin hooks.json — warn with coverage note
        suggestion = (
            "Anthropic states `hooks` in plugin agent frontmatter is ignored when loading from a plugin. "
            "Plugin-level `hooks/hooks.json` already cover these events — remove the redundant `hooks` "
            f"block from this agent file. Ref: {_DOCS_SUBAGENTS_PLUGIN_SCOPE}"
        )
    else:
        suggestion = (
            "Anthropic states `hooks` in plugin agent frontmatter is ignored when loading from a plugin. "
            "Move to `hooks/hooks.json` at the plugin root for plugin-wide hook definitions. "
            f"Refs: {_DOCS_SUBAGENTS_PLUGIN_SCOPE} · {_DOCS_PLUGIN_AGENTS_COMPONENT}"
        )

    return [
        issue_cls(
            field=rel_path,
            severity="warning",
            message=(
                "Unsupported `hooks` in plugin-packaged agent frontmatter "
                "(Anthropic: ignored when loading agents from a plugin for security reasons)"
            ),
            code=code,
            suggestion=suggestion,
            docs_url=_DOCS_SUBAGENTS_PLUGIN_SCOPE,
        )
    ]


def _check_mcp_servers(
    snap: PluginAgentPa001Snapshot,
    rel_path: str,
    plugin_servers: frozenset[str],
    code: str,
    issue_cls: type[ValidationIssue],
) -> list[ValidationIssue]:
    """Check mcpServers field — warning severity with cross-checking.

    Args:
        snap: Parsed agent frontmatter snapshot for PA001.
        rel_path: Relative path of the agent file.
        plugin_servers: MCP server names from ``.mcp.json`` / ``plugin.json`` (validated).
        code: The PA001 error code.
        issue_cls: ValidationIssue class.

    Returns:
        List of warning issues for inline definitions or unresolved references.
    """
    if not snap.mcp_entries:
        return []
    issues: list[ValidationIssue] = []

    for entry in snap.mcp_entries:
        if isinstance(entry, McpInlineServerDefinition):
            server_name = entry.server_name
            issues.append(
                issue_cls(
                    field=rel_path,
                    severity="warning",
                    message=(
                        f"Inline `mcpServers` entry `{server_name}` in plugin-packaged agent "
                        "(Anthropic: `mcpServers` in plugin agent frontmatter is ignored when loading from a plugin)"
                    ),
                    code=code,
                    suggestion=(
                        "Define MCP servers in `.mcp.json` at the plugin root (or register them in "
                        f"`plugin.json`), not in agent frontmatter. Refs: {_DOCS_SUBAGENTS_PLUGIN_SCOPE} · "
                        f"{_DOCS_PLUGIN_AGENTS_COMPONENT}"
                    ),
                    docs_url=_DOCS_SUBAGENTS_PLUGIN_SCOPE,
                )
            )
        elif isinstance(entry, McpServerNameRef):
            server_name = entry.name
            if server_name not in plugin_servers:
                issues.append(
                    issue_cls(
                        field=rel_path,
                        severity="warning",
                        message=(
                            f"`mcpServers` references `{server_name}` but that server is not declared at plugin level "
                            "(plugin agent frontmatter cannot supply inline MCP config)"
                        ),
                        code=code,
                        suggestion=(
                            f"Add `{server_name}` to `.mcp.json` or `plugin.json` at the plugin root so the name "
                            f"resolves. Anthropic: `mcpServers` in plugin agent files is ignored at load. "
                            f"Ref: {_DOCS_SUBAGENTS_PLUGIN_SCOPE}"
                        ),
                        docs_url=_DOCS_SUBAGENTS_PLUGIN_SCOPE,
                    )
                )

    return issues


def _check_permission_mode(
    snap: PluginAgentPa001Snapshot, rel_path: str, code: str, issue_cls: type[ValidationIssue]
) -> list[ValidationIssue]:
    """Check permissionMode field — always error severity.

    Args:
        snap: Parsed agent frontmatter snapshot for PA001.
        rel_path: Relative path of the agent file.
        code: The PA001 error code.
        issue_cls: ValidationIssue class.

    Returns:
        List of error issues.
    """
    if not snap.permission_mode_key_present:
        return []

    return [
        issue_cls(
            field=rel_path,
            severity="error",
            message=(
                "Unsupported `permissionMode` in plugin-packaged agent frontmatter "
                "(Anthropic: ignored when loading agents from a plugin for security reasons)"
            ),
            code=code,
            suggestion=(
                "Remove `permissionMode` here, or copy this agent to `.claude/agents/` or `~/.claude/agents/` "
                "where the full subagent frontmatter schema applies. For session-wide tool policy (not scoped to "
                f"one agent), use `permissions.allow` in settings. Refs: {_DOCS_SUBAGENTS_PLUGIN_SCOPE} · "
                f"{_DOCS_SETTINGS_PERMISSIONS}"
            ),
            docs_url=_DOCS_SUBAGENTS_PLUGIN_SCOPE,
        )
    ]


def _ingest_agent_frontmatter_for_pa001(
    fm_text: str, agent_md: Path, plugin_dir: Path, errors: list, warnings: list
) -> PluginAgentPa001Snapshot | None:
    """Parse agent frontmatter YAML via the boundary ingestor; record FM002/AS004 issues.

    Args:
        fm_text: Raw YAML frontmatter text (no ``---`` delimiters).
        agent_md: Path to the agent markdown file.
        plugin_dir: Plugin root directory for relative path display.
        errors: Mutable error list — FM002 appended on unrecoverable failure.
        warnings: Mutable warning list — AS004 appended on colon auto-fix.

    Returns:
        Snapshot for PA001 checks, or None on YAML failure or non-mapping document root.
    """
    from skilllint.plugin_validator import (  # noqa: PLC0415 — deferred to break circular import
        FM002,
        ErrorCode,
        ValidationIssue,
        generate_docs_url,
    )

    outcome = ingest_plugin_agent_frontmatter_for_pa001(fm_text)

    if outcome.colon_fields_fixed:
        rel = str(agent_md.relative_to(plugin_dir))
        warnings.append(
            ValidationIssue(
                field="description",
                severity="warning",
                message=(
                    f"{rel}: Description contains unquoted colons that break YAML — quote the following fields: "
                    f"{', '.join(outcome.colon_fields_fixed)}"
                ),
                code=ErrorCode.AS004,
                docs_url=generate_docs_url(ErrorCode.AS004),
            )
        )

    if outcome.yaml_error is not None:
        rel = str(agent_md.relative_to(plugin_dir))
        errors.append(
            ValidationIssue(
                field="(yaml)",
                severity="error",
                message=f"{rel}: Invalid YAML frontmatter: {outcome.yaml_error}",
                code=FM002,
                docs_url=generate_docs_url(FM002),
            )
        )
        return None

    return outcome.snapshot


@skilllint_rule(
    "PA001",
    severity="error",
    category="plugin",
    authority={"origin": "anthropic.com", "reference": _DOCS_SUBAGENTS_PLUGIN_SCOPE},
)
def check_pa001(path: Path) -> ValidationResult:
    """PA001 — Restricted frontmatter fields in plugin agent.

    Plugin agents (sub-agents) have restrictions on ``hooks``, ``mcpServers``,
    and ``permissionMode`` in their SKILL.md frontmatter:

    - ``permissionMode`` → **error**: Anthropic ignores it for plugin agents; skilllint
      errors so authors do not assume the mode applies.
    - ``hooks`` → **warning**: Anthropic ignores it at load; always emitted with
      guidance based on plugin ``hooks/hooks.json`` coverage.
    - ``mcpServers`` → **warning** with cross-checking against plugin-level
      ``.mcp.json`` and ``plugin.json``:
      - inline definitions → warn, suggest ``.mcp.json``
      - string references found in plugin config → silenced
      - string references not found → warn

    Source: https://docs.anthropic.com/en/docs/claude-code/sub-agents.md#choose-the-subagent-scope

    Args:
        path: Path to plugin directory (must contain .claude-plugin/plugin.json).

    Returns:
        ValidationResult with errors/warnings for restricted fields found.

    Fix:
    - ``hooks`` → move to ``hooks/hooks.json`` at plugin root
    - ``mcpServers`` → move to ``.mcp.json`` / ``plugin.json`` at plugin root
    - ``permissionMode`` → remove, or copy agent to ``.claude/agents/`` or ``~/.claude/agents/``; or use session-wide ``permissions.allow`` in settings
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

    # Hoist plugin-level JSON reads above the loop to avoid N+1 I/O (Pydantic boundary ingest)
    plugin_hooks_events = ingest_plugin_hook_event_names(plugin_dir / "hooks" / "hooks.json")
    plugin_mcp_servers = ingest_plugin_level_mcp_server_names(plugin_dir)

    for agent_md in sorted(agents_dir.glob("*.md")):
        if agent_md.name in FRONTMATTER_EXEMPT_FILENAMES:
            continue
        content = agent_md.read_text(encoding="utf-8")
        fm_text, _start, _end = extract_frontmatter(content)
        if fm_text is None:
            continue

        snap = _ingest_agent_frontmatter_for_pa001(fm_text, agent_md, plugin_dir, errors, warnings)
        if snap is None:
            continue

        rel_path = str(agent_md.relative_to(plugin_dir))

        # permissionMode — always error
        errors.extend(_check_permission_mode(snap, rel_path, PA001_CODE, ValidationIssue))

        # hooks — warning, silenced if plugin hooks.json covers same events
        warnings.extend(_check_hooks(snap, rel_path, plugin_hooks_events, PA001_CODE, ValidationIssue))

        # mcpServers — warning with cross-checking
        warnings.extend(_check_mcp_servers(snap, rel_path, plugin_mcp_servers, PA001_CODE, ValidationIssue))

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


__all__ = ["PluginAgentFrontmatterValidator", "PluginAgentPa001Snapshot", "check_pa001"]
