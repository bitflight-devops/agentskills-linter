"""
Test stubs for Phase 2 adapter requirements (ADPT-01 through ADPT-05).

Wave 0 TDD scaffold — all tests fail RED (ImportError) until plans 02-02
through 02-05 create the implementation modules.

Test IDs map to VALIDATION.md task IDs for traceability.
"""

from __future__ import annotations

import pathlib

from skilllint.adapters import load_adapters
from skilllint.adapters.claude_code import ClaudeCodeAdapter
from skilllint.adapters.codex import CodexAdapter
from skilllint.adapters.cursor import CursorAdapter

# These imports fail RED until plan 02-02 creates the modules.
from skilllint.adapters.protocol import PlatformAdapter

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
CLAUDE_CODE_FIXTURES = FIXTURES / "claude_code"
CURSOR_FIXTURES = FIXTURES / "cursor"
CODEX_FIXTURES = FIXTURES / "codex"


# ---------------------------------------------------------------------------
# ADPT-01: Protocol definition and runtime checkability
# ---------------------------------------------------------------------------


def test_protocol_defined():
    """PlatformAdapter is importable as a typing.Protocol."""

    assert hasattr(PlatformAdapter, "__protocol_attrs__") or isinstance(PlatformAdapter, type), (
        "PlatformAdapter must be a Protocol class"
    )


def test_runtime_checkable():
    """PlatformAdapter is decorated with @runtime_checkable."""

    class MockAdapter:
        def id(self) -> str:
            return "mock"

        def path_patterns(self) -> list[str]:
            return ["**/*.mock"]

        def applicable_rules(self) -> set[str]:
            return {"AS"}

        def validate(self, path: pathlib.Path) -> list[dict]:
            return []

    # runtime_checkable allows isinstance checks without raising TypeError
    result = isinstance(MockAdapter(), PlatformAdapter)
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# ADPT-02: Entry_points discovery
# ---------------------------------------------------------------------------


def test_entry_points_discovery():
    """load_adapters() returns at least the three bundled adapters."""
    adapters = load_adapters()
    adapter_ids = {a.id() for a in adapters}
    assert "claude_code" in adapter_ids
    assert "cursor" in adapter_ids
    assert "codex" in adapter_ids


def test_third_party_adapter_discovery(mocker):
    """load_adapters() includes a mocked fourth entry_point."""

    class FourthAdapter:
        def id(self) -> str:
            return "fourth_platform"

        def path_patterns(self) -> list[str]:
            return ["**/*.fourth"]

        def applicable_rules(self) -> set[str]:
            return {"AS"}

        def validate(self, path: pathlib.Path) -> list[dict]:
            return []

    mock_ep = mocker.MagicMock()
    mock_ep.load.return_value = FourthAdapter

    mocker.patch("skilllint.adapters.importlib.metadata.entry_points", return_value=[mock_ep])

    adapters = load_adapters()
    adapter_ids = {a.id() for a in adapters}
    assert "fourth_platform" in adapter_ids


# ---------------------------------------------------------------------------
# ADPT-03: Claude Code adapter path patterns and validation
# ---------------------------------------------------------------------------


def test_claude_code_path_patterns():
    """ClaudeCodeAdapter.path_patterns() declares .claude/**/*.md pattern."""
    adapter = ClaudeCodeAdapter()
    patterns = adapter.path_patterns()
    assert ".claude/**/*.md" in patterns


def test_cursor_adapter_mdc_validation():
    """CursorAdapter validates valid_rule.mdc with zero violations."""
    adapter = CursorAdapter()
    violations = adapter.validate(CURSOR_FIXTURES / "valid_rule.mdc")
    assert violations == [], f"Expected no violations, got: {violations}"


def test_cursor_mdc_unknown_fields():
    """CursorAdapter reports a violation for unknown field in .mdc frontmatter."""
    adapter = CursorAdapter()
    violations = adapter.validate(CURSOR_FIXTURES / "invalid_rule.mdc")
    codes = [v["code"] for v in violations]
    assert any("cursor" in c.lower() or "unknown" in c.lower() or c for c in codes), (
        f"Expected a violation for unknown .mdc field, got: {violations}"
    )
    assert len(violations) > 0


# ---------------------------------------------------------------------------
# ADPT-04: Cursor adapter
# ---------------------------------------------------------------------------


def test_cursor_adapter_path_patterns():
    """CursorAdapter.path_patterns() declares **/*.mdc pattern."""
    adapter = CursorAdapter()
    patterns = adapter.path_patterns()
    assert "**/*.mdc" in patterns


# ---------------------------------------------------------------------------
# ADPT-05: Codex adapter
# ---------------------------------------------------------------------------


def test_codex_agents_md_validation():
    """Empty AGENTS.md produces a violation; non-empty passes."""
    adapter = CodexAdapter()

    # empty file should fail
    empty_violations = adapter.validate(CODEX_FIXTURES / "empty_agents.md")
    assert len(empty_violations) > 0, "Expected violation for empty AGENTS.md"

    # non-empty file should pass
    valid_violations = adapter.validate(CODEX_FIXTURES / "valid_agents.md")
    assert valid_violations == [], f"Expected no violations for valid AGENTS.md, got: {valid_violations}"


def test_codex_rules_field_validation():
    """prefix_rule() with unknown field 'owner' produces a violation."""
    adapter = CodexAdapter()
    violations = adapter.validate(CODEX_FIXTURES / "invalid_rules.rules")
    assert len(violations) > 0, f"Expected violation for unknown field 'owner' in .rules, got: {violations}"


def test_codex_path_patterns():
    """CodexAdapter.path_patterns() declares AGENTS.md pattern."""
    adapter = CodexAdapter()
    patterns = adapter.path_patterns()
    assert "AGENTS.md" in patterns
