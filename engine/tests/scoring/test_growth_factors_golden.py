"""Golden-value tests for all 4 growth factor modules.

Each test uses fixed hand-calculated inputs and asserts exact known outputs.
These establish canonical correctness — any change to growth factor math
that alters these values must be intentional and reviewed.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.incremental_roic import incremental_roic
from margin_engine.scoring.quantitative.revenue_cagr import revenue_cagr
from margin_engine.scoring.quantitative.rule_of_40 import rule_of_40
from margin_engine.scoring.quantitative.runway_score import runway_score


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_period(
    *,
    period_end: str = "2024-09-28",
    revenue: Decimal = Decimal("1_000_000"),
    ebit: Decimal = Decimal("100_000"),
    total_assets: Decimal = Decimal("2_000_000"),
    total_equity: Decimal = Decimal("500_000"),
    long_term_debt: Decimal | None = Decimal("200_000"),
    short_term_debt: Decimal = Decimal("100_000"),
    cash_and_equivalents: Decimal | None = Decimal("50_000"),
    operating_cash_flow: Decimal = Decimal("80_000"),
    capital_expenditures: Decimal = Decimal("-10_000"),
) -> FinancialPeriod:
    """Build a FinancialPeriod with explicit golden-value fields."""
    return FinancialPeriod(
        period_end=period_end,
        filing_date="2024-11-01",
        current_income=IncomeStatement(
            revenue=revenue,
            ebit=ebit,
            net_income=Decimal("75_000"),
        ),
        current_balance=BalanceSheet(
            total_assets=total_assets,
            total_equity=total_equity,
            long_term_debt=long_term_debt,
            short_term_debt=short_term_debt,
            cash_and_equivalents=cash_and_equivalents,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=operating_cash_flow,
            capital_expenditures=capital_expenditures,
        ),
    )


# ---------------------------------------------------------------------------
# TestIncrementalRoicGolden
# ---------------------------------------------------------------------------


class TestIncrementalRoicGolden:
    """Hand-calculated golden values for incremental ROIC."""

    def test_golden_positive(self) -> None:
        """Two periods — hand-calculated NOPAT and IC verify incremental ROIC.

        Period 1 (earliest):
            EBIT = 1_000, no tax_provision → effective_tax_rate = 0.21
            NOPAT = 1_000 * (1 - 0.21) = 790.0
            IC = total_equity(500) + total_debt(200+100) - cash(50) = 750.0

        Period 2 (latest):
            EBIT = 2_000, no tax_provision → effective_tax_rate = 0.21
            NOPAT = 2_000 * (1 - 0.21) = 1_580.0
            IC = total_equity(800) + total_debt(300+100) - cash(100) = 1_100.0

        delta_NOPAT = 1_580 - 790 = 790.0
        delta_IC    = 1_100 - 750 = 350.0
        incremental_ROIC = 790 / 350 ≈ 2.2571
        """
        history = FinancialHistory(
            ticker="TEST",
            periods=[
                _make_period(
                    period_end="2023-09-28",
                    ebit=Decimal("1_000"),
                    total_equity=Decimal("500"),
                    long_term_debt=Decimal("200"),
                    short_term_debt=Decimal("100"),
                    cash_and_equivalents=Decimal("50"),
                ),
                _make_period(
                    period_end="2024-09-28",
                    ebit=Decimal("2_000"),
                    total_equity=Decimal("800"),
                    long_term_debt=Decimal("300"),
                    short_term_debt=Decimal("100"),
                    cash_and_equivalents=Decimal("100"),
                ),
            ],
        )

        result = incremental_roic(history)

        assert result.name == "incremental_roic"
        # delta_NOPAT = 790.0, delta_IC = 350.0 → 790/350
        assert result.raw_value == pytest.approx(790.0 / 350.0, rel=1e-6)

    def test_single_period_returns_zero(self) -> None:
        """Single period — cannot compute incremental ROIC, raw_value = 0.0."""
        history = FinancialHistory(
            ticker="TEST",
            periods=[_make_period()],
        )

        result = incremental_roic(history)

        assert result.raw_value == 0.0
        assert "Single period" in result.detail

    def test_zero_delta_ic(self) -> None:
        """Same IC both periods — delta_IC = 0 → raw_value = 0.0."""
        # Both periods identical IC = equity(500) + debt(200+100) - cash(50) = 750
        period = _make_period(
            total_equity=Decimal("500"),
            long_term_debt=Decimal("200"),
            short_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("50"),
        )
        history = FinancialHistory(
            ticker="TEST",
            periods=[
                _make_period(
                    period_end="2023-09-28",
                    ebit=Decimal("1_000"),
                    total_equity=Decimal("500"),
                    long_term_debt=Decimal("200"),
                    short_term_debt=Decimal("100"),
                    cash_and_equivalents=Decimal("50"),
                ),
                _make_period(
                    period_end="2024-09-28",
                    ebit=Decimal("1_500"),
                    total_equity=Decimal("500"),
                    long_term_debt=Decimal("200"),
                    short_term_debt=Decimal("100"),
                    cash_and_equivalents=Decimal("50"),
                ),
            ],
        )

        result = incremental_roic(history)

        assert result.raw_value == 0.0
        assert "delta_IC=0" in result.detail


# ---------------------------------------------------------------------------
# TestRevenueCagrGolden
# ---------------------------------------------------------------------------


class TestRevenueCagrGolden:
    """Hand-calculated golden values for revenue CAGR."""

    def test_golden_3_year(self) -> None:
        """4 periods: 1M → ~1.26M → ~1.587M → 2M (doubling over 3 years).

        CAGR = (2_000_000 / 1_000_000) ^ (1/3) - 1 = 2^(1/3) - 1 ≈ 0.25992
        """
        history = FinancialHistory(
            ticker="TEST",
            periods=[
                _make_period(period_end="2021-12-31", revenue=Decimal("1_000_000")),
                _make_period(period_end="2022-12-31", revenue=Decimal("1_259_921")),
                _make_period(period_end="2023-12-31", revenue=Decimal("1_587_401")),
                _make_period(period_end="2024-12-31", revenue=Decimal("2_000_000")),
            ],
        )

        result = revenue_cagr(history, years=3)

        assert result.name == "revenue_cagr"
        expected = 2.0 ** (1.0 / 3.0) - 1.0  # ≈ 0.25992
        assert result.raw_value == pytest.approx(expected, rel=1e-4)

    def test_golden_2_year(self) -> None:
        """2 periods: 500K → 750K (n=1 year).

        CAGR = (750_000 / 500_000) ^ (1/1) - 1 = 1.5 - 1 = 0.5
        """
        history = FinancialHistory(
            ticker="TEST",
            periods=[
                _make_period(period_end="2023-12-31", revenue=Decimal("500_000")),
                _make_period(period_end="2024-12-31", revenue=Decimal("750_000")),
            ],
        )

        result = revenue_cagr(history, years=3)

        assert result.raw_value == pytest.approx(0.50, rel=1e-6)

    def test_single_period_returns_zero(self) -> None:
        """Single period — insufficient data, raw_value = 0.0."""
        history = FinancialHistory(
            ticker="TEST",
            periods=[_make_period()],
        )

        result = revenue_cagr(history)

        assert result.raw_value == 0.0
        assert "need at least 2 periods" in result.detail

    def test_zero_start_revenue(self) -> None:
        """Zero starting revenue — sentinel 0.0 returned."""
        history = FinancialHistory(
            ticker="TEST",
            periods=[
                _make_period(period_end="2023-12-31", revenue=Decimal("0")),
                _make_period(period_end="2024-12-31", revenue=Decimal("1_000_000")),
            ],
        )

        result = revenue_cagr(history)

        assert result.raw_value == 0.0
        assert "zero/negative starting revenue" in result.detail


# ---------------------------------------------------------------------------
# TestRuleOf40Golden
# ---------------------------------------------------------------------------


class TestRuleOf40Golden:
    """Hand-calculated golden values for Rule of 40."""

    def test_golden_above_40(self) -> None:
        """growth=0.30, fcf_margin=0.15 → 30 + 15 = 45.0."""
        result = rule_of_40(revenue_growth_rate=0.30, fcf_margin=0.15)

        assert result.name == "rule_of_40"
        assert result.raw_value == pytest.approx(45.0, rel=1e-6)

    def test_golden_below_40(self) -> None:
        """growth=0.10, fcf_margin=0.20 → 10 + 20 = 30.0."""
        result = rule_of_40(revenue_growth_rate=0.10, fcf_margin=0.20)

        assert result.raw_value == pytest.approx(30.0, rel=1e-6)

    def test_negative_growth(self) -> None:
        """growth=-0.05, fcf_margin=0.25 → -5 + 25 = 20.0."""
        result = rule_of_40(revenue_growth_rate=-0.05, fcf_margin=0.25)

        assert result.raw_value == pytest.approx(20.0, rel=1e-6)

    def test_negative_margin(self) -> None:
        """growth=0.50, fcf_margin=-0.30 → 50 + (-30) = 20.0."""
        result = rule_of_40(revenue_growth_rate=0.50, fcf_margin=-0.30)

        assert result.raw_value == pytest.approx(20.0, rel=1e-6)


# ---------------------------------------------------------------------------
# TestRunwayScoreGolden
# ---------------------------------------------------------------------------


class TestRunwayScoreGolden:
    """Hand-calculated golden values for runway score (revenue penetration)."""

    def test_golden_penetration(self) -> None:
        """company_revenue=10M, sub_industry_revenue=100M → penetration = 0.10."""
        result = runway_score(
            company_revenue=Decimal("10_000_000"),
            sub_industry_revenue=Decimal("100_000_000"),
        )

        assert result.name == "runway_score"
        assert result.raw_value == pytest.approx(0.10, rel=1e-6)

    def test_none_sub_industry(self) -> None:
        """sub_industry_revenue=None → neutral sentinel 0.5."""
        result = runway_score(
            company_revenue=Decimal("10_000_000"),
            sub_industry_revenue=None,
        )

        assert result.raw_value == pytest.approx(0.5, rel=1e-6)
        assert "neutral" in result.detail

    def test_zero_sub_industry(self) -> None:
        """sub_industry_revenue=0 → fully saturated sentinel 1.0."""
        result = runway_score(
            company_revenue=Decimal("10_000_000"),
            sub_industry_revenue=Decimal("0"),
        )

        assert result.raw_value == pytest.approx(1.0, rel=1e-6)
        assert "saturated" in result.detail
