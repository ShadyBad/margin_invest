"""V3 Universe Pipeline — orchestrates full v3 scoring across a universe of tickers.

Handles peer comparison IV computation, owner earnings IV, asset floor IV,
timing signals, and portfolio concentration cap enforcement.
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import (
    GICSSector,
)
from margin_engine.models.scoring import CompositeTier, FilterResult
from margin_engine.scoring.ticker_data import TickerDataBase
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


def _compute_ev_ebit(td: TickerV3Data) -> float | None:
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
    tickers_data: list[TickerV3Data],
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
    td: TickerV3Data,
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


def _compute_owner_earnings_per_share(td: TickerV3Data) -> float:
    """Compute owner earnings per share from period data."""
    cfo = float(td.latest_period.current_cash_flow.operating_cash_flow)
    depreciation = float(td.latest_period.current_income.depreciation or Decimal("0"))
    maintenance_capex = depreciation * 1.1
    owner_earnings = cfo - maintenance_capex
    shares = td.profile.shares_outstanding or 1
    return max(owner_earnings / shares, 0.0)


def _compute_asset_floor_per_share(td: TickerV3Data) -> float:
    """Compute asset floor IV per share."""
    cb = td.latest_period.current_balance
    net_cash = (cb.cash_and_equivalents or Decimal("0")) - cb.total_debt
    tangible_book = max(cb.total_equity, Decimal("0"))
    shares = td.profile.shares_outstanding or 1
    return asset_floor_valuation(net_cash, tangible_book, td.profile.sector, shares)


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
    sector_medians = _compute_sector_median_ev_ebit(tickers_data)

    results: list[V3Result] = []

    for td in tickers_data:
        wacc = compute_company_wacc(
            period=td.latest_period,
            profile=td.profile,
            beta=td.beta,
            sector_fallback=get_sector_wacc(td.profile.sector),
        )

        # Step 3: Owner earnings IV
        oe_per_share = _compute_owner_earnings_per_share(td)
        owner_earnings_iv = compute_owner_earnings_iv(oe_per_share, wacc)

        # Step 4: Asset floor IV
        asset_floor_iv = _compute_asset_floor_per_share(td)

        # Step 2 (per ticker): Peer comparison IV
        peer_comparison_iv = _compute_peer_comparison_iv(td, sector_medians)

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
        multiplier = _conditional_multiplier_for_ticker(td.ticker, filter_results)
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
