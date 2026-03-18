"""Full pipeline integration test — exercises all engine subpackages end-to-end.

Verifies that models, filters, scoring, composite, events, backtesting, and
ingestion (providers) packages work together with synthetic data.  No real
data providers or network calls are used.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

# ---------------------------------------------------------------------------
# Helpers — synthetic data factories
# ---------------------------------------------------------------------------
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import (
    CompositeScore,
    FactorScore,
    FilterResult,
    GrowthStage,
)


def _make_income(
    revenue: int = 10_000,
    cogs: int = 4_000,
    gross_profit: int | None = None,
    net_income: int = 1_500,
    ebit: int = 5_000,
    interest_expense: int = 200,
) -> IncomeStatement:
    gp = gross_profit if gross_profit is not None else revenue - cogs
    return IncomeStatement(
        revenue=Decimal(revenue),
        cost_of_revenue=Decimal(cogs),
        gross_profit=Decimal(gp),
        net_income=Decimal(net_income),
        ebit=Decimal(ebit),
        interest_expense=Decimal(interest_expense),
    )


def _make_balance(
    total_assets: int = 50_000,
    current_assets: int = 15_000,
    current_liabilities: int = 8_000,
    total_liabilities: int = 20_000,
    total_equity: int = 30_000,
    long_term_debt: int = 10_000,
) -> BalanceSheet:
    return BalanceSheet(
        total_assets=Decimal(total_assets),
        current_assets=Decimal(current_assets),
        current_liabilities=Decimal(current_liabilities),
        total_liabilities=Decimal(total_liabilities),
        total_equity=Decimal(total_equity),
        long_term_debt=Decimal(long_term_debt),
    )


def _make_cashflow(
    operating: int = 3_000,
    capex: int = -500,
) -> CashFlowStatement:
    return CashFlowStatement(
        operating_cash_flow=Decimal(operating),
        capital_expenditures=Decimal(capex),
    )


def _make_period(
    revenue: int = 10_000,
    cogs: int = 4_000,
    total_assets: int = 50_000,
    operating_cf: int = 3_000,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end="2025-09-28",
        filing_date="2025-11-01",
        current_income=_make_income(revenue=revenue, cogs=cogs),
        prior_income=_make_income(revenue=int(revenue * 0.9), cogs=int(cogs * 0.9)),
        current_balance=_make_balance(total_assets=total_assets),
        prior_balance=_make_balance(total_assets=int(total_assets * 0.95)),
        current_cash_flow=_make_cashflow(operating=operating_cf),
        prior_cash_flow=_make_cashflow(operating=int(operating_cf * 0.85)),
    )


def _make_profile(
    ticker: str = "AAPL",
    sector: GICSSector = GICSSector.TECHNOLOGY,
    market_cap: int = 3_000_000_000,
    avg_daily_volume: int = 50_000_000,
    years_of_history: int = 20,
) -> AssetProfile:
    return AssetProfile(
        ticker=ticker,
        name=f"{ticker} Corp",
        sector=sector,
        market_cap=Decimal(market_cap),
        avg_daily_volume=Decimal(avg_daily_volume),
        years_of_history=years_of_history,
    )


# ===========================================================================
# 1. test_all_engine_packages_importable
# ===========================================================================


class TestAllEnginePackagesImportable:
    """Verify that all engine subpackages are importable and expose key symbols."""

    def test_models_package(self) -> None:
        import margin_engine.models

        assert hasattr(margin_engine.models, "AssetProfile")
        assert hasattr(margin_engine.models, "FinancialPeriod")
        assert hasattr(margin_engine.models, "FactorScore")
        assert hasattr(margin_engine.models, "CompositeScore")
        assert hasattr(margin_engine.models, "GrowthStage")
        assert hasattr(margin_engine.models, "FilterResult")

    def test_scoring_filters_package(self) -> None:
        import margin_engine.scoring.filters

        assert hasattr(margin_engine.scoring.filters, "run_elimination_filters")
        assert hasattr(margin_engine.scoring.filters, "PipelineResult")
        assert hasattr(margin_engine.scoring.filters, "altman_z_score")
        assert hasattr(margin_engine.scoring.filters, "beneish_m_score")
        assert hasattr(margin_engine.scoring.filters, "liquidity_check")

    def test_scoring_quantitative_package(self) -> None:
        import margin_engine.scoring.quantitative

        assert hasattr(margin_engine.scoring.quantitative, "gross_profitability")
        assert hasattr(margin_engine.scoring.quantitative, "piotroski_f_score")
        assert hasattr(margin_engine.scoring.quantitative, "acquirers_multiple")
        assert hasattr(margin_engine.scoring.quantitative, "price_momentum")

    def test_scoring_composite_functions(self) -> None:
        import margin_engine.scoring

        assert hasattr(margin_engine.scoring, "compute_composite_score")
        assert hasattr(margin_engine.scoring, "compute_percentile_ranks")
        assert hasattr(margin_engine.scoring, "classify_growth_stage")
        assert hasattr(margin_engine.scoring, "sector_neutral_ranks")

    def test_events_package(self) -> None:
        import margin_engine.events

        assert hasattr(margin_engine.events, "EventRecord")
        assert hasattr(margin_engine.events, "EventPipeline")
        assert hasattr(margin_engine.events, "NotificationThrottle")
        assert hasattr(margin_engine.events, "ImpactClassifier")
        assert hasattr(margin_engine.events, "ProcessedEvent")
        assert hasattr(margin_engine.events, "EventSeverity")

    def test_backtesting_package(self) -> None:
        import margin_engine.backtesting

        assert hasattr(margin_engine.backtesting, "WalkForwardSimulator")
        assert hasattr(margin_engine.backtesting, "BacktestConfig")
        assert hasattr(margin_engine.backtesting, "BacktestResult")
        assert hasattr(margin_engine.backtesting, "ValidationGate")
        assert hasattr(margin_engine.backtesting, "ScoredStock")
        assert hasattr(margin_engine.backtesting, "PerformanceCalculator")

    def test_ingestion_package(self) -> None:
        import margin_engine.ingestion

        assert hasattr(margin_engine.ingestion, "ProviderRegistry")
        assert hasattr(margin_engine.ingestion, "RateLimiter")
        assert hasattr(margin_engine.ingestion, "DataProvider")
        assert hasattr(margin_engine.ingestion, "DataCategory")
        assert hasattr(margin_engine.ingestion, "FetchResult")


# ===========================================================================
# 2. test_filter_to_scoring_pipeline
# ===========================================================================


class TestFilterToScoringPipeline:
    """Create synthetic data, run through elimination filters, then score survivors."""

    def test_healthy_stock_passes_filters_and_gets_scored(self) -> None:
        from margin_engine.scoring.filters import run_elimination_filters
        from margin_engine.scoring.quantitative import gross_profitability

        period = _make_period(revenue=10_000, cogs=4_000, total_assets=50_000)
        profile = _make_profile(ticker="GOOD", market_cap=3_000_000_000)

        pipeline_result = run_elimination_filters(period, profile)
        assert pipeline_result.passed, (
            f"Expected healthy stock to pass all filters, "
            f"but these failed: {[f.name for f in pipeline_result.failed_filters]}"
        )

        # Score the survivor
        score = gross_profitability(period)
        assert score.name == "gross_profitability"
        assert isinstance(score.raw_value, float)
        # (10000 - 4000) / 50000 = 0.12
        assert abs(score.raw_value - 0.12) < 1e-6

    def test_small_cap_fails_filter(self) -> None:
        """Stock with market cap below minimum should fail liquidity filter."""
        from margin_engine.scoring.filters import run_elimination_filters

        period = _make_period()
        profile = _make_profile(ticker="TINY", market_cap=50_000_000)  # $50M < $100M min

        pipeline_result = run_elimination_filters(period, profile)
        assert not pipeline_result.passed
        assert any(f.name == "liquidity" for f in pipeline_result.failed_filters)

    def test_multiple_stocks_filter_and_score(self) -> None:
        """Filter a universe of stocks, score survivors, verify numeric results."""
        from margin_engine.scoring.filters import run_elimination_filters
        from margin_engine.scoring.quantitative import gross_profitability

        stocks = [
            ("AAPL", GICSSector.TECHNOLOGY, 3_000_000_000, 10_000, 3_000, 50_000),
            ("MSFT", GICSSector.TECHNOLOGY, 2_500_000_000, 20_000, 8_000, 80_000),
            ("JPM", GICSSector.FINANCIALS, 500_000_000_000, 50_000, 20_000, 200_000),
            ("TINY", GICSSector.TECHNOLOGY, 50_000_000, 5_000, 2_000, 30_000),
        ]

        survivors: list[tuple[str, FactorScore]] = []
        for ticker, sector, mcap, rev, cogs, assets in stocks:
            period = _make_period(revenue=rev, cogs=cogs, total_assets=assets)
            profile = _make_profile(ticker=ticker, sector=sector, market_cap=mcap)
            result = run_elimination_filters(period, profile)
            if result.passed:
                score = gross_profitability(period)
                survivors.append((ticker, score))

        # TINY too small market cap ($50M < $100M), JPM now passes (sector exclusion removed)
        survivor_tickers = {t for t, _ in survivors}
        assert "AAPL" in survivor_tickers
        assert "MSFT" in survivor_tickers
        assert "JPM" in survivor_tickers
        assert "TINY" not in survivor_tickers

        # All survivors have numeric scores
        for _, score in survivors:
            assert isinstance(score.raw_value, float)
            assert score.raw_value > 0


# ===========================================================================
# 3. test_scoring_to_composite_pipeline
# ===========================================================================


class TestScoringToCompositePipeline:
    """Take individual factor scores, rank them, classify, and produce a composite."""

    def test_percentile_ranker_produces_valid_ranks(self) -> None:
        from margin_engine.scoring import compute_percentile_ranks

        scores = [
            FactorScore(name="gp", raw_value=0.10, percentile_rank=0.0),
            FactorScore(name="gp", raw_value=0.20, percentile_rank=0.0),
            FactorScore(name="gp", raw_value=0.30, percentile_rank=0.0),
            FactorScore(name="gp", raw_value=0.40, percentile_rank=0.0),
            FactorScore(name="gp", raw_value=0.50, percentile_rank=0.0),
        ]

        ranked = compute_percentile_ranks(scores)
        assert len(ranked) == 5

        # Every rank should be in (0, 100]
        for r in ranked:
            assert 0.0 < r.percentile_rank <= 100.0

        # Higher raw_value should get higher percentile
        assert ranked[4].percentile_rank > ranked[0].percentile_rank

    def test_growth_stage_classifier(self) -> None:
        from margin_engine.scoring import classify_growth_stage

        period = _make_period(revenue=10_000, cogs=4_000, total_assets=50_000)
        profile = _make_profile(
            ticker="GROW", sector=GICSSector.TECHNOLOGY, market_cap=5_000_000_000
        )

        # High growth: revenue CAGR > 20%, gross margin > 40%, market cap > $2B
        stage = classify_growth_stage(
            period=period,
            profile=profile,
            revenue_cagr_3yr=0.30,  # 30% CAGR
        )
        # gross margin = (10000-4000)/10000 = 60%, market cap > $2B, CAGR > 20%
        assert stage == GrowthStage.HIGH_GROWTH

    def test_composite_scorer_end_to_end(self) -> None:
        """Rank scores, classify growth stage, compute composite, verify output."""
        from margin_engine.scoring import (
            classify_growth_stage,
            compute_composite_score,
            compute_percentile_ranks,
        )

        # Build raw quality scores for 5 stocks
        quality_raw = [
            FactorScore(name="gross_profitability", raw_value=v, percentile_rank=0.0)
            for v in [0.10, 0.15, 0.20, 0.25, 0.30]
        ]
        value_raw = [
            FactorScore(name="ev_fcf", raw_value=v, percentile_rank=0.0)
            for v in [15.0, 12.0, 10.0, 8.0, 6.0]
        ]
        momentum_raw = [
            FactorScore(name="price_momentum", raw_value=v, percentile_rank=0.0)
            for v in [0.05, 0.10, 0.15, 0.20, 0.25]
        ]

        # Rank within each factor
        quality_ranked = compute_percentile_ranks(quality_raw)
        value_ranked = compute_percentile_ranks(value_raw, invert=True)
        momentum_ranked = compute_percentile_ranks(momentum_raw)

        # Classify growth stage for the "best" stock (index 4)
        period = _make_period(revenue=10_000, cogs=4_000, total_assets=50_000)
        profile = _make_profile(
            ticker="BEST", sector=GICSSector.TECHNOLOGY, market_cap=5_000_000_000
        )
        stage = classify_growth_stage(period=period, profile=profile, revenue_cagr_3yr=0.10)

        # Compute composite for the best stock (index 4) using its ranked scores
        composite = compute_composite_score(
            ticker="BEST",
            quality_scores=[quality_ranked[4]],
            value_scores=[value_ranked[4]],
            momentum_scores=[momentum_ranked[4]],
            filters_passed=[FilterResult(name="liquidity", passed=True)],
            growth_stage=stage,
        )

        assert isinstance(composite, CompositeScore)
        assert composite.ticker == "BEST"
        assert 0.0 <= composite.composite_percentile <= 100.0
        assert composite.growth_stage is not None

    def test_composite_scores_bounded_0_to_100(self) -> None:
        """Verify composite percentiles are always within [0, 100]."""
        from margin_engine.scoring import compute_composite_score

        # Extreme case: all percentile ranks at 100
        max_scores = [
            FactorScore(name="q", raw_value=1.0, percentile_rank=100.0),
        ]
        composite = compute_composite_score(
            ticker="MAX",
            quality_scores=max_scores,
            value_scores=max_scores,
            momentum_scores=max_scores,
            filters_passed=[],
        )
        assert 0.0 <= composite.composite_percentile <= 100.0

        # Extreme case: all percentile ranks at 0
        min_scores = [
            FactorScore(name="q", raw_value=0.0, percentile_rank=0.0),
        ]
        composite = compute_composite_score(
            ticker="MIN",
            quality_scores=min_scores,
            value_scores=min_scores,
            momentum_scores=min_scores,
            filters_passed=[],
        )
        assert composite.composite_percentile == 0.0


# ===========================================================================
# 4. test_composite_to_backtesting_pipeline
# ===========================================================================


class TestCompositeToBacktestingPipeline:
    """Use composite scores to run a mini backtest and validate results."""

    def test_walk_forward_simulation_with_mock_providers(self) -> None:
        from margin_engine.backtesting import (
            BacktestConfig,
            ScoredStock,
            ValidationGate,
            WalkForwardSimulator,
        )

        # Build a set of scored stocks
        scored_stocks = [
            ScoredStock(ticker="AAPL", composite_score=95.0, price=150.0),
            ScoredStock(ticker="MSFT", composite_score=90.0, price=300.0),
            ScoredStock(ticker="GOOGL", composite_score=85.0, price=140.0),
            ScoredStock(ticker="NVDA", composite_score=80.0, price=500.0),
            ScoredStock(ticker="META", composite_score=75.0, price=350.0),
        ]

        # Simple mock providers that return constant data
        class MockUniverseProvider:
            def get_scores(self, as_of_date: date) -> list[ScoredStock]:
                return scored_stocks

        class MockBenchmarkProvider:
            def get_price(self, ticker: str, as_of_date: date) -> float:
                # Slight upward trend for the benchmark
                base_date = date(2024, 1, 1)
                months = (as_of_date.year - base_date.year) * 12 + (
                    as_of_date.month - base_date.month
                )
                return 450.0 * (1.0 + 0.008 * months)

        config = BacktestConfig(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            rebalance_frequency="monthly",
            top_percentile=0.40,
            benchmark_ticker="SPY",
        )

        simulator = WalkForwardSimulator(
            config=config,
            universe_provider=MockUniverseProvider(),
            benchmark_provider=MockBenchmarkProvider(),
        )

        result = simulator.run()

        # BacktestResult should have snapshots and metrics
        assert result.snapshots, "Expected at least one monthly snapshot"
        assert result.metrics is not None
        assert result.metrics.num_months > 0
        assert result.duration_seconds >= 0

        # Validate through ValidationGate
        gate = ValidationGate()
        validated_result = gate.validate_result(result)
        assert validated_result.validation is not None
        # We don't require all checks to pass with synthetic data,
        # but the validation structure should be complete
        assert validated_result.validation.total_checks == 6

    def test_backtest_result_has_performance_metrics(self) -> None:
        from margin_engine.backtesting import (
            BacktestConfig,
            ScoredStock,
            WalkForwardSimulator,
        )

        scored_stocks = [
            ScoredStock(ticker="AAPL", composite_score=95.0, price=150.0),
            ScoredStock(ticker="MSFT", composite_score=85.0, price=300.0),
        ]

        class StaticUniverseProvider:
            def get_scores(self, as_of_date: date) -> list[ScoredStock]:
                return scored_stocks

        class StaticBenchmarkProvider:
            def get_price(self, ticker: str, as_of_date: date) -> float:
                return 100.0

        config = BacktestConfig(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 4, 30),
            rebalance_frequency="monthly",
            top_percentile=0.50,
        )

        result = WalkForwardSimulator(
            config=config,
            universe_provider=StaticUniverseProvider(),
            benchmark_provider=StaticBenchmarkProvider(),
        ).run()

        m = result.metrics
        # All metric fields should be numeric
        assert isinstance(m.cagr, float)
        assert isinstance(m.sharpe_ratio, float)
        assert isinstance(m.sortino_ratio, float)
        assert isinstance(m.max_drawdown, float)
        assert isinstance(m.win_rate, float)
        assert isinstance(m.information_ratio, float)
        assert isinstance(m.total_return, float)
        assert isinstance(m.benchmark_total_return, float)


# ===========================================================================
# 5. test_event_pipeline_end_to_end
# ===========================================================================


class TestEventPipelineEndToEnd:
    """Create events, process through pipeline, apply throttle."""

    def test_full_event_processing_flow(self) -> None:
        from margin_engine.events import (
            EventPipeline,
            EventRecord,
            EventSeverity,
            EventType,
            NotificationThrottle,
            RelevanceFilter,
        )

        now = datetime.now(UTC)

        events = [
            EventRecord(
                event_type=EventType.EARNINGS_RELEASE,
                ticker="AAPL",
                timestamp=now,
                severity=EventSeverity.MAJOR,
                source="finnhub",
            ),
            EventRecord(
                event_type=EventType.PRICE_ALERT,
                ticker="AAPL",
                timestamp=now,
                severity=EventSeverity.MINOR,
                source="internal",
            ),
            EventRecord(
                event_type=EventType.INSIDER_TRANSACTION,
                ticker="MSFT",
                timestamp=now,
                severity=EventSeverity.MODERATE,
                source="edgar",
            ),
            EventRecord(
                event_type=EventType.SCORE_CHANGE,
                ticker="GOOGL",
                timestamp=now,
                severity=EventSeverity.MINOR,
                source="engine",
                payload={"delta": 15.0},
            ),
            EventRecord(
                event_type=EventType.MACRO_EVENT,
                ticker="UNWATCHED",
                timestamp=now,
                severity=EventSeverity.MINOR,
                source="fred",
            ),
        ]

        # Step 1: Build pipeline
        relevance_filter = RelevanceFilter(watched_tickers={"AAPL", "MSFT", "GOOGL"})
        pipeline = EventPipeline(relevance_filter=relevance_filter)

        # Step 2: Process events
        processed = pipeline.process(events)

        # UNWATCHED ticker should be filtered out
        processed_tickers = {pe.event.ticker for pe in processed}
        assert "UNWATCHED" not in processed_tickers
        assert "AAPL" in processed_tickers
        assert "MSFT" in processed_tickers
        assert "GOOGL" in processed_tickers

        # Step 3: Verify classifications
        for pe in processed:
            if pe.event.event_type == EventType.EARNINGS_RELEASE:
                assert pe.classified_severity == EventSeverity.MAJOR
            elif pe.event.event_type == EventType.PRICE_ALERT:
                assert pe.classified_severity == EventSeverity.MINOR
            elif pe.event.event_type == EventType.INSIDER_TRANSACTION:
                assert pe.classified_severity == EventSeverity.MODERATE
            elif pe.event.event_type == EventType.SCORE_CHANGE:
                # delta=15 -> |15| > 10 -> MAJOR
                assert pe.classified_severity == EventSeverity.MAJOR

        # Step 4: Apply throttle
        throttle = NotificationThrottle(cooldown=timedelta(hours=1))

        # First notification for AAPL should go through
        assert throttle.should_notify("AAPL", EventSeverity.MINOR, now)
        throttle.record_notification("AAPL", now)

        # Second MINOR notification within cooldown should be suppressed
        assert not throttle.should_notify("AAPL", EventSeverity.MINOR, now + timedelta(minutes=30))

        # But MAJOR always gets through
        assert throttle.should_notify("AAPL", EventSeverity.MAJOR, now + timedelta(minutes=30))

        # After cooldown, MINOR is allowed again
        assert throttle.should_notify("AAPL", EventSeverity.MINOR, now + timedelta(hours=2))

    def test_score_delta_checker(self) -> None:
        from margin_engine.events import ScoreDeltaChecker

        checker = ScoreDeltaChecker(threshold=5.0)
        assert checker.exceeds_threshold(6.0)
        assert checker.exceeds_threshold(-6.0)
        assert not checker.exceeds_threshold(4.0)
        assert not checker.exceeds_threshold(5.0)  # not strictly greater


# ===========================================================================
# 6. test_determinism_guarantee
# ===========================================================================


class TestDeterminismGuarantee:
    """Run the same pipeline twice with identical inputs and verify identical outputs."""

    def test_scoring_pipeline_is_deterministic(self) -> None:
        from margin_engine.scoring import (
            compute_composite_score,
            compute_percentile_ranks,
        )
        from margin_engine.scoring.filters import run_elimination_filters
        from margin_engine.scoring.quantitative import gross_profitability

        # Same inputs for both runs
        period = _make_period(revenue=15_000, cogs=5_000, total_assets=60_000)
        profile = _make_profile(ticker="DET", market_cap=5_000_000_000)

        results = []

        for _ in range(2):
            # Filter
            filter_result = run_elimination_filters(period, profile)

            # Score
            gp_score = gross_profitability(period)

            # Rank (simulate 3 stocks)
            scores = [
                FactorScore(name="gp", raw_value=0.10, percentile_rank=0.0),
                FactorScore(name="gp", raw_value=gp_score.raw_value, percentile_rank=0.0),
                FactorScore(name="gp", raw_value=0.30, percentile_rank=0.0),
            ]
            ranked = compute_percentile_ranks(scores)

            # Composite
            composite = compute_composite_score(
                ticker="DET",
                quality_scores=[ranked[1]],
                value_scores=[FactorScore(name="ev_fcf", raw_value=10.0, percentile_rank=50.0)],
                momentum_scores=[
                    FactorScore(name="momentum", raw_value=0.15, percentile_rank=60.0)
                ],
                filters_passed=[
                    FilterResult(name=r.name, passed=r.passed) for r in filter_result.results
                ],
                growth_stage=GrowthStage.STEADY_GROWTH,
            )

            results.append(
                {
                    "filter_passed": filter_result.passed,
                    "gp_raw": gp_score.raw_value,
                    "ranked_percentiles": [r.percentile_rank for r in ranked],
                    "composite_percentile": composite.composite_percentile,
                    "data_coverage": composite.data_coverage,
                }
            )

        # Both runs must produce identical results
        assert results[0] == results[1], (
            f"Non-deterministic results detected:\n  Run 1: {results[0]}\n  Run 2: {results[1]}"
        )

    def test_event_pipeline_is_deterministic(self) -> None:
        from margin_engine.events import (
            EventPipeline,
            EventRecord,
            EventSeverity,
            EventType,
            RelevanceFilter,
        )

        now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)

        events = [
            EventRecord(
                event_type=EventType.EARNINGS_RELEASE,
                ticker="AAPL",
                timestamp=now,
                severity=EventSeverity.MAJOR,
                source="test",
                event_id="fixed-id-1",
            ),
            EventRecord(
                event_type=EventType.PRICE_ALERT,
                ticker="MSFT",
                timestamp=now,
                severity=EventSeverity.MINOR,
                source="test",
                event_id="fixed-id-2",
            ),
        ]

        results = []
        for _ in range(2):
            pipeline = EventPipeline(
                relevance_filter=RelevanceFilter(watched_tickers={"AAPL", "MSFT"})
            )
            processed = pipeline.process(events)
            results.append(
                [
                    (pe.event.event_id, pe.classified_severity, pe.rescore_trigger)
                    for pe in processed
                ]
            )

        assert results[0] == results[1]


# ===========================================================================
# 7. test_version_available
# ===========================================================================


class TestVersionAvailable:
    """Verify that margin_engine.__version__ is set and well-formed."""

    def test_version_is_set(self) -> None:
        import margin_engine

        assert hasattr(margin_engine, "__version__")
        assert isinstance(margin_engine.__version__, str)
        assert len(margin_engine.__version__) > 0

    def test_version_is_semver_like(self) -> None:
        import margin_engine

        parts = margin_engine.__version__.split(".")
        assert len(parts) >= 2, (
            f"Version should have at least major.minor: {margin_engine.__version__}"
        )
        # Major and minor should be numeric
        assert parts[0].isdigit()
        assert parts[1].isdigit()
