"""V3 Track C (Efficient Growth) conviction thresholds."""

from __future__ import annotations

from margin_engine.models.scoring import CompositeTier

_FULL_GATES = 4
_MEDIUM_GATES = 3
_EXCEPTIONAL_RULE_OF_40 = 50.0
_EXCEPTIONAL_ROIC_WACC_MULTIPLE = 2.0
_EXCEPTIONAL_TAM_HEADROOM = 5.0
_HIGH_RULE_OF_40 = 30.0


def assess_track_c_conviction(
    gates_passed: int,
    total_gates: int,
    rule_of_40_score: float,
    incremental_roic: float,
    wacc: float,
    tam_headroom: float,
    conditional: bool = False,
) -> CompositeTier:
    """Determine Track C conviction level from absolute thresholds.

    EXCEPTIONAL: 4/4 gates + rule_of_40 >= 50 + inc_ROIC > 2*WACC + TAM > 5x
    HIGH: 4/4 gates + rule_of_40 >= 30 + inc_ROIC > WACC
    MEDIUM: 3+ gates
    NONE: < 3 gates

    Args:
        conditional: When True, cap maximum conviction at HIGH (trajectory-based
            passes cannot reach EXCEPTIONAL).
    """
    if gates_passed < _MEDIUM_GATES:
        return CompositeTier.NONE

    if (
        gates_passed >= _FULL_GATES
        and rule_of_40_score >= _EXCEPTIONAL_RULE_OF_40
        and incremental_roic > _EXCEPTIONAL_ROIC_WACC_MULTIPLE * wacc
        and tam_headroom > _EXCEPTIONAL_TAM_HEADROOM
        and tam_headroom < 50  # reject implausible TAM estimates
    ):
        # Conditional passes (trajectory-based) cap at HIGH
        return CompositeTier.HIGH if conditional else CompositeTier.EXCEPTIONAL

    if (
        gates_passed >= _FULL_GATES
        and rule_of_40_score >= _HIGH_RULE_OF_40
        and incremental_roic > wacc
    ):
        return CompositeTier.HIGH

    return CompositeTier.MEDIUM
