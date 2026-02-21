"""Tests for backtesting data models and configuration."""

from __future__ import annotations

from datetime import UTC, date

import pytest
from margin_engine.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    HoldingRecord,
    MonthlySnapshot,
    PassThreshold,
    PerformanceMetrics,
    RebalanceFrequency,
    SelectionMode,
    ValidationResult,
)


class TestRebalanceFrequency:
    def test_monthly_value(self):
        assert RebalanceFrequency.MONTHLY == "monthly"

    def test_quarterly_value(self):
        assert RebalanceFrequency.QUARTERLY == "quarterly"

    def test_is_str(self):
        assert isinstance(RebalanceFrequency.MONTHLY, str)
        assert isinstance(RebalanceFrequency.QUARTERLY, str)

    def test_all_members(self):
        members = list(RebalanceFrequency)
        assert len(members) == 2


class TestSelectionMode:
    def test_enum_values(self):
        assert SelectionMode.TOP_PERCENTILE == "top_percentile"
        assert SelectionMode.CONVICTION_MOS == "conviction_mos"

    def test_default_selection_mode_is_top_percentile(self):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )
        assert config.selection_mode == SelectionMode.TOP_PERCENTILE

    def test_conviction_mos_config(self):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
            min_conviction_score=79.0,
            min_margin_of_safety=0.30,
        )
        assert config.selection_mode == SelectionMode.CONVICTION_MOS
        assert config.min_conviction_score == 79.0
        assert config.min_margin_of_safety == 0.30

    def test_conviction_mos_defaults(self):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            selection_mode=SelectionMode.CONVICTION_MOS,
        )
        assert config.min_conviction_score == 79.0
        assert config.min_margin_of_safety == 0.30


class TestBacktestConfig:
    def test_defaults(self):
        config = BacktestConfig()
        assert config.start_date == date(2015, 1, 1)
        assert config.end_date == date.today()
        assert config.rebalance_frequency == RebalanceFrequency.MONTHLY
        assert config.top_percentile == 0.05
        assert config.transaction_cost_bps == 10.0
        assert config.slippage_bps == 5.0
        assert config.benchmark_ticker == "SPY"

    def test_custom_values(self):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            top_percentile=0.10,
            transaction_cost_bps=15.0,
            slippage_bps=8.0,
            benchmark_ticker="QQQ",
        )
        assert config.start_date == date(2020, 1, 1)
        assert config.end_date == date(2024, 12, 31)
        assert config.rebalance_frequency == RebalanceFrequency.QUARTERLY
        assert config.top_percentile == 0.10
        assert config.transaction_cost_bps == 15.0
        assert config.slippage_bps == 8.0
        assert config.benchmark_ticker == "QQQ"

    def test_start_date_must_be_before_end_date(self):
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            BacktestConfig(
                start_date=date(2025, 1, 1),
                end_date=date(2020, 1, 1),
            )

    def test_same_start_and_end_date_fails(self):
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            BacktestConfig(
                start_date=date(2020, 1, 1),
                end_date=date(2020, 1, 1),
            )

    def test_total_cost_bps_property(self):
        config = BacktestConfig(transaction_cost_bps=10.0, slippage_bps=5.0)
        assert config.total_cost_bps == 15.0

    def test_serialization_roundtrip(self):
        config = BacktestConfig(
            start_date=date(2018, 6, 1),
            end_date=date(2023, 12, 31),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
        )
        data = config.model_dump()
        restored = BacktestConfig(**data)
        assert restored == config

    def test_json_roundtrip(self):
        config = BacktestConfig(
            start_date=date(2018, 6, 1),
            end_date=date(2023, 12, 31),
        )
        json_str = config.model_dump_json()
        restored = BacktestConfig.model_validate_json(json_str)
        assert restored == config


class TestHoldingRecord:
    def test_create(self):
        holding = HoldingRecord(
            ticker="AAPL",
            weight=0.05,
            entry_price=175.50,
            composite_score=95.2,
        )
        assert holding.ticker == "AAPL"
        assert holding.weight == 0.05
        assert holding.entry_price == 175.50
        assert holding.composite_score == 95.2

    def test_serialization_roundtrip(self):
        holding = HoldingRecord(
            ticker="MSFT",
            weight=0.04,
            entry_price=350.00,
            composite_score=97.1,
        )
        data = holding.model_dump()
        restored = HoldingRecord(**data)
        assert restored == holding


