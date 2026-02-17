"""Opportunity Type classifier — Compounder, Mispricing, Both, or Neither.

Compounder requires:
    - 5yr median ROIC > 15%
    - Reinvestment Rate > 30%
    - ROIC CV < 0.30

Mispricing requires:
    - Price / Intrinsic Value < 0.60
    - Quality floor: 5yr median ROIC > 8% OR improving ROIC trajectory
    - At least one active catalyst
"""

from __future__ import annotations

from margin_engine.models.scoring import OpportunityType

# Compounder thresholds
_COMPOUNDER_ROIC_MIN = 0.15
_COMPOUNDER_RR_MIN = 0.30
_COMPOUNDER_CV_MAX = 0.30

# Mispricing thresholds
_MISPRICING_PRICE_RATIO_MAX = 0.60
_MISPRICING_ROIC_FLOOR = 0.08


def classify_opportunity_type(
    roic_5yr_median: float,
    roic_cv: float,
    reinvestment_rate: float,
    price_to_intrinsic_ratio: float,
    has_catalyst: bool,
    roic_improving: bool,
) -> OpportunityType:
    """Classify a stock's opportunity type based on quantitative criteria."""
    is_compounder = (
        roic_5yr_median > _COMPOUNDER_ROIC_MIN
        and reinvestment_rate > _COMPOUNDER_RR_MIN
        and roic_cv < _COMPOUNDER_CV_MAX
    )

    quality_floor_met = roic_5yr_median > _MISPRICING_ROIC_FLOOR or roic_improving

    is_mispricing = (
        price_to_intrinsic_ratio < _MISPRICING_PRICE_RATIO_MAX
        and quality_floor_met
        and has_catalyst
    )

    if is_compounder and is_mispricing:
        return OpportunityType.BOTH
    if is_compounder:
        return OpportunityType.COMPOUNDER
    if is_mispricing:
        return OpportunityType.MISPRICING
    return OpportunityType.NEITHER
