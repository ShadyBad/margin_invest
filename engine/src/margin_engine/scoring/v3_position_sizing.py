"""v3 Position Sizing — track-specific with portfolio concentration cap.

Compounders slightly larger than mispricings. Medium gets starter positions.
"Both" classification gets maximum 20%.
"""

from __future__ import annotations

from margin_engine.backtesting.models import TierStats
from margin_engine.models.scoring import CompositeTier
from margin_engine.scoring.kelly_position_sizing import kelly_position_size

MAX_POSITIONS = 10

_SIZING: dict[str, dict[CompositeTier, float]] = {
    "compounder": {
        CompositeTier.EXCEPTIONAL: 15.0,
        CompositeTier.HIGH: 8.0,
        CompositeTier.MEDIUM: 4.0,
        CompositeTier.NONE: 0.0,
    },
    "mispricing": {
        CompositeTier.EXCEPTIONAL: 12.0,
        CompositeTier.HIGH: 6.0,
        CompositeTier.MEDIUM: 3.0,
        CompositeTier.NONE: 0.0,
    },
    "both": {
        CompositeTier.EXCEPTIONAL: 20.0,
        CompositeTier.HIGH: 10.0,
        CompositeTier.MEDIUM: 5.0,
        CompositeTier.NONE: 0.0,
    },
    "efficient_growth": {
        CompositeTier.EXCEPTIONAL: 15.0,
        CompositeTier.HIGH: 8.0,
        CompositeTier.MEDIUM: 3.0,
        CompositeTier.NONE: 0.0,
    },
    "compounder_growth": {
        CompositeTier.EXCEPTIONAL: 20.0,
        CompositeTier.HIGH: 10.0,
        CompositeTier.MEDIUM: 5.0,
        CompositeTier.NONE: 0.0,
    },
    "all_three": {
        CompositeTier.EXCEPTIONAL: 20.0,
        CompositeTier.HIGH: 12.0,
        CompositeTier.MEDIUM: 5.0,
        CompositeTier.NONE: 0.0,
    },
}


def compute_v3_position_size(track: str, conviction: CompositeTier) -> float:
    """Compute max position size (%) for a track and conviction level."""
    track_key = track if track in _SIZING else "compounder"
    return _SIZING[track_key].get(conviction, 0.0)


_MIN_KELLY_POSITIONS = 10
"""Minimum number of historical positions required to trust Kelly statistics."""


def kelly_position_size_or_fallback(
    tier: CompositeTier,
    opportunity_type: str,
    tier_stats: list[TierStats] | None,
) -> float:
    """Return a Kelly-derived position size when sufficient data exists, else fixed table.

    Uses Kelly when the matching TierStats entry has n_positions >= 10. Falls back
    to the fixed _SIZING table in all other cases:
      - tier_stats is None
      - tier_stats is empty
      - no entry matches the requested CompositeTier name
      - the matching entry has n_positions < 10
      - Kelly yields 0.0 for negative edge (0.0 is returned as-is)

    Args:
        tier:             The conviction tier of the position.
        opportunity_type: Track classification (e.g. "compounder", "mispricing").
        tier_stats:       Historical per-tier statistics, or None if unavailable.

    Returns:
        Position size as a percentage (e.g. 10.0 for 10%).
    """
    # Attempt Kelly path first
    if tier_stats is not None:
        tier_name = str(tier)  # CompositeTier is a StrEnum — its value equals the tier name
        matching = next(
            (s for s in tier_stats if s.tier == tier_name),
            None,
        )
        if matching is not None and matching.n_positions >= _MIN_KELLY_POSITIONS:
            track_key = opportunity_type if opportunity_type in _SIZING else "compounder"
            cap = _SIZING[track_key].get(tier, 15.0)
            return kelly_position_size(
                win_probability=matching.win_rate,
                expected_gain=matching.avg_winner_return,
                expected_loss=matching.avg_loser_return if matching.avg_loser_return > 0 else 1e-9,
                kelly_fraction=0.25,
                max_position_pct=cap,
            )

    # Fallback to fixed sizing table
    return compute_v3_position_size(opportunity_type, tier)
