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


# ---------------------------------------------------------------------------
# Cost assumptions & academic benchmarks
# ---------------------------------------------------------------------------

_DEFAULTS = CostModelConfig()

COST_ASSUMPTIONS: dict[str, object] = {
    "base_commission_bps": _DEFAULTS.base_commission_bps,
    "market_impact_coefficient": _DEFAULTS.market_impact_coefficient,
    "spread_formula": "spread_bps = 3.0 + 50.0 / sqrt(market_cap / 1e9)",
    "spread_description": (
        "Bid-ask spread widens for smaller companies. "
        "Mega-caps converge toward ~3 bps; micro-caps can exceed 100 bps."
    ),
    "impact_formula": "impact_bps = coefficient * sqrt(trade_value / adv) * 10000",
    "impact_description": (
        "Square-root market impact model. Cost grows sub-linearly with trade size "
        "relative to average daily volume, consistent with Kyle (1985)."
    ),
    "not_modeled": [
        "short-selling costs",
        "taxes",
        "management fees",
        "opportunity cost",
        "time-of-day effects",
    ],
}

ACADEMIC_BENCHMARKS: list[dict[str, object]] = [
    {
        "source": "Frazzini, Israel & Moskowitz (2015)",
        "paper": "Trading Costs of Asset Pricing Anomalies",
        "asset_class": "US equities",
        "market_cap_range": "large_cap",
        "cost_range_bps": (10, 20),
    },
    {
        "source": "Frazzini, Israel & Moskowitz (2015)",
        "paper": "Trading Costs of Asset Pricing Anomalies",
        "asset_class": "US equities",
        "market_cap_range": "small_cap",
        "cost_range_bps": (30, 60),
    },
    {
        "source": "Novy-Marx & Velikov (2016)",
        "paper": "A Taxonomy of Anomalies and Their Trading Costs",
        "asset_class": "US equities",
        "market_cap_range": "all_cap",
        "cost_range_bps": (10, 50),
    },
]


def validate_cost_assumptions(
    model_cost_bps: float,
    market_cap_billions: float,
) -> dict[str, object]:
    """Validate model cost against academic benchmark for the appropriate cap tier.

    Tier selection:
        - >= 10B  -> large_cap  (Frazzini et al.)
        - >= 2B   -> all_cap    (Novy-Marx & Velikov)
        - <  2B   -> small_cap  (Frazzini et al.)

    Args:
        model_cost_bps: The modeled transaction cost in basis points.
        market_cap_billions: Company market capitalisation in billions of dollars.

    Returns:
        Dict with model_cost_bps, benchmark_range_bps, status, and source.
    """
    if market_cap_billions >= 10.0:
        tier = "large_cap"
    elif market_cap_billions >= 2.0:
        tier = "all_cap"
    else:
        tier = "small_cap"

    benchmark = next(
        (b for b in ACADEMIC_BENCHMARKS if b["market_cap_range"] == tier),
        ACADEMIC_BENCHMARKS[0],
    )
    low, high = benchmark["cost_range_bps"]

    if model_cost_bps < low:
        status = "below_benchmark"
    elif model_cost_bps > high:
        status = "above_benchmark"
    else:
        status = "within_range"

    return {
        "model_cost_bps": model_cost_bps,
        "benchmark_range_bps": (low, high),
        "status": status,
        "source": benchmark["source"],
    }
