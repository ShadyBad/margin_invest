"""EV/FCF (Enterprise Value / Free Cash Flow) value factor.

Measures how expensive a company is relative to the cash it generates.
Lower values indicate cheaper stocks (inverted percentile rank at scoring phase).

Formula:
    EV = Market Cap + Total Debt - Cash
    FCF = CFO + CapEx  (CapEx is negative, so this is CFO - |CapEx|)
    EV/FCF = EV / FCF
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore


def ev_fcf(period: FinancialPeriod, market_cap: Decimal) -> FactorScore:
    """Compute EV/FCF ratio for a single financial period.

    Returns a FactorScore with:
    - raw_value: EV / FCF, or 0.0 if FCF <= 0 or market_cap <= 0
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer in Phase 6)
    - name: "ev_fcf"
    """
    if market_cap <= 0:
        return FactorScore(
            name="ev_fcf",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"market_cap={market_cap}; invalid market cap, EV/FCF undefined",
        )

    total_debt = period.current_balance.total_debt
    cash = period.current_balance.cash_and_equivalents or Decimal("0")
    ev = market_cap + total_debt - cash

    fcf = period.current_cash_flow.free_cash_flow

    if fcf <= 0:
        return FactorScore(
            name="ev_fcf",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"FCF={fcf}; negative/zero free cash flow, EV/FCF undefined",
        )

    ratio = float(ev / fcf)

    return FactorScore(
        name="ev_fcf",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=(
            f"EV = {market_cap} + {total_debt} - {cash} = {ev}"
            f"; FCF = {fcf}"
            f"; EV/FCF = {ev} / {fcf} = {ratio:.4f}"
        ),
    )
