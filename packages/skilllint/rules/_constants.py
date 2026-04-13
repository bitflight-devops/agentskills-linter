"""Rule-set constants for the skilllint rules package."""

from __future__ import annotations

# Full set of expected series prefixes: AS + FM + PA (existing 3) + SK + LK + PD + PL +
# HK + NR + SL + TC + PR (9 extracted from monolith) + CU + CX (2 adapter-backed).
# CM001 is scoped out — reserved, no validator logic (P038 architect spec §9).
# Source: P038 architect spec section 8.
EXPECTED_SERIES: frozenset[str] = frozenset({
    "AS",
    "FM",
    "PA",
    "SK",
    "LK",
    "PD",
    "PL",
    "HK",
    "NR",
    "SL",
    "TC",
    "PR",
    "CU",
    "CX",
})

# Derived from EXPECTED_SERIES so the count never drifts from the canonical set.
MIN_REGISTERED_SERIES: int = len(EXPECTED_SERIES)
