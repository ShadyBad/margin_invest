"""Tests for moat durability classifier — detects moat signatures from financial patterns."""

from decimal import Decimal

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.moat_durability import moat_durability_score


def _make_period(
    *,
    revenue: Decimal = Decimal("1000"),
    ebit: Decimal = Decimal("200"),
    cost_of_revenue: Decimal = Decimal("600"),
    gross_profit: Decimal = Decimal("400"),
    depreciation: Decimal | None = Decimal("50"),
    total_equity: Decimal = Decimal("500"),
    long_term_debt: Decimal | None = Decimal("200"),
    short_term_debt: Decimal = Decimal("100"),
    cash_and_equivalents: Decimal | None = Decimal("0"),
    operating_cash_flow: Decimal = Decimal("250"),
    capital_expenditures: Decimal = Decimal("-80"),
    period_end: str = "2024-09-28",
) -> FinancialPeriod:
    income = IncomeStatement(
        revenue=revenue,
        cost_of_revenue=cost_of_revenue,
        gross_profit=gross_profit,
        ebit=ebit,
        depreciation=depreciation,
        net_income=ebit * Decimal("0.79"),
        shares_outstanding=100,
    )
    balance = BalanceSheet(
        total_assets=Decimal("1500"),
        total_equity=total_equity,
        long_term_debt=long_term_debt,
        short_term_debt=short_term_debt,
        cash_and_equivalents=cash_and_equivalents,
        shares_outstanding=100,
    )
    cf = CashFlowStatement(
        operating_cash_flow=operating_cash_flow,
        capital_expenditures=capital_expenditures,
    )
    return FinancialPeriod(
        period_end=period_end,
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


class TestMoatDurability:
    def test_scale_economics_detected(self):
        """ROIC increases as revenue grows -> scale economics signature."""
        periods = [
            _make_period(
                revenue=Decimal("500"),
                ebit=Decimal("50"),
                total_equity=Decimal("300"),
                period_end="2019-12-31",
            ),
            _make_period(
                revenue=Decimal("700"),
                ebit=Decimal("100"),
                total_equity=Decimal("400"),
                period_end="2020-12-31",
            ),
            _make_period(
                revenue=Decimal("900"),
                ebit=Decimal("170"),
                total_equity=Decimal("500"),
                period_end="2021-12-31",
            ),
            _make_period(
                revenue=Decimal("1100"),
                ebit=Decimal("260"),
                total_equity=Decimal("600"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1300"),
                ebit=Decimal("370"),
                total_equity=Decimal("700"),
                period_end="2023-12-31",
            ),
        ]
        history = FinancialHistory(ticker="SCALE", periods=periods)
        result = moat_durability_score(history)
        assert result.raw_value >= 1.0
        assert "scale_economics" in result.detail

    def test_capital_efficiency_detected(self):
        """Incremental ROIC >= trailing ROIC -> capital efficiency signature."""
        periods = [
            _make_period(
                ebit=Decimal("100"),
                total_equity=Decimal("400"),
                period_end="2019-12-31",
            ),
            _make_period(
                ebit=Decimal("200"),
                total_equity=Decimal("600"),
                period_end="2023-12-31",
            ),
        ]
        history = FinancialHistory(ticker="CAPEFF", periods=periods)
        result = moat_durability_score(history)
        assert "capital_efficiency" in result.detail

    def test_pricing_power_detected(self):
        """Gross margin expands while revenue grows -> pricing power signature."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                gross_profit=Decimal("400"),
                cost_of_revenue=Decimal("600"),
                period_end="2019-12-31",
            ),
            _make_period(
                revenue=Decimal("1100"),
                gross_profit=Decimal("460"),
                cost_of_revenue=Decimal("640"),
                period_end="2020-12-31",
            ),
            _make_period(
                revenue=Decimal("1200"),
                gross_profit=Decimal("530"),
                cost_of_revenue=Decimal("670"),
                period_end="2021-12-31",
            ),
            _make_period(
                revenue=Decimal("1300"),
                gross_profit=Decimal("610"),
                cost_of_revenue=Decimal("690"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1400"),
                gross_profit=Decimal("700"),
                cost_of_revenue=Decimal("700"),
                period_end="2023-12-31",
            ),
        ]
        history = FinancialHistory(ticker="PRICE", periods=periods)
        result = moat_durability_score(history)
        assert "pricing_power" in result.detail

    def test_no_moat_signatures(self):
        """Declining ROIC with flat margins -> 0 signatures."""
        periods = [
            _make_period(
                ebit=Decimal("200"),
                total_equity=Decimal("400"),
                gross_profit=Decimal("400"),
                period_end="2019-12-31",
            ),
            _make_period(
                ebit=Decimal("150"),
                total_equity=Decimal("500"),
                gross_profit=Decimal("380"),
                period_end="2020-12-31",
            ),
            _make_period(
                ebit=Decimal("100"),
                total_equity=Decimal("600"),
                gross_profit=Decimal("360"),
                period_end="2021-12-31",
            ),
        ]
        history = FinancialHistory(ticker="NOMOAT", periods=periods)
        result = moat_durability_score(history)
        assert result.raw_value == 0.0

    def test_single_period_returns_zero(self):
        """Need 2+ periods to detect moat patterns."""
        history = FinancialHistory(ticker="ONE", periods=[_make_period()])
        result = moat_durability_score(history)
        assert result.raw_value == 0.0

    def test_percentile_rank_placeholder(self):
        history = FinancialHistory(ticker="PH", periods=[_make_period()])
        result = moat_durability_score(history)
        assert result.percentile_rank == 0.0
        assert result.name == "moat_durability"
