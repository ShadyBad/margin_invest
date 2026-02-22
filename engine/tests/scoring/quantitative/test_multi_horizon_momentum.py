"""Tests for multi-horizon momentum factor."""

import datetime
from decimal import Decimal

import pytest
from margin_engine.models.financial import PriceBar
from margin_engine.scoring.quantitative.multi_horizon_momentum import (
    multi_horizon_momentum,
)


def _make_bars(prices: list[float], start_date: str = "2023-01-01") -> list[PriceBar]:
    """Generate daily price bars from a list of closing prices."""
    start = datetime.date.fromisoformat(start_date)
    bars = []
    for i, p in enumerate(prices):
        d = start + datetime.timedelta(days=i)
        bars.append(
            PriceBar(
                date=d.isoformat(),
                open=Decimal(str(p)),
                high=Decimal(str(p)),
                low=Decimal(str(p)),
                close=Decimal(str(p)),
                volume=1000,
            )
        )
    return bars


def test_uptrend_positive_momentum():
    """Steadily rising prices should produce positive momentum across all horizons."""
    prices = [100.0 + (100.0 * i / 399) for i in range(400)]
    bars = _make_bars(prices)
    result = multi_horizon_momentum(bars)
    assert result.raw_value > 0
    assert result.name == "multi_horizon_momentum"


def test_downtrend_negative_momentum():
    """Steadily falling prices should produce negative momentum."""
    prices = [200.0 - (100.0 * i / 399) for i in range(400)]
    bars = _make_bars(prices)
    result = multi_horizon_momentum(bars)
    assert result.raw_value < 0


def test_insufficient_data():
    """< 100 days of data returns 0.0."""
    prices = [100.0] * 50
    bars = _make_bars(prices)
    result = multi_horizon_momentum(bars)
    assert result.raw_value == 0.0


def test_flat_prices_zero_momentum():
    """Flat prices produce ~0 momentum."""
    prices = [100.0] * 400
    bars = _make_bars(prices)
    result = multi_horizon_momentum(bars)
    assert result.raw_value == pytest.approx(0.0, abs=0.01)
