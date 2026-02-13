"""Acquirer's Multiple (EV/EBIT) value factor (Tobias Carlisle).

Measures how expensive a company is relative to its operating earnings.
Lower values indicate cheaper stocks (inverted percentile rank at scoring phase).

Formula:
    EV = Market Cap + Total Debt - Cash
    Acquirer's Multiple = EV / EBIT
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore


def acquirers_multiple(period: FinancialPeriod, market_cap: Decimal) -> FactorScore:
    """Compute Acquirer's Multiple (EV/EBIT) for a single financial period.

    Returns a FactorScore with:
    - raw_value: EV / EBIT, or 0.0 if EBIT <= 0 or market_cap <= 0
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer in Phase 6)
    - name: "acquirers_multiple"
    """
    if market_cap <= 0:
        return FactorScore(
            name="acquirers_multiple",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"market_cap={market_cap}; invalid market cap, EV/EBIT undefined",
        )

    ebit = period.current_income.ebit

    if ebit <= 0:
        return FactorScore(
            name="acquirers_multiple",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"EBIT={ebit}; non-positive EBIT, EV/EBIT undefined",
        )

    total_debt = period.current_balance.total_debt
    cash = period.current_balance.cash_and_equivalents or Decimal("0")
    ev = market_cap + total_debt - cash

    ratio = float(ev / ebit)

    return FactorScore(
        name="acquirers_multiple",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=(
            f"EV = {market_cap} + {total_debt} - {cash} = {ev}"
            f"; EBIT = {ebit}"
            f"; EV/EBIT = {ev} / {ebit} = {ratio:.4f}"
        ),
    )
