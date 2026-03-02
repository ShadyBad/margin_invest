"""Tests for ROIC stability factor (median ROIC * (1 - CV))."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.roic_stability import roic_stability


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


class TestRoicStability:
    def test_stable_high_roic(self):
        """5 identical periods → CV=0, score = median ROIC."""
        periods = [
            _make_period(
                ebit=Decimal("100"),
                total_equity=Decimal("500"),
                long_term_debt=Decimal("200"),
                short_term_debt=Decimal("100"),
                cash_and_equivalents=Decimal("0"),
                period_end=f"202{i}-09-28",
            )
            for i in range(5)
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = roic_stability(history)

        # NOPAT = 100 * (1 - 0.21) = 79
        # IC = 500 + (200 + 100) - 0 = 800
        # ROIC = 79 / 800 = 0.09875
        # CV = 0 (all same), score = 0.09875 * (1 - 0) = 0.09875
        assert score.name == "roic_stability"
        assert score.raw_value == pytest.approx(0.09875, abs=1e-4)
        assert score.percentile_rank == 0.0

    def test_volatile_roic_lower_than_stable(self):
        """Varying EBIT → positive CV → lower score than stable."""
        # Volatile: EBIT varies widely
        ebits = [Decimal("50"), Decimal("150"), Decimal("30"), Decimal("200"), Decimal("70")]
        volatile_periods = [
            _make_period(ebit=e, period_end=f"202{i}-09-28") for i, e in enumerate(ebits)
        ]
        volatile_history = FinancialHistory(ticker="VOL", periods=volatile_periods)
        volatile_score = roic_stability(volatile_history)

        # Stable: constant EBIT
        stable_periods = [
            _make_period(ebit=Decimal("100"), period_end=f"202{i}-09-28") for i in range(5)
        ]
        stable_history = FinancialHistory(ticker="STB", periods=stable_periods)
        stable_score = roic_stability(stable_history)

        assert volatile_score.raw_value < stable_score.raw_value

    def test_single_period_cv_zero(self):
        """Single period → CV=0, score = ROIC."""
        period = _make_period(ebit=Decimal("100"))
        history = FinancialHistory(ticker="ONE", periods=[period])
        score = roic_stability(history)

        # ROIC = 79 / 800 = 0.09875, CV = 0
        assert score.raw_value == pytest.approx(0.09875, abs=1e-4)

    def test_zero_invested_capital_all_periods(self):
        """All periods with zero IC → raw_value = 0.0."""
        periods = [
            _make_period(
                total_equity=Decimal("0"),
                long_term_debt=Decimal("0"),
                short_term_debt=Decimal("0"),
                cash_and_equivalents=Decimal("0"),
                period_end=f"202{i}-09-28",
            )
            for i in range(3)
        ]
        history = FinancialHistory(ticker="ZERO", periods=periods)
        score = roic_stability(history)
        assert score.raw_value == 0.0

    def test_uses_average_ic_when_prior_balance_available(self):
        """With prior_balance on each period, ROIC should use average IC."""
        # Period with prior_balance: current IC = 800, prior IC = 600, avg IC = 700
        # NOPAT = 100 * (1 - 0.21) = 79
        # ROIC = 79 / 700 = 0.11286
        period = _make_period(ebit=Decimal("100"))
        period_with_prior = period.model_copy(
            update={
                "prior_balance": BalanceSheet(
                    total_assets=Decimal("800"),
                    total_equity=Decimal("300"),
                    long_term_debt=Decimal("200"),
                    short_term_debt=Decimal("100"),
                    cash_and_equivalents=Decimal("0"),
                    shares_outstanding=100,
                )
            }
        )
        history = FinancialHistory(ticker="AVG", periods=[period_with_prior] * 3)
        score = roic_stability(history)
        # All periods identical → CV=0, score = avg-IC ROIC
        assert score.raw_value == pytest.approx(0.11286, abs=0.001)

    def test_percentile_rank_always_zero(self):
        """Percentile rank is always 0.0 (placeholder)."""
        period = _make_period()
        history = FinancialHistory(ticker="PR", periods=[period])
        score = roic_stability(history)
        assert score.percentile_rank == 0.0
