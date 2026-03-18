"""Verify golden fixture data produces expected computed values."""

import pytest

from tests.fixtures.golden_apple_2024 import (
    APPLE_BALANCE_2024,
    APPLE_CASHFLOW_2024,
    APPLE_INCOME_2023,
    APPLE_INCOME_2024,
    APPLE_PERIOD_2024,
    APPLE_PROFILE,
    EXPECTED,
)


class TestGoldenAppleFixture:
    def test_gross_margin_2024(self):
        assert APPLE_INCOME_2024.gross_margin == pytest.approx(
            EXPECTED["gross_margin_2024"], abs=0.001
        )

    def test_gross_margin_2023(self):
        assert APPLE_INCOME_2023.gross_margin == pytest.approx(
            EXPECTED["gross_margin_2023"], abs=0.001
        )

    def test_revenue_growth(self):
        assert APPLE_PERIOD_2024.revenue_growth == pytest.approx(
            EXPECTED["revenue_growth"], abs=0.001
        )

    def test_fcf_2024(self):
        assert APPLE_CASHFLOW_2024.free_cash_flow == EXPECTED["fcf_2024"]

    def test_net_buybacks(self):
        assert APPLE_CASHFLOW_2024.net_buybacks == EXPECTED["net_buyback_2024"]

    def test_working_capital(self):
        assert APPLE_BALANCE_2024.working_capital == EXPECTED["working_capital_2024"]

    def test_current_ratio(self):
        assert APPLE_BALANCE_2024.current_ratio == pytest.approx(
            EXPECTED["current_ratio_2024"], abs=0.001
        )

    def test_roa_2024(self):
        roa = float(APPLE_INCOME_2024.net_income / APPLE_BALANCE_2024.total_assets)
        assert roa == pytest.approx(EXPECTED["roa_2024"], abs=0.001)

    def test_profile_sector(self):
        assert APPLE_PROFILE.sector.is_cyclical is False
