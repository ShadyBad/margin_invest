"""Scoring service — bridge between raw JSONB financial data and the engine.

Converts raw JSON dicts (as stored in the database) into engine Pydantic models,
then runs the full scoring pipeline: elimination filters -> factor scoring ->
growth stage classification -> composite scoring.
"""

from __future__ import annotations

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
from margin_engine.models.scoring import CompositeScore, FactorScore
from margin_engine.scoring.classifier import classify_growth_stage
from margin_engine.scoring.composite import compute_composite_score
from margin_engine.scoring.filters.pipeline import run_elimination_filters
from margin_engine.scoring.quantitative.accrual_ratio import sloan_accrual_ratio
from margin_engine.scoring.quantitative.acquirers_multiple import acquirers_multiple
from margin_engine.scoring.quantitative.dcf_mos import dcf_margin_of_safety
from margin_engine.scoring.quantitative.ev_fcf import ev_fcf
from margin_engine.scoring.quantitative.f_score import piotroski_f_score
from margin_engine.scoring.quantitative.gross_profitability import gross_profitability
from margin_engine.scoring.quantitative.price_momentum import price_momentum
from margin_engine.scoring.quantitative.roic_wacc import roic_wacc_spread
from margin_engine.scoring.quantitative.sentiment_score import sentiment_score
from margin_engine.scoring.quantitative.shareholder_yield import shareholder_yield
from margin_engine.scoring.quantitative.sue import sue_score

# Sector string -> GICSSector mapping for lookups
_SECTOR_MAP: dict[str, GICSSector] = {s.value: s for s in GICSSector}


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


def run_scoring_pipeline(
    ticker: str,
    period: FinancialPeriod,
    profile: AssetProfile,
    price_bars_raw: list[dict],
    earnings_raw: list[dict],
) -> CompositeScore:
    """Run the full scoring pipeline: filters -> factors -> composite.

    Steps:
        1. Run elimination filters (fail-fast check).
        2. Compute 4 quality factor scores.
        3. Compute 4 value factor scores (dcf_margin_of_safety uses
           conservative defaults: growth_rate=0.05, discount_rate=0.10).
        4. Compute 5 momentum factor scores — price_momentum and sue_score
           from real data; sentiment, insider_cluster, and institutional_accumulation
           use zero-value placeholders (data not yet available).
        5. Classify growth stage.
        6. Compute weighted composite score.

    Args:
        ticker: Stock ticker symbol.
        period: FinancialPeriod with current (and optionally prior) data.
        profile: AssetProfile with metadata and sector.
        price_bars_raw: List of raw price bar dicts for price momentum.
        earnings_raw: List of raw earnings surprise dicts for SUE score.

    Returns:
        A fully populated CompositeScore.
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
    # Convert raw price bars to PriceBar models
    bars: list[PriceBar] = [normalize_price_bar(b) for b in price_bars_raw]

    # Convert raw earnings to EarningsSurprise models
    surprises = normalize_earnings_list(earnings_raw)

    momentum_scores: list[FactorScore] = [
        price_momentum(bars),
        sue_score(surprises),
        # Placeholders for data we don't have yet
        sentiment_score(score=0.0),
        FactorScore(
            name="insider_cluster",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="No insider transaction data available",
        ),
        FactorScore(
            name="institutional_accumulation",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="No institutional holding data available",
        ),
    ]

    # --- Step 5: Classify growth stage ---
    growth_stage = classify_growth_stage(period, profile)

    # --- Step 6: Composite score ---
    return compute_composite_score(
        ticker=ticker,
        quality_scores=quality_scores,
        value_scores=value_scores,
        momentum_scores=momentum_scores,
        filters_passed=filter_results,
        growth_stage=growth_stage,
    )
