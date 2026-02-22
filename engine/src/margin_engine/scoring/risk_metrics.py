"""Risk metrics: Sharpe ratio, max drawdown, and annualized volatility.

Computes risk metrics from daily price bars for both 1-year (252-day)
and 3-year (756-day) horizons.  All calculations use simple daily returns
(close-to-close) and Python stdlib ``statistics`` functions.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from pydantic import BaseModel

from margin_engine.models.financial import PriceBar

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRADING_DAYS_PER_YEAR = 252
WINDOW_1Y = 252
WINDOW_3Y = 756


# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------


class RiskMetrics(BaseModel):
    """Bundle of risk metrics across 1-year and 3-year windows."""

    sharpe_1y: float | None = None
    sharpe_3y: float | None = None
    max_drawdown_1y: float | None = None
    max_drawdown_3y: float | None = None
    volatility_1y: float | None = None
    volatility_3y: float | None = None
    sharpe_unavailable_reason: str | None = None
    drawdown_unavailable_reason: str | None = None
    volatility_unavailable_reason: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sorted_closes(bars: Sequence[PriceBar]) -> list[float]:
    """Return close prices sorted by date ascending."""
    sorted_bars = sorted(bars, key=lambda b: b.date)
    return [float(b.close) for b in sorted_bars]


def _daily_returns(closes: list[float]) -> list[float]:
    """Compute simple daily returns from a list of close prices."""
    return [(closes[i] / closes[i - 1]) - 1.0 for i in range(1, len(closes))]


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def compute_sharpe_ratio(
    bars: Sequence[PriceBar],
    risk_free_rate: float = 0.043,
    window: int = WINDOW_1Y,
    min_bars: int | None = None,
) -> float | None:
    """Annualized Sharpe ratio.

    Formula:
        (mean_daily_return * 252 - risk_free_rate) / (stdev_daily_returns * sqrt(252))

    Parameters
    ----------
    bars : sequence of PriceBar
        Daily OHLCV bars.
    risk_free_rate : float
        Annualized risk-free rate (default 4.3%).
    window : int
        Number of *returns* to use (default 252).  If len(bars) > window+1,
        only the last ``window+1`` bars (→ ``window`` returns) are used.
    min_bars : int | None
        Minimum number of returns required.  Defaults to ``window`` when None.

    Returns
    -------
    float | None
        Sharpe ratio, or None if insufficient data or zero volatility.
    """
    effective_min = min_bars if min_bars is not None else window

    closes = _sorted_closes(bars)
    # We need at least effective_min+1 prices to produce effective_min returns
    if len(closes) < effective_min + 1:
        return None

    # Trim to window
    tail = closes[-(window + 1) :] if len(closes) > window + 1 else closes
    returns = _daily_returns(tail)

    if len(returns) < 2:
        return None

    daily_stdev = statistics.stdev(returns)
    if daily_stdev == 0.0:
        return None

    mean_daily = statistics.mean(returns)
    annualized_return = mean_daily * TRADING_DAYS_PER_YEAR
    annualized_stdev = daily_stdev * math.sqrt(TRADING_DAYS_PER_YEAR)

    return (annualized_return - risk_free_rate) / annualized_stdev


def compute_max_drawdown(
    bars: Sequence[PriceBar],
    window: int | None = None,
) -> float | None:
    """Maximum peak-to-trough decline.

    Returns a non-positive number (e.g., -0.333 for a 33.3% drawdown).
    Returns 0.0 for monotonically increasing prices.
    Returns None for empty input.

    Parameters
    ----------
    bars : sequence of PriceBar
        Daily OHLCV bars.
    window : int | None
        If set, only the last ``window`` bars are considered.
    """
    if not bars:
        return None

    closes = _sorted_closes(bars)
    if window is not None and len(closes) > window:
        closes = closes[-window:]

    if len(closes) < 2:
        return 0.0

    peak = closes[0]
    max_dd = 0.0

    for price in closes[1:]:
        if price > peak:
            peak = price
        else:
            dd = (price - peak) / peak
            if dd < max_dd:
                max_dd = dd

    return max_dd


def compute_volatility(
    bars: Sequence[PriceBar],
    window: int = WINDOW_1Y,
) -> float | None:
    """Annualized volatility.

    Formula: stdev(daily_returns) * sqrt(252)

    Parameters
    ----------
    bars : sequence of PriceBar
        Daily OHLCV bars.
    window : int
        Number of returns to use (default 252).  Requires at least
        ``window + 1`` bars.

    Returns
    -------
    float | None
        Annualized volatility, or None if insufficient data.
    """
    closes = _sorted_closes(bars)

    if len(closes) < window + 1:
        return None

    tail = closes[-(window + 1) :]
    returns = _daily_returns(tail)

    if len(returns) < 2:
        return None

    daily_stdev = statistics.stdev(returns)
    return daily_stdev * math.sqrt(TRADING_DAYS_PER_YEAR)


def compute_risk_metrics(
    bars: Sequence[PriceBar],
    risk_free_rate: float = 0.043,
) -> RiskMetrics:
    """Compute all risk metrics for 1Y and 3Y windows.

    Populates ``_unavailable_reason`` fields when a metric cannot be computed.
    """
    sharpe_1y = compute_sharpe_ratio(bars, risk_free_rate=risk_free_rate, window=WINDOW_1Y)
    sharpe_3y = compute_sharpe_ratio(bars, risk_free_rate=risk_free_rate, window=WINDOW_3Y)

    dd_1y = compute_max_drawdown(bars, window=WINDOW_1Y)
    dd_3y = compute_max_drawdown(bars, window=WINDOW_3Y)

    vol_1y = compute_volatility(bars, window=WINDOW_1Y)
    vol_3y = compute_volatility(bars, window=WINDOW_3Y)

    n_bars = len(bars)

    # Build unavailable reasons
    sharpe_reason: str | None = None
    if sharpe_1y is None or sharpe_3y is None:
        missing = []
        if sharpe_1y is None:
            missing.append(f"1Y (need >= {WINDOW_1Y + 1} bars, have {n_bars})")
        if sharpe_3y is None:
            missing.append(f"3Y (need >= {WINDOW_3Y + 1} bars, have {n_bars})")
        sharpe_reason = "Sharpe unavailable: " + "; ".join(missing)

    dd_reason: str | None = None
    if dd_1y is None or dd_3y is None:
        missing = []
        if dd_1y is None:
            missing.append(f"1Y (need >= 1 bar, have {n_bars})")
        if dd_3y is None:
            missing.append(f"3Y (need >= 1 bar, have {n_bars})")
        dd_reason = "Max drawdown unavailable: " + "; ".join(missing)

    vol_reason: str | None = None
    if vol_1y is None or vol_3y is None:
        missing = []
        if vol_1y is None:
            missing.append(f"1Y (need >= {WINDOW_1Y + 1} bars, have {n_bars})")
        if vol_3y is None:
            missing.append(f"3Y (need >= {WINDOW_3Y + 1} bars, have {n_bars})")
        vol_reason = "Volatility unavailable: " + "; ".join(missing)

    return RiskMetrics(
        sharpe_1y=sharpe_1y,
        sharpe_3y=sharpe_3y,
        max_drawdown_1y=dd_1y,
        max_drawdown_3y=dd_3y,
        volatility_1y=vol_1y,
        volatility_3y=vol_3y,
        sharpe_unavailable_reason=sharpe_reason,
        drawdown_unavailable_reason=dd_reason,
        volatility_unavailable_reason=vol_reason,
    )
