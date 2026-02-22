"""Golden test cases for valuation computation — regression safety net.

These tests use fixed inputs and assert exact known outputs to catch any
accidental changes to the valuation math. Every value was computed once
from the deterministic engine and then hard-coded as the golden expected.
"""

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
from margin_engine.models.scoring import ConvictionLevel, GrowthStage
from margin_engine.scoring.quantitative.price_targets import compute_price_targets

# ---------------------------------------------------------------------------
# Fixtures: each test builds its own complete fixture for isolation.
# ---------------------------------------------------------------------------


def _make_all_valid_period() -> FinancialPeriod:
    """Period where all 4 valuation methods produce valid numbers."""
    return FinancialPeriod(
        period_end="2025-09-28",
        filing_date="2025-11-01",
        current_income=IncomeStatement(
            revenue=Decimal("400000000000"),
            gross_profit=Decimal("180000000000"),
            ebit=Decimal("120000000000"),
            net_income=Decimal("100000000000"),
            shares_outstanding=15_000_000_000,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("350000000000"),
            current_assets=Decimal("130000000000"),
            cash_and_equivalents=Decimal("30000000000"),
            current_liabilities=Decimal("120000000000"),
            long_term_debt=Decimal("100000000000"),
            total_equity=Decimal("60000000000"),
            shares_outstanding=15_000_000_000,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("110000000000"),
            capital_expenditures=Decimal("-10000000000"),  # FCF = 100B
            dividends_paid=Decimal("-15000000000"),
            share_repurchases=Decimal("-90000000000"),
        ),
    )


def _make_all_valid_profile() -> AssetProfile:
    return AssetProfile(
        ticker="GOLD",
        name="Golden Test Corp",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("2550000000000"),
        shares_outstanding=15_000_000_000,
    )


def _make_all_valid_bars() -> list[PriceBar]:
    return [
        PriceBar(
            date="2025-09-28",
            open=Decimal("168"),
            high=Decimal("172"),
            low=Decimal("167"),
            close=Decimal("170"),
            volume=50_000_000,
        ),
        PriceBar(
            date="2025-09-27",
            open=Decimal("165"),
            high=Decimal("169"),
            low=Decimal("164"),
            close=Decimal("168"),
            volume=45_000_000,
        ),
    ]


class TestGoldenAllMethodsValid:
    """All 4 valuation methods valid -> known MIV, MoS, Buy/Sell."""

    def test_normal_all_methods_valid(self):
        """Fixed inputs -> deterministic outputs. Assert exact golden values."""
        period = _make_all_valid_period()
        profile = _make_all_valid_profile()
        bars = _make_all_valid_bars()

        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=bars,
            conviction_level=ConvictionLevel.HIGH,
            growth_stage=GrowthStage.STEADY_GROWTH,
            growth_rate=0.05,
            discount_rate=0.10,
            terminal_growth_rate=0.025,
            projection_years=10,
        )

        # No errors
        assert result.invalid_reason is None

        # Golden MIV and price targets
        assert result.margin_invest_value == pytest.approx(115.35, rel=1e-3)
        assert result.buy_price == pytest.approx(81.14, rel=1e-3)
        assert result.sell_price == pytest.approx(149.57, rel=1e-3)
        assert result.actual_price == pytest.approx(170.0, rel=1e-3)
        assert result.price_upside == pytest.approx(-0.3214, rel=1e-3)
        assert result.margin_of_safety == pytest.approx(0.2966, rel=1e-3)

        # All 4 methods present with golden per-share values
        assert result.valuation_methods is not None
        assert len(result.valuation_methods) == 4
        assert result.valuation_methods["dcf"] == pytest.approx(109.30, rel=1e-3)
        assert result.valuation_methods["ev_fcf"] == pytest.approx(95.33, rel=1e-3)
        assert result.valuation_methods["acquirers_multiple"] == pytest.approx(91.33, rel=1e-3)
        assert result.valuation_methods["shareholder_yield"] == pytest.approx(175.0, rel=1e-3)

        # Audit trail
        audit = result.valuation_audit
        assert audit is not None
        assert audit.mos_base == pytest.approx(0.25, rel=1e-3)
        assert audit.mos_cv == pytest.approx(0.2864, rel=1e-2)
        assert audit.was_clamped is False

        # All methods included with correct renormalized weights (sum to 1.0)
        for m in audit.methods:
            assert m.included is True
            assert m.renormalized_weight == pytest.approx(m.weight, rel=1e-3)


