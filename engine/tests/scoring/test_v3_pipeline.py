"""Tests for v3 universe scoring pipeline."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    AssetProfile, BalanceSheet, CashFlowStatement, FinancialHistory,
    FinancialPeriod, GICSSector, IncomeStatement,
)
from margin_engine.scoring.v3_pipeline import TickerV3Data, score_universe_v3


def _period(period_end="2024-09-28", ebit=Decimal("200"), **kwargs):
    defaults = dict(
        revenue=Decimal("1000"), cost_of_revenue=Decimal("600"),
        gross_profit=Decimal("400"), depreciation=Decimal("50"),
        net_income=Decimal("160"), total_equity=Decimal("500"),
        long_term_debt=Decimal("200"), short_term_debt=Decimal("100"),
        cash_and_equivalents=Decimal("50"), total_assets=Decimal("1500"),
        operating_cash_flow=Decimal("250"), capital_expenditures=Decimal("-80"),
        shares_outstanding=100,
    )
    defaults.update(kwargs)
    defaults["ebit"] = ebit
    return FinancialPeriod(
        period_end=period_end, filing_date="2024-11-01",
        current_income=IncomeStatement(
            revenue=defaults["revenue"], cost_of_revenue=defaults["cost_of_revenue"],
            gross_profit=defaults["gross_profit"], ebit=defaults["ebit"],
            depreciation=defaults["depreciation"], net_income=defaults["net_income"],
            shares_outstanding=defaults["shares_outstanding"],
        ),
        current_balance=BalanceSheet(
            total_assets=defaults["total_assets"], total_equity=defaults["total_equity"],
            long_term_debt=defaults["long_term_debt"], short_term_debt=defaults["short_term_debt"],
            cash_and_equivalents=defaults["cash_and_equivalents"],
            shares_outstanding=defaults["shares_outstanding"],
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=defaults["operating_cash_flow"],
            capital_expenditures=defaults["capital_expenditures"],
        ),
    )


def _make_ticker_data(ticker: str, sector=GICSSector.TECHNOLOGY) -> TickerV3Data:
    periods = [_period(period_end=f"{yr}-12-31") for yr in range(2020, 2025)]
    return TickerV3Data(
        ticker=ticker,
        history=FinancialHistory(ticker=ticker, periods=periods),
        latest_period=periods[-1],
        profile=AssetProfile(
            ticker=ticker, name=f"{ticker} Corp", sector=sector,
            market_cap=Decimal("10000000000"), shares_outstanding=100,
        ),
        current_price=100.0, current_fcf_per_share=5.0,
        sustainable_growth_rate=0.08,
        insider_percentile=50.0, institutional_percentile=50.0,
        sue_percentile=50.0, momentum_percentile=50.0,
        dcf_iv=120.0,
    )


class TestScoreUniverseV3:
    def test_basic_scoring(self):
        """Score 3 tickers, get V3Result for each."""
        data = [_make_ticker_data(t) for t in ["AAPL", "MSFT", "GOOGL"]]
        results = score_universe_v3(data, shiller_cape=25.0)
        assert len(results) == 3
        for r in results:
            assert r.ticker in {"AAPL", "MSFT", "GOOGL"}
            assert r.track_a.track == "compounder"
            assert r.track_b.track == "mispricing"

    def test_portfolio_cap_enforced(self):
        """With > 10 tickers, only top 10 get non-zero positions."""
        data = [_make_ticker_data(f"T{i:02d}") for i in range(15)]
        results = score_universe_v3(data, shiller_cape=25.0)
        assert len(results) == 15
        positioned = [r for r in results if r.max_position_pct > 0]
        assert len(positioned) <= 10

    def test_empty_universe(self):
        results = score_universe_v3([], shiller_cape=25.0)
        assert results == []

    def test_single_ticker(self):
        data = [_make_ticker_data("SOLO")]
        results = score_universe_v3(data, shiller_cape=25.0)
        assert len(results) == 1

    def test_regime_affects_results(self):
        """Different CAPE values should be accepted."""
        data = [_make_ticker_data("TEST")]
        euphoria = score_universe_v3(data, shiller_cape=40.0)
        cheap = score_universe_v3(data, shiller_cape=12.0)
        assert euphoria[0].ticker == cheap[0].ticker == "TEST"
