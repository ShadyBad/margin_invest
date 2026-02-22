"""Integration tests for the backtesting engine.

Verifies end-to-end flows: config -> simulator -> metrics -> validation,
methodology comparison, metrics agreement, config serialization, and exports.
"""

from __future__ import annotations

from datetime import date

import pytest
from margin_engine.backtesting import (
    BacktestConfig,
    BacktestResult,
    BenchmarkProvider,
    HoldingRecord,
    MethodologyComparison,
    MonthlySnapshot,
    PassThreshold,
    PerformanceCalculator,
    PerformanceMetrics,
    RebalanceFrequency,
    ScoredStock,
    ScoredUniverseProvider,
    ValidationGate,
    ValidationResult,
    WalkForwardSimulator,
)

# ---------------------------------------------------------------------------
# In-memory fake providers
# ---------------------------------------------------------------------------


class FakeUniverseProvider:
    """Deterministic provider returning stocks with linearly growing prices."""

    def __init__(
        self,
        tickers: list[str],
        base_price: float = 100.0,
        monthly_return: float = 0.01,
        start_date: date = date(2020, 1, 1),
    ) -> None:
        self._tickers = tickers
        self._base_price = base_price
        self._monthly_return = monthly_return
        self._start_date = start_date

    def get_scores(self, as_of_date: date) -> list[ScoredStock]:
        months = (
            (as_of_date.year - self._start_date.year) * 12
            + (as_of_date.month - self._start_date.month)
        )
        price = self._base_price * (1 + self._monthly_return) ** months
        return [
            ScoredStock(
                ticker=t,
                composite_score=90.0 - i,
                price=price + i,
            )
            for i, t in enumerate(self._tickers)
        ]


class FakeBenchmarkProvider:
    """Deterministic benchmark growing at a fixed monthly rate."""

    def __init__(
        self,
        base_price: float = 100.0,
        monthly_return: float = 0.005,
        start_date: date = date(2020, 1, 1),
    ) -> None:
        self._base_price = base_price
        self._monthly_return = monthly_return
        self._start_date = start_date

    def get_price(self, ticker: str, as_of_date: date) -> float:
        months = (
            (as_of_date.year - self._start_date.year) * 12
            + (as_of_date.month - self._start_date.month)
        )
        return self._base_price * (1 + self._monthly_return) ** months


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

START = date(2020, 1, 1)
END = date(2021, 12, 31)
TICKERS = ["AAPL", "MSFT", "GOOG", "AMZN", "META", "NVDA", "TSLA", "JPM"]


def _make_config(
    start: date = START,
    end: date = END,
    freq: RebalanceFrequency = RebalanceFrequency.MONTHLY,
    top_pct: float = 0.25,
) -> BacktestConfig:
    return BacktestConfig(
        start_date=start,
        end_date=end,
        rebalance_frequency=freq,
        top_percentile=top_pct,
        transaction_cost_bps=10.0,
        slippage_bps=5.0,
    )


def _run_backtest(
    config: BacktestConfig | None = None,
    tickers: list[str] | None = None,
    portfolio_return: float = 0.01,
    benchmark_return: float = 0.005,
) -> BacktestResult:
    """Run a full backtest with fake providers."""
    cfg = config or _make_config()
    universe = FakeUniverseProvider(
        tickers=tickers or TICKERS,
        monthly_return=portfolio_return,
        start_date=cfg.start_date,
    )
    benchmark = FakeBenchmarkProvider(
        monthly_return=benchmark_return,
        start_date=cfg.start_date,
    )
    sim = WalkForwardSimulator(cfg, universe, benchmark)
    return sim.run()


def _make_metrics(**overrides: float) -> PerformanceMetrics:
    """Build a PerformanceMetrics with sensible defaults, allowing overrides."""
    defaults = dict(
        cagr=0.10,
        excess_cagr=0.05,
        sharpe_ratio=0.9,
        sortino_ratio=1.2,
        max_drawdown=0.20,
        win_rate=0.60,
        information_ratio=0.7,
        total_return=0.50,
        benchmark_total_return=0.30,
        num_months=24,
        avg_turnover=0.15,
    )
    defaults.update(overrides)
    return PerformanceMetrics(**defaults)


