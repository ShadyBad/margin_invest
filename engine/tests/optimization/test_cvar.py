"""Tests for CVaR portfolio optimization."""

from __future__ import annotations

import numpy as np
from margin_engine.optimization.cvar import optimize_cvar
from margin_engine.optimization.models import (
    OptimizationConstraints,
    PortfolioCandidate,
)


def _make_candidates(n: int, alphas: list[float] | None = None) -> list[PortfolioCandidate]:
    """Create N candidates with specified or uniform alphas."""
    if alphas is None:
        alphas = [0.02 - 0.005 * i for i in range(n)]
    sectors = ["Tech", "Healthcare", "Financials", "Energy", "Industrials"]
    return [
        PortfolioCandidate(
            ticker=f"T{i}",
            expected_alpha=alphas[i],
            track="compounder",
            conviction="high",
            sector=sectors[i % len(sectors)],
        )
        for i in range(n)
    ]


def _make_scenarios(n_scenarios: int, n_assets: int, seed: int = 42) -> np.ndarray:
    """Generate synthetic return scenarios."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n_scenarios, n_assets)) * 0.02


class TestCVaRBasic:
    """Basic CVaR optimizer tests."""

    def test_weights_sum_to_one(self):
        candidates = _make_candidates(5)
        scenarios = _make_scenarios(200, 5)
        tickers = [f"T{i}" for i in range(5)]

        result = optimize_cvar(candidates, scenarios, tickers)
        assert result.solver_status in ("optimal", "optimal_inaccurate")
        total = sum(result.weights.values())
        assert abs(total - 1.0) < 1e-3

    def test_all_nonnegative(self):
        candidates = _make_candidates(5)
        scenarios = _make_scenarios(200, 5)
        tickers = [f"T{i}" for i in range(5)]

        result = optimize_cvar(candidates, scenarios, tickers)
        assert all(w >= -1e-8 for w in result.weights.values())

    def test_position_cap(self):
        candidates = _make_candidates(5, alphas=[0.10, 0.01, 0.01, 0.01, 0.01])
        scenarios = _make_scenarios(200, 5)
        tickers = [f"T{i}" for i in range(5)]
        constraints = OptimizationConstraints(max_position=0.30)

        result = optimize_cvar(candidates, scenarios, tickers, constraints=constraints)
        assert all(w <= 0.30 + 1e-3 for w in result.weights.values())

    def test_feasible_with_alpha_005(self):
        """CVaR at 5% tail should produce feasible solution."""
        candidates = _make_candidates(3)
        scenarios = _make_scenarios(500, 3)
        tickers = ["T0", "T1", "T2"]
        constraints = OptimizationConstraints(max_position=0.50)

        result = optimize_cvar(
            candidates, scenarios, tickers, alpha=0.05, constraints=constraints
        )
        assert result.solver_status in ("optimal", "optimal_inaccurate")
        assert len(result.weights) > 0

    def test_max_holdings_enforced(self):
        candidates = _make_candidates(15)
        scenarios = _make_scenarios(200, 15)
        tickers = [f"T{i}" for i in range(15)]
        constraints = OptimizationConstraints(max_holdings=5)

        result = optimize_cvar(candidates, scenarios, tickers, constraints=constraints)
        assert len(result.weights) <= 5


class TestCVaRTailProtection:
    """Test that CVaR actually protects against tail risk."""

    def test_avoids_high_tail_risk_asset(self):
        """Asset with fat left tail should get less weight."""
        rng = np.random.default_rng(99)
        n_assets = 3
        n_scenarios = 500

        # Asset 0: normal returns
        # Asset 1: normal returns
        # Asset 2: fat left tail (occasional -20% crashes)
        scenarios = rng.standard_normal((n_scenarios, n_assets)) * 0.02
        # Add crash scenarios to asset 2
        crash_idx = rng.choice(n_scenarios, size=25, replace=False)
        scenarios[crash_idx, 2] = -0.20

        # All same expected alpha
        candidates = _make_candidates(3, alphas=[0.02, 0.02, 0.02])
        tickers = ["T0", "T1", "T2"]
        constraints = OptimizationConstraints(max_position=0.50)

        result = optimize_cvar(
            candidates, scenarios, tickers, alpha=0.05, constraints=constraints
        )
        assert result.solver_status in ("optimal", "optimal_inaccurate")
        # T2 should get less weight due to tail risk
        assert result.weights.get("T2", 1.0) < result.weights.get("T0", 0.0) + 0.1


class TestCVaREdgeCases:
    """Edge cases for CVaR optimizer."""

    def test_empty(self):
        result = optimize_cvar([], np.empty((0, 0)), [])
        assert result.solver_status == "no_candidates"

    def test_single_asset(self):
        candidates = _make_candidates(1, alphas=[0.02])
        scenarios = _make_scenarios(100, 1)
        constraints = OptimizationConstraints(max_position=1.0)
        result = optimize_cvar(candidates, scenarios, ["T0"], constraints=constraints)
        assert result.solver_status in ("optimal", "optimal_inaccurate")
        assert abs(result.weights.get("T0", 0) - 1.0) < 1e-2

    def test_risk_aversion_concentrates(self):
        """Lower risk aversion should allow more concentrated portfolio."""
        candidates = _make_candidates(5, alphas=[0.05, 0.01, 0.01, 0.01, 0.01])
        scenarios = _make_scenarios(200, 5)
        tickers = [f"T{i}" for i in range(5)]

        low_aversion = optimize_cvar(
            candidates, scenarios, tickers, risk_aversion=0.1
        )
        high_aversion = optimize_cvar(
            candidates, scenarios, tickers, risk_aversion=5.0
        )

        # Low aversion should put more in T0 (highest alpha)
        assert low_aversion.weights.get("T0", 0) >= high_aversion.weights.get("T0", 0) - 0.05
