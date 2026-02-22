"""Publication bias adjustments for backtested returns.

Applies a decay haircut to backtested performance metrics to account for
data-snooping and overfitting bias. Also provides t-stat significance
testing for validating new signals during R&D.
"""

from __future__ import annotations

import math

from margin_engine.backtesting.models import PerformanceMetrics


def haircut_returns(
    metrics: PerformanceMetrics,
    decay_rate: float = 0.12,
) -> PerformanceMetrics:
    """Apply publication bias haircut to backtested returns.

    Reduces return-based metrics by decay_rate (default 12%) to account
    for look-ahead bias, data snooping, and overfitting in backtests.

    Args:
        metrics: Original backtest performance metrics.
        decay_rate: Fraction to haircut (0.12 = 12% reduction).

    Returns:
        New PerformanceMetrics with haircut applied to return metrics.
        Risk metrics (drawdown, turnover) and ratios are recomputed.
    """
    factor = 1.0 - decay_rate

    haircut_cagr = metrics.cagr * factor
    haircut_excess_cagr = metrics.excess_cagr * factor
    haircut_total_return = metrics.total_return * factor

    # Ratios scale proportionally (return scaled, vol unchanged)
    haircut_sharpe = metrics.sharpe_ratio * factor
    haircut_sortino = metrics.sortino_ratio * factor
    haircut_ir = metrics.information_ratio * factor

    return PerformanceMetrics(
        cagr=haircut_cagr,
        excess_cagr=haircut_excess_cagr,
        sharpe_ratio=haircut_sharpe,
        sortino_ratio=haircut_sortino,
        max_drawdown=metrics.max_drawdown,  # Drawdown unchanged
        win_rate=metrics.win_rate,  # Win rate unchanged
        information_ratio=haircut_ir,
        total_return=haircut_total_return,
        benchmark_total_return=metrics.benchmark_total_return,
        num_months=metrics.num_months,
        avg_turnover=metrics.avg_turnover,
    )


def signal_significance(
    ic: float,
    n_obs: int,
    threshold: float = 1.8,
) -> tuple[float, bool]:
    """Compute t-statistic for IC and check significance.

    Used during R&D to validate new signals. Not used in production pipeline.

    t = ic * sqrt(n_obs) (for Spearman rank correlation)

    Args:
        ic: Information Coefficient (Spearman correlation).
        n_obs: Number of observations (rebalance periods).
        threshold: t-stat threshold for significance (default 1.8).

    Returns:
        Tuple of (t_statistic, passes_threshold).
    """
    if n_obs < 2:
        return (0.0, False)

    t_stat = ic * math.sqrt(n_obs)
    return (t_stat, abs(t_stat) > threshold)
