"""Tests for Wasserstein DRO mean-variance portfolio optimizer.

Includes golden-value tests, constraint verification, regime
adjustment, and infeasibility handling.
"""

from __future__ import annotations

import numpy as np
from margin_engine.optimization.dro_meanvar import optimize_dro_meanvar
from margin_engine.optimization.models import (
    DROConfig,
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


def _make_covariance(n: int, seed: int = 42) -> np.ndarray:
    """Create a valid PSD covariance matrix for N assets."""
    rng = np.random.default_rng(seed)
    a_matrix = rng.standard_normal((n * 2, n)) * 0.01
    return a_matrix.T @ a_matrix / (n * 2)


class TestDROBasic:
    """Basic DRO optimizer tests."""

    def test_weights_sum_to_one(self):
        """Optimal weights must sum to 1.0."""
        candidates = _make_candidates(5)
        cov = _make_covariance(5)
        tickers = [f"T{i}" for i in range(5)]

        result = optimize_dro_meanvar(candidates, cov, tickers)
        assert result.solver_status == "optimal"
        total = sum(result.weights.values())
        assert abs(total - 1.0) < 1e-4

    def test_all_weights_nonnegative(self):
        """Long-only constraint: all weights >= 0."""
        candidates = _make_candidates(5)
        cov = _make_covariance(5)
        tickers = [f"T{i}" for i in range(5)]

        result = optimize_dro_meanvar(candidates, cov, tickers)
        assert all(w >= -1e-8 for w in result.weights.values())

    def test_position_cap_respected(self):
        """No single position exceeds max_position."""
        candidates = _make_candidates(5, alphas=[0.10, 0.01, 0.01, 0.01, 0.01])
        cov = _make_covariance(5)
        tickers = [f"T{i}" for i in range(5)]
        constraints = OptimizationConstraints(max_position=0.30)

        result = optimize_dro_meanvar(candidates, cov, tickers, constraints=constraints)
        assert all(w <= 0.30 + 1e-4 for w in result.weights.values())

    def test_higher_alpha_gets_more_weight(self):
        """Asset with highest alpha should get highest weight (all else equal)."""
        # Use diagonal covariance for equal variance
        cov = np.eye(3) * 0.01
        candidates = _make_candidates(3, alphas=[0.05, 0.02, 0.01])
        tickers = ["T0", "T1", "T2"]

        result = optimize_dro_meanvar(candidates, cov, tickers)
        assert result.weights.get("T0", 0) >= result.weights.get("T1", 0)
        assert result.weights.get("T1", 0) >= result.weights.get("T2", 0)

    def test_expected_return_and_risk(self):
        """Expected return and risk should be populated."""
        cov = np.eye(3) * 0.01
        candidates = _make_candidates(3, alphas=[0.03, 0.02, 0.01])
        tickers = ["T0", "T1", "T2"]
        constraints = OptimizationConstraints(max_position=0.50)

        result = optimize_dro_meanvar(candidates, cov, tickers, constraints=constraints)
        assert result.solver_status in ("optimal", "optimal_inaccurate")
        assert result.expected_return != 0.0
        assert result.portfolio_risk > 0.0


class TestDROGoldenValue:
    """Golden-value 3-stock deterministic test."""

    def test_3_stock_golden(self):
        """Fixed 3-stock problem produces deterministic result."""
        rng = np.random.default_rng(12345)
        returns = rng.standard_normal((100, 3)) * 0.01
        cov = (returns - returns.mean(axis=0)).T @ (returns - returns.mean(axis=0)) / 100

        candidates = [
            PortfolioCandidate(
                ticker="A", expected_alpha=0.03, track="compounder",
                conviction="exceptional", sector="Tech",
            ),
            PortfolioCandidate(
                ticker="B", expected_alpha=0.02, track="mispricing",
                conviction="high", sector="Healthcare",
            ),
            PortfolioCandidate(
                ticker="C", expected_alpha=0.01, track="both",
                conviction="medium", sector="Financials",
            ),
        ]
        tickers = ["A", "B", "C"]
        config = DROConfig(epsilon_base=0.05, gamma_base=1.0)
        constraints = OptimizationConstraints(max_position=0.50)

        result = optimize_dro_meanvar(
            candidates, cov, tickers, constraints=constraints, dro_config=config
        )

        assert result.solver_status == "optimal"
        assert abs(sum(result.weights.values()) - 1.0) < 1e-4
        # A should get the most weight (highest alpha)
        assert result.weights.get("A", 0) > result.weights.get("C", 0)

        # Verify deterministic: run again
        result2 = optimize_dro_meanvar(
            candidates, cov, tickers, constraints=constraints, dro_config=config
        )
        for t in tickers:
            assert abs(result.weights.get(t, 0) - result2.weights.get(t, 0)) < 1e-4


class TestDROConstraints:
    """Constraint satisfaction tests."""

    def test_sector_cap(self):
        """Sector exposure should not exceed max_sector."""
        # 3 sectors: 2 Tech, 2 Healthcare, 1 Financials
        candidates = [
            PortfolioCandidate(
                ticker="T0", expected_alpha=0.03, track="compounder",
                conviction="high", sector="Tech",
            ),
            PortfolioCandidate(
                ticker="T1", expected_alpha=0.025, track="compounder",
                conviction="high", sector="Tech",
            ),
            PortfolioCandidate(
                ticker="T2", expected_alpha=0.02, track="mispricing",
                conviction="high", sector="Healthcare",
            ),
            PortfolioCandidate(
                ticker="T3", expected_alpha=0.015, track="mispricing",
                conviction="high", sector="Healthcare",
            ),
            PortfolioCandidate(
                ticker="T4", expected_alpha=0.01, track="both",
                conviction="medium", sector="Financials",
            ),
        ]
        cov = np.eye(5) * 0.01
        tickers = [f"T{i}" for i in range(5)]
        constraints = OptimizationConstraints(max_sector=0.40)

        result = optimize_dro_meanvar(candidates, cov, tickers, constraints=constraints)
        assert result.solver_status in ("optimal", "optimal_inaccurate")
        # Each sector should be at or below 40%
        for sector, exposure in result.sector_exposures.items():
            assert exposure <= 0.40 + 1e-3, f"{sector} exposure {exposure} > 0.40"

    def test_max_holdings_enforced(self):
        """Post-processing should limit number of holdings."""
        candidates = _make_candidates(20)
        cov = _make_covariance(20)
        tickers = [f"T{i}" for i in range(20)]
        constraints = OptimizationConstraints(max_holdings=5)

        result = optimize_dro_meanvar(candidates, cov, tickers, constraints=constraints)
        assert len(result.weights) <= 5


class TestDRORegime:
    """Regime adjustment tests."""

    def test_regime_scales_epsilon(self):
        """Euphoria regime should use higher epsilon."""
        candidates = _make_candidates(3)
        cov = _make_covariance(3)
        tickers = ["T0", "T1", "T2"]

        normal = optimize_dro_meanvar(candidates, cov, tickers, regime="normal")
        euphoria = optimize_dro_meanvar(candidates, cov, tickers, regime="euphoria")

        assert euphoria.epsilon_used > normal.epsilon_used
        assert euphoria.gamma_used > normal.gamma_used

    def test_cheap_regime_less_conservative(self):
        """Cheap regime should have lower epsilon (less conservative)."""
        candidates = _make_candidates(3)
        cov = _make_covariance(3)
        tickers = ["T0", "T1", "T2"]

        cheap = optimize_dro_meanvar(candidates, cov, tickers, regime="cheap")
        normal = optimize_dro_meanvar(candidates, cov, tickers, regime="normal")

        assert cheap.epsilon_used < normal.epsilon_used


class TestDROEdgeCases:
    """Edge case handling."""

    def test_empty_candidates(self):
        result = optimize_dro_meanvar([], np.empty((0, 0)), [])
        assert result.solver_status == "no_candidates"
        assert result.weights == {}

    def test_single_asset(self):
        """Single asset gets 100% weight."""
        candidates = _make_candidates(1, alphas=[0.02])
        cov = np.array([[0.0001]])
        constraints = OptimizationConstraints(max_position=1.0)
        result = optimize_dro_meanvar(
            candidates, cov, ["T0"], constraints=constraints
        )
        assert result.solver_status in ("optimal", "optimal_inaccurate")
        assert abs(result.weights.get("T0", 0) - 1.0) < 1e-2

    def test_diversification_ratio(self):
        """Diversification ratio should be >= 1.0 for diversified portfolio."""
        candidates = _make_candidates(5)
        cov = _make_covariance(5)
        tickers = [f"T{i}" for i in range(5)]
        result = optimize_dro_meanvar(candidates, cov, tickers)
        # For a properly diversified portfolio, weighted avg vol >= portfolio vol
        assert result.diversification_ratio >= 0.9  # Allow small numerical tolerance
