"""Gross Profitability (Novy-Marx) quality factor.

Measures a company's gross profit scaled by total assets.
Academic reference: Novy-Marx (2013), "The other side of value:
The gross profitability premium."

Formula: (Revenue - COGS) / Total Assets
"""

from __future__ import annotations

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore


def gross_profitability(period: FinancialPeriod) -> FactorScore:
    """Compute gross profitability ratio for a single financial period.

    Returns a FactorScore with:
    - raw_value: (revenue - cost_of_revenue) / total_assets, or 0.0 if
      total_assets is zero
    - percentile_rank: 0.0 (placeholder — filled by composite scorer in Phase 6)
    - name: "gross_profitability"
    """
    revenue = period.current_income.revenue
    cogs = period.current_income.cost_of_revenue
    total_assets = period.current_balance.total_assets

    if total_assets == 0:
        return FactorScore(
            name="gross_profitability",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="total_assets=0; gross profitability undefined",
        )

    gross_profit = revenue - cogs
    ratio = float(gross_profit / total_assets)

    return FactorScore(
        name="gross_profitability",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=(
            f"({revenue} - {cogs}) / {total_assets}"
            f" = {gross_profit} / {total_assets}"
            f" = {ratio:.4f}"
        ),
    )
