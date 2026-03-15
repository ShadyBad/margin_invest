"""Composite scorer — combines quality, value, and momentum into a final ConvictionScore.

Takes pre-computed sub-factor percentile ranks, applies growth-stage-adjusted
weights, and returns a fully populated CompositeScore.
"""

from __future__ import annotations

from margin_engine.models.scoring import (
    CompositeScore,
    FactorBreakdown,
    FactorScore,
    FilterResult,
    GrowthStage,
    ScoringConfig,
)
from margin_engine.scoring.quantitative.price_targets import PriceTargets


def compute_composite_score(
    ticker: str,
    quality_scores: list[FactorScore],
    value_scores: list[FactorScore],
    momentum_scores: list[FactorScore],
    filters_passed: list[FilterResult],
    growth_stage: GrowthStage | None = None,
    config: ScoringConfig | None = None,
    price_targets: PriceTargets | None = None,
    growth_scores: list[FactorScore] | None = None,
) -> CompositeScore:
    """Compute a weighted composite score from quality, value, momentum, and growth sub-factors.

    Args:
        ticker: Stock symbol.
        quality_scores: FactorScore list for quality sub-factors (percentile_rank filled).
        value_scores: FactorScore list for value sub-factors.
        momentum_scores: FactorScore list for momentum sub-factors.
        filters_passed: FilterResult list from elimination phase.
        growth_stage: If provided, adjusts factor weights via ScoringConfig.
        config: Optional ScoringConfig override; defaults to ScoringConfig().
        price_targets: Optional PriceTargets to attach to the composite.
        growth_scores: Optional FactorScore list for growth sub-factors.

    Returns:
        A fully populated CompositeScore.
    """
    if config is None:
        config = ScoringConfig()

    # 1. Determine weights from growth stage (or default)
    if growth_stage is not None:
        q_weight, v_weight, m_weight, _g_weight = config.weights_for_stage(growth_stage)
    else:
        q_weight = config.quality_weight
        v_weight = config.value_weight
        m_weight = config.momentum_weight

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
    momentum = FactorBreakdown(
        factor_name="momentum",
        weight=m_weight,
        sub_scores=momentum_scores,
    )

    # Build growth breakdown (informational; not yet part of composite weighting)
    growth_breakdown: FactorBreakdown | None = None
    if growth_scores:
        growth_breakdown = FactorBreakdown(
            factor_name="growth",
            weight=0.0,
            sub_scores=growth_scores,
        )

    # 3. Compute weighted composite percentile
    composite_percentile = (
        quality.average_percentile * q_weight
        + value.average_percentile * v_weight
        + momentum.average_percentile * m_weight
    )

    # 4. Compute data coverage
    all_scores = [*quality_scores, *value_scores, *momentum_scores]
    total_scores = len(all_scores)
    if total_scores == 0:
        data_coverage = 1.0
    else:
        scores_with_data = sum(1 for s in all_scores if s.percentile_rank > 0.0)
        data_coverage = scores_with_data / total_scores

    # 5. Attach price targets if provided
    price_kwargs: dict = {}
    if price_targets:
        price_kwargs = {
            "margin_invest_value": price_targets.margin_invest_value,
            "buy_price": price_targets.buy_price,
            "sell_price": price_targets.sell_price,
            "actual_price": price_targets.actual_price,
            "price_upside": price_targets.price_upside,
            "margin_of_safety": price_targets.margin_of_safety,
            "valuation_methods": price_targets.valuation_methods,
            "price_target_invalid_reason": price_targets.invalid_reason,
        }

    # 6. Assemble and return CompositeScore
    return CompositeScore(
        ticker=ticker,
        composite_percentile=composite_percentile,
        composite_raw_score=composite_percentile,
        quality=quality,
        value=value,
        momentum=momentum,
        growth=growth_breakdown,
        filters_passed=filters_passed,
        data_coverage=data_coverage,
        growth_stage=growth_stage,
        **price_kwargs,
    )
