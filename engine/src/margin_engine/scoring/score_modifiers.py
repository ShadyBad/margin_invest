"""Post-composite score modifiers.

Each modifier returns a float multiplier. Combined product clamped to [0.75, 1.25].
Applied after v3/v4 cascade -- affects ranking and position sizing, not conviction tier.
"""
from __future__ import annotations

import math

_COMBINED_FLOOR = 0.75
_COMBINED_CEILING = 1.25

_LIQ_FLOOR = 0.85
_LIQ_CEILING = 1.0


def liquidity_modifier(
    market_cap: float,
    avg_daily_dollar_volume: float,
    divergence_ratio: float | None,
) -> float:
    """Returns multiplier 0.85-1.00. Never boosts, only penalizes.

    Three components (equal weight):
    1. Market cap tier: log-scaled, $100B+=1.0, $100M=0.0
    2. Turnover adequacy: ADV/market_cap, >=0.5%=1.0, <=0.01%=0.0
    3. Liquidity stability: from divergence ratio, <=1.5=1.0, >=3.0=0.5, None=0.7
    """
    # Component 1: Market cap tier (log-scaled)
    if market_cap <= 0:
        cap_score = 0.0
    else:
        log_cap = math.log10(max(market_cap, 1))
        cap_score = max(0.0, min(1.0, (log_cap - 8.0) / 3.0))

    # Component 2: Turnover adequacy
    if market_cap <= 0:
        turnover_score = 0.0
    else:
        turnover = avg_daily_dollar_volume / market_cap
        if turnover >= 0.005:
            turnover_score = 1.0
        elif turnover <= 0.0001:
            turnover_score = 0.0
        else:
            log_t = math.log10(turnover)
            turnover_score = max(0.0, min(1.0, (log_t + 4.0) / 1.7))

    # Component 3: Liquidity stability
    if divergence_ratio is None:
        stability_score = 0.7
    elif divergence_ratio <= 1.5:
        stability_score = 1.0
    elif divergence_ratio >= 3.0:
        stability_score = 0.5
    else:
        stability_score = 1.0 - 0.5 * (divergence_ratio - 1.5) / 1.5

    avg = (cap_score + turnover_score + stability_score) / 3.0
    return _LIQ_FLOOR + (_LIQ_CEILING - _LIQ_FLOOR) * avg


def apply_all_modifiers(
    composite_score: float,
    anti_consensus: float,
    liquidity: float,
    insider: float,
) -> tuple[float, dict[str, float]]:
    """Apply all post-composite modifiers with combined bounds.

    Returns (modified_score, breakdown) where breakdown contains
    each modifier value and the combined product.
    """
    combined = anti_consensus * liquidity * insider
    combined = max(_COMBINED_FLOOR, min(_COMBINED_CEILING, combined))
    return composite_score * combined, {
        "anti_consensus": anti_consensus,
        "liquidity": liquidity,
        "insider": insider,
        "combined": combined,
    }
