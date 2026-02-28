"""Capacity analysis for backtesting.

Estimates how strategy performance degrades as AUM increases,
due to growing market impact costs.
"""

from __future__ import annotations

import math

from margin_engine.backtesting.cost_model import compute_market_impact_bps
from margin_engine.backtesting.metrics import PerformanceCalculator
from margin_engine.backtesting.models import MonthlySnapshot

DEFAULT_AUM_LEVELS = [1e6, 10e6, 50e6, 100e6, 250e6, 500e6, 1e9]
_ADV_PROXY_FRACTION = 0.005  # 0.5% daily turnover
_DEFAULT_MARKET_CAP = 10e9
_BREAKEVEN_SHARPE = 0.5


def run_capacity_analysis(
    snapshots: list[MonthlySnapshot],
    aum_levels: list[float] | None = None,
    market_impact_coefficient: float = 0.1,
    risk_free_rate: float = 0.04,
) -> dict[str, object]:
    """Estimate performance at various AUM levels.

    For each AUM level, scales trade sizes proportionally and computes
    the additional market impact cost, then re-derives net returns and metrics.

    Args:
        snapshots: Chronologically ordered list of monthly snapshots.
        aum_levels: AUM levels to evaluate. Defaults to DEFAULT_AUM_LEVELS.
        market_impact_coefficient: Coefficient for square-root impact model.
        risk_free_rate: Annual risk-free rate for Sharpe computation.

    Returns:
        Dict with "rows" (list of per-AUM dicts) and "breakeven_aum" (float or None).
    """
    if aum_levels is None:
        aum_levels = list(DEFAULT_AUM_LEVELS)

    # ADV proxy: 0.5% of default market cap = $50M
    adv = _DEFAULT_MARKET_CAP * _ADV_PROXY_FRACTION

    # Pre-extract gross returns from snapshots
    gross_returns = [s.gross_return for s in snapshots]

    risk_free_monthly = risk_free_rate / 12.0

    rows: list[dict[str, float]] = []
    breakeven_aum: float | None = None

    for aum in aum_levels:
        if not snapshots:
            rows.append({"aum": aum, "cagr": 0.0, "sharpe": 0.0, "avg_impact_bps": 0.0})
            continue

        pv = aum
        net_returns: list[float] = []
        total_impact_bps = 0.0

        for i, snapshot in enumerate(snapshots):
            turnover = snapshot.turnover
            num_holdings = max(len(snapshot.holdings), 1)

            # Gross portfolio value before costs
            gross_pv = pv * (1.0 + gross_returns[i])

            # Trade value per position
            trade_value = pv * turnover / num_holdings

            # Market impact in bps
            impact_bps = compute_market_impact_bps(trade_value, adv, market_impact_coefficient)
            total_impact_bps += impact_bps

            # Scale base costs proportionally to AUM
            if snapshot.portfolio_value > 0:
                base_cost = snapshot.transaction_costs * (pv / snapshot.portfolio_value)
            else:
                base_cost = 0.0

            # Impact cost in dollars
            impact_cost = pv * turnover * impact_bps / 10_000

            # Total cost
            total_cost = base_cost + impact_cost

            # Net portfolio value
            net_pv = gross_pv - total_cost

            # Net return for this month
            if pv > 0:
                net_ret = (net_pv - pv) / pv
            else:
                net_ret = 0.0

            net_returns.append(net_ret)
            pv = net_pv

        # Compute CAGR from adjusted returns
        num_months = len(net_returns)
        years = num_months / 12.0
        total_return_ratio = math.prod(1.0 + r for r in net_returns)
        cagr = PerformanceCalculator._cagr(total_return_ratio, years)

        # Compute Sharpe from adjusted returns
        sharpe = PerformanceCalculator._sharpe(net_returns, risk_free_monthly)

        # Average impact bps
        avg_impact_bps = total_impact_bps / num_months if num_months > 0 else 0.0

        rows.append(
            {
                "aum": aum,
                "cagr": cagr,
                "sharpe": sharpe,
                "avg_impact_bps": avg_impact_bps,
            }
        )

        # Track breakeven: first AUM where Sharpe drops below threshold
        if breakeven_aum is None and sharpe < _BREAKEVEN_SHARPE:
            breakeven_aum = aum

    return {
        "rows": rows,
        "breakeven_aum": breakeven_aum,
    }