class TestGoldenNegativeFCF:
    """Negative FCF -> DCF + EV/FCF return None -> 2 methods with renormalized weights."""

    def test_negative_fcf_two_methods_only(self):
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("50000000000"),
                gross_profit=Decimal("20000000000"),
                ebit=Decimal("8000000000"),
                net_income=Decimal("5000000000"),
                shares_outstanding=2_000_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("100000000000"),
                current_assets=Decimal("30000000000"),
                cash_and_equivalents=Decimal("10000000000"),
                current_liabilities=Decimal("20000000000"),
                long_term_debt=Decimal("25000000000"),
                total_equity=Decimal("50000000000"),
                shares_outstanding=2_000_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("5000000000"),
                capital_expenditures=Decimal("-12000000000"),  # FCF = -7B
                dividends_paid=Decimal("-3000000000"),
                share_repurchases=Decimal("-2000000000"),
            ),
        )
        profile = AssetProfile(
            ticker="NEGF",
            name="Negative FCF Corp",
            sector=GICSSector.INDUSTRIALS,
            market_cap=Decimal("100000000000"),
            shares_outstanding=2_000_000_000,
        )
        bars = [
            PriceBar(
                date="2025-09-28",
                open=Decimal("48"),
                high=Decimal("52"),
                low=Decimal("47"),
                close=Decimal("50"),
                volume=30_000_000,
            ),
        ]

        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=bars,
            conviction_level=ConvictionLevel.HIGH,
            growth_stage=GrowthStage.STEADY_GROWTH,
        )

        assert result.invalid_reason is None

        # Golden values with only 2 methods (acquirers_multiple + shareholder_yield)
        assert result.margin_invest_value == pytest.approx(51.50, rel=1e-3)
        assert result.buy_price == pytest.approx(37.16, rel=1e-3)
        assert result.sell_price == pytest.approx(65.84, rel=1e-3)
        assert result.actual_price == pytest.approx(50.0, rel=1e-3)
        assert result.price_upside == pytest.approx(0.03, rel=1e-3)
        assert result.margin_of_safety == pytest.approx(0.2784, rel=1e-3)

        # Only 2 methods survived
        assert result.valuation_methods is not None
        assert "dcf" not in result.valuation_methods
        assert "ev_fcf" not in result.valuation_methods
        assert result.valuation_methods["acquirers_multiple"] == pytest.approx(40.50, rel=1e-3)
        assert result.valuation_methods["shareholder_yield"] == pytest.approx(62.50, rel=1e-3)

        # Renormalized weights: acq 0.20/(0.20+0.20) = 0.50, shy = 0.50
        audit = result.valuation_audit
        assert audit is not None
        for m in audit.methods:
            if m.method in ("dcf", "ev_fcf"):
                assert m.included is False
                assert m.exclusion_reason == "negative_fcf"
                assert m.renormalized_weight is None
            else:
                assert m.included is True
                assert m.renormalized_weight == pytest.approx(0.50, rel=1e-3)


class TestGoldenHighLeverageAcquirersExcluded:
    """Acquirer's implied equity <= 0 -> excluded from consensus (high debt, low EBIT)."""

    def test_high_leverage_acquirers_excluded(self):
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("30000000000"),
                gross_profit=Decimal("10000000000"),
                ebit=Decimal("5000000000"),
                net_income=Decimal("2000000000"),
                shares_outstanding=1_000_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("150000000000"),
                current_assets=Decimal("20000000000"),
                cash_and_equivalents=Decimal("10000000000"),
                current_liabilities=Decimal("30000000000"),
                long_term_debt=Decimal("80000000000"),  # Huge debt
                total_equity=Decimal("20000000000"),
                shares_outstanding=1_000_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("8000000000"),
                capital_expenditures=Decimal("-2000000000"),  # FCF = 6B
                dividends_paid=Decimal("-1000000000"),
                share_repurchases=Decimal("-500000000"),
            ),
        )
        profile = AssetProfile(
            ticker="HLEV",
            name="High Leverage Corp",
            sector=GICSSector.INDUSTRIALS,
            market_cap=Decimal("30000000000"),
            shares_outstanding=1_000_000_000,
        )
        bars = [
            PriceBar(
                date="2025-09-28",
                open=Decimal("29"),
                high=Decimal("32"),
                low=Decimal("28"),
                close=Decimal("30"),
                volume=20_000_000,
            ),
        ]

        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=bars,
            conviction_level=ConvictionLevel.HIGH,
            growth_stage=GrowthStage.STEADY_GROWTH,
        )

        assert result.invalid_reason is None

        # Golden values: 3 methods (dcf, ev_fcf, shareholder_yield)
        assert result.margin_invest_value == pytest.approx(58.66, rel=1e-3)
        assert result.buy_price == pytest.approx(38.13, rel=1e-3)
        assert result.sell_price == pytest.approx(79.19, rel=1e-3)
        assert result.actual_price == pytest.approx(30.0, rel=1e-3)
        assert result.price_upside == pytest.approx(0.9554, rel=1e-3)

        # MoS hit ceiling (0.35) due to high dispersion
        assert result.margin_of_safety == pytest.approx(0.35, rel=1e-3)

        # Acquirer's multiple excluded
        assert result.valuation_methods is not None
        assert "acquirers_multiple" not in result.valuation_methods
        assert "dcf" in result.valuation_methods
        assert "ev_fcf" in result.valuation_methods
        assert "shareholder_yield" in result.valuation_methods

        # Verify exclusion reason in audit
        audit = result.valuation_audit
        assert audit is not None
        acq = next(m for m in audit.methods if m.method == "acquirers_multiple")
        assert acq.included is False
        assert acq.exclusion_reason == "negative_implied_equity"


