"""Tests for multi-factor price target computation module."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
    PriceBar,
)
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.quantitative.price_targets import (
    PriceTargets,
    compute_price_targets,
)


@pytest.fixture
def healthy_period():
    return FinancialPeriod(
        period_end="2025-09-28",
        filing_date="2025-11-01",
        current_income=IncomeStatement(
            revenue=Decimal("100000000000"),
            gross_profit=Decimal("45000000000"),
            ebit=Decimal("30000000000"),
            net_income=Decimal("25000000000"),
            shares_outstanding=15000000000,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("350000000000"),
            current_assets=Decimal("130000000000"),
            cash_and_equivalents=Decimal("60000000000"),
            current_liabilities=Decimal("120000000000"),
            long_term_debt=Decimal("100000000000"),
            total_equity=Decimal("60000000000"),
            shares_outstanding=15000000000,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("110000000000"),
            capital_expenditures=Decimal("-10000000000"),
            dividends_paid=Decimal("-15000000000"),
            share_repurchases=Decimal("-90000000000"),
        ),
    )


@pytest.fixture
def healthy_profile():
    return AssetProfile(
        ticker="AAPL",
        name="Apple Inc.",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("3000000000000"),
        shares_outstanding=15000000000,
    )


@pytest.fixture
def price_bars():
    return [
        PriceBar(
            date="2025-09-28",
            open=Decimal("195"),
            high=Decimal("198"),
            low=Decimal("194"),
            close=Decimal("197"),
            volume=50000000,
        ),
        PriceBar(
            date="2025-09-27",
            open=Decimal("193"),
            high=Decimal("196"),
            low=Decimal("192"),
            close=Decimal("195"),
            volume=48000000,
        ),
    ]


class TestPriceTargets:
    def test_returns_price_targets_model(
        self, healthy_period, healthy_profile, price_bars
    ):
        """Verify result is a PriceTargets instance."""
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert isinstance(result, PriceTargets)

    def test_intrinsic_value_is_positive(
        self, healthy_period, healthy_profile, price_bars
    ):
        """With healthy data, intrinsic value should be positive."""
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.intrinsic_value is not None
        assert result.intrinsic_value > 0

    def test_buy_price_below_intrinsic(
        self, healthy_period, healthy_profile, price_bars
    ):
        """buy_price should always be less than sell_price."""
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.buy_price is not None
        assert result.sell_price is not None
        assert result.buy_price < result.sell_price

    def test_actual_price_from_latest_bar(
        self, healthy_period, healthy_profile, price_bars
    ):
        """actual_price should be the close of the latest-dated bar."""
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        # Latest bar is 2025-09-28 with close=197
        assert result.actual_price == pytest.approx(197.0)

    def test_margin_of_safety_varies_by_conviction(
        self, healthy_period, healthy_profile, price_bars
    ):
        """EXCEPTIONAL buy_price > WATCHLIST buy_price (tighter MoS = higher buy price)."""
        exceptional = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.EXCEPTIONAL,
        )
        watchlist = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.WATCHLIST,
        )
        assert exceptional.buy_price is not None
        assert watchlist.buy_price is not None
        # EXCEPTIONAL has 15% MoS (tighter), WATCHLIST has 25% MoS (wider)
        # So EXCEPTIONAL buy_price should be higher (closer to intrinsic)
        assert exceptional.buy_price > watchlist.buy_price

    def test_no_price_bars_returns_none_actual(
        self, healthy_period, healthy_profile
    ):
        """Empty bars should produce actual_price = None."""
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=[],
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.actual_price is None

    def test_negative_fcf_uses_fewer_methods(
        self, healthy_profile, price_bars
    ):
        """FCF <= 0 excludes DCF and EV/FCF methods from valuation_methods."""
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("100000000000"),
                gross_profit=Decimal("45000000000"),
                ebit=Decimal("30000000000"),
                net_income=Decimal("25000000000"),
                shares_outstanding=15000000000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("350000000000"),
                current_assets=Decimal("130000000000"),
                cash_and_equivalents=Decimal("60000000000"),
                current_liabilities=Decimal("120000000000"),
                long_term_debt=Decimal("100000000000"),
                total_equity=Decimal("60000000000"),
                shares_outstanding=15000000000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("5000000000"),
                capital_expenditures=Decimal("-10000000000"),
                dividends_paid=Decimal("-15000000000"),
                share_repurchases=Decimal("-90000000000"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.valuation_methods is not None
        assert "dcf" not in result.valuation_methods
        assert "ev_fcf" not in result.valuation_methods
        # Acquirer's multiple and shareholder yield should still work
        assert "acquirers_multiple" in result.valuation_methods
        assert "shareholder_yield" in result.valuation_methods

    def test_no_shares_outstanding_returns_none(
        self, healthy_period, price_bars
    ):
        """No shares_outstanding in profile -> None for intrinsic/buy/sell."""
        profile = AssetProfile(
            ticker="AAPL",
            name="Apple Inc.",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("3000000000000"),
            shares_outstanding=None,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.intrinsic_value is None
        assert result.buy_price is None
        assert result.sell_price is None

    def test_valuation_methods_dict(
        self, healthy_period, healthy_profile, price_bars
    ):
        """With healthy data, all 4 valuation methods should appear in the dict."""
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.valuation_methods is not None
        assert len(result.valuation_methods) == 4
        assert "dcf" in result.valuation_methods
        assert "ev_fcf" in result.valuation_methods
        assert "acquirers_multiple" in result.valuation_methods
        assert "shareholder_yield" in result.valuation_methods

    def test_price_upside_calculation(
        self, healthy_period, healthy_profile, price_bars
    ):
        """Verify price_upside = (intrinsic - actual) / actual."""
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.price_upside is not None
        assert result.intrinsic_value is not None
        assert result.actual_price is not None
        expected_upside = (result.intrinsic_value - result.actual_price) / result.actual_price
        assert result.price_upside == pytest.approx(expected_upside, abs=1e-4)
