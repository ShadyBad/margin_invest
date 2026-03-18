"""Shared helper functions for v3 and v4 scoring pipelines.

These functions were extracted from v3_pipeline.py and v4_pipeline.py to eliminate
duplication. They operate on TickerDataBase (the shared base class) so they work
with both TickerV3Data and TickerV4Data.
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.models.financial import GICSSector
from margin_engine.models.scoring import FilterResult
from margin_engine.scoring.quantitative.asset_floor import asset_floor_valuation
from margin_engine.scoring.ticker_data import TickerDataBase

DEFAULT_CONDITIONAL_MULTIPLIER = 0.90


def conditional_multiplier_for_ticker(
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
                metrics.get("conditional_score_multiplier", DEFAULT_CONDITIONAL_MULTIPLIER)
            )
    return 1.0


def compute_ev_ebit(td: TickerDataBase) -> float | None:
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


def compute_sector_median_ev_ebit(
    tickers_data: list[TickerDataBase],
) -> dict[GICSSector, float]:
    """Compute median EV/EBIT per sector from the universe."""
    sector_ev_ebits: dict[GICSSector, list[float]] = {}
    for td in tickers_data:
        ev_ebit = compute_ev_ebit(td)
        if ev_ebit is not None and ev_ebit > 0:
            sector = td.profile.sector
            sector_ev_ebits.setdefault(sector, []).append(ev_ebit)

    result: dict[GICSSector, float] = {}
    for sector, values in sector_ev_ebits.items():
        result[sector] = statistics.median(values)
    return result


def compute_peer_comparison_iv(
    td: TickerDataBase,
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


def compute_owner_earnings_per_share(td: TickerDataBase) -> float:
    """Compute owner earnings per share from period data."""
    cfo = float(td.latest_period.current_cash_flow.operating_cash_flow)
    depreciation = float(td.latest_period.current_income.depreciation or Decimal("0"))
    maintenance_capex = depreciation * 1.1
    owner_earnings = cfo - maintenance_capex
    shares = td.profile.shares_outstanding or 1
    return max(owner_earnings / shares, 0.0)


def compute_asset_floor_per_share(td: TickerDataBase) -> float:
    """Compute asset floor IV per share."""
    cb = td.latest_period.current_balance
    net_cash = (cb.cash_and_equivalents or Decimal("0")) - cb.total_debt
    tangible_book = max(cb.total_equity, Decimal("0"))
    shares = td.profile.shares_outstanding or 1
    return asset_floor_valuation(net_cash, tangible_book, td.profile.sector, shares)
