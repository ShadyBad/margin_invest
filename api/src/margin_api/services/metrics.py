"""Institutional metrics calculation service.

Computes Sharpe ratio, max drawdown, volatility, avg profit margin,
and risk classification from stored financial data.

Constants:
    RISK_FREE_RATE: 5% annualized (conservative; US 10Y ~4.3% as of 2026)
    TRADING_DAYS_PER_YEAR: 252
    MIN_BARS_FOR_STATS: 5 (minimum price bars required)
"""

from __future__ import annotations

import math

RISK_FREE_RATE = 0.05
TRADING_DAYS_PER_YEAR = 252
MIN_BARS_FOR_STATS = 5


def _daily_returns(closes: list[float]) -> list[float]:
    returns = []
    for i in range(1, len(closes)):
        if math.isnan(closes[i]) or math.isnan(closes[i - 1]):
            continue
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
    return returns


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _stddev(values: list[float]) -> float:
    m = _mean(values)
    variance = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def compute_sharpe_ratio(closes: list[float]) -> float | None:
    """Annualized Sharpe ratio from daily close prices.

    Formula: ((mean_daily_return - Rf/252) / std_daily_return) * sqrt(252)
    Returns None if < 5 bars or zero standard deviation.
    """
    returns = _daily_returns(closes)
    if len(returns) < MIN_BARS_FOR_STATS:
        return None

    daily_std = _stddev(returns)
    if daily_std == 0:
        return None

    avg_daily_return = _mean(returns)
    daily_rf = RISK_FREE_RATE / TRADING_DAYS_PER_YEAR
    sharpe = ((avg_daily_return - daily_rf) / daily_std) * math.sqrt(TRADING_DAYS_PER_YEAR)
    return round(sharpe, 2)


def compute_max_drawdown(closes: list[float]) -> float:
    """Maximum peak-to-trough decline as a decimal (e.g., -0.20 for 20% drawdown)."""
    peak = -math.inf
    max_dd = 0.0
    for close in closes:
        if math.isnan(close):
            continue
        if close > peak:
            peak = close
        dd = (close - peak) / peak if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 4)


def compute_volatility(closes: list[float]) -> float | None:
    """Annualized volatility as a percentage (e.g., 25.3 for 25.3%).

    Formula: std(daily_returns) * sqrt(252) * 100
    Returns None if < 5 bars.
    """
    returns = _daily_returns(closes)
    if len(returns) < MIN_BARS_FOR_STATS:
        return None

    annualized = _stddev(returns) * math.sqrt(TRADING_DAYS_PER_YEAR) * 100
    return round(annualized, 1)


def _get_field(period: dict, *candidates: str) -> float | None:
    """Try multiple key variants for yfinance compatibility."""
    for key in candidates:
        if key in period:
            val = period[key]
            return float(val) if val is not None else None
    return None


def compute_avg_profit_margin(income_periods: list[dict]) -> float | None:
    """Average net profit margin across income statement periods.

    Computes net_income / total_revenue for each period, returns the mean as a percentage.
    Skips periods with zero or missing revenue.
    Returns None if no valid periods.
    """
    margins = []
    for period in income_periods:
        net_income = _get_field(period, "net_income", "Net Income", "netIncome")
        total_revenue = _get_field(period, "total_revenue", "Total Revenue", "totalRevenue")
        if net_income is None or total_revenue is None or total_revenue == 0:
            continue
        margins.append((net_income / total_revenue) * 100)

    if not margins:
        return None
    return round(_mean(margins), 1)


def classify_risk(volatility: float | None) -> str:
    """Classify risk based on annualized volatility percentage."""
    if volatility is None:
        return "Unknown"
    if volatility > 40:
        return "Aggressive"
    if volatility > 25:
        return "Moderate-High"
    if volatility > 15:
        return "Moderate"
    return "Conservative"
