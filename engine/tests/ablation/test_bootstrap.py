"""Tests for ablation bootstrap module."""

from __future__ import annotations

import numpy as np
import pytest

from margin_engine.ablation.bootstrap import (
    block_bootstrap_ci,
    bootstrap_sharpe_difference,
)


class TestBlockBootstrapCI:
    """Tests for block_bootstrap_ci."""

    def test_block_bootstrap_ci_known_mean(self) -> None:
        """Constant series should have a tight CI around the constant."""
        data = [5.0] * 60  # 60 months of constant value
        ci_low, point, ci_high = block_bootstrap_ci(data, statistic="mean")

        assert point == pytest.approx(5.0)
        assert ci_low == pytest.approx(5.0)
        assert ci_high == pytest.approx(5.0)

    def test_block_bootstrap_ci_respects_alpha(self) -> None:
        """99% CI should be wider than 90% CI."""
        rng = np.random.default_rng(123)
        data = rng.normal(0.01, 0.05, size=120).tolist()

        # 90% CI (alpha=0.10)
        lo_90, _, hi_90 = block_bootstrap_ci(
            data, statistic="mean", alpha=0.10, seed=99
        )
        width_90 = hi_90 - lo_90

        # 99% CI (alpha=0.01)
        lo_99, _, hi_99 = block_bootstrap_ci(
            data, statistic="mean", alpha=0.01, seed=99
        )
        width_99 = hi_99 - lo_99

        assert width_99 > width_90


class TestBootstrapSharpeDifference:
    """Tests for bootstrap_sharpe_difference."""

    def test_bootstrap_sharpe_difference_same_series(self) -> None:
        """Identical series should have CI spanning zero and not be significant."""
        rng = np.random.default_rng(77)
        returns = rng.normal(0.008, 0.04, size=60).tolist()

        result = bootstrap_sharpe_difference(returns, returns, seed=42)

        assert result.point_estimate == pytest.approx(0.0)
        # CI must span zero
        assert result.ci_low <= 0.0
        assert result.ci_high >= 0.0
        assert result.significant is False

    def test_bootstrap_sharpe_difference_detects_clear_winner(self) -> None:
        """One series clearly dominates — CI should not span zero, significant=True."""
        rng = np.random.default_rng(55)
        n = 120  # 10 years of monthly data

        # Series A: strong positive returns with moderate vol
        returns_a = rng.normal(0.02, 0.03, size=n)

        # Series B: weak / negative returns with higher vol
        returns_b = rng.normal(-0.005, 0.06, size=n)

        result = bootstrap_sharpe_difference(
            returns_a.tolist(),
            returns_b.tolist(),
            seed=42,
        )

        # A dominates B so difference should be clearly positive
        assert result.point_estimate > 0
        assert result.ci_low > 0, "CI lower bound should be above zero"
        assert result.significant is True
        assert result.p_value < 0.05
        assert result.n_resamples == 10_000
