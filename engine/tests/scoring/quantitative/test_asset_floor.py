"""Tests for asset-based floor valuation — liquidation/breakup value."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import GICSSector
from margin_engine.scoring.quantitative.asset_floor import asset_floor_valuation


class TestAssetFloorValuation:
    def test_technology_low_multiple(self):
        """Tech gets 0.3x tangible book (IP-heavy)."""
        result = asset_floor_valuation(
            net_cash=Decimal("500"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.TECHNOLOGY,
            shares_outstanding=100,
        )
        # 500 + 1000*0.3 = 800, per share = 8.0
        assert result == pytest.approx(8.0)

    def test_utilities_high_multiple(self):
        """Utilities get 0.8x tangible book (regulated assets)."""
        result = asset_floor_valuation(
            net_cash=Decimal("200"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.UTILITIES,
            shares_outstanding=100,
        )
        # 200 + 1000*0.8 = 1000, per share = 10.0
        assert result == pytest.approx(10.0)

    def test_negative_net_cash(self):
        """Negative net cash (net debt) reduces floor."""
        result = asset_floor_valuation(
            net_cash=Decimal("-300"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.INDUSTRIALS,
            shares_outstanding=100,
        )
        # -300 + 1000*0.6 = 300, per share = 3.0
        assert result == pytest.approx(3.0)

    def test_floor_cannot_go_negative(self):
        """Floor bottoms at 0.0 even with massive debt."""
        result = asset_floor_valuation(
            net_cash=Decimal("-5000"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.TECHNOLOGY,
            shares_outstanding=100,
        )
        assert result == 0.0

    def test_zero_shares_returns_zero(self):
        result = asset_floor_valuation(
            net_cash=Decimal("500"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.TECHNOLOGY,
            shares_outstanding=0,
        )
        assert result == 0.0

    def test_default_regime_multiplier_unchanged(self):
        """Default regime_multiplier=1.0 produces same result as before."""
        result = asset_floor_valuation(
            net_cash=Decimal("500"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.TECHNOLOGY,
            shares_outstanding=100,
            regime_multiplier=1.0,
        )
        # 500 + 1000*0.3*1.0 = 800, per share = 8.0
        assert result == pytest.approx(8.0)

    def test_regime_multiplier_stress_lowers_floor(self):
        """regime_multiplier=0.7 reduces the liquidation multiple, lowering the floor."""
        result = asset_floor_valuation(
            net_cash=Decimal("500"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.TECHNOLOGY,
            shares_outstanding=100,
            regime_multiplier=0.7,
        )
        # 500 + 1000*0.3*0.7 = 500 + 210 = 710, per share = 7.1
        assert result == pytest.approx(7.1)

    def test_regime_multiplier_boom_raises_floor(self):
        """regime_multiplier=1.2 increases the liquidation multiple, raising the floor."""
        result = asset_floor_valuation(
            net_cash=Decimal("500"),
            tangible_book=Decimal("1000"),
            sector=GICSSector.TECHNOLOGY,
            shares_outstanding=100,
            regime_multiplier=1.2,
        )
        # 500 + 1000*0.3*1.2 = 500 + 360 = 860, per share = 8.6
        assert result == pytest.approx(8.6)
