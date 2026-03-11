"""Backward-compatibility shim for skilllint.token_utils.

All token counting logic now lives in :mod:`skilllint.token_counter`.
This module re-exports the public symbols so existing imports continue
to work without modification.
"""

from __future__ import annotations

from skilllint.token_counter import TOKEN_ERROR_THRESHOLD, TOKEN_WARNING_THRESHOLD, count_tokens

__all__ = ["TOKEN_ERROR_THRESHOLD", "TOKEN_WARNING_THRESHOLD", "count_tokens"]
