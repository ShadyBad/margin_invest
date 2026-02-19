"""Tests for Liquidity filter (v1 and v2)."""

from decimal import Decimal

from margin_engine.config.filter_config import (
    DollarVolumeTiers,
    LiquidityConfig,
    PositionSizingConfig,
)
from margin_engine.models.financial import AssetProfile, GICSSector, PriceBar
from margin_engine.scoring.filters.liquidity import liquidity_check, liquidity_check_v2


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


# ---------------------------------------------------------------------------
# Helpers for v2 tests
# ---------------------------------------------------------------------------

def _make_bars(
    n: int,
    close: Decimal = Decimal("100.00"),
    volume: int = 1_000_000,
) -> list[PriceBar]:
    """Generate n synthetic price bars with uniform close/volume."""
    bars = []
    for i in range(n):
        day = f"2025-01-{(i % 28) + 1:02d}"
        bars.append(
            PriceBar(
                date=day,
                open=close,
                high=close + Decimal("1"),
                low=close - Decimal("1"),
                close=close,
                volume=volume,
            )
        )
    return bars


def _make_divergent_bars(
    n_recent: int = 20,
    n_older: int = 70,
    recent_volume: int = 100_000,
    older_volume: int = 2_000_000,
    close: Decimal = Decimal("50.00"),
) -> list[PriceBar]:
    """Generate bars where recent volume is much lower than older volume.

    Returns n_recent + n_older bars. The most recent bars (by date) have
    ``recent_volume`` and the older bars have ``older_volume``.
    """
    bars = []
    # Older bars first (earlier dates)
    for i in range(n_older):
        day = f"2024-{((i // 28) % 12) + 1:02d}-{(i % 28) + 1:02d}"
        bars.append(
            PriceBar(
                date=day,
                open=close,
                high=close + Decimal("1"),
                low=close - Decimal("1"),
                close=close,
                volume=older_volume,
            )
        )
    # Recent bars (later dates)
    for i in range(n_recent):
        day = f"2025-02-{(i % 28) + 1:02d}"
        bars.append(
            PriceBar(
                date=day,
                open=close,
                high=close + Decimal("1"),
                low=close - Decimal("1"),
                close=close,
                volume=recent_volume,
            )
        )
    return bars


def _healthy_profile() -> AssetProfile:
    """Return a profile that passes all basic liquidity criteria."""
    return AssetProfile(
        ticker="HLTH",
        name="Healthy Corp",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("5_000_000_000"),  # $5B mid-cap
        avg_daily_volume=Decimal("10_000_000"),
        years_of_history=10,
    )


# ---------------------------------------------------------------------------
# v2 tests
# ---------------------------------------------------------------------------


