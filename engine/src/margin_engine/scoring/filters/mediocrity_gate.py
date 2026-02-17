"""Anti-Mediocrity Gate — pre-scoring filter removing businesses not worth evaluating.

Thresholds:
    - 5yr median ROIC > 8%
    - Gross margin > 20% (sector-adjusted: Utilities > 10%, Energy > 15%)
    - Positive FCF in 4 of last 5 years
    - Revenue not declining 3+ consecutive years
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import FinancialHistory, GICSSector
from margin_engine.models.scoring import FilterResult

_ROIC_THRESHOLD = 0.08
_DEFAULT_GM_THRESHOLD = 0.20
_UTILITIES_GM_THRESHOLD = 0.10
_ENERGY_GM_THRESHOLD = 0.15
_MIN_FCF_POSITIVE_YEARS = 4
_MAX_REVENUE_DECLINE_YEARS = 3


def _sector_gm_threshold(sector: GICSSector) -> float:
    if sector == GICSSector.UTILITIES:
        return _UTILITIES_GM_THRESHOLD
    if sector == GICSSector.ENERGY:
        return _ENERGY_GM_THRESHOLD
    return _DEFAULT_GM_THRESHOLD


def _compute_roic(period) -> float | None:
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


def mediocrity_gate(
    history: FinancialHistory,
    sector: GICSSector,
) -> FilterResult:
    """Run anti-mediocrity gate. Returns FilterResult (passed=True/False)."""
    failures: list[str] = []

    # 1. ROIC check (5yr median > 8%)
    roics = [r for p in history.periods if (r := _compute_roic(p)) is not None]
    if roics:
        median_roic = statistics.median(roics)
        if median_roic <= _ROIC_THRESHOLD:
            failures.append(f"median_ROIC={median_roic:.4f} <= {_ROIC_THRESHOLD}")
    else:
        failures.append("no valid ROIC periods")

    # 2. Gross margin check (sector-adjusted)
    gm_threshold = _sector_gm_threshold(sector)
    gms = [p.current_income.gross_margin for p in history.periods]
    if gms:
        median_gm = statistics.median(gms)
        if median_gm <= gm_threshold:
            failures.append(f"median_GM={median_gm:.4f} <= {gm_threshold}")

    # 3. FCF consistency (4 of last 5 years positive)
    recent = history.periods[-5:] if len(history.periods) >= 5 else history.periods
    fcf_positive = sum(1 for p in recent if p.current_cash_flow.free_cash_flow > 0)
    if len(recent) >= 5 and fcf_positive < _MIN_FCF_POSITIVE_YEARS:
        failures.append(
            f"FCF positive {fcf_positive}/{len(recent)} years (need {_MIN_FCF_POSITIVE_YEARS})"
        )

    # 4. Revenue trend (not declining 3+ consecutive years)
    if len(history.periods) >= _MAX_REVENUE_DECLINE_YEARS:
        revenues = [float(p.current_income.revenue) for p in history.periods]
        consecutive_declines = 0
        max_declines = 0
        for i in range(1, len(revenues)):
            if revenues[i] < revenues[i - 1]:
                consecutive_declines += 1
                max_declines = max(max_declines, consecutive_declines)
            else:
                consecutive_declines = 0
        if max_declines >= _MAX_REVENUE_DECLINE_YEARS:
            failures.append(f"revenue declined {max_declines} consecutive years")

    passed = len(failures) == 0
    detail = "All gates passed" if passed else "; ".join(failures)

    return FilterResult(
        name="mediocrity_gate",
        passed=passed,
        detail=detail,
    )
