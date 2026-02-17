"""Timing overlay — momentum as entry signal, not conviction.

For Track A (Compounder): positive momentum confirms quality -> buy_now.
For Track B (Mispricing): negative momentum is contrarian confirmation -> buy_now.
"""

from __future__ import annotations


def compute_timing_signal(
    momentum_percentile: float,
    is_mispricing_track: bool,
    sue_percentile: float | None = None,
) -> str:
    """Compute timing signal from momentum direction and track type.

    Args:
        momentum_percentile: Momentum percentile rank (0-100).
        is_mispricing_track: True if the winning track is mispricing (Track B).
        sue_percentile: Optional SUE (Standardized Unexpected Earnings) percentile.
            Reserved for future use.

    Returns:
        One of: "buy_now", "add_on_pullback", "wait_for_catalyst".
    """
    if is_mispricing_track:
        # Track B: contrarian — negative momentum is confirmation
        if momentum_percentile < 50.0:
            return "buy_now"
        return "wait_for_catalyst"
    else:
        # Track A: momentum confirms quality
        if momentum_percentile >= 50.0:
            return "buy_now"
        return "add_on_pullback"


def compute_v3_timing_signal(
    momentum_percentile: float,
    is_mispricing_track: bool,
) -> str:
    """Compute v3 timing signal with 3-tier Track A signals.

    Track A (Compounder):
        >= 50  -> buy_now
        30-49  -> add_on_pullback
        < 30   -> accumulate_slowly (DCA into compounders in pain)

    Track B (Mispricing):
        < 50   -> buy_now (contrarian confirmation)
        >= 50  -> wait_for_catalyst
    """
    if is_mispricing_track:
        return "buy_now" if momentum_percentile < 50.0 else "wait_for_catalyst"
    # Track A: 3-tier
    if momentum_percentile >= 50.0:
        return "buy_now"
    if momentum_percentile >= 30.0:
        return "add_on_pullback"
    return "accumulate_slowly"
