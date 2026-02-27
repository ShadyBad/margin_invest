"""Tests for circuit breakers — breadth suspension and variance guard."""

from __future__ import annotations

from margin_engine.healing.circuit_breakers import (
    check_sector_breadth,
    check_variance_compression,
)
from margin_engine.healing.models import HealingConfig

# ---------------------------------------------------------------------------
# Breadth suspension tests
# ---------------------------------------------------------------------------

class TestCheckSectorBreadth:
    """Test check_sector_breadth with default threshold of 0.15 (15%)."""

    def test_10_percent_not_suspended(self) -> None:
        """10% flagged is below 15% threshold — corrections should continue."""
        config = HealingConfig()
        flagged = {f"TICK{i}" for i in range(10)}  # 10 out of 100
        assert check_sector_breadth(flagged, sector_size=100, config=config) is False

    def test_20_percent_suspended(self) -> None:
        """20% flagged exceeds 15% threshold — corrections should be suspended."""
        config = HealingConfig()
        flagged = {f"TICK{i}" for i in range(20)}  # 20 out of 100
        assert check_sector_breadth(flagged, sector_size=100, config=config) is True

    def test_exactly_15_percent_suspended(self) -> None:
        """Exactly 15% flagged meets threshold (>=) — corrections suspended."""
        config = HealingConfig()
        flagged = {f"TICK{i}" for i in range(15)}  # 15 out of 100
        assert check_sector_breadth(flagged, sector_size=100, config=config) is True

    def test_zero_sector_size_not_suspended(self) -> None:
        """Zero sector size should return False (no division by zero)."""
        config = HealingConfig()
        flagged = {"AAPL", "MSFT"}
        assert check_sector_breadth(flagged, sector_size=0, config=config) is False

    def test_negative_sector_size_not_suspended(self) -> None:
        """Negative sector size should return False."""
        config = HealingConfig()
        flagged = {"AAPL"}
        assert check_sector_breadth(flagged, sector_size=-5, config=config) is False

    def test_empty_flagged_not_suspended(self) -> None:
        """No flagged tickers — corrections should continue."""
        config = HealingConfig()
        assert check_sector_breadth(set(), sector_size=50, config=config) is False

    def test_custom_threshold(self) -> None:
        """Custom threshold of 0.25 — 20% should not trigger suspension."""
        config = HealingConfig(sector_breadth_threshold=0.25)
        flagged = {f"TICK{i}" for i in range(20)}  # 20 out of 100 = 20%
        assert check_sector_breadth(flagged, sector_size=100, config=config) is False

    def test_all_tickers_flagged(self) -> None:
        """100% flagged — always suspended."""
        config = HealingConfig()
        flagged = {f"TICK{i}" for i in range(50)}
        assert check_sector_breadth(flagged, sector_size=50, config=config) is True


# ---------------------------------------------------------------------------
# Variance compression tests
# ---------------------------------------------------------------------------

class TestCheckVarianceCompression:
    """Test check_variance_compression with default floor of 0.85."""

    def test_no_compression_ok(self) -> None:
        """Corrected values preserve variance — no warning."""
        config = HealingConfig()
        raw = [10.0, 20.0, 30.0, 40.0, 50.0]
        # Corrected values with similar spread — ratio ~1.0
        corrected = [11.0, 21.0, 31.0, 41.0, 51.0]
        assert check_variance_compression(raw, corrected, config=config) is False

    def test_heavy_compression_flagged(self) -> None:
        """Corrected values heavily compressed — warning fires."""
        config = HealingConfig()
        raw = [10.0, 20.0, 30.0, 40.0, 50.0]
        # Squeeze all values toward the mean (30) — much lower stdev
        corrected = [28.0, 29.0, 30.0, 31.0, 32.0]
        assert check_variance_compression(raw, corrected, config=config) is True

    def test_insufficient_data_no_warning(self) -> None:
        """Fewer than 3 data points — cannot compute stdev, no warning."""
        config = HealingConfig()
        raw = [10.0, 20.0]
        corrected = [15.0, 15.0]
        assert check_variance_compression(raw, corrected, config=config) is False

    def test_empty_lists_no_warning(self) -> None:
        """Empty lists — no warning."""
        config = HealingConfig()
        assert check_variance_compression([], [], config=config) is False

    def test_single_element_no_warning(self) -> None:
        """Single element — insufficient data."""
        config = HealingConfig()
        assert check_variance_compression([5.0], [5.0], config=config) is False

    def test_raw_zero_stdev_no_warning(self) -> None:
        """All raw values identical (stdev=0) — no warning (avoid division by zero)."""
        config = HealingConfig()
        raw = [25.0, 25.0, 25.0, 25.0]
        corrected = [24.0, 25.0, 26.0, 27.0]
        assert check_variance_compression(raw, corrected, config=config) is False

    def test_exactly_at_floor_no_warning(self) -> None:
        """Ratio exactly at 0.85 — not below floor, no warning."""
        config = HealingConfig()
        # We need corrected_std / raw_std == 0.85 exactly
        # raw = [0, 10, 20] → stdev = 10.0
        # corrected needs stdev = 8.5 → e.g. [1.5, 10, 18.5] → stdev = 8.5
        raw = [0.0, 10.0, 20.0]
        corrected = [1.5, 10.0, 18.5]
        assert check_variance_compression(raw, corrected, config=config) is False

    def test_just_below_floor_warning(self) -> None:
        """Ratio just below 0.85 — warning fires."""
        config = HealingConfig()
        raw = [0.0, 10.0, 20.0]
        # stdev of raw = 10.0; need corrected stdev < 8.5
        # [2.0, 10.0, 18.0] → stdev = 8.0, ratio = 0.80
        corrected = [2.0, 10.0, 18.0]
        assert check_variance_compression(raw, corrected, config=config) is True

    def test_custom_floor(self) -> None:
        """Custom floor of 0.50 — moderate compression should be OK."""
        config = HealingConfig(variance_compression_floor=0.50)
        raw = [10.0, 20.0, 30.0, 40.0, 50.0]
        # Moderate compression
        corrected = [20.0, 25.0, 30.0, 35.0, 40.0]
        # corrected stdev / raw stdev ≈ 0.5 — exactly at floor, no warning
        assert check_variance_compression(raw, corrected, config=config) is False
