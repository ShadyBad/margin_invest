"""Tests for Gross Profitability (Novy-Marx) quality factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.gross_profitability import gross_profitability


class TestGrossProfitability:
    def test_apple_golden_value(self):
        """Apple FY2024: GP = (391035 - 210352) / 364980 ≈ 0.4951."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = gross_profitability(APPLE_PERIOD_2024)
        assert result.raw_value == pytest.approx(0.4951, abs=0.001)

    def test_name(self):
        """Factor name should be 'gross_profitability'."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = gross_profitability(APPLE_PERIOD_2024)
        assert result.name == "gross_profitability"

    def test_zero_assets(self):
        """When total_assets=0, raw_value should be 0.0 (avoid division by zero)."""
        period = _make_period(
            revenue=Decimal("1000"),
            cost_of_revenue=Decimal("400"),
            total_assets=Decimal("0"),
        )
        result = gross_profitability(period)
        assert result.raw_value == 0.0

    def test_percentile_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6 composite scorer)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = gross_profitability(APPLE_PERIOD_2024)
        assert result.percentile_rank == 0.0

    def test_high_profitability(self):
        """Synthetic company with GP ratio > 0.5."""
        period = _make_period(
            revenue=Decimal("10000"),
            cost_of_revenue=Decimal("3000"),
            total_assets=Decimal("10000"),
        )
        result = gross_profitability(period)
        # (10000 - 3000) / 10000 = 0.7
        assert result.raw_value == pytest.approx(0.7, abs=0.001)
        assert result.raw_value > 0.5


def _make_period(
    revenue: Decimal,
    cost_of_revenue: Decimal,
    total_assets: Decimal,
) -> FinancialPeriod:
    """Helper to build a minimal FinancialPeriod for testing."""
    income = IncomeStatement(
        revenue=revenue,
        cost_of_revenue=cost_of_revenue,
    )
    balance = BalanceSheet(
        total_assets=total_assets,
    )
    cf = CashFlowStatement()
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )
