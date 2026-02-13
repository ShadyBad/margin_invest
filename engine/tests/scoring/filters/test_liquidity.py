"""Tests for Liquidity filter."""

from decimal import Decimal

from margin_engine.models.financial import AssetProfile, GICSSector
from margin_engine.scoring.filters.liquidity import liquidity_check


class TestLiquidity:
    def test_apple_passes(self):
        """Apple should pass all liquidity criteria."""
        from tests.fixtures.golden_apple_2024 import APPLE_PROFILE
        result = liquidity_check(APPLE_PROFILE)
        assert result.passed is True
        assert result.name == "liquidity"

    def test_small_cap_fails(self):
        """Company with market cap < $300M should FAIL."""
        profile = AssetProfile(
            ticker="TINY",
            name="Tiny Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("200000000"),  # $200M
            avg_daily_volume=Decimal("5000000"),
            years_of_history=10,
        )
        result = liquidity_check(profile)
        assert result.passed is False

    def test_low_volume_fails(self):
        """Company with avg daily volume < $1M should FAIL."""
        profile = AssetProfile(
            ticker="LOW",
            name="Low Volume Inc",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("1000000000"),  # $1B
            avg_daily_volume=Decimal("500000"),  # $500K
            years_of_history=10,
        )
        result = liquidity_check(profile)
        assert result.passed is False

    def test_insufficient_history_fails(self):
        """Company with < 5 years history should FAIL."""
        profile = AssetProfile(
            ticker="NEW",
            name="New IPO Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("5000000000"),  # $5B
            avg_daily_volume=Decimal("10000000"),
            years_of_history=3,
        )
        result = liquidity_check(profile)
        assert result.passed is False

    def test_financials_excluded(self):
        """Financial sector should be excluded."""
        profile = AssetProfile(
            ticker="JPM",
            name="JPMorgan Chase",
            sector=GICSSector.FINANCIALS,
            market_cap=Decimal("500000000000"),
            avg_daily_volume=Decimal("50000000"),
            years_of_history=30,
        )
        result = liquidity_check(profile)
        assert result.passed is False
        assert "excluded" in result.detail.lower() or "sector" in result.detail.lower()

    def test_real_estate_excluded(self):
        """Real estate sector should be excluded."""
        profile = AssetProfile(
            ticker="AMT",
            name="American Tower",
            sector=GICSSector.REAL_ESTATE,
            market_cap=Decimal("100000000000"),
            avg_daily_volume=Decimal("5000000"),
            years_of_history=20,
        )
        result = liquidity_check(profile)
        assert result.passed is False

    def test_energy_higher_market_cap_threshold(self):
        """Energy sector needs >= $500M market cap."""
        profile = AssetProfile(
            ticker="OIL",
            name="Oil Co",
            sector=GICSSector.ENERGY,
            market_cap=Decimal("400000000"),  # $400M — passes default but fails energy
            avg_daily_volume=Decimal("5000000"),
            years_of_history=10,
        )
        result = liquidity_check(profile)
        assert result.passed is False

    def test_utilities_higher_market_cap_threshold(self):
        """Utilities sector needs >= $1B market cap."""
        profile = AssetProfile(
            ticker="UTIL",
            name="Utility Co",
            sector=GICSSector.UTILITIES,
            market_cap=Decimal("800000000"),  # $800M — passes default but fails utilities
            avg_daily_volume=Decimal("5000000"),
            years_of_history=10,
        )
        result = liquidity_check(profile)
        assert result.passed is False

    def test_passing_energy_company(self):
        """Energy company with >= $500M should pass."""
        profile = AssetProfile(
            ticker="XOM",
            name="Exxon Mobil",
            sector=GICSSector.ENERGY,
            market_cap=Decimal("500000000000"),  # $500B
            avg_daily_volume=Decimal("20000000"),
            years_of_history=25,
        )
        result = liquidity_check(profile)
        assert result.passed is True
