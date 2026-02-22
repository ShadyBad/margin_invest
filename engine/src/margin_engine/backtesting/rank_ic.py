"""Rank Information Coefficient (IC) measurement for scoring signals.

Computes the Spearman rank correlation between predicted scores
and realized forward returns, providing a key metric for signal quality.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel
from scipy.stats import spearmanr


class RankICReport(BaseModel):
    """Rank IC statistics over the backtest period."""

    ic_mean: float  # Average IC across periods
    ic_std: float  # IC standard deviation
    ic_ir: float  # IC Information Ratio = ic_mean / ic_std
    hit_rate: float  # Fraction of periods with positive IC
    n_periods: int  # Number of periods measured
    ic_series: list[float]  # IC per period


def compute_rank_ic(predicted: np.ndarray, realized: np.ndarray) -> float:
    """Compute Spearman rank correlation between predicted and realized.

    Args:
        predicted: Predicted scores/alphas for N assets.
        realized: Realized forward returns for N assets.

    Returns:
        Spearman rank correlation coefficient (float in [-1, 1]).
        Returns 0.0 if fewer than 3 observations.
    """
    if len(predicted) < 3 or len(realized) < 3:
        return 0.0
    corr, _ = spearmanr(predicted, realized)
    if np.isnan(corr):
        return 0.0
    return float(corr)


def compute_rank_ic_report(ic_series: list[float]) -> RankICReport:
    """Build a RankICReport from a series of per-period IC values.

    Args:
        ic_series: List of IC values, one per rebalance period.

    Returns:
        RankICReport with mean, std, IR, and hit rate.
    """
    if not ic_series:
        return RankICReport(
            ic_mean=0.0,
            ic_std=0.0,
            ic_ir=0.0,
            hit_rate=0.0,
            n_periods=0,
            ic_series=[],
        )

    arr = np.array(ic_series)
    mean_ic = float(np.mean(arr))
    std_ic = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    ir = mean_ic / std_ic if std_ic > 1e-10 else 0.0
    hit = float(np.mean(arr > 0))

    return RankICReport(
        ic_mean=mean_ic,
        ic_std=std_ic,
        ic_ir=ir,
        hit_rate=hit,
        n_periods=len(ic_series),
        ic_series=ic_series,
    )