class TestMonthlySnapshot:
    def test_create(self):
        snapshot = MonthlySnapshot(
            date=date(2023, 6, 30),
            holdings=[
                HoldingRecord(
                    ticker="AAPL", weight=0.05, entry_price=175.0, composite_score=95.0
                ),
            ],
            portfolio_value=1_050_000.0,
            benchmark_value=1_030_000.0,
            portfolio_return=0.02,
            benchmark_return=0.015,
            turnover=0.12,
            transaction_costs=150.0,
        )
        assert snapshot.date == date(2023, 6, 30)
        assert len(snapshot.holdings) == 1
        assert snapshot.portfolio_value == 1_050_000.0
        assert snapshot.benchmark_value == 1_030_000.0
        assert snapshot.portfolio_return == 0.02
        assert snapshot.benchmark_return == 0.015
        assert snapshot.turnover == 0.12
        assert snapshot.transaction_costs == 150.0

    def test_excess_return_property(self):
        snapshot = MonthlySnapshot(
            date=date(2023, 6, 30),
            holdings=[],
            portfolio_value=1_050_000.0,
            benchmark_value=1_030_000.0,
            portfolio_return=0.02,
            benchmark_return=0.015,
            turnover=0.0,
            transaction_costs=0.0,
        )
        assert snapshot.excess_return == pytest.approx(0.005)

    def test_empty_holdings(self):
        snapshot = MonthlySnapshot(
            date=date(2023, 1, 31),
            holdings=[],
            portfolio_value=1_000_000.0,
            benchmark_value=1_000_000.0,
            portfolio_return=0.0,
            benchmark_return=0.0,
            turnover=0.0,
            transaction_costs=0.0,
        )
        assert len(snapshot.holdings) == 0

    def test_serialization_roundtrip(self):
        snapshot = MonthlySnapshot(
            date=date(2023, 6, 30),
            holdings=[
                HoldingRecord(
                    ticker="AAPL", weight=0.05, entry_price=175.0, composite_score=95.0
                ),
                HoldingRecord(
                    ticker="MSFT", weight=0.04, entry_price=350.0, composite_score=97.0
                ),
            ],
            portfolio_value=1_050_000.0,
            benchmark_value=1_030_000.0,
            portfolio_return=0.02,
            benchmark_return=0.015,
            turnover=0.12,
            transaction_costs=150.0,
        )
        data = snapshot.model_dump()
        restored = MonthlySnapshot(**data)
        assert restored == snapshot


class TestPerformanceMetrics:
    def test_create(self):
        metrics = PerformanceMetrics(
            cagr=0.12,
            excess_cagr=0.04,
            sharpe_ratio=0.85,
            sortino_ratio=1.2,
            max_drawdown=0.25,
            win_rate=0.60,
            information_ratio=0.65,
            total_return=1.85,
            benchmark_total_return=1.45,
            num_months=120,
            avg_turnover=0.15,
        )
        assert metrics.cagr == 0.12
        assert metrics.excess_cagr == 0.04
        assert metrics.sharpe_ratio == 0.85
        assert metrics.sortino_ratio == 1.2
        assert metrics.max_drawdown == 0.25
        assert metrics.win_rate == 0.60
        assert metrics.information_ratio == 0.65
        assert metrics.total_return == 1.85
        assert metrics.benchmark_total_return == 1.45
        assert metrics.num_months == 120
        assert metrics.avg_turnover == 0.15

    def test_serialization_roundtrip(self):
        metrics = PerformanceMetrics(
            cagr=0.12,
            excess_cagr=0.04,
            sharpe_ratio=0.85,
            sortino_ratio=1.2,
            max_drawdown=0.25,
            win_rate=0.60,
            information_ratio=0.65,
            total_return=1.85,
            benchmark_total_return=1.45,
            num_months=120,
            avg_turnover=0.15,
        )
        data = metrics.model_dump()
        restored = PerformanceMetrics(**data)
        assert restored == metrics


class TestPassThreshold:
    def test_default_values_match_spec(self):
        """Verify defaults match the design spec thresholds exactly."""
        thresholds = PassThreshold()
        assert thresholds.min_excess_cagr == 0.03  # > 3% annualized
        assert thresholds.min_sharpe == 0.7  # > 0.7
        assert thresholds.min_sortino == 1.0  # > 1.0
        assert thresholds.max_drawdown == 0.35  # < 35%
        assert thresholds.min_win_rate == 0.55  # > 55%
        assert thresholds.min_information_ratio == 0.5  # > 0.5

    def test_custom_thresholds(self):
        thresholds = PassThreshold(
            min_excess_cagr=0.05,
            min_sharpe=1.0,
            min_sortino=1.5,
            max_drawdown=0.25,
            min_win_rate=0.60,
            min_information_ratio=0.8,
        )
        assert thresholds.min_excess_cagr == 0.05
        assert thresholds.min_sharpe == 1.0
        assert thresholds.min_sortino == 1.5
        assert thresholds.max_drawdown == 0.25
        assert thresholds.min_win_rate == 0.60
        assert thresholds.min_information_ratio == 0.8

    def test_serialization_roundtrip(self):
        thresholds = PassThreshold()
        data = thresholds.model_dump()
        restored = PassThreshold(**data)
        assert restored == thresholds


