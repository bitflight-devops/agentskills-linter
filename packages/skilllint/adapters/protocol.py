"""PlatformAdapter Protocol definition.

Defines the @runtime_checkable Protocol that all platform adapters must satisfy.
Any object implementing the five methods (id, path_patterns, applicable_rules,
constraint_scopes, validate) passes isinstance(obj, PlatformAdapter) without inheritance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import pathlib


@runtime_checkable
class PlatformAdapter(Protocol):
    """Protocol for platform-specific skill/plugin adapters.

    Any class implementing all five methods satisfies this Protocol.
    No inheritance required — structural subtyping only.
    """

    def id(self) -> str:
        """Return the unique platform identifier (e.g. 'claude_code', 'cursor')."""
        ...

    def path_patterns(self) -> list[str]:
        """Return glob patterns matching files this adapter handles."""
        ...

    def applicable_rules(self) -> set[str]:
        """Return the set of rule-series codes this adapter applies (e.g. {'AS', 'CC'})."""
        ...

    def constraint_scopes(self) -> set[str]:
        """Return the set of constraint_scope values from the provider schema.

        Values are extracted from field-level constraint_scope annotations
        in the loaded schema (values: 'shared' or 'provider_specific').
        """
        ...

    def validate(self, path: pathlib.Path) -> list[dict]:
        """Validate the given file path and return a list of violation dicts."""
        ...
