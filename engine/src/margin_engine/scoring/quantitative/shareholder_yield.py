"""Shareholder Yield (Mebane Faber) value factor.

Measures the total capital returned to shareholders as a percentage of
market capitalization, combining dividends and net share buybacks.

Academic reference: Faber (2013), "Shareholder Yield: A Better Approach
to Dividend Investing."

Formula: (Dividends Paid + Net Buybacks) / Market Cap
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore


def shareholder_yield(period: FinancialPeriod, market_cap: Decimal) -> FactorScore:
    """Compute shareholder yield for a single financial period.

    Returns a FactorScore with:
    - raw_value: (abs(dividends_paid) + net_buybacks) / market_cap, or 0.0 if
      market_cap <= 0
    - percentile_rank: 0.0 (placeholder — filled by composite scorer in Phase 6)
    - name: "shareholder_yield"
    """
    if market_cap <= 0:
        return FactorScore(
            name="shareholder_yield",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"market_cap={market_cap}; shareholder yield undefined",
        )

    dividends = abs(period.current_cash_flow.dividends_paid or Decimal("0"))
    net_buybacks = period.current_cash_flow.net_buybacks

    total_return = dividends + net_buybacks
    ratio = float(total_return / market_cap)

    return FactorScore(
        name="shareholder_yield",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=(
            f"(dividends={dividends} + net_buybacks={net_buybacks})"
            f" / market_cap={market_cap}"
            f" = {total_return} / {market_cap}"
            f" = {ratio:.4f}"
        ),
    )
