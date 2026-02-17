"""Tests for incremental ROIC factor (return on new capital deployed)."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.incremental_roic import incremental_roic


def _make_period(
    *,
    ebit: Decimal = Decimal("100"),
    total_equity: Decimal = Decimal("500"),
    long_term_debt: Decimal | None = Decimal("200"),
    short_term_debt: Decimal = Decimal("100"),
    cash_and_equivalents: Decimal | None = Decimal("0"),
    period_end: str = "2024-09-28",
) -> FinancialPeriod:
    """Build a minimal FinancialPeriod for unit tests."""
    income = IncomeStatement(
        revenue=Decimal("1000"),
        ebit=ebit,
        net_income=Decimal("80"),
        shares_outstanding=100,
    )
    balance = BalanceSheet(
        total_assets=Decimal("1000"),
        total_equity=total_equity,
        long_term_debt=long_term_debt,
        short_term_debt=short_term_debt,
        cash_and_equivalents=cash_and_equivalents,
        shares_outstanding=100,
    )
    cf = CashFlowStatement(
        operating_cash_flow=Decimal("120"),
        capital_expenditures=Decimal("-20"),
    )
    return FinancialPeriod(
        period_end=period_end,
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


class TestIncrementalRoic:
    def test_growing_nopat_on_growing_ic(self):
        """Growing NOPAT on growing IC → positive incremental ROIC."""
        # Earliest: EBIT=100, IC=800 → NOPAT=79
        earliest = _make_period(
            ebit=Decimal("100"),
            total_equity=Decimal("500"),
            long_term_debt=Decimal("200"),
            short_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("0"),
            period_end="2020-09-28",
        )
        # Latest: EBIT=200, IC=1200 → NOPAT=158
        latest = _make_period(
            ebit=Decimal("200"),
            total_equity=Decimal("800"),
            long_term_debt=Decimal("300"),
            short_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("0"),
            period_end="2024-09-28",
        )
        history = FinancialHistory(ticker="GROW", periods=[earliest, latest])
        score = incremental_roic(history)

        # delta_NOPAT = 158 - 79 = 79
        # delta_IC = 1200 - 800 = 400
        # incremental ROIC = 79 / 400 = 0.1975
        assert score.name == "incremental_roic"
        assert score.raw_value == pytest.approx(0.1975, abs=1e-3)

    def test_zero_delta_ic(self):
        """No change in IC → 0.0."""
        p1 = _make_period(ebit=Decimal("100"), period_end="2020-09-28")
        p2 = _make_period(ebit=Decimal("200"), period_end="2024-09-28")
        history = FinancialHistory(ticker="FLAT", periods=[p1, p2])
        score = incremental_roic(history)
        assert score.raw_value == 0.0

    def test_single_period(self):
        """Single period → 0.0."""
        period = _make_period()
        history = FinancialHistory(ticker="ONE", periods=[period])
        score = incremental_roic(history)
        assert score.raw_value == 0.0

    def test_percentile_rank_always_zero(self):
        """Percentile rank is always 0.0 (placeholder)."""
        period = _make_period()
        history = FinancialHistory(ticker="PR", periods=[period])
        score = incremental_roic(history)
        assert score.percentile_rank == 0.0
