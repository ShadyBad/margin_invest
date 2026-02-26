"""Tests for replay orchestrator."""

from datetime import date

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
