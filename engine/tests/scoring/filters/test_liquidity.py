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


class TestLiquidityWithConfig:
    """Tests for config-driven liquidity thresholds."""

    def test_dollar_volume_tiered_by_market_cap(self):
        """Mega-cap needs $50M daily volume, small-cap needs $2M."""
        from margin_engine.config.filter_config import FilterConfig

        config = FilterConfig()

        # Mega-cap ($500B) with $30M volume: fails $50M mega threshold
        mega_profile = AssetProfile(
            ticker="MEGA",
            name="Mega Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("500_000_000_000"),
            avg_daily_volume=Decimal("30_000_000"),
            years_of_history=10,
        )
        result = liquidity_check(mega_profile, config=config.liquidity)
        assert not result.passed

        # Small-cap ($1B) with $3M volume: passes $2M small threshold
        small_profile = AssetProfile(
            ticker="SMLL",
            name="Small Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("1_000_000_000"),
            avg_daily_volume=Decimal("3_000_000"),
            years_of_history=10,
        )
        result = liquidity_check(small_profile, config=config.liquidity)
        assert result.passed

    def test_dollar_volume_large_cap_threshold(self):
        """Large-cap ($50B) needs $20M daily volume."""
        from margin_engine.config.filter_config import FilterConfig

        config = FilterConfig()

        # Large-cap with $15M volume: fails $20M large threshold
        profile = AssetProfile(
            ticker="LRG",
            name="Large Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("50_000_000_000"),
            avg_daily_volume=Decimal("15_000_000"),
            years_of_history=10,
        )
        result = liquidity_check(profile, config=config.liquidity)
        assert not result.passed

        # Large-cap with $25M volume: passes $20M large threshold
        profile2 = AssetProfile(
            ticker="LRG2",
            name="Large Corp 2",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("50_000_000_000"),
            avg_daily_volume=Decimal("25_000_000"),
            years_of_history=10,
        )
        result2 = liquidity_check(profile2, config=config.liquidity)
        assert result2.passed

    def test_dollar_volume_mid_cap_threshold(self):
        """Mid-cap ($5B) needs $5M daily volume."""
        from margin_engine.config.filter_config import FilterConfig

        config = FilterConfig()

        # Mid-cap with $3M volume: fails $5M mid threshold
        profile = AssetProfile(
            ticker="MID",
            name="Mid Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("5_000_000_000"),
            avg_daily_volume=Decimal("3_000_000"),
            years_of_history=10,
        )
        result = liquidity_check(profile, config=config.liquidity)
        assert not result.passed

        # Mid-cap with $6M volume: passes $5M mid threshold
        profile2 = AssetProfile(
            ticker="MID2",
            name="Mid Corp 2",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("5_000_000_000"),
            avg_daily_volume=Decimal("6_000_000"),
            years_of_history=10,
        )
        result2 = liquidity_check(profile2, config=config.liquidity)
        assert result2.passed

    def test_liquidity_backward_compatible_without_config(self):
        """Without config parameter, behavior matches original hardcoded thresholds."""
        # A profile that passes old $1M threshold should still pass without config
        profile = AssetProfile(
            ticker="TEST",
            name="Test Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("5_000_000_000"),
            avg_daily_volume=Decimal("2_000_000"),
            years_of_history=10,
        )
        result = liquidity_check(profile)  # no config parameter
        assert result.passed

    def test_config_sector_exclusions(self):
        """Sector exclusions should come from config."""
        from margin_engine.config.filter_config import LiquidityConfig

        # Config with no excluded sectors
        config = LiquidityConfig(excluded_sectors=[])
        profile = AssetProfile(
            ticker="FIN",
            name="Finance Corp",
            sector=GICSSector.FINANCIALS,
            market_cap=Decimal("50_000_000_000"),
            avg_daily_volume=Decimal("100_000_000"),
            years_of_history=10,
        )
        result = liquidity_check(profile, config=config)
        assert result.passed  # Financials NOT excluded when config says so

    def test_config_market_cap_minimum_overrides(self):
        """Market cap minimum thresholds should come from config."""
        from margin_engine.config.filter_config import LiquidityConfig, MarketCapMinimum

        # Config with higher default market cap minimum
        config = LiquidityConfig(
            market_cap_minimum=MarketCapMinimum(default=500_000_000)
        )
        profile = AssetProfile(
            ticker="SMAL",
            name="Smallish Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("400_000_000"),  # $400M — passes old $300M but fails new $500M
            avg_daily_volume=Decimal("100_000_000"),
            years_of_history=10,
        )
        result = liquidity_check(profile, config=config)
        assert not result.passed

    def test_config_min_years_of_history(self):
        """Years of history threshold should come from config."""
        from margin_engine.config.filter_config import LiquidityConfig

        # Config with lower years requirement
        config = LiquidityConfig(min_years_of_history=3)
        profile = AssetProfile(
            ticker="YUNG",
            name="Young Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("5_000_000_000"),
            avg_daily_volume=Decimal("100_000_000"),
            years_of_history=4,  # Fails default 5, passes config 3
        )
        result = liquidity_check(profile, config=config)
        assert result.passed
