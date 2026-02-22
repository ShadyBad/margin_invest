"""Incremental ROIC factor — return on new capital deployed.

Formula:
    Incremental ROIC = (NOPAT_latest - NOPAT_earliest) / (IC_latest - IC_earliest)

This measures how efficiently a company deploys *marginal* capital.
A company earning 25% ROIC on existing capital but only 5% on new
investments is deteriorating — incremental ROIC catches that.

Uses first and last period from FinancialHistory.
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import FactorScore


def _nopat_and_ic(period: FinancialPeriod) -> tuple[float, float]:
    """Return (NOPAT, Invested Capital) for a period."""
    ci = period.current_income
    cb = period.current_balance

    ebit = float(ci.ebit)
    tax_rate = ci.effective_tax_rate
    nopat = ebit * (1.0 - tax_rate)

    cash = float(cb.cash_and_equivalents or Decimal("0"))
    total_equity = float(cb.total_equity)
    total_debt = float(cb.total_debt)
    invested_capital = total_equity + total_debt - cash

    return nopat, invested_capital


def incremental_roic(history: FinancialHistory) -> FactorScore:
    """Compute incremental ROIC from first and last financial periods.

    Returns a FactorScore with percentile_rank=0.0 (placeholder).
    """
    if len(history.periods) < 2:
        return FactorScore(
            name="incremental_roic",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Single period — cannot compute incremental ROIC",
        )

    earliest = history.periods[0]
    latest = history.periods[-1]

    nopat_earliest, ic_earliest = _nopat_and_ic(earliest)
    nopat_latest, ic_latest = _nopat_and_ic(latest)

    delta_ic = ic_latest - ic_earliest
    delta_nopat = nopat_latest - nopat_earliest

    if delta_ic == 0.0:
        return FactorScore(
            name="incremental_roic",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(f"delta_NOPAT={delta_nopat:,.2f}, delta_IC=0 (no change in invested capital)"),
        )

    raw_value = delta_nopat / delta_ic

    detail = (
        f"delta_NOPAT={delta_nopat:,.2f}, delta_IC={delta_ic:,.2f}, "
        f"incremental_ROIC={raw_value:.4f}"
    )

    return FactorScore(
        name="incremental_roic",
        raw_value=raw_value,
        percentile_rank=0.0,
        detail=detail,
    )
