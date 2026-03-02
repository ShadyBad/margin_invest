"""Tests for beta computation from price history."""
import datetime
import math
from decimal import Decimal

import pytest

from margin_engine.models.financial import PriceBar
from margin_engine.scoring.quantitative.beta import compute_beta


def _make_bar(date_str: str, close: float) -> PriceBar:
    price = Decimal(str(close))
    return PriceBar(
        date=date_str, open=price, high=price, low=price, close=price, volume=1000000
    )


class TestComputeBeta:
    def test_perfect_correlation_beta_one(self):
        """Stock moving exactly with market -> beta ~ 1.0."""
        base = datetime.date(2020, 1, 1)
        stock_bars = []
        market_bars = []
        for i in range(252):
            d = (base + datetime.timedelta(days=i)).isoformat()
            price = 100.0 + i * 0.1
            stock_bars.append(_make_bar(d, round(price, 4)))
            market_bars.append(_make_bar(d, round(price, 4)))
        result = compute_beta(stock_bars, market_bars)
        assert result == pytest.approx(1.0, abs=0.05)

    def test_double_volatility_beta_two(self):
        """Stock with 2x market moves -> beta ~ 2.0."""
        base = datetime.date(2020, 1, 1)
        stock_bars = []
        market_bars = []
        for i in range(252):
            d = (base + datetime.timedelta(days=i)).isoformat()
            market_price = 100.0 + 10.0 * math.sin(i * 0.05)
            stock_price = 100.0 + 20.0 * math.sin(i * 0.05)  # 2x amplitude
            stock_bars.append(_make_bar(d, round(stock_price, 4)))
            market_bars.append(_make_bar(d, round(market_price, 4)))
        result = compute_beta(stock_bars, market_bars)
        assert result == pytest.approx(2.0, abs=0.15)

    def test_insufficient_data_returns_one(self):
        """Fewer than 60 bars -> fallback beta = 1.0."""
        bars = [_make_bar(f"2024-01-{i + 1:02d}", 100.0) for i in range(30)]
        result = compute_beta(bars, bars)
        assert result == 1.0

    def test_empty_bars_returns_one(self):
        """Empty input -> fallback beta = 1.0."""
        result = compute_beta([], [])
        assert result == 1.0

    def test_low_beta_clamped(self):
        """Beta should never go below 0.3."""
        base = datetime.date(2020, 1, 1)
        stock_bars = []
        market_bars = []
        for i in range(252):
            d = (base + datetime.timedelta(days=i)).isoformat()
            # Market oscillates, stock is almost flat
            market_bars.append(_make_bar(d, round(100.0 + 10.0 * math.sin(i * 0.1), 4)))
            stock_bars.append(_make_bar(d, round(100.0 + 0.01 * math.sin(i * 0.1), 4)))
        result = compute_beta(stock_bars, market_bars)
        assert result >= 0.3

    def test_no_date_overlap_returns_one(self):
        """Stock and market bars with no overlapping dates -> fallback 1.0."""
        base_stock = datetime.date(2020, 1, 1)
        base_market = datetime.date(2021, 1, 1)
        stock_bars = [
            _make_bar((base_stock + datetime.timedelta(days=i)).isoformat(), 100.0 + i * 0.1)
            for i in range(100)
        ]
        market_bars = [
            _make_bar((base_market + datetime.timedelta(days=i)).isoformat(), 100.0 + i * 0.1)
            for i in range(100)
        ]
        result = compute_beta(stock_bars, market_bars)
        assert result == 1.0

    def test_high_beta_clamped(self):
        """Beta should never exceed 3.0."""
        base = datetime.date(2020, 1, 1)
        stock_bars = []
        market_bars = []
        for i in range(252):
            d = (base + datetime.timedelta(days=i)).isoformat()
            market_price = 100.0 + 1.0 * math.sin(i * 0.05)
            stock_price = 100.0 + 50.0 * math.sin(i * 0.05)  # 50x amplitude
            stock_bars.append(_make_bar(d, round(stock_price, 4)))
            market_bars.append(_make_bar(d, round(market_price, 4)))
        result = compute_beta(stock_bars, market_bars)
        assert result <= 3.0

    def test_zero_variance_market_returns_one(self):
        """If market is flat (zero variance), return fallback 1.0."""
        base = datetime.date(2020, 1, 1)
        stock_bars = []
        market_bars = []
        for i in range(252):
            d = (base + datetime.timedelta(days=i)).isoformat()
            stock_bars.append(_make_bar(d, 100.0 + i * 0.1))
            market_bars.append(_make_bar(d, 100.0))  # flat market
        result = compute_beta(stock_bars, market_bars)
        assert result == 1.0
