"""Moat Durability classifier — detects moat signatures from financial patterns.

Four signatures detected from multi-year financial data:
1. Scale Economics: ROIC increases as revenue grows (positive slope)
2. Pricing Power: Gross margins expand over time
3. Operating Leverage: Revenue growth exceeds proportional cost growth
4. Capital Efficiency: Incremental ROIC >= trailing ROIC

Signatures are weighted by empirical durability:
    operating_leverage=1.5, pricing_power=1.25, scale_economics=1.0, capital_efficiency=0.75
raw_value = weighted sum normalized to 0-4 scale.
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import FactorScore


def _compute_roic(period: FinancialPeriod) -> float | None:
    """Compute ROIC for a single period. Returns None if IC <= 0."""
    ci = period.current_income
    cb = period.current_balance
    ebit = float(ci.ebit)
    tax_rate = ci.effective_tax_rate
    nopat = ebit * (1.0 - tax_rate)
    cash = float(cb.cash_and_equivalents or Decimal("0"))
    ic = float(cb.total_equity) + float(cb.total_debt) - cash
    if ic <= 0:
        return None
    return nopat / ic


def _detect_scale_economics(history: FinancialHistory) -> bool:
    """ROIC increases as revenue grows over 3+ periods."""
    pairs: list[tuple[float, float]] = []
    for p in history.periods:
        roic = _compute_roic(p)
        if roic is not None:
            pairs.append((float(p.current_income.revenue), roic))
    if len(pairs) < 3:
        return False
    rev_grew = pairs[-1][0] > pairs[0][0]
    roic_grew = pairs[-1][1] > pairs[0][1]
    if not (rev_grew and roic_grew):
        return False
    increases = sum(1 for i in range(1, len(pairs)) if pairs[i][1] > pairs[i - 1][1])
    return increases / (len(pairs) - 1) >= 0.6


def _detect_pricing_power(history: FinancialHistory) -> bool:
    """Gross margins expand over 3+ periods."""
    margins = [p.current_income.gross_margin for p in history.periods]
    if len(margins) < 3:
        return False
    if margins[-1] <= margins[0]:
        return False
    increases = sum(1 for i in range(1, len(margins)) if margins[i] > margins[i - 1])
    return increases / (len(margins) - 1) >= 0.6


def _detect_operating_leverage(history: FinancialHistory) -> bool:
    """Operating leverage proxy: revenue growth rate exceeds cost growth rate."""
    if len(history.periods) < 3:
        return False
    revenues = [float(p.current_income.revenue) for p in history.periods]
    costs = [float(p.current_income.cost_of_revenue) for p in history.periods]
    if revenues[0] <= 0 or costs[0] <= 0:
        return False
    rev_growth = (revenues[-1] / revenues[0]) - 1.0
    cost_growth = (costs[-1] / costs[0]) - 1.0
    return rev_growth > cost_growth and rev_growth > 0


def _detect_capital_efficiency(history: FinancialHistory) -> bool:
    """Incremental ROIC >= trailing median ROIC."""
    roics = [r for p in history.periods if (r := _compute_roic(p)) is not None]
    if len(roics) < 2:
        return False
    median_roic = statistics.median(roics)
    earliest = history.periods[0]
    latest = history.periods[-1]
    ci_e, cb_e = earliest.current_income, earliest.current_balance
    ci_l, cb_l = latest.current_income, latest.current_balance
    nopat_e = float(ci_e.ebit) * (1.0 - ci_e.effective_tax_rate)
    nopat_l = float(ci_l.ebit) * (1.0 - ci_l.effective_tax_rate)
    cash_e = float(cb_e.cash_and_equivalents or Decimal("0"))
    cash_l = float(cb_l.cash_and_equivalents or Decimal("0"))
    ic_e = float(cb_e.total_equity) + float(cb_e.total_debt) - cash_e
    ic_l = float(cb_l.total_equity) + float(cb_l.total_debt) - cash_l
    delta_ic = ic_l - ic_e
    if delta_ic <= 0:
        return False
    inc_roic = (nopat_l - nopat_e) / delta_ic
    return inc_roic >= median_roic and inc_roic > 0


_SIGNATURE_WEIGHTS: dict[str, float] = {
    "operating_leverage": 1.5,
    "pricing_power": 1.25,
    "scale_economics": 1.0,
    "capital_efficiency": 0.75,
}

_MAX_WEIGHTED = sum(_SIGNATURE_WEIGHTS.values())  # 4.5


def moat_durability_score(history: FinancialHistory) -> FactorScore:
    """Compute moat durability score (weighted 0-4 scale).

    Signatures are weighted by empirical durability, then normalized to
    the 0-4 scale so that downstream thresholds (>= 2, >= 3) remain valid.
    """
    if len(history.periods) < 2:
        return FactorScore(
            name="moat_durability",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Need 2+ periods for moat detection",
        )

    signatures: list[str] = []
    if _detect_scale_economics(history):
        signatures.append("scale_economics")
    if _detect_pricing_power(history):
        signatures.append("pricing_power")
    if _detect_operating_leverage(history):
        signatures.append("operating_leverage")
    if _detect_capital_efficiency(history):
        signatures.append("capital_efficiency")

    weighted_sum = sum(_SIGNATURE_WEIGHTS[s] for s in signatures)
    normalized = weighted_sum * (4.0 / _MAX_WEIGHTED)

    return FactorScore(
        name="moat_durability",
        raw_value=normalized,
        percentile_rank=0.0,
        detail=f"signatures={signatures}, count={len(signatures)}",
    )
