"""Tests for ROIC-WACC spread quality factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.roic_wacc import compute_roic, roic_wacc_spread


def _minimal_period(
    *,
    ebit: Decimal = Decimal("100"),
    interest_expense: Decimal | None = None,
    tax_provision: Decimal | None = None,
    total_equity: Decimal = Decimal("500"),
    long_term_debt: Decimal | None = None,
    short_term_debt: Decimal = Decimal("200"),
    cash_and_equivalents: Decimal | None = None,
) -> FinancialPeriod:
    """Build a minimal FinancialPeriod for unit tests."""
    income = IncomeStatement(
        revenue=Decimal("1000"),
        ebit=ebit,
        interest_expense=interest_expense,
        tax_provision=tax_provision,
        net_income=Decimal("80"),
        shares_outstanding=100,
    )
    balance = BalanceSheet(
        total_assets=Decimal("1000"),
        current_assets=Decimal("400"),
        cash_and_equivalents=cash_and_equivalents,
        short_term_debt=short_term_debt,
        total_equity=total_equity,
        long_term_debt=long_term_debt,
        shares_outstanding=100,
    )
    cf = CashFlowStatement(
        operating_cash_flow=Decimal("120"),
        capital_expenditures=Decimal("-20"),
    )
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


class TestComputeRoic:
    def test_apple_roic_golden(self):
        """Apple FY2024 ROIC should be ~63.81% using average IC.

        With average IC: (144,697M + 143,434M) / 2 = 144,065.5M
        NOPAT ~91,926M, ROIC = 91926 / 144065.5 = ~0.6381
        """
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        roic = compute_roic(APPLE_PERIOD_2024)
        assert roic == pytest.approx(0.6381, abs=0.01)

    def test_compute_roic_uses_average_ic(self):
        """When prior_balance is provided, ROIC should use average IC.

        Current IC = 500 + 200 - 0 = 700
        Prior IC   = 400 + 100 - 0 = 500
        Avg IC     = (700 + 500) / 2 = 600
        NOPAT      = 100 * (1 - 0.21) = 79  (no tax_provision -> default 21%)
        ROIC       = 79 / 600 = 0.13167
        """
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            net_income=Decimal("80"),
            shares_outstanding=100,
        )
        current_balance = BalanceSheet(
            total_assets=Decimal("1000"),
            current_assets=Decimal("400"),
            cash_and_equivalents=Decimal("0"),
            short_term_debt=Decimal("200"),
            total_equity=Decimal("500"),
            shares_outstanding=100,
        )
        prior_balance = BalanceSheet(
            total_assets=Decimal("800"),
            current_assets=Decimal("300"),
            cash_and_equivalents=Decimal("0"),
            short_term_debt=Decimal("100"),
            total_equity=Decimal("400"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("120"),
            capital_expenditures=Decimal("-20"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=current_balance,
            prior_balance=prior_balance,
            current_cash_flow=cf,
        )
        roic = compute_roic(period)
        # With avg IC=600, ROIC = 79 / 600 = 0.13167
        assert roic == pytest.approx(79.0 / 600.0, abs=1e-4)

    def test_compute_roic_falls_back_when_no_prior(self):
        """Without prior_balance, behavior unchanged: uses current IC only.

        Current IC = 500 + 200 - 0 = 700
        NOPAT = 100 * (1 - 0.21) = 79
        ROIC = 79 / 700 = 0.11286
        """
        period = _minimal_period(
            ebit=Decimal("100"),
            total_equity=Decimal("500"),
            short_term_debt=Decimal("200"),
            cash_and_equivalents=Decimal("0"),
        )
        roic = compute_roic(period)
        assert roic == pytest.approx(79.0 / 700.0, abs=1e-4)


class TestRoicWaccSpread:
    def test_apple_roic_wacc_spread(self):
        """With WACC=11%, spread should be ROIC - 0.11 ~ 0.5281 (avg IC)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        score = roic_wacc_spread(APPLE_PERIOD_2024, wacc=0.11)
        assert score.raw_value == pytest.approx(0.5281, abs=0.01)

    def test_roic_wacc_spread_uses_average_ic(self):
        """roic_wacc_spread should use average IC when prior_balance available.

        Same period as test_compute_roic_uses_average_ic:
        Avg IC = 600, NOPAT = 79, ROIC = 79/600 = 0.13167
        Spread (wacc=0.10) = 0.13167 - 0.10 = 0.03167
        """
        income = IncomeStatement(
            revenue=Decimal("1000"),
            ebit=Decimal("100"),
            net_income=Decimal("80"),
            shares_outstanding=100,
        )
        current_balance = BalanceSheet(
            total_assets=Decimal("1000"),
            current_assets=Decimal("400"),
            cash_and_equivalents=Decimal("0"),
            short_term_debt=Decimal("200"),
            total_equity=Decimal("500"),
            shares_outstanding=100,
        )
        prior_balance = BalanceSheet(
            total_assets=Decimal("800"),
            current_assets=Decimal("300"),
            cash_and_equivalents=Decimal("0"),
            short_term_debt=Decimal("100"),
            total_equity=Decimal("400"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("120"),
            capital_expenditures=Decimal("-20"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=current_balance,
            prior_balance=prior_balance,
            current_cash_flow=cf,
        )
        score = roic_wacc_spread(period, wacc=0.10)
        expected_roic = 79.0 / 600.0
        assert score.raw_value == pytest.approx(expected_roic - 0.10, abs=1e-4)

    def test_roic_without_wacc(self):
        """When wacc=None, raw_value should equal ROIC."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        roic = compute_roic(APPLE_PERIOD_2024)
        score = roic_wacc_spread(APPLE_PERIOD_2024, wacc=None)
        assert score.raw_value == pytest.approx(roic, abs=1e-6)

    def test_name(self):
        """Factor score name must be 'roic_wacc_spread'."""
        period = _minimal_period()
        score = roic_wacc_spread(period)
        assert score.name == "roic_wacc_spread"

    def test_zero_invested_capital(self):
        """When equity=0, debt=0, cash=0 -> IC=0 -> raw_value=0.0."""
        period = _minimal_period(
            total_equity=Decimal("0"),
            long_term_debt=Decimal("0"),
            short_term_debt=Decimal("0"),
            cash_and_equivalents=Decimal("0"),
        )
        score = roic_wacc_spread(period)
        assert score.raw_value == 0.0

    def test_negative_invested_capital(self):
        """When cash > equity + debt -> IC < 0 -> raw_value=0.0."""
        period = _minimal_period(
            total_equity=Decimal("100"),
            long_term_debt=Decimal("0"),
            short_term_debt=Decimal("50"),
            cash_and_equivalents=Decimal("500"),
        )
        score = roic_wacc_spread(period)
        assert score.raw_value == 0.0

    def test_default_tax_rate(self):
        """When no tax_provision, effective_tax_rate defaults to 0.21."""
        period = _minimal_period(
            ebit=Decimal("100"),
            tax_provision=None,
            total_equity=Decimal("500"),
            long_term_debt=Decimal("200"),
            short_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("0"),
        )
        roic = compute_roic(period)
        # NOPAT = 100 * (1 - 0.21) = 79
        # IC = 500 + (200 + 100) - 0 = 800
        # ROIC = 79 / 800 = 0.09875
        assert roic == pytest.approx(0.09875, abs=1e-4)
