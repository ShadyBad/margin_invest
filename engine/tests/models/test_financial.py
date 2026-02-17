"""Tests for financial model fields and computed properties."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)


def test_asset_profile_shares_outstanding():
    profile = AssetProfile(
        ticker="AAPL",
        name="Apple Inc.",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("3000000000000"),
        shares_outstanding=15000000000,
    )
    assert profile.shares_outstanding == 15000000000


def test_asset_profile_shares_outstanding_default():
    profile = AssetProfile(
        ticker="AAPL",
        name="Apple Inc.",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("3000000000000"),
    )
    assert profile.shares_outstanding is None


class TestBalanceSheetTotalDebt:
    def test_total_debt_uses_short_term_debt_not_current_liabilities(self):
        """total_debt = long_term_debt + short_term_debt, NOT current_liabilities."""
        bs = BalanceSheet(
            total_assets=Decimal("1000"),
            current_liabilities=Decimal("300"),  # includes AP, accrued expenses, etc.
            long_term_debt=Decimal("200"),
            short_term_debt=Decimal("50"),  # only the financial debt portion
            total_equity=Decimal("500"),
        )
        assert bs.total_debt == Decimal("250")  # 200 + 50, NOT 200 + 300

    def test_total_debt_defaults_short_term_to_zero(self):
        """If short_term_debt is not set, total_debt = long_term_debt only."""
        bs = BalanceSheet(
            total_assets=Decimal("1000"),
            current_liabilities=Decimal("300"),
            long_term_debt=Decimal("200"),
            total_equity=Decimal("500"),
        )
        assert bs.total_debt == Decimal("200")

    def test_total_debt_with_none_long_term(self):
        """If long_term_debt is None, total_debt = short_term_debt only."""
        bs = BalanceSheet(
            total_assets=Decimal("1000"),
            short_term_debt=Decimal("75"),
            total_equity=Decimal("500"),
        )
        assert bs.total_debt == Decimal("75")


def _make_period(
    year: int,
    revenue: Decimal = Decimal("100"),
    ebit: Decimal = Decimal("20"),
    net_income: Decimal = Decimal("15"),
    cfo: Decimal = Decimal("25"),
    capex: Decimal = Decimal("-5"),
    total_equity: Decimal = Decimal("50"),
    total_debt: Decimal = Decimal("20"),
    cash: Decimal = Decimal("10"),
    total_assets: Decimal = Decimal("100"),
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=IncomeStatement(
            revenue=revenue,
            ebit=ebit,
            net_income=net_income,
            cost_of_revenue=revenue * Decimal("0.6"),
            gross_profit=revenue * Decimal("0.4"),
        ),
        current_balance=BalanceSheet(
            total_assets=total_assets,
            total_equity=total_equity,
            long_term_debt=total_debt,
            cash_and_equivalents=cash,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=cfo,
            capital_expenditures=capex,
        ),
    )


class TestFinancialHistory:
    def test_requires_at_least_one_period(self):
        with pytest.raises(ValueError, match="at least 1"):
            FinancialHistory(ticker="TEST", periods=[])

    def test_periods_sorted_by_period_end(self):
        p2020 = _make_period(2020)
        p2021 = _make_period(2021)
        h = FinancialHistory(ticker="TEST", periods=[p2021, p2020])
        assert h.periods[0].period_end == "2020-12-31"
        assert h.periods[1].period_end == "2021-12-31"

    def test_years_of_data(self):
        periods = [_make_period(y) for y in range(2019, 2024)]
        h = FinancialHistory(ticker="TEST", periods=periods)
        assert h.years_of_data == 5

    def test_single_period(self):
        h = FinancialHistory(ticker="SOLO", periods=[_make_period(2023)])
        assert h.years_of_data == 1
        assert h.periods[0].period_end == "2023-12-31"
