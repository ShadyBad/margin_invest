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
