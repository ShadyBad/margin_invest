"""Market Regime modifier -- CAPE-based threshold adjustment.

Detects current market regime and returns adjustment values for conviction thresholds.
Not prediction -- detection of current conditions.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class MarketRegime(StrEnum):
    CHEAP = "cheap"
    NORMAL = "normal"
    EXPENSIVE = "expensive"
    EUPHORIA = "euphoria"


class RegimeAdjustments(BaseModel):
    """Adjustments to apply to conviction thresholds based on market regime."""

    regime: MarketRegime
    track_a_growth_gap_adjustment: float  # Added to growth_gap threshold (positive = tighter)
    track_b_asymmetry_adjustment: float  # Added to asymmetry threshold (negative = relaxed)
    track_b_catalyst_percentile_override: float | None  # Override catalyst gate if set


def detect_regime(shiller_cape: float) -> MarketRegime:
    """Detect market regime from Shiller CAPE ratio."""
    if shiller_cape < 15.0:
        return MarketRegime.CHEAP
    if shiller_cape <= 25.0:
        return MarketRegime.NORMAL
    if shiller_cape <= 35.0:
        return MarketRegime.EXPENSIVE
    return MarketRegime.EUPHORIA


def regime_adjustments(regime: MarketRegime) -> RegimeAdjustments:
    """Return threshold adjustments for a given market regime."""
    if regime == MarketRegime.CHEAP:
        return RegimeAdjustments(
            regime=regime,
            track_a_growth_gap_adjustment=-0.02,
            track_b_asymmetry_adjustment=-1.0,
            track_b_catalyst_percentile_override=None,
        )
    if regime == MarketRegime.NORMAL:
        return RegimeAdjustments(
            regime=regime,
            track_a_growth_gap_adjustment=0.0,
            track_b_asymmetry_adjustment=0.0,
            track_b_catalyst_percentile_override=None,
        )
    if regime == MarketRegime.EXPENSIVE:
        return RegimeAdjustments(
            regime=regime,
            track_a_growth_gap_adjustment=0.02,
            track_b_asymmetry_adjustment=0.0,
            track_b_catalyst_percentile_override=None,
        )
    # EUPHORIA
    return RegimeAdjustments(
        regime=regime,
        track_a_growth_gap_adjustment=0.05,
        track_b_asymmetry_adjustment=0.0,
        track_b_catalyst_percentile_override=90.0,
    )
