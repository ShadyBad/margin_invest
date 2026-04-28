"""Component attribution: tercile spread + rank-IC + bootstrap CI + Holm-Bonferroni."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from margin_engine.backtesting.rank_ic import compute_rank_ic

from margin_api.audit.schema import AttributionVerdict

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


def holm_bonferroni(p_values: np.ndarray) -> np.ndarray:
    """Apply Holm-Bonferroni correction to p-values.

    Algorithm: sort p-values, multiply each by (m - rank), enforce monotonicity
    (running max), cap at 1.0, then unsort back to original order.
    """
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    if m == 0:
        return p.copy()
    order = np.argsort(p)
    sorted_p = p[order]
    corrected = np.empty(m, dtype=float)
    running_max = 0.0
    for rank, sp in enumerate(sorted_p):
        adj = (m - rank) * sp
        running_max = max(running_max, min(adj, 1.0))
        corrected[rank] = running_max
    out = np.empty(m, dtype=float)
    out[order] = corrected
    return out


@dataclass(frozen=True)
class AttributionInputs:
    """Inputs for verdict assignment logic."""

    spread: float | None
    rank_ic: float | None
    ci_lo: float
    ci_hi: float
    p_value_holm: float
    n_top: int | None
    n_bottom: int | None


def assign_verdict(inputs: AttributionInputs) -> AttributionVerdict:
    """Map attribution stats to keep/demote/cut/underpowered.

    Order matters (spec §8.5):
      1. UNDERPOWERED if n < 30 per tercile or bootstrap CI crosses zero.
      2. CUT if spread + rank-IC both negative AND p_value_holm <= 0.05.
      3. DEMOTE if signs differ between spread and rank-IC.
      4. KEEP if spread positive and significant.
      5. Default UNDERPOWERED.
    """
    if inputs.n_top is None or inputs.n_bottom is None:
        return AttributionVerdict.UNDERPOWERED
    if inputs.n_top < MIN_TERCILE_N or inputs.n_bottom < MIN_TERCILE_N:
        return AttributionVerdict.UNDERPOWERED
    if inputs.ci_lo <= 0.0 <= inputs.ci_hi:
        return AttributionVerdict.UNDERPOWERED
    if inputs.spread is None or inputs.rank_ic is None:
        return AttributionVerdict.UNDERPOWERED

    spread_negative = inputs.spread < 0
    ic_negative = inputs.rank_ic < 0
    significant = inputs.p_value_holm <= 0.05

    if spread_negative and ic_negative and significant:
        return AttributionVerdict.CUT
    if spread_negative != ic_negative:
        return AttributionVerdict.DEMOTE
    if not spread_negative and significant:
        return AttributionVerdict.KEEP
    return AttributionVerdict.UNDERPOWERED
