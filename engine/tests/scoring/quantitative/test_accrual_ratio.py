"""Tests for Sloan Accrual Ratio earnings quality factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.accrual_ratio import sloan_accrual_ratio


class TestSloanAccrualRatio:
    def test_apple_golden_value(self):
        """Apple FY2024: (93736 - 118254) / 364980 ≈ -0.0672."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = sloan_accrual_ratio(APPLE_PERIOD_2024)
        assert result.raw_value == pytest.approx(-0.0672, abs=0.001)

    def test_name(self):
        """Factor name should be 'accrual_ratio'."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = sloan_accrual_ratio(APPLE_PERIOD_2024)
        assert result.name == "accrual_ratio"

    def test_zero_assets(self):
        """When total_assets=0, raw_value should be 0.0 (avoid division by zero)."""
        period = _make_period(
            net_income=Decimal("5000"),
            operating_cash_flow=Decimal("3000"),
            total_assets=Decimal("0"),
        )
        result = sloan_accrual_ratio(period)
        assert result.raw_value == 0.0

    def test_percentile_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6 composite scorer)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = sloan_accrual_ratio(APPLE_PERIOD_2024)
        assert result.percentile_rank == 0.0

    def test_high_accruals(self):
        """Synthetic: net_income >> CFO -> positive ratio (poor earnings quality)."""
        period = _make_period(
            net_income=Decimal("10000"),
            operating_cash_flow=Decimal("2000"),
            total_assets=Decimal("50000"),
        )
        result = sloan_accrual_ratio(period)
        # (10000 - 2000) / 50000 = 0.16
        assert result.raw_value == pytest.approx(0.16, abs=0.001)
        assert result.raw_value > 0.0

    def test_negative_accruals(self):
        """Synthetic: CFO >> net_income -> negative ratio (high earnings quality)."""
        period = _make_period(
            net_income=Decimal("3000"),
            operating_cash_flow=Decimal("12000"),
            total_assets=Decimal("50000"),
        )
        result = sloan_accrual_ratio(period)
        # (3000 - 12000) / 50000 = -0.18
        assert result.raw_value == pytest.approx(-0.18, abs=0.001)
        assert result.raw_value < 0.0


def _make_period(
    net_income: Decimal,
    operating_cash_flow: Decimal,
    total_assets: Decimal,
) -> FinancialPeriod:
    """Helper to build a minimal FinancialPeriod for testing."""
    income = IncomeStatement(
        revenue=Decimal("0"),
        net_income=net_income,
    )
    balance = BalanceSheet(
        total_assets=total_assets,
    )
    cf = CashFlowStatement(
        operating_cash_flow=operating_cash_flow,
    )
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )
