"""V3 Universe Pipeline — orchestrates full v3 scoring across a universe of tickers.

Handles peer comparison IV computation, owner earnings IV, asset floor IV,
timing signals, and portfolio concentration cap enforcement.
"""

from __future__ import annotations

from margin_engine.config.industry_growth_rates import get_sector_growth_rate
from margin_engine.models.scoring import CompositeTier, FilterResult
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
from margin_engine.scoring.v3_orchestrator import V3Result, orchestrate_v3
from margin_engine.scoring.v3_position_sizing import MAX_POSITIONS


class TickerV3Data(TickerDataBase):
    """All data needed to score a single ticker through the v3 pipeline."""

    pass


_CONVICTION_ORDER = {
    CompositeTier.EXCEPTIONAL: 0,
    CompositeTier.HIGH: 1,
    CompositeTier.MEDIUM: 2,
    CompositeTier.NONE: 3,
}


def score_universe_v3(
    tickers_data: list[TickerV3Data],
    shiller_cape: float,
    optimize: bool = False,
    filter_results: dict[str, list[FilterResult]] | None = None,
) -> list[V3Result]:
    """Score a universe of tickers through the full v3 pipeline.

    Steps:
        1. Detect regime and compute adjustments
        2. Compute sector median EV/EBIT for peer comparison IVs
        3. Compute owner_earnings_iv per ticker
        4. Compute asset_floor_iv per ticker
        5. Build TrackAInputs + TrackBInputs, run both cascades
        6. Compute timing signal per ticker
        7. Orchestrate v3 per ticker
        8. Sort by conviction then max_position_pct
        9. Enforce MAX_POSITIONS cap
    """
    if not tickers_data:
        return []

    # Step 1: Regime detection
    regime = detect_regime(shiller_cape)
    adj = regime_adjustments(regime)

    # Step 2: Sector median EV/EBIT
    sector_medians = compute_sector_median_ev_ebit(tickers_data)

    results: list[V3Result] = []

    for td in tickers_data:
        wacc = compute_company_wacc(
            period=td.latest_period,
            profile=td.profile,
            beta=td.beta,
            sector_fallback=get_sector_wacc(td.profile.sector),
        )

        # Step 3: Owner earnings IV
        oe_per_share = compute_owner_earnings_per_share(td)
        owner_earnings_iv = compute_owner_earnings_iv(oe_per_share, wacc)

        # Step 4: Asset floor IV
        asset_floor_iv = compute_asset_floor_per_share(td)

        # Step 2 (per ticker): Peer comparison IV
        peer_comparison_iv = compute_peer_comparison_iv(td, sector_medians)

        # Step 5: Build inputs and run cascades
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
            wacc=wacc,
            regime_adjustments=adj,
        )
        track_b = run_track_b_cascade(track_b_inputs)

        # Step 5b: Apply conditional score multiplier if any filter is conditional
        multiplier = conditional_multiplier_for_ticker(td.ticker, filter_results)
        if multiplier != 1.0:
            track_a = track_a.model_copy(update={"score": track_a.score * multiplier})
            track_b = track_b.model_copy(update={"score": track_b.score * multiplier})

        # Step 6: Timing signal — use winning track's is_mispricing flag
        # Determine the winning track for timing purposes
        a_order = _CONVICTION_ORDER.get(track_a.conviction, 3)
        b_order = _CONVICTION_ORDER.get(track_b.conviction, 3)
        if b_order < a_order:
            is_mispricing = True
        elif a_order < b_order:
            is_mispricing = False
        else:
            # Tie: Track B wins if it qualifies (mispricing flag)
            is_mispricing = track_b.qualifies

        timing_signal = compute_v3_timing_signal(
            momentum_percentile=td.momentum_percentile,
            is_mispricing_track=is_mispricing,
        )

        # Step 7: Orchestrate
        result = orchestrate_v3(td.ticker, track_a, track_b, timing_signal)

        # Step 7b: Compute and apply score modifiers
        # Composite score = winning track's score
        composite_score = max(
            track_a.score if track_a.qualifies else 0.0,
            track_b.score if track_b.qualifies else 0.0,
        )

        ac_mod = anti_consensus_modifier(
            td.short_interest_percentile,
            td.analyst_divergence,
            td.eps_revision_strength,
            td.fundamental_trajectory,
        )

        # Divergence ratio not yet available — pass None
        divergence_ratio = None
        liq_mod = liquidity_modifier(
            float(td.profile.market_cap),
            float(td.profile.avg_daily_volume),
            divergence_ratio,
        )

        # Compute drawdown from 52-week high
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

        result = result.model_copy(
            update={
                "modified_score": modified_score,
                "modifier_breakdown": modifier_breakdown,
            }
        )

        results.append(result)

    # Step 8: Sort by conviction order, then by max_position_pct descending
    results.sort(
        key=lambda r: (_CONVICTION_ORDER.get(r.conviction, 3), -r.max_position_pct),
    )

    # Step 9: Enforce portfolio cap — zero out positions beyond top MAX_POSITIONS
    # When optimize=True, skip position zeroing so the optimizer can allocate freely.
    if not optimize:
        for i in range(MAX_POSITIONS, len(results)):
            results[i] = results[i].model_copy(update={"max_position_pct": 0.0})

    return results
