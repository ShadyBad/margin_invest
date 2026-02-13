"""Tests for Price Momentum (12-1 month) factor (Jegadeesh & Titman)."""

import datetime
from decimal import Decimal

import pytest
from margin_engine.models.financial import PriceBar
from margin_engine.models.scoring import FactorScore
from margin_engine.scoring.quantitative.price_momentum import price_momentum


def _make_bar(date_str: str, close: float, volume: int = 100_000) -> PriceBar:
    """Helper to create a minimal PriceBar."""
    price = Decimal(str(close))
    return PriceBar(
        date=date_str,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=volume,
    )


def _generate_daily_bars(
    start_date: str,
    num_days: int,
    start_price: float,
    end_price: float,
) -> list[PriceBar]:
    """Generate synthetic daily bars with linear price interpolation.

    Creates bars for every calendar day (weekends included for simplicity).
    """
    base = datetime.date.fromisoformat(start_date)
    bars = []
    for i in range(num_days):
        t = i / max(num_days - 1, 1)
        price = start_price + (end_price - start_price) * t
        d = base + datetime.timedelta(days=i)
        bars.append(_make_bar(d.isoformat(), round(price, 2)))
    return bars


class TestPriceMomentumBasic:
    """Core computation tests."""

    def test_positive_momentum_roughly_20_percent(self):
        """Synthetic 13-month daily data: price goes from 100 -> 120 over 12 months,
        then stays flat for the last month. Momentum should be ~0.20."""
        # 365 days of data from 100 to 120 (the price 12 months ago to 1 month ago)
        # then 30 more days at 120 (the excluded last month)
        base_date = datetime.date(2025, 1, 1)
        bars = []

        # From T-12 months (day 0) to T-1 month (day 335): price rises 100 -> 120
        for i in range(336):
            t = i / 335
            price = 100.0 + 20.0 * t
            d = base_date + datetime.timedelta(days=i)
            bars.append(_make_bar(d.isoformat(), round(price, 2)))

        # From T-1 month to T-0 (day 336 to day 395): price stays at 120
        for i in range(336, 396):
            d = base_date + datetime.timedelta(days=i)
            bars.append(_make_bar(d.isoformat(), 120.0))

        result = price_momentum(bars)

        # The most recent date is base_date + 395 days = 2026-02-01 (approx)
        # T-1 month: ~30 days back -> bar closest to 2026-01-02 -> price ~120
        # T-12 months: ~365 days back -> bar closest to 2025-02-01 -> price ~100
        # Momentum = (120 / 100) - 1 = 0.20
        assert result.raw_value == pytest.approx(0.20, abs=0.03)

    def test_negative_momentum(self):
        """Stock declining from 100 to 70 should give ~-0.30 momentum."""
        base_date = datetime.date(2025, 1, 1)
        bars = []

        # From day 0 to day 335: price drops 100 -> 70
        for i in range(336):
            t = i / 335
            price = 100.0 - 30.0 * t
            d = base_date + datetime.timedelta(days=i)
            bars.append(_make_bar(d.isoformat(), round(price, 2)))

        # Last month: price stays at 70
        for i in range(336, 396):
            d = base_date + datetime.timedelta(days=i)
            bars.append(_make_bar(d.isoformat(), 70.0))

        result = price_momentum(bars)

        # T-1 month price: ~70, T-12 months price: ~100
        # Momentum = (70 / 100) - 1 = -0.30
        assert result.raw_value == pytest.approx(-0.30, abs=0.03)

    def test_flat_price_zero_momentum(self):
        """Stock that stays flat at 50 should give ~0.0 momentum."""
        bars = _generate_daily_bars("2025-01-01", 396, 50.0, 50.0)
        result = price_momentum(bars)
        assert result.raw_value == pytest.approx(0.0, abs=0.01)


class TestPriceMomentumEdgeCases:
    """Edge cases and error handling."""

    def test_fewer_than_two_bars(self):
        """With fewer than 2 bars, return raw_value=0.0."""
        result = price_momentum([_make_bar("2025-06-01", 100.0)])
        assert result.raw_value == 0.0
        assert "insufficient" in result.detail.lower()

    def test_empty_bars(self):
        """With no bars at all, return raw_value=0.0."""
        result = price_momentum([])
        assert result.raw_value == 0.0
        assert "insufficient" in result.detail.lower()

    def test_zero_price_t12(self):
        """If the T-12 month price is zero, return raw_value=0.0."""
        base_date = datetime.date(2025, 1, 1)
        bars = []
        # Start with price=0, then go to price=100
        for i in range(396):
            if i < 50:
                price = 0.0
            else:
                price = 100.0
            d = base_date + datetime.timedelta(days=i)
            bars.append(_make_bar(d.isoformat(), price))

        result = price_momentum(bars)
        assert result.raw_value == 0.0
        assert "zero" in result.detail.lower()

    def test_insufficient_history(self):
        """With only 2 months of data, T-12 is unavailable. Should return 0.0."""
        # Only 60 days of data — not enough for 12-month lookback
        bars = _generate_daily_bars("2025-10-01", 60, 100.0, 110.0)
        result = price_momentum(bars)
        assert result.raw_value == 0.0
        assert "insufficient" in result.detail.lower()


class TestPriceMomentumFactorScore:
    """Tests for FactorScore metadata fields."""

    def test_name_is_price_momentum(self):
        """Factor name should be 'price_momentum'."""
        bars = _generate_daily_bars("2025-01-01", 396, 100.0, 120.0)
        result = price_momentum(bars)
        assert result.name == "price_momentum"

    def test_returns_factor_score_type(self):
        """Should return a FactorScore instance."""
        bars = _generate_daily_bars("2025-01-01", 396, 100.0, 120.0)
        result = price_momentum(bars)
        assert isinstance(result, FactorScore)

    def test_percentile_rank_is_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6)."""
        bars = _generate_daily_bars("2025-01-01", 396, 100.0, 120.0)
        result = price_momentum(bars)
        assert result.percentile_rank == 0.0

    def test_detail_contains_breakdown(self):
        """Detail string should contain a human-readable breakdown."""
        bars = _generate_daily_bars("2025-01-01", 396, 100.0, 120.0)
        result = price_momentum(bars)
        # Should mention the T-1 month and T-12 month prices
        assert "price_t1" in result.detail or "T-1" in result.detail
        assert "price_t12" in result.detail or "T-12" in result.detail


class TestPriceMomentumSorting:
    """Test that bars are sorted properly regardless of input order."""

    def test_unsorted_bars_still_work(self):
        """Bars passed in random order should produce the same result as sorted."""
        import random

        bars = _generate_daily_bars("2025-01-01", 396, 100.0, 120.0)
        sorted_result = price_momentum(bars)

        shuffled = bars.copy()
        random.seed(42)
        random.shuffle(shuffled)
        shuffled_result = price_momentum(shuffled)

        assert sorted_result.raw_value == pytest.approx(shuffled_result.raw_value, abs=1e-9)