class TestValidationResult:
    @pytest.fixture()
    def passing_metrics(self) -> PerformanceMetrics:
        return PerformanceMetrics(
            cagr=0.15,
            excess_cagr=0.05,
            sharpe_ratio=0.9,
            sortino_ratio=1.3,
            max_drawdown=0.20,
            win_rate=0.62,
            information_ratio=0.7,
            total_return=2.0,
            benchmark_total_return=1.5,
            num_months=120,
            avg_turnover=0.15,
        )

    @pytest.fixture()
    def failing_metrics(self) -> PerformanceMetrics:
        return PerformanceMetrics(
            cagr=0.08,
            excess_cagr=0.01,  # Below 3%
            sharpe_ratio=0.5,  # Below 0.7
            sortino_ratio=0.8,  # Below 1.0
            max_drawdown=0.40,  # Above 35%
            win_rate=0.48,  # Below 55%
            information_ratio=0.3,  # Below 0.5
            total_return=1.2,
            benchmark_total_return=1.1,
            num_months=120,
            avg_turnover=0.20,
        )

    def test_all_passing(self, passing_metrics: PerformanceMetrics):
        result = ValidationResult(
            metrics=passing_metrics,
            thresholds=PassThreshold(),
            excess_cagr_pass=True,
            sharpe_pass=True,
            sortino_pass=True,
            drawdown_pass=True,
            win_rate_pass=True,
            information_ratio_pass=True,
        )
        assert result.overall_pass is True
        assert result.passed_count == 6
        assert result.total_checks == 6

    def test_all_failing(self, failing_metrics: PerformanceMetrics):
        result = ValidationResult(
            metrics=failing_metrics,
            thresholds=PassThreshold(),
            excess_cagr_pass=False,
            sharpe_pass=False,
            sortino_pass=False,
            drawdown_pass=False,
            win_rate_pass=False,
            information_ratio_pass=False,
        )
        assert result.overall_pass is False
        assert result.passed_count == 0
        assert result.total_checks == 6

    def test_partial_passing(self, passing_metrics: PerformanceMetrics):
        """If even one check fails, overall_pass is False."""
        result = ValidationResult(
            metrics=passing_metrics,
            thresholds=PassThreshold(),
            excess_cagr_pass=True,
            sharpe_pass=True,
            sortino_pass=True,
            drawdown_pass=True,
            win_rate_pass=True,
            information_ratio_pass=False,  # One failure
        )
        assert result.overall_pass is False
        assert result.passed_count == 5
        assert result.total_checks == 6

    def test_total_checks_is_always_six(self, passing_metrics: PerformanceMetrics):
        result = ValidationResult(
            metrics=passing_metrics,
            thresholds=PassThreshold(),
            excess_cagr_pass=True,
            sharpe_pass=False,
            sortino_pass=True,
            drawdown_pass=False,
            win_rate_pass=True,
            information_ratio_pass=False,
        )
        assert result.total_checks == 6

    def test_serialization_roundtrip(self, passing_metrics: PerformanceMetrics):
        result = ValidationResult(
            metrics=passing_metrics,
            thresholds=PassThreshold(),
            excess_cagr_pass=True,
            sharpe_pass=True,
            sortino_pass=True,
            drawdown_pass=True,
            win_rate_pass=True,
            information_ratio_pass=True,
        )
        data = result.model_dump()
        restored = ValidationResult(**data)
        assert restored.overall_pass == result.overall_pass
        assert restored.passed_count == result.passed_count


