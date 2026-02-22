"""Operating Leverage — revenue growth rate relative to OpEx growth rate.

Measures whether a company is scaling efficiently. A ratio > 1.0 means
revenue is growing faster than operating expenses, indicating positive
operating leverage and improving margins.

Formula:
    Operating Leverage = revenue_growth_rate / opex_growth_rate

Where:
    OpEx = SGA expense (selling, general & administrative)
    Growth rates are computed from earliest to latest period in the history.

Capped at 10.0 to prevent extreme outliers when opex growth is near zero.
"""

from __future__ import annotations

from margin_engine.models.financial import FinancialHistory
from margin_engine.models.scoring import FactorScore

_CAP = 10.0


def operating_leverage(history: FinancialHistory) -> FactorScore:
    """Compute operating leverage from multi-year financial history.

    Returns a FactorScore with:
    - raw_value: revenue growth / opex growth, capped at 10.0
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer)
    - name: "operating_leverage"

    Uses earliest and latest periods. OpEx is SGA expense.
    Returns 0.0 if fewer than 2 periods or missing SGA data.
    """
    if len(history.periods) < 2:
        return FactorScore(
            name="operating_leverage",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"periods={len(history.periods)}; need at least 2 periods",
        )

    earliest = history.periods[0]
    latest = history.periods[-1]

    start_revenue = float(earliest.current_income.revenue)
    end_revenue = float(latest.current_income.revenue)

    start_sga = earliest.current_income.sga_expense
    end_sga = latest.current_income.sga_expense

    if start_sga is None or end_sga is None:
        return FactorScore(
            name="operating_leverage",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Missing SGA expense data; cannot compute operating leverage",
        )

    start_opex = float(start_sga)
    end_opex = float(end_sga)

    if start_revenue <= 0 or start_opex <= 0:
        return FactorScore(
            name="operating_leverage",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"start_revenue={start_revenue}, start_opex={start_opex}; "
                "zero/negative starting values"
            ),
        )

    rev_growth = (end_revenue - start_revenue) / start_revenue
    opex_growth = (end_opex - start_opex) / start_opex

    # Cost-cutting floor: near-zero revenue growth but declining opex
    # rewards operational discipline even without top-line growth
    if rev_growth <= 0.01 and opex_growth < 0:
        leverage = min(abs(opex_growth) * 5.0, 2.0)
        return FactorScore(
            name="operating_leverage",
            raw_value=leverage,
            percentile_rank=0.0,
            detail=(
                f"cost_cutting_floor: rev_growth={rev_growth:.4f}"
                f"; opex_growth={opex_growth:.4f}"
                f"; raw_value=min(|{opex_growth:.4f}|*5.0, 2.0)={leverage:.4f}"
            ),
        )

    if opex_growth == 0.0:
        # OpEx flat while revenue grew: very high leverage, cap it
        leverage = _CAP if rev_growth > 0 else 0.0
    else:
        leverage = rev_growth / opex_growth
        leverage = min(leverage, _CAP)

    return FactorScore(
        name="operating_leverage",
        raw_value=leverage,
        percentile_rank=0.0,
        detail=(
            f"rev_growth={rev_growth:.4f} ({rev_growth * 100:.2f}%)"
            f"; opex_growth={opex_growth:.4f} ({opex_growth * 100:.2f}%)"
            f"; leverage = {rev_growth:.4f} / {opex_growth:.4f} = {leverage:.4f}"
            f" (capped at {_CAP})"
        ),
    )
