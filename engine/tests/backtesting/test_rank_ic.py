"""Tests for Rank IC measurement."""

from __future__ import annotations

import numpy as np
from margin_engine.backtesting.rank_ic import compute_rank_ic, compute_rank_ic_report


class TestComputeRankIC:
    """Tests for compute_rank_ic."""

    def test_perfect_positive(self):
        """Perfect rank agreement -> IC = 1.0."""
        predicted = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        realized = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
        ic = compute_rank_ic(predicted, realized)
        assert abs(ic - 1.0) < 1e-6

    def test_perfect_negative(self):
        """Perfect reverse rank -> IC = -1.0."""
        predicted = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
        realized = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
        ic = compute_rank_ic(predicted, realized)
        assert abs(ic - (-1.0)) < 1e-6

    def test_no_correlation(self):
        """Random data should have IC near 0."""
        rng = np.random.default_rng(42)
        predicted = rng.standard_normal(100)
        realized = rng.standard_normal(100)
        ic = compute_rank_ic(predicted, realized)
        assert abs(ic) < 0.3  # Not significantly correlated

    def test_too_few_observations(self):
        """Fewer than 3 observations returns 0.0."""
        assert compute_rank_ic(np.array([1.0, 2.0]), np.array([0.01, 0.02])) == 0.0
        assert compute_rank_ic(np.array([1.0]), np.array([0.01])) == 0.0
        assert compute_rank_ic(np.array([]), np.array([])) == 0.0

    def test_constant_input(self):
        """Constant input produces IC of 0.0 (not NaN)."""
        predicted = np.array([5.0, 5.0, 5.0, 5.0])
        realized = np.array([0.01, 0.02, 0.03, 0.04])
        ic = compute_rank_ic(predicted, realized)
        assert ic == 0.0

    def test_golden_value(self):
        """Deterministic golden value test."""
        predicted = np.array([80.0, 75.0, 90.0, 60.0, 85.0])
        realized = np.array([0.05, 0.02, 0.08, -0.01, 0.06])
        ic = compute_rank_ic(predicted, realized)
        # Rankings: predicted=[3,2,5,1,4], realized=[3,2,5,1,4] -> perfect
        assert abs(ic - 1.0) < 1e-6


class TestRankICReport:
    """Tests for compute_rank_ic_report."""

    def test_empty_series(self):
        report = compute_rank_ic_report([])
        assert report.n_periods == 0
        assert report.ic_mean == 0.0
        assert report.hit_rate == 0.0

    def test_all_positive(self):
        report = compute_rank_ic_report([0.05, 0.10, 0.08, 0.03, 0.12])
        assert report.ic_mean > 0
        assert report.hit_rate == 1.0
        assert report.n_periods == 5
        assert report.ic_ir > 0  # Positive mean, positive IC IR

    def test_mixed_ic(self):
        report = compute_rank_ic_report([0.05, -0.02, 0.10, -0.01, 0.08])
        assert report.n_periods == 5
        assert 0.0 < report.hit_rate < 1.0
        assert len(report.ic_series) == 5

    def test_single_period(self):
        report = compute_rank_ic_report([0.05])
        assert report.n_periods == 1
        assert report.ic_mean == 0.05
        assert report.ic_std == 0.0
        assert report.ic_ir == 0.0  # std=0 means IR=0

    def test_ic_ir_formula(self):
        """IC IR = mean / std."""
        series = [0.10, 0.05, 0.15, 0.08, 0.12]
        report = compute_rank_ic_report(series)
        expected_mean = float(np.mean(series))
        expected_std = float(np.std(series, ddof=1))
        expected_ir = expected_mean / expected_std
        assert abs(report.ic_ir - expected_ir) < 1e-6
