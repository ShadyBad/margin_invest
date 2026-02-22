"""Tests for FCF conversion ratio factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.fcf_conversion import fcf_conversion


def _make_period(net_income: float, ocf: float, capex: float) -> FinancialPeriod:
    return FinancialPeriod(
        period_end="2024-12-31",
        filing_date="2025-02-15",
        current_income=IncomeStatement(
            revenue=Decimal("1000"), net_income=Decimal(str(net_income)),
        ),
        current_balance=BalanceSheet(total_assets=Decimal("5000")),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal(str(ocf)),
            capital_expenditures=Decimal(str(capex)),
        ),
    )


def test_high_conversion():
    """FCF > NI implies strong cash quality."""
    period = _make_period(net_income=100, ocf=130, capex=-20)
    result = fcf_conversion(period)
    # FCF = 130 + (-20) = 110. Conversion = 110/100 = 1.10
    assert result.raw_value == pytest.approx(1.10, rel=1e-2)
    assert result.name == "fcf_conversion"


def test_low_conversion():
    """FCF < NI implies poor cash quality."""
    period = _make_period(net_income=100, ocf=80, capex=-30)
    result = fcf_conversion(period)
    # FCF = 80 + (-30) = 50. Conversion = 50/100 = 0.50
    assert result.raw_value == pytest.approx(0.50, rel=1e-2)


def test_zero_net_income():
    """Zero NI returns 0.0."""
    period = _make_period(net_income=0, ocf=50, capex=-10)
    result = fcf_conversion(period)
    assert result.raw_value == 0.0


def test_negative_net_income():
    """Negative NI returns 0.0 (ratio meaningless)."""
    period = _make_period(net_income=-50, ocf=20, capex=-10)
    result = fcf_conversion(period)
    assert result.raw_value == 0.0
