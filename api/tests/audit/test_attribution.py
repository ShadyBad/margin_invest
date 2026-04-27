from __future__ import annotations

import numpy as np
from margin_api.audit.attribution import compute_tercile_spread


def _monotonic(n: int = 90, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    scores = rng.uniform(0, 100, n)
    alphas = scores * 0.001 + rng.normal(0, 0.005, n)
    return scores, alphas


def test_tercile_spread_monotonic_positive_spread() -> None:
    scores, alphas = _monotonic()
    result = compute_tercile_spread(scores, alphas)
    assert result.spread > 0.0
    assert result.n_top == 30
    assert result.n_bottom == 30


def test_tercile_spread_n_below_minimum_returns_none_spread() -> None:
    rng = np.random.default_rng(42)
    scores = rng.uniform(0, 100, 30)
    alphas = rng.normal(0, 0.01, 30)
    result = compute_tercile_spread(scores, alphas)
    assert result.spread is None
    assert result.underpowered is True


def test_tercile_spread_pure_noise_spread_near_zero() -> None:
    rng = np.random.default_rng(42)
    scores = rng.uniform(0, 100, 300)
    alphas = rng.normal(0, 0.01, 300)
    result = compute_tercile_spread(scores, alphas)
    assert result.spread is not None
    assert abs(result.spread) < 0.005