# ---------------------------------------------------------------------------
# 1. Full backtest flow
# ---------------------------------------------------------------------------


class TestFullBacktestFlow:
    """Create config -> run simulator with mock providers -> calculate metrics
    -> validate -> verify all pieces fit together."""

    def test_config_to_result(self):
        config = _make_config()
        result = _run_backtest(config)

        assert result.config == config
        assert len(result.snapshots) > 0
        assert result.metrics is not None
        assert result.duration_seconds >= 0

    def test_snapshots_are_chronological(self):
        result = _run_backtest()
        dates = [s.date for s in result.snapshots]
        assert dates == sorted(dates)

    def test_metrics_populated(self):
        result = _run_backtest()
        m = result.metrics
        assert m.num_months == len(result.snapshots)
        assert m.num_months > 0

    def test_validation_gate_attaches_to_result(self):
        result = _run_backtest()
        gate = ValidationGate()
        validated = gate.validate_result(result)

        assert validated.validation is not None
        assert validated.validation.metrics == result.metrics
        assert validated.validation.total_checks == 6

    def test_full_pipeline_end_to_end(self):
        """Config -> simulate -> validate -> check overall_pass is a bool."""
        config = _make_config()
        result = _run_backtest(config)
        gate = ValidationGate()
        validated = gate.validate_result(result)

        assert isinstance(validated.validation.overall_pass, bool)
        assert validated.validation.passed_count >= 0
        assert validated.validation.passed_count <= 6


# ---------------------------------------------------------------------------
# 2. Validation gate integration
# ---------------------------------------------------------------------------


class TestValidationGateIntegration:
    """Run a backtest, pass result to ValidationGate, verify validation."""

    def test_validate_result_returns_new_copy(self):
        result = _run_backtest()
        gate = ValidationGate()
        validated = gate.validate_result(result)

        # Original should not have validation
        assert result.validation is None
        # Validated copy should
        assert validated.validation is not None

    def test_validation_checks_individual_passes(self):
        result = _run_backtest()
        gate = ValidationGate()
        validated = gate.validate_result(result)
        v = validated.validation

        # Each individual check should be a bool
        assert isinstance(v.excess_cagr_pass, bool)
        assert isinstance(v.sharpe_pass, bool)
        assert isinstance(v.sortino_pass, bool)
        assert isinstance(v.drawdown_pass, bool)
        assert isinstance(v.win_rate_pass, bool)
        assert isinstance(v.information_ratio_pass, bool)

    def test_custom_thresholds(self):
        result = _run_backtest()
        # Very permissive thresholds - everything should pass
        easy = PassThreshold(
            min_excess_cagr=-1.0,
            min_sharpe=-10.0,
            min_sortino=-10.0,
            max_drawdown=1.0,
            min_win_rate=0.0,
            min_information_ratio=-10.0,
        )
        gate = ValidationGate(thresholds=easy)
        validated = gate.validate_result(result)
        assert validated.validation.overall_pass is True
        assert validated.validation.passed_count == 6

    def test_strict_thresholds_can_fail(self):
        result = _run_backtest()
        # Very strict thresholds
        strict = PassThreshold(
            min_excess_cagr=0.50,
            min_sharpe=5.0,
            min_sortino=5.0,
            max_drawdown=0.001,
            min_win_rate=0.99,
            min_information_ratio=5.0,
        )
        gate = ValidationGate(thresholds=strict)
        validated = gate.validate_result(result)
        assert validated.validation.overall_pass is False
        assert validated.validation.passed_count < 6


# ---------------------------------------------------------------------------
# 3. Methodology comparison flow
# ---------------------------------------------------------------------------