class TestBacktestResult:
    def test_create(self):
        config = BacktestConfig(
            start_date=date(2015, 1, 1),
            end_date=date(2025, 1, 1),
        )
        metrics = PerformanceMetrics(
            cagr=0.12,
            excess_cagr=0.04,
            sharpe_ratio=0.85,
            sortino_ratio=1.2,
            max_drawdown=0.25,
            win_rate=0.60,
            information_ratio=0.65,
            total_return=1.85,
            benchmark_total_return=1.45,
            num_months=120,
            avg_turnover=0.15,
        )
        result = BacktestResult(
            config=config,
            snapshots=[],
            metrics=metrics,
            duration_seconds=42.5,
        )
        assert result.config == config
        assert result.snapshots == []
        assert result.metrics == metrics
        assert result.validation is None
        assert result.duration_seconds == 42.5

    def test_run_at_auto_generated(self):
        config = BacktestConfig()
        metrics = PerformanceMetrics(
            cagr=0.12,
            excess_cagr=0.04,
            sharpe_ratio=0.85,
            sortino_ratio=1.2,
            max_drawdown=0.25,
            win_rate=0.60,
            information_ratio=0.65,
            total_return=1.85,
            benchmark_total_return=1.45,
            num_months=120,
            avg_turnover=0.15,
        )
        result = BacktestResult(
            config=config,
            snapshots=[],
            metrics=metrics,
            duration_seconds=1.0,
        )
        assert result.run_at is not None
        assert result.run_at.tzinfo == UTC

    def test_with_validation(self):
        config = BacktestConfig()
        metrics = PerformanceMetrics(
            cagr=0.15,
            excess_cagr=0.05,
            sharpe_ratio=0.9,
            sortino_ratio=1.3,
            max_drawdown=0.20,
            win_rate=0.62,
            information_ratio=0.7,
            total_return=2.0,
            benchmark_total_return=1.5,
            num_months=120,
            avg_turnover=0.15,
        )
        validation = ValidationResult(
            metrics=metrics,
            thresholds=PassThreshold(),
            excess_cagr_pass=True,
            sharpe_pass=True,
            sortino_pass=True,
            drawdown_pass=True,
            win_rate_pass=True,
            information_ratio_pass=True,
        )
        result = BacktestResult(
            config=config,
            snapshots=[],
            metrics=metrics,
            validation=validation,
            duration_seconds=10.0,
        )
        assert result.validation is not None
        assert result.validation.overall_pass is True

    def test_with_snapshots(self):
        config = BacktestConfig()
        metrics = PerformanceMetrics(
            cagr=0.12,
            excess_cagr=0.04,
            sharpe_ratio=0.85,
            sortino_ratio=1.2,
            max_drawdown=0.25,
            win_rate=0.60,
            information_ratio=0.65,
            total_return=1.85,
            benchmark_total_return=1.45,
            num_months=2,
            avg_turnover=0.15,
        )
        snapshots = [
            MonthlySnapshot(
                date=date(2015, 1, 31),
                holdings=[
                    HoldingRecord(
                        ticker="AAPL", weight=0.05, entry_price=110.0, composite_score=96.0
                    ),
                ],
                portfolio_value=1_000_000.0,
                benchmark_value=1_000_000.0,
                portfolio_return=0.0,
                benchmark_return=0.0,
                turnover=1.0,
                transaction_costs=1500.0,
            ),
            MonthlySnapshot(
                date=date(2015, 2, 28),
                holdings=[
                    HoldingRecord(
                        ticker="AAPL", weight=0.05, entry_price=115.0, composite_score=95.5
                    ),
                ],
                portfolio_value=1_020_000.0,
                benchmark_value=1_015_000.0,
                portfolio_return=0.02,
                benchmark_return=0.015,
                turnover=0.10,
                transaction_costs=153.0,
            ),
        ]
        result = BacktestResult(
            config=config,
            snapshots=snapshots,
            metrics=metrics,
            duration_seconds=5.0,
        )
        assert len(result.snapshots) == 2
        assert result.snapshots[0].date == date(2015, 1, 31)
        assert result.snapshots[1].portfolio_return == 0.02

    def test_serialization_roundtrip(self):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2024, 1, 1),
        )
        metrics = PerformanceMetrics(
            cagr=0.12,
            excess_cagr=0.04,
            sharpe_ratio=0.85,
            sortino_ratio=1.2,
            max_drawdown=0.25,
            win_rate=0.60,
            information_ratio=0.65,
            total_return=1.85,
            benchmark_total_return=1.45,
            num_months=48,
            avg_turnover=0.15,
        )
        result = BacktestResult(
            config=config,
            snapshots=[],
            metrics=metrics,
            duration_seconds=3.0,
        )
        json_str = result.model_dump_json()
        restored = BacktestResult.model_validate_json(json_str)
        assert restored.config == result.config
        assert restored.metrics == result.metrics
        assert restored.duration_seconds == result.duration_seconds
