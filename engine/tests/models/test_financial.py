"""Tests for AssetProfile shares_outstanding field."""

from decimal import Decimal

from margin_engine.models.financial import AssetProfile, GICSSector


def test_asset_profile_shares_outstanding():
    profile = AssetProfile(
        ticker="AAPL",
        name="Apple Inc.",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("3000000000000"),
        shares_outstanding=15000000000,
    )
    assert profile.shares_outstanding == 15000000000


def test_asset_profile_shares_outstanding_default():
    profile = AssetProfile(
        ticker="AAPL",
        name="Apple Inc.",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("3000000000000"),
    )
    assert profile.shares_outstanding is None
