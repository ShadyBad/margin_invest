"""V3 intermediate value calculators — pure functions converting raw data to v3 metrics.

These bridge the gap between raw financial data and the v3 composite scoring
functions (v3_composite.py) which expect pre-computed metrics.
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.scoring.quantitative.capital_allocation import (
    debt_discipline,
    insider_ownership_score,
    ma_discipline,
    organic_reinvestment_ratio,
    sbc_dilution_tax,
)


def compute_owner_earnings_iv(
    owner_earnings_per_share: float,
    wacc: float,
    terminal_growth: float = 0.03,
) -> float:
    """Gordon growth model: OE * (1 + g) / (WACC - g).

    Returns 0.0 if inputs are invalid (negative OE, WACC <= growth).
    """
    if owner_earnings_per_share <= 0 or wacc <= terminal_growth:
        return 0.0
    return owner_earnings_per_share * (1.0 + terminal_growth) / (wacc - terminal_growth)


def _median_tax_rate(history: FinancialHistory) -> float:
    """Return median effective tax rate across all periods."""
    rates = [p.current_income.effective_tax_rate for p in history.periods]
    if not rates:
        return 0.21  # US statutory fallback
    return statistics.median(rates)


def _nopat_and_ic(period: FinancialPeriod) -> tuple[float, float]:
    """Return (NOPAT, Invested Capital) for a period."""
    ci = period.current_income
    cb = period.current_balance
    ebit = float(ci.ebit)
    tax_rate = ci.effective_tax_rate
    nopat = ebit * (1.0 - tax_rate)
    cash = float(cb.cash_and_equivalents or Decimal("0"))
    ic = float(cb.total_equity) + float(cb.total_debt) - cash
    return nopat, ic


def compute_compounding_power(history: FinancialHistory) -> float:
    """Compute compounding power = incremental_ROIC * reinvestment_rate * stability.

    Stability uses MAD (median absolute deviation) instead of CV, making it
    robust to outliers. This benefits serial acquirers with lumpy ROIC histories.

    Returns 0.0 if insufficient data or any component is non-positive.
    """
    if len(history.periods) < 2:
        return 0.0

    # Incremental ROIC (earliest -> latest)
    nopat_e, ic_e = _nopat_and_ic(history.periods[0])
    nopat_l, ic_l = _nopat_and_ic(history.periods[-1])
    delta_ic = ic_l - ic_e
    if delta_ic <= 0:
        return 0.0
    inc_roic = (nopat_l - nopat_e) / delta_ic
    if inc_roic <= 0:
        return 0.0

    # Reinvestment rate from latest period: (growth_capex + rd_growth) / NOPAT
    latest = history.periods[-1]
    capex = abs(float(latest.current_cash_flow.capital_expenditures))
    depreciation = float(latest.current_income.depreciation or Decimal("0"))
    growth_capex = max(capex - depreciation, 0.0)

    # Include R&D growth as reinvestment (captures R&D-intensive compounders)
    rd_growth = 0.0
    if (
        latest.current_income.rd_expense is not None
        and latest.prior_income is not None
        and latest.prior_income.rd_expense is not None
    ):
        current_rd = float(latest.current_income.rd_expense)
        prior_rd = float(latest.prior_income.rd_expense)
        inflation_adj_prior = prior_rd * 1.03  # 3% inflation adjustment
        rd_growth = max(current_rd - inflation_adj_prior, 0.0)

    total_reinvestment = growth_capex + rd_growth
    if nopat_l <= 0:
        return 0.0
    reinvestment_rate = total_reinvestment / nopat_l
    if reinvestment_rate <= 0:
        return 0.0

    # ROIC stability via MAD (robust to outliers, benefits serial acquirers)
    # Use median tax rate to isolate operating performance from tax volatility
    med_tax = _median_tax_rate(history)
    roics = []
    for p in history.periods:
        ci = p.current_income
        cb = p.current_balance
        ebit = float(ci.ebit)
        nopat_m = ebit * (1.0 - med_tax)
        cash = float(cb.cash_and_equivalents or Decimal("0"))
        ic = float(cb.total_equity) + float(cb.total_debt) - cash
        if ic > 0:
            roics.append(nopat_m / ic)
    if len(roics) < 2:
        stability = 1.0
    else:
        median_roic = statistics.median(roics)
        mad = statistics.median([abs(r - median_roic) for r in roics])
        normalized_mad = min(mad / max(abs(median_roic), 0.001), 1.0)
        stability = 1.0 - normalized_mad

    return inc_roic * reinvestment_rate * max(stability, 0.0)


def _normalize_factor(raw_value: float, max_value: float) -> float:
    """Normalize a raw factor value to 0-1 range."""
    if max_value <= 0:
        return 0.0
    return min(max(raw_value / max_value, 0.0), 1.0)


def compute_capital_allocation_composite(
    period: FinancialPeriod,
    history: FinancialHistory,
    buyback_yield: float | None,
    insider_ownership_pct: float | None,
    sbc_pct: float | None,
    recent_acquisition_count: int,
) -> float:
    """Compute capital allocation composite from available sub-factors.

    Runs available capital allocation sub-factors, normalizes each to 0-1,
    returns simple average of available factors.
    """
    scores: list[float] = []

    # 1. Debt discipline — needs 2+ periods
    if len(history.periods) >= 2:
        dd = debt_discipline(history)
        # Negative slope = improving discipline, so negate for scoring
        scores.append(_normalize_factor(-dd.raw_value, 3.0))

    # 2. Organic reinvestment ratio — always available
    orr = organic_reinvestment_ratio(period)
    scores.append(min(max(orr.raw_value, 0.0), 1.0))

    # 3. Buyback effectiveness — if buyback_yield provided and > 0
    if buyback_yield is not None and buyback_yield > 0:
        scores.append(_normalize_factor(buyback_yield, 0.10))

    # 4. Insider ownership — if provided
    if insider_ownership_pct is not None:
        io = insider_ownership_score(insider_ownership_pct)
        scores.append(_normalize_factor(io.raw_value, 3.0))

    # 5. SBC dilution tax — if sbc_pct provided
    if sbc_pct is not None:
        sbc_amount = Decimal(str(sbc_pct * float(period.current_income.revenue)))
        sbc = sbc_dilution_tax(sbc_amount, period.current_income.revenue)
        # raw_value is ratio (lower = better), invert: 1.0 - ratio
        scores.append(min(max(1.0 - sbc.raw_value, 0.0), 1.0))

    # 6. M&A discipline
    if recent_acquisition_count == 0:
        scores.append(1.0)
    else:
        ma = ma_discipline(None, None)
        scores.append(_normalize_factor(ma.raw_value, 1.0))

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


def compute_catalyst_strength(
    sue_percentile: float,
) -> float:
    """Catalyst strength = SUE percentile (passthrough).

    Insider and institutional percentiles were removed because they had no
    real data source (hardcoded at 50.0). They will return when a 13F
    filing pipeline is available.
    """
    return sue_percentile


def compute_quality_floor_factor(roic: float, roic_improving: bool) -> float:
    """Quality floor factor for Track B multiplicative scoring.

    Returns:
        1.0 if ROIC >= 8%
        0.5-1.0 if ROIC < 8% but improving (scaled linearly)
        0.0 if ROIC < 8% and not improving
    """
    threshold = 0.08
    if roic >= threshold:
        return 1.0
    if roic_improving:
        return 0.5 + 0.5 * min(roic / threshold, 1.0)
    return 0.0


def compute_valuation_convergence_factor(converging_count: int) -> float:
    """Valuation convergence factor for Track B multiplicative scoring.

    Returns converging_count/4, floored at 0.75.
    """
    return max(converging_count / 4.0, 0.75)


def compute_downside_protection(
    current_price: float,
    asset_floor_per_share: float,
) -> tuple[float, bool]:
    """Compute max loss percentage and whether downside protection gate passes.

    Returns (max_loss_pct, passed) where passed = max_loss_pct < 0.50.
    """
    if current_price <= 0:
        return 0.0, True
    max_loss = max(0.0, (current_price - asset_floor_per_share) / current_price)
    return max_loss, max_loss < 0.50
