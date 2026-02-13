"""Sloan Accrual Ratio earnings quality factor.

Measures the proportion of earnings attributable to accruals vs. cash.
Lower (more negative) values indicate higher earnings quality, meaning
cash earnings exceed accrual earnings.

Academic reference: Sloan (1996), "Do Stock Prices Fully Reflect
Information in Accruals and Cash Flows about Future Earnings?"

Formula: (Net Income - Operating Cash Flow) / Total Assets
"""

from __future__ import annotations

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore


def sloan_accrual_ratio(period: FinancialPeriod) -> FactorScore:
    """Compute the Sloan accrual ratio for a single financial period.

    Returns a FactorScore with:
    - raw_value: (net_income - operating_cash_flow) / total_assets, or 0.0 if
      total_assets is zero
    - percentile_rank: 0.0 (placeholder — filled by composite scorer in Phase 6)
    - name: "accrual_ratio"
    """
    net_income = period.current_income.net_income
    cfo = period.current_cash_flow.operating_cash_flow
    total_assets = period.current_balance.total_assets

    if total_assets == 0:
        return FactorScore(
            name="accrual_ratio",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="total_assets=0; accrual ratio undefined",
        )

    accruals = net_income - cfo
    ratio = float(accruals / total_assets)

    return FactorScore(
        name="accrual_ratio",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=(
            f"({net_income} - {cfo}) / {total_assets}"
            f" = {accruals} / {total_assets}"
            f" = {ratio:.4f}"
        ),
    )
