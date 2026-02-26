"""Failure audit for backtesting.

Identifies the worst-performing rebalance periods and explains what
the model held, what drove the underperformance, and the macro context.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from margin_engine.backtesting.models import HoldingRecord, MonthlySnapshot
from margin_engine.backtesting.regime_classifier import MarketRegimeHistorical


class FailurePeriod(BaseModel):
    """A single worst-performing rebalance period."""

    rebalance_date: date
    portfolio_return: float
    benchmark_return: float
    relative_underperformance: float
    holdings: list[HoldingRecord]
    regime: MarketRegimeHistorical
    regime_context: str


def _regime_context(regime: MarketRegimeHistorical, as_of: date) -> str:
    """Generate human-readable regime context for a failure period."""
    month_name = as_of.strftime("%b %Y")

    if regime == MarketRegimeHistorical.CRISIS:
        if 2007 <= as_of.year <= 2009:
            return f"{month_name}: Global Financial Crisis"
        if as_of.year == 2020 and as_of.month <= 4:
            return f"{month_name}: COVID-19 pandemic"
        return f"{month_name}: Market crisis"

    if regime == MarketRegimeHistorical.BEAR:
        return f"{month_name}: Bear market"

    if regime == MarketRegimeHistorical.SIDEWAYS:
        return f"{month_name}: Sideways market"

    return f"{month_name}: Bull market — model underperformed during rally"


def compute_failure_audit(
    snapshots: list[MonthlySnapshot],
    regimes: list[MarketRegimeHistorical],
    n_worst: int = 10,
) -> list[FailurePeriod]:
    """Identify the N worst rebalance periods by relative underperformance."""
    if not snapshots:
        return []

    periods: list[FailurePeriod] = []
    for snapshot, regime in zip(snapshots, regimes):
        relative = snapshot.benchmark_return - snapshot.portfolio_return
        if relative > 0:
            periods.append(
                FailurePeriod(
                    rebalance_date=snapshot.date,
                    portfolio_return=snapshot.portfolio_return,
                    benchmark_return=snapshot.benchmark_return,
                    relative_underperformance=relative,
                    holdings=snapshot.holdings,
                    regime=regime,
                    regime_context=_regime_context(regime, snapshot.date),
                )
            )

    periods.sort(key=lambda p: -p.relative_underperformance)
    return periods[:n_worst]
