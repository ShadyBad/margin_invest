"""Historical scorer — scores a universe at a point-in-time using PIT data.

Runs the IDENTICAL scoring pipeline as the live scorer in
``api/src/margin_api/services/scoring.py``:
    elimination filters -> raw factor scores -> sector-neutral percentile ranking
    -> composite score

The only difference is that data comes from pre-built PIT snapshot dicts and
price bar dicts rather than live database queries.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from margin_engine.ingestion.normalizer import (
    normalize_balance_sheet,
    normalize_cash_flow,
    normalize_income_statement,
    normalize_price_bar,
)
from margin_engine.models.financial import (
    AssetProfile,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    PriceBar,
)
from margin_engine.models.scoring import (
    CompositeScore,
    CompositeTier,
    FactorBreakdown,
    FactorScore,
    FilterResult,
    GrowthStage,
)
from margin_engine.scoring.classifier import classify_growth_stage
from margin_engine.scoring.composite import compute_composite_score
from margin_engine.scoring.data_quality_gate import apply_data_quality_gate
from margin_engine.scoring.filters.pipeline import run_elimination_filters
from margin_engine.scoring.normalizer import compute_percentile_ranks, rerank_composites
from margin_engine.scoring.quantitative.accrual_ratio import sloan_accrual_ratio
from margin_engine.scoring.quantitative.acquirers_multiple import acquirers_multiple
from margin_engine.scoring.quantitative.competitive_dynamics import gross_margin_stability
from margin_engine.scoring.quantitative.dcf_mos import dcf_margin_of_safety
from margin_engine.scoring.quantitative.ev_fcf import ev_fcf
from margin_engine.scoring.quantitative.f_score import piotroski_f_score
from margin_engine.scoring.quantitative.fcf_conversion import fcf_conversion
from margin_engine.scoring.quantitative.gross_profitability import gross_profitability
from margin_engine.scoring.quantitative.incremental_roic import incremental_roic
from margin_engine.scoring.quantitative.multi_horizon_momentum import multi_horizon_momentum
from margin_engine.scoring.quantitative.revenue_cagr import revenue_cagr
from margin_engine.scoring.quantitative.roic_trend import roic_trend
from margin_engine.scoring.quantitative.roic_wacc import roic_wacc_spread
from margin_engine.scoring.quantitative.rule_of_40 import rule_of_40
from margin_engine.scoring.quantitative.runway_score import runway_score
from margin_engine.scoring.quantitative.sentiment_score import sentiment_score
from margin_engine.scoring.quantitative.shareholder_yield import shareholder_yield

# Sector string -> GICSSector mapping for lookups
_SECTOR_MAP: dict[str, GICSSector] = {s.value: s for s in GICSSector}

# Factors where lower raw_value = better (higher percentile)
INVERTED_FACTORS: frozenset[str] = frozenset(
    {
        "accrual_ratio",
        "ev_fcf",
        "acquirers_multiple",
        "gross_margin_stability",  # lower CoV = better
    }
)


@dataclass
class _RawScoringResult:
    """Intermediate result from raw factor scoring (before percentile ranking)."""

    ticker: str
    sector: str
    quality_scores: list[FactorScore] = field(default_factory=list)
    value_scores: list[FactorScore] = field(default_factory=list)
    momentum_scores: list[FactorScore] = field(default_factory=list)
    growth_scores: list[FactorScore] = field(default_factory=list)
    filter_results: list[FilterResult] = field(default_factory=list)
    growth_stage: GrowthStage | None = None
    period: FinancialPeriod | None = None
    profile: AssetProfile | None = None
    price_bars: list[PriceBar] = field(default_factory=list)
    history: FinancialHistory | None = None


def _build_financial_period(
    income_raw: dict,
    balance_raw: dict,
    cashflow_raw: dict,
    period_end: str,
    filing_date: str,
    prior_income_raw: dict | None = None,
    prior_balance_raw: dict | None = None,
    prior_cashflow_raw: dict | None = None,
) -> FinancialPeriod:
    """Convert raw JSON dicts into a FinancialPeriod engine model."""
    current_income = normalize_income_statement(income_raw)
    current_balance = normalize_balance_sheet(balance_raw)
    current_cash_flow = normalize_cash_flow(cashflow_raw)

    prior_income = normalize_income_statement(prior_income_raw) if prior_income_raw else None
    prior_balance = normalize_balance_sheet(prior_balance_raw) if prior_balance_raw else None
    prior_cash_flow = normalize_cash_flow(prior_cashflow_raw) if prior_cashflow_raw else None

    return FinancialPeriod(
        period_end=period_end,
        filing_date=filing_date,
        current_income=current_income,
        prior_income=prior_income,
        current_balance=current_balance,
        prior_balance=prior_balance,
        current_cash_flow=current_cash_flow,
        prior_cash_flow=prior_cash_flow,
    )


def _build_history_from_snapshots(
    ticker: str,
    snapshots: list[dict],
) -> FinancialHistory:
    """Build a FinancialHistory from multiple PIT snapshots (sorted oldest-first).

    Each snapshot should have: period_end, filing_date, income_statement,
    balance_sheet, cash_flow.
    """
    sorted_snaps = sorted(snapshots, key=lambda s: s["period_end"])
    periods: list[FinancialPeriod] = []
    for i, snap in enumerate(sorted_snaps):
        prior = sorted_snaps[i - 1] if i > 0 else None
        period = _build_financial_period(
            income_raw=snap.get("income_statement") or {},
            balance_raw=snap.get("balance_sheet") or {},
            cashflow_raw=snap.get("cash_flow") or {},
            period_end=snap["period_end"],
            filing_date=snap.get("filing_date", ""),
            prior_income_raw=(prior.get("income_statement") or {}) if prior else None,
            prior_balance_raw=(prior.get("balance_sheet") or {}) if prior else None,
            prior_cashflow_raw=(prior.get("cash_flow") or {}) if prior else None,
        )
        periods.append(period)
    return FinancialHistory(ticker=ticker, periods=periods)


def _compute_raw_scores(
    ticker: str,
    period: FinancialPeriod,
    profile: AssetProfile,
    price_bars_raw: list[dict],
    history: FinancialHistory | None = None,
) -> _RawScoringResult:
    """Compute raw factor scores for a single ticker (before percentile ranking).

    Mirrors ``compute_raw_factor_scores()`` in the live scorer, but excludes
    SUE (no earnings surprise data in PIT snapshots), scenario IV, and price targets.
    Adds growth factors (revenue_cagr, incremental_roic, rule_of_40, runway_score).
    """
    market_cap = profile.market_cap

    # --- Step 1: Elimination filters ---
    pipeline_result = run_elimination_filters(period, profile)
    filter_results = pipeline_result.results

    # --- Step 2: Quality factors ---
    quality_scores: list[FactorScore] = [
        gross_profitability(period),
        roic_wacc_spread(period),
        sloan_accrual_ratio(period),
        piotroski_f_score(period),
        fcf_conversion(period),
    ]
    if history is not None and len(history.periods) >= 2:
        quality_scores.append(roic_trend(history))
        quality_scores.append(gross_margin_stability(history))

    # --- Step 3: Value factors ---
    value_scores: list[FactorScore] = [
        ev_fcf(period, market_cap),
        shareholder_yield(period, market_cap),
        dcf_margin_of_safety(
            period,
            market_cap,
            growth_rate=0.05,
            discount_rate=0.10,
        ),
        acquirers_multiple(period, market_cap),
    ]

    # --- Step 4: Momentum factors ---
    bars: list[PriceBar] = [normalize_price_bar(b) for b in price_bars_raw]
    momentum_scores: list[FactorScore] = [
        multi_horizon_momentum(bars),
        sentiment_score(score=0.0),  # neutral stub for consistent sub-score count
    ]

    # --- Step 5: Growth factors ---
    growth_scores: list[FactorScore] = []
    if history is not None and len(history.periods) >= 2:
        growth_scores.append(revenue_cagr(history))
        growth_scores.append(incremental_roic(history))

    # rule_of_40: requires revenue > 0 and revenue_growth
    rev = float(period.current_income.revenue)
    if rev > 0:
        fcf = float(period.current_cash_flow.free_cash_flow)
        fcf_margin = fcf / rev
        rev_growth = period.revenue_growth
        if rev_growth is not None:
            growth_scores.append(rule_of_40(rev_growth, fcf_margin))

    # runway_score: always (None for sub_industry_revenue)
    growth_scores.append(runway_score(period.current_income.revenue, None))

    # --- Step 6: Classify growth stage ---
    growth_stage = classify_growth_stage(period, profile)

    return _RawScoringResult(
        ticker=ticker,
        sector=profile.sector.value,
        quality_scores=quality_scores,
        value_scores=value_scores,
        momentum_scores=momentum_scores,
        growth_scores=growth_scores,
        filter_results=filter_results,
        growth_stage=growth_stage,
        period=period,
        profile=profile,
        price_bars=bars,
        history=history,
    )


def _rank_and_compute_composites(
    raw_results: list[_RawScoringResult],
) -> list[CompositeScore]:
    """Rank factor scores across sector peers and compute composite scores.

    Mirrors ``rank_and_compute_composites()`` in the live scorer exactly.
    """
    # Collect: (sector, factor_name) -> [(result_idx, list_attr, score_idx)]
    groups: dict[tuple[str, str], list[tuple[int, str, int]]] = defaultdict(list)
    scores_by_key: dict[tuple[str, str], list[FactorScore]] = defaultdict(list)

    for i, result in enumerate(raw_results):
        for list_attr in (
            "quality_scores",
            "value_scores",
            "momentum_scores",
            "growth_scores",
        ):
            scores = getattr(result, list_attr)
            for j, score in enumerate(scores):
                key = (result.sector, score.name)
                groups[key].append((i, list_attr, j))
                scores_by_key[key].append(score)

    # Rank each (sector, factor_name) group
    for key, entries in groups.items():
        _, factor_name = key
        ranked = compute_percentile_ranks(
            scores_by_key[key], invert=(factor_name in INVERTED_FACTORS)
        )
        # Map ranked scores back
        for (result_idx, list_attr, score_idx), ranked_score in zip(entries, ranked):
            getattr(raw_results[result_idx], list_attr)[score_idx] = ranked_score

    # Compute composite scores with ranked percentiles
    composites: list[CompositeScore] = []
    for r in raw_results:
        composite = compute_composite_score(
            ticker=r.ticker,
            quality_scores=r.quality_scores,
            value_scores=r.value_scores,
            momentum_scores=r.momentum_scores,
            filters_passed=r.filter_results,
            growth_stage=r.growth_stage,
        )

        # Attach growth breakdown if growth scores exist
        if r.growth_scores:
            growth_breakdown = FactorBreakdown(
                factor_name="growth",
                weight=0.0,  # growth doesn't affect composite weighting in v1
                sub_scores=r.growth_scores,
            )
            composite = composite.model_copy(update={"growth": growth_breakdown})

        composites.append(composite)

    # Final re-rank: convert weighted-average composite scores to proper
    # percentile ranks across the full universe so conviction thresholds work.
    composites = rerank_composites(composites)

    # Apply data quality gate: cap conviction when data coverage is low
    tier_score_cap: dict[CompositeTier, float] = {
        CompositeTier.NONE: 64.9,
        CompositeTier.MEDIUM: 71.9,
        CompositeTier.HIGH: 78.9,
    }
    gated: list[CompositeScore] = []
    for composite in composites:
        gated_tier = apply_data_quality_gate(composite.composite_tier, composite.data_coverage)
        if gated_tier != composite.composite_tier:
            max_score = tier_score_cap.get(gated_tier, composite.composite_raw_score)
            composite = composite.model_copy(
                update={
                    "composite_raw_score": min(composite.composite_raw_score, max_score),
                    "composite_percentile": min(composite.composite_percentile, max_score),
                }
            )
        gated.append(composite)

    return gated


def score_universe_at_date(
    pit_snapshots: list[dict],
    pit_prices: dict[str, list[dict]],
    rebalance_date: str,
    active_tickers: set[str],
) -> list[CompositeScore]:
    """Score all active tickers at a given rebalance date using PIT data.

    Runs the identical scoring pipeline as the live scorer:
    elimination filters -> raw factor scores -> sector-neutral percentile ranking
    -> composite score.

    Args:
        pit_snapshots: List of PIT snapshot dicts, each containing:
            ticker, filing_date, period_end, income_statement, balance_sheet,
            cash_flow, sector, market_cap, shares_outstanding.
        pit_prices: Mapping of ticker -> list of price bar dicts (daily OHLCV).
        rebalance_date: ISO date string for the rebalance (used for context, not filtering).
        active_tickers: Set of tickers to score. Tickers not in this set are
            excluded to prevent survivorship bias.

    Returns:
        List of CompositeScore for each scored ticker.
    """
    if not pit_snapshots or not active_tickers:
        return []

    # --- Group snapshots by ticker, filter to active only ---
    by_ticker: dict[str, list[dict]] = defaultdict(list)
    for snap in pit_snapshots:
        ticker = snap["ticker"]
        if ticker in active_tickers:
            by_ticker[ticker].append(snap)

    if not by_ticker:
        return []

    # --- For each ticker: build period, profile, history, compute raw scores ---
    raw_results: list[_RawScoringResult] = []
    for ticker, snaps in by_ticker.items():
        # Sort by period_end, use latest for scoring
        snaps_sorted = sorted(snaps, key=lambda s: s["period_end"])
        latest = snaps_sorted[-1]

        # Build the latest FinancialPeriod
        prior_snap = snaps_sorted[-2] if len(snaps_sorted) >= 2 else None
        period = _build_financial_period(
            income_raw=latest.get("income_statement") or {},
            balance_raw=latest.get("balance_sheet") or {},
            cashflow_raw=latest.get("cash_flow") or {},
            period_end=latest["period_end"],
            filing_date=latest.get("filing_date", ""),
            prior_income_raw=((prior_snap.get("income_statement") or {}) if prior_snap else None),
            prior_balance_raw=((prior_snap.get("balance_sheet") or {}) if prior_snap else None),
            prior_cashflow_raw=((prior_snap.get("cash_flow") or {}) if prior_snap else None),
        )

        # Build AssetProfile
        sector_str = latest.get("sector", "Information Technology")
        gics_sector = _SECTOR_MAP.get(sector_str)
        if gics_sector is None:
            # Skip tickers with unknown sectors
            continue

        market_cap = Decimal(str(latest.get("market_cap", 0)))
        shares_outstanding = latest.get("shares_outstanding")

        profile = AssetProfile(
            ticker=ticker,
            name=ticker,  # PIT data doesn't store name; use ticker
            sector=gics_sector,
            market_cap=market_cap,
            shares_outstanding=shares_outstanding,
        )

        # Build FinancialHistory when multiple snapshots exist
        history: FinancialHistory | None = None
        if len(snaps_sorted) >= 2:
            history = _build_history_from_snapshots(ticker, snaps_sorted)

        # Price bars for this ticker
        price_bars_raw = pit_prices.get(ticker, [])

        # Compute raw scores
        raw = _compute_raw_scores(
            ticker=ticker,
            period=period,
            profile=profile,
            price_bars_raw=price_bars_raw,
            history=history,
        )
        raw_results.append(raw)

    if not raw_results:
        return []

    # --- Sector-neutral ranking and composite scoring ---
    return _rank_and_compute_composites(raw_results)
