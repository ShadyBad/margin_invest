"""Tests for company-specific WACC computation (CAPM-based)."""

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
from margin_engine.scoring.quantitative.wacc_company import compute_company_wacc


def _make_period(
    *,
    revenue: Decimal = Decimal("1000000000"),
    ebit: Decimal = Decimal("200000000"),
    net_income: Decimal = Decimal("150000000"),
    interest_expense: Decimal | None = Decimal("30000000"),
    tax_provision: Decimal | None = Decimal("35700000"),
    total_assets: Decimal = Decimal("2000000000"),
    total_equity: Decimal = Decimal("800000000"),
    long_term_debt: Decimal | None = Decimal("400000000"),
    short_term_debt: Decimal = Decimal("100000000"),
) -> FinancialPeriod:
    """Build a minimal FinancialPeriod for WACC tests."""
    income = IncomeStatement(
        revenue=revenue,
        ebit=ebit,
        net_income=net_income,
        interest_expense=interest_expense,
        tax_provision=tax_provision,
        shares_outstanding=1_000_000,
    )
    balance = BalanceSheet(
        total_assets=total_assets,
        total_equity=total_equity,
        long_term_debt=long_term_debt,
        short_term_debt=short_term_debt,
        shares_outstanding=1_000_000,
    )
    cf = CashFlowStatement(
        operating_cash_flow=Decimal("180000000"),
        capital_expenditures=Decimal("-50000000"),
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
    market_cap: Decimal = Decimal("1000000000"),
) -> AssetProfile:
    """Build a minimal AssetProfile."""
    return AssetProfile(
        ticker="TEST",
        name="Test Corp",
        sector=GICSSector.TECHNOLOGY,
        market_cap=market_cap,
    )


class TestBasicWaccComputation:
    def test_basic_wacc_computation(self):
        """Verify WACC formula with known values.

        beta=1.2, market_cap=1B, total_debt=500M (400M LT + 100M ST)
        interest_expense=30M, tax_provision=35.7M

        Ke = 0.0425 + 1.2 * 0.055 = 0.1085
        Kd = 30M / 500M = 0.06

        effective_tax_rate: pretax = ebit - interest = 200M - 30M = 170M
        tax_rate = 35.7M / 170M = 0.21

        E=1B, D=500M, V=1.5B
        E/V = 2/3, D/V = 1/3

        WACC = (2/3 * 0.1085) + (1/3 * 0.06 * (1 - 0.21))
             = 0.07233 + 0.01580
             = 0.08813
        """
        period = _make_period()
        profile = _make_profile()
        wacc = compute_company_wacc(period, profile, beta=1.2)
        expected = (2 / 3 * 0.1085) + (1 / 3 * 0.06 * (1 - 0.21))
        assert wacc == pytest.approx(expected, abs=1e-4)


class TestHighLeverageHigherWacc:
    def test_high_leverage_higher_wacc(self):
        """More debt with a high cost of debt should produce a higher WACC.

        Low leverage:  D=200M, interest=10M -> Kd=0.05
            E/V = 1000/1200, D/V = 200/1200
            WACC = (0.833 * 0.0975) + (0.167 * 0.05 * 0.79) = 0.0878

        High leverage: D=2B, interest=300M -> Kd=min(0.15, 0.15) = 0.15
            E/V = 1000/3000, D/V = 2000/3000
            Kd*(1-t) = 0.15 * 0.79 = 0.1185 > Ke=0.0975
            WACC = (0.333 * 0.0975) + (0.667 * 0.15 * 0.79) = 0.1115

        Higher leverage with expensive debt pushes WACC above low-leverage case.
        """
        # Low leverage: 200M debt, 1B equity
        period_low = _make_period(
            long_term_debt=Decimal("150000000"),
            short_term_debt=Decimal("50000000"),
            interest_expense=Decimal("10000000"),
        )
        profile = _make_profile(market_cap=Decimal("1000000000"))

        # High leverage: 2B debt with expensive interest (capped at 15%)
        period_high = _make_period(
            long_term_debt=Decimal("1600000000"),
            short_term_debt=Decimal("400000000"),
            interest_expense=Decimal("300000000"),
        )

        wacc_low = compute_company_wacc(period_low, profile, beta=1.0)
        wacc_high = compute_company_wacc(period_high, profile, beta=1.0)

        # Higher leverage with expensive debt should give higher WACC
        assert wacc_high > wacc_low


