"""v3 Position Sizing — track-specific with portfolio concentration cap.

Compounders slightly larger than mispricings. Medium gets starter positions.
"Both" classification gets maximum 20%.
"""

from __future__ import annotations

from margin_engine.models.scoring import CompositeTier

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
