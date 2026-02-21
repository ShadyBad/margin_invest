"""EV/Gross Profit — enterprise value relative to gross profit factor.

Measures how expensive a company is relative to its gross profit.
Lower values indicate cheaper stocks (inverted percentile at scoring phase).

Formula:
    EV = Market Cap + Total Debt - Cash
    GP = Revenue - Cost of Revenue  (i.e. gross_profit from IncomeStatement)
    EV/GP = EV / GP
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore


def ev_gross_profit(period: FinancialPeriod, market_cap: Decimal) -> FactorScore:
    """Compute EV/Gross Profit ratio for a single financial period.

    Returns a FactorScore with:
    - raw_value: EV / Gross Profit, or 0.0 if GP <= 0 or market_cap <= 0
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer)
    - name: "ev_gross_profit"

    Args:
        period: Financial period containing income statement and balance sheet.
        market_cap: Current market capitalization.
    """
    if market_cap <= 0:
        return FactorScore(
            name="ev_gross_profit",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"market_cap={market_cap}; invalid market cap, EV/GP undefined",
        )

    gross_profit = period.current_income.gross_profit

    if gross_profit <= 0:
        return FactorScore(
            name="ev_gross_profit",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"gross_profit={gross_profit}; non-positive gross profit, EV/GP undefined",
        )

    total_debt = period.current_balance.total_debt
    cash = period.current_balance.cash_and_equivalents or Decimal("0")
    ev = market_cap + total_debt - cash

    ratio = float(ev / gross_profit)

    return FactorScore(
        name="ev_gross_profit",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=(
            f"EV = {market_cap} + {total_debt} - {cash} = {ev}"
            f"; GP = {gross_profit}"
            f"; EV/GP = {ev} / {gross_profit} = {ratio:.4f}"
        ),
    )
