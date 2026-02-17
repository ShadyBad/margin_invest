"""Tests for multi-factor price target computation module."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

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
    _filter_outlier_methods,
    _validate_final_output,
    compute_price_targets,
)


class TestPriceTargetsModel:
    def test_invalid_reason_default_none(self):
        """invalid_reason should default to None."""
        pt = PriceTargets(intrinsic_value=100.0, buy_price=100.0, sell_price=125.0)
        assert pt.invalid_reason is None

    def test_invalid_reason_with_null_prices(self):
        """When invalid_reason is set, price fields should be None."""
        pt = PriceTargets(
            actual_price=197.0,
            invalid_reason="shares_outstanding_out_of_bounds",
        )
        assert pt.invalid_reason == "shares_outstanding_out_of_bounds"
        assert pt.intrinsic_value is None
        assert pt.buy_price is None
        assert pt.sell_price is None

    def test_invalid_reason_set_with_prices_raises(self):
        """Setting invalid_reason AND price fields should raise ValidationError."""
        with pytest.raises(ValidationError):
            PriceTargets(
                intrinsic_value=100.0,
                buy_price=100.0,
                sell_price=125.0,
                invalid_reason="shares_outstanding_out_of_bounds",
            )

    def test_positive_price_fields_when_present(self):
        """intrinsic_value, buy_price, sell_price must be > 0 when set."""
        with pytest.raises(ValidationError):
            PriceTargets(intrinsic_value=-5.0, buy_price=-5.0, sell_price=-3.0)


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

    def test_buy_price_equals_intrinsic(
        self, healthy_period, healthy_profile, price_bars
    ):
        """buy_price should equal intrinsic_value (floor), sell_price above it."""
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.buy_price is not None
        assert result.sell_price is not None
        assert result.intrinsic_value is not None
        assert result.buy_price == result.intrinsic_value
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

    def test_margin_of_safety_varies_by_growth_stage(
        self, healthy_period, healthy_profile, price_bars
    ):
        """Steady growth gets tighter MoS than turnaround (lower sell price)."""
        from margin_engine.models.scoring import GrowthStage

        steady = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
            growth_stage=GrowthStage.STEADY_GROWTH,
        )
        turnaround = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
            growth_stage=GrowthStage.TURNAROUND,
        )
        assert steady.margin_of_safety is not None
        assert turnaround.margin_of_safety is not None
        # Steady (25% base) should have tighter MoS than Turnaround (40% base)
        assert steady.margin_of_safety < turnaround.margin_of_safety
        # Both buy_prices equal intrinsic (same inputs -> same intrinsic)
        assert steady.buy_price == turnaround.buy_price
        # Tighter MoS = lower sell price
        assert steady.sell_price < turnaround.sell_price

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


class TestLayer1InputValidation:
    """Tests for Layer 1 input validation: share bounds and market-cap cross-check."""

    def test_shares_too_low_returns_invalid(self, healthy_period, price_bars):
        """shares_outstanding=50 should be rejected as out of bounds."""
        profile = AssetProfile(
            ticker="TINY",
            name="Tiny Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("1000000"),
            shares_outstanding=50,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.invalid_reason == "shares_outstanding_out_of_bounds"

    def test_shares_too_high_returns_invalid(self, healthy_period, price_bars):
        """shares_outstanding=100B should be rejected as out of bounds."""
        profile = AssetProfile(
            ticker="HUGE",
            name="Huge Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("10000000000000"),
            shares_outstanding=100_000_000_000,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.invalid_reason == "shares_outstanding_out_of_bounds"

    def test_shares_at_lower_bound_accepted(self, healthy_period, price_bars):
        """shares_outstanding=100,000 (lower bound) should be accepted."""
        profile = AssetProfile(
            ticker="LBND",
            name="Lower Bound Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("50000000"),
            shares_outstanding=100_000,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.invalid_reason is None

    def test_shares_at_upper_bound_accepted(self, healthy_period, price_bars):
        """shares_outstanding=50B (upper bound) should be accepted."""
        profile = AssetProfile(
            ticker="UBND",
            name="Upper Bound Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("5000000000000"),
            shares_outstanding=50_000_000_000,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.invalid_reason is None

    def test_implied_market_cap_too_low(self, healthy_period):
        """actual_price * shares < $1M should be rejected."""
        profile = AssetProfile(
            ticker="MCLO",
            name="MicroCap Low",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("500000"),
            shares_outstanding=100_000,
        )
        # price=0.50 * 100,000 shares = $50K implied market cap (< $1M)
        bars = [
            PriceBar(
                date="2025-09-28",
                open=Decimal("0.50"),
                high=Decimal("0.55"),
                low=Decimal("0.45"),
                close=Decimal("0.50"),
                volume=1000,
            ),
        ]
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.invalid_reason == "implied_market_cap_unreasonable"

    def test_implied_market_cap_too_high(self, healthy_period):
        """actual_price * shares > $10T should be rejected."""
        profile = AssetProfile(
            ticker="MCHI",
            name="MegaCap High",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("15000000000000"),
            shares_outstanding=50_000_000_000,
        )
        # price=500,000 * 50B shares = $25,000T implied market cap (> $10T)
        bars = [
            PriceBar(
                date="2025-09-28",
                open=Decimal("500000"),
                high=Decimal("510000"),
                low=Decimal("490000"),
                close=Decimal("500000"),
                volume=1000,
            ),
        ]
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.invalid_reason == "implied_market_cap_unreasonable"

    def test_no_actual_price_skips_market_cap_check(self, healthy_period):
        """No price bars means no actual_price, so market cap check is skipped."""
        profile = AssetProfile(
            ticker="NOPR",
            name="No Price Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("500000"),
            shares_outstanding=100_000,
        )
        result = compute_price_targets(
            period=healthy_period,
            profile=profile,
            price_bars=[],
            conviction_level=ConvictionLevel.HIGH,
        )
        # Market cap check skipped because actual_price is None
        # invalid_reason should NOT be "implied_market_cap_unreasonable"
        assert result.invalid_reason != "implied_market_cap_unreasonable"


class TestLayer2PerMethodBounds:
    """Layer 2: Per-method output must be >= $0.01 and <= 100x actual_price."""

    def test_tiny_method_result_excluded(self, healthy_profile, price_bars):
        """A method producing < $0.01/share should be excluded from valuation_methods."""
        # Create period with tiny cash flows relative to 15B shares
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("1000"),
                gross_profit=Decimal("500"),
                ebit=Decimal("100"),
                net_income=Decimal("50"),
                shares_outstanding=15000000000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("10000"),
                current_assets=Decimal("5000"),
                cash_and_equivalents=Decimal("1000"),
                current_liabilities=Decimal("3000"),
                long_term_debt=Decimal("2000"),
                total_equity=Decimal("5000"),
                shares_outstanding=15000000000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("200"),
                capital_expenditures=Decimal("-50"),
                dividends_paid=Decimal("-10"),
                share_repurchases=Decimal("-20"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        # With 15B shares and tiny cash flows, methods producing < $0.01 are excluded
        if result.valuation_methods:
            for method_price in result.valuation_methods.values():
                assert method_price >= 0.01

    def test_method_exceeding_100x_actual_excluded(self, healthy_profile, price_bars):
        """A method producing > 100x actual_price should be excluded."""
        # actual_price from price_bars is $197. 100x = $19,700.
        # Create financials with extremely high cash flows to inflate valuations
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("100000000000000"),
                gross_profit=Decimal("50000000000000"),
                ebit=Decimal("40000000000000"),
                net_income=Decimal("30000000000000"),
                shares_outstanding=15000000000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("500000000000000"),
                current_assets=Decimal("200000000000000"),
                cash_and_equivalents=Decimal("100000000000000"),
                current_liabilities=Decimal("50000000000000"),
                long_term_debt=Decimal("10000000000000"),
                total_equity=Decimal("400000000000000"),
                shares_outstanding=15000000000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("35000000000000"),
                capital_expenditures=Decimal("-5000000000000"),
                dividends_paid=Decimal("-1000000000000"),
                share_repurchases=Decimal("-2000000000000"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        # Any surviving method must be <= 100x actual_price ($19,700)
        if result.valuation_methods:
            for method_price in result.valuation_methods.values():
                assert method_price <= 100.0 * 197.0

    def test_healthy_data_passes_layer2(self, healthy_period, healthy_profile, price_bars):
        """Healthy data should not trigger Layer 2 rejection."""
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.intrinsic_value is not None
        assert result.invalid_reason is None


class TestFilterOutlierMethods:
    """Unit tests for _filter_outlier_methods helper."""

    def test_high_outlier_excluded(self):
        """A method 20x the median should be excluded."""
        methods = {"dcf": 50.0, "ev_fcf": 55.0, "acquirers_multiple": 52.0, "shareholder_yield": 5000.0}
        filtered = _filter_outlier_methods(methods)
        assert "shareholder_yield" not in filtered
        assert len(filtered) == 3

    def test_all_methods_agree_kept(self):
        """When all methods are within 10x of median, all are kept."""
        methods = {"dcf": 50.0, "ev_fcf": 55.0, "acquirers_multiple": 48.0, "shareholder_yield": 60.0}
        filtered = _filter_outlier_methods(methods)
        assert len(filtered) == 4

    def test_single_method_kept(self):
        """A single method cannot be outlier-filtered."""
        methods = {"dcf": 50.0}
        filtered = _filter_outlier_methods(methods)
        assert len(filtered) == 1

    def test_low_outlier_excluded(self):
        """A method < 0.1x median should be excluded."""
        methods = {"dcf": 50.0, "ev_fcf": 55.0, "acquirers_multiple": 52.0, "shareholder_yield": 2.0}
        filtered = _filter_outlier_methods(methods)
        assert "shareholder_yield" not in filtered

    def test_empty_dict_returns_empty(self):
        """Empty input returns empty output."""
        filtered = _filter_outlier_methods({})
        assert len(filtered) == 0

    def test_two_methods_both_kept_when_close(self):
        """Two methods within 10x of each other are both kept."""
        methods = {"dcf": 50.0, "ev_fcf": 55.0}
        filtered = _filter_outlier_methods(methods)
        assert len(filtered) == 2

    def test_zero_median_returns_all(self):
        """If median is zero or negative, no filtering occurs."""
        methods = {"dcf": 0.0, "ev_fcf": 0.0, "acquirers_multiple": 50.0}
        filtered = _filter_outlier_methods(methods)
        assert len(filtered) == 3


class TestLayer3CrossMethodConsistency:
    """Layer 3: Exclude methods that differ > 10x from median."""

    def test_outlier_method_excluded(self):
        """A method 20x the median should be excluded."""
        methods = {"dcf": 50.0, "ev_fcf": 55.0, "acquirers_multiple": 52.0, "shareholder_yield": 5000.0}
        filtered = _filter_outlier_methods(methods)
        assert "shareholder_yield" not in filtered
        assert len(filtered) == 3

    def test_all_methods_agree_kept(self):
        """When all methods are within 10x of median, all are kept."""
        methods = {"dcf": 50.0, "ev_fcf": 55.0, "acquirers_multiple": 48.0, "shareholder_yield": 60.0}
        filtered = _filter_outlier_methods(methods)
        assert len(filtered) == 4

    def test_single_method_kept(self):
        """A single method cannot be outlier-filtered."""
        methods = {"dcf": 50.0}
        filtered = _filter_outlier_methods(methods)
        assert len(filtered) == 1

    def test_low_outlier_excluded(self):
        """A method < 0.1x median should be excluded."""
        methods = {"dcf": 50.0, "ev_fcf": 55.0, "acquirers_multiple": 52.0, "shareholder_yield": 2.0}
        filtered = _filter_outlier_methods(methods)
        assert "shareholder_yield" not in filtered


class TestLayer4FinalOutputValidation:
    """Layer 4: Final intrinsic value must be within bounds."""

    def test_extreme_low_relative_to_price(self):
        """Intrinsic value < 1% of actual_price -> invalid."""
        reason = _validate_final_output(intrinsic_value=0.50, actual_price=100.0)
        assert reason == "intrinsic_value_extreme"

    def test_extreme_high_relative_to_price(self):
        """Intrinsic value > 50x actual_price -> invalid."""
        reason = _validate_final_output(intrinsic_value=6000.0, actual_price=100.0)
        assert reason == "intrinsic_value_extreme"

    def test_within_bounds_returns_none(self):
        """Intrinsic value within 1%-50x of actual_price -> valid."""
        reason = _validate_final_output(intrinsic_value=150.0, actual_price=100.0)
        assert reason is None

    def test_no_actual_price_absolute_low(self):
        """Without actual_price, intrinsic_value < $0.10 -> invalid."""
        reason = _validate_final_output(intrinsic_value=0.05, actual_price=None)
        assert reason == "intrinsic_value_extreme"

    def test_no_actual_price_absolute_high(self):
        """Without actual_price, intrinsic_value > $1M -> invalid."""
        reason = _validate_final_output(intrinsic_value=1_500_000.0, actual_price=None)
        assert reason == "intrinsic_value_extreme"

    def test_no_actual_price_within_absolute_bounds(self):
        """Without actual_price, value in $0.10-$1M range -> valid."""
        reason = _validate_final_output(intrinsic_value=50.0, actual_price=None)
        assert reason is None
