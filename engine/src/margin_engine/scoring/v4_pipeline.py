"""V4 Universe Pipeline — extends V3 with Track C, style classification, and ML override.

Handles peer comparison IV computation, owner earnings IV, asset floor IV,
timing signals, Track C cascade for GROWTH-style tickers, ML ensemble override,
and portfolio concentration cap enforcement.
"""

from __future__ import annotations

from pydantic import BaseModel

from margin_engine.config.industry_growth_rates import get_sector_growth_rate
from margin_engine.ml.ensemble_override import apply_ml_override
from margin_engine.models.scoring import CompositeTier, FilterResult, InvestmentStyle
from margin_engine.scoring.market_regime import detect_regime, regime_adjustments
from margin_engine.scoring.pipeline_helpers import (
    compute_asset_floor_per_share,
    compute_owner_earnings_per_share,
    compute_peer_comparison_iv,
    compute_sector_median_ev_ebit,
    conditional_multiplier_for_ticker,
)
from margin_engine.scoring.quantitative.inflection_detection import inflection_score
from margin_engine.scoring.quantitative.tam_expansion import tam_expansion_velocity
from margin_engine.scoring.quantitative.wacc_company import compute_company_wacc
from margin_engine.scoring.quantitative.wacc_sector import get_sector_wacc
from margin_engine.scoring.score_modifiers import (
    anti_consensus_modifier,
    apply_all_modifiers,
    inflection_modifier,
    insider_signal_modifier,
    liquidity_modifier,
    tam_modifier,
)
from margin_engine.scoring.ticker_data import TickerDataBase
from margin_engine.scoring.timing_overlay import compute_v3_timing_signal
from margin_engine.scoring.v3_cascade import (
    TrackAInputs,
    TrackBInputs,
    run_track_a_cascade,
    run_track_b_cascade,
)
from margin_engine.scoring.v3_intermediates import compute_owner_earnings_iv
from margin_engine.scoring.v3_orchestrator import V3TrackResult
from margin_engine.scoring.v3_position_sizing import compute_v3_position_size
from margin_engine.scoring.v3_track_c_cascade import TrackCInputs, run_track_c_cascade
from margin_engine.scoring.v4_orchestrator import orchestrate_v4

# V4 uses a larger portfolio cap than V3 (50 vs 10).
V4_MAX_POSITIONS = 50


class TickerV4Data(TickerDataBase):
    """All data needed to score a single ticker through the v4 pipeline."""

    accumulation_percentile: float = 0.0

    # V4 additions
    style: InvestmentStyle = InvestmentStyle.BLEND

    # Track C (Efficient Growth) input fields
    revenue_growth_rate: float = 0.0
    fcf_margin: float = 0.0
    gross_margin_current: float = 0.0
    gross_margin_3yr_ago: float = 0.0
    opex_growth_rate: float = 0.0
    revenue_growth_rate_for_leverage: float = 0.0
    incremental_roic: float = 0.0
    revenue_deceleration: float = 0.0
    tam_headroom: float = 0.0


class V4ResultWithML(BaseModel):
    """Final v4 scoring result for a single ticker, with ML override info."""

    ticker: str
    opportunity_type: str
    conviction: CompositeTier  # final, after ML override
    rules_conviction: CompositeTier  # before ML override
    track_a: V3TrackResult
    track_b: V3TrackResult
    track_c: V3TrackResult
    style: InvestmentStyle
    timing_signal: str
    max_position_pct: float
    ml_alpha: float | None = None
    ml_confidence: float | None = None
    ml_override: str = "none"
    composite_score: float = 0.0
    modified_score: float | None = None
    modifier_breakdown: dict[str, float] | None = None


_CONVICTION_ORDER = {
    CompositeTier.EXCEPTIONAL: 0,
    CompositeTier.HIGH: 1,
    CompositeTier.MEDIUM: 2,
    CompositeTier.NONE: 3,
}


def _build_track_c_inputs(td: TickerV4Data, wacc: float) -> TrackCInputs:
    """Build Track C inputs from ticker data."""
    return TrackCInputs(
        revenue_growth_rate=td.revenue_growth_rate,
        fcf_margin=td.fcf_margin,
        gross_margin_current=td.gross_margin_current,
        gross_margin_3yr_ago=td.gross_margin_3yr_ago,
        opex_growth_rate=td.opex_growth_rate,
        revenue_growth_rate_for_leverage=td.revenue_growth_rate_for_leverage,
        incremental_roic=td.incremental_roic,
        wacc=wacc,
        revenue_deceleration=td.revenue_deceleration,
        tam_headroom=td.tam_headroom,
    )


