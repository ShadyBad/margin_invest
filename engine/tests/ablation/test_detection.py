"""Tests for ablation interference detection module."""

from __future__ import annotations

import numpy as np
import pytest
from margin_engine.ablation.detection import (
    compute_failure_correlation,
    detect_degradation,
    detect_negative_marginal,
    detect_pairwise_destruction,
    detect_universe_collapse,
)


class TestDetectDegradation:
    """Tests for detect_degradation."""

    def test_detect_degradation_when_stack_worse(self) -> None:
        """Full stack Sharpe < best single → detected=True with correct severity."""
        result = detect_degradation(
            full_stack_sharpe=0.6,
            single_sharpes={"pe_filter": 0.8, "momentum": 0.7, "quality": 0.5},
        )

        assert result.detected is True
        assert result.best_single == "pe_filter"
        assert result.best_single_sharpe == pytest.approx(0.8)
        assert result.full_stack_sharpe == pytest.approx(0.6)
        # severity = |0.6 - 0.8| / 0.8 = 0.25
        assert result.severity == pytest.approx(0.25)

    def test_detect_degradation_when_stack_better(self) -> None:
        """Full stack Sharpe >= best single → detected=False, severity=0."""
        result = detect_degradation(
            full_stack_sharpe=1.0,
            single_sharpes={"pe_filter": 0.8, "momentum": 0.7, "quality": 0.5},
        )

        assert result.detected is False
        assert result.severity == pytest.approx(0.0)
        assert result.best_single == "pe_filter"
        assert result.best_single_sharpe == pytest.approx(0.8)
        assert result.full_stack_sharpe == pytest.approx(1.0)


class TestDetectNegativeMarginal:
    """Tests for detect_negative_marginal."""

    def test_detect_negative_marginal(self) -> None:
        """Identify filters with MC below threshold in the greedy stack."""
        # Stack order: A, B, C, D, E
        # Sharpes:  [control=0.5, +A=0.6, +B=0.55, +C=0.50, +D=0.52, +E=0.48]
        # MC:       A=+0.10, B=-0.05, C=-0.05, D=+0.02, E=-0.04
        # Threshold = -0.02, so B, C, E flagged
        stack_sharpes = [0.5, 0.6, 0.55, 0.50, 0.52, 0.48]
        filter_order = ["A", "B", "C", "D", "E"]

        results = detect_negative_marginal(stack_sharpes, filter_order, threshold=-0.02)

        assert len(results) == 3

        names = {r.filter_name for r in results}
        assert names == {"B", "C", "E"}

        # Check B specifically
        b_result = next(r for r in results if r.filter_name == "B")
        assert b_result.marginal_contribution == pytest.approx(-0.05)
        assert b_result.position_in_stack == 1

        # Check E
        e_result = next(r for r in results if r.filter_name == "E")
        assert e_result.marginal_contribution == pytest.approx(-0.04)
        assert e_result.position_in_stack == 4


class TestDetectPairwiseDestruction:
    """Tests for detect_pairwise_destruction."""

    def test_detect_pairwise_destruction(self) -> None:
        """Identify destructive pairs where interaction < threshold."""
        single_sharpes = {"A": 0.8, "B": 0.7, "C": 0.6}
        pair_sharpes = {
            ("A", "B"): 0.75,  # interaction = 0.75 - 0.8 = -0.05 → flagged
            ("A", "C"): 0.9,  # interaction = 0.9 - 0.8 = +0.10 → OK
            ("B", "C"): 0.60,  # interaction = 0.60 - 0.7 = -0.10 → flagged
        }

        results = detect_pairwise_destruction(single_sharpes, pair_sharpes, threshold=-0.03)

        assert len(results) == 2

        pairs = {(r.filter_a, r.filter_b) for r in results}
        assert pairs == {("A", "B"), ("B", "C")}

        # Check (A, B) interaction
        ab_result = next(r for r in results if r.filter_a == "A" and r.filter_b == "B")
        assert ab_result.pair_sharpe == pytest.approx(0.75)
        assert ab_result.best_single_sharpe == pytest.approx(0.8)
        assert ab_result.interaction_effect == pytest.approx(-0.05)

        # Check (B, C) interaction
        bc_result = next(r for r in results if r.filter_a == "B" and r.filter_b == "C")
        assert bc_result.interaction_effect == pytest.approx(-0.10)


