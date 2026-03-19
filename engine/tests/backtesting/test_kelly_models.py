"""Tests for Kelly Criterion model extensions.

Covers new HoldingRecord fields, PositionOutcome, TierStats,
and PerformanceMetrics.tier_stats extension.
"""

from __future__ import annotations

from margin_engine.backtesting.models import (
    HoldingRecord,
    PerformanceMetrics,
    PositionOutcome,
    TierStats,
)


class TestHoldingRecordBackwardCompat:
    """Existing HoldingRecord still works without the new optional fields."""

    def test_minimal_creation(self):
        hr = HoldingRecord(ticker="AAPL", weight=0.15, entry_price=150.0, composite_score=85.0)
        assert hr.ticker == "AAPL"
        assert hr.weight == 0.15
        assert hr.entry_price == 150.0
        assert hr.composite_score == 85.0

    def test_new_optional_fields_default_to_none(self):
        hr = HoldingRecord(ticker="MSFT", weight=0.10, entry_price=200.0, composite_score=80.0)
        assert hr.conviction_tier is None
        assert hr.exit_price is None
        assert hr.position_return is None


class TestHoldingRecordNewFields:
    """New optional fields populate correctly."""

    def test_conviction_tier_field(self):
        hr = HoldingRecord(
            ticker="GOOG",
            weight=0.12,
            entry_price=100.0,
            composite_score=90.0,
            conviction_tier="exceptional",
        )
        assert hr.conviction_tier == "exceptional"

    def test_exit_price_field(self):
        hr = HoldingRecord(
            ticker="AMZN",
            weight=0.08,
            entry_price=100.0,
            composite_score=75.0,
            exit_price=120.0,
        )
        assert hr.exit_price == 120.0

    def test_position_return_field(self):
        hr = HoldingRecord(
            ticker="TSLA",
            weight=0.05,
            entry_price=200.0,
            composite_score=70.0,
            position_return=0.25,
        )
        assert hr.position_return == 0.25

    def test_all_new_fields_together(self):
        hr = HoldingRecord(
            ticker="NVDA",
            weight=0.15,
            entry_price=50.0,
            composite_score=95.0,
            conviction_tier="high",
            exit_price=65.0,
            position_return=0.30,
        )
        assert hr.conviction_tier == "high"
        assert hr.exit_price == 65.0
        assert hr.position_return == 0.30


class TestPositionOutcome:
    """PositionOutcome model creation and is_winner property."""

    def test_winner_positive_return(self):
        outcome = PositionOutcome(
            ticker="AAPL",
            conviction_tier="exceptional",
            entry_price=100.0,
            exit_price=120.0,
            return_pct=0.20,
        )
        assert outcome.is_winner is True

    def test_loser_negative_return(self):
        outcome = PositionOutcome(
            ticker="XYZ",
            conviction_tier="high",
            entry_price=100.0,
            exit_price=90.0,
            return_pct=-0.10,
        )
        assert outcome.is_winner is False

    def test_zero_return_is_not_winner(self):
        outcome = PositionOutcome(
            ticker="FLAT",
            conviction_tier="medium",
            entry_price=100.0,
            exit_price=100.0,
            return_pct=0.0,
        )
        assert outcome.is_winner is False

    def test_all_fields_accessible(self):
        outcome = PositionOutcome(
            ticker="MSFT",
            conviction_tier="exceptional",
            entry_price=250.0,
            exit_price=300.0,
            return_pct=0.20,
        )
        assert outcome.ticker == "MSFT"
        assert outcome.conviction_tier == "exceptional"
        assert outcome.entry_price == 250.0
        assert outcome.exit_price == 300.0
        assert outcome.return_pct == 0.20


class TestTierStats:
    """TierStats model creation."""

    def test_basic_creation(self):
        stats = TierStats(
            tier="exceptional",
            win_rate=0.65,
            avg_winner_return=0.22,
            avg_loser_return=0.08,
            n_positions=20,
        )
        assert stats.tier == "exceptional"
        assert stats.win_rate == 0.65
        assert stats.avg_winner_return == 0.22
        assert stats.avg_loser_return == 0.08
        assert stats.n_positions == 20

    def test_high_tier(self):
        stats = TierStats(
            tier="high",
            win_rate=0.55,
            avg_winner_return=0.15,
            avg_loser_return=0.10,
            n_positions=35,
        )
        assert stats.tier == "high"
        assert stats.n_positions == 35


class TestPerformanceMetricsTierStats:
    """PerformanceMetrics tier_stats extension."""

    def test_tier_stats_defaults_to_none(self):
        metrics = PerformanceMetrics(
            cagr=0.12,
            excess_cagr=0.03,
            sharpe_ratio=0.8,
            sortino_ratio=1.2,
            max_drawdown=0.15,
            win_rate=0.6,
            information_ratio=0.55,
            total_return=0.45,
            benchmark_total_return=0.30,
            num_months=36,
            avg_turnover=0.2,
        )
        assert metrics.tier_stats is None

    def test_tier_stats_can_be_set(self):
        stats = [
            TierStats(
                tier="exceptional",
                win_rate=0.70,
                avg_winner_return=0.25,
                avg_loser_return=0.10,
                n_positions=15,
            ),
            TierStats(
                tier="high",
                win_rate=0.55,
                avg_winner_return=0.15,
                avg_loser_return=0.08,
                n_positions=30,
            ),
        ]
        metrics = PerformanceMetrics(
            cagr=0.12,
            excess_cagr=0.03,
            sharpe_ratio=0.8,
            sortino_ratio=1.2,
            max_drawdown=0.15,
            win_rate=0.6,
            information_ratio=0.55,
            total_return=0.45,
            benchmark_total_return=0.30,
            num_months=36,
            avg_turnover=0.2,
            tier_stats=stats,
        )
        assert metrics.tier_stats is not None
        assert len(metrics.tier_stats) == 2
        assert metrics.tier_stats[0].tier == "exceptional"
        assert metrics.tier_stats[1].tier == "high"
