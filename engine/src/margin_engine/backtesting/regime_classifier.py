"""Historical market regime classifier.

Classifies dates into Bull, Bear, Sideways, or Crisis using S&P 500
drawdown thresholds, VIX levels, and NBER recession dates.
"""

from __future__ import annotations

import math
from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class MarketRegimeHistorical(StrEnum):
    """Market regime classification for backtesting."""

    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    CRISIS = "crisis"


class RegimeSegment(BaseModel):
    """Aggregated performance within a single regime."""

    regime: MarketRegimeHistorical
    num_months: int
    portfolio_returns: list[float]
    benchmark_returns: list[float]

    @property
    def total_portfolio_return(self) -> float:
        return math.prod(1.0 + r for r in self.portfolio_returns) - 1.0

    @property
    def total_benchmark_return(self) -> float:
        return math.prod(1.0 + r for r in self.benchmark_returns) - 1.0

    @property
    def max_drawdown(self) -> float:
        if not self.portfolio_returns:
            return 0.0
        peak = 1.0
        value = 1.0
        max_dd = 0.0
        for r in self.portfolio_returns:
            value *= 1.0 + r
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd


class RegimePeriod(BaseModel):
    """A time-stamped regime classification."""

    as_of_date: date
    regime: MarketRegimeHistorical
    drawdown_from_peak: float
    vix: float | None = None


def classify_regime(
    drawdown_from_peak: float,
    vix: float | None = None,
    in_nber_recession: bool = False,
) -> MarketRegimeHistorical:
    """Classify a market regime from drawdown and VIX.

    Thresholds:
    - Crisis: drawdown > 20% AND (VIX > 30 OR NBER recession)
    - Bear: drawdown > 20%
    - Sideways: drawdown 10-20%
    - Bull: drawdown < 10%
    """
    vix_val = vix or 0.0

    if drawdown_from_peak > 0.20 and (vix_val > 30.0 or in_nber_recession):
        return MarketRegimeHistorical.CRISIS
    if drawdown_from_peak > 0.20:
        return MarketRegimeHistorical.BEAR
    if drawdown_from_peak > 0.10:
        return MarketRegimeHistorical.SIDEWAYS
    return MarketRegimeHistorical.BULL


def get_nber_recessions() -> list[tuple[date, date]]:
    """Return NBER recession date ranges (start, end).

    Source: National Bureau of Economic Research.
    Covers recessions relevant to 2005-2025 backtesting window.
    """
    return [
        (date(2007, 12, 1), date(2009, 6, 30)),  # Great Financial Crisis
        (date(2020, 2, 1), date(2020, 4, 30)),  # COVID-19
    ]


def is_in_recession(as_of: date) -> bool:
    """Check if a date falls within an NBER recession."""
    return any(start <= as_of <= end for start, end in get_nber_recessions())


def segment_by_regime(
    dates: list[date],
    regimes: list[MarketRegimeHistorical],
    portfolio_returns: list[float],
    benchmark_returns: list[float],
) -> dict[MarketRegimeHistorical, RegimeSegment]:
    """Group returns by regime for segmented analysis."""
    buckets: dict[MarketRegimeHistorical, dict] = {}

    for _d, regime, pr, br in zip(dates, regimes, portfolio_returns, benchmark_returns):
        if regime not in buckets:
            buckets[regime] = {
                "portfolio_returns": [],
                "benchmark_returns": [],
            }
        buckets[regime]["portfolio_returns"].append(pr)
        buckets[regime]["benchmark_returns"].append(br)

    return {
        regime: RegimeSegment(
            regime=regime,
            num_months=len(data["portfolio_returns"]),
            portfolio_returns=data["portfolio_returns"],
            benchmark_returns=data["benchmark_returns"],
        )
        for regime, data in buckets.items()
    }
