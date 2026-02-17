"""Track A (Compounder) composite scorer.

Assembles Quality (50%) + Value (30%) + Capital Allocation (20%) using
weighted sub-factors. Growth stage adjusts pillar weights.
"""

from __future__ import annotations

from margin_engine.models.scoring import (
    CompositeScore,
    FactorBreakdown,
    FactorScore,
    FilterResult,
    GrowthStage,
)

# Default pillar weights (Steady Growth)
_DEFAULT_QUALITY_WEIGHT = 0.50
_DEFAULT_VALUE_WEIGHT = 0.30
_DEFAULT_CAP_ALLOC_WEIGHT = 0.20

# Growth stage -> (quality, value, capital_allocation)
_STAGE_WEIGHTS: dict[GrowthStage, tuple[float, float, float]] = {
    GrowthStage.HIGH_GROWTH: (0.55, 0.25, 0.20),
    GrowthStage.STEADY_GROWTH: (0.50, 0.30, 0.20),
    GrowthStage.MATURE: (0.40, 0.35, 0.25),
    GrowthStage.CYCLICAL: (0.45, 0.30, 0.25),
    GrowthStage.TURNAROUND: (0.40, 0.35, 0.25),
}


def compute_compounder_score(
    ticker: str,
    quality_scores: list[FactorScore],
    value_scores: list[FactorScore],
    capital_allocation_scores: list[FactorScore],
    filters_passed: list[FilterResult],
    growth_stage: GrowthStage | None = None,
    data_coverage: float = 1.0,
) -> CompositeScore:
    """Compute Track A (Compounder) composite score.

    Pillars:
        - Quality: ROIC stability, incremental ROIC, reinvestment, GP, accrual
        - Value: DCF MoS, owner earnings yield, acquirer's multiple, runway
        - Capital Allocation: organic reinvestment, buyback, insider, debt discipline

    Args:
        ticker: Stock symbol.
        quality_scores: Pre-ranked quality sub-factor scores with weights.
        value_scores: Pre-ranked value sub-factor scores with weights.
        capital_allocation_scores: Pre-ranked cap alloc sub-factor scores with weights.
        filters_passed: Filter results from elimination phase.
        growth_stage: Adjusts pillar weights. None defaults to Steady Growth.
        data_coverage: Fraction of data available (0-1).

    Returns:
        CompositeScore with winning_track="compounder".
    """
    # 1. Determine pillar weights
    if growth_stage is not None and growth_stage in _STAGE_WEIGHTS:
        q_weight, v_weight, ca_weight = _STAGE_WEIGHTS[growth_stage]
    else:
        q_weight = _DEFAULT_QUALITY_WEIGHT
        v_weight = _DEFAULT_VALUE_WEIGHT
        ca_weight = _DEFAULT_CAP_ALLOC_WEIGHT

    # 2. Build FactorBreakdowns
    quality = FactorBreakdown(
        factor_name="quality",
        weight=q_weight,
        sub_scores=quality_scores,
    )
    value = FactorBreakdown(
        factor_name="value",
        weight=v_weight,
        sub_scores=value_scores,
    )
    capital_allocation = FactorBreakdown(
        factor_name="capital_allocation",
        weight=ca_weight,
        sub_scores=capital_allocation_scores,
    )
    momentum = FactorBreakdown(
        factor_name="momentum",
        weight=0.0,
        sub_scores=[],
    )

    # 3. Compute weighted composite percentile
    composite_percentile = (
        quality.average_percentile * q_weight
        + value.average_percentile * v_weight
        + capital_allocation.average_percentile * ca_weight
    )

    return CompositeScore(
        ticker=ticker,
        composite_percentile=composite_percentile,
        composite_raw_score=composite_percentile,
        quality=quality,
        value=value,
        momentum=momentum,
        capital_allocation=capital_allocation,
        filters_passed=filters_passed,
        data_coverage=data_coverage,
        growth_stage=growth_stage,
        winning_track="compounder",
    )
