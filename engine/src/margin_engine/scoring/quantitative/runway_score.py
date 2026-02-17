"""Runway Score factor — revenue penetration of sub-industry TAM.

raw_value = company_revenue / sub_industry_revenue  (penetration ratio)

Lower penetration = more runway for growth. This value will be
*inverted* at ranking time so that companies with more runway score
higher.

Edge cases:
    - None sub_industry_revenue → 0.5 (neutral assumption)
    - Zero sub_industry_revenue → 1.0 (fully saturated)
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.scoring import FactorScore


def runway_score(
    company_revenue: Decimal,
    sub_industry_revenue: Decimal | None,
) -> FactorScore:
    """Compute runway score (revenue penetration ratio).

    Returns a FactorScore with percentile_rank=0.0 (placeholder).
    """
    if sub_industry_revenue is None:
        return FactorScore(
            name="runway_score",
            raw_value=0.5,
            percentile_rank=0.0,
            detail="Sub-industry revenue unknown — neutral 0.5",
        )

    if sub_industry_revenue == Decimal("0"):
        return FactorScore(
            name="runway_score",
            raw_value=1.0,
            percentile_rank=0.0,
            detail=(
                f"company_rev={float(company_revenue):,.2f}, "
                f"industry_rev=0 (saturated)"
            ),
        )

    penetration = float(company_revenue / sub_industry_revenue)

    detail = (
        f"company_rev={float(company_revenue):,.2f}, "
        f"industry_rev={float(sub_industry_revenue):,.2f}, "
        f"penetration={penetration:.4f}"
    )

    return FactorScore(
        name="runway_score",
        raw_value=penetration,
        percentile_rank=0.0,
        detail=detail,
    )
