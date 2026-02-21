"""Multi-Horizon Momentum — blended 3/6/12-month price momentum.

Replaces single 12-1 month momentum with a weighted blend:
- 3-month (short-term): 0.30 weight
- 6-month (medium-term): 0.40 weight
- 12-1 month (long-term): 0.30 weight

All horizons exclude the most recent month (mean-reversion avoidance).
Requires >= 100 days of price data.
"""

from __future__ import annotations

import datetime

from margin_engine.models.financial import PriceBar
from margin_engine.models.scoring import FactorScore

_MIN_HISTORY_DAYS = 100
_T1_DAYS = 30    # 1 month (excluded)
_T3_DAYS = 91    # 3 months
_T6_DAYS = 182   # 6 months
_T12_DAYS = 365  # 12 months

_W_SHORT = 0.30
_W_MEDIUM = 0.40
_W_LONG = 0.30


def _closest_index(dates: list[datetime.date], target: datetime.date) -> int:
    best_idx = 0
    best_diff = abs((dates[0] - target).days)
    for i, d in enumerate(dates):
        diff = abs((d - target).days)
        if diff < best_diff:
            best_diff = diff
            best_idx = i
    return best_idx


def _horizon_return(
    sorted_bars: list[PriceBar],
    dates: list[datetime.date],
    most_recent: datetime.date,
    near_days: int,
    far_days: int,
) -> float | None:
    """Compute return from far_days ago to near_days ago."""
    target_near = most_recent - datetime.timedelta(days=near_days)
    target_far = most_recent - datetime.timedelta(days=far_days)

    idx_near = _closest_index(dates, target_near)
    idx_far = _closest_index(dates, target_far)

    price_near = float(sorted_bars[idx_near].close)
    price_far = float(sorted_bars[idx_far].close)

    if price_far == 0.0:
        return None
    return (price_near / price_far) - 1.0


def multi_horizon_momentum(price_bars: list[PriceBar]) -> FactorScore:
    """Compute blended 3/6/12-month momentum (excluding last month)."""
    if len(price_bars) < 2:
        return FactorScore(
            name="multi_horizon_momentum", raw_value=0.0, percentile_rank=0.0,
            detail="Insufficient data",
        )

    sorted_bars = sorted(price_bars, key=lambda b: b.date)
    dates = [datetime.date.fromisoformat(b.date) for b in sorted_bars]
    span = (dates[-1] - dates[0]).days

    if span < _MIN_HISTORY_DAYS:
        return FactorScore(
            name="multi_horizon_momentum", raw_value=0.0, percentile_rank=0.0,
            detail=f"Insufficient history: {span} days (need {_MIN_HISTORY_DAYS})",
        )

    most_recent = dates[-1]
    horizons: list[tuple[str, float, float]] = []

    r3 = _horizon_return(sorted_bars, dates, most_recent, _T1_DAYS, _T3_DAYS)
    if r3 is not None and span >= _T3_DAYS:
        horizons.append(("3mo", _W_SHORT, r3))

    r6 = _horizon_return(sorted_bars, dates, most_recent, _T1_DAYS, _T6_DAYS)
    if r6 is not None and span >= _T6_DAYS:
        horizons.append(("6mo", _W_MEDIUM, r6))

    r12 = _horizon_return(sorted_bars, dates, most_recent, _T1_DAYS, _T12_DAYS)
    if r12 is not None and span >= _T12_DAYS:
        horizons.append(("12mo", _W_LONG, r12))

    if not horizons:
        return FactorScore(
            name="multi_horizon_momentum", raw_value=0.0, percentile_rank=0.0,
            detail="No valid horizons computable",
        )

    total_weight = sum(w for _, w, _ in horizons)
    blended = sum(w * r / total_weight for _, w, r in horizons)

    detail_parts = [f"{name}={r:.4f}" for name, _, r in horizons]
    return FactorScore(
        name="multi_horizon_momentum", raw_value=blended, percentile_rank=0.0,
        detail=f"blended={blended:.4f} ({', '.join(detail_parts)})",
    )
