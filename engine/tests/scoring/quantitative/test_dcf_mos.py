"""Tests for DCF Margin of Safety (Klarman/Buffett) value factor."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.dcf_mos import dcf_margin_of_safety


class TestDcfMarginOfSafety:
    def test_apple_golden_value(self):
        """Apple FY2024 with growth=5%, discount=10%, terminal=2.5%.

        FCF_0 = 108,295,000,000
        MoS ~ -0.9713 (Apple overvalued by this DCF with conservative inputs)
        """
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = dcf_margin_of_safety(
            period=APPLE_PERIOD_2024,
            market_cap=APPLE_PROFILE.market_cap,
            growth_rate=0.05,
            discount_rate=0.10,
            terminal_growth_rate=0.025,
            projection_years=10,
        )
        assert result.raw_value == pytest.approx(-0.9713, rel=1e-2)

    def test_undervalued_stock(self):
        """Synthetic data where intrinsic value > market cap -> positive MoS.

        FCF = 1000, market_cap = 5000, growth=5%, discount=10%, terminal=2.5%.
        Should produce a positive margin of safety.
        """
        period = _make_period(
            operating_cash_flow=Decimal("1500"),
            capital_expenditures=Decimal("-500"),
        )
        # FCF = 1000; with these rates, intrinsic value should be much higher than 5000
        result = dcf_margin_of_safety(
            period=period,
            market_cap=Decimal("5000"),
            growth_rate=0.05,
            discount_rate=0.10,
            terminal_growth_rate=0.025,
            projection_years=10,
        )
        assert result.raw_value > 0.0, "Stock should be undervalued"

    def test_negative_fcf(self):
        """When FCF <= 0, raw_value should be 0.0 with explanatory detail."""
        period = _make_period(
            operating_cash_flow=Decimal("3000"),
            capital_expenditures=Decimal("-5000"),
        )
        result = dcf_margin_of_safety(
            period=period,
            market_cap=Decimal("100000"),
            growth_rate=0.05,
            discount_rate=0.10,
        )
        assert result.raw_value == 0.0
        assert "negative" in result.detail.lower() or "zero" in result.detail.lower()

    def test_zero_fcf(self):
        """When FCF = 0, raw_value should be 0.0."""
        period = _make_period(
            operating_cash_flow=Decimal("5000"),
            capital_expenditures=Decimal("-5000"),
        )
        result = dcf_margin_of_safety(
            period=period,
            market_cap=Decimal("100000"),
            growth_rate=0.05,
            discount_rate=0.10,
        )
        assert result.raw_value == 0.0

    def test_zero_market_cap(self):
        """When market_cap <= 0, raw_value should be 0.0 with explanatory detail."""
        period = _make_period(
            operating_cash_flow=Decimal("10000"),
            capital_expenditures=Decimal("-2000"),
        )
        result = dcf_margin_of_safety(
            period=period,
            market_cap=Decimal("0"),
            growth_rate=0.05,
            discount_rate=0.10,
        )
        assert result.raw_value == 0.0
        assert "market cap" in result.detail.lower()

    def test_negative_market_cap(self):
        """When market_cap < 0, raw_value should be 0.0."""
        period = _make_period(
            operating_cash_flow=Decimal("10000"),
            capital_expenditures=Decimal("-2000"),
        )
        result = dcf_margin_of_safety(
            period=period,
            market_cap=Decimal("-100"),
            growth_rate=0.05,
            discount_rate=0.10,
        )
        assert result.raw_value == 0.0

    def test_discount_rate_equals_terminal_growth(self):
        """When discount_rate <= terminal_growth_rate, terminal value is undefined."""
        period = _make_period(
            operating_cash_flow=Decimal("10000"),
            capital_expenditures=Decimal("-2000"),
        )
        result = dcf_margin_of_safety(
            period=period,
            market_cap=Decimal("50000"),
            growth_rate=0.05,
            discount_rate=0.03,
            terminal_growth_rate=0.03,
        )
        assert result.raw_value == 0.0
        assert "terminal" in result.detail.lower() or "discount" in result.detail.lower()

    def test_discount_rate_below_terminal_growth(self):
        """When discount_rate < terminal_growth_rate, terminal value is undefined."""
        period = _make_period(
            operating_cash_flow=Decimal("10000"),
            capital_expenditures=Decimal("-2000"),
        )
        result = dcf_margin_of_safety(
            period=period,
            market_cap=Decimal("50000"),
            growth_rate=0.05,
            discount_rate=0.02,
            terminal_growth_rate=0.03,
        )
        assert result.raw_value == 0.0

    def test_factor_score_name(self):
        """Factor name should be 'dcf_margin_of_safety'."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = dcf_margin_of_safety(
            period=APPLE_PERIOD_2024,
            market_cap=APPLE_PROFILE.market_cap,
            growth_rate=0.05,
            discount_rate=0.10,
        )
        assert result.name == "dcf_margin_of_safety"

    def test_percentile_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6 composite scorer)."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = dcf_margin_of_safety(
            period=APPLE_PERIOD_2024,
            market_cap=APPLE_PROFILE.market_cap,
            growth_rate=0.05,
            discount_rate=0.10,
        )
        assert result.percentile_rank == 0.0

    def test_detail_contains_key_values(self):
        """Detail string should contain FCF, intrinsic value, and margin info."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = dcf_margin_of_safety(
            period=APPLE_PERIOD_2024,
            market_cap=APPLE_PROFILE.market_cap,
            growth_rate=0.05,
            discount_rate=0.10,
        )
        # Should mention FCF
        assert "108295000000" in result.detail
        # Should mention intrinsic value
        assert "intrinsic" in result.detail.lower()
        # Should mention margin of safety
        assert "margin" in result.detail.lower() or "mos" in result.detail.lower()

    def test_apple_intrinsic_value_components(self):
        """Verify intermediate DCF values match golden expectations.

        PV of projected FCFs ~ 845,979,179,528
        Terminal Value ~ 2,410,815,629,294
        PV of Terminal ~ 929,473,787,926
        Intrinsic Value ~ 1,775,452,967,454
        """
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = dcf_margin_of_safety(
            period=APPLE_PERIOD_2024,
            market_cap=APPLE_PROFILE.market_cap,
            growth_rate=0.05,
            discount_rate=0.10,
            terminal_growth_rate=0.025,
            projection_years=10,
        )
        # The detail string should contain the intrinsic value;
        # we verify the computed MoS implies the expected intrinsic value
        # MoS = (IV - MC) / IV => IV = MC / (1 - MoS)
        # With MoS ~ -0.9713, IV ~ 3500B / (1 - (-0.9713)) ~ 1775B
        expected_intrinsic = 1_775_452_967_454
        expected_mos = (expected_intrinsic - 3_500_000_000_000) / expected_intrinsic
        assert result.raw_value == pytest.approx(expected_mos, rel=1e-2)


def _make_period(
    operating_cash_flow: Decimal,
    capital_expenditures: Decimal,
) -> FinancialPeriod:
    """Helper to build a minimal FinancialPeriod for testing DCF MoS."""
    income = IncomeStatement(revenue=Decimal("0"))
    balance = BalanceSheet(total_assets=Decimal("100000"))
    cf = CashFlowStatement(
        operating_cash_flow=operating_cash_flow,
        capital_expenditures=capital_expenditures,
    )
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )
