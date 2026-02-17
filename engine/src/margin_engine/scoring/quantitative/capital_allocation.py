"""Capital Allocation sub-factors.

Four metrics measuring management's skill at deploying capital:
1. Buyback Effectiveness — buying below average price
2. Debt Discipline — Net Debt / EBITDA trend
3. Organic Reinvestment Ratio — growth capex vs total deployment
4. Insider Ownership — skin in the game
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import FactorScore


def buyback_effectiveness(
    total_repurchases: Decimal,
    shares_reduced: int,
    avg_stock_price: float,
) -> FactorScore:
    """Ratio of avg buyback price to avg stock price. < 1.0 = buying cheap."""
    if shares_reduced <= 0 or total_repurchases <= 0:
        return FactorScore(
            name="buyback_effectiveness",
            raw_value=0.5,
            percentile_rank=0.0,
            detail="No buybacks, neutral score",
        )

    avg_buyback_price = float(abs(total_repurchases)) / shares_reduced
    if avg_stock_price <= 0:
        return FactorScore(
            name="buyback_effectiveness",
            raw_value=0.5,
            percentile_rank=0.0,
            detail="avg_stock_price <= 0",
        )

    ratio = avg_buyback_price / avg_stock_price

    return FactorScore(
        name="buyback_effectiveness",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=f"avg_buyback={avg_buyback_price:.2f}, avg_price={avg_stock_price:.2f}, ratio={ratio:.4f}",
    )


def debt_discipline(history: FinancialHistory) -> FactorScore:
    """5yr slope of Net Debt / EBITDA. Negative slope = improving discipline."""
    if len(history.periods) < 2:
        return FactorScore(
            name="debt_discipline",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Need 2+ periods for trend",
        )

    ratios = []
    for p in history.periods:
        ebitda = float(p.current_income.ebit) + float(p.current_income.depreciation or Decimal("0"))
        if ebitda <= 0:
            continue
        net_debt = float(p.current_balance.total_debt) - float(
            p.current_balance.cash_and_equivalents or Decimal("0")
        )
        ratios.append(net_debt / ebitda)

    if len(ratios) < 2:
        return FactorScore(
            name="debt_discipline",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Insufficient EBITDA-positive periods",
        )

    # Simple slope: (last - first) / (n - 1)
    slope = (ratios[-1] - ratios[0]) / (len(ratios) - 1)

    return FactorScore(
        name="debt_discipline",
        raw_value=slope,
        percentile_rank=0.0,
        detail=f"ND/EBITDA series={[f'{r:.2f}' for r in ratios]}, slope={slope:.4f}",
    )


def organic_reinvestment_ratio(period: FinancialPeriod) -> FactorScore:
    """Growth CapEx / Total Capital Deployed. Higher = investing in business."""
    ci = period.current_income
    cf = period.current_cash_flow

    capex_abs = abs(float(cf.capital_expenditures))
    depreciation = float(ci.depreciation or Decimal("0"))
    growth_capex = max(0.0, capex_abs - depreciation)

    buybacks = abs(float(cf.share_repurchases or Decimal("0")))
    dividends = abs(float(cf.dividends_paid or Decimal("0")))

    total_deployed = growth_capex + buybacks + dividends
    if total_deployed <= 0:
        return FactorScore(
            name="organic_reinvestment_ratio",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="No capital deployed",
        )

    ratio = growth_capex / total_deployed

    return FactorScore(
        name="organic_reinvestment_ratio",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=(
            f"growth_capex={growth_capex:.2f}, buybacks={buybacks:.2f}, "
            f"dividends={dividends:.2f}, total={total_deployed:.2f}, ratio={ratio:.4f}"
        ),
    )


def insider_ownership_score(ownership_pct: float) -> FactorScore:
    """Insider ownership as a raw percentage."""
    return FactorScore(
        name="insider_ownership",
        raw_value=ownership_pct,
        percentile_rank=0.0,
        detail=f"insider_ownership={ownership_pct:.4f}",
    )


def sbc_dilution_tax(
    sbc_amount: Decimal,
    revenue: Decimal,
) -> FactorScore:
    """SBC as % of revenue. Lower = better. Inverted at ranking time."""
    if revenue <= 0:
        return FactorScore(
            name="sbc_dilution_tax",
            raw_value=1.0,
            percentile_rank=0.0,
            detail="zero revenue, worst case",
        )

    ratio = float(abs(sbc_amount) / revenue)
    return FactorScore(
        name="sbc_dilution_tax",
        raw_value=ratio,
        percentile_rank=0.0,
        detail=f"SBC={float(sbc_amount):,.2f}, revenue={float(revenue):,.2f}, ratio={ratio:.4f}",
    )


def ma_discipline(
    roic_before_acquisition: float | None,
    roic_after_acquisition: float | None,
) -> FactorScore:
    """ROIC change after large acquisitions. Positive = value-creating."""
    if roic_before_acquisition is None or roic_after_acquisition is None:
        return FactorScore(
            name="ma_discipline",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="No acquisition data, neutral",
        )

    delta = roic_after_acquisition - roic_before_acquisition
    return FactorScore(
        name="ma_discipline",
        raw_value=delta,
        percentile_rank=0.0,
        detail=f"ROIC_before={roic_before_acquisition:.4f}, after={roic_after_acquisition:.4f}, delta={delta:.4f}",
    )
