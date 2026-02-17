"""Tests for sector WACC lookup."""

import pytest
from margin_engine.models.financial import GICSSector
from margin_engine.scoring.quantitative.wacc_sector import get_sector_wacc


class TestGetSectorWacc:
    def test_technology_wacc(self):
        assert get_sector_wacc(GICSSector.TECHNOLOGY) == pytest.approx(0.10)

    def test_utilities_wacc(self):
        assert get_sector_wacc(GICSSector.UTILITIES) == pytest.approx(0.065)

    def test_all_sectors_have_wacc(self):
        for sector in GICSSector:
            wacc = get_sector_wacc(sector)
            assert 0.05 <= wacc <= 0.15, f"{sector}: {wacc}"

    def test_return_type_is_float(self):
        assert isinstance(get_sector_wacc(GICSSector.ENERGY), float)
