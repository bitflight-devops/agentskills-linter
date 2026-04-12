"""SL-series symlink validation rules (SL001).

Each function is decorated with @skilllint_rule and returns a list of
ValidationIssue objects.

SL001 is emitted by ``SymlinkTargetValidator`` in ``plugin_validator.py``.
Detection requires filesystem access (reading symlink targets via
``Path.readlink()`` / ``os.readlink()``, scanning directory trees for
symlinks, and checking whether cleaned targets resolve to existing paths).
None of that information is available from frontmatter alone, so the
validator function registered here is a **registration-only stub** — it
exists to make rule metadata available via ``RULE_REGISTRY`` (and therefore
via ``skilllint rule SL001``) without duplicating the detection logic that
belongs in the filesystem-owning ``SymlinkTargetValidator`` class.

Rule IDs and default severities:
    +-------+-----------------------------------------------------------+-----------+
    | ID    | Summary                                                   | Severity  |
    +-------+-----------------------------------------------------------+-----------+
    | SL001 | Symlink target has trailing whitespace/newlines           | error     |
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

_SL_DOCS_BASE = "https://github.com/jamie-bitflight/claude_skills/blob/main/plugins/plugin-creator/docs/ERROR_CODES.md"


def _docs_url(code: str) -> str:
    """Return the documentation URL for an SL rule code.

    Args:
        code: Rule code string (e.g., "SL001").

    Returns:
        Full URL with anchor for the error code documentation.
    """
    return f"{_SL_DOCS_BASE}#{code.lower()}"


# ---------------------------------------------------------------------------
# SL001 — Symlink target has trailing whitespace/newlines
# ---------------------------------------------------------------------------


@skilllint_rule(
    "SL001",
    severity="error",
    category="symlink",
    platforms=["agentskills"],
    authority={"origin": "github.com/jamie-bitflight/claude_skills", "reference": _SL_DOCS_BASE},
)
def check_sl001(frontmatter: dict[str, object], path: Path, file_type: str) -> list[ValidationIssue]:
    r"""## SL001 — Symlink target has trailing whitespace or newlines

    A symlink within the validated path has a target string that contains
    trailing whitespace or newline characters.  For example,
    ``os.readlink()`` may return ``'../../python3-development/skills/uv\\n'``
    when the symlink was created with a newline-terminated target.

    Such symlinks cause ``Path.resolve()`` and ``is_file()``/``is_dir()`` to
    fail silently or raise unexpected errors, producing false-positive
    failures in other validators that depend on resolved paths.

    **Source:** ``SymlinkTargetValidator.validate`` in
    ``plugin_validator.py`` — reads symlink targets via ``Path.readlink()``,
    compares the raw target string against its ``rstrip()`` form, and emits
    this rule for any mismatch.

    **Fix:** Strip trailing whitespace from the symlink target and recreate
    the symlink.  Run ``skilllint check --fix`` to apply the fix
    automatically, or repair manually:

    ```bash
    python3 -c "
    import os
    p = 'path/to/symlink'
    t = os.readlink(p).rstrip()
    os.remove(p)
    os.symlink(t, p)
    "
    ```

    The auto-fix is only applied when the cleaned target resolves to an
    existing path.  Symlinks whose cleaned target does not exist are left
    untouched and reported as unfixable.

    Returns:
        Always an empty list.  SL001 is emitted by ``SymlinkTargetValidator``
        in ``plugin_validator.py`` after reading symlink targets from the
        filesystem; this function exists for rule metadata registration only.

    <!-- examples: SL001 -->
    """
    # Detection requires reading symlink targets from the filesystem via
    # Path.readlink() and scanning directory trees for symlinks.
    # Owned by SymlinkTargetValidator in plugin_validator.py.
    return []


__all__ = ["check_sl001"]
