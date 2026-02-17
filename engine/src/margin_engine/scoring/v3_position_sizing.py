"""v3 Position Sizing — track-specific with portfolio concentration cap.

Watchlist = 0% (not actionable). Compounders slightly larger than mispricings.
"Both" classification gets maximum 20%.
"""

from __future__ import annotations

from margin_engine.models.scoring import ConvictionLevel

MAX_POSITIONS = 10

_SIZING: dict[str, dict[ConvictionLevel, float]] = {
    "compounder": {
        ConvictionLevel.EXCEPTIONAL: 15.0,
        ConvictionLevel.HIGH: 8.0,
        ConvictionLevel.WATCHLIST: 0.0,
        ConvictionLevel.NONE: 0.0,
    },
    "mispricing": {
        ConvictionLevel.EXCEPTIONAL: 12.0,
        ConvictionLevel.HIGH: 6.0,
        ConvictionLevel.WATCHLIST: 0.0,
        ConvictionLevel.NONE: 0.0,
    },
    "both": {
        ConvictionLevel.EXCEPTIONAL: 20.0,
        ConvictionLevel.HIGH: 10.0,
        ConvictionLevel.WATCHLIST: 0.0,
        ConvictionLevel.NONE: 0.0,
    },
}


def compute_v3_position_size(track: str, conviction: ConvictionLevel) -> float:
    """Compute max position size (%) for a track and conviction level."""
    track_key = track if track in _SIZING else "compounder"
    return _SIZING[track_key].get(conviction, 0.0)
