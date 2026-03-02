"""Institutional Accumulation (Smart Money) factor.

Tracks 13F filings from curated top-fund lists to detect smart-money
accumulation patterns. New positions are weighted more heavily than
additions to existing positions, as initiating a brand-new position
represents a stronger conviction signal.

Note: 13F filings have a 45-day reporting lag. This function receives
pre-processed data; the lag is already accounted for upstream.

Base scoring:
  - New position (is_new_position=True, shares_changed > 0): +3 points
  - Addition (shares_changed > 0, not new):                  +1 point
  - No change (shares_changed == 0):                          0 points
  - Reduction (shares_changed < 0):                          -1 point

Position-size weighting:
  Each base score is multiplied by a size weight derived from
  abs(shares_changed) / median(abs(shares_changed)) across all
  active holdings in the quarter. Capped at 5x to prevent outlier
  dominance. When all holdings have the same size, weights are 1.0
  and the result is identical to unweighted scoring.

Raw score = sum of size-weighted points for the most recent quarter.
Higher accumulation = better signal.
"""

from __future__ import annotations

import statistics

from margin_engine.models.financial import InstitutionalHolding
from margin_engine.models.scoring import FactorScore

_NEW_POSITION_WEIGHT = 3
_ADDITION_WEIGHT = 1
_REDUCTION_WEIGHT = -1
_MAX_SIZE_WEIGHT = 5.0


def institutional_accumulation(holdings: list[InstitutionalHolding]) -> FactorScore:
    """Compute the institutional accumulation score from 13F holdings data.

    Filters to the most recent quarter, then scores each fund's activity
    with position-size weighting. Larger positions amplify the signal.

    Returns a FactorScore with:
    - raw_value: net size-weighted accumulation score (can be negative)
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer in Phase 6)
    - name: "institutional_accumulation"

    Edge cases:
    - Empty list: raw_value=0.0
    - All reductions: raw_value will be negative
    - Mixed quarters: only the most recent quarter's data is used
    - Single holding: size_weight=1.0 (median equals itself)
    """
    if not holdings:
        return FactorScore(
            name="institutional_accumulation",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="no holdings data provided",
        )

    # 1. Filter to the most recent quarter (YYYY-QN format sorts lexicographically).
    most_recent_quarter = max(h.quarter for h in holdings)
    recent_holdings = [h for h in holdings if h.quarter == most_recent_quarter]

    # 2. Compute median position size for normalization.
    position_sizes = [abs(h.shares_changed) for h in recent_holdings if h.shares_changed != 0]
    median_size = statistics.median(position_sizes) if position_sizes else 1
    if median_size == 0:
        median_size = 1

    # 3. Count fund categories and compute size-weighted score.
    new_positions = 0
    additions = 0
    reductions = 0
    no_change = 0
    total_score = 0.0

    for h in recent_holdings:
        shares_changed = h.shares_changed
        # Size weight: ratio of this position to median, capped at 5x
        size_weight = (
            min(abs(shares_changed) / median_size, _MAX_SIZE_WEIGHT) if shares_changed != 0 else 0.0
        )

        if h.is_new_position and shares_changed > 0:
            new_positions += 1
            total_score += _NEW_POSITION_WEIGHT * size_weight
        elif shares_changed > 0:
            additions += 1
            total_score += _ADDITION_WEIGHT * size_weight
        elif shares_changed < 0:
            reductions += 1
            total_score += _REDUCTION_WEIGHT * size_weight
        else:
            no_change += 1

    accumulating = new_positions + additions

    return FactorScore(
        name="institutional_accumulation",
        raw_value=total_score,
        percentile_rank=0.0,
        detail=(
            f"quarter={most_recent_quarter}; "
            f"accumulating={accumulating} (new={new_positions}, additions={additions}); "
            f"reducing={reductions}; no_change={no_change}; "
            f"size_weighted_score={total_score:.4f}; median_size={median_size}"
        ),
    )
