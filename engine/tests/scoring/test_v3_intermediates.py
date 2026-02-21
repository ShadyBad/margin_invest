"""Tests for v3 intermediate value calculators."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet, CashFlowStatement, FinancialHistory, FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.v3_intermediates import (
    compute_capital_allocation_composite,
    compute_catalyst_strength,
    compute_compounding_power,
    compute_downside_protection,
    compute_owner_earnings_iv,
    compute_quality_floor_factor,
    compute_valuation_convergence_factor,
)


def _period(
    revenue=Decimal("1000"), ebit=Decimal("200"), net_income=Decimal("160"),
    cost_of_revenue=Decimal("600"), gross_profit=Decimal("400"),
    depreciation=Decimal("50"), total_equity=Decimal("500"),
    long_term_debt=Decimal("200"), short_term_debt=Decimal("100"),
    cash_and_equivalents=Decimal("50"),
    operating_cash_flow=Decimal("250"), capital_expenditures=Decimal("-80"),
    total_assets=Decimal("1500"), period_end="2024-09-28",
    shares_outstanding=100,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=period_end, filing_date="2024-11-01",
        current_income=IncomeStatement(
            revenue=revenue, cost_of_revenue=cost_of_revenue,
            gross_profit=gross_profit, ebit=ebit, depreciation=depreciation,
            net_income=net_income, shares_outstanding=shares_outstanding,
        ),
        current_balance=BalanceSheet(
            total_assets=total_assets, total_equity=total_equity,
            long_term_debt=long_term_debt, short_term_debt=short_term_debt,
            cash_and_equivalents=cash_and_equivalents,
            shares_outstanding=shares_outstanding,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=operating_cash_flow,
            capital_expenditures=capital_expenditures,
        ),
    )


class TestComputeOwnerEarningsIv:
    def test_basic_gordon_growth(self):
        """OE=10, WACC=0.10, g=0.03 -> 10 * 1.03 / 0.07 = 147.14"""
        result = compute_owner_earnings_iv(
            owner_earnings_per_share=10.0, wacc=0.10, terminal_growth=0.03,
        )
        assert result == pytest.approx(147.14, rel=0.01)

    def test_zero_owner_earnings(self):
        result = compute_owner_earnings_iv(0.0, 0.10, 0.03)
        assert result == 0.0

    def test_wacc_equals_growth_returns_zero(self):
        result = compute_owner_earnings_iv(10.0, 0.03, 0.03)
        assert result == 0.0

    def test_negative_owner_earnings(self):
        result = compute_owner_earnings_iv(-5.0, 0.10, 0.03)
        assert result == 0.0


class TestComputeCompoundingPower:
    def test_growing_company(self):
        """Incremental ROIC > 0, reinvestment rate > 0, low CV -> positive power."""
        periods = [
            _period(ebit=Decimal("100"), total_equity=Decimal("400"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    operating_cash_flow=Decimal("150"), capital_expenditures=Decimal("-80"),
                    depreciation=Decimal("40"), net_income=Decimal("79"),
                    period_end="2020-12-31"),
            _period(ebit=Decimal("120"), total_equity=Decimal("450"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    operating_cash_flow=Decimal("180"), capital_expenditures=Decimal("-90"),
                    depreciation=Decimal("45"), net_income=Decimal("95"),
                    period_end="2021-12-31"),
            _period(ebit=Decimal("150"), total_equity=Decimal("500"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    operating_cash_flow=Decimal("220"), capital_expenditures=Decimal("-100"),
                    depreciation=Decimal("50"), net_income=Decimal("118"),
                    period_end="2022-12-31"),
            _period(ebit=Decimal("180"), total_equity=Decimal("560"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    operating_cash_flow=Decimal("260"), capital_expenditures=Decimal("-110"),
                    depreciation=Decimal("55"), net_income=Decimal("142"),
                    period_end="2023-12-31"),
            _period(ebit=Decimal("220"), total_equity=Decimal("630"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    operating_cash_flow=Decimal("310"), capital_expenditures=Decimal("-120"),
                    depreciation=Decimal("60"), net_income=Decimal("174"),
                    period_end="2024-12-31"),
        ]
        history = FinancialHistory(ticker="GROW", periods=periods)
        result = compute_compounding_power(history)
        assert result > 0.0

    def test_single_period_returns_zero(self):
        history = FinancialHistory(ticker="ONE", periods=[_period()])
        result = compute_compounding_power(history)
        assert result == 0.0

    def test_negative_incremental_roic(self):
        """Declining NOPAT with growing IC -> negative incremental ROIC -> 0."""
        periods = [
            _period(ebit=Decimal("200"), total_equity=Decimal("400"),
                    period_end="2020-12-31"),
            _period(ebit=Decimal("100"), total_equity=Decimal("600"),
                    period_end="2024-12-31"),
        ]
        history = FinancialHistory(ticker="DECLINE", periods=periods)
        result = compute_compounding_power(history)
        assert result == 0.0

    def test_steady_roic_stability_near_one(self):
        """Steady ROICs -> MAD-based stability near 1.0."""
        # Target ROICs ~ [0.14, 0.15, 0.16, 0.15, 0.155]
        # IC = equity + ltd(200) + std(100) - cash(50) = equity + 250
        # ebit = target_roic * IC / 0.79
        periods = [
            _period(ebit=Decimal("115.19"), total_equity=Decimal("400"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("40"), capital_expenditures=Decimal("-80"),
                    period_end="2020-12-31"),
            _period(ebit=Decimal("132.91"), total_equity=Decimal("450"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("45"), capital_expenditures=Decimal("-90"),
                    period_end="2021-12-31"),
            _period(ebit=Decimal("151.90"), total_equity=Decimal("500"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("50"), capital_expenditures=Decimal("-100"),
                    period_end="2022-12-31"),
            _period(ebit=Decimal("151.90"), total_equity=Decimal("550"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("55"), capital_expenditures=Decimal("-110"),
                    period_end="2023-12-31"),
            _period(ebit=Decimal("166.77"), total_equity=Decimal("600"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("60"), capital_expenditures=Decimal("-120"),
                    period_end="2024-12-31"),
        ]
        history = FinancialHistory(ticker="STEADY", periods=periods)
        result = compute_compounding_power(history)
        assert result > 0.0
        # With MAD-based stability near 1.0, result should be high relative to
        # inc_roic * reinvestment_rate (the stability multiplier is close to 1.0)

    def test_identical_roics_stability_one(self):
        """Identical ROICs [0.12, 0.12, 0.12] -> MAD=0, stability=1.0."""
        # IC = equity + 250; ebit = 0.12 * IC / 0.79
        periods = [
            _period(ebit=Decimal("98.73"), total_equity=Decimal("400"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("40"), capital_expenditures=Decimal("-80"),
                    period_end="2020-12-31"),
            _period(ebit=Decimal("113.92"), total_equity=Decimal("500"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("45"), capital_expenditures=Decimal("-90"),
                    period_end="2022-12-31"),
            _period(ebit=Decimal("129.11"), total_equity=Decimal("600"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("50"), capital_expenditures=Decimal("-100"),
                    period_end="2024-12-31"),
        ]
        history = FinancialHistory(ticker="IDENT", periods=periods)
        result = compute_compounding_power(history)
        # MAD = 0 => stability = 1.0 => result = inc_roic * reinvestment_rate * 1.0
        # inc_roic = 0.12, reinvestment_rate = (100-50)/102 ~ 0.49
        expected = 0.12 * ((100 - 50) / (129.11 * 0.79))
        assert result == pytest.approx(expected, rel=0.02)

    def test_lumpy_roic_positive_result(self):
        """Lumpy ROICs [0.10, 0.25, 0.12, 0.22, 0.14] -> still positive with MAD."""
        # IC = equity + 250; ebit = target_roic * IC / 0.79
        periods = [
            _period(ebit=Decimal("82.28"), total_equity=Decimal("400"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("40"), capital_expenditures=Decimal("-80"),
                    period_end="2020-12-31"),
            _period(ebit=Decimal("221.52"), total_equity=Decimal("450"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("45"), capital_expenditures=Decimal("-90"),
                    period_end="2021-12-31"),
            _period(ebit=Decimal("113.92"), total_equity=Decimal("500"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("50"), capital_expenditures=Decimal("-100"),
                    period_end="2022-12-31"),
            _period(ebit=Decimal("222.78"), total_equity=Decimal("550"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("55"), capital_expenditures=Decimal("-110"),
                    period_end="2023-12-31"),
            _period(ebit=Decimal("150.63"), total_equity=Decimal("600"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("60"), capital_expenditures=Decimal("-120"),
                    period_end="2024-12-31"),
        ]
        history = FinancialHistory(ticker="LUMPY", periods=periods)
        result = compute_compounding_power(history)
        # MAD-based stability ~ 0.71, more forgiving than CV-based ~ 0.65
        assert result > 0.0

    def test_single_outlier_forgiving(self):
        """Single outlier [0.15, 0.15, 0.15, 0.15, 0.40] -> MAD handles outlier well."""
        # Most ROICs match the median (0.15), so MAD = 0, stability = 1.0
        # CV would penalize heavily (stability ~ 0.50)
        periods = [
            _period(ebit=Decimal("123.42"), total_equity=Decimal("400"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("40"), capital_expenditures=Decimal("-80"),
                    period_end="2020-12-31"),
            _period(ebit=Decimal("132.91"), total_equity=Decimal("450"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("45"), capital_expenditures=Decimal("-90"),
                    period_end="2021-12-31"),
            _period(ebit=Decimal("142.41"), total_equity=Decimal("500"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("50"), capital_expenditures=Decimal("-100"),
                    period_end="2022-12-31"),
            _period(ebit=Decimal("151.90"), total_equity=Decimal("550"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("55"), capital_expenditures=Decimal("-110"),
                    period_end="2023-12-31"),
            _period(ebit=Decimal("430.38"), total_equity=Decimal("600"),
                    long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("50"),
                    depreciation=Decimal("60"), capital_expenditures=Decimal("-120"),
                    period_end="2024-12-31"),
        ]
        history = FinancialHistory(ticker="OUTLIER", periods=periods)
        result = compute_compounding_power(history)
        # With MAD: stability = 1.0 (median ROIC is 0.15, most match it)
        # With CV: stability = 0.50 (stdev/mean penalizes the outlier)
        assert result > 0.0
        # MAD gives stability=1.0 (median is 0.15, most values match it)
        # CV would give stability=0.50, halving the result.
        # Under MAD the result exceeds 0.15; under CV it would be ~0.107
        assert result > 0.15


class TestComputeCapitalAllocationComposite:
    def test_all_strong_subfactors(self):
        """All 6 sub-factors present and strong -> score near 1.0."""
        periods = [
            _period(period_end="2020-12-31"),
            _period(period_end="2024-12-31"),
        ]
        history = FinancialHistory(ticker="STRONG", periods=periods)
        result = compute_capital_allocation_composite(
            period=periods[-1],
            history=history,
            buyback_yield=0.05,
            insider_ownership_pct=15.0,
            sbc_pct=0.01,
            recent_acquisition_count=0,
        )
        assert 0.0 <= result <= 1.0

    def test_no_optional_data(self):
        """Missing optional data -> score based on available sub-factors only."""
        history = FinancialHistory(
            ticker="MIN", periods=[_period(), _period(period_end="2023-12-31")]
        )
        result = compute_capital_allocation_composite(
            period=history.periods[-1],
            history=history,
            buyback_yield=None,
            insider_ownership_pct=None,
            sbc_pct=None,
            recent_acquisition_count=0,
        )
        assert 0.0 <= result <= 1.0

    def test_returns_float(self):
        history = FinancialHistory(
            ticker="T", periods=[_period(), _period(period_end="2023-12-31")]
        )
        result = compute_capital_allocation_composite(
            period=history.periods[-1],
            history=history,
            buyback_yield=None,
            insider_ownership_pct=None,
            sbc_pct=None,
            recent_acquisition_count=0,
        )
        assert isinstance(result, float)


class TestComputeCatalystStrength:
    def test_weighted_blend_mixed(self):
        """30, 70, 50 sorted = [70, 50, 30]: 0.50*70 + 0.30*50 + 0.20*30 = 56.0."""
        assert compute_catalyst_strength(30.0, 70.0, 50.0) == pytest.approx(56.0)

    def test_all_zero(self):
        """All zero signals: result = 0.0."""
        assert compute_catalyst_strength(0.0, 0.0, 0.0) == pytest.approx(0.0)

    def test_single_strong_signal(self):
        """Single signal at 90 with others low: 0.50*90 + 0.30*20 + 0.20*10 = 53.0."""
        assert compute_catalyst_strength(90.0, 10.0, 20.0) == pytest.approx(53.0)

    def test_catalyst_all_three_at_70(self):
        """Uniform signals: 0.50*70 + 0.30*70 + 0.20*70 = 70.0."""
        result = compute_catalyst_strength(70.0, 70.0, 70.0)
        assert result == pytest.approx(70.0)

    def test_catalyst_single_strong_signal_others_zero(self):
        """Single signal at 90 with others at 0: 0.50*90 = 45.0 (was 90.0)."""
        result = compute_catalyst_strength(0.0, 0.0, 90.0)
        assert result == pytest.approx(45.0)

    def test_catalyst_mixed_signals(self):
        """80, 50, 20: 0.50*80 + 0.30*50 + 0.20*20 = 59.0."""
        result = compute_catalyst_strength(80.0, 50.0, 20.0)
        assert result == pytest.approx(59.0)


class TestComputeQualityFloorFactor:
    def test_above_threshold(self):
        assert compute_quality_floor_factor(0.12, roic_improving=False) == pytest.approx(1.0)

    def test_below_threshold_improving(self):
        result = compute_quality_floor_factor(0.04, roic_improving=True)
        assert 0.5 <= result < 1.0

    def test_below_threshold_not_improving(self):
        assert compute_quality_floor_factor(0.04, roic_improving=False) == pytest.approx(0.0)

    def test_zero_roic_improving(self):
        assert compute_quality_floor_factor(0.0, roic_improving=True) == pytest.approx(0.5)

    def test_exactly_at_threshold(self):
        assert compute_quality_floor_factor(0.08, roic_improving=False) == pytest.approx(1.0)


class TestComputeValuationConvergenceFactor:
    def test_four_converging(self):
        assert compute_valuation_convergence_factor(4) == pytest.approx(1.0)

    def test_three_converging(self):
        assert compute_valuation_convergence_factor(3) == pytest.approx(0.75)

    def test_two_converging(self):
        assert compute_valuation_convergence_factor(2) == pytest.approx(0.75)

    def test_zero_converging(self):
        assert compute_valuation_convergence_factor(0) == pytest.approx(0.75)


class TestComputeDownsideProtection:
    def test_price_well_above_floor(self):
        loss, passed = compute_downside_protection(100.0, 30.0)
        assert loss == pytest.approx(0.70)
        assert passed is False

    def test_price_near_floor(self):
        loss, passed = compute_downside_protection(100.0, 60.0)
        assert loss == pytest.approx(0.40)
        assert passed is True

    def test_floor_above_price(self):
        loss, passed = compute_downside_protection(50.0, 60.0)
        assert loss == pytest.approx(0.0)
        assert passed is True

    def test_zero_price(self):
        loss, passed = compute_downside_protection(0.0, 10.0)
        assert loss == pytest.approx(0.0)
        assert passed is True
