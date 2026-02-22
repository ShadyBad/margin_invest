"""Tests for competitive dynamics proxies."""

from decimal import Decimal

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.competitive_dynamics import (
    gross_margin_stability,
    relative_revenue_growth,
)


def _make_period(revenue: float, cogs: float) -> FinancialPeriod:
    return FinancialPeriod(
        period_end="2024-12-31",
        filing_date="2025-02-15",
        current_income=IncomeStatement(
            revenue=Decimal(str(revenue)),
            cost_of_revenue=Decimal(str(cogs)),
            gross_profit=Decimal(str(revenue - cogs)),
        ),
        current_balance=BalanceSheet(total_assets=Decimal("5000")),
        current_cash_flow=CashFlowStatement(),
    )


def test_stable_margins():
    """Consistent gross margins should produce low volatility."""
    periods = [_make_period(1000, 500), _make_period(1100, 550), _make_period(1200, 600)]
    history = FinancialHistory(ticker="STABLE", periods=periods)
    result = gross_margin_stability(history)
    assert result.raw_value < 0.02
    assert result.name == "gross_margin_stability"


def test_volatile_margins():
    """Wildly varying margins should produce high volatility."""
    periods = [_make_period(1000, 400), _make_period(1100, 770), _make_period(1200, 480)]
    history = FinancialHistory(ticker="VOLATILE", periods=periods)
    result = gross_margin_stability(history)
    assert result.raw_value > 0.10


def test_relative_growth_outperforming():
    """Company growing faster than sector median should be positive."""
    result = relative_revenue_growth(company_cagr=0.15, sector_median_cagr=0.08)
    assert result.raw_value > 0
    assert result.name == "relative_revenue_growth"


def test_relative_growth_underperforming():
    """Company growing slower than sector median should be negative."""
    result = relative_revenue_growth(company_cagr=0.03, sector_median_cagr=0.08)
    assert result.raw_value < 0
