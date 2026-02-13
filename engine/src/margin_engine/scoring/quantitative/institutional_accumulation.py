"""Institutional Accumulation (Smart Money) factor.

Tracks 13F filings from curated top-fund lists to detect smart-money
accumulation patterns. New positions are weighted more heavily than
additions to existing positions, as initiating a brand-new position
represents a stronger conviction signal.

Note: 13F filings have a 45-day reporting lag. This function receives
pre-processed data; the lag is already accounted for upstream.

Scoring:
  - New position (is_new_position=True, shares_changed > 0): +3 points
  - Addition (shares_changed > 0, not new):                  +1 point
  - No change (shares_changed == 0):                          0 points
  - Reduction (shares_changed < 0):                          -1 point

Raw score = sum of all points for the most recent quarter.
Higher accumulation = better signal.
"""

from __future__ import annotations

from margin_engine.models.financial import InstitutionalHolding
from margin_engine.models.scoring import FactorScore

_NEW_POSITION_WEIGHT = 3
_ADDITION_WEIGHT = 1
_REDUCTION_WEIGHT = -1


def institutional_accumulation(holdings: list[InstitutionalHolding]) -> FactorScore:
    """Compute the institutional accumulation score from 13F holdings data.

    Filters to the most recent quarter, then scores each fund's activity.

    Returns a FactorScore with:
    - raw_value: net accumulation score (can be negative)
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer in Phase 6)
    - name: "institutional_accumulation"

    Edge cases:
    - Empty list: raw_value=0.0
    - All reductions: raw_value will be negative
    - Mixed quarters: only the most recent quarter's data is used
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

    # 2. Count fund categories and compute weighted score.
    new_positions = 0
    additions = 0
    reductions = 0
    no_change = 0
    score = 0

    for h in recent_holdings:
        if h.is_new_position and h.shares_changed > 0:
            new_positions += 1
            score += _NEW_POSITION_WEIGHT
        elif h.shares_changed > 0:
            additions += 1
            score += _ADDITION_WEIGHT
        elif h.shares_changed < 0:
            reductions += 1
            score += _REDUCTION_WEIGHT
        else:
            no_change += 1

    accumulating = new_positions + additions

    return FactorScore(
        name="institutional_accumulation",
        raw_value=float(score),
        percentile_rank=0.0,
        detail=(
            f"quarter={most_recent_quarter}; "
            f"accumulating={accumulating} (new={new_positions}, additions={additions}); "
            f"reducing={reductions}; no_change={no_change}; "
            f"score={score}"
        ),
    )
