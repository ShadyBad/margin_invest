"""Reinvestment Engine factor — compounding power of capital allocation.

Score = ROIC * Reinvestment Rate

Where:
    ROIC = NOPAT / Invested Capital
    Reinvestment Rate = Growth CapEx / NOPAT
    Growth CapEx = |CapEx| - Depreciation  (if positive, else 0)

This captures the *speed* at which a company compounds intrinsic value.
A 30% ROIC with 60% reinvestment rate = 18% organic value growth —
far better than a 30% ROIC with 10% reinvestment (mature, low growth).
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore


def reinvestment_engine(period: FinancialPeriod) -> FactorScore:
    """Compute reinvestment engine factor from a single financial period.

    Returns a FactorScore with percentile_rank=0.0 (placeholder).
    """
    ci = period.current_income
    cb = period.current_balance
    ccf = period.current_cash_flow

    # NOPAT
    ebit = float(ci.ebit)
    tax_rate = ci.effective_tax_rate
    nopat = ebit * (1.0 - tax_rate)

    # Invested Capital
    cash = float(cb.cash_and_equivalents or Decimal("0"))
    total_equity = float(cb.total_equity)
    total_debt = float(cb.total_debt)
    invested_capital = total_equity + total_debt - cash

    if invested_capital <= 0 or nopat <= 0:
        return FactorScore(
            name="reinvestment_engine",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(f"NOPAT={nopat:,.2f}, IC={invested_capital:,.2f} (non-positive NOPAT or IC)"),
        )

    roic = nopat / invested_capital

    # Growth CapEx = |CapEx| - Depreciation
    capex_abs = abs(float(ccf.capital_expenditures))
    depreciation = float(ci.depreciation or Decimal("0"))
    growth_capex = capex_abs - depreciation

    if growth_capex <= 0:
        return FactorScore(
            name="reinvestment_engine",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"ROIC={roic:.4f}, |CapEx|={capex_abs:,.2f}, "
                f"Depr={depreciation:,.2f}, GrowthCapEx<=0"
            ),
        )

    reinvestment_rate = growth_capex / nopat
    raw_value = roic * reinvestment_rate

    detail = (
        f"ROIC={roic:.4f}, GrowthCapEx={growth_capex:,.2f}, "
        f"ReinvRate={reinvestment_rate:.4f}, Score={raw_value:.4f}"
    )

    return FactorScore(
        name="reinvestment_engine",
        raw_value=raw_value,
        percentile_rank=0.0,
        detail=detail,
    )
