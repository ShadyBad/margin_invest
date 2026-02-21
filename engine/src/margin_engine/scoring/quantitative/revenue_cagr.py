"""Revenue CAGR — compound annual growth rate of revenue.

Measures the annualized growth rate of revenue over multiple periods.
Higher values indicate faster-growing companies.

Formula:
    CAGR = (end_revenue / start_revenue) ^ (1 / years) - 1

Uses the first and last periods from FinancialHistory, up to years+1 periods.
"""

from __future__ import annotations

from margin_engine.models.financial import FinancialHistory
from margin_engine.models.scoring import FactorScore


def revenue_cagr(history: FinancialHistory, years: int = 3) -> FactorScore:
    """Compute revenue CAGR from multi-year financial history.

    Returns a FactorScore with:
    - raw_value: CAGR as a decimal (0.26 = 26% annual growth), or 0.0 sentinel
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer)
    - name: "revenue_cagr"

    Args:
        history: Financial history with periods sorted by period_end ascending.
        years: Target number of years to compute CAGR over (uses up to years+1 periods).
    """
    # Need at least 2 periods to compute growth
    if len(history.periods) < 2:
        return FactorScore(
            name="revenue_cagr",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"periods={len(history.periods)}; need at least 2 periods for CAGR",
        )

    # Take up to years+1 periods (already sorted ascending by period_end)
    usable_periods = history.periods[: years + 1]
    start_revenue = float(usable_periods[0].current_income.revenue)
    end_revenue = float(usable_periods[-1].current_income.revenue)
    n = len(usable_periods) - 1  # number of years between first and last

    if start_revenue <= 0:
        return FactorScore(
            name="revenue_cagr",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"start_revenue={start_revenue}; zero/negative starting revenue",
        )

    if end_revenue <= 0:
        # Negative ending revenue means company is shrinking badly
        cagr = -1.0
    else:
        cagr = (end_revenue / start_revenue) ** (1.0 / n) - 1.0

    return FactorScore(
        name="revenue_cagr",
        raw_value=cagr,
        percentile_rank=0.0,
        detail=(
            f"start_revenue={start_revenue:.2f}"
            f"; end_revenue={end_revenue:.2f}"
            f"; years={n}"
            f"; CAGR = ({end_revenue:.2f} / {start_revenue:.2f})^(1/{n}) - 1"
            f" = {cagr:.4f} ({cagr * 100:.2f}%)"
        ),
    )
