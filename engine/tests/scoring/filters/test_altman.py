"""Tests for Altman Z'' Score financial distress filter."""

from decimal import Decimal

import pytest
from margin_engine.config.filter_config import AltmanConfig
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import FilterVerdict
from margin_engine.scoring.filters.altman import altman_z_score


class TestAltmanZScore:
    def test_apple_passes(self):
        """Apple FY2024 should PASS with Z'' ≈ 1.86."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024
        result = altman_z_score(APPLE_PERIOD_2024, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True
        assert result.value is not None
        assert result.value == pytest.approx(1.86, abs=0.05)

    def test_distressed_company_fails(self):
        """Synthetic distressed company should FAIL (Z'' < 1.1)."""
        income = IncomeStatement(
            revenue=Decimal("500"),
            ebit=Decimal("-50"),  # Negative EBIT
            net_income=Decimal("-80"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("1000"),
            current_assets=Decimal("200"),
            current_liabilities=Decimal("400"),  # Negative working capital
            total_liabilities=Decimal("900"),
            total_equity=Decimal("100"),
            retained_earnings=Decimal("-200"),  # Accumulated losses
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("-30"),
            capital_expenditures=Decimal("-10"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        result = altman_z_score(period)
        assert result.passed is False
        assert result.verdict == FilterVerdict.FAIL
        assert result.value < 1.1

    def test_utilities_exempt(self):
        """Utilities sector should be exempt (auto-PASS)."""
        income = IncomeStatement(
            revenue=Decimal("500"),
            ebit=Decimal("-50"),
            net_income=Decimal("-80"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("1000"),
            current_assets=Decimal("200"),
            current_liabilities=Decimal("400"),
            total_liabilities=Decimal("900"),
            total_equity=Decimal("100"),
            retained_earnings=Decimal("-200"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("-30"),
            capital_expenditures=Decimal("-10"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        result = altman_z_score(period, sector=GICSSector.UTILITIES)
        assert result.passed is True
        assert "utilities" in result.detail.lower() or "not applicable" in result.detail.lower()

    def test_filter_name_and_threshold(self):
        """Filter result should have correct name and threshold."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024
        result = altman_z_score(APPLE_PERIOD_2024)
        assert result.name == "altman_z_score"
        assert result.threshold == 1.1

    def test_healthy_company_passes(self):
        """Synthetic healthy company should PASS."""
        income = IncomeStatement(
            revenue=Decimal("2000"),
            ebit=Decimal("500"),
            net_income=Decimal("400"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("3000"),
            current_assets=Decimal("1500"),
            current_liabilities=Decimal("600"),
            total_liabilities=Decimal("1200"),
            total_equity=Decimal("1800"),
            retained_earnings=Decimal("800"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("450"),
            capital_expenditures=Decimal("-100"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        result = altman_z_score(period)
        assert result.passed is True
        assert result.value > 1.1


class TestAltmanWithConfig:
    """Tests for config-driven Altman thresholds."""

    def test_config_parameter_accepted(self):
        """Config parameter should be accepted without error."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        config = AltmanConfig()
        result = altman_z_score(APPLE_PERIOD_2024, sector=GICSSector.TECHNOLOGY, config=config)
        assert result.passed is True

    def test_config_threshold_overrides_hardcoded(self):
        """Config threshold should override the hardcoded 1.1.

        Apple Z'' is approx 1.86. With a stricter threshold of 2.0,
        Apple should FAIL because 1.86 < 2.0.
        """
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        strict_config = AltmanConfig(threshold=2.0)
        result = altman_z_score(
            APPLE_PERIOD_2024,
            sector=GICSSector.TECHNOLOGY,
            config=strict_config,
        )
        assert result.passed is False
        assert result.threshold == 2.0

    def test_without_config_backward_compatible(self):
        """Without config, behavior matches original hardcoded thresholds."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024

        result = altman_z_score(APPLE_PERIOD_2024)
        assert result.passed is True
        assert result.threshold == 1.1

    def test_config_exempt_sectors(self):
        """Config exempt_sectors should override the hardcoded Utilities exemption."""
        income = IncomeStatement(
            revenue=Decimal("500"),
            ebit=Decimal("-50"),
            net_income=Decimal("-80"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("1000"),
            current_assets=Decimal("200"),
            current_liabilities=Decimal("400"),
            total_liabilities=Decimal("900"),
            total_equity=Decimal("100"),
            retained_earnings=Decimal("-200"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("-30"),
            capital_expenditures=Decimal("-10"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        # With empty exempt_sectors, Utilities should NOT be exempt
        config = AltmanConfig(exempt_sectors=[])
        result = altman_z_score(period, sector=GICSSector.UTILITIES, config=config)
        # This distressed company should now FAIL because Utilities is not exempt
        assert result.passed is False

    def test_config_equity_tl_cap(self):
        """Config equity_tl_cap should override the hardcoded cap of 10.0."""
        income = IncomeStatement(
            revenue=Decimal("2000"),
            ebit=Decimal("500"),
            net_income=Decimal("400"),
            shares_outstanding=100,
        )
        balance = BalanceSheet(
            total_assets=Decimal("3000"),
            current_assets=Decimal("1500"),
            current_liabilities=Decimal("600"),
            total_liabilities=Decimal("0"),  # Zero TL triggers cap
            total_equity=Decimal("3000"),
            retained_earnings=Decimal("800"),
            shares_outstanding=100,
        )
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("450"),
            capital_expenditures=Decimal("-100"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=income,
            current_balance=balance,
            current_cash_flow=cf,
        )
        # With default cap of 10.0
        result_default = altman_z_score(period)
        # With lower cap of 5.0, score should be lower
        config = AltmanConfig(equity_tl_cap=5.0)
        result_lower = altman_z_score(period, config=config)
        assert result_lower.value < result_default.value
