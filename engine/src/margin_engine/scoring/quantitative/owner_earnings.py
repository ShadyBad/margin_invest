"""Owner Earnings Yield factor — Buffett-adjusted free cash flow yield.

Owner Earnings = CFO - Maintenance CapEx
Maintenance CapEx = Depreciation * 1.1  (slight premium for inflation)
Yield = Owner Earnings / Enterprise Value
EV = Market Cap + Total Debt - Cash

Buffett's owner earnings concept strips out growth capex to reveal
the true cash generation power of existing operations. This is more
conservative than reported FCF (which includes growth capex) and more
accurate than earnings (which include non-cash accruals).
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import AssetProfile, FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import FactorScore
from margin_engine.scoring.quantitative.cyclical_normalizer import normalize_metric


def _compute_owner_earnings(period: FinancialPeriod) -> float:
    """Compute owner earnings for a single period."""
    cfo = float(period.current_cash_flow.operating_cash_flow)
    depreciation = float(period.current_income.depreciation or Decimal("0"))
    maintenance_capex = depreciation * 1.1
    return cfo - maintenance_capex


def owner_earnings_yield(
    period: FinancialPeriod,
    profile: AssetProfile,
    history: FinancialHistory | None = None,
) -> FactorScore:
    """Compute owner earnings yield from a financial period and asset profile.

    For cyclical sectors, uses 7-year median owner earnings when history
    is provided (via cyclical_normalizer). Non-cyclical sectors and calls
    without history use current-period values (backward compatible).

    Returns a FactorScore with percentile_rank=0.0 (placeholder).
    """
    ci = period.current_income
    cb = period.current_balance
    ccf = period.current_cash_flow

    # Owner Earnings (current period)
    cfo = float(ccf.operating_cash_flow)
    depreciation = float(ci.depreciation or Decimal("0"))
    maintenance_capex = depreciation * 1.1
    owner_earnings = cfo - maintenance_capex

    # Cyclical normalization: use 7-year median owner earnings
    norm_detail = ""
    if history is not None and profile.sector.is_cyclical:
        historical_oe = [_compute_owner_earnings(p) for p in history.periods]
        owner_earnings, norm_detail = normalize_metric(
            current_value=owner_earnings,
            historical_values=historical_oe,
            is_cyclical=True,
        )
        norm_detail = f", norm=[{norm_detail}]"

    if owner_earnings <= 0:
        return FactorScore(
            name="owner_earnings_yield",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"CFO={cfo:,.2f}, MaintCapEx={maintenance_capex:,.2f}, "
                f"OwnerEarnings={owner_earnings:,.2f} (negative){norm_detail}"
            ),
        )

    # Enterprise Value
    market_cap = float(profile.market_cap)
    total_debt = float(cb.total_debt)
    cash = float(cb.cash_and_equivalents or Decimal("0"))
    ev = market_cap + total_debt - cash

    if ev <= 0:
        return FactorScore(
            name="owner_earnings_yield",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(f"OwnerEarnings={owner_earnings:,.2f}, EV={ev:,.2f} (non-positive)"),
        )

    raw_value = owner_earnings / ev

    detail = (
        f"CFO={cfo:,.2f}, MaintCapEx={maintenance_capex:,.2f}, "
        f"OE={owner_earnings:,.2f}, EV={ev:,.2f}, Yield={raw_value:.4f}{norm_detail}"
    )

    return FactorScore(
        name="owner_earnings_yield",
        raw_value=raw_value,
        percentile_rank=0.0,
        detail=detail,
    )
