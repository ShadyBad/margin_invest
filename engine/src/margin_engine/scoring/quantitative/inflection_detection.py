"""Inflection Detection — identifies companies transitioning from deterioration to improvement.

Three signals are combined:

1. OpEx Deleverage: OpEx/Revenue ratio declining for 2+ consecutive periods.
   Score = min(total_magnitude / 0.01, 4.0). Zero if fewer than 2 consecutive declines.

2. FCF Crossover: Company transitions from negative to positive FCF (net_income + depreciation).
   Score = min(prior_negative_streak_length, 3.0). Requires last 2 positive + >= 1 prior negative.

3. Margin Expansion: Gross margin expanding for 2+ consecutive periods, near all-time high.
   Score = proximity * consistency * 3.0, capped at 3.0.
   "Near ATH" = within 200bps.

Composite (0-10 scale): opex + fcf + margin, capped at 10.0.
"""

from __future__ import annotations

from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import FactorScore

_OPEX_SCALE = 0.01  # 1 bp per unit of magnitude
_OPEX_CAP = 4.0
_FCF_CAP = 3.0
_MARGIN_CAP = 3.0
_COMPOSITE_CAP = 10.0
_ATH_PROXIMITY_THRESHOLD = 0.02  # 200 bps


def _opex_ratio(period: FinancialPeriod) -> float | None:
    """Compute OpEx/Revenue for a period. Returns None if revenue is zero."""
    income = period.current_income
    rev = float(income.revenue)
    if rev == 0.0:
        return None
    cor = float(income.cost_of_revenue)
    sga = float(income.sga_expense) if income.sga_expense is not None else 0.0
    return (cor + sga) / rev


def opex_deleverage_score(history: FinancialHistory) -> float:
    """Compute OpEx deleverage score (0-4).

    Counts consecutive OpEx/Revenue ratio declines. Score is proportional to
    total magnitude of decline, capped at 4.0. Returns 0 if fewer than 2
    consecutive declines exist.
    """
    periods = history.periods
    if len(periods) < 2:
        return 0.0

    ratios = [_opex_ratio(p) for p in periods]

    # Find the longest streak of consecutive declines
    best_streak_magnitude = 0.0
    current_streak_len = 0
    current_streak_magnitude = 0.0

    for i in range(1, len(ratios)):
        if ratios[i] is None or ratios[i - 1] is None:
            current_streak_len = 0
            current_streak_magnitude = 0.0
            continue
        if ratios[i] < ratios[i - 1]:  # type: ignore[operator]
            current_streak_len += 1
            current_streak_magnitude += ratios[i - 1] - ratios[i]  # type: ignore[operator]
            if current_streak_len >= 2:
                best_streak_magnitude = max(best_streak_magnitude, current_streak_magnitude)
        else:
            current_streak_len = 0
            current_streak_magnitude = 0.0

    # Check the final streak (may not have been "closed" by a non-decline)
    if current_streak_len >= 2:
        best_streak_magnitude = max(best_streak_magnitude, current_streak_magnitude)

    if best_streak_magnitude == 0.0:
        return 0.0

    return min(best_streak_magnitude / _OPEX_SCALE, _OPEX_CAP)


def _estimate_fcf(period: FinancialPeriod) -> float:
    """Estimate FCF = net_income + depreciation."""
    income = period.current_income
    net_income = float(income.net_income)
    depreciation = float(income.depreciation) if income.depreciation is not None else 0.0
    return net_income + depreciation


def fcf_crossover_score(history: FinancialHistory) -> float:
    """Compute FCF crossover score (0-3).

    Detects when a company transitions from sustained negative FCF to positive.
    Requires last 2 periods positive FCF and at least 1 prior negative period.
    Score = min(prior_negative_streak_length, 3.0).
    """
    periods = history.periods
    if len(periods) < 2:
        return 0.0

    fcf_values = [_estimate_fcf(p) for p in periods]

    # Last 2 periods must both be positive
    if fcf_values[-1] <= 0.0 or fcf_values[-2] <= 0.0:
        return 0.0

    # Count consecutive negatives just before the two positive periods
    negative_streak = 0
    for i in range(len(fcf_values) - 3, -1, -1):
        if fcf_values[i] < 0.0:
            negative_streak += 1
        else:
            break

    if negative_streak == 0:
        return 0.0

    return min(float(negative_streak), _FCF_CAP)


