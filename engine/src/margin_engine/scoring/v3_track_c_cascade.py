"""V3 Track C (Efficient Growth) Gate Cascade.

4 gates:
1. Growth Efficiency: Rule of 40 >= 30 OR (CAGR > 25% AND gross margin > 50%)
2. Unit Economics: Gross margin stable (3yr trend >= -2pp) AND positive operating leverage (>= 1.0)
3. Capital Efficiency: Incremental ROIC > WACC
4. Growth Durability: Deceleration >= -5pp AND TAM headroom >= 3x
"""

from __future__ import annotations

from pydantic import BaseModel

from margin_engine.config.v3_scoring_config import V3CompositeConfig
from margin_engine.models.scoring import CompositeTier
from margin_engine.scoring.v3_composite import compute_track_c_score
from margin_engine.scoring.v3_orchestrator import V3TrackResult
from margin_engine.scoring.v3_track_c_thresholds import assess_track_c_conviction

# Conviction levels that qualify for inclusion
_QUALIFYING_CONVICTIONS = frozenset(
    {CompositeTier.EXCEPTIONAL, CompositeTier.HIGH, CompositeTier.MEDIUM}
)


class TrackCInputs(BaseModel):
    """All inputs needed to run the Track C (Efficient Growth) gate cascade."""

    # Gate 1: Growth Efficiency
    revenue_growth_rate: float  # decimal (0.30 = 30%)
    fcf_margin: float  # decimal

    # Gate 2: Unit Economics
    gross_margin_current: float
    gross_margin_3yr_ago: float
    opex_growth_rate: float
    revenue_growth_rate_for_leverage: float

    # Gate 3: Capital Efficiency
    incremental_roic: float
    wacc: float

    # Gate 4: Growth Durability
    revenue_deceleration: float  # change in growth rate (negative = slowing)
    tam_headroom: float  # TAM / current_revenue
    composite_config: V3CompositeConfig | None = None


def run_track_c_cascade(inputs: TrackCInputs) -> V3TrackResult:
    """Run 4-gate Efficient Growth cascade."""
    gates_passed = 0
    total_gates = 4

    # --- Gate 1: Growth Efficiency ---
    rule_of_40 = (inputs.revenue_growth_rate * 100) + (inputs.fcf_margin * 100)
    alt_growth = inputs.revenue_growth_rate > 0.25 and inputs.gross_margin_current > 0.50
    gate1 = rule_of_40 >= 30.0 or alt_growth
    if gate1:
        gates_passed += 1

    # --- Gate 2: Unit Economics ---
    margin_trend = inputs.gross_margin_current - inputs.gross_margin_3yr_ago
    margin_stable = margin_trend >= -0.02
    if inputs.opex_growth_rate > 0:
        op_leverage = inputs.revenue_growth_rate_for_leverage / inputs.opex_growth_rate
    elif inputs.opex_growth_rate == 0 and inputs.revenue_growth_rate_for_leverage > 0:
        op_leverage = 10.0
    else:
        op_leverage = 0.0
    gate2 = margin_stable and op_leverage >= 1.0
    if gate2:
        gates_passed += 1

    # --- Gate 3: Capital Efficiency ---
    gate3 = inputs.incremental_roic > inputs.wacc
    if gate3:
        gates_passed += 1

    # --- Gate 4: Growth Durability ---
    gate4 = inputs.revenue_deceleration >= -0.05 and inputs.tam_headroom >= 3.0
    if gate4:
        gates_passed += 1

    # --- Score (multiplicative) ---
    # GE = min(rule_of_40 / 40, 2.0)
    ge = min(rule_of_40 / 40.0, 2.0) if rule_of_40 > 0 else 0.0

    # UE = (1 + margin_trend) * max(op_leverage, 0)
    ue = (1.0 + margin_trend) * max(op_leverage, 0.0)

    # CE = min(inc_roic / wacc, 3.0) if wacc > 0 else 0
    ce = min(inputs.incremental_roic / inputs.wacc, 3.0) if inputs.wacc > 0 else 0.0

    # GD = min(tam / 3, 1.5) * (1 - max(-decel, 0) / 20)
    gd = min(inputs.tam_headroom / 3.0, 1.5) * (1.0 - max(-inputs.revenue_deceleration, 0.0) / 20.0)

    score = compute_track_c_score(
        growth_efficiency=ge,
        unit_economics=ue,
        capital_efficiency=ce,
        growth_durability=gd,
        config=inputs.composite_config,
    )

    # --- Conviction ---
    conviction = assess_track_c_conviction(
        gates_passed=gates_passed,
        total_gates=total_gates,
        rule_of_40_score=rule_of_40,
        incremental_roic=inputs.incremental_roic,
        wacc=inputs.wacc,
        tam_headroom=inputs.tam_headroom,
        conditional=False,
    )

    qualifies = conviction in _QUALIFYING_CONVICTIONS

    return V3TrackResult(
        track="efficient_growth",
        qualifies=qualifies,
        conviction=conviction,
        score=score,
        conditional=False,
        gates_passed=gates_passed,
        total_gates=total_gates,
    )
