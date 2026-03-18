"""V4 Orchestrator — three-track scoring with style-aware promotion rules.

Extends v3 by adding Track C (Efficient Growth) and new promotion combos:
- all_three: A+B+C strong -> EXCEPTIONAL, 20% max position
- compounder_growth: A+C strong -> EXCEPTIONAL
- Existing "both" (A+B) rule preserved
"""

from __future__ import annotations

from pydantic import BaseModel

from margin_engine.models.scoring import CompositeTier
from margin_engine.scoring.v3_orchestrator import V3TrackResult
from margin_engine.scoring.v3_position_sizing import compute_v3_position_size


class V4Result(BaseModel):
    """Final v4 scoring result for a single ticker."""

    ticker: str
    opportunity_type: str  # "compounder", "mispricing", "efficient_growth",
    # "both", "compounder_growth", "all_three", "neither"
    conviction: CompositeTier
    track_a: V3TrackResult
    track_b: V3TrackResult
    track_c: V3TrackResult
    timing_signal: str
    max_position_pct: float


_STRONG_CONVICTIONS = frozenset({CompositeTier.EXCEPTIONAL, CompositeTier.HIGH})

_QUALIFYING_CONVICTIONS = frozenset(
    {CompositeTier.EXCEPTIONAL, CompositeTier.HIGH, CompositeTier.MEDIUM}
)

_CONVICTION_ORDER = {
    CompositeTier.EXCEPTIONAL: 0,
    CompositeTier.HIGH: 1,
    CompositeTier.MEDIUM: 2,
    CompositeTier.NONE: 3,
}


def _qualifies(track: V3TrackResult) -> bool:
    """Return True if a track qualifies (passed gates + qualifying conviction)."""
    return track.qualifies and track.conviction in _QUALIFYING_CONVICTIONS


def _is_strong(track: V3TrackResult) -> bool:
    """Return True if a track has strong conviction (HIGH or EXCEPTIONAL)."""
    return track.conviction in _STRONG_CONVICTIONS


def orchestrate_v4(
    ticker: str,
    track_a: V3TrackResult,
    track_b: V3TrackResult,
    track_c: V3TrackResult,
    timing_signal: str,
) -> V4Result:
    """Orchestrate v4 scoring — combine three track results.

    Promotion rules (checked in order):
    1. All three strong -> "all_three", EXCEPTIONAL
    2. A+B strong -> "both", EXCEPTIONAL (existing rule)
    3. A+C strong -> "compounder_growth", EXCEPTIONAL
    4. B+C: no special promotion, pick strongest
    5. Single qualifier -> use that track
    6. None -> "neither"
    """
    a_qual = _qualifies(track_a)
    b_qual = _qualifies(track_b)
    c_qual = _qualifies(track_c)

    a_strong = a_qual and _is_strong(track_a)
    b_strong = b_qual and _is_strong(track_b)
    c_strong = c_qual and _is_strong(track_c)

    # Rule 1: All three strong -> "all_three", EXCEPTIONAL
    # At least one participating track must be non-conditional for EXCEPTIONAL
    if a_strong and b_strong and c_strong:
        all_conditional = track_a.conditional and track_b.conditional and track_c.conditional
        conviction = CompositeTier.HIGH if all_conditional else CompositeTier.EXCEPTIONAL
        opp_type = "all_three"
        position = compute_v3_position_size(opp_type, conviction)
        return V4Result(
            ticker=ticker,
            opportunity_type=opp_type,
            conviction=conviction,
            track_a=track_a,
            track_b=track_b,
            track_c=track_c,
            timing_signal=timing_signal,
            max_position_pct=position,
        )

    # Rule 2: A+B strong -> "both", EXCEPTIONAL
    # At least one participating track must be non-conditional for EXCEPTIONAL
    if a_strong and b_strong:
        both_conditional = track_a.conditional and track_b.conditional
        conviction = CompositeTier.HIGH if both_conditional else CompositeTier.EXCEPTIONAL
        opp_type = "both"
        position = compute_v3_position_size(opp_type, conviction)
        return V4Result(
            ticker=ticker,
            opportunity_type=opp_type,
            conviction=conviction,
            track_a=track_a,
            track_b=track_b,
            track_c=track_c,
            timing_signal=timing_signal,
            max_position_pct=position,
        )

    # Rule 3: A+C strong -> "compounder_growth", EXCEPTIONAL
    # At least one participating track must be non-conditional for EXCEPTIONAL
    if a_strong and c_strong:
        both_conditional = track_a.conditional and track_c.conditional
        conviction = CompositeTier.HIGH if both_conditional else CompositeTier.EXCEPTIONAL
        opp_type = "compounder_growth"
        position = compute_v3_position_size(opp_type, conviction)
        return V4Result(
            ticker=ticker,
            opportunity_type=opp_type,
            conviction=conviction,
            track_a=track_a,
            track_b=track_b,
            track_c=track_c,
            timing_signal=timing_signal,
            max_position_pct=position,
        )

    # Rule 4/5: No special promotion — pick strongest qualifying single track
    qualifying = []
    if a_qual:
        qualifying.append(("compounder", track_a.conviction))
    if b_qual:
        qualifying.append(("mispricing", track_b.conviction))
    if c_qual:
        qualifying.append(("efficient_growth", track_c.conviction))

    if qualifying:
        # Pick strongest by conviction, then first in list order (A > B > C)
        qualifying.sort(key=lambda x: _CONVICTION_ORDER[x[1]])
        opp_type, conviction = qualifying[0]
        position = compute_v3_position_size(opp_type, conviction)
    else:
        # Rule 6: None qualify
        opp_type = "neither"
        conviction = CompositeTier.NONE
        position = 0.0

    return V4Result(
        ticker=ticker,
        opportunity_type=opp_type,
        conviction=conviction,
        track_a=track_a,
        track_b=track_b,
        track_c=track_c,
        timing_signal=timing_signal,
        max_position_pct=position,
    )
