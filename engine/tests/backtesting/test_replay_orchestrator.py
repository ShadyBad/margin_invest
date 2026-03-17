"""Tests for replay orchestrator."""

from datetime import date
from unittest.mock import MagicMock, patch

from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.pit_provider import InMemoryPITProvider
from margin_engine.backtesting.replay_orchestrator import (
    RebalanceAuditRecord,
    ReplayConfig,
    ReplayOrchestrator,
    ReplayResult,
)
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import CompositeTier
from margin_engine.scoring.v3_orchestrator import V3Result, V3TrackResult


def _make_profile(ticker: str, sector: GICSSector = GICSSector.TECHNOLOGY) -> AssetProfile:
    return AssetProfile(
        ticker=ticker,
        name=f"{ticker} Inc",
        sector=sector,
        sub_industry="Software",
        market_cap=50_000_000_000,
        avg_daily_volume=10_000_000,
        shares_outstanding=1_000_000_000,
    )


def _make_period(period_end_str: str = "2008-12-31") -> FinancialPeriod:
    income = IncomeStatement(
        revenue=10_000,
        cost_of_revenue=4_000,
        gross_profit=6_000,
        sga_expense=1_000,
        depreciation=500,
        ebit=4_500,
        interest_expense=200,
        tax_provision=1_000,
        net_income=3_300,
        shares_outstanding=1_000_000_000,
    )
    balance = BalanceSheet(
        total_assets=50_000,
        current_assets=20_000,
        cash_and_equivalents=10_000,
        receivables=5_000,
        total_liabilities=20_000,
        current_liabilities=8_000,
        long_term_debt=10_000,
        total_equity=30_000,
        retained_earnings=15_000,
        shares_outstanding=1_000_000_000,
    )
    cash_flow = CashFlowStatement(
        operating_cash_flow=5_000,
        capital_expenditures=-1_000,
    )
    return FinancialPeriod(
        period_end=period_end_str,
        filing_date=period_end_str,
        current_income=income,
        current_balance=balance,
        current_cash_flow=cash_flow,
        prior_income=income,
        prior_balance=balance,
        prior_cash_flow=cash_flow,
    )


def _build_provider_with_data(months: int = 6) -> InMemoryPITProvider:
    """Build a provider with AAPL and MSFT data for N months starting 2020-01."""
    provider = InMemoryPITProvider()
    base_prices = {"AAPL": 300.0, "MSFT": 170.0}

    for i in range(months):
        month = 1 + i
        year = 2020 + (month - 1) // 12
        m = ((month - 1) % 12) + 1
        rebal_date = date(year, m, 1)
        period_str = rebal_date.isoformat()
        for ticker, base in base_prices.items():
            price = base * (1 + 0.01 * i)
            provider.add_snapshot(
                rebal_date,
                ticker,
                _make_profile(ticker),
                _make_period(period_end_str=period_str),
                price,
            )
    return provider


class TestReplayOrchestrator:
    def test_run_produces_result(self):
        provider = _build_provider_with_data(months=6)
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
        assert isinstance(result, ReplayResult)
        assert result.metrics is not None
        assert len(result.audit_log) > 0

    def test_audit_log_has_correct_fields(self):
        provider = _build_provider_with_data(months=3)
        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )
        result = orchestrator.run()
        record = result.audit_log[0]
        assert isinstance(record, RebalanceAuditRecord)
        assert record.universe_size >= 2
        assert record.factor_coverage > 0.0

    def test_regime_segments_populated(self):
        provider = _build_provider_with_data(months=6)
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
        assert len(result.regime_segments) > 0

    def test_factor_timeline_populated(self):
        provider = _build_provider_with_data(months=3)
        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )
        result = orchestrator.run()
        assert len(result.factor_timeline) > 0
        entry = result.factor_timeline[0]
        assert hasattr(entry, "available")
        assert hasattr(entry, "missing")
        assert len(entry.available) > 0
        assert isinstance(entry.missing, list)

    def test_empty_result_when_no_data(self):
        provider = InMemoryPITProvider()
        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )
        result = orchestrator.run()
        assert isinstance(result, ReplayResult)
        assert result.metrics.num_months == 0
        assert len(result.audit_log) == 0

    def test_quarterly_rebalance(self):
        provider = _build_provider_with_data(months=6)
        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 1),
            rebalance_frequency="quarterly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )
        result = orchestrator.run()
        assert isinstance(result, ReplayResult)
        # Quarterly => fewer rebalance dates than monthly
        assert len(result.audit_log) < 6

    def test_use_real_scoring_flag_stored(self):
        """Verify the use_real_scoring flag is stored on the instance."""
        provider = InMemoryPITProvider()
        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 1),
        )
        # Default should be False
        orch_default = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )
        assert orch_default._use_real_scoring is False

        # Explicit True
        orch_real = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
            use_real_scoring=True,
        )
        assert orch_real._use_real_scoring is True

    def test_simple_scoring_default(self):
        """Verify default behavior (use_real_scoring=False) still produces valid results."""
        provider = _build_provider_with_data(months=3)
        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
            use_real_scoring=False,
        )
        result = orchestrator.run()
        assert isinstance(result, ReplayResult)
        assert len(result.audit_log) > 0
        # Scores should be computed via simple scorer (baseline ~50 + margin + yield)
        for record in result.audit_log:
            for holding in record.top_holdings:
                assert 0.0 <= holding["score"] <= 100.0

    @patch("margin_engine.backtesting.replay_orchestrator.score_universe_v3")
    @patch("margin_engine.backtesting.replay_orchestrator.run_elimination_filters")
    def test_score_with_pipeline_calls_v3(self, mock_filters, mock_score_v3):
        """Verify v3 pipeline is called when use_real_scoring=True."""
        # Make all filters pass so survivors reach the scoring step
        mock_filter_result = MagicMock()
        mock_filter_result.passed = True
        mock_filter_result.failed_filters = []
        mock_filters.return_value = mock_filter_result

        # Build mock V3 results for AAPL and MSFT
        def _make_v3_result(ticker: str, score: float) -> V3Result:
            track_a = V3TrackResult(
                track="compounder",
                qualifies=True,
                conviction=CompositeTier.HIGH,
                score=score,
                gates_passed=3,
                total_gates=4,
            )
            track_b = V3TrackResult(
                track="mispricing",
                qualifies=False,
                conviction=CompositeTier.NONE,
                score=0.0,
                gates_passed=1,
                total_gates=4,
            )
            return V3Result(
                ticker=ticker,
                opportunity_type="compounder",
                conviction=CompositeTier.HIGH,
                track_a=track_a,
                track_b=track_b,
                timing_signal="neutral",
                max_position_pct=5.0,
            )

        mock_score_v3.return_value = [
            _make_v3_result("AAPL", 0.75),
            _make_v3_result("MSFT", 0.60),
        ]

        provider = _build_provider_with_data(months=3)
        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
            use_real_scoring=True,
        )
        result = orchestrator.run()

        assert isinstance(result, ReplayResult)
        assert mock_score_v3.call_count >= 1
        # Each call should pass shiller_cape=25.0
        for call in mock_score_v3.call_args_list:
            assert (
                call.kwargs.get("shiller_cape", call.args[1] if len(call.args) > 1 else None)
                == 25.0
            )
        # Scores should reflect the mocked values (0.75 * 100 = 75.0, 0.60 * 100 = 60.0)
        assert len(result.audit_log) > 0
        # Verify audit log has scored holdings
        for record in result.audit_log:
            assert record.survivor_count == 2
            for holding in record.top_holdings:
                assert holding["score"] in [75.0, 60.0]


