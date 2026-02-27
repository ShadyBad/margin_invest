"""Regime-conditioned Shapley value computation.

Extends the standard Shapley value computation to produce per-regime values.
Coalition returns are fetched once and cached, then sliced per regime to compute
per-regime Sharpe ratios as the value function.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from itertools import combinations

from pydantic import BaseModel, Field

from margin_engine.ablation.shapley import ShapleyResult, compute_shapley_values


class RegimeShapleyResult(BaseModel):
    """Result of regime-conditioned Shapley value computation."""

    per_regime: dict[str, ShapleyResult] = Field(default_factory=dict)


def _sharpe_from_returns(
    returns: list[float],
    risk_free_monthly: float = 0.04 / 12,
) -> float:
    """Compute annualized Sharpe ratio from monthly returns.

    Returns 0.0 if fewer than 2 returns or if standard deviation is zero.
    """
    n = len(returns)
    if n < 2:
        return 0.0

    mean = sum(returns) / n
    mean_excess = mean - risk_free_monthly

    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    std = math.sqrt(variance)

    if std == 0.0:
        return 0.0

    return (mean_excess / std) * math.sqrt(12)


def compute_regime_conditioned_shapley(
    *,
    filters: list[str],
    coalition_returns_fn: Callable[[frozenset[str]], dict[str, list[float]]],
    regime_keys: list[str],
) -> RegimeShapleyResult:
    """Compute Shapley values conditioned on market regime.

    Parameters
    ----------
    filters:
        List of filter names.
    coalition_returns_fn:
        Takes a frozenset of filter names and returns a dict mapping
        regime_key -> list[float] of monthly returns for that coalition
        within that regime.
    regime_keys:
        List of regime keys to compute Shapley values for.

    Returns
    -------
    RegimeShapleyResult with per-regime ShapleyResult entries.
    """
    # Cache coalition returns: call coalition_returns_fn once per coalition
    n = len(filters)
    cached_returns: dict[frozenset[str], dict[str, list[float]]] = {}

    for size in range(n + 1):
        for combo in combinations(filters, size):
            coalition = frozenset(combo)
            cached_returns[coalition] = coalition_returns_fn(coalition)

    # For each regime, build a value function from the cached returns and compute Shapley
    per_regime: dict[str, ShapleyResult] = {}

    for regime_key in regime_keys:
        # Use default argument to capture regime_key correctly (avoid late binding)
        def value_fn(coalition: frozenset[str], _rk: str = regime_key) -> float:
            regime_returns = cached_returns[coalition][_rk]
            return _sharpe_from_returns(regime_returns)

        per_regime[regime_key] = compute_shapley_values(filters, value_fn)

    return RegimeShapleyResult(per_regime=per_regime)