class TestMethodologyComparisonFlow:
    """Create two sets of metrics (old/new), run comparison, verify result."""

    def test_new_beats_old(self):
        old_metrics = _make_metrics(
            excess_cagr=0.03,
            sharpe_ratio=0.7,
            sortino_ratio=1.0,
            max_drawdown=0.30,
            win_rate=0.55,
        )
        new_metrics = _make_metrics(
            excess_cagr=0.08,
            sharpe_ratio=1.2,
            sortino_ratio=1.8,
            max_drawdown=0.15,
            win_rate=0.65,
        )
        gate = ValidationGate()
        comparison = gate.compare_methodologies(old_metrics, new_metrics)

        assert comparison.new_is_better is True
        assert len(comparison.new_wins) >= 3
        assert len(comparison.metrics_compared) == 5

    def test_old_beats_new(self):
        old_metrics = _make_metrics(
            excess_cagr=0.10,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=0.10,
            win_rate=0.70,
        )
        new_metrics = _make_metrics(
            excess_cagr=0.02,
            sharpe_ratio=0.5,
            sortino_ratio=0.8,
            max_drawdown=0.40,
            win_rate=0.45,
        )
        gate = ValidationGate()
        comparison = gate.compare_methodologies(old_metrics, new_metrics)

        assert comparison.new_is_better is False
        assert len(comparison.old_wins) >= 3

    def test_comparison_tracks_all_five_metrics(self):
        old_metrics = _make_metrics()
        new_metrics = _make_metrics()
        gate = ValidationGate()
        comparison = gate.compare_methodologies(old_metrics, new_metrics)

        expected_metrics = {"excess_cagr", "sharpe_ratio", "sortino_ratio", "max_drawdown",
                            "win_rate"}
        assert set(comparison.metrics_compared) == expected_metrics

    def test_ties_counted(self):
        metrics = _make_metrics()
        gate = ValidationGate()
        comparison = gate.compare_methodologies(metrics, metrics)

        # All metrics identical -> all ties
        assert len(comparison.ties) == 5
        assert len(comparison.new_wins) == 0
        assert len(comparison.old_wins) == 0
        assert comparison.new_is_better is False

    def test_comparison_is_methodology_comparison_type(self):
        gate = ValidationGate()
        comparison = gate.compare_methodologies(_make_metrics(), _make_metrics())
        assert isinstance(comparison, MethodologyComparison)


# ---------------------------------------------------------------------------
# 4. Simulator + metrics agreement
# ---------------------------------------------------------------------------


class TestSimulatorMetricsAgreement:
    """Run simulator, verify its metrics match what PerformanceCalculator.calculate()
    would produce from the same snapshots."""

    def test_metrics_match_recalculation(self):
        result = _run_backtest()
        calculator = PerformanceCalculator()
        recalculated = calculator.calculate(result.snapshots)

        m = result.metrics
        assert m.cagr == pytest.approx(recalculated.cagr)
        assert m.excess_cagr == pytest.approx(recalculated.excess_cagr)
        assert m.sharpe_ratio == pytest.approx(recalculated.sharpe_ratio)
        assert m.sortino_ratio == pytest.approx(recalculated.sortino_ratio)
        assert m.max_drawdown == pytest.approx(recalculated.max_drawdown)
        assert m.win_rate == pytest.approx(recalculated.win_rate)
        assert m.information_ratio == pytest.approx(recalculated.information_ratio)
        assert m.total_return == pytest.approx(recalculated.total_return)
        assert m.benchmark_total_return == pytest.approx(recalculated.benchmark_total_return)
        assert m.num_months == recalculated.num_months
        assert m.avg_turnover == pytest.approx(recalculated.avg_turnover)

    def test_num_months_equals_snapshot_count(self):
        result = _run_backtest()
        assert result.metrics.num_months == len(result.snapshots)

    def test_quarterly_metrics_match(self):
        config = _make_config(freq=RebalanceFrequency.QUARTERLY)
        result = _run_backtest(config)
        calculator = PerformanceCalculator()
        recalculated = calculator.calculate(result.snapshots)

        assert result.metrics.cagr == pytest.approx(recalculated.cagr)
        assert result.metrics.sharpe_ratio == pytest.approx(recalculated.sharpe_ratio)
        assert result.metrics.num_months == recalculated.num_months


# ---------------------------------------------------------------------------
# 5. Round-trip config serialization
# ---------------------------------------------------------------------------