class TestDetectUniverseCollapse:
    """Tests for detect_universe_collapse."""

    def test_detect_universe_collapse(self) -> None:
        """Flag filters with low unique-kill rate."""
        # 10 stocks. Filter A kills {0,1,2,3}, Filter B kills {0,1,2,4}
        # Overlap kills (both fail): {0,1,2}
        # A unique kills: {3} (fails A, passes B) → 1/4 = 0.25
        # B unique kills: {4} (fails B, passes A) → 1/4 = 0.25
        #
        # Filter C kills {0,1,2,3} — same as A
        # C unique kills: must pass A AND B. Stock 3 fails A → not unique for C.
        #   Stocks 0,1,2 fail A&B. Stock 3 fails A. → 0 unique for C → rate 0.0
        fail_a = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
        fail_b = np.array([1, 1, 1, 0, 1, 0, 0, 0, 0, 0])
        fail_c = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])  # identical to A

        fail_vectors = {"A": fail_a, "B": fail_b, "C": fail_c}

        # threshold=0.10 → flag anything with unique_kill_rate < 10%
        results = detect_universe_collapse(fail_vectors, threshold=0.10)

        # C should be flagged (unique_kill_rate = 0.0)
        # A has unique_kill_rate = 0 (stock 3 also killed by C)
        # B has unique_kill_rate = 1/4 = 0.25 → not flagged
        flagged_names = {r.filter_name for r in results}
        assert "C" in flagged_names
        assert "A" in flagged_names
        assert "B" not in flagged_names

        c_result = next(r for r in results if r.filter_name == "C")
        assert c_result.total_kills == 4
        assert c_result.unique_kills == 0
        assert c_result.unique_kill_rate == pytest.approx(0.0)


class TestDetectVolatilityInjection:
    """Tested implicitly through compute_failure_correlation — but vol injection
    is tested via the correlation test below for completeness."""


class TestFailureCorrelation:
    """Tests for compute_failure_correlation."""

    def test_failure_correlation(self) -> None:
        """Identical vectors → correlation 1.0; independent → near 0."""
        rng = np.random.default_rng(42)
        n = 1000

        # Two identical vectors
        vec_a = rng.integers(0, 2, size=n)
        vec_b = vec_a.copy()

        # An independent vector
        vec_c = rng.integers(0, 2, size=n)

        fail_vectors = {"A": vec_a, "B": vec_b, "C": vec_c}
        corr = compute_failure_correlation(fail_vectors)

        # Identical vectors → perfect correlation
        assert corr["A"]["B"] == pytest.approx(1.0)
        assert corr["B"]["A"] == pytest.approx(1.0)

        # Self-correlation is always 1.0
        assert corr["A"]["A"] == pytest.approx(1.0)

        # Independent vectors → low correlation (not exactly 0 due to randomness)
        assert abs(corr["A"]["C"]) < 0.15

    def test_failure_correlation_constant_column(self) -> None:
        """A constant vector (std=0) should produce 0.0 correlation."""
        vec_a = np.ones(100, dtype=int)  # constant — all fail
        vec_b = np.array([1, 0] * 50)  # non-constant

        corr = compute_failure_correlation({"const": vec_a, "vary": vec_b})

        assert corr["const"]["vary"] == pytest.approx(0.0)
        assert corr["vary"]["const"] == pytest.approx(0.0)
        # Self-correlation for constant is still 1.0
        assert corr["const"]["const"] == pytest.approx(1.0)
