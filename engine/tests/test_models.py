"""Tests for core financial data models."""

import pytest
from decimal import Decimal
from margin_engine.models.financial import (
    IncomeStatement,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    PriceBar,
    AssetProfile,
    GICSSector,
)


class TestIncomeStatement:
    def test_create_income_statement(self):
        stmt = IncomeStatement(
            revenue=Decimal("394328000000"),
            cost_of_revenue=Decimal("223546000000"),
            gross_profit=Decimal("170782000000"),
            sga_expense=Decimal("24932000000"),
            rd_expense=Decimal("29915000000"),
            depreciation=Decimal("11519000000"),
            ebit=Decimal("114301000000"),
            interest_expense=Decimal("3933000000"),
            tax_provision=Decimal("16741000000"),
            net_income=Decimal("96995000000"),
            shares_outstanding=15460000000,
        )
        assert stmt.revenue == Decimal("394328000000")
        assert stmt.gross_margin == pytest.approx(0.4331, abs=0.001)
        assert stmt.net_margin == pytest.approx(0.2460, abs=0.001)

    def test_gross_margin_calculation(self):
        stmt = IncomeStatement(
            revenue=Decimal("100"),
            cost_of_revenue=Decimal("60"),
            gross_profit=Decimal("40"),
            ebit=Decimal("20"),
            net_income=Decimal("15"),
            shares_outstanding=100,
        )
        assert stmt.gross_margin == pytest.approx(0.40)

    def test_zero_revenue_margin(self):
        stmt = IncomeStatement(
            revenue=Decimal("0"),
            cost_of_revenue=Decimal("0"),
            gross_profit=Decimal("0"),
            ebit=Decimal("0"),
            net_income=Decimal("-100"),
            shares_outstanding=100,
        )
        assert stmt.gross_margin == 0.0
        assert stmt.net_margin == 0.0


class TestBalanceSheet:
    def test_create_balance_sheet(self):
        bs = BalanceSheet(
            total_assets=Decimal("352583000000"),
            current_assets=Decimal("143566000000"),
            cash_and_equivalents=Decimal("29965000000"),
            receivables=Decimal("60932000000"),
            total_liabilities=Decimal("290437000000"),
            current_liabilities=Decimal("145308000000"),
            long_term_debt=Decimal("98959000000"),
            total_equity=Decimal("62146000000"),
            retained_earnings=Decimal("4336000000"),
            pp_and_e=Decimal("43715000000"),
            shares_outstanding=15460000000,
        )
        assert bs.working_capital == Decimal("143566000000") - Decimal("145308000000")
        assert bs.debt_to_equity == pytest.approx(1.5925, abs=0.001)
        assert bs.current_ratio == pytest.approx(0.9880, abs=0.001)

    def test_working_capital(self):
        bs = BalanceSheet(
            total_assets=Decimal("1000"),
            current_assets=Decimal("500"),
            total_liabilities=Decimal("600"),
            current_liabilities=Decimal("300"),
            total_equity=Decimal("400"),
            shares_outstanding=100,
        )
        assert bs.working_capital == Decimal("200")

    def test_zero_equity_debt_ratio(self):
        bs = BalanceSheet(
            total_assets=Decimal("1000"),
            current_assets=Decimal("500"),
            total_liabilities=Decimal("1000"),
            current_liabilities=Decimal("300"),
            total_equity=Decimal("0"),
            shares_outstanding=100,
        )
        assert bs.debt_to_equity == float("inf")


class TestCashFlowStatement:
    def test_create_cash_flow(self):
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("110543000000"),
            capital_expenditures=Decimal("-10959000000"),
            dividends_paid=Decimal("-15025000000"),
            share_repurchases=Decimal("-77550000000"),
            share_issuance=Decimal("0"),
        )
        assert cf.free_cash_flow == Decimal("110543000000") + Decimal("-10959000000")
        assert cf.net_buybacks == Decimal("77550000000") - Decimal("0")

    def test_fcf_calculation(self):
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("100"),
            capital_expenditures=Decimal("-30"),
        )
        assert cf.free_cash_flow == Decimal("70")


class TestFinancialPeriod:
    def test_create_period_with_two_years(self):
        current_income = IncomeStatement(
            revenue=Decimal("200"),
            cost_of_revenue=Decimal("100"),
            gross_profit=Decimal("100"),
            ebit=Decimal("50"),
            net_income=Decimal("30"),
            shares_outstanding=100,
        )
        prior_income = IncomeStatement(
            revenue=Decimal("180"),
            cost_of_revenue=Decimal("100"),
            gross_profit=Decimal("80"),
            ebit=Decimal("40"),
            net_income=Decimal("20"),
            shares_outstanding=100,
        )
        current_balance = BalanceSheet(
            total_assets=Decimal("500"),
            current_assets=Decimal("200"),
            total_liabilities=Decimal("300"),
            current_liabilities=Decimal("150"),
            total_equity=Decimal("200"),
            shares_outstanding=100,
        )
        prior_balance = BalanceSheet(
            total_assets=Decimal("480"),
            current_assets=Decimal("190"),
            total_liabilities=Decimal("290"),
            current_liabilities=Decimal("140"),
            total_equity=Decimal("190"),
            shares_outstanding=100,
        )
        current_cf = CashFlowStatement(
            operating_cash_flow=Decimal("40"),
            capital_expenditures=Decimal("-10"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=current_income,
            prior_income=prior_income,
            current_balance=current_balance,
            prior_balance=prior_balance,
            current_cash_flow=current_cf,
        )
        assert period.period_end == "2024-09-28"
        assert period.revenue_growth == pytest.approx(0.1111, abs=0.001)


class TestAssetProfile:
    def test_create_asset_profile(self):
        profile = AssetProfile(
            ticker="AAPL",
            name="Apple Inc.",
            sector=GICSSector.TECHNOLOGY,
            sub_industry="Technology Hardware, Storage & Peripherals",
            market_cap=Decimal("3500000000000"),
            avg_daily_volume=Decimal("55000000"),
            years_of_history=20,
        )
        assert profile.ticker == "AAPL"
        assert profile.sector == GICSSector.TECHNOLOGY
        assert profile.is_excluded is False

    def test_financials_excluded(self):
        profile = AssetProfile(
            ticker="JPM",
            name="JPMorgan Chase",
            sector=GICSSector.FINANCIALS,
            market_cap=Decimal("500000000000"),
            avg_daily_volume=Decimal("10000000"),
            years_of_history=20,
        )
        assert profile.is_excluded is True

    def test_real_estate_excluded(self):
        profile = AssetProfile(
            ticker="AMT",
            name="American Tower",
            sector=GICSSector.REAL_ESTATE,
            market_cap=Decimal("100000000000"),
            avg_daily_volume=Decimal("5000000"),
            years_of_history=15,
        )
        assert profile.is_excluded is True


class TestPriceBar:
    def test_create_price_bar(self):
        bar = PriceBar(
            date="2024-01-15",
            open=Decimal("185.50"),
            high=Decimal("187.20"),
            low=Decimal("184.80"),
            close=Decimal("186.90"),
            volume=50000000,
            adj_close=Decimal("186.90"),
        )
        assert bar.close == Decimal("186.90")
