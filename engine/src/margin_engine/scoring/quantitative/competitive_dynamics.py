"""Competitive Dynamics Proxies — moat leading indicators.

1. Gross Margin Stability: StdDev of gross margins over 3-5 years.
   Lower = more durable pricing power. Inverted for scoring (lower is better).

2. Relative Revenue Growth: Company CAGR vs sector median CAGR.
   Positive = gaining market share.
"""

from __future__ import annotations

import statistics

from margin_engine.models.financial import FinancialHistory
from margin_engine.models.scoring import FactorScore


def gross_margin_stability(history: FinancialHistory) -> FactorScore:
    """Compute standard deviation of gross margins across periods.

    Lower std dev = more stable margins = stronger pricing power.
    This is an INVERTED factor (lower raw_value is better).
    """
    if len(history.periods) < 2:
        return FactorScore(
            name="gross_margin_stability",
            raw_value=1.0,
            percentile_rank=0.0,
            detail="Need 2+ periods",
        )

    margins = [p.current_income.gross_margin for p in history.periods]
    std = statistics.pstdev(margins)

    return FactorScore(
        name="gross_margin_stability",
        raw_value=std,
        percentile_rank=0.0,
        detail=f"stdev={std:.4f} over {len(margins)} periods, margins={[round(m, 4) for m in margins]}",
    )


def relative_revenue_growth(
    company_cagr: float,
    sector_median_cagr: float,
) -> FactorScore:
    """Compute company revenue CAGR minus sector median CAGR.

    Positive = gaining share. Negative = losing share.
    """
    spread = company_cagr - sector_median_cagr

    return FactorScore(
        name="relative_revenue_growth",
        raw_value=spread,
        percentile_rank=0.0,
        detail=f"company={company_cagr:.4f} - sector={sector_median_cagr:.4f} = {spread:.4f}",
    )
