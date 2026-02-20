"""Dual-track orchestrator — picks best of compounder (Track A) vs mispricing (Track B).

This is the top-level scoring entry point for the v2 conviction engine.
It runs both tracks, picks the higher score, applies conviction gates,
computes position sizing, and sets timing signal.
"""

from __future__ import annotations

from margin_engine.models.scoring import (
    CompositeScore,
    OpportunityType,
)
from margin_engine.scoring.conviction_gates import ConvictionGateResult
from margin_engine.scoring.position_sizing import compute_position_size

# Medium threshold — gate failures cap conviction here
_MEDIUM_CAP = 98.0


def score_dual_track(
    track_a_score: CompositeScore,
    track_b_score: CompositeScore,
    opportunity_type: OpportunityType,
    asymmetry_ratio_value: float,
    timing_signal: str,
    gate_result_a: ConvictionGateResult,
    gate_result_b: ConvictionGateResult,
) -> CompositeScore:
    """Pick the winning track and assemble the final CompositeScore.

    Logic:
        1. Pick the track with higher composite_percentile (tie goes to Track A).
        2. Copy the winning CompositeScore.
        3. Set v2 fields: opportunity_type, winning_track, asymmetry_ratio, timing_signal.
        4. If winning track's gates failed -> cap conviction at MEDIUM.
        5. Compute position sizing from asymmetry + conviction level.

    Args:
        track_a_score: CompositeScore from compounder scorer.
        track_b_score: CompositeScore from mispricing scorer.
        opportunity_type: Classified opportunity type.
        asymmetry_ratio_value: Computed asymmetry ratio.
        timing_signal: Computed timing signal string.
        gate_result_a: Conviction gate result for Track A.
        gate_result_b: Conviction gate result for Track B.

    Returns:
        Final CompositeScore with all v2 fields populated.
    """
    # 1. Pick winning track (tie goes to Track A)
    if track_a_score.composite_percentile >= track_b_score.composite_percentile:
        winner = track_a_score
        winning_gate = gate_result_a
    else:
        winner = track_b_score
        winning_gate = gate_result_b

    # 2. Copy the winning score (Pydantic model_copy)
    result = winner.model_copy()

    # 3. Set v2 fields
    result.opportunity_type = opportunity_type
    result.winning_track = winner.winning_track
    result.asymmetry_ratio = asymmetry_ratio_value
    result.timing_signal = timing_signal

    # 4. Cap conviction if gates failed
    if not winning_gate.passed:
        result.composite_percentile = min(result.composite_percentile, _MEDIUM_CAP)

    # 5. Compute position sizing
    conviction_level = result.conviction_level
    result.max_position_pct = compute_position_size(asymmetry_ratio_value, conviction_level)

    return result