class TestGoldenCyclicalHigherMoS:
    """Cyclical growth stage -> base MoS 0.35, wider buy/sell spread."""

    def test_cyclical_higher_mos(self):
        """Same financials as all-valid test but CYCLICAL stage widens MoS."""
        period = _make_all_valid_period()
        profile = AssetProfile(
            ticker="CYCL",
            name="Cyclical Corp",
            sector=GICSSector.ENERGY,
            market_cap=Decimal("2550000000000"),
            shares_outstanding=15_000_000_000,
        )
        bars = _make_all_valid_bars()

        result_cyclical = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=bars,
            conviction_level=ConvictionLevel.HIGH,
            growth_stage=GrowthStage.CYCLICAL,
            growth_rate=0.05,
            discount_rate=0.10,
            terminal_growth_rate=0.025,
            projection_years=10,
        )
        result_steady = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=bars,
            conviction_level=ConvictionLevel.HIGH,
            growth_stage=GrowthStage.STEADY_GROWTH,
            growth_rate=0.05,
            discount_rate=0.10,
            terminal_growth_rate=0.025,
            projection_years=10,
        )

        # Same intrinsic value (same financial inputs)
        assert result_cyclical.margin_invest_value == pytest.approx(
            result_steady.margin_invest_value, rel=1e-4
        )

        # Cyclical base MoS = 0.35 vs Steady = 0.25, same CV adjustment
        assert result_cyclical.margin_of_safety == pytest.approx(0.3966, rel=1e-3)
        assert result_steady.margin_of_safety == pytest.approx(0.2966, rel=1e-3)

        # Cyclical golden values
        assert result_cyclical.margin_invest_value == pytest.approx(115.35, rel=1e-3)
        assert result_cyclical.buy_price == pytest.approx(69.60, rel=1e-3)
        assert result_cyclical.sell_price == pytest.approx(161.10, rel=1e-3)

        # Wider spread: lower buy, higher sell
        assert result_cyclical.buy_price < result_steady.buy_price
        assert result_cyclical.sell_price > result_steady.sell_price

        # Verify audit captures cyclical base MoS
        audit = result_cyclical.valuation_audit
        assert audit is not None
        assert audit.mos_base == pytest.approx(0.35, rel=1e-3)


