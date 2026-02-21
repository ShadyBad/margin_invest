"""V4 Style x Stage weight matrix.

Returns (quality, value, momentum, growth) weights for each
(InvestmentStyle, GrowthStage) combination.

Properties:
- No cell exceeds 0.45
- Momentum varies: VALUE=0.20, BLEND=0.25, GROWTH=0.30
- Quality always >= 0.20
- All rows sum to 1.0
"""

from __future__ import annotations

from margin_engine.models.scoring import GrowthStage, InvestmentStyle

# (quality, value, momentum, growth)
_WEIGHT_MATRIX: dict[tuple[InvestmentStyle, GrowthStage], tuple[float, float, float, float]] = {
    # Value: momentum 0.20 (was 0.25), value gets +0.05
    (InvestmentStyle.VALUE, GrowthStage.MATURE): (0.25, 0.40, 0.20, 0.15),
    (InvestmentStyle.VALUE, GrowthStage.STEADY_GROWTH): (0.25, 0.35, 0.20, 0.20),
    (InvestmentStyle.VALUE, GrowthStage.CYCLICAL): (0.25, 0.35, 0.20, 0.20),
    (InvestmentStyle.VALUE, GrowthStage.HIGH_GROWTH): (0.25, 0.30, 0.20, 0.25),
    (InvestmentStyle.VALUE, GrowthStage.TURNAROUND): (0.30, 0.30, 0.20, 0.20),
    # Blend: momentum 0.25 (unchanged)
    (InvestmentStyle.BLEND, GrowthStage.MATURE): (0.30, 0.25, 0.25, 0.20),
    (InvestmentStyle.BLEND, GrowthStage.STEADY_GROWTH): (0.30, 0.20, 0.25, 0.25),
    (InvestmentStyle.BLEND, GrowthStage.CYCLICAL): (0.30, 0.20, 0.25, 0.25),
    (InvestmentStyle.BLEND, GrowthStage.HIGH_GROWTH): (0.25, 0.15, 0.25, 0.35),
    (InvestmentStyle.BLEND, GrowthStage.TURNAROUND): (0.30, 0.25, 0.25, 0.20),
    # Growth: momentum 0.30 (was 0.25), value gets -0.05
    (InvestmentStyle.GROWTH, GrowthStage.MATURE): (0.25, 0.15, 0.30, 0.30),
    (InvestmentStyle.GROWTH, GrowthStage.STEADY_GROWTH): (0.25, 0.10, 0.30, 0.35),
    (InvestmentStyle.GROWTH, GrowthStage.CYCLICAL): (0.25, 0.10, 0.30, 0.35),
    (InvestmentStyle.GROWTH, GrowthStage.HIGH_GROWTH): (0.20, 0.05, 0.30, 0.45),
    (InvestmentStyle.GROWTH, GrowthStage.TURNAROUND): (0.30, 0.20, 0.30, 0.20),
}


def weights_for_style_stage(
    style: InvestmentStyle,
    stage: GrowthStage,
) -> tuple[float, float, float, float]:
    """Return (quality, value, momentum, growth) weights.
    Falls back to Blend x Steady Growth if combination not found."""
    return _WEIGHT_MATRIX.get(
        (style, stage),
        (0.30, 0.20, 0.25, 0.25),
    )
