"""HK-series hooks validation rules (HK001-HK005).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

HK001 through HK005 are emitted by ``HookValidator`` in
``plugin_validator.py``.  Detection requires filesystem access (reading
``hooks.json``, resolving relative script paths, checking file existence, and
inspecting Git index execute bits).  None of that information is available from
frontmatter alone, so the validator functions registered here are
**registration-only stubs** — they exist to make rule metadata available via
``RULE_REGISTRY`` (and therefore via ``skilllint rule HKxxx``) without
duplicating the detection logic that belongs in the filesystem-owning
``HookValidator`` class.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | HK001 | Invalid hooks.json structure                              | error     |
    | HK002 | Invalid event type in hooks.json                          | error     |
    | HK003 | Invalid hook entry structure                               | error     |
    | HK004 | Hook script referenced but not found                      | error     |
    | HK005 | Hook script exists but is not executable                  | warning   |
    +-------+-----------------------------------------------------------+-----------+

Import note: ValidationIssue is deferred inside each function to break the
circular import: plugin_validator imports rules/, so rules/ cannot import
plugin_validator at module level.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skilllint.rule_registry import skilllint_rule

if TYPE_CHECKING:
    from pathlib import Path

    from skilllint.plugin_validator import ValidationIssue

# ---------------------------------------------------------------------------
# Spec sources
# ---------------------------------------------------------------------------

_HK_DOCS_BASE = "https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md"


def _docs_url(code: str) -> str:
    """Return the documentation URL for an HK rule code.

    Args:
        code: Rule code string (e.g., "HK001").

    Returns:
        Full URL with anchor for the error code documentation.
    """
    return f"{_HK_DOCS_BASE}#{code.lower()}"


# ---------------------------------------------------------------------------
# HK001 — Invalid hooks.json structure
# ---------------------------------------------------------------------------


@skilllint_rule(
    "HK001",
    severity="error",
    category="hook",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _HK_DOCS_BASE},
)
def check_hk001(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## HK001 — Invalid hooks.json structure

    The ``hooks.json`` file has an invalid top-level structure.  This rule
    fires when:

    - The file cannot be read (I/O error).
    - The file contains malformed JSON that cannot be parsed.
    - The parsed JSON is not an object, or does not have a top-level
      ``"hooks"`` key.
    - The value of the ``"hooks"`` key is not an object (dict).

    A valid ``hooks.json`` must have the shape:

    ```json
    {
      "hooks": {
        "EventType": [...]
      }
    }
    ```

    **Source:** ``HookValidator._validate_hook_config`` in
    ``plugin_validator.py`` — checks file readability, JSON validity, and
    top-level ``"hooks"`` structure.

    **Fix:** Ensure ``hooks.json`` is valid JSON containing a top-level
    ``"hooks"`` key whose value is an object:

    ```json
    {
      "hooks": {
        "PreToolUse": [
          {
            "hooks": [
              {"type": "command", "command": "./hooks/pre-tool.sh"}
            ]
          }
        ]
      }
    }
    ```

    Returns:
        Always an empty list.  HK001 is emitted by ``HookValidator`` in
        ``plugin_validator.py`` after reading and parsing ``hooks.json``
        from the filesystem; this function exists for rule metadata
        registration only.

    <!-- examples: HK001 -->
    """
    # Detection requires reading and JSON-parsing hooks.json from the filesystem.
    # Owned by HookValidator in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# HK002 — Invalid event type in hooks.json
# ---------------------------------------------------------------------------


