"""Tests for Anti-Mediocrity Gate."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet, CashFlowStatement, FinancialHistory,
    FinancialPeriod, GICSSector, IncomeStatement,
)
from margin_engine.models.scoring import FilterResult
from margin_engine.scoring.filters.mediocrity_gate import mediocrity_gate


def _make_period(year: int, ebit: Decimal = Decimal("200"),
                 revenue: Decimal = Decimal("1000"),
                 cfo: Decimal = Decimal("250"),
                 gross_margin_pct: float = 0.40) -> FinancialPeriod:
    cogs = revenue * Decimal(str(1 - gross_margin_pct))
    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=IncomeStatement(
            revenue=revenue, cost_of_revenue=cogs,
            gross_profit=revenue - cogs, ebit=ebit,
            net_income=ebit * Decimal("0.79"),
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("2000"), total_equity=Decimal("500"),
            long_term_debt=Decimal("200"), cash_and_equivalents=Decimal("100"),
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=cfo, capital_expenditures=Decimal("-50"),
        ),
    )


class TestMediocrityGate:
    def test_quality_business_passes(self):
        """Business with ROIC > 8%, GM > 20%, consistent FCF passes."""
        history = FinancialHistory(
            ticker="GOOD",
            periods=[_make_period(y) for y in range(2019, 2024)],
        )
        result = mediocrity_gate(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True

    def test_low_roic_fails(self):
        """5yr median ROIC < 8% = mediocre."""
        history = FinancialHistory(
            ticker="WEAK",
            periods=[_make_period(y, ebit=Decimal("20")) for y in range(2019, 2024)],
        )
        result = mediocrity_gate(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is False
        assert "roic" in result.detail.lower()

    def test_low_gross_margin_fails(self):
        """Gross margin < 20% = commodity business."""
        history = FinancialHistory(
            ticker="COMM",
            periods=[_make_period(y, gross_margin_pct=0.12) for y in range(2019, 2024)],
        )
        result = mediocrity_gate(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is False

    def test_utilities_lower_gm_threshold(self):
        """Utilities have lower GM threshold (10%)."""
        history = FinancialHistory(
            ticker="UTIL",
            periods=[_make_period(y, gross_margin_pct=0.15) for y in range(2019, 2024)],
        )
        result = mediocrity_gate(history, sector=GICSSector.UTILITIES)
        assert result.passed is True  # 15% > 10% threshold for utilities

    def test_energy_lower_gm_threshold(self):
        """Energy has 15% GM threshold. 15% should pass."""
        history = FinancialHistory(
            ticker="ENRG",
            periods=[_make_period(y, gross_margin_pct=0.16) for y in range(2019, 2024)],
        )
        result = mediocrity_gate(history, sector=GICSSector.ENERGY)
        assert result.passed is True  # 16% > 15% threshold for energy
