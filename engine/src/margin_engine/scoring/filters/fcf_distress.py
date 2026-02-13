"""Free Cash Flow distress check filter.

Checks whether a company has negative free cash flow, which indicates
potential financial distress or unsustainable operations.

FCF = operating_cash_flow + capital_expenditures (capex is already negative).

A negative FCF means the company is burning cash and may not be able to
sustain operations without external financing.

NOTE: The design spec calls for "3+ consecutive quarters with negative FCF = FAIL."
This implementation uses annual FCF as a simplification since the FinancialPeriod
model currently carries annual (not quarterly) data. The quarterly check will be
added when the ingestion layer (Phase 7) provides quarterly time-series data.
"""

from __future__ import annotations

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FilterResult

_THRESHOLD = 0.0


def fcf_distress_check(period: FinancialPeriod) -> FilterResult:
    """Check if free cash flow indicates financial distress.

    FAIL if current period FCF is negative.
    Uses annual data: FCF = operating_cash_flow + capital_expenditures.

    Args:
        period: Financial data with current cash flow statement.

    Returns:
        FilterResult with passed=True if FCF >= 0, False otherwise.
    """
    name = "fcf_distress"

    fcf = period.current_cash_flow.free_cash_flow
    fcf_float = float(fcf)

    passed = fcf_float >= _THRESHOLD

    detail = (
        f"FCF={fcf_float:,.0f} ({'PASS' if passed else 'FAIL'}, "
        f"threshold={_THRESHOLD}). "
        f"operating_cf={float(period.current_cash_flow.operating_cash_flow):,.0f}, "
        f"capex={float(period.current_cash_flow.capital_expenditures):,.0f}"
    )

    return FilterResult(
        name=name,
        passed=passed,
        value=fcf_float,
        threshold=_THRESHOLD,
        detail=detail,
    )
