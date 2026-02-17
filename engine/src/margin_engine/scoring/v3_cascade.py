"""V3 Gate Cascade Runners — sequential gate evaluation for each track.

Each track runs its gates in order. A gate either passes or fails.
After all gates, we compute the multiplicative score, assess conviction,
and return a V3TrackResult.
"""

from __future__ import annotations

from pydantic import BaseModel

from margin_engine.models.financial import AssetProfile, FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.market_regime import RegimeAdjustments
from margin_engine.scoring.quantitative.moat_durability import moat_durability_score
from margin_engine.scoring.quantitative.reverse_dcf import reverse_dcf_growth_gap
from margin_engine.scoring.v3_composite import compute_track_a_score
from margin_engine.scoring.v3_intermediates import (
    compute_capital_allocation_composite,
    compute_compounding_power,
)
from margin_engine.scoring.v3_orchestrator import V3TrackResult
from margin_engine.scoring.v3_thresholds import assess_track_a_conviction


class TrackAInputs(BaseModel):
    """All inputs needed to run the Track A (Compounder) gate cascade."""

    history: FinancialHistory
    period: FinancialPeriod
    profile: AssetProfile
    current_price: float
    current_fcf_per_share: float
    wacc: float
    terminal_growth: float = 0.03
    sustainable_growth_rate: float
    buyback_yield: float | None = None
    insider_ownership_pct: float | None = None
    sbc_pct: float | None = None
    recent_acquisition_count: int = 0
    regime_adjustments: RegimeAdjustments | None = None


# Conviction levels that qualify for inclusion
_QUALIFYING_CONVICTIONS = frozenset(
    {ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH, ConvictionLevel.WATCHLIST}
)


def run_track_a_cascade(inputs: TrackAInputs) -> V3TrackResult:
    """Run the 4-gate Compounder cascade and return a V3TrackResult.

    Gates:
        1. Moat Evidence: moat_durability_score >= 2
        2. Reinvestment Engine: compounding_power > 0.04
        3. Capital Allocation: capital_allocation_composite > 0.5
        4. Valuation (Reverse DCF): growth_gap > threshold (0.0 + regime adjustment)
    """
    gates_passed = 0
    total_gates = 4

    # --- Gate 1: Moat Evidence ---
    moat_result = moat_durability_score(inputs.history)
    moat_val = moat_result.raw_value
    if moat_val >= 2:
        gates_passed += 1

    # --- Gate 2: Reinvestment Engine ---
    compounding = compute_compounding_power(inputs.history)
    if compounding > 0.04:
        gates_passed += 1

    # --- Gate 3: Capital Allocation ---
    cap_alloc = compute_capital_allocation_composite(
        period=inputs.period,
        history=inputs.history,
        buyback_yield=inputs.buyback_yield,
        insider_ownership_pct=inputs.insider_ownership_pct,
        sbc_pct=inputs.sbc_pct,
        recent_acquisition_count=inputs.recent_acquisition_count,
    )
    if cap_alloc > 0.5:
        gates_passed += 1

    # --- Gate 4: Valuation (Reverse DCF) ---
    shares = inputs.profile.shares_outstanding or 1
    current_fcf = inputs.current_fcf_per_share * shares

    growth_gap_result = reverse_dcf_growth_gap(
        current_price=inputs.current_price,
        current_fcf=current_fcf,
        wacc=inputs.wacc,
        terminal_growth=inputs.terminal_growth,
        shares_outstanding=shares,
        sustainable_growth_rate=inputs.sustainable_growth_rate,
    )
    growth_gap = growth_gap_result.raw_value

    growth_gap_adjustment = 0.0
    if inputs.regime_adjustments is not None:
        growth_gap_adjustment = inputs.regime_adjustments.track_a_growth_gap_adjustment

    threshold = 0.0 + growth_gap_adjustment
    if growth_gap > threshold:
        gates_passed += 1

    # --- Score ---
    score = compute_track_a_score(
        moat_durability=moat_val,
        compounding_power=compounding,
        capital_allocation=cap_alloc,
        growth_gap=max(growth_gap, 0.0),
    )

    # --- Conviction ---
    conviction = assess_track_a_conviction(
        gates_passed=gates_passed,
        total_gates=total_gates,
        compounding_power=compounding,
        moat_durability=int(moat_val),
        growth_gap=growth_gap,
        growth_gap_adjustment=growth_gap_adjustment,
    )

    qualifies = conviction in _QUALIFYING_CONVICTIONS

    return V3TrackResult(
        track="compounder",
        qualifies=qualifies,
        conviction=conviction,
        score=score,
        gates_passed=gates_passed,
        total_gates=total_gates,
    )
