"""Integration tests for the backtesting engine.

Verifies end-to-end flows: config -> simulator -> metrics -> validation,
methodology comparison, metrics agreement, config serialization, exports,
and the full replay pipeline with PIT data.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from margin_engine.backtesting import (
    BacktestConfig,
    BacktestResult,
    BenchmarkProvider,
    FactorRegistry,
    HoldingRecord,
    InMemoryPITProvider,
    MethodologyComparison,
    MonthlySnapshot,
    PassThreshold,
    PerformanceCalculator,
    PerformanceMetrics,
    RebalanceFrequency,
    ReplayConfig,
    ReplayOrchestrator,
    ScoredStock,
    ScoredUniverseProvider,
    ValidationGate,
    ValidationResult,
    WalkForwardSimulator,
    compute_failure_audit,
    generate_walk_forward_partitions,
)
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
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
        months = (as_of_date.year - self._start_date.year) * 12 + (
            as_of_date.month - self._start_date.month
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
        months = (as_of_date.year - self._start_date.year) * 12 + (
            as_of_date.month - self._start_date.month
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

        expected_metrics = {
            "excess_cagr",
            "sharpe_ratio",
            "sortino_ratio",
            "max_drawdown",
            "win_rate",
        }
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
            "DelistingEvent",
            "DelistingType",
            "FactorAvailability",
            "FactorRegistry",
            "FailurePeriod",
            "HoldingRecord",
            "InMemoryPITProvider",
            "MarketRegimeHistorical",
            "MethodologyComparison",
            "MonthlySnapshot",
            "PITSnapshot",
            "PassThreshold",
            "PerformanceCalculator",
            "PerformanceMetrics",
            "PointInTimeProvider",
            "RankICReport",
            "RebalanceAuditRecord",
            "RebalanceFrequency",
            "RegimeSegment",
            "ReplayConfig",
            "ReplayOrchestrator",
            "ReplayResult",
            "ScoredStock",
            "ScoredUniverseProvider",
            "SelectionMode",
            "ShadowPortfolio",
            "ShadowPosition",
            "ShadowSnapshot",
            "ValidationGate",
            "ValidationResult",
            "WalkForwardPartition",
            "WalkForwardSimulator",
            "classify_regime",
            "compute_failure_audit",
            "compute_rank_ic",
            "compute_rank_ic_report",
            "generate_walk_forward_partitions",
            "haircut_returns",
            "segment_by_regime",
            "signal_significance",
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

    def test_new_modules_accessible_from_engine(self):
        from margin_engine import backtesting

        assert hasattr(backtesting, "FactorRegistry")
        assert hasattr(backtesting, "InMemoryPITProvider")
        assert hasattr(backtesting, "ReplayOrchestrator")
        assert hasattr(backtesting, "ShadowPortfolio")
        assert hasattr(backtesting, "compute_failure_audit")
        assert hasattr(backtesting, "classify_regime")
        assert hasattr(backtesting, "generate_walk_forward_partitions")


# ---------------------------------------------------------------------------
# 8. Full replay pipeline with PIT data
# ---------------------------------------------------------------------------


def _make_pit_period(month: int, ticker_idx: int) -> FinancialPeriod:
    """Build a FinancialPeriod with deterministic data varying by month and ticker."""
    revenue = Decimal(10000 + ticker_idx * 500 + month * 100)
    cost = Decimal(int(float(revenue) * 0.4))
    gross = revenue - cost
    net = Decimal(int(float(gross) * 0.55))
    return FinancialPeriod(
        period_end=f"2020-{month:02d}-01",
        filing_date=f"2020-{month:02d}-15",
        current_income=IncomeStatement(
            revenue=revenue,
            cost_of_revenue=cost,
            gross_profit=gross,
            sga_expense=Decimal(1000),
            depreciation=Decimal(500),
            ebit=gross - Decimal(1500),
            interest_expense=Decimal(200),
            tax_provision=Decimal(1000),
            net_income=net,
            shares_outstanding=1_000_000_000,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal(50000),
            current_assets=Decimal(20000),
            cash_and_equivalents=Decimal(10000),
            receivables=Decimal(5000),
            total_liabilities=Decimal(20000),
            current_liabilities=Decimal(8000),
            long_term_debt=Decimal(10000),
            total_equity=Decimal(30000),
            retained_earnings=Decimal(15000),
            shares_outstanding=1_000_000_000,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal(5000),
            capital_expenditures=Decimal(-1000),
        ),
        prior_income=IncomeStatement(
            revenue=Decimal(9000),
            cost_of_revenue=Decimal(3600),
            gross_profit=Decimal(5400),
            sga_expense=Decimal(900),
            depreciation=Decimal(450),
            ebit=Decimal(4050),
            interest_expense=Decimal(200),
            tax_provision=Decimal(900),
            net_income=Decimal(2950),
            shares_outstanding=1_000_000_000,
        ),
        prior_balance=BalanceSheet(
            total_assets=Decimal(45000),
            current_assets=Decimal(18000),
            cash_and_equivalents=Decimal(9000),
            receivables=Decimal(4500),
            total_liabilities=Decimal(18000),
            current_liabilities=Decimal(7000),
            long_term_debt=Decimal(9000),
            total_equity=Decimal(27000),
            retained_earnings=Decimal(13000),
            shares_outstanding=1_000_000_000,
        ),
        prior_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal(4500),
            capital_expenditures=Decimal(-900),
        ),
    )


def _build_pit_provider(tickers: list[str], months: range) -> InMemoryPITProvider:
    """Build an InMemoryPITProvider with deterministic data for given tickers and months."""
    provider = InMemoryPITProvider()
    for month in months:
        for j, ticker in enumerate(tickers):
            price = 100.0 + j * 10 + month * 2
            provider.add_snapshot(
                as_of_date=date(2020, month, 1),
                ticker=ticker,
                profile=AssetProfile(
                    ticker=ticker,
                    name=f"{ticker} Inc",
                    sector=GICSSector.TECHNOLOGY,
                    sub_industry="Software",
                    market_cap=Decimal("50000000000"),
                    avg_daily_volume=Decimal("10000000"),
                    shares_outstanding=1_000_000_000,
                ),
                period=_make_pit_period(month, j),
                price=price,
            )
    return provider


class TestReplayPipeline:
    """End-to-end replay pipeline: PIT data -> elimination -> scoring -> metrics."""

    def test_end_to_end_replay(self):
        """Run a 12-month replay and verify all outputs are populated."""
        tickers = ["AAPL", "MSFT", "GOOG", "AMZN", "META"]
        provider = _build_pit_provider(tickers, range(1, 13))

        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )

        result = orchestrator.run()

        # Verify core result structure
        assert result.metrics.num_months > 0
        assert len(result.audit_log) > 0
        assert len(result.factor_timeline) > 0
        assert len(result.regime_segments) > 0
        assert result.duration_seconds > 0

        # Verify audit log contents
        first_audit = result.audit_log[0]
        assert first_audit.universe_size == 5
        assert first_audit.factor_coverage > 0

        # Verify snapshots track portfolio value
        assert len(result.snapshots) > 0
        for snap in result.snapshots:
            assert snap.portfolio_value > 0

    def test_failure_audit_on_replay_output(self):
        """Failure audit runs on replay snapshots without error."""
        tickers = ["AAPL", "MSFT", "GOOG"]
        provider = _build_pit_provider(tickers, range(1, 7))

        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )
        result = orchestrator.run()

        regimes = [a.regime for a in result.audit_log]
        failures = compute_failure_audit(result.snapshots, regimes)
        assert isinstance(failures, list)
        # Each failure period has correct structure
        for f in failures:
            assert f.relative_underperformance > 0
            assert isinstance(f.holdings, list)
            assert f.regime_context  # non-empty string

    def test_walk_forward_partitions_cover_historical_range(self):
        """Walk-forward partitions can be generated for a long historical range."""
        partitions = generate_walk_forward_partitions(
            start_date=date(2006, 1, 1),
            end_date=date(2024, 12, 31),
            train_years=5,
            test_years=1,
        )
        assert len(partitions) > 0
        # Each partition has non-overlapping train/test
        for p in partitions:
            assert p.train_end < p.test_start
            assert p.test_end <= date(2024, 12, 31)

    def test_barrel_exports_all_new_symbols(self):
        """All new public symbols are importable from the barrel module."""
        from margin_engine.backtesting import (
            FactorRegistry,
            classify_regime,
            compute_failure_audit,
            generate_walk_forward_partitions,
            segment_by_regime,
        )

        # Verify key classes are the right type
        assert callable(FactorRegistry.default)
        assert callable(compute_failure_audit)
        assert callable(generate_walk_forward_partitions)
        assert callable(classify_regime)
        assert callable(segment_by_regime)

    def test_replay_empty_provider_returns_empty_result(self):
        """An empty PIT provider produces an empty but valid result."""
        provider = InMemoryPITProvider()
        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )
        result = orchestrator.run()

        assert result.metrics.num_months == 0
        assert len(result.snapshots) == 0
        assert result.duration_seconds >= 0
