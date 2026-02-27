"""Tests for Tier 1 detection — deterministic impossibility checks.

Covers:
- Negative revenue flagged, zero revenue NOT flagged
- Zero shares flagged
- Accounting identity violation flagged, small rounding NOT flagged
- Identical current/prior periods flagged as stale, no prior → no stale flag
- Clean data → empty list
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from margin_engine.healing.detection import detect_tier1
from margin_engine.healing.models import DetectionResult, DetectionSeverity
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)


def _make_period(
    revenue: Decimal = Decimal("1000"),
    shares_outstanding: int = 100,
    total_assets: Decimal = Decimal("5000"),
    total_liabilities: Decimal = Decimal("2000"),
    total_equity: Decimal = Decimal("3000"),
    prior_income: IncomeStatement | None = None,
    prior_balance: BalanceSheet | None = None,
    prior_cash_flow: CashFlowStatement | None = None,
    income_kwargs: dict | None = None,
    balance_kwargs: dict | None = None,
    cash_flow_kwargs: dict | None = None,
) -> FinancialPeriod:
    """Helper to build a FinancialPeriod with sensible defaults."""
    income_kw = {
        "revenue": revenue,
        "shares_outstanding": shares_outstanding,
        "net_income": Decimal("200"),
        "ebit": Decimal("300"),
    }
    if income_kwargs:
        income_kw.update(income_kwargs)

    balance_kw = {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
    }
    if balance_kwargs:
        balance_kw.update(balance_kwargs)

    cash_flow_kw = {
        "operating_cash_flow": Decimal("400"),
        "capital_expenditures": Decimal("-100"),
    }
    if cash_flow_kwargs:
        cash_flow_kw.update(cash_flow_kwargs)

    return FinancialPeriod(
        period_end="2024-12-31",
        filing_date="2025-02-15",
        current_income=IncomeStatement(**income_kw),
        prior_income=prior_income,
        current_balance=BalanceSheet(**balance_kw),
        prior_balance=prior_balance,
        current_cash_flow=CashFlowStatement(**cash_flow_kw),
        prior_cash_flow=prior_cash_flow,
    )


class TestNegativeRevenue:
    """Revenue < 0 should be flagged as IMPOSSIBLE."""

    def test_negative_revenue_flagged(self) -> None:
        period = _make_period(revenue=Decimal("-100"))
        results = detect_tier1(period)

        revenue_flags = [r for r in results if r.field_path == "income_statement.revenue"]
        assert len(revenue_flags) == 1
        flag = revenue_flags[0]
        assert flag.severity == DetectionSeverity.IMPOSSIBLE
        assert flag.original_value == -100.0
        assert "negative" in flag.detail.lower() or "< 0" in flag.detail.lower()

    def test_zero_revenue_not_flagged(self) -> None:
        period = _make_period(revenue=Decimal("0"))
        results = detect_tier1(period)

        revenue_flags = [r for r in results if r.field_path == "income_statement.revenue"]
        assert len(revenue_flags) == 0

    def test_positive_revenue_not_flagged(self) -> None:
        period = _make_period(revenue=Decimal("5000"))
        results = detect_tier1(period)

        revenue_flags = [r for r in results if r.field_path == "income_statement.revenue"]
        assert len(revenue_flags) == 0


class TestZeroShares:
    """shares_outstanding <= 0 should be flagged as IMPOSSIBLE."""

    def test_zero_shares_flagged(self) -> None:
        period = _make_period(shares_outstanding=0)
        results = detect_tier1(period)

        shares_flags = [
            r for r in results if r.field_path == "income_statement.shares_outstanding"
        ]
        assert len(shares_flags) == 1
        flag = shares_flags[0]
        assert flag.severity == DetectionSeverity.IMPOSSIBLE
        assert flag.original_value == 0.0

    def test_negative_shares_flagged(self) -> None:
        period = _make_period(shares_outstanding=-50)
        results = detect_tier1(period)

        shares_flags = [
            r for r in results if r.field_path == "income_statement.shares_outstanding"
        ]
        assert len(shares_flags) == 1
        flag = shares_flags[0]
        assert flag.severity == DetectionSeverity.IMPOSSIBLE
        assert flag.original_value == -50.0

    def test_positive_shares_not_flagged(self) -> None:
        period = _make_period(shares_outstanding=1000)
        results = detect_tier1(period)

        shares_flags = [
            r for r in results if r.field_path == "income_statement.shares_outstanding"
        ]
        assert len(shares_flags) == 0


class TestAccountingIdentity:
    """total_liabilities + total_equity > total_assets * 1.01 should be flagged."""

    def test_identity_violation_flagged(self) -> None:
        # liabilities + equity = 8000, assets = 5000 → clearly violated
        period = _make_period(
            total_assets=Decimal("5000"),
            total_liabilities=Decimal("4000"),
            total_equity=Decimal("4000"),
        )
        results = detect_tier1(period)

        identity_flags = [r for r in results if r.field_path == "balance_sheet.identity"]
        assert len(identity_flags) == 1
        flag = identity_flags[0]
        assert flag.severity == DetectionSeverity.IMPOSSIBLE
        assert "identity" in flag.detail.lower() or "accounting" in flag.detail.lower()

    def test_small_rounding_not_flagged(self) -> None:
        # liabilities + equity = 5040, assets = 5000 → 5040 <= 5050 (1% tolerance)
        period = _make_period(
            total_assets=Decimal("5000"),
            total_liabilities=Decimal("2020"),
            total_equity=Decimal("3020"),
        )
        results = detect_tier1(period)

        identity_flags = [r for r in results if r.field_path == "balance_sheet.identity"]
        assert len(identity_flags) == 0

    def test_exact_match_not_flagged(self) -> None:
        # liabilities + equity = assets exactly
        period = _make_period(
            total_assets=Decimal("10000"),
            total_liabilities=Decimal("6000"),
            total_equity=Decimal("4000"),
        )
        results = detect_tier1(period)

        identity_flags = [r for r in results if r.field_path == "balance_sheet.identity"]
        assert len(identity_flags) == 0

    def test_at_tolerance_boundary_not_flagged(self) -> None:
        # liabilities + equity = 5050, assets = 5000 → exactly at 1% tolerance boundary
        period = _make_period(
            total_assets=Decimal("5000"),
            total_liabilities=Decimal("2525"),
            total_equity=Decimal("2525"),
        )
        results = detect_tier1(period)

        identity_flags = [r for r in results if r.field_path == "balance_sheet.identity"]
        assert len(identity_flags) == 0

    def test_just_over_tolerance_flagged(self) -> None:
        # liabilities + equity = 5051, assets = 5000 → 5051 > 5050
        period = _make_period(
            total_assets=Decimal("5000"),
            total_liabilities=Decimal("2526"),
            total_equity=Decimal("2525"),
        )
        results = detect_tier1(period)

        identity_flags = [r for r in results if r.field_path == "balance_sheet.identity"]
        assert len(identity_flags) == 1


class TestStaleDuplicate:
    """Identical current/prior flagged as stale; no prior → no flag."""

    def test_identical_periods_flagged_as_stale(self) -> None:
        income = IncomeStatement(
            revenue=Decimal("1000"),
            shares_outstanding=100,
            net_income=Decimal("200"),
            ebit=Decimal("300"),
        )
        balance = BalanceSheet(
            total_assets=Decimal("5000"),
            total_liabilities=Decimal("2000"),
            total_equity=Decimal("3000"),
        )
        cash_flow = CashFlowStatement(
            operating_cash_flow=Decimal("400"),
            capital_expenditures=Decimal("-100"),
        )

        period = FinancialPeriod(
            period_end="2024-12-31",
            filing_date="2025-02-15",
            current_income=income,
            prior_income=income,
            current_balance=balance,
            prior_balance=balance,
            current_cash_flow=cash_flow,
            prior_cash_flow=cash_flow,
        )

        results = detect_tier1(period)

        stale_flags = [r for r in results if r.field_path == "period"]
        assert len(stale_flags) == 1
        flag = stale_flags[0]
        assert flag.severity == DetectionSeverity.IMPOSSIBLE
        assert "stale" in flag.detail.lower()

    def test_no_prior_no_stale_flag(self) -> None:
        period = _make_period()  # no prior data by default
        results = detect_tier1(period)

        stale_flags = [r for r in results if r.field_path == "period"]
        assert len(stale_flags) == 0

    def test_different_prior_no_stale_flag(self) -> None:
        prior_income = IncomeStatement(
            revenue=Decimal("900"),  # different from current 1000
            shares_outstanding=100,
            net_income=Decimal("180"),
            ebit=Decimal("270"),
        )
        prior_balance = BalanceSheet(
            total_assets=Decimal("4800"),
            total_liabilities=Decimal("1900"),
            total_equity=Decimal("2900"),
        )
        prior_cash_flow = CashFlowStatement(
            operating_cash_flow=Decimal("350"),
            capital_expenditures=Decimal("-90"),
        )

        period = _make_period(
            prior_income=prior_income,
            prior_balance=prior_balance,
            prior_cash_flow=prior_cash_flow,
        )
        results = detect_tier1(period)

        stale_flags = [r for r in results if r.field_path == "period"]
        assert len(stale_flags) == 0


class TestCleanData:
    """Clean data should produce an empty list."""

    def test_clean_data_no_flags(self) -> None:
        period = _make_period()
        results = detect_tier1(period)
        assert results == []

    def test_clean_data_with_prior_no_flags(self) -> None:
        prior_income = IncomeStatement(
            revenue=Decimal("900"),
            shares_outstanding=95,
            net_income=Decimal("180"),
            ebit=Decimal("270"),
        )
        prior_balance = BalanceSheet(
            total_assets=Decimal("4800"),
            total_liabilities=Decimal("1900"),
            total_equity=Decimal("2900"),
        )
        prior_cash_flow = CashFlowStatement(
            operating_cash_flow=Decimal("350"),
            capital_expenditures=Decimal("-90"),
        )

        period = _make_period(
            prior_income=prior_income,
            prior_balance=prior_balance,
            prior_cash_flow=prior_cash_flow,
        )
        results = detect_tier1(period)
        assert results == []


class TestMultipleViolations:
    """Multiple violations in the same period should all be reported."""

    def test_multiple_violations(self) -> None:
        # Negative revenue AND zero shares AND identity violation
        period = _make_period(
            revenue=Decimal("-500"),
            shares_outstanding=0,
            total_assets=Decimal("5000"),
            total_liabilities=Decimal("4000"),
            total_equity=Decimal("4000"),
        )
        results = detect_tier1(period)

        field_paths = {r.field_path for r in results}
        assert "income_statement.revenue" in field_paths
        assert "income_statement.shares_outstanding" in field_paths
        assert "balance_sheet.identity" in field_paths
        assert len(results) == 3
