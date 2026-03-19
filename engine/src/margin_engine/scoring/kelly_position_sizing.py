"""Kelly Criterion position sizing formula.

Implements fractional Kelly sizing with a configurable fraction and hard cap.
Full Kelly: f* = (p * b - q) / b  where b = gain/loss, q = 1 - p.
Fractional Kelly: kelly_fraction * max(0, f*) * 100, capped at max_position_pct.
"""

from __future__ import annotations

from pydantic import BaseModel


class KellyConstraints(BaseModel):
    """Portfolio-level constraints for Kelly-sized positions."""

    max_single_position: float = 15.0
    max_top_3_combined: float = 50.0
    max_sector_concentration: float = 30.0
    min_positions: int = 5


def kelly_position_size(
    win_probability: float,
    expected_gain: float,
    expected_loss: float,
    kelly_fraction: float = 0.25,
    max_position_pct: float = 15.0,
) -> float:
    """Compute a fractional Kelly position size as a percentage.

    Full Kelly formula:
        b  = expected_gain / expected_loss
        f* = (p * b - (1 - p)) / b

    Fractional Kelly = kelly_fraction * max(0, f*) * 100, capped at
    max_position_pct.

    Args:
        win_probability: Estimated probability of a winning outcome (0 < p < 1).
        expected_gain:   Average return on winning positions (e.g. 0.20 for 20%).
        expected_loss:   Average absolute loss on losing positions (e.g. 0.10 for 10%).
        kelly_fraction:  Fraction of full Kelly to apply. Default 0.25 (quarter-Kelly).
        max_position_pct: Hard cap on the returned size in percent. Default 15.0.

    Returns:
        Position size as a percentage (e.g. 10.0 for 10%).
        Returns 0.0 when the Kelly criterion yields zero or negative edge.
    """
    b = expected_gain / expected_loss
    q = 1.0 - win_probability
    full_kelly = (win_probability * b - q) / b

    if full_kelly <= 0.0:
        return 0.0

    size_pct = kelly_fraction * full_kelly * 100.0
    return min(size_pct, max_position_pct)
