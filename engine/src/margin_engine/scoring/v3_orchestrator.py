"""v3 Orchestrator — runs both tracks independently, assigns conviction, handles 'both'.

This is the top-level v3 scoring entry point. It does NOT pick a winner —
each track produces an independent result. A stock can qualify on either, both, or neither.
"""

from __future__ import annotations

from pydantic import BaseModel

from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_position_sizing import compute_v3_position_size


class V3TrackResult(BaseModel):
    """Result from a single track's gate cascade + scoring."""

    track: str  # "compounder" or "mispricing"
    qualifies: bool
    conviction: ConvictionLevel
    score: float
    gates_passed: int
    total_gates: int


class V3Result(BaseModel):
    """Final v3 scoring result for a single ticker."""

    ticker: str
    opportunity_type: str  # "compounder", "mispricing", "both", "neither"
    conviction: ConvictionLevel
    track_a: V3TrackResult
    track_b: V3TrackResult
    timing_signal: str
    max_position_pct: float


# Conviction levels considered "strong" for "both" promotion
_STRONG_CONVICTIONS = frozenset({ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH})

# Conviction levels that count as qualifying
_QUALIFYING_CONVICTIONS = frozenset(
    {ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH, ConvictionLevel.WATCHLIST}
)

# Ordering for conviction comparison (lower index = stronger)
_CONVICTION_ORDER = {
    ConvictionLevel.EXCEPTIONAL: 0,
    ConvictionLevel.HIGH: 1,
    ConvictionLevel.WATCHLIST: 2,
    ConvictionLevel.NONE: 3,
}


def orchestrate_v3(
    ticker: str,
    track_a: V3TrackResult,
    track_b: V3TrackResult,
    timing_signal: str,
) -> V3Result:
    """Orchestrate v3 scoring — combine independent track results.

    Rules:
    - Both tracks qualify at HIGH+ -> "both", promoted to EXCEPTIONAL, 20% position
    - Only Track A qualifies -> "compounder"
    - Only Track B qualifies -> "mispricing"
    - Neither qualifies -> "neither", 0% position
    """
    a_qualifies = track_a.qualifies and track_a.conviction in _QUALIFYING_CONVICTIONS
    b_qualifies = track_b.qualifies and track_b.conviction in _QUALIFYING_CONVICTIONS

    a_strong = track_a.conviction in _STRONG_CONVICTIONS
    b_strong = track_b.conviction in _STRONG_CONVICTIONS

    # "Both" promotion: both qualify at HIGH or EXCEPTIONAL
    if a_qualifies and b_qualifies and a_strong and b_strong:
        conviction = ConvictionLevel.EXCEPTIONAL
        position = compute_v3_position_size("both", conviction)
        return V3Result(
            ticker=ticker,
            opportunity_type="both",
            conviction=conviction,
            track_a=track_a,
            track_b=track_b,
            timing_signal=timing_signal,
            max_position_pct=position,
        )

    # Single-track qualification: pick the stronger qualifying track
    if a_qualifies and b_qualifies:
        # Both qualify but not both strong — pick the stronger one
        a_rank = _CONVICTION_ORDER[track_a.conviction]
        b_rank = _CONVICTION_ORDER[track_b.conviction]
        if a_rank <= b_rank:
            conviction = track_a.conviction
            opp_type = "compounder"
        else:
            conviction = track_b.conviction
            opp_type = "mispricing"
    elif a_qualifies:
        conviction = track_a.conviction
        opp_type = "compounder"
    elif b_qualifies:
        conviction = track_b.conviction
        opp_type = "mispricing"
    else:
        conviction = ConvictionLevel.NONE
        opp_type = "neither"

    position = compute_v3_position_size(opp_type, conviction)

    return V3Result(
        ticker=ticker,
        opportunity_type=opp_type,
        conviction=conviction,
        track_a=track_a,
        track_b=track_b,
        timing_signal=timing_signal,
        max_position_pct=position,
    )