def _none_track_c() -> V3TrackResult:
    """Create a NONE placeholder Track C result for non-GROWTH tickers."""
    return V3TrackResult(
        track="efficient_growth",
        qualifies=False,
        conviction=CompositeTier.NONE,
        score=0.0,
        gates_passed=0,
        total_gates=4,
    )


def score_universe_v4(
    tickers_data: list[TickerV4Data],
    shiller_cape: float,
    ml_predictions: dict | None = None,
    optimize: bool = False,
    filter_results: dict[str, list[FilterResult]] | None = None,
) -> list[V4ResultWithML]:
    """Score a universe of tickers through the full v4 pipeline.

    Steps:
        1. Detect regime and compute adjustments
        2. Compute sector median EV/EBIT for peer comparison IVs
        3. Per ticker:
           a. Compute WACC, owner earnings IV, asset floor IV, peer comparison IV
           b. Run Track A cascade
           c. Run Track B cascade
           d. Run Track C cascade (GROWTH only) or NONE placeholder
           e. Compute timing signal
           f. Orchestrate v4
           g. Apply ML ensemble override
           h. Recompute position size if conviction changed
        4. Sort by conviction then max_position_pct desc
        5. Enforce V4_MAX_POSITIONS cap
    """
    if not tickers_data:
        return []

    # Step 1: Regime detection
    regime = detect_regime(shiller_cape)
    adj = regime_adjustments(regime)

    # Step 2: Sector median EV/EBIT
    sector_medians = compute_sector_median_ev_ebit(tickers_data)

    # Collect universe ML alphas for percentile ranking (needed by apply_ml_override)
    universe_ml_alphas: list[float] = []
    if ml_predictions is not None:
        universe_ml_alphas = list(ml_predictions.get("alphas", {}).values())

    results: list[V4ResultWithML] = []

    for td in tickers_data:
        wacc = compute_company_wacc(
            period=td.latest_period,
            profile=td.profile,
            beta=td.beta,
            sector_fallback=get_sector_wacc(td.profile.sector),
        )

        # Step 3a: Owner earnings IV
        oe_per_share = compute_owner_earnings_per_share(td)
        owner_earnings_iv = compute_owner_earnings_iv(oe_per_share, wacc)

        # Asset floor IV
        asset_floor_iv = compute_asset_floor_per_share(td)

        # Peer comparison IV
        peer_comparison_iv = compute_peer_comparison_iv(td, sector_medians)

        # Step 3b: Track A cascade
        track_a_inputs = TrackAInputs(
            history=td.history,
            period=td.latest_period,
            profile=td.profile,
            current_price=td.current_price,
            current_fcf_per_share=td.current_fcf_per_share,
            wacc=wacc,
            sustainable_growth_rate=td.sustainable_growth_rate,
            buyback_yield=td.buyback_yield,
            insider_ownership_pct=td.insider_ownership_pct,
            sbc_pct=td.sbc_pct,
            recent_acquisition_count=td.recent_acquisition_count,
            regime_adjustments=adj,
        )
        track_a = run_track_a_cascade(track_a_inputs)

        # Step 3c: Track B cascade
        track_b_inputs = TrackBInputs(
            history=td.history,
            period=td.latest_period,
            profile=td.profile,
            current_price=td.current_price,
            dcf_iv=td.dcf_iv,
            owner_earnings_iv=owner_earnings_iv,
            asset_floor_iv=asset_floor_iv,
            peer_comparison_iv=peer_comparison_iv,
            sue_percentile=td.sue_percentile,
            accumulation_percentile=td.accumulation_percentile,
            wacc=wacc,
            regime_adjustments=adj,
        )
        track_b = run_track_b_cascade(track_b_inputs)

        # Step 3d: Track C cascade (GROWTH only)
        if td.style == InvestmentStyle.GROWTH:
            track_c_inputs = _build_track_c_inputs(td, wacc)
            track_c = run_track_c_cascade(track_c_inputs)
        else:
            track_c = _none_track_c()

        # Step 3d-ii: Apply conditional score multiplier if any filter is conditional
        multiplier = conditional_multiplier_for_ticker(td.ticker, filter_results)
        if multiplier != 1.0:
            track_a = track_a.model_copy(update={"score": track_a.score * multiplier})
            track_b = track_b.model_copy(update={"score": track_b.score * multiplier})
            track_c = track_c.model_copy(update={"score": track_c.score * multiplier})

        # Step 3e: Timing signal — use winning track's is_mispricing flag
        a_order = _CONVICTION_ORDER.get(track_a.conviction, 3)
        b_order = _CONVICTION_ORDER.get(track_b.conviction, 3)
        if b_order < a_order:
            is_mispricing = True
        elif a_order < b_order:
            is_mispricing = False
        else:
            is_mispricing = track_b.qualifies

        timing_signal = compute_v3_timing_signal(
            momentum_percentile=td.momentum_percentile,
            is_mispricing_track=is_mispricing,
        )

        # Step 3f: Orchestrate v4
        v4_result = orchestrate_v4(td.ticker, track_a, track_b, track_c, timing_signal)
        rules_conviction = v4_result.conviction

        # Compute composite_score from winning track's score
        track_scores = {
            "compounder": track_a.score if track_a.qualifies else 0.0,
            "mispricing": track_b.score if track_b.qualifies else 0.0,
            "efficient_growth": track_c.score if track_c.qualifies else 0.0,
        }
        composite_score = max(track_scores.values())

        # Step 3g: Apply ML ensemble override
        ml_alpha_val: float | None = None
        ml_confidence_val: float | None = None
        ml_override_type = "none"
        final_conviction = rules_conviction

        if ml_predictions is not None:
            model_qualifies = ml_predictions.get("model_qualifies", False)
            alphas = ml_predictions.get("alphas", {})
            vae_means = ml_predictions.get("vae_means", {})
            vae_variances = ml_predictions.get("vae_variances", {})

            if td.ticker in alphas:
                ml_alpha_val = alphas[td.ticker]
                vae_mean = vae_means.get(td.ticker, 0.0)
                vae_var = vae_variances.get(td.ticker, 1.0)
                ml_confidence_val = 1.0 - min(max(vae_var, 0.0), 1.0)

                final_conviction, ml_override_type = apply_ml_override(
                    rules_conviction=rules_conviction,
                    ml_alpha=ml_alpha_val,
                    vae_mean=vae_mean,
                    vae_variance=vae_var,
                    model_qualifies=model_qualifies,
                    universe_ml_alphas=universe_ml_alphas,
                )

        # Step 3h: Recompute position size if conviction changed
        if final_conviction != rules_conviction:
            max_position_pct = compute_v3_position_size(
                v4_result.opportunity_type, final_conviction
            )
        else:
            max_position_pct = v4_result.max_position_pct

        # Step 3i: Compute and apply score modifiers
        ac_mod = anti_consensus_modifier(
            td.short_interest_percentile,
            td.analyst_divergence,
            td.eps_revision_strength,
            td.fundamental_trajectory,
        )

        divergence_ratio = None  # Not yet available from LiquidityProfile
        liq_mod = liquidity_modifier(
            float(td.profile.market_cap),
            float(td.profile.avg_daily_volume),
            divergence_ratio,
        )

        drawdown_pct = None
        if td.high_52w and td.high_52w > 0 and td.current_price > 0:
            drawdown_pct = (td.current_price - td.high_52w) / td.high_52w

        ins_mod = insider_signal_modifier(
            td.insider_cluster_score_value,
            td.insider_cluster_detected,
            td.insider_total_buy_value,
            drawdown_pct,
            td.insider_has_first_buy,
        )

        # Inflection detection
        infl_result = inflection_score(td.history)
        infl_mod = inflection_modifier(infl_result.raw_value)

        # TAM expansion: use revenue history when available
        tam_score = None
        if td.revenue_history and len(td.revenue_history) >= 2 and td.sector:
            industry_rate = get_sector_growth_rate(td.sector)
            tam_factor = tam_expansion_velocity(td.revenue_history, industry_rate)
            if tam_factor is not None:
                tam_score = tam_factor.raw_value
        tam_mod = tam_modifier(tam_score)

        modified_score, modifier_breakdown = apply_all_modifiers(
            composite_score, ac_mod, liq_mod, ins_mod, inflection=infl_mod, tam=tam_mod
        )

        results.append(
            V4ResultWithML(
                ticker=td.ticker,
                opportunity_type=v4_result.opportunity_type,
                conviction=final_conviction,
                rules_conviction=rules_conviction,
                track_a=track_a,
                track_b=track_b,
                track_c=track_c,
                style=td.style,
                timing_signal=timing_signal,
                max_position_pct=max_position_pct,
                ml_alpha=ml_alpha_val,
                ml_confidence=ml_confidence_val,
                ml_override=ml_override_type,
                composite_score=composite_score,
                modified_score=modified_score,
                modifier_breakdown=modifier_breakdown,
            )
        )

    # Step 4: Sort by conviction order, then by max_position_pct descending
    results.sort(
        key=lambda r: (_CONVICTION_ORDER.get(r.conviction, 3), -r.max_position_pct),
    )

    # Step 5: Enforce portfolio cap — zero out positions beyond top V4_MAX_POSITIONS
    if not optimize:
        for i in range(V4_MAX_POSITIONS, len(results)):
            results[i] = results[i].model_copy(update={"max_position_pct": 0.0})

    return results
