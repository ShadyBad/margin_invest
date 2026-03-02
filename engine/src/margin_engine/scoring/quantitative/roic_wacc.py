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

from margin_engine.models.financial import BalanceSheet, FinancialPeriod
from margin_engine.models.scoring import FactorScore


def _invested_capital(balance: BalanceSheet) -> float:
    """Compute Invested Capital from a single balance sheet.

    IC = Total Equity + Total Debt - Cash
    """
    cash = float(balance.cash_and_equivalents or Decimal("0"))
    total_equity = float(balance.total_equity)
    total_debt = float(balance.total_debt)
    return total_equity + total_debt - cash


def compute_roic(period: FinancialPeriod) -> float:
    """Compute Return on Invested Capital from financial data.

    Uses average of beginning and ending Invested Capital when prior_balance
    is available (institutional standard: Bloomberg, FactSet, S&P). Falls back
    to end-of-period IC when prior balance is unavailable.

    Returns 0.0 if invested capital is zero or negative.
    """
    ci = period.current_income

    ebit = float(ci.ebit)
    tax_rate = ci.effective_tax_rate
    nopat = ebit * (1.0 - tax_rate)

    current_ic = _invested_capital(period.current_balance)

    if period.prior_balance is not None:
        prior_ic = _invested_capital(period.prior_balance)
        if current_ic > 0 and prior_ic > 0:
            invested_capital = (current_ic + prior_ic) / 2.0
        elif current_ic > 0:
            invested_capital = current_ic
        else:
            return 0.0
    else:
        invested_capital = current_ic

    if invested_capital <= 0:
        return 0.0

    return nopat / invested_capital


def roic_wacc_spread(period: FinancialPeriod, wacc: float | None = None) -> FactorScore:
    """Compute ROIC-WACC spread quality factor.

    If wacc is provided, raw_value = ROIC - WACC (the spread).
    If wacc is None, raw_value = ROIC (just return raw ROIC).

    Uses compute_roic() for the ROIC calculation (average IC when available).
    Returns a FactorScore with percentile_rank=0.0 (placeholder).
    """
    ci = period.current_income

    ebit = float(ci.ebit)
    tax_rate = ci.effective_tax_rate
    nopat = ebit * (1.0 - tax_rate)

    current_ic = _invested_capital(period.current_balance)
    prior_ic = _invested_capital(period.prior_balance) if period.prior_balance is not None else None

    # Use average IC for detail string
    if current_ic > 0 and prior_ic is not None and prior_ic > 0:
        avg_ic = (current_ic + prior_ic) / 2.0
    else:
        avg_ic = current_ic

    roic = compute_roic(period)

    if avg_ic <= 0:
        detail = f"NOPAT={nopat:,.2f}, IC={current_ic:,.2f} (non-positive), ROIC=N/A"
        if wacc is not None:
            detail += f", WACC={wacc:.4f}, Spread=N/A"
        return FactorScore(
            name="roic_wacc_spread",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=detail,
        )

    if wacc is not None:
        spread = roic - wacc
    else:
        spread = roic

    detail = f"NOPAT={nopat:,.2f}, IC={avg_ic:,.2f}"
    if prior_ic is not None and prior_ic > 0:
        detail += f" (avg of {current_ic:,.2f} and {prior_ic:,.2f})"
    detail += f", ROIC={roic:.4f}"
    if wacc is not None:
        detail += f", WACC={wacc:.4f}, Spread={spread:.4f}"

    return FactorScore(
        name="roic_wacc_spread",
        raw_value=spread,
        percentile_rank=0.0,
        detail=detail,
    )