def margin_expansion_score(history: FinancialHistory) -> float:
    """Compute margin expansion score (0-3).

    Uses gross_margin = gross_profit / revenue (@property on IncomeStatement).
    Requires 2+ consecutive expansions and proximity to all-time high (within 200bps).
    Score = proximity_factor * consistency * 3.0, capped at 3.0.

    proximity_factor: 1.0 if at or above ATH, scales down linearly for larger gaps.
                      0.0 if gap > ATH_PROXIMITY_THRESHOLD (200 bps).
    consistency: fraction of consecutive expansion periods to total transition periods.
    """
    periods = history.periods
    if len(periods) < 2:
        return 0.0

    margins = [p.current_income.gross_margin for p in periods]

    # Count consecutive expansions ending at the latest period
    consecutive_expansions = 0
    for i in range(len(margins) - 1, 0, -1):
        if margins[i] > margins[i - 1]:
            consecutive_expansions += 1
        else:
            break

    if consecutive_expansions < 2:
        return 0.0

    # Compute ATH proximity
    all_time_high = max(margins)
    latest_margin = margins[-1]
    gap = all_time_high - latest_margin  # gap in decimal (e.g., 0.02 = 200bps)

    if gap > _ATH_PROXIMITY_THRESHOLD:
        proximity_factor = 0.0
    else:
        # Linear scale: 1.0 at gap=0, 0.0 at gap=200bps
        proximity_factor = 1.0 - (gap / _ATH_PROXIMITY_THRESHOLD)

    if proximity_factor == 0.0:
        return 0.0

    # Consistency: fraction of eligible periods that expanded
    total_transitions = len(margins) - 1
    consistency = consecutive_expansions / total_transitions if total_transitions > 0 else 0.0

    raw = proximity_factor * consistency * _MARGIN_CAP
    return min(raw, _MARGIN_CAP)


def inflection_score(history: FinancialHistory) -> FactorScore:
    """Compute composite inflection detection score (0-10 scale).

    Combines:
    - opex_deleverage_score (0-4)
    - fcf_crossover_score (0-3)
    - margin_expansion_score (0-3)

    Metadata:
    - opex_deleverage_detected (bool)
    - fcf_crossover_detected (bool)
    - margin_expansion_magnitude (float)
    - periods_since_inflection (int, placeholder = 0)
    """
    opex = opex_deleverage_score(history)
    fcf = fcf_crossover_score(history)
    margin = margin_expansion_score(history)

    raw = min(opex + fcf + margin, _COMPOSITE_CAP)

    # Compute margin expansion magnitude for metadata
    periods = history.periods
    margin_magnitude = 0.0
    if len(periods) >= 2:
        margins = [p.current_income.gross_margin for p in periods]
        if margins[-1] > margins[-2]:
            margin_magnitude = float(margins[-1] - margins[-2])

    metadata: dict[str, bool | float | int] = {
        "opex_deleverage_detected": opex > 0.0,
        "fcf_crossover_detected": fcf > 0.0,
        "margin_expansion_magnitude": margin_magnitude,
        "periods_since_inflection": 0,  # placeholder
    }

    # detail string
    parts = []
    if opex > 0.0:
        parts.append(f"opex_deleverage={opex:.2f}")
    if fcf > 0.0:
        parts.append(f"fcf_crossover={fcf:.2f}")
    if margin > 0.0:
        parts.append(f"margin_expansion={margin:.2f}")
    detail = "; ".join(parts) if parts else "no inflection signals detected"

    return FactorScore(
        name="inflection_detection",
        raw_value=raw,
        percentile_rank=0.0,
        detail=detail,
        metadata=metadata,
    )
