"""Tests for SECTOR_GROWTH_RATES completeness."""

from margin_engine.config.industry_growth_rates import SECTOR_GROWTH_RATES, get_sector_growth_rate
from margin_engine.models.financial import GICSSector


class TestSectorGrowthRates:
    def test_all_gics_sectors_have_rates(self):
        for sector in GICSSector:
            assert sector.value in SECTOR_GROWTH_RATES, f"Missing: {sector.value}"

    def test_rates_are_reasonable(self):
        for sector, rate in SECTOR_GROWTH_RATES.items():
            assert -0.05 <= rate <= 0.30, f"{sector} rate {rate} out of range"

    def test_get_sector_growth_rate_known(self):
        rate = get_sector_growth_rate("Information Technology")
        assert rate > 0

    def test_get_sector_growth_rate_unknown(self):
        rate = get_sector_growth_rate("Nonexistent Sector")
        assert rate == 0.05