def test_run_populates_gross_return_with_costs():
    """gross_return should reflect pre-cost return and exceed portfolio_return.

    Costs are nonzero.

    Scenario:
      Month 1: AAA scores high (net_income=10_000) -> selected; BBB scores low.
      Month 2: AAA price rises to 110 (+10%); AAA now scores low, BBB scores high.
               -> Portfolio earns 10% from AAA, then 100% turnover occurs (sell AAA, buy BBB),
                  incurring transaction costs. gross_return captures the 10% before costs;
                  portfolio_return is net-of-cost (< 10%).

    Without the fix, MonthlySnapshot model_validator defaults gross_return = portfolio_return,
    so gross_return would equal portfolio_return instead of being the pre-cost figure.
    """

    def _make_period_with_income(period_end_str: str, net_income: float) -> FinancialPeriod:
        income = IncomeStatement(
            revenue=10_000,
            cost_of_revenue=4_000,
            gross_profit=6_000,
            sga_expense=1_000,
            depreciation=500,
            ebit=4_500,
            interest_expense=200,
            tax_provision=1_000,
            net_income=net_income,
            shares_outstanding=1_000_000_000,
        )
        balance = BalanceSheet(
            total_assets=50_000,
            current_assets=20_000,
            cash_and_equivalents=10_000,
            receivables=5_000,
            total_liabilities=20_000,
            current_liabilities=8_000,
            long_term_debt=10_000,
            total_equity=30_000,
            retained_earnings=15_000,
            shares_outstanding=1_000_000_000,
        )
        cf = CashFlowStatement(operating_cash_flow=5_000, capital_expenditures=-1_000)
        return FinancialPeriod(
            period_end=period_end_str,
            filing_date=period_end_str,
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
            prior_income=income,
            prior_balance=balance,
            prior_cash_flow=cf,
        )

    provider = InMemoryPITProvider()
    # Month 1: AAA scores high -> gets selected; BBB scores low
    provider.add_snapshot(
        date(2020, 1, 1),
        "AAA",
        _make_profile("AAA"),
        _make_period_with_income("2020-01-01", net_income=10_000),
        100.0,
    )
    provider.add_snapshot(
        date(2020, 1, 1),
        "BBB",
        _make_profile("BBB"),
        _make_period_with_income("2020-01-01", net_income=1),
        100.0,
    )
    # Month 2: AAA price up 10%; AAA now scores low, BBB scores high -> 100% turnover -> costs
    provider.add_snapshot(
        date(2020, 2, 1),
        "AAA",
        _make_profile("AAA"),
        _make_period_with_income("2020-02-01", net_income=1),
        110.0,
    )
    provider.add_snapshot(
        date(2020, 2, 1),
        "BBB",
        _make_profile("BBB"),
        _make_period_with_income("2020-02-01", net_income=10_000),
        100.0,
    )

    config = ReplayConfig(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 2, 28),
        rebalance_frequency="monthly",
        transaction_cost_bps=100.0,  # 1% costs to make the spread visible
    )
    orchestrator = ReplayOrchestrator(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
        disabled_filters={"liquidity"},  # bypass years_of_history check on synthetic data
    )
    result = orchestrator.run()

    snapshots_with_costs = [s for s in result.snapshots if s.transaction_costs > 0]
    assert len(snapshots_with_costs) > 0, "Expected at least one snapshot with transaction costs"

    for s in snapshots_with_costs:
        assert s.gross_return is not None, "gross_return must be explicitly populated"
        if s.portfolio_return != 0.0:
            # When there is a real price return, gross_return > portfolio_return
            # (gross captures pre-cost value; portfolio_return is net-of-cost)
            assert s.gross_return > s.portfolio_return, (
                f"gross={s.gross_return} should exceed net={s.portfolio_return} when costs nonzero"
            )
