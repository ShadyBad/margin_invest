"""ROIC-WACC Spread quality factor.

Return on Invested Capital (ROIC) measures how efficiently a company
uses its capital to generate profits. When compared against the Weighted
Average Cost of Capital (WACC), the spread indicates whether the company
is creating or destroying shareholder value.

Formulas:
    NOPAT = EBIT * (1 - Effective Tax Rate)
    Invested Capital = Total Equity + Total Debt - Cash
    ROIC = NOPAT / Invested Capital
    Spread = ROIC - WACC
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore


def compute_roic(period: FinancialPeriod) -> float:
    """Compute Return on Invested Capital from financial data.

    Returns 0.0 if invested capital is zero or negative.
    """
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
        return 0.0

    return nopat / invested_capital


def roic_wacc_spread(
    period: FinancialPeriod, wacc: float | None = None
) -> FactorScore:
    """Compute ROIC-WACC spread quality factor.

    If wacc is provided, raw_value = ROIC - WACC (the spread).
    If wacc is None, raw_value = ROIC (just return raw ROIC).

    Returns a FactorScore with percentile_rank=0.0 (placeholder).
    """
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
        spread = 0.0 if wacc is None else 0.0
        detail = (
            f"NOPAT={nopat:,.2f}, IC={invested_capital:,.2f} "
            f"(non-positive), ROIC=N/A"
        )
        if wacc is not None:
            detail += f", WACC={wacc:.4f}, Spread=N/A"
        return FactorScore(
            name="roic_wacc_spread",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=detail,
        )

    roic = nopat / invested_capital

    if wacc is not None:
        spread = roic - wacc
    else:
        spread = roic

    detail = (
        f"NOPAT={nopat:,.2f}, IC={invested_capital:,.2f}, "
        f"ROIC={roic:.4f}"
    )
    if wacc is not None:
        detail += f", WACC={wacc:.4f}, Spread={spread:.4f}"

    return FactorScore(
        name="roic_wacc_spread",
        raw_value=spread,
        percentile_rank=0.0,
        detail=detail,
    )
