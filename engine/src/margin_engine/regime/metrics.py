"""Regime-segmented ablation metrics.

Segments ablation results by market regime and computes per-regime
performance metrics (Sharpe, max drawdown, win rate, etc.).
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from margin_engine.regime.models import RegimeState


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RegimePerformanceSlice(BaseModel):
    """Performance metrics for a single regime bucket."""

    model_config = ConfigDict(frozen=True)

    regime_key: str
    n_months: int
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    mean_return: float
    volatility: float
    mean_excess_return: float


class RegimeSegmentedMetrics(BaseModel):
    """Collection of performance slices keyed by regime."""

    slices: dict[str, RegimePerformanceSlice] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_DEFAULT_RF_MONTHLY: float = 0.04 / 12


def _compute_sharpe(
    returns: np.ndarray,
    risk_free_monthly: float = _DEFAULT_RF_MONTHLY,
) -> float:
    """Annualized Sharpe ratio from monthly returns.

    Returns 0.0 when fewer than 2 observations or zero standard deviation.
    """
    if len(returns) < 2:
        return 0.0
    excess = returns - risk_free_monthly
    std = float(np.std(excess, ddof=1))
    if std == 0.0:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(12))


def _compute_max_drawdown(returns: np.ndarray) -> float:
    """Maximum drawdown from a series of monthly returns.

    Computes from the cumulative product of ``(1 + r)``.
    Returns 0.0 for empty inputs or if the series never declines.
    """
    if len(returns) == 0:
        return 0.0

    cumulative = np.cumprod(1.0 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    min_dd = float(np.min(drawdowns))
    return min_dd if min_dd < 0.0 else 0.0


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def compute_regime_segmented_metrics(
    *,
    regime_tags: list[RegimeState],
    monthly_returns: list[float],
    benchmark_returns: list[float],
) -> RegimeSegmentedMetrics:
    """Segment ablation results by regime and compute per-regime metrics.

    Parameters
    ----------
    regime_tags:
        One ``RegimeState`` per month.
    monthly_returns:
        Portfolio monthly return per month.
    benchmark_returns:
        Benchmark monthly return per month.

    Returns
    -------
    RegimeSegmentedMetrics with one :class:`RegimePerformanceSlice` per
    distinct ``regime_key``.

    Raises
    ------
    ValueError
        If the three input lists are not the same length.
    """
    n = len(regime_tags)
    if len(monthly_returns) != n or len(benchmark_returns) != n:
        raise ValueError(
            f"regime_tags, monthly_returns, and benchmark_returns must be same length "
            f"(got {n}, {len(monthly_returns)}, {len(benchmark_returns)})"
        )

    if n == 0:
        return RegimeSegmentedMetrics()

    # Bucket indices by regime_key
    buckets: dict[str, list[int]] = defaultdict(list)
    for i, regime in enumerate(regime_tags):
        buckets[regime.regime_key].append(i)

    ret_arr = np.array(monthly_returns, dtype=np.float64)
    bench_arr = np.array(benchmark_returns, dtype=np.float64)

    slices: dict[str, RegimePerformanceSlice] = {}
    for key, indices in buckets.items():
        idx = np.array(indices)
        rets = ret_arr[idx]
        bench = bench_arr[idx]
        excess = rets - bench

        n_months = len(indices)
        sharpe = _compute_sharpe(rets)
        max_dd = _compute_max_drawdown(rets)
        win_rate = float(np.sum(excess > 0) / n_months) if n_months > 0 else 0.0
        mean_ret = float(np.mean(rets))
        vol = float(np.std(rets, ddof=1)) if n_months >= 2 else 0.0
        mean_excess = float(np.mean(excess))

        slices[key] = RegimePerformanceSlice(
            regime_key=key,
            n_months=n_months,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            win_rate=win_rate,
            mean_return=mean_ret,
            volatility=vol,
            mean_excess_return=mean_excess,
        )

    return RegimeSegmentedMetrics(slices=slices)
