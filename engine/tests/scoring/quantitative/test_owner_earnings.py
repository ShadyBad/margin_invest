"""Tests for owner earnings yield factor (Buffett-adjusted FCF / EV)."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.owner_earnings import owner_earnings_yield


def _make_period(
    *,
    depreciation: Decimal | None = Decimal("50"),
    operating_cash_flow: Decimal = Decimal("200"),
    long_term_debt: Decimal | None = Decimal("300"),
    short_term_debt: Decimal = Decimal("100"),
    cash_and_equivalents: Decimal | None = Decimal("50"),
) -> FinancialPeriod:
    """Build a minimal FinancialPeriod for unit tests."""
    income = IncomeStatement(
        revenue=Decimal("1000"),
        ebit=Decimal("200"),
        depreciation=depreciation,
        net_income=Decimal("150"),
        shares_outstanding=100,
    )
    balance = BalanceSheet(
        total_assets=Decimal("1500"),
        total_equity=Decimal("600"),
        long_term_debt=long_term_debt,
        short_term_debt=short_term_debt,
        cash_and_equivalents=cash_and_equivalents,
        shares_outstanding=100,
    )
    cf = CashFlowStatement(
        operating_cash_flow=operating_cash_flow,
        capital_expenditures=Decimal("-80"),
    )
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


def _make_profile(
    *,
    market_cap: Decimal = Decimal("5000"),
) -> AssetProfile:
    return AssetProfile(
        ticker="TEST",
        name="Test Corp",
        sector=GICSSector.TECHNOLOGY,
        market_cap=market_cap,
    )


class TestOwnerEarningsYield:
    def test_basic_computation(self):
        """Basic computation with known values."""
        period = _make_period()
        profile = _make_profile(market_cap=Decimal("5000"))
        score = owner_earnings_yield(period, profile)

        # Maintenance CapEx = Depreciation * 1.1 = 50 * 1.1 = 55
        # Owner Earnings = CFO - Maintenance CapEx = 200 - 55 = 145
        # EV = Market Cap + Total Debt - Cash = 5000 + 400 - 50 = 5350
        # Yield = 145 / 5350 ≈ 0.02710
        assert score.name == "owner_earnings_yield"
        assert score.raw_value == pytest.approx(0.02710, abs=1e-3)

    def test_zero_ev(self):
        """EV <= 0 → 0.0."""
        period = _make_period(
            long_term_debt=Decimal("0"),
            short_term_debt=Decimal("0"),
            cash_and_equivalents=Decimal("6000"),
        )
        profile = _make_profile(market_cap=Decimal("5000"))
        score = owner_earnings_yield(period, profile)
        assert score.raw_value == 0.0

    def test_negative_owner_earnings(self):
        """Negative owner earnings → 0.0."""
        # CFO = 10, Maintenance CapEx = 50 * 1.1 = 55 → OE = 10 - 55 = -45
        period = _make_period(
            operating_cash_flow=Decimal("10"),
            depreciation=Decimal("50"),
        )
        profile = _make_profile()
        score = owner_earnings_yield(period, profile)
        assert score.raw_value == 0.0

    def test_percentile_rank_always_zero(self):
        """Percentile rank is always 0.0 (placeholder)."""
        period = _make_period()
        profile = _make_profile()
        score = owner_earnings_yield(period, profile)
        assert score.percentile_rank == 0.0
