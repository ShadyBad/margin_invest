"""Beta computation from price history (CAPM)."""
from __future__ import annotations

import statistics

from margin_engine.models.financial import PriceBar

_MIN_BARS = 60
_MIN_BETA = 0.3
_MAX_BETA = 3.0


def compute_beta(
    stock_bars: list[PriceBar],
    market_bars: list[PriceBar],
) -> float:
    """Compute stock beta vs market from price bars.

    Beta = Cov(stock_returns, market_returns) / Var(market_returns)

    Returns 1.0 if insufficient data (<60 aligned bars).
    Clamped to [0.3, 3.0] to avoid extreme values.
    """
    if len(stock_bars) < _MIN_BARS or len(market_bars) < _MIN_BARS:
        return 1.0

    stock_sorted = sorted(stock_bars, key=lambda b: b.date)
    market_sorted = sorted(market_bars, key=lambda b: b.date)

    # Align by date
    market_by_date = {b.date: float(b.close) for b in market_sorted}
    aligned = [
        (float(b.close), market_by_date[b.date])
        for b in stock_sorted
        if b.date in market_by_date
    ]

    if len(aligned) < _MIN_BARS:
        return 1.0

    # Compute daily returns
    stock_returns: list[float] = []
    market_returns: list[float] = []
    for i in range(1, len(aligned)):
        if aligned[i - 1][0] > 0 and aligned[i - 1][1] > 0:
            stock_returns.append(aligned[i][0] / aligned[i - 1][0] - 1.0)
            market_returns.append(aligned[i][1] / aligned[i - 1][1] - 1.0)

    if len(stock_returns) < 30:
        return 1.0

    # Beta = Cov(stock, market) / Var(market)
    mean_s = statistics.mean(stock_returns)
    mean_m = statistics.mean(market_returns)
    n = len(stock_returns)
    cov = sum(
        (s - mean_s) * (m - mean_m) for s, m in zip(stock_returns, market_returns)
    ) / n
    var_m = sum((m - mean_m) ** 2 for m in market_returns) / n

    if var_m == 0:
        return 1.0

    beta = cov / var_m
    return max(_MIN_BETA, min(beta, _MAX_BETA))
