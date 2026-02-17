"""Tests for v3 intermediate value calculators."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet, CashFlowStatement, FinancialHistory, FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.v3_intermediates import (
    compute_compounding_power,
    compute_owner_earnings_iv,
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
