"""Component attribution: tercile spread + rank-IC + bootstrap CI + Holm-Bonferroni."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from margin_engine.backtesting.rank_ic import compute_rank_ic

MIN_TERCILE_N = 30


@dataclass(frozen=True)
class TercileSpreadResult:
    spread: float | None
    top_alpha: float
    bottom_alpha: float
    n_top: int
    n_bottom: int
    underpowered: bool


def compute_tercile_spread(
    component_scores: np.ndarray,
    forward_alphas: np.ndarray,
) -> TercileSpreadResult:
    if len(component_scores) != len(forward_alphas):
        raise ValueError("component_scores and forward_alphas must have equal length")
    n = len(component_scores)
    tercile = n // 3
    underpowered = tercile < MIN_TERCILE_N
    if tercile == 0:
        return TercileSpreadResult(None, 0.0, 0.0, 0, 0, True)
    order = np.argsort(component_scores)
    bottom = forward_alphas[order[:tercile]]
    top = forward_alphas[order[-tercile:]]
    top_alpha = float(np.mean(top))
    bottom_alpha = float(np.mean(bottom))
    spread = None if underpowered else top_alpha - bottom_alpha
    return TercileSpreadResult(
        spread=spread,
        top_alpha=top_alpha,
        bottom_alpha=bottom_alpha,
        n_top=tercile,
        n_bottom=tercile,
        underpowered=underpowered,
    )


def compute_rank_ic_attribution(
    component_scores: np.ndarray,
    forward_alphas: np.ndarray,
) -> float:
    if len(component_scores) != len(forward_alphas):
        raise ValueError("component_scores and forward_alphas must have equal length")
    return float(compute_rank_ic(component_scores, forward_alphas))


def bootstrap_ci(
    data: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(data)
    estimates = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        idx = rng.integers(0, n, n)
        estimates[i] = statistic(data[idx])
    alpha = (1.0 - confidence) / 2.0
    return float(np.quantile(estimates, alpha)), float(np.quantile(estimates, 1.0 - alpha))
