"""Tests for LiquidityProfile model and multi-window computation."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import PriceBar
from margin_engine.models.liquidity import LiquidityProfile, compute_liquidity_profile


def _make_bars(n: int, avg_close: float, avg_volume: int) -> list[PriceBar]:
    """Create n PriceBars with consistent close/volume for testing."""
    close = Decimal(str(avg_close))
    return [
        PriceBar(
            date=f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
            open=close,
            high=close + Decimal("1"),
            low=close - Decimal("1"),
            close=close,
            volume=avg_volume,
        )
        for i in range(n)
    ]


class TestLiquidityProfile:
    def test_profile_from_price_bars(self):
        """Compute median dollar volumes across 20/60/90 day windows."""
        bars = _make_bars(n=100, avg_close=150.0, avg_volume=1_000_000)
        profile = compute_liquidity_profile(
            bars=bars,
            listing_venue="NYSE",
            country_code="US",
        )
        assert profile.median_dollar_volume_20d > 0
        assert profile.median_dollar_volume_60d > 0
        assert profile.median_dollar_volume_90d > 0

    def test_profile_insufficient_bars(self):
        """Fewer than 20 bars should still compute available windows."""
        bars = _make_bars(n=15, avg_close=100.0, avg_volume=500_000)
        profile = compute_liquidity_profile(bars=bars)
        assert profile.median_dollar_volume_20d is None  # not enough
        assert profile.median_dollar_volume_60d is None
        assert profile.median_dollar_volume_90d is None

    def test_median_not_mean(self):
        """Median should resist outlier days with abnormal volume."""
        bars = _make_bars(n=25, avg_close=100.0, avg_volume=1_000_000)
        # Inject 3 extreme outlier days
        for i in range(3):
            bars[i] = PriceBar(
                date=bars[i].date,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=100_000_000,  # 100x normal
            )
        profile = compute_liquidity_profile(bars=bars)
        # Median should be close to normal, not pulled by outliers
        assert profile.median_dollar_volume_20d < Decimal("200_000_000")

    def test_exact_window_boundary(self):
        """Exactly 20 bars should compute 20d window but not 60d or 90d."""
        bars = _make_bars(n=20, avg_close=50.0, avg_volume=2_000_000)
        profile = compute_liquidity_profile(bars=bars)
        assert profile.median_dollar_volume_20d is not None
        assert profile.median_dollar_volume_60d is None
        assert profile.median_dollar_volume_90d is None

    def test_venue_and_country_stored(self):
        """listing_venue and country_code pass through to profile."""
        bars = _make_bars(n=25, avg_close=100.0, avg_volume=1_000_000)
        profile = compute_liquidity_profile(
            bars=bars,
            listing_venue="NASDAQ",
            country_code="US",
        )
        assert profile.listing_venue == "NASDAQ"
        assert profile.country_code == "US"

    def test_empty_bars(self):
        """Empty bar list should return all None windows."""
        profile = compute_liquidity_profile(bars=[])
        assert profile.median_dollar_volume_20d is None
        assert profile.median_dollar_volume_60d is None
        assert profile.median_dollar_volume_90d is None

    def test_median_dollar_volume_value(self):
        """Median dollar volume = median(close * volume) over window."""
        bars = _make_bars(n=20, avg_close=100.0, avg_volume=1_000_000)
        profile = compute_liquidity_profile(bars=bars)
        # All bars have close=100, volume=1_000_000
        # So every dollar_vol = 100 * 1_000_000 = 100_000_000
        expected = Decimal("100000000")
        assert profile.median_dollar_volume_20d == expected
