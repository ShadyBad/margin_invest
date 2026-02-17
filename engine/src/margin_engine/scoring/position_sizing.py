"""Position sizing — maps asymmetry ratio + conviction level to max position %.

Higher asymmetry (upside/downside) allows larger positions.
Conviction level scales within the asymmetry-determined maximum.
"""

from __future__ import annotations

from margin_engine.models.scoring import ConvictionLevel

# Asymmetry tier -> max position %
_ASYMMETRY_TIERS: list[tuple[float, float]] = [
    (5.0, 20.0),   # > 5x -> 20%
    (3.0, 10.0),   # 3-5x -> 10%
    (1.5, 5.0),    # 1.5-3x -> 5%
]
_DEFAULT_MAX = 3.0  # < 1.5x -> 3%

# Conviction level -> fraction of max
_CONVICTION_SCALE: dict[ConvictionLevel, float] = {
    ConvictionLevel.EXCEPTIONAL: 1.0,
    ConvictionLevel.HIGH: 0.6,
    ConvictionLevel.WATCHLIST: 0.3,
    ConvictionLevel.NONE: 0.0,
}


def compute_position_size(
    asymmetry_ratio: float,
    conviction_level: ConvictionLevel,
) -> float:
    """Compute max position size (%) from asymmetry ratio and conviction level.

    Args:
        asymmetry_ratio: Upside/downside ratio (e.g. 3.0 means 3:1 upside).
        conviction_level: Current conviction level.

    Returns:
        Maximum position size as a percentage (e.g. 10.0 for 10%).
    """
    # Determine max from asymmetry tier
    max_pct = _DEFAULT_MAX
    for threshold, tier_max in _ASYMMETRY_TIERS:
        if asymmetry_ratio > threshold:
            max_pct = tier_max
            break

    # Scale by conviction
    scale = _CONVICTION_SCALE[conviction_level]
    return max_pct * scale