@skilllint_rule(
    "HK002",
    severity="error",
    category="hook",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _HK_DOCS_BASE},
)
def check_hk002(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## HK002 — Invalid event type in hooks.json

    A key under ``hooks`` in ``hooks.json`` is not a recognised Claude Code
    event type.  Claude Code silently ignores unknown event types, but
    ``skilllint`` flags them so misspelled or outdated event names are caught
    before deployment.

    Valid event types include: ``SessionStart``, ``UserPromptSubmit``,
    ``PreToolUse``, ``PermissionRequest``, ``PostToolUse``,
    ``PostToolUseFailure``, ``Notification``, ``SubagentStart``,
    ``SubagentStop``, ``Stop``, ``StopFailure``, ``TeammateIdle``,
    ``TaskCompleted``, ``InstructionsLoaded``, ``ConfigChange``,
    ``WorktreeCreate``, ``WorktreeRemove``, ``PreCompact``, ``PostCompact``,
    ``Elicitation``, ``ElicitationResult``, ``SessionEnd``.

    **Source:** ``HookValidator.VALID_EVENT_TYPES`` in ``plugin_validator.py``
    — the canonical frozenset of accepted event type strings.

    **Fix:** Replace the unrecognised event type with a valid one:

    ```json
    {
      "hooks": {
        "PreToolUse": [...]
      }
    }
    ```

    Returns:
        Always an empty list.  HK002 is emitted by
        ``HookValidator._validate_hook_config`` in ``plugin_validator.py``
        after iterating over the ``hooks`` object keys; this function exists
        for rule metadata registration only.

    <!-- examples: HK002 -->
    """
    # Detection requires iterating over the parsed hooks.json structure.
    # Owned by HookValidator in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# HK003 — Invalid hook entry structure
# ---------------------------------------------------------------------------


@skilllint_rule(
    "HK003",
    severity="error",
    category="hook",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _HK_DOCS_BASE},
)
def check_hk003(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## HK003 — Invalid hook entry structure

    A hook group or hook entry within ``hooks.json`` is structurally invalid.
    This rule fires when any of the following are true:

    - An event type value is not a list of hook groups.
    - A hook group is not an object.
    - A hook group does not contain a ``"hooks"`` key with a list value.
    - A hook entry is not an object.
    - A hook entry has an invalid or missing ``"type"`` field.  Valid types
      are ``"command"``, ``"http"``, ``"prompt"``, and ``"agent"``.
    - A ``"command"`` entry is missing the required ``"command"`` field.
    - A ``"prompt"`` entry is missing the required ``"prompt"`` field.
    - An ``"http"`` entry is missing the required ``"url"`` field.
    - An ``"agent"`` entry is missing the required ``"prompt"`` field.

    **Source:** ``HookValidator._validate_hook_group`` and
    ``HookValidator._validate_hook_entry`` in ``plugin_validator.py``.

    **Fix:** Ensure each hook group and entry follows the required schema:

    ```json
    {
      "hooks": {
        "PreToolUse": [
          {
            "hooks": [
              {"type": "command", "command": "./hooks/pre-tool.sh"},
              {"type": "prompt", "prompt": "Summarise changes before tool use."}
            ]
          }
        ]
      }
    }
    ```

    Returns:
        Always an empty list.  HK003 is emitted by ``HookValidator`` in
        ``plugin_validator.py`` after validating each group and entry in the
        parsed ``hooks.json`` structure; this function exists for rule metadata
        registration only.

    <!-- examples: HK003 -->
    """
    # Detection requires traversing the parsed hooks.json tree.
    # Owned by HookValidator._validate_hook_group / _validate_hook_entry
    # in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# HK004 — Hook script referenced but not found
# ---------------------------------------------------------------------------


@skilllint_rule(
    "HK004",
    severity="error",
    category="hook",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _HK_DOCS_BASE},
)
def check_hk004(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## HK004 — Hook script referenced but not found

    A ``"command"`` hook entry points to a file path (starting with ``./``,
    ``../``, ``/``, or ``${CLAUDE_PLUGIN_ROOT}/``) that does not exist on the
    filesystem.  Claude Code will fail to execute the hook at runtime.

    Bare shell commands (e.g. ``echo hello``, ``python3 -m pytest``) are
    intentionally excluded from this check.

    **Source:** ``HookValidator._validate_command_script_references`` in
    ``plugin_validator.py`` — resolves the command path relative to the
    ``hooks.json`` directory and checks filesystem existence.

    **Fix:** Create the missing script at the referenced path, or update the
    path to point to an existing executable:

    ```bash
    # Create the missing hook script
    mkdir -p hooks
    cat > hooks/pre-tool.sh << 'EOF'
    #!/usr/bin/env bash
    echo "PreToolUse hook triggered"
    EOF
    git add hooks/pre-tool.sh
    git update-index --chmod=+x hooks/pre-tool.sh
    ```

    Returns:
        Always an empty list.  HK004 is emitted by ``HookValidator`` in
        ``plugin_validator.py`` after resolving script paths relative to the
        ``hooks.json`` parent directory and checking their existence; this
        function exists for rule metadata registration only.

    <!-- examples: HK004 -->
    """
    # Detection requires filesystem path resolution and existence checks.
    # Owned by HookValidator._validate_command_script_references
    # in plugin_validator.py.
    return []


# ---------------------------------------------------------------------------
# HK005 — Hook script exists but is not executable
# ---------------------------------------------------------------------------


@skilllint_rule(
    "HK005",
    severity="warning",
    category="hook",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _HK_DOCS_BASE},
)
def check_hk005(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    """## HK005 — Hook script exists but is not executable

    A ``"command"`` hook entry references a script that exists on disk but
    does not have the execute permission bit set.  Claude Code will fail to
    run the script at hook invocation time.

    The execute bit is checked via the Git index when the file is tracked by
    Git (cross-platform reliable), falling back to ``os.access(X_OK)`` when
    the file is not tracked.

    **Source:** ``HookValidator._validate_command_script_references`` in
    ``plugin_validator.py`` — checks the Git index execute bit via
    ``_git_file_has_execute_bit``, with ``os.access`` as a fallback.

    **Fix:** Mark the script executable.  Prefer the Git method for
    portability:

    ```bash
    # Git-tracked scripts (works on Windows too)
    git update-index --chmod=+x hooks/pre-tool.sh

    # Untracked / non-git scripts
    chmod +x hooks/pre-tool.sh
    ```

    This issue is auto-fixable: run ``skilllint check --fix`` to apply the
    executable bit automatically.

    Returns:
        Always an empty list.  HK005 is emitted by ``HookValidator`` in
        ``plugin_validator.py`` after inspecting Git index permissions and
        ``os.access`` for each referenced command script; this function exists
        for rule metadata registration only.

    <!-- examples: HK005 -->
    """
    # Detection requires Git index inspection and os.access checks on
    # resolved filesystem paths.
    # Owned by HookValidator._validate_command_script_references
    # in plugin_validator.py.
    return []


__all__ = ["check_hk001", "check_hk002", "check_hk003", "check_hk004", "check_hk005"]
