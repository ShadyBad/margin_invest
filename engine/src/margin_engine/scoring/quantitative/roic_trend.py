"""ROIC Trend factor — OLS slope of ROIC across financial periods.

Captures the direction of profitability over time. A positive slope
indicates improving capital efficiency; a negative slope signals
deterioration.

Formulas:
    NOPAT = EBIT * (1 - Effective Tax Rate)
    Invested Capital (IC) = Total Equity + Total Debt - Cash
    ROIC = NOPAT / IC
    Trend = OLS slope of ROIC series vs period index
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import FactorScore


def _compute_roic(period: FinancialPeriod) -> float | None:
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


def _ols_slope(ys: list[float]) -> float:
    """Compute OLS slope of ys against indices [0, 1, 2, ...].

    Uses the closed-form formula:
        slope = (n * sum(x*y) - sum(x) * sum(y)) / (n * sum(x^2) - sum(x)^2)
    """
    n = len(ys)
    if n < 2:
        return 0.0

    xs = list(range(n))
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)

    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return 0.0

    return (n * sum_xy - sum_x * sum_y) / denominator


def roic_trend(history: FinancialHistory) -> FactorScore:
    """Compute ROIC trend (OLS slope) across financial periods.

    Args:
        history: Multi-period financial data for a single ticker.

    Returns:
        FactorScore with raw_value = OLS slope of ROIC series.
        Positive slope means improving profitability.
        percentile_rank is set to 0.0 (placeholder for cross-sector ranking).
    """
    roic_values: list[float] = []
    for period in history.periods:
        roic = _compute_roic(period)
        if roic is not None:
            roic_values.append(roic)

    if len(roic_values) < 2:
        return FactorScore(
            name="roic_trend",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"Insufficient data: {len(roic_values)} valid ROIC point(s)",
        )

    slope = _ols_slope(roic_values)

    roic_strs = [f"{r:.4f}" for r in roic_values]
    detail = (
        f"ROIC trend slope={slope:.6f} over {len(roic_values)} periods, "
        f"ROIC values=[{', '.join(roic_strs)}]"
    )

    return FactorScore(
        name="roic_trend",
        raw_value=slope,
        percentile_rank=0.0,
        detail=detail,
    )
