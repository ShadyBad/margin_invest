"""Track B (Mispricing) composite scorer.

Assembles Value (45%) + Quality Floor (25%) + Catalyst (30%).
Weights are FIXED and do not vary by growth stage.
"""

from __future__ import annotations

from margin_engine.models.scoring import (
    CompositeScore,
    FactorBreakdown,
    FactorScore,
    FilterResult,
)

# Fixed pillar weights — Track B does not vary by growth stage
_VALUE_WEIGHT = 0.45
_QUALITY_FLOOR_WEIGHT = 0.25
_CATALYST_WEIGHT = 0.30


def compute_mispricing_score(
    ticker: str,
    value_scores: list[FactorScore],
    quality_floor_scores: list[FactorScore],
    catalyst_scores: list[FactorScore],
    filters_passed: list[FilterResult],
    data_coverage: float = 1.0,
) -> CompositeScore:
    """Compute Track B (Mispricing) composite score.

    Pillars:
        - Value (45%): DCF MoS, owner earnings yield, acquirer's multiple, asymmetry
        - Quality Floor (25%): ROIC trajectory, gross profitability, earnings quality
        - Catalyst (30%): Insider cluster, institutional accumulation, contrarian signal

    Args:
        ticker: Stock symbol.
        value_scores: Pre-ranked value sub-factor scores with weights.
        quality_floor_scores: Pre-ranked quality floor sub-factor scores with weights.
        catalyst_scores: Pre-ranked catalyst sub-factor scores with weights.
        filters_passed: Filter results from elimination phase.
        data_coverage: Fraction of data available (0-1).

    Returns:
        CompositeScore with winning_track="mispricing".
    """
    # Build FactorBreakdowns
    value = FactorBreakdown(
        factor_name="value",
        weight=_VALUE_WEIGHT,
        sub_scores=value_scores,
    )
    quality_floor = FactorBreakdown(
        factor_name="quality_floor",
        weight=_QUALITY_FLOOR_WEIGHT,
        sub_scores=quality_floor_scores,
    )
    catalyst = FactorBreakdown(
        factor_name="catalyst",
        weight=_CATALYST_WEIGHT,
        sub_scores=catalyst_scores,
    )
    momentum = FactorBreakdown(
        factor_name="momentum",
        weight=0.0,
        sub_scores=[],
    )

    # Compute weighted composite percentile
    composite_percentile = (
        value.average_percentile * _VALUE_WEIGHT
        + quality_floor.average_percentile * _QUALITY_FLOOR_WEIGHT
        + catalyst.average_percentile * _CATALYST_WEIGHT
    )

    return CompositeScore(
        ticker=ticker,
        composite_percentile=composite_percentile,
        composite_raw_score=composite_percentile,
        quality=quality_floor,  # quality field stores quality_floor
        value=value,
        momentum=momentum,
        catalyst=catalyst,
        filters_passed=filters_passed,
        data_coverage=data_coverage,
        winning_track="mispricing",
    )
