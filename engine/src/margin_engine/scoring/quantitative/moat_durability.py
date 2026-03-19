"""Moat Durability classifier — detects moat signatures from financial patterns.

Four signatures detected from multi-year financial data:
1. Scale Economics: ROIC increases as revenue grows (positive slope)
2. Pricing Power: Gross margins expand over time
3. Operating Leverage: Revenue growth exceeds proportional cost growth
4. Capital Efficiency: Incremental ROIC >= trailing ROIC

Signatures are weighted by empirical durability:
    operating_leverage=1.5, pricing_power=1.25, scale_economics=1.0, capital_efficiency=0.75
raw_value = weighted sum normalized to 0-4 scale.

Additional qualitative proxies (not part of _SIGNATURE_WEIGHTS):
- Switching Costs: high SGA/Revenue + stable revenue retention
- Regulatory Moat: sector-level regulatory barriers
- Brand Moat: sustained gross margin premium over sector median
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, FinancialPeriod, GICSSector
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


def _detect_switching_costs(history: FinancialHistory) -> float:
    """Switching-costs proxy: high SGA spend + sticky revenue retention.

    Returns confidence 0.0–0.8.

    Conditions (both must hold across 3+ periods):
    - Average SGA/Revenue > 20%
    - Minimum period-over-period revenue retention > 95%
      (i.e. revenue never drops more than 5% in any single year)
    """
    periods = history.periods
    if len(periods) < 3:
        return 0.0

    # Collect SGA ratios; all periods must have non-None sga_expense
    sga_ratios: list[float] = []
    for p in periods:
        sga = p.current_income.sga_expense
        rev = p.current_income.revenue
        if sga is None or rev == 0:
            return 0.0
        sga_ratios.append(float(sga / rev))

    avg_sga_ratio = sum(sga_ratios) / len(sga_ratios)
    if avg_sga_ratio <= 0.20:
        return 0.0

    # Check minimum revenue retention across consecutive periods
    revenues = [float(p.current_income.revenue) for p in periods]
    for i in range(1, len(revenues)):
        if revenues[i - 1] <= 0:
            return 0.0
        retention = revenues[i] / revenues[i - 1]
        if retention < 0.95:
            return 0.0

    return 0.8


def _detect_regulatory_moat(sector: GICSSector) -> float:
    """Regulatory-moat proxy: sector-level regulatory barriers.

    Returns:
        1.0 for Utilities (natural monopoly / rate-regulated)
        0.7 for Financials and Healthcare (licensing/compliance barriers)
        0.0 for all other sectors
    """
    if sector == GICSSector.UTILITIES:
        return 1.0
    if sector in (GICSSector.FINANCIALS, GICSSector.HEALTHCARE):
        return 0.7
    return 0.0


def _detect_brand_moat(
    history: FinancialHistory,
    sector: GICSSector,
    sector_median_gm: float = 0.30,
) -> float:
    """Brand-moat proxy: sustained gross-margin premium above sector median.

    Requires 5+ periods where >= 80% of periods have GM > (sector_median_gm + 0.15).

    Returns 0.7 if conditions met, else 0.0.
    """
    periods = history.periods
    if len(periods) < 5:
        return 0.0

    threshold = sector_median_gm + 0.15
    above = sum(1 for p in periods if p.current_income.gross_margin > threshold)
    if above / len(periods) >= 0.80:
        return 0.7
    return 0.0


_SIGNATURE_WEIGHTS: dict[str, float] = {
    "operating_leverage": 1.5,
    "pricing_power": 1.25,
    "scale_economics": 1.0,
    "capital_efficiency": 0.75,
}

_MAX_WEIGHTED = sum(_SIGNATURE_WEIGHTS.values())  # 4.5


def moat_durability_score(
    history: FinancialHistory,
    sector: GICSSector | None = None,
    sector_median_gm: float = 0.30,
) -> FactorScore:
    """Compute moat durability score (weighted 0-4 scale).

    Signatures are weighted by empirical durability, then normalized to
    the 0-4 scale so that downstream thresholds (>= 2, >= 3) remain valid.

    Optional ``sector`` and ``sector_median_gm`` enable moat-source
    classification metadata without changing the numeric score.
    """
    if len(history.periods) < 2:
        return FactorScore(
            name="moat_durability",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="Need 2+ periods for moat detection",
            metadata={
                "primary_moat": "none",
                "moat_confidence": 0.0,
                "secondary_moats": [],
                "moat_sources_detected": [],
            },
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

    # --- Moat source classification (does NOT affect numeric score) ---
    detected: dict[str, float] = {}

    sc_confidence = _detect_switching_costs(history)
    if sc_confidence > 0.0:
        detected["switching_costs"] = sc_confidence

    if sector is not None:
        reg_confidence = _detect_regulatory_moat(sector)
        if reg_confidence > 0.0:
            detected["regulatory"] = reg_confidence

        brand_confidence = _detect_brand_moat(history, sector, sector_median_gm)
        if brand_confidence > 0.0:
            detected["brand"] = brand_confidence

    if detected:
        primary = max(detected, key=lambda k: detected[k])
        confidence = detected[primary]
    else:
        primary = "none"
        confidence = 0.0

    metadata: dict[str, object] = {
        "primary_moat": primary,
        "moat_confidence": confidence,
        "secondary_moats": [k for k in detected if k != primary],
        "moat_sources_detected": list(detected.keys()),
    }

    return FactorScore(
        name="moat_durability",
        raw_value=normalized,
        percentile_rank=0.0,
        detail=f"signatures={signatures}, count={len(signatures)}",
        metadata=metadata,
    )
