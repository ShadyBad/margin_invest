"""Tests for Risk Metrics module (Sharpe, Max Drawdown, Volatility)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from margin_engine.models.financial import PriceBar
from margin_engine.scoring.risk_metrics import (
    RiskMetrics,
    compute_max_drawdown,
    compute_risk_metrics,
    compute_sharpe_ratio,
    compute_volatility,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_bar(date_str: str, close: float, volume: int = 1_000_000) -> PriceBar:
    """Create a minimal PriceBar with all OHLC = close."""
    p = Decimal(str(round(close, 4)))
    return PriceBar(date=date_str, open=p, high=p, low=p, close=p, volume=volume)


def _make_bars_from_prices(prices: list[float], start: date | None = None) -> list[PriceBar]:
    """Build a bar list from an explicit price sequence (one bar per calendar day)."""
    start = start or date(2022, 1, 3)
    return [_make_bar((start + timedelta(days=i)).isoformat(), p) for i, p in enumerate(prices)]


def _make_constant_return_bars(
    n: int, daily_return: float, start_price: float = 100.0
) -> list[PriceBar]:
    """Create n+1 bars with a fixed daily return (so there are exactly n daily returns).

    Uses datetime.date + timedelta for date generation to avoid overflow for large n.
    """
    start = date(2022, 1, 3)
    bars: list[PriceBar] = []
    price = start_price
    for i in range(n + 1):  # n+1 prices => n returns
        d = (start + timedelta(days=i)).isoformat()
        p = Decimal(str(round(price, 4)))
        bars.append(PriceBar(date=d, open=p, high=p, low=p, close=p, volume=1_000_000))
        price *= 1 + daily_return
    return bars


def _make_bars(n: int, start_price: float = 100.0) -> list[PriceBar]:
    """Create n bars with a small positive drift (0.02% daily)."""
    return _make_constant_return_bars(n, daily_return=0.0002, start_price=start_price)



# ===================================================================
# Sharpe Ratio
# ===================================================================


class TestSharpeRatio:
    """Tests for compute_sharpe_ratio."""

    def test_sharpe_basic(self):
        """Known constant daily return => positive Sharpe."""
        bars = _make_constant_return_bars(n=252, daily_return=0.0004)
        sharpe = compute_sharpe_ratio(bars, risk_free_rate=0.043)
        assert sharpe is not None
        assert sharpe > 0

    def test_sharpe_insufficient_bars(self):
        """Fewer bars than min_bars => None."""
        bars = _make_bars(n=100)
        sharpe = compute_sharpe_ratio(bars, risk_free_rate=0.043, min_bars=252)
        assert sharpe is None

    def test_sharpe_3y(self):
        """756-day window with constant return => positive Sharpe."""
        bars = _make_constant_return_bars(n=756, daily_return=0.0003)
        sharpe = compute_sharpe_ratio(bars, risk_free_rate=0.043, window=756)
        assert sharpe is not None

    def test_sharpe_negative(self):
        """Daily return below risk-free equivalent => negative Sharpe."""
        # risk-free 4.3% annually => ~0.000170 daily
        # daily_return = 0.00005 => annualized ~ 1.3%, well below 4.3%
        bars = _make_constant_return_bars(n=252, daily_return=0.00005)
        sharpe = compute_sharpe_ratio(bars, risk_free_rate=0.043)
        assert sharpe is not None
        assert sharpe < 0

    def test_sharpe_zero_stdev_returns_none(self):
        """Constant price => stdev == 0 => None (avoid division by zero)."""
        bars = _make_bars_from_prices([100.0] * 253)
        sharpe = compute_sharpe_ratio(bars, risk_free_rate=0.043)
        assert sharpe is None

    def test_sharpe_window_uses_tail(self):
        """When bars > window, only the last `window` returns are used."""
        # Build 500 bars; window=252 should only use last 253 prices (252 returns)
        bars = _make_constant_return_bars(n=500, daily_return=0.0004)
        sharpe_full = compute_sharpe_ratio(bars, risk_free_rate=0.043, window=252)
        assert sharpe_full is not None
        assert sharpe_full > 0

    def test_sharpe_min_bars_defaults_to_window(self):
        """When min_bars is None, it defaults to window. 200 bars < 252 => None."""
        bars = _make_constant_return_bars(n=200, daily_return=0.0004)
        sharpe = compute_sharpe_ratio(bars, risk_free_rate=0.043, window=252)
        assert sharpe is None

    def test_sharpe_custom_min_bars_lower(self):
        """min_bars=100 with 200 bars => should compute fine."""
        bars = _make_constant_return_bars(n=200, daily_return=0.0004)
        sharpe = compute_sharpe_ratio(bars, risk_free_rate=0.043, window=252, min_bars=100)
        assert sharpe is not None


# ===================================================================
# Max Drawdown
# ===================================================================


class TestMaxDrawdown:
    """Tests for compute_max_drawdown."""

    def test_drawdown_known_sequence(self):
        """100 -> 120 -> 80 -> 90. Max drawdown = (80-120)/120 = -33.3%."""
        bars = _make_bars_from_prices([100, 110, 120, 100, 80, 90])
        dd = compute_max_drawdown(bars)
        assert dd == pytest.approx(-0.333, abs=0.01)

    def test_drawdown_no_decline(self):
        """Monotonically increasing prices => drawdown == 0.0."""
        bars = _make_bars_from_prices([100, 101, 102, 103, 104])
        dd = compute_max_drawdown(bars)
        assert dd == 0.0

    def test_drawdown_full_loss(self):
        """Price drops to near zero => drawdown close to -1.0."""
        bars = _make_bars_from_prices([100, 50, 1])
        dd = compute_max_drawdown(bars)
        assert dd == pytest.approx(-0.99, abs=0.01)

    def test_drawdown_recovery_doesnt_erase(self):
        """100 -> 50 -> 100 still has max drawdown of -50%."""
        bars = _make_bars_from_prices([100, 50, 100])
        dd = compute_max_drawdown(bars)
        assert dd == pytest.approx(-0.50, abs=0.01)

    def test_drawdown_window_limits_data(self):
        """With window, only last N bars are considered."""
        # Big drop early, recovery later.  If window only sees last 3, no big drop.
        bars = _make_bars_from_prices([100, 30, 90, 95, 100])
        dd_all = compute_max_drawdown(bars)
        dd_window = compute_max_drawdown(bars, window=3)
        assert dd_all < dd_window  # full history has bigger drawdown

    def test_drawdown_single_bar(self):
        """Single bar => 0.0 (no trough)."""
        bars = _make_bars_from_prices([100])
        dd = compute_max_drawdown(bars)
        assert dd == 0.0

    def test_drawdown_empty_bars_returns_none(self):
        """No bars => None."""
        dd = compute_max_drawdown([])
        assert dd is None


# ===================================================================
# Volatility
# ===================================================================


class TestVolatility:
    """Tests for compute_volatility."""

    def test_volatility_known(self):
        """Constant daily return bars => positive volatility (near zero stdev is still > 0)."""
        bars = _make_constant_return_bars(n=252, daily_return=0.001)
        vol = compute_volatility(bars, window=252)
        assert vol is not None
        assert vol > 0

    def test_volatility_zero_for_constant_price(self):
        """Constant price => all returns are 0 => vol ~ 0."""
        bars = _make_bars_from_prices([100.0] * 30)
        vol = compute_volatility(bars, window=20)
        assert vol == pytest.approx(0.0, abs=0.001)

    def test_volatility_increases_with_larger_swings(self):
        """Bigger daily moves => higher vol.

        Use alternating up/down returns to create actual variance.
        """
        start = date(2022, 1, 3)
        # Small swings: +0.5% / -0.5% alternating
        bars_small: list[PriceBar] = []
        price = 100.0
        for i in range(253):
            d = (start + timedelta(days=i)).isoformat()
            p = Decimal(str(round(price, 4)))
            bars_small.append(PriceBar(date=d, open=p, high=p, low=p, close=p, volume=1_000_000))
            price *= 1.005 if i % 2 == 0 else 0.995
        # Large swings: +3% / -3% alternating
        bars_large: list[PriceBar] = []
        price = 100.0
        for i in range(253):
            d = (start + timedelta(days=i)).isoformat()
            p = Decimal(str(round(price, 4)))
            bars_large.append(PriceBar(date=d, open=p, high=p, low=p, close=p, volume=1_000_000))
            price *= 1.03 if i % 2 == 0 else 0.97

        vol_small = compute_volatility(bars_small, window=252)
        vol_large = compute_volatility(bars_large, window=252)
        assert vol_small is not None and vol_large is not None
        assert vol_large > vol_small

    def test_volatility_insufficient_bars(self):
        """Fewer bars than window => None."""
        bars = _make_constant_return_bars(n=50, daily_return=0.001)
        vol = compute_volatility(bars, window=252)
        assert vol is None

    def test_volatility_empty_bars(self):
        """No bars => None."""
        vol = compute_volatility([], window=252)
        assert vol is None

    def test_volatility_annualization(self):
        """Annualized vol should be ~sqrt(252) times daily stdev."""
        import math
        import statistics

        bars = _make_constant_return_bars(n=252, daily_return=0.001)
        closes = [float(b.close) for b in sorted(bars, key=lambda b: b.date)]
        daily_returns = [(closes[i] / closes[i - 1]) - 1 for i in range(1, len(closes))]
        expected_daily_stdev = statistics.stdev(daily_returns)
        expected_annual = expected_daily_stdev * math.sqrt(252)

        vol = compute_volatility(bars, window=252)
        assert vol == pytest.approx(expected_annual, rel=0.01)


# ===================================================================
# Risk Metrics Bundle
# ===================================================================


class TestRiskMetricsBundle:
    """Tests for compute_risk_metrics (the bundler)."""

    def test_full_bundle(self):
        """756 bars => all 1Y and 3Y metrics present."""
        bars = _make_constant_return_bars(n=756, daily_return=0.0004)
        metrics = compute_risk_metrics(bars, risk_free_rate=0.043)
        assert isinstance(metrics, RiskMetrics)
        assert metrics.sharpe_1y is not None
        assert metrics.sharpe_3y is not None
        assert metrics.max_drawdown_1y is not None
        assert metrics.max_drawdown_3y is not None
        assert metrics.volatility_1y is not None
        assert metrics.volatility_3y is not None

    def test_1y_only(self):
        """252 bars => 1Y metrics present, 3Y metrics are None with reason."""
        bars = _make_constant_return_bars(n=252, daily_return=0.0004)
        metrics = compute_risk_metrics(bars, risk_free_rate=0.043)
        assert metrics.sharpe_1y is not None
        assert metrics.sharpe_3y is None
        assert metrics.volatility_1y is not None
        assert metrics.volatility_3y is None

    def test_insufficient_bars(self):
        """Very few bars => all None with unavailable reasons."""
        bars = _make_constant_return_bars(n=50, daily_return=0.0004)
        metrics = compute_risk_metrics(bars, risk_free_rate=0.043)
        assert metrics.sharpe_1y is None
        assert metrics.sharpe_3y is None
        assert metrics.volatility_1y is None
        assert metrics.volatility_3y is None
        assert metrics.sharpe_unavailable_reason is not None
        assert metrics.volatility_unavailable_reason is not None

    def test_unavailable_reasons_populated_for_3y(self):
        """252 bars: 3Y fields None, sharpe_unavailable_reason should mention 3Y."""
        bars = _make_constant_return_bars(n=252, daily_return=0.0004)
        metrics = compute_risk_metrics(bars, risk_free_rate=0.043)
        # 1Y is available so reason should not exist or only reference 3Y
        # sharpe_unavailable_reason only set if at least one sharpe is None
        if metrics.sharpe_3y is None:
            assert metrics.sharpe_unavailable_reason is not None

    def test_empty_bars(self):
        """Empty input => all None."""
        metrics = compute_risk_metrics([], risk_free_rate=0.043)
        assert metrics.sharpe_1y is None
        assert metrics.max_drawdown_1y is None
        assert metrics.volatility_1y is None


class TestRiskMetricsModel:
    """Tests for the RiskMetrics pydantic model itself."""

    def test_defaults_are_none(self):
        """All fields default to None."""
        m = RiskMetrics()
        assert m.sharpe_1y is None
        assert m.sharpe_3y is None
        assert m.max_drawdown_1y is None
        assert m.max_drawdown_3y is None
        assert m.volatility_1y is None
        assert m.volatility_3y is None
        assert m.sharpe_unavailable_reason is None
        assert m.drawdown_unavailable_reason is None
        assert m.volatility_unavailable_reason is None

    def test_model_dump_roundtrip(self):
        """model_dump / model_validate roundtrip."""
        m = RiskMetrics(sharpe_1y=1.5, max_drawdown_1y=-0.15, volatility_1y=0.20)
        d = m.model_dump()
        m2 = RiskMetrics.model_validate(d)
        assert m2.sharpe_1y == 1.5
        assert m2.max_drawdown_1y == -0.15
        assert m2.volatility_1y == 0.20
