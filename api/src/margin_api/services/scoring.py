"""Scoring service — bridge between raw JSONB financial data and the engine.

Converts raw JSON dicts (as stored in the database) into engine Pydantic models,
then runs the full scoring pipeline: elimination filters -> factor scoring ->
growth stage classification -> percentile ranking -> composite scoring.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from margin_engine.ingestion.normalizer import (
    normalize_balance_sheet,
    normalize_cash_flow,
    normalize_earnings_list,
    normalize_income_statement,
    normalize_price_bar,
)
from margin_engine.models.financial import (
    AssetProfile,
    FinancialPeriod,
    GICSSector,
    PriceBar,
)
from margin_engine.models.scoring import CompositeScore, FactorScore, FilterResult, GrowthStage
from margin_engine.scoring.classifier import classify_growth_stage
from margin_engine.scoring.composite import compute_composite_score
from margin_engine.scoring.filters.pipeline import run_elimination_filters
from margin_engine.scoring.normalizer import compute_percentile_ranks
from margin_engine.scoring.quantitative.accrual_ratio import sloan_accrual_ratio
from margin_engine.scoring.quantitative.acquirers_multiple import acquirers_multiple
from margin_engine.scoring.quantitative.dcf_mos import dcf_margin_of_safety
from margin_engine.scoring.quantitative.ev_fcf import ev_fcf
from margin_engine.scoring.quantitative.f_score import piotroski_f_score
from margin_engine.scoring.quantitative.gross_profitability import gross_profitability
from margin_engine.scoring.quantitative.price_momentum import price_momentum
from margin_engine.scoring.quantitative.roic_wacc import roic_wacc_spread
from margin_engine.scoring.quantitative.price_targets import compute_price_targets
from margin_engine.scoring.quantitative.shareholder_yield import shareholder_yield
from margin_engine.scoring.quantitative.sue import sue_score

# Sector string -> GICSSector mapping for lookups
_SECTOR_MAP: dict[str, GICSSector] = {s.value: s for s in GICSSector}

# Factors where lower raw_value = better (higher percentile)
INVERTED_FACTORS: frozenset[str] = frozenset({
    "accrual_ratio",
    "ev_fcf",
    "acquirers_multiple",
})


@dataclass
class RawScoringResult:
    """Intermediate result from raw factor scoring (before percentile ranking)."""

    ticker: str
    sector: str
    quality_scores: list[FactorScore] = field(default_factory=list)
    value_scores: list[FactorScore] = field(default_factory=list)
    momentum_scores: list[FactorScore] = field(default_factory=list)
    filter_results: list[FilterResult] = field(default_factory=list)
    growth_stage: GrowthStage | None = None
    period: FinancialPeriod | None = None
    profile: AssetProfile | None = None
    price_bars: list[PriceBar] = field(default_factory=list)


def build_financial_period(
    income_raw: dict,
    balance_raw: dict,
    cashflow_raw: dict,
    period_end: str,
    filing_date: str,
    prior_income_raw: dict | None = None,
    prior_balance_raw: dict | None = None,
    prior_cashflow_raw: dict | None = None,
) -> FinancialPeriod:
    """Convert raw JSON dicts into a FinancialPeriod engine model.

    Uses the engine's normalizer functions to handle field-name variations
    across different data providers.

    Args:
        income_raw: Raw income statement dict (camelCase or snake_case keys).
        balance_raw: Raw balance sheet dict.
        cashflow_raw: Raw cash flow statement dict.
        period_end: ISO date string for the period end (e.g. "2024-09-28").
        filing_date: ISO date string for the filing date (e.g. "2024-11-01").
        prior_income_raw: Optional prior-period income statement dict.
        prior_balance_raw: Optional prior-period balance sheet dict.
        prior_cashflow_raw: Optional prior-period cash flow statement dict.

    Returns:
        A fully populated FinancialPeriod.
    """
    current_income = normalize_income_statement(income_raw)
    current_balance = normalize_balance_sheet(balance_raw)
    current_cash_flow = normalize_cash_flow(cashflow_raw)

    prior_income = (
        normalize_income_statement(prior_income_raw) if prior_income_raw else None
    )
    prior_balance = (
        normalize_balance_sheet(prior_balance_raw) if prior_balance_raw else None
    )
    prior_cash_flow = (
        normalize_cash_flow(prior_cashflow_raw) if prior_cashflow_raw else None
    )

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


def build_asset_profile(
    ticker: str,
    name: str,
    sector: str,
    market_cap: Decimal,
    avg_daily_volume: Decimal = Decimal("0"),
    years_of_history: int = 0,
) -> AssetProfile:
    """Build an AssetProfile engine model from basic metadata.

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL").
        name: Company name (e.g. "Apple Inc.").
        sector: GICS sector string (e.g. "Information Technology").
        market_cap: Market capitalization as a Decimal.
        avg_daily_volume: Average daily dollar volume. Defaults to 0.
        years_of_history: Years of trading history. Defaults to 0.

    Returns:
        A populated AssetProfile.

    Raises:
        ValueError: If the sector string does not match any GICSSector value.
    """
    gics_sector = _SECTOR_MAP.get(sector)
    if gics_sector is None:
        valid = ", ".join(sorted(_SECTOR_MAP.keys()))
        raise ValueError(
            f"Unknown sector: '{sector}'. Valid sectors: {valid}"
        )

    return AssetProfile(
        ticker=ticker,
        name=name,
        sector=gics_sector,
        market_cap=market_cap,
        avg_daily_volume=avg_daily_volume,
        years_of_history=years_of_history,
    )


def compute_raw_factor_scores(
    ticker: str,
    period: FinancialPeriod,
    profile: AssetProfile,
    price_bars_raw: list[dict],
    earnings_raw: list[dict],
) -> RawScoringResult:
    """Compute raw factor scores without percentile ranking.

    Steps 1-5 of the pipeline (filters, quality, value, momentum, growth stage).
    Percentile ranking must be done in a batch via rank_and_compute_composites().

    Args:
        ticker: Stock ticker symbol.
        period: FinancialPeriod with current (and optionally prior) data.
        profile: AssetProfile with metadata and sector.
        price_bars_raw: List of raw price bar dicts for price momentum.
        earnings_raw: List of raw earnings surprise dicts for SUE score.

    Returns:
        A RawScoringResult with unranked factor scores.
    """
    market_cap = profile.market_cap

    # --- Step 1: Elimination filters ---
    pipeline_result = run_elimination_filters(period, profile)
    filter_results = pipeline_result.results

    # --- Step 2: Quality factors (4) ---
    quality_scores = [
        gross_profitability(period),
        roic_wacc_spread(period),
        sloan_accrual_ratio(period),
        piotroski_f_score(period),
    ]

    # --- Step 3: Value factors (4) ---
    value_scores = [
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

    # --- Step 4: Momentum factors (5) ---
    bars: list[PriceBar] = [normalize_price_bar(b) for b in price_bars_raw]
    surprises = normalize_earnings_list(earnings_raw)

    momentum_scores: list[FactorScore] = [
        price_momentum(bars),
    ]
    # Only include SUE when real earnings data exists. When all tickers
    # have no earnings, every SUE is 0.0 → all get 50th percentile,
    # dragging momentum averages down and capping composites below
    # conviction thresholds (same issue as the removed placeholders).
    if earnings_raw:
        momentum_scores.append(sue_score(surprises))

    # --- Step 5: Classify growth stage ---
    growth_stage = classify_growth_stage(period, profile)

    return RawScoringResult(
        ticker=ticker,
        sector=profile.sector.value,
        quality_scores=quality_scores,
        value_scores=value_scores,
        momentum_scores=momentum_scores,
        filter_results=filter_results,
        growth_stage=growth_stage,
        period=period,
        profile=profile,
        price_bars=bars,
    )


def rank_and_compute_composites(
    raw_results: list[RawScoringResult],
) -> list[CompositeScore]:
    """Rank factor scores across sector peers and compute composite scores.

    Takes raw scoring results for all tickers and:
    1. Groups sub-factor scores by (sector, factor_name).
    2. Runs compute_percentile_ranks() within each sector group.
    3. Maps ranked scores back to each ticker.
    4. Computes composite scores with the ranked percentiles.

    Args:
        raw_results: List of RawScoringResult from compute_raw_factor_scores().

    Returns:
        List of CompositeScore with sector-neutral percentile ranks.
    """
    # Collect: (sector, factor_name) -> [(result_idx, list_attr, score_idx)]
    groups: dict[tuple[str, str], list[tuple[int, str, int]]] = defaultdict(list)
    scores_by_key: dict[tuple[str, str], list[FactorScore]] = defaultdict(list)

    for i, result in enumerate(raw_results):
        for list_attr in ("quality_scores", "value_scores", "momentum_scores"):
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

    # Compute composite scores with ranked percentiles and price targets
    composites: list[CompositeScore] = []
    for r in raw_results:
        # First pass: compute composite without price targets to get conviction_level
        base_composite = compute_composite_score(
            ticker=r.ticker,
            quality_scores=r.quality_scores,
            value_scores=r.value_scores,
            momentum_scores=r.momentum_scores,
            filters_passed=r.filter_results,
            growth_stage=r.growth_stage,
        )

        # Second pass: compute price targets using the derived conviction_level
        price_targets = None
        if r.period is not None and r.profile is not None:
            price_targets = compute_price_targets(
                period=r.period,
                profile=r.profile,
                price_bars=r.price_bars,
                conviction_level=base_composite.conviction_level,
            )

        if price_targets is not None:
            # Re-compute with price targets attached
            composite = compute_composite_score(
                ticker=r.ticker,
                quality_scores=r.quality_scores,
                value_scores=r.value_scores,
                momentum_scores=r.momentum_scores,
                filters_passed=r.filter_results,
                growth_stage=r.growth_stage,
                price_targets=price_targets,
            )
        else:
            composite = base_composite

        composites.append(composite)

    return composites


def run_scoring_pipeline(
    ticker: str,
    period: FinancialPeriod,
    profile: AssetProfile,
    price_bars_raw: list[dict],
    earnings_raw: list[dict],
) -> CompositeScore:
    """Run the full scoring pipeline for a single ticker.

    Note: Single-ticker scoring cannot produce meaningful percentile ranks
    (all sub-factors get 50th percentile). For proper sector-neutral ranking,
    use compute_raw_factor_scores() + rank_and_compute_composites() in a batch.

    Args:
        ticker: Stock ticker symbol.
        period: FinancialPeriod with current (and optionally prior) data.
        profile: AssetProfile with metadata and sector.
        price_bars_raw: List of raw price bar dicts for price momentum.
        earnings_raw: List of raw earnings surprise dicts for SUE score.

    Returns:
        A CompositeScore (with single-ticker percentile ranks).
    """
    raw = compute_raw_factor_scores(ticker, period, profile, price_bars_raw, earnings_raw)
    composites = rank_and_compute_composites([raw])
    return composites[0]
