"""V3 Gate Cascade Runners — sequential gate evaluation for each track.

Each track runs its gates in order. A gate either passes or fails.
After all gates, we compute the multiplicative score, assess conviction,
and return a V3TrackResult.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from margin_engine.config.v3_scoring_config import V3CompositeConfig
from margin_engine.models.financial import AssetProfile, FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import CompositeTier
from margin_engine.scoring.market_regime import RegimeAdjustments
from margin_engine.scoring.quantitative.asset_floor import asset_floor_valuation
from margin_engine.scoring.quantitative.asymmetry import asymmetry_ratio as compute_asymmetry
from margin_engine.scoring.quantitative.ensemble_valuation import compute_ensemble_valuation
from margin_engine.scoring.quantitative.moat_durability import moat_durability_score
from margin_engine.scoring.quantitative.reverse_dcf import (
    reverse_dcf_combined_gap,
    reverse_dcf_growth_gap,
)
from margin_engine.scoring.v3_composite import compute_track_a_score, compute_track_b_score
from margin_engine.scoring.v3_intermediates import (
    compute_capital_allocation_composite,
    compute_catalyst_strength,
    compute_compounding_power,
    compute_downside_protection,
    compute_quality_floor_factor,
    compute_valuation_convergence_factor,
)
from margin_engine.scoring.v3_orchestrator import V3TrackResult
from margin_engine.scoring.v3_thresholds import assess_track_a_conviction, assess_track_b_conviction


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
    current_revenue: float | None = None
    current_fcf_margin: float | None = None
    sustainable_fcf_margin: float | None = None
    revenue_growth_for_margin_solve: float | None = None
    buyback_yield: float | None = None
    insider_ownership_pct: float | None = None
    sbc_pct: float | None = None
    recent_acquisition_count: int = 0
    regime_adjustments: RegimeAdjustments | None = None
    composite_config: V3CompositeConfig | None = None


# Conviction levels that qualify for inclusion
_QUALIFYING_CONVICTIONS = frozenset(
    {CompositeTier.EXCEPTIONAL, CompositeTier.HIGH, CompositeTier.MEDIUM}
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

    # If margin inputs available, use combined gap; otherwise use growth-only gap
    if all(
        v is not None
        for v in [
            inputs.current_revenue,
            inputs.current_fcf_margin,
            inputs.sustainable_fcf_margin,
            inputs.revenue_growth_for_margin_solve,
        ]
    ):
        combined = reverse_dcf_combined_gap(
            current_price=inputs.current_price,
            current_fcf=current_fcf,
            current_revenue=inputs.current_revenue,
            current_fcf_margin=inputs.current_fcf_margin,
            sustainable_fcf_margin=inputs.sustainable_fcf_margin,
            wacc=inputs.wacc,
            terminal_growth=inputs.terminal_growth,
            shares_outstanding=shares,
            sustainable_growth_rate=inputs.sustainable_growth_rate,
            revenue_growth_for_margin_solve=inputs.revenue_growth_for_margin_solve,
        )
        growth_gap = combined.raw_value
    else:
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
        config=inputs.composite_config,
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


# ---------------------------------------------------------------------------
# Track B — Mispricing
# ---------------------------------------------------------------------------


class TrackBInputs(BaseModel):
    """All inputs needed to run the Track B (Mispricing) gate cascade."""

    history: FinancialHistory
    period: FinancialPeriod
    profile: AssetProfile
    current_price: float
    dcf_iv: float
    owner_earnings_iv: float
    asset_floor_iv: float
    peer_comparison_iv: float
    sue_percentile: float
    accumulation_percentile: float = 0.0
    wacc: float
    regime_adjustments: RegimeAdjustments | None = None
    composite_config: V3CompositeConfig | None = None


def _current_roic(period: FinancialPeriod) -> float:
    """Compute current-period ROIC = NOPAT / Invested Capital."""
    ci = period.current_income
    cb = period.current_balance
    cash = float(cb.cash_and_equivalents or Decimal("0"))
    ic = float(cb.total_equity) + float(cb.total_debt) - cash
    if ic <= 0:
        return 0.0
    return float(ci.ebit) * (1.0 - ci.effective_tax_rate) / ic


def _is_roic_improving(history: FinancialHistory) -> bool:
    """Return True if ROIC is higher in the latest period than the earliest."""
    if len(history.periods) < 2:
        return False
    roics: list[float] = []
    for p in history.periods:
        ci, cb = p.current_income, p.current_balance
        cash = float(cb.cash_and_equivalents or Decimal("0"))
        ic = float(cb.total_equity) + float(cb.total_debt) - cash
        if ic > 0:
            roics.append(float(ci.ebit) * (1.0 - ci.effective_tax_rate) / ic)
    return len(roics) >= 2 and roics[-1] > roics[0]


def run_track_b_cascade(inputs: TrackBInputs) -> V3TrackResult:
    """Run the 4-gate Mispricing cascade and return a V3TrackResult.

    Gates:
        1. Ensemble Valuation: converged AND price < iv_discount * ensemble_iv
           iv_discount is tiered by quality floor:
             0.75 (25% margin) if quality_floor >= 1.0 (ROIC >= 8%)
             0.65 (35% margin) if quality_floor > 0 (improving)
             0.60 (40% margin) if quality_floor == 0 (low quality)
        2. Downside Protection: max loss < 50%
        3. Catalyst: catalyst_strength > 40 (or regime override)
        4. Quality Floor: quality_floor_factor > 0
    """
    gates_passed = 0
    total_gates = 4

    # Compute quality floor early (needed for tiered Gate 1 threshold)
    roic = _current_roic(inputs.period)
    improving = _is_roic_improving(inputs.history)
    quality_floor = compute_quality_floor_factor(roic, improving)

    # --- Gate 1: Ensemble Valuation (tiered IV discount by quality) ---
    ensemble = compute_ensemble_valuation(
        dcf_iv=inputs.dcf_iv,
        owner_earnings_iv=inputs.owner_earnings_iv,
        asset_floor_iv=inputs.asset_floor_iv,
        peer_comparison_iv=inputs.peer_comparison_iv,
        sector=inputs.profile.sector,
    )
    if quality_floor >= 1.0:
        iv_discount = 0.75  # 25% margin for quality businesses (ROIC >= 8%)
    elif quality_floor > 0:
        iv_discount = 0.65  # 35% margin for improving businesses
    else:
        iv_discount = 0.60  # 40% margin for low-quality (original)

    if ensemble.converged and inputs.current_price < iv_discount * ensemble.ensemble_iv:
        gates_passed += 1

    # --- Gate 2: Downside Protection ---
    cb = inputs.period.current_balance
    net_cash = float(cb.cash_and_equivalents or Decimal("0")) - float(cb.total_debt)
    tangible_book = float(cb.total_equity)
    shares = inputs.profile.shares_outstanding or 1

    asset_floor_ps = asset_floor_valuation(
        net_cash=Decimal(str(net_cash)),
        tangible_book=Decimal(str(tangible_book)),
        sector=inputs.profile.sector,
        shares_outstanding=shares,
    )
    _max_loss, downside_passed = compute_downside_protection(
        current_price=inputs.current_price,
        asset_floor_per_share=asset_floor_ps,
    )
    if downside_passed:
        gates_passed += 1

    # --- Gate 3: Catalyst ---
    catalyst = compute_catalyst_strength(
        sue_percentile=inputs.sue_percentile,
        accumulation_percentile=inputs.accumulation_percentile,
    )
    catalyst_threshold = 40.0
    if inputs.regime_adjustments and inputs.regime_adjustments.track_b_catalyst_percentile_override:
        catalyst_threshold = inputs.regime_adjustments.track_b_catalyst_percentile_override
    if catalyst > catalyst_threshold:
        gates_passed += 1

    # --- Gate 4: Quality Floor (reuses quality_floor computed before Gate 1) ---
    if quality_floor > 0:
        gates_passed += 1

    # --- Derived values ---
    net_cash_ps = net_cash / shares if shares > 0 else 0.0
    tangible_book_ps = tangible_book / shares if shares > 0 else 0.0
    ensemble_iv = ensemble.ensemble_iv if ensemble.converged else 0.0

    asym = compute_asymmetry(
        intrinsic_value=ensemble_iv,
        current_price=inputs.current_price,
        net_cash_per_share=net_cash_ps,
        tangible_book_per_share=tangible_book_ps,
    )

    convergence = compute_valuation_convergence_factor(ensemble.converging_count)

    # --- Score ---
    score = compute_track_b_score(
        asymmetry_ratio=asym.raw_value,
        catalyst_strength=catalyst / 100.0,
        quality_floor_factor=quality_floor,
        valuation_convergence=convergence,
        config=inputs.composite_config,
    )

    # --- Conviction ---
    asymmetry_adjustment = 0.0
    catalyst_pctl_override: float | None = None
    if inputs.regime_adjustments is not None:
        asymmetry_adjustment = inputs.regime_adjustments.track_b_asymmetry_adjustment
        catalyst_pctl_override = inputs.regime_adjustments.track_b_catalyst_percentile_override

    conviction = assess_track_b_conviction(
        gates_passed=gates_passed,
        total_gates=total_gates,
        asymmetry_ratio=asym.raw_value,
        catalyst_percentile=catalyst,
        converging_methods=ensemble.converging_count,
        asymmetry_adjustment=asymmetry_adjustment,
        catalyst_percentile_override=catalyst_pctl_override,
    )

    qualifies = conviction in _QUALIFYING_CONVICTIONS

    return V3TrackResult(
        track="mispricing",
        qualifies=qualifies,
        conviction=conviction,
        score=score,
        gates_passed=gates_passed,
        total_gates=total_gates,
    )
