"""V4 Universe Pipeline — extends V3 with Track C, style classification, and ML override.

Handles peer comparison IV computation, owner earnings IV, asset floor IV,
timing signals, Track C cascade for GROWTH-style tickers, ML ensemble override,
and portfolio concentration cap enforcement.
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from pydantic import BaseModel

from margin_engine.ml.ensemble_override import apply_ml_override
from margin_engine.models.financial import (
    AssetProfile,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
)
from margin_engine.models.scoring import CompositeTier, FilterResult, InvestmentStyle
from margin_engine.scoring.market_regime import detect_regime, regime_adjustments
from margin_engine.scoring.quantitative.asset_floor import asset_floor_valuation
from margin_engine.scoring.quantitative.wacc_company import compute_company_wacc
from margin_engine.scoring.quantitative.wacc_sector import get_sector_wacc
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


class TickerV4Data(BaseModel):
    """All data needed to score a single ticker through the v4 pipeline."""

    ticker: str
    history: FinancialHistory
    latest_period: FinancialPeriod
    profile: AssetProfile
    current_price: float
    current_fcf_per_share: float
    sustainable_growth_rate: float
    buyback_yield: float | None = None
    insider_ownership_pct: float | None = None
    sbc_pct: float | None = None
    recent_acquisition_count: int = 0
    sue_percentile: float = 0.0
    accumulation_percentile: float = 0.0
    beta: float | None = None
    momentum_percentile: float = 50.0
    dcf_iv: float = 0.0

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


_CONVICTION_ORDER = {
    CompositeTier.EXCEPTIONAL: 0,
    CompositeTier.HIGH: 1,
    CompositeTier.MEDIUM: 2,
    CompositeTier.NONE: 3,
}

_DEFAULT_CONDITIONAL_MULTIPLIER = 0.90


def _conditional_multiplier_for_ticker(
    ticker: str,
    filter_results: dict[str, list[FilterResult]] | None,
) -> float:
    """Return the conditional score multiplier if any filter for this ticker is conditional.

    Returns 1.0 (no penalty) when no filter is conditional.
    """
    if filter_results is None:
        return 1.0
    ticker_filters = filter_results.get(ticker)
    if not ticker_filters:
        return 1.0
    for fr in ticker_filters:
        if fr.conditional:
            metrics = fr.computed_metrics or {}
            return float(
                metrics.get("conditional_score_multiplier", _DEFAULT_CONDITIONAL_MULTIPLIER)
            )
    return 1.0


def _compute_ev_ebit(td: TickerV4Data) -> float | None:
    """Compute EV/EBIT for a ticker. Returns None if EBIT <= 0."""
    cb = td.latest_period.current_balance
    market_cap = float(td.profile.market_cap)
    total_debt = float(cb.total_debt)
    cash = float(cb.cash_and_equivalents or Decimal("0"))
    ev = market_cap + total_debt - cash

    ebit = float(td.latest_period.current_income.ebit)
    if ebit <= 0:
        return None
    return ev / ebit


def _compute_sector_median_ev_ebit(
    tickers_data: list[TickerV4Data],
) -> dict[GICSSector, float]:
    """Compute median EV/EBIT per sector from the universe."""
    sector_ev_ebits: dict[GICSSector, list[float]] = {}
    for td in tickers_data:
        ev_ebit = _compute_ev_ebit(td)
        if ev_ebit is not None and ev_ebit > 0:
            sector = td.profile.sector
            sector_ev_ebits.setdefault(sector, []).append(ev_ebit)

    result: dict[GICSSector, float] = {}
    for sector, values in sector_ev_ebits.items():
        result[sector] = statistics.median(values)
    return result


def _compute_peer_comparison_iv(
    td: TickerV4Data,
    sector_median_ev_ebit: dict[GICSSector, float],
) -> float:
    """Compute peer comparison IV: sector_median_ev_ebit * company_ebit / shares."""
    median = sector_median_ev_ebit.get(td.profile.sector)
    if median is None:
        return 0.0
    ebit = float(td.latest_period.current_income.ebit)
    if ebit <= 0:
        return 0.0
    shares = td.profile.shares_outstanding or 1
    return median * ebit / shares


def _compute_owner_earnings_per_share(td: TickerV4Data) -> float:
    """Compute owner earnings per share from period data."""
    cfo = float(td.latest_period.current_cash_flow.operating_cash_flow)
    depreciation = float(td.latest_period.current_income.depreciation or Decimal("0"))
    maintenance_capex = depreciation * 1.1
    owner_earnings = cfo - maintenance_capex
    shares = td.profile.shares_outstanding or 1
    return max(owner_earnings / shares, 0.0)


def _compute_asset_floor_per_share(td: TickerV4Data) -> float:
    """Compute asset floor IV per share."""
    cb = td.latest_period.current_balance
    net_cash = (cb.cash_and_equivalents or Decimal("0")) - cb.total_debt
    tangible_book = max(cb.total_equity, Decimal("0"))
    shares = td.profile.shares_outstanding or 1
    return asset_floor_valuation(net_cash, tangible_book, td.profile.sector, shares)


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
    sector_medians = _compute_sector_median_ev_ebit(tickers_data)

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
        oe_per_share = _compute_owner_earnings_per_share(td)
        owner_earnings_iv = compute_owner_earnings_iv(oe_per_share, wacc)

        # Asset floor IV
        asset_floor_iv = _compute_asset_floor_per_share(td)

        # Peer comparison IV
        peer_comparison_iv = _compute_peer_comparison_iv(td, sector_medians)

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
        multiplier = _conditional_multiplier_for_ticker(td.ticker, filter_results)
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
