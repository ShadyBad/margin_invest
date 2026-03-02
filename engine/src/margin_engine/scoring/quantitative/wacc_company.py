"""Company-specific WACC computation (CAPM-based).

Replaces static sector WACC lookup with a per-company estimate:

    WACC = (E/V x Ke) + (D/V x Kd x (1 - t))

Where:
    Ke = Rf + beta x MRP  (Cost of Equity via CAPM)
    Kd = interest_expense / total_debt  (Cost of Debt, with floor/cap)
    E  = market_cap, D = total_debt, V = E + D
    t  = effective_tax_rate
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import AssetProfile, FinancialPeriod

_RISK_FREE_RATE = 0.0425
_MARKET_RISK_PREMIUM = 0.055
_MIN_COST_OF_DEBT = 0.01
_MAX_COST_OF_DEBT = 0.15
_WACC_FLOOR = 0.02


def compute_company_wacc(
    period: FinancialPeriod,
    profile: AssetProfile,
    beta: float | None = None,
    sector_fallback: float | None = None,
    risk_free_rate: float = _RISK_FREE_RATE,
    market_risk_premium: float = _MARKET_RISK_PREMIUM,
) -> float:
    """Compute company-specific WACC using CAPM.

    Falls back to *sector_fallback* when *beta* is ``None``.
    Returns a default of ``0.09`` if neither beta nor fallback is available.
    """
    if beta is None:
        return sector_fallback if sector_fallback is not None else 0.09

    # Cost of equity (CAPM)
    cost_of_equity = risk_free_rate + beta * market_risk_premium

    # Cost of debt
    total_debt = float(period.current_balance.total_debt)
    interest = float(period.current_income.interest_expense or Decimal("0"))

    if total_debt > 0 and interest > 0:
        cost_of_debt = max(_MIN_COST_OF_DEBT, min(interest / total_debt, _MAX_COST_OF_DEBT))
    else:
        cost_of_debt = risk_free_rate + 0.02  # risk-free + 200 bps spread

    # Tax rate
    tax_rate = period.current_income.effective_tax_rate

    # Capital structure
    market_cap = float(profile.market_cap)
    if market_cap <= 0:
        return sector_fallback if sector_fallback is not None else 0.09

    total_value = market_cap + total_debt
    equity_weight = market_cap / total_value
    debt_weight = total_debt / total_value

    wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt * (1 - tax_rate))
    return max(wacc, _WACC_FLOOR)
