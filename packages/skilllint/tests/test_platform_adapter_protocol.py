"""Tests for skilllint.adapters.protocol module.

Tests:
- PlatformAdapter is a @runtime_checkable Protocol
- Protocol method stubs return expected values when called directly
- Concrete adapter classes satisfy isinstance(obj, PlatformAdapter)
- Incomplete adapters do NOT satisfy isinstance(obj, PlatformAdapter)

How: Calls protocol methods directly on Protocol class and on conforming
     mock implementations.
Why: The protocol method stubs (``...`` bodies) were 0% covered because
     they are only called when testing structural subtyping at runtime.
"""

from __future__ import annotations

import pathlib
from typing import no_type_check

import pytest

from skilllint.adapters.protocol import PlatformAdapter


class _FullAdapter:
    """A complete mock adapter implementing all five protocol methods."""

    def id(self) -> str:
        return "mock"

    def path_patterns(self) -> list[str]:
        return ["**/*.mock"]

    def applicable_rules(self) -> set[str]:
        return {"AS", "CC"}

    def constraint_scopes(self) -> set[str]:
        return {"shared"}

    def validate(self, path: pathlib.Path) -> list[dict]:
        return []


class _IncompleteAdapter:
    """A mock adapter missing constraint_scopes and validate methods."""

    def id(self) -> str:
        return "incomplete"

    def path_patterns(self) -> list[str]:
        return []

    def applicable_rules(self) -> set[str]:
        return set()


class TestPlatformAdapterProtocol:
    """Tests for the PlatformAdapter Protocol class."""

    def test_full_adapter_satisfies_protocol(self) -> None:
        """A class implementing all five methods is a PlatformAdapter."""
        adapter = _FullAdapter()
        assert isinstance(adapter, PlatformAdapter)

    def test_incomplete_adapter_does_not_satisfy_protocol(self) -> None:
        """A class missing required methods is not a PlatformAdapter."""
        adapter = _IncompleteAdapter()
        assert not isinstance(adapter, PlatformAdapter)

    def test_protocol_is_runtime_checkable(self) -> None:
        """isinstance() against PlatformAdapter does not raise TypeError."""
        # Would raise TypeError if not @runtime_checkable
        result = isinstance(_FullAdapter(), PlatformAdapter)
        assert isinstance(result, bool)

    @no_type_check
    def test_protocol_method_id(self) -> None:
        """Protocol.id() ellipsis body is reachable via unbound call.

        ``self`` is not a real adapter; this only exercises runtime Protocol stubs.
        ``@no_type_check`` marks intentional static unsoundness (see TYPING_POLICY —
        tests, not ingress boundaries).
        """
        result = PlatformAdapter.id(None)
        assert result is None

    @no_type_check
    def test_protocol_method_path_patterns(self) -> None:
        """Protocol.path_patterns() ellipsis body is reachable via unbound call."""
        result = PlatformAdapter.path_patterns(None)
        assert result is None

    @no_type_check
    def test_protocol_method_applicable_rules(self) -> None:
        """Protocol.applicable_rules() ellipsis body is reachable via unbound call."""
        result = PlatformAdapter.applicable_rules(None)
        assert result is None

    @no_type_check
    def test_protocol_method_constraint_scopes(self) -> None:
        """Protocol.constraint_scopes() ellipsis body is reachable via unbound call."""
        result = PlatformAdapter.constraint_scopes(None)
        assert result is None

    @no_type_check
    def test_protocol_method_validate(self) -> None:
        """Protocol.validate() ellipsis body is reachable via unbound call."""
        result = PlatformAdapter.validate(None, pathlib.Path())
        assert result is None

    def test_real_adapters_satisfy_protocol(self) -> None:
        """Built-in adapters (ClaudeCode, Cursor, Codex) satisfy PlatformAdapter."""
        from skilllint.adapters.claude_code import ClaudeCodeAdapter
        from skilllint.adapters.codex import CodexAdapter
        from skilllint.adapters.cursor import CursorAdapter

        for adapter_cls in (ClaudeCodeAdapter, CursorAdapter, CodexAdapter):
            adapter = adapter_cls()
            assert isinstance(adapter, PlatformAdapter), (
                f"{adapter_cls.__name__} should satisfy PlatformAdapter protocol"
            )

    def test_non_adapter_object_not_protocol(self) -> None:
        """A plain object without the required methods is not a PlatformAdapter."""
        assert not isinstance(object(), PlatformAdapter)
        assert not isinstance("string", PlatformAdapter)
        assert not isinstance(42, PlatformAdapter)


class TestProtocolMethodSignatures:
    """Tests for the concrete method behaviour on real adapters."""

    @pytest.fixture(params=["claude_code", "cursor", "codex"])
    def adapter(self, request: pytest.FixtureRequest) -> PlatformAdapter:
        """Parametrised fixture providing each built-in adapter."""
        if request.param == "claude_code":
            from skilllint.adapters.claude_code import ClaudeCodeAdapter

            return ClaudeCodeAdapter()
        if request.param == "cursor":
            from skilllint.adapters.cursor import CursorAdapter

            return CursorAdapter()
        from skilllint.adapters.codex import CodexAdapter

        return CodexAdapter()

    def test_id_returns_non_empty_string(self, adapter: PlatformAdapter) -> None:
        """id() returns a non-empty string."""
        result = adapter.id()
        assert isinstance(result, str)
        assert result

    def test_path_patterns_returns_list_of_strings(self, adapter: PlatformAdapter) -> None:
        """path_patterns() returns a non-empty list of strings."""
        result = adapter.path_patterns()
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(p, str) for p in result)

    def test_applicable_rules_returns_set_of_strings(self, adapter: PlatformAdapter) -> None:
        """applicable_rules() returns a set of strings."""
        result = adapter.applicable_rules()
        assert isinstance(result, set)
        assert all(isinstance(r, str) for r in result)

    def test_constraint_scopes_returns_set(self, adapter: PlatformAdapter) -> None:
        """constraint_scopes() returns a set."""
        result = adapter.constraint_scopes()
        assert isinstance(result, set)
