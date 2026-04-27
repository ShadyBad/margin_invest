"""Component attribution: tercile spread + rank-IC + bootstrap CI + Holm-Bonferroni."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

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
