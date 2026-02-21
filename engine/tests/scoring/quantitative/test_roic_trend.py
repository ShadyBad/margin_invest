"""Tests for ROIC trend (3-year slope) factor."""

import pytest
from decimal import Decimal

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.roic_trend import roic_trend


def _make_period(ebit: float, equity: float, debt: float, cash: float) -> FinancialPeriod:
    return FinancialPeriod(
        period_end="2024-12-31",
        filing_date="2025-02-15",
        current_income=IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal(str(ebit)),
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("5000"),
            total_equity=Decimal(str(equity)),
            long_term_debt=Decimal(str(debt)),
            cash_and_equivalents=Decimal(str(cash)),
        ),
        current_cash_flow=CashFlowStatement(),
    )


def test_improving_roic_positive_slope():
    """Improving ROIC over 3 periods should produce positive raw_value."""
    periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0),
        _make_period(ebit=120, equity=850, debt=200, cash=50),
        _make_period(ebit=150, equity=900, debt=200, cash=100),
    ]
    history = FinancialHistory(ticker="TEST", periods=periods)
    result = roic_trend(history)
    assert result.raw_value > 0
    assert result.name == "roic_trend"


def test_declining_roic_negative_slope():
    """Declining ROIC should produce negative raw_value."""
    periods = [
        _make_period(ebit=150, equity=900, debt=200, cash=100),
        _make_period(ebit=120, equity=850, debt=200, cash=50),
        _make_period(ebit=100, equity=800, debt=200, cash=0),
    ]
    history = FinancialHistory(ticker="TEST", periods=periods)
    result = roic_trend(history)
    assert result.raw_value < 0


def test_insufficient_data():
    """Single period returns 0.0."""
    periods = [_make_period(ebit=100, equity=800, debt=200, cash=0)]
    history = FinancialHistory(ticker="TEST", periods=periods)
    result = roic_trend(history)
    assert result.raw_value == 0.0


def test_flat_roic_zero_slope():
    """Flat ROIC across periods should produce near-zero slope."""
    periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0),
        _make_period(ebit=100, equity=800, debt=200, cash=0),
        _make_period(ebit=100, equity=800, debt=200, cash=0),
    ]
    history = FinancialHistory(ticker="TEST", periods=periods)
    result = roic_trend(history)
    assert result.raw_value == pytest.approx(0.0, abs=1e-10)


def test_two_periods_computes_slope():
    """Two periods is enough data for a slope."""
    periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0),
        _make_period(ebit=150, equity=800, debt=200, cash=0),
    ]
    history = FinancialHistory(ticker="TEST", periods=periods)
    result = roic_trend(history)
    assert result.raw_value > 0


def test_zero_invested_capital_skipped():
    """Period with IC <= 0 is skipped; remaining periods still produce a score."""
    periods = [
        # IC = 0 + 0 - 100 = -100 -> skip
        _make_period(ebit=100, equity=0, debt=0, cash=100),
        _make_period(ebit=120, equity=800, debt=200, cash=0),
        _make_period(ebit=150, equity=900, debt=200, cash=0),
    ]
    history = FinancialHistory(ticker="TEST", periods=periods)
    result = roic_trend(history)
    # With only 2 valid points, slope should still compute
    assert result.raw_value > 0


def test_all_periods_zero_ic():
    """If all periods have IC <= 0, raw_value should be 0.0."""
    periods = [
        _make_period(ebit=100, equity=0, debt=0, cash=100),
        _make_period(ebit=120, equity=0, debt=0, cash=200),
        _make_period(ebit=150, equity=0, debt=0, cash=300),
    ]
    history = FinancialHistory(ticker="TEST", periods=periods)
    result = roic_trend(history)
    assert result.raw_value == 0.0


def test_percentile_rank_is_placeholder():
    """Percentile rank should be 0.0 (placeholder for cross-sector ranking)."""
    periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0),
        _make_period(ebit=150, equity=800, debt=200, cash=0),
    ]
    history = FinancialHistory(ticker="TEST", periods=periods)
    result = roic_trend(history)
    assert result.percentile_rank == 0.0


def test_detail_contains_slope_info():
    """Detail string should contain useful info about the computation."""
    periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0),
        _make_period(ebit=150, equity=800, debt=200, cash=0),
    ]
    history = FinancialHistory(ticker="TEST", periods=periods)
    result = roic_trend(history)
    assert "slope" in result.detail.lower()
    assert "roic" in result.detail.lower()
