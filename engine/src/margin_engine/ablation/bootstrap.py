"""Block bootstrap confidence intervals and Sharpe ratio difference tests.

Implements the block bootstrap of Kunsch (1989) to preserve autocorrelation
structure in monthly return series. Used by the ablation study orchestrator
to produce confidence intervals on Sharpe ratio differences between filter
combinations.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from numpy.random import Generator
from pydantic import BaseModel


class SharpeDifferenceResult(BaseModel):
    """Result of a paired block bootstrap test for Sharpe ratio difference."""

    point_estimate: float
    ci_low: float
    ci_high: float
    p_value: float
    significant: bool
    n_resamples: int


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _block_indices(n: int, block_size: int, rng: Generator) -> np.ndarray:
    """Generate block bootstrap index array of length *n*.

    Draws ceil(n / block_size) random start positions and builds contiguous
    blocks of *block_size* indices, wrapping around via modulo. The result is
    truncated to exactly *n* indices.
    """
    n_blocks = int(np.ceil(n / block_size))
    starts = rng.integers(0, n, size=n_blocks)
    indices = np.concatenate([(start + np.arange(block_size)) % n for start in starts])
    return indices[:n]


def _draw_block_sample(data: np.ndarray, block_size: int, rng: Generator) -> np.ndarray:
    """Draw a single block-bootstrap resample from *data*."""
    idx = _block_indices(len(data), block_size, rng)
    return data[idx]


def _compute_statistic(sample: np.ndarray, statistic: Literal["mean", "median", "std"]) -> float:
    """Compute a scalar summary statistic on *sample*."""
    if statistic == "mean":
        return float(np.mean(sample))
    if statistic == "median":
        return float(np.median(sample))
    if statistic == "std":
        return float(np.std(sample, ddof=1))
    msg = f"Unknown statistic: {statistic!r}"
    raise ValueError(msg)


def _annualized_sharpe(monthly_returns: np.ndarray, risk_free_annual: float) -> float:
    """Annualized Sharpe ratio from monthly excess returns.

    Sharpe = mean(excess) / std(excess, ddof=1) * sqrt(12)
    """
    risk_free_monthly = risk_free_annual / 12.0
    excess = monthly_returns - risk_free_monthly
    std = float(np.std(excess, ddof=1))
    if std == 0.0:
        return 0.0
    return float(np.mean(excess)) / std * np.sqrt(12.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def block_bootstrap_ci(
    data: np.ndarray | list[float],
    statistic: Literal["mean", "median", "std"] = "mean",
    alpha: float = 0.05,
    n_resamples: int = 10_000,
    block_size: int = 3,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Block bootstrap confidence interval (Kunsch 1989).

    Parameters
    ----------
    data:
        1-D array of observations (e.g. monthly returns).
    statistic:
        Summary statistic — ``"mean"``, ``"median"``, or ``"std"``.
    alpha:
        Significance level. CI covers 1 - alpha probability.
    n_resamples:
        Number of bootstrap resamples.
    block_size:
        Contiguous block length to preserve autocorrelation.
    seed:
        Random seed for reproducibility.

    Returns
    -------
    (ci_low, point_estimate, ci_high)
    """
    arr = np.asarray(data, dtype=np.float64)
    rng = np.random.default_rng(seed)

    point = _compute_statistic(arr, statistic)

    boot_stats = np.empty(n_resamples)
    for i in range(n_resamples):
        sample = _draw_block_sample(arr, block_size, rng)
        boot_stats[i] = _compute_statistic(sample, statistic)

    ci_low = float(np.percentile(boot_stats, 100 * alpha / 2))
    ci_high = float(np.percentile(boot_stats, 100 * (1 - alpha / 2)))

    return (ci_low, point, ci_high)


def bootstrap_sharpe_difference(
    returns_a: np.ndarray | list[float],
    returns_b: np.ndarray | list[float],
    alpha: float = 0.05,
    n_resamples: int = 10_000,
    block_size: int = 3,
    risk_free_annual: float = 0.04,
    seed: int = 42,
) -> SharpeDifferenceResult:
    """Paired block bootstrap test for difference in annualized Sharpe ratios.

    The same block indices are applied to both series on each resample so that
    the pairing is preserved (same market conditions for both variants).

    Parameters
    ----------
    returns_a, returns_b:
        Monthly return series of equal length.
    alpha:
        Significance level.
    n_resamples:
        Number of bootstrap resamples.
    block_size:
        Contiguous block length.
    risk_free_annual:
        Annualized risk-free rate (default 4 %).
    seed:
        Random seed for reproducibility.

    Returns
    -------
    SharpeDifferenceResult with point estimate, CI, p-value and significance flag.
    """
    a = np.asarray(returns_a, dtype=np.float64)
    b = np.asarray(returns_b, dtype=np.float64)
    if len(a) != len(b):
        msg = f"Series must be equal length, got {len(a)} and {len(b)}"
        raise ValueError(msg)

    n = len(a)
    rng = np.random.default_rng(seed)

    # Point estimate
    sharpe_a = _annualized_sharpe(a, risk_free_annual)
    sharpe_b = _annualized_sharpe(b, risk_free_annual)
    point = sharpe_a - sharpe_b

    # Bootstrap distribution of Sharpe difference
    diffs = np.empty(n_resamples)
    for i in range(n_resamples):
        idx = _block_indices(n, block_size, rng)
        sa = _annualized_sharpe(a[idx], risk_free_annual)
        sb = _annualized_sharpe(b[idx], risk_free_annual)
        diffs[i] = sa - sb

    ci_low = float(np.percentile(diffs, 100 * alpha / 2))
    ci_high = float(np.percentile(diffs, 100 * (1 - alpha / 2)))

    # Two-sided p-value: proportion of resamples on the opposite side of zero
    # from the point estimate (or spanning zero).
    if point >= 0:
        p_value = float(np.mean(diffs <= 0)) * 2
    else:
        p_value = float(np.mean(diffs >= 0)) * 2
    p_value = min(p_value, 1.0)

    significant = p_value < alpha

    return SharpeDifferenceResult(
        point_estimate=point,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
        significant=significant,
        n_resamples=n_resamples,
    )
