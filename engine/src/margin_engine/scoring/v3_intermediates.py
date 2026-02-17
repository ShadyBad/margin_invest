"""V3 intermediate value calculators — pure functions converting raw data to v3 metrics.

These bridge the gap between raw financial data and the v3 composite scoring
functions (v3_composite.py) which expect pre-computed metrics.
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, FinancialPeriod


def compute_owner_earnings_iv(
    owner_earnings_per_share: float,
    wacc: float,
    terminal_growth: float = 0.03,
) -> float:
    """Gordon growth model: OE * (1 + g) / (WACC - g).

    Returns 0.0 if inputs are invalid (negative OE, WACC <= growth).
    """
    if owner_earnings_per_share <= 0 or wacc <= terminal_growth:
        return 0.0
    return owner_earnings_per_share * (1.0 + terminal_growth) / (wacc - terminal_growth)


def _nopat_and_ic(period: FinancialPeriod) -> tuple[float, float]:
    """Return (NOPAT, Invested Capital) for a period."""
    ci = period.current_income
    cb = period.current_balance
    ebit = float(ci.ebit)
    tax_rate = ci.effective_tax_rate
    nopat = ebit * (1.0 - tax_rate)
    cash = float(cb.cash_and_equivalents or Decimal("0"))
    ic = float(cb.total_equity) + float(cb.total_debt) - cash
    return nopat, ic


def compute_compounding_power(history: FinancialHistory) -> float:
    """Compute compounding power = incremental_ROIC * reinvestment_rate * (1 - ROIC_CV).

    Returns 0.0 if insufficient data or any component is non-positive.
    """
    if len(history.periods) < 2:
        return 0.0

    # Incremental ROIC (earliest -> latest)
    nopat_e, ic_e = _nopat_and_ic(history.periods[0])
    nopat_l, ic_l = _nopat_and_ic(history.periods[-1])
    delta_ic = ic_l - ic_e
    if delta_ic <= 0:
        return 0.0
    inc_roic = (nopat_l - nopat_e) / delta_ic
    if inc_roic <= 0:
        return 0.0

    # Reinvestment rate from latest period: growth_capex / NOPAT
    latest = history.periods[-1]
    capex = abs(float(latest.current_cash_flow.capital_expenditures))
    depreciation = float(latest.current_income.depreciation or Decimal("0"))
    growth_capex = max(capex - depreciation, 0.0)
    if nopat_l <= 0:
        return 0.0
    reinvestment_rate = growth_capex / nopat_l
    if reinvestment_rate <= 0:
        return 0.0

    # ROIC CV (coefficient of variation across all periods)
    roics = []
    for p in history.periods:
        nopat, ic = _nopat_and_ic(p)
        if ic > 0:
            roics.append(nopat / ic)
    if len(roics) < 2:
        cv = 0.0
    else:
        mean_roic = statistics.mean(roics)
        if mean_roic == 0:
            return 0.0
        stdev_roic = statistics.pstdev(roics)
        cv = min(abs(stdev_roic / mean_roic), 1.0)

    return inc_roic * reinvestment_rate * (1.0 - cv)
