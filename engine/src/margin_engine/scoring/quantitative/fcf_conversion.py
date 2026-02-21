"""FCF Conversion Ratio — measures cash quality of earnings.

FCF / Net Income. Values > 1.0 indicate earnings are fully backed by cash.
Values < 1.0 indicate accrual-heavy earnings that may not be durable.
"""

from __future__ import annotations

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore


def fcf_conversion(period: FinancialPeriod) -> FactorScore:
    """Compute FCF / Net Income ratio.

    Returns 0.0 if net income <= 0 (ratio is meaningless).
    """
    ni = float(period.current_income.net_income)
    if ni <= 0:
        return FactorScore(
            name="fcf_conversion",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"NI={ni:.2f}; non-positive, ratio undefined",
        )

    fcf = float(period.current_cash_flow.free_cash_flow)
    ratio = fcf / ni

    return FactorScore(
        name="fcf_conversion",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=f"FCF={fcf:.2f} / NI={ni:.2f} = {ratio:.4f}",
    )