class TestHighBetaHigherWacc:
    def test_high_beta_higher_wacc(self):
        """Higher beta raises cost of equity, which raises WACC.

        Ke(low) = 0.0425 + 0.8 * 0.055 = 0.0865
        Ke(high) = 0.0425 + 1.5 * 0.055 = 0.1250

        Same capital structure, so equity_weight is the same.
        Higher Ke -> higher WACC.
        """
        period = _make_period()
        profile = _make_profile()

        wacc_low_beta = compute_company_wacc(period, profile, beta=0.8)
        wacc_high_beta = compute_company_wacc(period, profile, beta=1.5)

        assert wacc_high_beta > wacc_low_beta


class TestFallbackToSectorWacc:
    def test_fallback_to_sector_wacc(self):
        """When beta is None, return sector_fallback."""
        period = _make_period()
        profile = _make_profile()

        wacc = compute_company_wacc(period, profile, beta=None, sector_fallback=0.10)
        assert wacc == 0.10


class TestZeroDebtEqualsCostOfEquity:
    def test_zero_debt_equals_cost_of_equity(self):
        """No debt means WACC = cost of equity = Rf + beta * MRP.

        beta=1.0: Ke = 0.0425 + 1.0 * 0.055 = 0.0975
        D=0, so equity_weight=1.0, debt_weight=0.0
        WACC = 1.0 * 0.0975 + 0 = 0.0975
        """
        period = _make_period(
            long_term_debt=Decimal("0"),
            short_term_debt=Decimal("0"),
            interest_expense=Decimal("0"),
        )
        profile = _make_profile()

        wacc = compute_company_wacc(period, profile, beta=1.0)
        expected_ke = 0.0425 + 1.0 * 0.055
        assert wacc == pytest.approx(expected_ke, abs=1e-6)


class TestNoInterestExpenseUsesDefaultDebtCost:
    def test_no_interest_expense_uses_default_debt_cost(self):
        """When interest_expense is None/0, use Rf + 200bps as cost of debt.

        beta=1.0, market_cap=1B, total_debt=500M
        Ke = 0.0425 + 1.0 * 0.055 = 0.0975
        Kd = 0.0425 + 0.02 = 0.0625 (default spread)
        E/V = 2/3, D/V = 1/3
        tax_rate = 0.21 (default, since no tax_provision and ebit check)
        WACC = (2/3 * 0.0975) + (1/3 * 0.0625 * (1 - 0.21))
             = 0.0650 + 0.01646
             = 0.08146
        """
        period = _make_period(
            interest_expense=None,
            tax_provision=None,
        )
        profile = _make_profile()

        wacc = compute_company_wacc(period, profile, beta=1.0)
        ke = 0.0425 + 1.0 * 0.055
        kd = 0.0425 + 0.02
        expected = (2 / 3 * ke) + (1 / 3 * kd * (1 - 0.21))
        assert wacc == pytest.approx(expected, abs=1e-4)


class TestWaccFloor:
    def test_wacc_floor(self):
        """Extremely low computed WACC should clamp to 2% floor.

        Using beta very close to 0 with zero debt:
        Ke = 0.0425 + 0.0 * 0.055 = 0.0425
        D=0 so WACC = 0.0425 > 0.02, so this won't trigger.

        Instead, use negative beta (though unrealistic) to get Ke below floor:
        beta = -0.5: Ke = 0.0425 + (-0.5) * 0.055 = 0.0425 - 0.0275 = 0.015
        D=0: WACC = 0.015 < 0.02 -> clamped to 0.02
        """
        period = _make_period(
            long_term_debt=Decimal("0"),
            short_term_debt=Decimal("0"),
            interest_expense=Decimal("0"),
        )
        profile = _make_profile()

        wacc = compute_company_wacc(period, profile, beta=-0.5)
        assert wacc == 0.02


class TestNoBetaNoFallbackReturnsDefault:
    def test_no_beta_no_fallback_returns_default(self):
        """beta=None and sector_fallback=None should return 0.09."""
        period = _make_period()
        profile = _make_profile()

        wacc = compute_company_wacc(period, profile, beta=None, sector_fallback=None)
        assert wacc == 0.09
