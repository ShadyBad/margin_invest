"""Non-linear transaction cost model.

Replaces flat bps assumption with size-dependent costs:
- Base commission (fixed bps)
- Spread model: wider for small-caps
- Square-root market impact: scales with trade_value / ADV
"""

from __future__ import annotations

import math

from pydantic import BaseModel


class CostModelConfig(BaseModel):
    """Configuration for the non-linear cost model."""

    base_commission_bps: float = 5.0
    impact_model: str = "square_root"  # Only "square_root" supported currently
    market_impact_coefficient: float = 0.1


class TransactionCost(BaseModel):
    """Breakdown of transaction costs for a single trade."""

    commission_bps: float
    spread_bps: float
    market_impact_bps: float
    total_bps: float


def compute_spread_bps(market_cap: float) -> float:
    """Compute bid-ask spread estimate based on market capitalization.

    Spread model: spread_bps = 3.0 + 50.0 / sqrt(market_cap / 1e9)
    Wider for small-caps, tighter for mega-caps.

    Args:
        market_cap: Company market capitalization in dollars.

    Returns:
        Estimated spread in basis points.
    """
    # Floor market_cap at 1e6 to avoid division issues
    floored_cap = max(market_cap, 1e6)
    return 3.0 + 50.0 / math.sqrt(floored_cap / 1e9)


def compute_market_impact_bps(
    trade_value: float,
    adv: float,
    coefficient: float = 0.1,
) -> float:
    """Compute square-root market impact cost.

    Impact model: impact_bps = coefficient * sqrt(trade_value / adv) * 10000

    Args:
        trade_value: Dollar value of the trade.
        adv: Average daily volume in dollars.
        coefficient: Market impact coefficient (default 0.1).

    Returns:
        Estimated market impact in basis points.
    """
    if adv <= 0 or trade_value <= 0:
        return 0.0
    return coefficient * math.sqrt(trade_value / adv) * 10_000


def compute_transaction_cost(
    trade_value: float,
    adv: float,
    market_cap: float,
    config: CostModelConfig | None = None,
) -> TransactionCost:
    """Compute total non-linear transaction cost for a single trade.

    Combines commission + spread + market impact into a TransactionCost breakdown.

    Args:
        trade_value: Dollar value of the trade.
        adv: Average daily volume in dollars.
        market_cap: Company market capitalization in dollars.
        config: Cost model configuration. Uses defaults if None.

    Returns:
        TransactionCost with commission, spread, impact, and total in bps.
    """
    if config is None:
        config = CostModelConfig()

    commission_bps = config.base_commission_bps
    spread_bps = compute_spread_bps(market_cap)
    market_impact_bps = compute_market_impact_bps(
        trade_value, adv, config.market_impact_coefficient
    )
    total_bps = commission_bps + spread_bps + market_impact_bps

    return TransactionCost(
        commission_bps=commission_bps,
        spread_bps=spread_bps,
        market_impact_bps=market_impact_bps,
        total_bps=total_bps,
    )
