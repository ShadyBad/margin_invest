"""ROIC Stability factor — rewards consistent capital efficiency.

Score = median_ROIC * (1 - CV), where CV = stdev / mean of ROIC series,
clamped to [0, 1].

A company with high *and* stable ROIC scores much better than one with
high but volatile ROIC (which suggests cyclicality or eroding moats).

Per-period ROIC:
    NOPAT = EBIT * (1 - effective_tax_rate)
    Invested Capital = Total Equity + Total Debt - Cash
    ROIC = NOPAT / Invested Capital
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import FinancialHistory
from margin_engine.models.scoring import FactorScore


def _period_roic(period) -> float | None:
    """Compute ROIC for a single period. Returns None if IC <= 0."""
    ci = period.current_income
    cb = period.current_balance

    ebit = float(ci.ebit)
    tax_rate = ci.effective_tax_rate
    nopat = ebit * (1.0 - tax_rate)

    cash = float(cb.cash_and_equivalents or Decimal("0"))
    total_equity = float(cb.total_equity)
    total_debt = float(cb.total_debt)
    invested_capital = total_equity + total_debt - cash

    if invested_capital <= 0:
        return None

    return nopat / invested_capital


def roic_stability(history: FinancialHistory) -> FactorScore:
    """Compute ROIC stability factor from multi-year financial history.

    Returns a FactorScore with percentile_rank=0.0 (placeholder).
    """
    roics: list[float] = []
    for period in history.periods:
        r = _period_roic(period)
        if r is not None:
            roics.append(r)

    if not roics:
        return FactorScore(
            name="roic_stability",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="No valid periods (all had non-positive invested capital)",
        )

    median_roic = statistics.median(roics)

    if len(roics) == 1:
        cv = 0.0
    else:
        mean_roic = statistics.mean(roics)
        if mean_roic == 0.0:
            cv = 1.0
        else:
            stdev_roic = statistics.stdev(roics)
            cv = min(max(abs(stdev_roic / mean_roic), 0.0), 1.0)

    raw_value = median_roic * (1.0 - cv)

    detail = (
        f"median_ROIC={median_roic:.4f}, CV={cv:.4f}, "
        f"periods_used={len(roics)}/{len(history.periods)}"
    )

    return FactorScore(
        name="roic_stability",
        raw_value=raw_value,
        percentile_rank=0.0,
        detail=detail,
    )
