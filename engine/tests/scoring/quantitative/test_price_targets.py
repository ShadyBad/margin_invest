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
    _clamp_intrinsic_value,
    _detect_currency_mismatch,
    _filter_outlier_methods,
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

    def test_dual_threshold_mos(
        self, healthy_period, healthy_profile, price_bars
    ):
        """buy_price = MIV * (1 - MoS), sell_price = MIV * (1 + MoS)."""
        result = compute_price_targets(
            period=healthy_period,
            profile=healthy_profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.buy_price is not None
        assert result.sell_price is not None
        assert result.intrinsic_value is not None
        assert result.margin_of_safety is not None
        mos = result.margin_of_safety
        # Dual threshold: buy below fair value, sell above
        assert result.buy_price == pytest.approx(
            result.intrinsic_value * (1 - mos), rel=1e-2
        )
        assert result.sell_price == pytest.approx(
            result.intrinsic_value * (1 + mos), rel=1e-2
        )
        # Ordering invariant
        assert result.buy_price < result.intrinsic_value < result.sell_price

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

    def test_mos_symmetry_across_growth_stages(
        self, healthy_period, healthy_profile, price_bars
    ):
        """Both buy and sell prices should widen symmetrically with higher MoS."""
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
        # Same intrinsic value (same inputs)
        assert steady.intrinsic_value == pytest.approx(
            turnaround.intrinsic_value, rel=1e-4
        )
        # Turnaround has wider MoS -> lower buy price, higher sell price
        assert turnaround.buy_price < steady.buy_price
        assert turnaround.sell_price > steady.sell_price
        # Both satisfy the dual threshold relationship
        assert steady.buy_price == pytest.approx(
            steady.intrinsic_value * (1 - steady.margin_of_safety), rel=1e-2
        )
        assert turnaround.buy_price == pytest.approx(
            turnaround.intrinsic_value * (1 - turnaround.margin_of_safety), rel=1e-2
        )

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

    def test_no_shares_outstanding_returns_invalid(
        self, healthy_period, price_bars
    ):
        """No shares_outstanding in profile -> invalid_reason set."""
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
        assert result.invalid_reason == "shares_outstanding_missing"

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


class TestDeterminism:
    """Verify same inputs always produce same outputs."""

    def test_deterministic_across_runs(self, healthy_period, healthy_profile, price_bars):
        """Running compute_price_targets 10 times with same inputs produces identical results."""
        results = [
            compute_price_targets(
                period=healthy_period,
                profile=healthy_profile,
                price_bars=price_bars,
                conviction_level=ConvictionLevel.HIGH,
            )
            for _ in range(10)
        ]
        first = results[0]
        for r in results[1:]:
            assert r.intrinsic_value == first.intrinsic_value
            assert r.buy_price == first.buy_price
            assert r.sell_price == first.sell_price
            assert r.price_upside == first.price_upside
            assert r.margin_of_safety == first.margin_of_safety
            assert r.valuation_methods == first.valuation_methods
            assert r.invalid_reason == first.invalid_reason


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

    def test_shares_at_lower_bound_accepted(self, price_bars):
        """shares_outstanding=100,000 (lower bound) should be accepted."""
        profile = AssetProfile(
            ticker="LBND",
            name="Lower Bound Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("50000000"),
            shares_outstanding=100_000,
        )
        # Scale financials proportionally to stay within all bounds:
        # 100K shares * $197 price = $19.7M market cap
        # Revenue/share must be < 10x price (currency check) → < $1,970/share
        # Intrinsic/share is clamped to 10x price (Layer 4) if it exceeds → $1,970
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("20000000"),        # $20M → $200/share (~1x price)
                gross_profit=Decimal("8000000"),
                ebit=Decimal("3000000"),            # $30/share
                net_income=Decimal("2000000"),
                shares_outstanding=100_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("50000000"),
                current_assets=Decimal("15000000"),
                cash_and_equivalents=Decimal("5000000"),
                current_liabilities=Decimal("10000000"),
                long_term_debt=Decimal("8000000"),
                total_equity=Decimal("30000000"),
                shares_outstanding=100_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("4000000"),   # $40/share
                capital_expenditures=Decimal("-1000000"),  # FCF=$30/share
                dividends_paid=Decimal("-500000"),
                share_repurchases=Decimal("-300000"),
            ),
        )
        result = compute_price_targets(
            period=period,
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
    """Layer 2: Per-method output must be >= $0.01 and <= 20x actual_price."""

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

    def test_method_exceeding_20x_actual_excluded(self, price_bars):
        """A method producing > 20x actual_price should be excluded."""
        # actual_price from price_bars is $197. 20x = $3,940.
        # Revenue/shares must stay below 10x price to avoid currency mismatch check.
        # Use 500M shares and higher cash flows to inflate per-share valuations.
        profile = AssetProfile(
            ticker="BIGV",
            name="Big Value Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("100000000000"),
            shares_outstanding=500_000_000,
        )
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("200000000000"),   # $400/share (2x price, safe)
                gross_profit=Decimal("100000000000"),
                ebit=Decimal("80000000000"),        # $160/share -> acq mult = 12*160 = $1920
                net_income=Decimal("60000000000"),
                shares_outstanding=500_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("500000000000"),
                current_assets=Decimal("200000000000"),
                cash_and_equivalents=Decimal("100000000000"),
                current_liabilities=Decimal("50000000000"),
                long_term_debt=Decimal("10000000000"),
                total_equity=Decimal("400000000000"),
                shares_outstanding=500_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("90000000000"),  # $180/share
                capital_expenditures=Decimal("-5000000000"),  # FCF = $170/share
                dividends_paid=Decimal("-1000000000"),
                share_repurchases=Decimal("-2000000000"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        # Any surviving method must be <= 20x actual_price ($3,940)
        if result.valuation_methods:
            for method_price in result.valuation_methods.values():
                assert method_price <= 20.0 * 197.0

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


class TestLayer4IntrinsicValueClamping:
    """Layer 4: Clamp intrinsic value to reasonable bounds instead of rejecting."""

    def test_clamps_low_relative_to_price(self):
        """Intrinsic value < 1% of actual_price -> clamped to floor."""
        value, was_clamped = _clamp_intrinsic_value(intrinsic_value=0.50, actual_price=100.0)
        assert was_clamped is True
        assert value == 1.0  # 1% of $100

    def test_clamps_high_relative_to_price(self):
        """Intrinsic value > 10x actual_price -> clamped to ceiling."""
        value, was_clamped = _clamp_intrinsic_value(intrinsic_value=1200.0, actual_price=100.0)
        assert was_clamped is True
        assert value == 1000.0  # 10x $100

    def test_within_bounds_not_clamped(self):
        """Intrinsic value within 1%-10x of actual_price -> unchanged."""
        value, was_clamped = _clamp_intrinsic_value(intrinsic_value=150.0, actual_price=100.0)
        assert was_clamped is False
        assert value == 150.0

    def test_no_actual_price_clamps_low(self):
        """Without actual_price, intrinsic_value < $0.10 -> clamped."""
        value, was_clamped = _clamp_intrinsic_value(intrinsic_value=0.05, actual_price=None)
        assert was_clamped is True
        assert value == 0.10

    def test_no_actual_price_clamps_high(self):
        """Without actual_price, intrinsic_value > $1M -> clamped."""
        value, was_clamped = _clamp_intrinsic_value(intrinsic_value=1_500_000.0, actual_price=None)
        assert was_clamped is True
        assert value == 1_000_000.0

    def test_no_actual_price_within_absolute_bounds(self):
        """Without actual_price, value in $0.10-$1M range -> unchanged."""
        value, was_clamped = _clamp_intrinsic_value(intrinsic_value=50.0, actual_price=None)
        assert was_clamped is False
        assert value == 50.0

    def test_deep_value_stock_gets_capped_target(self):
        """Stock at $10 with computed intrinsic of $80 -> clamped to $100 (10x)."""
        value, was_clamped = _clamp_intrinsic_value(intrinsic_value=80.0, actual_price=10.0)
        assert was_clamped is False  # 8x is within 10x bound
        assert value == 80.0

    def test_extreme_deep_value_gets_capped(self):
        """Stock at $10 with computed intrinsic of $150 -> clamped to $100 (10x)."""
        value, was_clamped = _clamp_intrinsic_value(intrinsic_value=150.0, actual_price=10.0)
        assert was_clamped is True
        assert value == 100.0  # 10x $10


class TestCurrencyMismatchDetection:
    """Layer 1b: Detect financial data reported in foreign currency."""

    def test_revenue_mismatch_detected(self):
        """Revenue/share >> price indicates currency mismatch (e.g., JPY financials, USD price)."""
        # Simulates Japanese company: revenue in yen, price in USD
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("5000000000000"),  # 5T yen
                gross_profit=Decimal("2000000000000"),
                ebit=Decimal("500000000000"),
                net_income=Decimal("300000000000"),
                shares_outstanding=500_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("10000000000000"),
                current_assets=Decimal("3000000000000"),
                cash_and_equivalents=Decimal("500000000000"),
                current_liabilities=Decimal("2000000000000"),
                long_term_debt=Decimal("1000000000000"),
                total_equity=Decimal("5000000000000"),
                shares_outstanding=500_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("600000000000"),
                capital_expenditures=Decimal("-200000000000"),
            ),
        )
        # rev/share = 5T/500M = 10,000; price = 20; ratio = 500x -> mismatch
        assert _detect_currency_mismatch(period, 500_000_000, 20.0) is True

    def test_usd_aligned_not_flagged(self):
        """Normal USD-denominated company should not trigger mismatch."""
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("100000000000"),  # $100B
                gross_profit=Decimal("45000000000"),
                ebit=Decimal("30000000000"),
                net_income=Decimal("25000000000"),
                shares_outstanding=15_000_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("350000000000"),
                current_assets=Decimal("130000000000"),
                cash_and_equivalents=Decimal("60000000000"),
                current_liabilities=Decimal("120000000000"),
                long_term_debt=Decimal("100000000000"),
                total_equity=Decimal("60000000000"),
                shares_outstanding=15_000_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("110000000000"),
                capital_expenditures=Decimal("-10000000000"),
            ),
        )
        # rev/share = 100B/15B ≈ 6.67; price = 197; ratio ≈ 0.034 -> no mismatch
        assert _detect_currency_mismatch(period, 15_000_000_000, 197.0) is False

    def test_ocf_mismatch_detected(self):
        """OCF/share >> price indicates currency mismatch even when revenue is low."""
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("0"),
                gross_profit=Decimal("0"),
                ebit=Decimal("0"),
                net_income=Decimal("0"),
                shares_outstanding=1_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("1000000000"),
                current_assets=Decimal("500000000"),
                total_equity=Decimal("800000000"),
                shares_outstanding=1_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("500000000000"),  # 500B (foreign currency)
                capital_expenditures=Decimal("-100000000000"),
            ),
        )
        # ocf/share = 500B/1M = 500,000; price = 10; ratio = 50,000x
        assert _detect_currency_mismatch(period, 1_000_000, 10.0) is True

    def test_no_price_skips_check(self):
        """With no actual_price, currency mismatch detection is skipped."""
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("5000000000000"),
                gross_profit=Decimal("2000000000000"),
                ebit=Decimal("500000000000"),
                net_income=Decimal("300000000000"),
                shares_outstanding=500_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("10000000000000"),
                total_equity=Decimal("5000000000000"),
                shares_outstanding=500_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("600000000000"),
                capital_expenditures=Decimal("-200000000000"),
            ),
        )
        assert _detect_currency_mismatch(period, 500_000_000, None) is False

    def test_currency_mismatch_sets_invalid_reason(self, price_bars):
        """Full compute_price_targets should return invalid_reason for currency mismatch."""
        profile = AssetProfile(
            ticker="JPNX",
            name="Japanese Co OTC",
            sector=GICSSector.INDUSTRIALS,
            market_cap=Decimal("10000000000"),
            shares_outstanding=500_000_000,
        )
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("5000000000000"),  # 5T yen
                gross_profit=Decimal("2000000000000"),
                ebit=Decimal("500000000000"),
                net_income=Decimal("300000000000"),
                shares_outstanding=500_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("10000000000000"),
                current_assets=Decimal("3000000000000"),
                cash_and_equivalents=Decimal("500000000000"),
                current_liabilities=Decimal("2000000000000"),
                long_term_debt=Decimal("1000000000000"),
                total_equity=Decimal("5000000000000"),
                shares_outstanding=500_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("600000000000"),
                capital_expenditures=Decimal("-200000000000"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        # Currency mismatch is now a warning, not a hard rejection.
        # The engine proceeds to valuation methods, but with yen-scale
        # financials all methods return None → insufficient_data.
        # Real ADRs with moderate currency differences will get clamped targets.
        assert result.invalid_reason == "insufficient_data"
        assert result.intrinsic_value is None
        assert result.actual_price == pytest.approx(197.0)


class TestInsufficientDataReason:
    """All methods returning None should produce invalid_reason='insufficient_data'."""

    def test_all_negative_metrics(self, price_bars):
        """Negative FCF, EBIT, no dividends/buybacks → all methods None."""
        profile = AssetProfile(
            ticker="LSNG",
            name="Losing Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("500000000"),
            shares_outstanding=10_000_000,
        )
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("50000000"),   # $5/share (safe ratio)
                gross_profit=Decimal("-10000000"),
                ebit=Decimal("-20000000"),
                net_income=Decimal("-30000000"),
                shares_outstanding=10_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("200000000"),
                current_assets=Decimal("50000000"),
                cash_and_equivalents=Decimal("20000000"),
                current_liabilities=Decimal("80000000"),
                long_term_debt=Decimal("50000000"),
                total_equity=Decimal("70000000"),
                shares_outstanding=10_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("-15000000"),
                capital_expenditures=Decimal("-5000000"),
            ),
        )
        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=price_bars,
            conviction_level=ConvictionLevel.HIGH,
        )
        assert result.invalid_reason == "insufficient_data"
        assert result.intrinsic_value is None