class TestLiquidityCheckV2:
    """Tests for liquidity_check_v2 with price-bar-derived checks."""

    def test_liquidity_all_criteria_pass(self):
        """Asset meeting all criteria should PASS with full metrics."""
        profile = _healthy_profile()
        # 90 bars with $100 close * 1M volume = $100M daily dollar volume
        # Mid-cap threshold is $5M, so $100M passes easily.
        # days_to_fill: $500K / (0.05 * $100M) = 0.1 days -> PASS
        bars = _make_bars(n=90, close=Decimal("100.00"), volume=1_000_000)
        result = liquidity_check_v2(profile, price_bars=bars)

        assert result.passed is True
        assert result.name == "liquidity"
        assert result.computed_metrics is not None

        m = result.computed_metrics
        assert "market_cap" in m
        assert "dollar_volume" in m
        assert "days_to_fill" in m
        assert "median_dollar_volume_90d" in m
        assert "years_of_history" in m
        assert m["days_to_fill"] <= 5.0

    def test_liquidity_position_sizing_fail(self):
        """Asset where position can't be filled in 5 days should FAIL."""
        profile = _healthy_profile()
        # Very low volume: $50 close * 100 shares = $5K daily dollar volume
        # days_to_fill: $500K / (0.05 * $5K) = 2000 days -> FAIL
        # Also dollar_volume check will fail ($5K < $5M mid threshold)
        bars = _make_bars(n=90, close=Decimal("50.00"), volume=100)
        result = liquidity_check_v2(profile, price_bars=bars)

        assert result.passed is False
        assert result.computed_metrics is not None
        assert result.computed_metrics["days_to_fill"] > 5.0
        assert "days_to_fill" in result.detail

    def test_liquidity_position_sizing_fail_borderline(self):
        """Position sizing check fails even when dollar volume passes.

        Engineer the volume so dollar_volume passes the $5M mid-cap threshold
        but days_to_fill exceeds 5 days.
        """
        profile = _healthy_profile()
        # Need volume >= $5M to pass mid-cap dollar volume threshold
        # days_to_fill = $500K / (0.05 * vol_90d)
        # For dtf > 5: vol_90d < $500K / (0.05 * 5) = $2M
        # So use volume that gives ~$1.5M dollar volume (passes $5M? No...)
        #
        # Actually for dtf > 5 we need vol_90d < $2M. But $2M < $5M mid threshold,
        # so both would fail. Let's use custom config with lower dollar volume tier.
        config = LiquidityConfig(
            dollar_volume=DollarVolumeTiers(mid=1_000_000),  # Lower threshold to $1M
            position_sizing=PositionSizingConfig(
                target_position=500_000,
                max_participation_rate=0.05,
                max_days_to_fill=5,
            ),
        )
        # $50 * 30_000 = $1.5M daily dollar volume
        # Passes $1M mid threshold
        # days_to_fill = $500K / (0.05 * $1.5M) = 6.67 days -> FAIL
        bars = _make_bars(n=90, close=Decimal("50.00"), volume=30_000)
        result = liquidity_check_v2(profile, price_bars=bars, config=config)

        assert result.passed is False
        assert result.computed_metrics is not None
        assert result.computed_metrics["days_to_fill"] > 5.0
        assert "FAIL" in result.detail

    def test_liquidity_divergence_fail(self):
        """20d vol much lower than 90d vol -> liquidity evaporating -> FAIL."""
        profile = _healthy_profile()
        # Recent 20 bars: $50 * 100K = $5M daily
        # Older 70 bars: $50 * 2M = $100M daily
        # 90d median will be dominated by the older bars: ~$100M
        # 20d median: $5M
        # divergence ratio: $100M / $5M = 20.0 >> 3.0 -> FAIL
        bars = _make_divergent_bars(
            n_recent=20,
            n_older=70,
            recent_volume=100_000,
            older_volume=2_000_000,
            close=Decimal("50.00"),
        )
        result = liquidity_check_v2(profile, price_bars=bars)

        assert result.passed is False
        assert result.computed_metrics is not None
        assert result.computed_metrics["divergence_ratio"] > 3.0
        assert "divergence" in result.detail.lower()

    def test_liquidity_v2_without_price_bars_falls_back(self):
        """v2 without price_bars should fall back to profile volume only."""
        profile = _healthy_profile()
        result = liquidity_check_v2(profile, price_bars=None)

        # Should pass basic criteria (market cap, volume from profile, history)
        assert result.passed is True
        assert result.computed_metrics is not None
        # No position sizing or divergence metrics without bars
        assert "days_to_fill" not in result.computed_metrics
        assert "divergence_ratio" not in result.computed_metrics
        # But dollar_volume should come from profile
        assert result.computed_metrics["dollar_volume"] == 10_000_000.0

    def test_liquidity_backward_compat(self):
        """Old liquidity_check() still works without price_bars."""
        profile = _healthy_profile()
        result = liquidity_check(profile)

        assert result.passed is True
        assert result.name == "liquidity"
        # v1 doesn't produce computed_metrics
        assert result.computed_metrics is None

    def test_v2_sector_exclusion(self):
        """v2 also checks sector exclusion."""
        profile = AssetProfile(
            ticker="JPM",
            name="JPMorgan Chase",
            sector=GICSSector.FINANCIALS,
            market_cap=Decimal("500_000_000_000"),
            avg_daily_volume=Decimal("50_000_000"),
            years_of_history=30,
        )
        result = liquidity_check_v2(profile, price_bars=None)
        assert result.passed is False
        assert "excluded" in result.detail.lower()

    def test_v2_insufficient_bars_skips_90d(self):
        """When fewer than 90 bars provided, falls back to profile volume."""
        profile = _healthy_profile()
        # Only 30 bars -> 90d median is None, falls back to profile avg
        bars = _make_bars(n=30, close=Decimal("100.00"), volume=1_000_000)
        result = liquidity_check_v2(profile, price_bars=bars)

        assert result.passed is True
        # Dollar volume comes from profile, not bars
        assert result.computed_metrics is not None
        assert "profile_avg" in result.detail

    def test_v2_computed_metrics_contains_impact_bps(self):
        """computed_metrics should include market_impact_bps when bars are provided."""
        profile = _healthy_profile()
        bars = _make_bars(n=90, close=Decimal("100.00"), volume=1_000_000)
        result = liquidity_check_v2(profile, price_bars=bars)

        assert result.computed_metrics is not None
        assert "market_impact_bps" in result.computed_metrics
        assert result.computed_metrics["market_impact_bps"] > 0

    def test_v2_custom_config(self):
        """v2 respects custom config thresholds."""
        profile = _healthy_profile()
        config = LiquidityConfig(
            min_years_of_history=3,
            divergence_max_ratio=5.0,
            position_sizing=PositionSizingConfig(
                target_position=1_000_000,
                max_participation_rate=0.10,
                max_days_to_fill=10,
            ),
        )
        bars = _make_bars(n=90, close=Decimal("100.00"), volume=1_000_000)
        result = liquidity_check_v2(profile, price_bars=bars, config=config)
        assert result.passed is True

    def test_v2_empty_bars_treated_as_none(self):
        """Empty price_bars list treated same as None."""
        profile = _healthy_profile()
        result = liquidity_check_v2(profile, price_bars=[])
        assert result.passed is True
        assert result.computed_metrics is not None
        assert "days_to_fill" not in result.computed_metrics

    def test_v2_default_config_when_none(self):
        """When config=None, v2 uses default LiquidityConfig."""
        profile = _healthy_profile()
        result_explicit = liquidity_check_v2(profile, config=LiquidityConfig())
        result_none = liquidity_check_v2(profile, config=None)
        assert result_explicit.passed == result_none.passed
