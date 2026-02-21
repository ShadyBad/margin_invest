"""Tests for expanded reinvestment rate including R&D growth."""

import pytest
from decimal import Decimal

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.v3_intermediates import compute_compounding_power


def _make_period(
    ebit: float,
    equity: float,
    debt: float,
    cash: float,
    capex: float = -50,
    depreciation: float = 30,
    rd: float | None = None,
    prior_rd: float | None = None,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end="2024-12-31",
        filing_date="2025-02-15",
        current_income=IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal(str(ebit)),
            depreciation=Decimal(str(depreciation)),
            rd_expense=Decimal(str(rd)) if rd is not None else None,
        ),
        prior_income=IncomeStatement(
            revenue=Decimal("900"),
            rd_expense=Decimal(str(prior_rd)) if prior_rd is not None else None,
        ) if prior_rd is not None else None,
        current_balance=BalanceSheet(
            total_assets=Decimal("5000"),
            total_equity=Decimal(str(equity)),
            long_term_debt=Decimal(str(debt)),
            cash_and_equivalents=Decimal(str(cash)),
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("200"),
            capital_expenditures=Decimal(str(capex)),
        ),
    )


def test_rd_intensive_gets_higher_reinvestment():
    """A company with R&D growth should have higher compounding power
    than an identical company without R&D."""
    base_periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0),
        _make_period(ebit=120, equity=900, debt=200, cash=50),
        _make_period(ebit=150, equity=1000, debt=200, cash=100),
    ]
    rd_periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0, rd=50, prior_rd=40),
        _make_period(ebit=120, equity=900, debt=200, cash=50, rd=60, prior_rd=50),
        _make_period(ebit=150, equity=1000, debt=200, cash=100, rd=75, prior_rd=60),
    ]
    base_history = FinancialHistory(ticker="BASE", periods=base_periods)
    rd_history = FinancialHistory(ticker="RD", periods=rd_periods)

    base_power = compute_compounding_power(base_history)
    rd_power = compute_compounding_power(rd_history)

    # R&D-intensive company should get credit for its R&D reinvestment
    assert rd_power > base_power


def test_rd_growth_zero_when_no_rd_data():
    """When R&D fields are None, behavior matches the base case exactly."""
    periods_no_rd = [
        _make_period(ebit=100, equity=800, debt=200, cash=0),
        _make_period(ebit=120, equity=900, debt=200, cash=50),
        _make_period(ebit=150, equity=1000, debt=200, cash=100),
    ]
    periods_none_rd = [
        _make_period(ebit=100, equity=800, debt=200, cash=0, rd=None, prior_rd=None),
        _make_period(ebit=120, equity=900, debt=200, cash=50, rd=None, prior_rd=None),
        _make_period(ebit=150, equity=1000, debt=200, cash=100, rd=None, prior_rd=None),
    ]
    h1 = FinancialHistory(ticker="A", periods=periods_no_rd)
    h2 = FinancialHistory(ticker="B", periods=periods_none_rd)

    assert compute_compounding_power(h1) == pytest.approx(
        compute_compounding_power(h2)
    )


def test_declining_rd_adds_nothing():
    """If R&D is declining (below inflation-adjusted prior), rd_growth should be 0."""
    # current_rd=40 < prior_rd*1.03 = 50*1.03 = 51.5 => rd_growth = 0
    declining_periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0, rd=40, prior_rd=50),
        _make_period(ebit=120, equity=900, debt=200, cash=50, rd=40, prior_rd=50),
        _make_period(ebit=150, equity=1000, debt=200, cash=100, rd=40, prior_rd=50),
    ]
    base_periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0),
        _make_period(ebit=120, equity=900, debt=200, cash=50),
        _make_period(ebit=150, equity=1000, debt=200, cash=100),
    ]
    h_declining = FinancialHistory(ticker="DEC", periods=declining_periods)
    h_base = FinancialHistory(ticker="BASE", periods=base_periods)

    # Declining R&D should not add anything over base
    assert compute_compounding_power(h_declining) == pytest.approx(
        compute_compounding_power(h_base)
    )


def test_rd_growth_with_no_prior_income():
    """If prior_income is None on the latest period, rd_growth = 0."""
    # Only current rd, no prior — should match base
    periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0),
        _make_period(ebit=120, equity=900, debt=200, cash=50),
        _make_period(ebit=150, equity=1000, debt=200, cash=100, rd=75),
    ]
    base_periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0),
        _make_period(ebit=120, equity=900, debt=200, cash=50),
        _make_period(ebit=150, equity=1000, debt=200, cash=100),
    ]
    h_rd_no_prior = FinancialHistory(ticker="NP", periods=periods)
    h_base = FinancialHistory(ticker="BASE", periods=base_periods)

    assert compute_compounding_power(h_rd_no_prior) == pytest.approx(
        compute_compounding_power(h_base)
    )


def test_inflation_adjustment_applied():
    """R&D growth uses 3% inflation adjustment on prior R&D.

    current_rd=103, prior_rd=100 => inflation_adj_prior = 103.0
    rd_growth = max(103 - 103, 0) = 0 (exactly at inflation, no real growth)
    """
    at_inflation_periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0, rd=103, prior_rd=100),
        _make_period(ebit=120, equity=900, debt=200, cash=50, rd=103, prior_rd=100),
        _make_period(ebit=150, equity=1000, debt=200, cash=100, rd=103, prior_rd=100),
    ]
    base_periods = [
        _make_period(ebit=100, equity=800, debt=200, cash=0),
        _make_period(ebit=120, equity=900, debt=200, cash=50),
        _make_period(ebit=150, equity=1000, debt=200, cash=100),
    ]
    h_at_inflation = FinancialHistory(ticker="INF", periods=at_inflation_periods)
    h_base = FinancialHistory(ticker="BASE", periods=base_periods)

    # At exactly inflation, no real R&D growth — should match base
    assert compute_compounding_power(h_at_inflation) == pytest.approx(
        compute_compounding_power(h_base)
    )