class TestGoldenOutlierMethodRemoved:
    """One method producing 15x median -> excluded by Layer 3 outlier filter."""

    def test_outlier_method_removed(self):
        """Shareholder yield at $750 vs ~$55 median -> filtered as outlier."""
        period = FinancialPeriod(
            period_end="2025-09-28",
            filing_date="2025-11-01",
            current_income=IncomeStatement(
                revenue=Decimal("10000000000"),
                gross_profit=Decimal("4000000000"),
                ebit=Decimal("2000000000"),
                net_income=Decimal("1500000000"),
                shares_outstanding=500_000_000,
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("30000000000"),
                current_assets=Decimal("8000000000"),
                cash_and_equivalents=Decimal("3000000000"),
                current_liabilities=Decimal("5000000000"),
                long_term_debt=Decimal("5000000000"),
                total_equity=Decimal("15000000000"),
                shares_outstanding=500_000_000,
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("2500000000"),
                capital_expenditures=Decimal("-500000000"),  # FCF = 2B
                dividends_paid=Decimal("-8000000000"),  # Huge dividends
                share_repurchases=Decimal("-7000000000"),  # Huge buybacks
            ),
        )
        profile = AssetProfile(
            ticker="OUTL",
            name="Outlier Test Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("20000000000"),
            shares_outstanding=500_000_000,
        )
        bars = [
            PriceBar(
                date="2025-09-28",
                open=Decimal("39"),
                high=Decimal("42"),
                low=Decimal("38"),
                close=Decimal("40"),
                volume=15_000_000,
            ),
        ]

        result = compute_price_targets(
            period=period,
            profile=profile,
            price_bars=bars,
            conviction_level=ConvictionLevel.HIGH,
            growth_stage=GrowthStage.STEADY_GROWTH,
        )

        assert result.invalid_reason is None

        # Golden values: 3 methods (dcf, ev_fcf, acquirers_multiple)
        assert result.margin_invest_value == pytest.approx(57.19, rel=1e-3)
        assert result.buy_price == pytest.approx(42.04, rel=1e-3)
        assert result.sell_price == pytest.approx(72.35, rel=1e-3)
        assert result.actual_price == pytest.approx(40.0, rel=1e-3)
        assert result.price_upside == pytest.approx(0.4298, rel=1e-3)
        assert result.margin_of_safety == pytest.approx(0.265, rel=1e-3)

        # Shareholder yield excluded as outlier (750.0 / median ~56 = ~13.4x)
        assert result.valuation_methods is not None
        assert "shareholder_yield" not in result.valuation_methods
        assert result.valuation_methods["dcf"] == pytest.approx(65.58, rel=1e-3)
        assert result.valuation_methods["ev_fcf"] == pytest.approx(56.0, rel=1e-3)
        assert result.valuation_methods["acquirers_multiple"] == pytest.approx(44.0, rel=1e-3)

        # Verify audit shows outlier_filtered reason
        audit = result.valuation_audit
        assert audit is not None
        shy = next(m for m in audit.methods if m.method == "shareholder_yield")
        assert shy.included is False
        assert shy.exclusion_reason == "outlier_filtered"
        # The raw result was $750/share before filtering
        assert shy.result_per_share == pytest.approx(750.0, rel=1e-3)


class TestGoldenDeterminism:
    """Run twice with identical inputs -> bit-identical results."""

    def test_deterministic_same_inputs_same_outputs(self):
        """Bit-identical results across two independent calls."""
        period = _make_all_valid_period()
        profile = _make_all_valid_profile()
        bars = _make_all_valid_bars()

        kwargs = dict(
            period=period,
            profile=profile,
            price_bars=bars,
            conviction_level=ConvictionLevel.HIGH,
            growth_stage=GrowthStage.STEADY_GROWTH,
            growth_rate=0.05,
            discount_rate=0.10,
            terminal_growth_rate=0.025,
            projection_years=10,
        )

        result_a = compute_price_targets(**kwargs)
        result_b = compute_price_targets(**kwargs)

        # Bit-identical scalar fields
        assert result_a.margin_invest_value == result_b.margin_invest_value
        assert result_a.buy_price == result_b.buy_price
        assert result_a.sell_price == result_b.sell_price
        assert result_a.actual_price == result_b.actual_price
        assert result_a.price_upside == result_b.price_upside
        assert result_a.margin_of_safety == result_b.margin_of_safety
        assert result_a.invalid_reason == result_b.invalid_reason

        # Bit-identical method values
        assert result_a.valuation_methods == result_b.valuation_methods

        # Bit-identical audit
        assert result_a.valuation_audit is not None
        assert result_b.valuation_audit is not None
        assert result_a.valuation_audit.mos_base == result_b.valuation_audit.mos_base
        assert result_a.valuation_audit.mos_cv == result_b.valuation_audit.mos_cv
        assert result_a.valuation_audit.mos_adjustment == result_b.valuation_audit.mos_adjustment
        assert result_a.valuation_audit.was_clamped == result_b.valuation_audit.was_clamped

        for ma, mb in zip(result_a.valuation_audit.methods, result_b.valuation_audit.methods):
            assert ma.method == mb.method
            assert ma.result_per_share == mb.result_per_share
            assert ma.included == mb.included
            assert ma.renormalized_weight == mb.renormalized_weight
            assert ma.exclusion_reason == mb.exclusion_reason
