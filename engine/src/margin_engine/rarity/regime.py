"""Rarity-specific regime classification and alignment scoring.

Standalone regime (independent of engine/src/margin_engine/regime/).
Purpose-built for rarity historical comparison with 4 simple classes.
"""

from __future__ import annotations

from margin_engine.rarity.models import RarityRegime

_REGIME_ALIGNMENT: dict[RarityRegime, dict[str, float]] = {
    RarityRegime.EXPANSION: {"compounder": 70.0, "mispricing": 40.0, "efficient_growth": 80.0},
    RarityRegime.LATE_CYCLE: {"compounder": 60.0, "mispricing": 55.0, "efficient_growth": 50.0},
    RarityRegime.CONTRACTION: {"compounder": 35.0, "mispricing": 80.0, "efficient_growth": 30.0},
    RarityRegime.CRISIS: {"compounder": 25.0, "mispricing": 90.0, "efficient_growth": 20.0},
}


def classify_regime(vix: float, yield_curve_slope: float, credit_spread: float) -> RarityRegime:
    """Classify current macro environment. Precedence order (first match wins)."""
    if vix > 35 and credit_spread > 2.5:
        return RarityRegime.CRISIS
    if yield_curve_slope < 0 or vix > 25:
        return RarityRegime.CONTRACTION
    if -0.2 <= yield_curve_slope <= 0.5 and 15 <= vix <= 25:
        return RarityRegime.LATE_CYCLE
    return RarityRegime.EXPANSION


def compute_regime_alignment(regime: RarityRegime, winning_track: str) -> float:
    """Score 0-100: how well the current regime favors this stock's track."""
    alignment_map = _REGIME_ALIGNMENT.get(regime, {})
    return alignment_map.get(winning_track, 50.0)
