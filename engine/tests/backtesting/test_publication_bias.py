"""Tests for publication bias adjustments."""

from __future__ import annotations

import math

from margin_engine.backtesting.models import PerformanceMetrics
from margin_engine.backtesting.publication_bias import (
    haircut_returns,
    signal_significance,
)


def _make_metrics(**overrides) -> PerformanceMetrics:
    defaults = dict(
        cagr=0.15,
        excess_cagr=0.08,
        sharpe_ratio=1.2,
        sortino_ratio=1.5,
        max_drawdown=0.20,
        win_rate=0.60,
        information_ratio=0.8,
        total_return=1.50,
        benchmark_total_return=0.80,
        num_months=60,
        avg_turnover=0.30,
    )
    defaults.update(overrides)
    return PerformanceMetrics(**defaults)


class TestHaircutReturns:
    """Tests for haircut_returns."""

    def test_default_12_percent(self):
        metrics = _make_metrics()
        haircut = haircut_returns(metrics)
        assert abs(haircut.cagr - 0.15 * 0.88) < 1e-6
        assert abs(haircut.excess_cagr - 0.08 * 0.88) < 1e-6
        assert abs(haircut.sharpe_ratio - 1.2 * 0.88) < 1e-6
        assert abs(haircut.total_return - 1.50 * 0.88) < 1e-6

    def test_drawdown_unchanged(self):
        metrics = _make_metrics()
        haircut = haircut_returns(metrics)
        assert haircut.max_drawdown == metrics.max_drawdown

    def test_win_rate_unchanged(self):
        metrics = _make_metrics()
        haircut = haircut_returns(metrics)
        assert haircut.win_rate == metrics.win_rate

    def test_benchmark_unchanged(self):
        metrics = _make_metrics()
        haircut = haircut_returns(metrics)
        assert haircut.benchmark_total_return == metrics.benchmark_total_return

    def test_custom_decay(self):
        metrics = _make_metrics()
        haircut = haircut_returns(metrics, decay_rate=0.20)
        assert abs(haircut.cagr - 0.15 * 0.80) < 1e-6

    def test_zero_decay(self):
        metrics = _make_metrics()
        haircut = haircut_returns(metrics, decay_rate=0.0)
        assert abs(haircut.cagr - metrics.cagr) < 1e-6

    def test_num_months_preserved(self):
        metrics = _make_metrics()
        haircut = haircut_returns(metrics)
        assert haircut.num_months == metrics.num_months
        assert haircut.avg_turnover == metrics.avg_turnover


class TestSignalSignificance:
    """Tests for signal_significance."""

    def test_high_ic_many_obs(self):
        t_stat, passes = signal_significance(0.20, 100)
        assert t_stat == 0.20 * math.sqrt(100)  # 2.0 > 1.8
        assert passes is True

    def test_low_ic_few_obs(self):
        t_stat, passes = signal_significance(0.02, 10)
        expected_t = 0.02 * math.sqrt(10)
        assert abs(t_stat - expected_t) < 1e-6
        assert passes is False  # ~0.063, well below 1.8

    def test_single_observation(self):
        t_stat, passes = signal_significance(0.50, 1)
        assert t_stat == 0.0
        assert passes is False

    def test_negative_ic(self):
        t_stat, passes = signal_significance(-0.20, 100)
        assert t_stat < 0
        assert passes is True  # abs(t) > 1.8

    def test_custom_threshold(self):
        t_stat, passes = signal_significance(0.05, 36)
        # t = 0.05 * 6 = 0.30
        assert not passes  # Below 1.8
        t_stat2, passes2 = signal_significance(0.05, 36, threshold=0.25)
        assert passes2  # Above custom threshold

    def test_golden_value(self):
        """Deterministic t-stat for known input."""
        ic = 0.08
        n = 60
        t_stat, passes = signal_significance(ic, n)
        expected = 0.08 * math.sqrt(60)
        assert abs(t_stat - expected) < 1e-10
        assert passes is False  # ~0.619, below 1.8
