"""Scoring service — bridge between raw JSONB financial data and the engine.

Converts raw JSON dicts (as stored in the database) into engine Pydantic models,
then runs the full scoring pipeline: elimination filters -> factor scoring ->
growth stage classification -> percentile ranking -> composite scoring.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from margin_engine.healing.models import SectorDistribution
from margin_engine.healing.pipeline import HealingPipeline, HealingResult
from margin_engine.ingestion.normalizer import (
    normalize_balance_sheet,
    normalize_cash_flow,
    normalize_earnings_list,
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
from margin_engine.scoring.quantitative.price_targets import compute_price_targets
from margin_engine.scoring.quantitative.revenue_cagr import revenue_cagr
from margin_engine.scoring.quantitative.roic_trend import roic_trend
from margin_engine.scoring.quantitative.roic_wacc import roic_wacc_spread
from margin_engine.scoring.quantitative.rule_of_40 import rule_of_40
from margin_engine.scoring.quantitative.runway_score import runway_score
from margin_engine.scoring.quantitative.scenario_iv import compute_scenario_iv
from margin_engine.scoring.quantitative.sentiment_score import sentiment_score
from margin_engine.scoring.quantitative.shareholder_yield import shareholder_yield
from margin_engine.scoring.quantitative.sue import sue_score

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
class RawScoringResult:
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


def build_financial_period(
    income_raw: dict,
    balance_raw: dict,
    cashflow_raw: dict,
    period_end: str,
    filing_date: str,
    prior_income_raw: dict | None = None,
    prior_balance_raw: dict | None = None,
    prior_cashflow_raw: dict | None = None,
    # Healing pipeline (optional)
    healing_pipeline: HealingPipeline | None = None,
    sector: str = "",
    sector_distributions: list[SectorDistribution] | None = None,
    prior_sector_distributions: list[SectorDistribution] | None = None,
    ticker_history: dict[str, list[float]] | None = None,
    secondary_values: dict[str, float] | None = None,
    prior_valid_values: dict[str, float] | None = None,
    sector_ticker_count: int = 0,
    sector_flagged_tickers: set[str] | None = None,
) -> FinancialPeriod | tuple[FinancialPeriod, HealingResult]:
    """Convert raw JSON dicts into a FinancialPeriod engine model.

    Uses the engine's normalizer functions to handle field-name variations
    across different data providers. When a ``healing_pipeline`` is supplied,
    the pipeline is run after normalization and the result is returned as a
    ``(FinancialPeriod, HealingResult)`` tuple.

    Args:
        income_raw: Raw income statement dict (camelCase or snake_case keys).
        balance_raw: Raw balance sheet dict.
        cashflow_raw: Raw cash flow statement dict.
        period_end: ISO date string for the period end (e.g. "2024-09-28").
        filing_date: ISO date string for the filing date (e.g. "2024-11-01").
        prior_income_raw: Optional prior-period income statement dict.
        prior_balance_raw: Optional prior-period balance sheet dict.
        prior_cashflow_raw: Optional prior-period cash flow statement dict.
        healing_pipeline: Optional HealingPipeline instance. When provided the
            function runs detection/correction and returns a tuple.
        sector: GICS sector name (required when healing_pipeline is set).
        sector_distributions: Current cross-sectional distributions for Tier 2/3.
        prior_sector_distributions: Prior-period distributions for Tier 3.
        ticker_history: Field path -> historical values for self-history detection.
        secondary_values: Alternative data source values for L1 correction.
        prior_valid_values: Last known good values for L2 carry-forward.
        sector_ticker_count: Total tickers in sector (for breadth circuit breaker).
        sector_flagged_tickers: Set of tickers already flagged in this sector.

    Returns:
        A bare ``FinancialPeriod`` when no healing pipeline is provided, or a
        ``(FinancialPeriod, HealingResult)`` tuple when healing is enabled.
    """
    current_income = normalize_income_statement(income_raw)
    current_balance = normalize_balance_sheet(balance_raw)
    current_cash_flow = normalize_cash_flow(cashflow_raw)

    prior_income = normalize_income_statement(prior_income_raw) if prior_income_raw else None
    prior_balance = normalize_balance_sheet(prior_balance_raw) if prior_balance_raw else None
    prior_cash_flow = normalize_cash_flow(prior_cashflow_raw) if prior_cashflow_raw else None

    period = FinancialPeriod(
        period_end=period_end,
        filing_date=filing_date,
        current_income=current_income,
        prior_income=prior_income,
        current_balance=current_balance,
        prior_balance=prior_balance,
        current_cash_flow=current_cash_flow,
        prior_cash_flow=prior_cash_flow,
    )

    if healing_pipeline is None:
        return period

    healing_result = healing_pipeline.heal(
        period=period,
        sector=sector,
        sector_distributions=sector_distributions or [],
        prior_sector_distributions=prior_sector_distributions or [],
        ticker_history=ticker_history or {},
        secondary_values=secondary_values,
        prior_valid_values=prior_valid_values,
        sector_ticker_count=sector_ticker_count,
        sector_flagged_tickers=sector_flagged_tickers,
    )

    return healing_result.period, healing_result


def build_asset_profile(
    ticker: str,
    name: str,
    sector: str,
    market_cap: Decimal,
    avg_daily_volume: Decimal = Decimal("0"),
    years_of_history: int = 0,
    shares_outstanding: int | None = None,
) -> AssetProfile:
    """Build an AssetProfile engine model from basic metadata.

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL").
        name: Company name (e.g. "Apple Inc.").
        sector: GICS sector string (e.g. "Information Technology").
        market_cap: Market capitalization as a Decimal.
        avg_daily_volume: Average daily dollar volume. Defaults to 0.
        years_of_history: Years of trading history. Defaults to 0.
        shares_outstanding: Total shares outstanding. Defaults to None.

    Returns:
        A populated AssetProfile.

    Raises:
        ValueError: If the sector string does not match any GICSSector value.
    """
    gics_sector = _SECTOR_MAP.get(sector)
    if gics_sector is None:
        valid = ", ".join(sorted(_SECTOR_MAP.keys()))
        raise ValueError(f"Unknown sector: '{sector}'. Valid sectors: {valid}")

    return AssetProfile(
        ticker=ticker,
        name=name,
        sector=gics_sector,
        market_cap=market_cap,
        avg_daily_volume=avg_daily_volume,
        years_of_history=years_of_history,
        shares_outstanding=shares_outstanding,
    )


def compute_raw_factor_scores(
    ticker: str,
    period: FinancialPeriod,
    profile: AssetProfile,
    price_bars_raw: list[dict],
    earnings_raw: list[dict],
    history: FinancialHistory | None = None,
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
        history: Optional multi-period history for temporal factors
                 (roic_trend, gross_margin_stability).

    Returns:
        A RawScoringResult with unranked factor scores.
    """
    market_cap = profile.market_cap

    # --- Step 1: Elimination filters ---
    pipeline_result = run_elimination_filters(period, profile)
    filter_results = pipeline_result.results

    # --- Step 2: Quality factors ---
    quality_scores = [
        gross_profitability(period),
        roic_wacc_spread(period),
        sloan_accrual_ratio(period),
        piotroski_f_score(period),
        fcf_conversion(period),
    ]
    if history is not None:
        quality_scores.append(roic_trend(history))
        quality_scores.append(gross_margin_stability(history))

    # --- Step 3: Value factors ---
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
    # Scenario IV adapter: ScenarioIV -> FactorScore
    if profile.shares_outstanding and profile.shares_outstanding > 0:
        _fcf = float(period.current_cash_flow.free_cash_flow)
        if _fcf > 0:
            scenario = compute_scenario_iv(
                base_fcf=_fcf,
                base_growth=0.05,
                wacc=0.10,
                terminal_growth=0.03,
                shares_outstanding=profile.shares_outstanding,
            )
            value_scores.append(
                FactorScore(
                    name="scenario_iv",
                    raw_value=scenario.weighted_iv,
                    percentile_rank=0.0,
                    detail=(
                        f"bear={scenario.bear_iv:.2f} "
                        f"base={scenario.base_iv:.2f} "
                        f"bull={scenario.bull_iv:.2f}"
                    ),
                )
            )

    # --- Step 4: Momentum factors ---
    bars: list[PriceBar] = [normalize_price_bar(b) for b in price_bars_raw]
    surprises = normalize_earnings_list(earnings_raw)

    momentum_scores: list[FactorScore] = [
        multi_horizon_momentum(bars),
    ]
    # Only include SUE when real earnings data exists. When all tickers
    # have no earnings, every SUE is 0.0 → all get 50th percentile,
    # dragging momentum averages down and capping composites below
    # conviction thresholds (same issue as the removed placeholders).
    if earnings_raw:
        momentum_scores.append(sue_score(surprises))

    # Sentiment: stub with neutral value (LLM pipeline not yet wired)
    momentum_scores.append(sentiment_score(score=0.0))

    # --- Step 5: Growth factors ---
    growth_scores: list[FactorScore] = []
    if history is not None and len(history.periods) >= 2:
        growth_scores.append(revenue_cagr(history))
        growth_scores.append(incremental_roic(history))

    # Rule of 40: revenue growth + FCF margin
    revenue = float(period.current_income.revenue)
    if revenue > 0:
        fcf = float(period.current_cash_flow.free_cash_flow)
        fcf_margin = fcf / revenue
        # Derive revenue growth from current vs prior period
        rev_growth_rate = 0.0
        if period.prior_income is not None:
            prior_rev = float(period.prior_income.revenue)
            if prior_rev > 0:
                rev_growth_rate = (revenue - prior_rev) / prior_rev
        growth_scores.append(rule_of_40(rev_growth_rate, fcf_margin))

    # Runway score: sub-industry revenue not available, use None (neutral 0.5)
    growth_scores.append(runway_score(period.current_income.revenue, None))

    # --- Step 6: Classify growth stage ---
    growth_stage = classify_growth_stage(period, profile)

    return RawScoringResult(
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
        for list_attr in ("quality_scores", "value_scores", "momentum_scores", "growth_scores"):
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
        # First pass: compute composite without price targets to get composite_tier
        base_composite = compute_composite_score(
            ticker=r.ticker,
            quality_scores=r.quality_scores,
            value_scores=r.value_scores,
            momentum_scores=r.momentum_scores,
            growth_scores=r.growth_scores,
            filters_passed=r.filter_results,
            growth_stage=r.growth_stage,
        )

        # Second pass: compute price targets using the derived composite_tier
        price_targets = None
        if r.period is not None and r.profile is not None:
            price_targets = compute_price_targets(
                period=r.period,
                profile=r.profile,
                price_bars=r.price_bars,
                conviction_level=base_composite.composite_tier,
                growth_stage=r.growth_stage,
            )

        if price_targets is not None:
            # Re-compute with price targets attached
            composite = compute_composite_score(
                ticker=r.ticker,
                quality_scores=r.quality_scores,
                value_scores=r.value_scores,
                momentum_scores=r.momentum_scores,
                growth_scores=r.growth_scores,
                filters_passed=r.filter_results,
                growth_stage=r.growth_stage,
                price_targets=price_targets,
            )
        else:
            composite = base_composite

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


def run_scoring_pipeline(
    ticker: str,
    period: FinancialPeriod,
    profile: AssetProfile,
    price_bars_raw: list[dict],
    earnings_raw: list[dict],
    history: FinancialHistory | None = None,
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
        history: Optional multi-period history for temporal factors.

    Returns:
        A CompositeScore (with single-ticker percentile ranks).
    """
    raw = compute_raw_factor_scores(
        ticker, period, profile, price_bars_raw, earnings_raw, history=history
    )
    composites = rank_and_compute_composites([raw])
    return composites[0]


def build_financial_history_from_rows(
    ticker: str,
    rows: list[dict],
) -> FinancialHistory:
    """Build a FinancialHistory from multiple DB rows (sorted oldest-first).

    Each row should have: period_end, filing_date, income_statement, balance_sheet, cash_flow.
    """
    sorted_rows = sorted(rows, key=lambda r: r["period_end"])
    periods = []
    for i, row in enumerate(sorted_rows):
        prior_row = sorted_rows[i - 1] if i > 0 else None
        period = build_financial_period(
            income_raw=row.get("income_statement") or {},
            balance_raw=row.get("balance_sheet") or {},
            cashflow_raw=row.get("cash_flow") or {},
            period_end=row["period_end"],
            filing_date=row.get("filing_date", ""),
            prior_income_raw=(prior_row.get("income_statement") or {}) if prior_row else None,
            prior_balance_raw=(prior_row.get("balance_sheet") or {}) if prior_row else None,
            prior_cashflow_raw=(prior_row.get("cash_flow") or {}) if prior_row else None,
        )
        periods.append(period)
    return FinancialHistory(ticker=ticker, periods=periods)