class TestConfigSerialization:
    """BacktestConfig -> JSON -> BacktestConfig round-trip."""

    def test_round_trip_default_config(self):
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2023, 12, 31),
        )
        json_str = config.model_dump_json()
        restored = BacktestConfig.model_validate_json(json_str)

        assert restored.start_date == config.start_date
        assert restored.end_date == config.end_date
        assert restored.rebalance_frequency == config.rebalance_frequency
        assert restored.top_percentile == config.top_percentile
        assert restored.transaction_cost_bps == config.transaction_cost_bps
        assert restored.slippage_bps == config.slippage_bps
        assert restored.benchmark_ticker == config.benchmark_ticker

    def test_round_trip_custom_config(self):
        config = BacktestConfig(
            start_date=date(2018, 6, 15),
            end_date=date(2024, 1, 31),
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            top_percentile=0.10,
            transaction_cost_bps=20.0,
            slippage_bps=8.0,
            benchmark_ticker="QQQ",
        )
        json_str = config.model_dump_json()
        restored = BacktestConfig.model_validate_json(json_str)

        assert restored == config

    def test_round_trip_via_dict(self):
        config = _make_config()
        data = config.model_dump()
        restored = BacktestConfig.model_validate(data)
        assert restored == config

    def test_result_serialization_round_trip(self):
        """Full BacktestResult can be serialized and deserialized."""
        result = _run_backtest()
        json_str = result.model_dump_json()
        restored = BacktestResult.model_validate_json(json_str)

        assert restored.config == result.config
        assert len(restored.snapshots) == len(result.snapshots)
        assert restored.metrics.cagr == pytest.approx(result.metrics.cagr)
        assert restored.metrics.num_months == result.metrics.num_months


# ---------------------------------------------------------------------------
# 6. Export verification
# ---------------------------------------------------------------------------


class TestExportVerification:
    """All symbols importable from margin_engine.backtesting."""

    def test_all_models_importable(self):
        from margin_engine.backtesting import (
            BacktestConfig,
            BacktestResult,
            PassThreshold,
            PerformanceMetrics,
            RebalanceFrequency,
        )
        # Verify they are real classes
        assert BacktestConfig is not None
        assert BacktestResult is not None
        assert HoldingRecord is not None
        assert MonthlySnapshot is not None
        assert PassThreshold is not None
        assert PerformanceMetrics is not None
        assert RebalanceFrequency is not None
        assert ValidationResult is not None

    def test_metrics_importable(self):
        from margin_engine.backtesting import PerformanceCalculator
        assert PerformanceCalculator is not None

    def test_simulator_importable(self):
        from margin_engine.backtesting import (
            ScoredStock,
            WalkForwardSimulator,
        )
        assert BenchmarkProvider is not None
        assert ScoredStock is not None
        assert ScoredUniverseProvider is not None
        assert WalkForwardSimulator is not None

    def test_validation_importable(self):
        from margin_engine.backtesting import MethodologyComparison, ValidationGate
        assert MethodologyComparison is not None
        assert ValidationGate is not None

    def test_all_exports_in_dunder_all(self):
        import margin_engine.backtesting as bt
        expected = {
            "BacktestConfig",
            "BacktestResult",
            "BenchmarkProvider",
            "HoldingRecord",
            "MethodologyComparison",
            "MonthlySnapshot",
            "PassThreshold",
            "PerformanceCalculator",
            "PerformanceMetrics",
            "RebalanceFrequency",
            "ScoredStock",
            "ScoredUniverseProvider",
            "ValidationGate",
            "ValidationResult",
            "WalkForwardSimulator",
        }
        assert set(bt.__all__) == expected


# ---------------------------------------------------------------------------
# 7. Package accessible from top-level
# ---------------------------------------------------------------------------


class TestTopLevelAccess:
    """from margin_engine import backtesting works."""

    def test_import_backtesting_from_engine(self):
        from margin_engine import backtesting
        assert hasattr(backtesting, "WalkForwardSimulator")
        assert hasattr(backtesting, "PerformanceCalculator")
        assert hasattr(backtesting, "ValidationGate")
        assert hasattr(backtesting, "BacktestConfig")

    def test_backtesting_in_engine_all(self):
        import margin_engine
        assert "backtesting" in margin_engine.__all__
