"""Anti-Mediocrity Gate — pre-scoring filter removing businesses not worth evaluating.

Thresholds:
    - 5yr median ROIC > 8%
    - Gross margin > 20% (sector-adjusted: Utilities > 10%, Energy > 15%)
    - Positive FCF in 4 of last 5 years
    - Revenue not declining 3+ consecutive years

Trajectory overrides (conditional pass):
    When the static gate fails, 4 trajectory conditions can trigger a conditional pass:
    1. ROIC improving 200bps+/quarter for 3 consecutive quarters
    2. GM within 3% of sector threshold AND expanding 300bps+/year
    3. FCF positive in most recent 2 quarters after negative priors
    4. TURNAROUND or HIGH_GROWTH stage with any positive ROIC trajectory
"""

from __future__ import annotations

import math
import statistics
from decimal import Decimal

from margin_engine.config.v3_scoring_config import MediocracyTrajectoryConfig
from margin_engine.models.financial import FinancialHistory, FinancialPeriod, GICSSector
from margin_engine.models.scoring import FilterResult, GrowthStage

_ROIC_THRESHOLD = 0.08
_DEFAULT_GM_THRESHOLD = 0.20
_UTILITIES_GM_THRESHOLD = 0.10
_ENERGY_GM_THRESHOLD = 0.15
_MIN_FCF_POSITIVE_YEARS = 4
_MAX_REVENUE_DECLINE_YEARS = 3
_FLOAT_EPS = 1e-9  # Tolerance for floating-point comparisons


def _sector_gm_threshold(sector: GICSSector) -> float:
    if sector == GICSSector.UTILITIES:
        return _UTILITIES_GM_THRESHOLD
    if sector == GICSSector.ENERGY:
        return _ENERGY_GM_THRESHOLD
    return _DEFAULT_GM_THRESHOLD


def _compute_roic(period: FinancialPeriod) -> float | None:
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


def _filter_finite(series: list[float] | None) -> list[float]:
    """Filter a quarterly series, removing NaN and Inf values."""
    if series is None:
        return []
    return [v for v in series if math.isfinite(v)]


def _check_roic_trajectory(
    roic_q: list[float],
    config: MediocracyTrajectoryConfig,
) -> bool:
    """Check if ROIC improved by min_delta_per_quarter for min_consecutive quarters."""
    if len(roic_q) < config.roic_min_consecutive + 1:
        return False
    consecutive = 0
    for i in range(1, len(roic_q)):
        delta = roic_q[i] - roic_q[i - 1]
        if delta >= config.roic_min_delta_per_quarter - _FLOAT_EPS:
            consecutive += 1
            if consecutive >= config.roic_min_consecutive:
                return True
        else:
            consecutive = 0
    return False


def _check_gm_approaching(
    gm_q: list[float],
    sector: GICSSector,
    config: MediocracyTrajectoryConfig,
) -> bool:
    """Check if GM is within approaching_distance of threshold AND expanding enough."""
    if len(gm_q) < 4:
        return False
    gm_threshold = _sector_gm_threshold(sector)
    most_recent = gm_q[-1]
    # Most recent GM must be within approaching_distance of the threshold
    if most_recent < gm_threshold - config.gm_approaching_distance:
        return False
    # Already above threshold doesn't count as "approaching"
    if most_recent > gm_threshold:
        return False
    # Calculate annualized expansion: (last - first) / (num_quarters / 4)
    n_quarters = len(gm_q)
    years_span = n_quarters / 4.0
    if years_span <= 0:
        return False
    annual_expansion = (gm_q[-1] - gm_q[0]) / years_span
    return annual_expansion >= config.gm_min_annual_expansion - _FLOAT_EPS


def _check_fcf_inflection(
    fcf_q: list[float],
    config: MediocracyTrajectoryConfig,
) -> bool:
    """Check if FCF turned positive in most recent N quarters after being negative."""
    if len(fcf_q) < config.fcf_positive_recent_quarters + 1:
        return False
    recent = fcf_q[-config.fcf_positive_recent_quarters :]
    prior = fcf_q[: -config.fcf_positive_recent_quarters]
    # All recent quarters must be positive
    if not all(v > 0 for v in recent):
        return False
    # At least one prior quarter must be negative (proves inflection)
    return any(v < 0 for v in prior)


def _check_growth_stage_override(
    roic_q: list[float],
    growth_stage: GrowthStage | None,
    config: MediocracyTrajectoryConfig,
) -> bool:
    """Check if growth stage qualifies for override with any positive ROIC trajectory."""
    if growth_stage is None or len(roic_q) < 2:
        return False
    allowed = {s.lower() for s in config.trajectory_stages}
    if growth_stage.value.lower() not in allowed:
        return False
    # Any positive trajectory: most recent > earliest
    return roic_q[-1] > roic_q[0]


def mediocrity_gate(
    history: FinancialHistory,
    sector: GICSSector,
    roic_quarterly: list[float] | None = None,
    gm_quarterly: list[float] | None = None,
    fcf_quarterly: list[float] | None = None,
    growth_stage: GrowthStage | None = None,
    config: MediocracyTrajectoryConfig | None = None,
) -> FilterResult:
    """Run anti-mediocrity gate. Returns FilterResult (passed=True/False).

    When the static gate fails but a trajectory condition fires, returns
    FilterResult(passed=False, conditional=True) with conditional_score_multiplier
    in computed_metrics.
    """
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

    # If static gate passed, no need for trajectory override
    if passed:
        return FilterResult(
            name="mediocrity_gate",
            passed=True,
            detail=detail,
        )

    # --- Trajectory override check ---
    cfg = config or MediocracyTrajectoryConfig()
    roic_q = _filter_finite(roic_quarterly)
    gm_q = _filter_finite(gm_quarterly)
    fcf_q = _filter_finite(fcf_quarterly)

    trajectory_reasons: list[str] = []

    if _check_roic_trajectory(roic_q, cfg):
        trajectory_reasons.append("roic_trajectory")

    if _check_gm_approaching(gm_q, sector, cfg):
        trajectory_reasons.append("gm_approaching")

    if _check_fcf_inflection(fcf_q, cfg):
        trajectory_reasons.append("fcf_inflection")

    if _check_growth_stage_override(roic_q, growth_stage, cfg):
        trajectory_reasons.append("growth_stage_override")

    if trajectory_reasons:
        return FilterResult(
            name="mediocrity_gate",
            passed=False,
            conditional=True,
            detail=f"{detail} [trajectory override: {', '.join(trajectory_reasons)}]",
            computed_metrics={
                "conditional_score_multiplier": cfg.conditional_score_multiplier,
                "trajectory_reasons": ", ".join(trajectory_reasons),
            },
        )

    return FilterResult(
        name="mediocrity_gate",
        passed=False,
        detail=detail,
    )
