"""Tests for reinvestment engine factor (ROIC * reinvestment rate)."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.reinvestment_engine import reinvestment_engine


def _make_period(
    *,
    ebit: Decimal = Decimal("200"),
    depreciation: Decimal | None = Decimal("50"),
    total_equity: Decimal = Decimal("500"),
    long_term_debt: Decimal | None = Decimal("300"),
    short_term_debt: Decimal = Decimal("200"),
    cash_and_equivalents: Decimal | None = Decimal("0"),
    capital_expenditures: Decimal = Decimal("-100"),
) -> FinancialPeriod:
    """Build a minimal FinancialPeriod for unit tests."""
    income = IncomeStatement(
        revenue=Decimal("1000"),
        ebit=ebit,
        depreciation=depreciation,
        net_income=Decimal("150"),
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
        operating_cash_flow=Decimal("250"),
        capital_expenditures=capital_expenditures,
    )
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


class TestReinvestmentEngine:
    def test_high_reinvestment_high_roic(self):
        """High reinvestment with high ROIC → positive score."""
        # NOPAT = 200 * (1 - 0.21) = 158
        # IC = 500 + (300 + 200) - 0 = 1000
        # ROIC = 158 / 1000 = 0.158
        # Growth CapEx = |CapEx| - Depreciation = 100 - 50 = 50
        # Reinvestment Rate = 50 / 158 = 0.3165
        # Score = 0.158 * 0.3165 ≈ 0.050
        period = _make_period()
        score = reinvestment_engine(period)

        assert score.name == "reinvestment_engine"
        assert score.raw_value == pytest.approx(0.050, abs=0.005)
        assert score.raw_value > 0.0

    def test_no_growth_capex(self):
        """CapEx < Depreciation → zero growth capex → 0.0."""
        # |CapEx| = 30, Depreciation = 50 → growth capex = 0
        period = _make_period(
            capital_expenditures=Decimal("-30"),
            depreciation=Decimal("50"),
        )
        score = reinvestment_engine(period)
        assert score.raw_value == 0.0

    def test_zero_invested_capital(self):
        """IC <= 0 → 0.0."""
        period = _make_period(
            total_equity=Decimal("0"),
            long_term_debt=Decimal("0"),
            short_term_debt=Decimal("0"),
            cash_and_equivalents=Decimal("0"),
        )
        score = reinvestment_engine(period)
        assert score.raw_value == 0.0

    def test_percentile_rank_always_zero(self):
        """Percentile rank is always 0.0 (placeholder)."""
        period = _make_period()
        score = reinvestment_engine(period)
        assert score.percentile_rank == 0.0
