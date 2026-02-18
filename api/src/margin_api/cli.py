"""CLI for seeding financial data from yfinance into the database.

Fetches fundamentals, price history, and earnings for tickers defined
in the active universe snapshot and upserts them into the database.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yfinance
from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider
from margin_engine.ingestion.rate_limiter import RateLimiterRegistry
from sqlalchemy import select

from margin_api.db.models import Asset, FinancialData
from margin_api.db.session import get_engine, get_session_factory
from margin_api.services.universe import activate_universe, get_active_snapshot

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SP500_TICKERS: list[str] = [
    # Tech
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "AVGO", "ORCL", "CRM", "AMD",
    # Healthcare
    "UNH", "JNJ", "LLY", "ABBV", "MRK",
    # Financials
    "JPM", "V", "MA", "BAC", "GS",
    # Consumer Staples
    "PG", "KO", "PEP", "COST", "WMT",
    # Consumer Discretionary
    "TSLA", "HD", "NKE", "SBUX", "MCD", "TJX",
    # Energy
    "XOM", "CVX",
    # Industrials
    "CAT", "GE", "HON", "UNP", "RTX",
    # Communication Services
    "NFLX", "DIS", "CMCSA",
    # Utilities
    "NEE", "SO", "DUK",
    # Materials
    "LIN", "APD", "SHW",
    # Real Estate
    "PLD", "AMT",
]

SECTOR_MAP: dict[str, str] = {
    "Technology": "Information Technology",
    "Healthcare": "Health Care",
    "Financial Services": "Financials",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Energy": "Energy",
    "Industrials": "Industrials",
    "Basic Materials": "Materials",
    "Real Estate": "Real Estate",
    "Utilities": "Utilities",
    "Communication Services": "Communication Services",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sanitize_for_json(obj: Any) -> Any:
    """Replace NaN/Inf floats with None so the data is valid JSON for PostgreSQL JSONB."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------


async def seed_ticker_data(
    *,
    ticker: str,
    provider: YFinanceProvider,
    session,
) -> bool:
    """Fetch data for a single ticker and upsert it into the database.

    Returns True on success, False on failure.
    """
    try:
        # Fetch data from yfinance provider
        fundamentals = provider.fetch_fundamentals(ticker)
        price_history = provider.fetch_price_history(ticker, days=365)
        earnings = provider.fetch_earnings(ticker)

        # Get asset info from yfinance
        yf_ticker = yfinance.Ticker(ticker)
        info = yf_ticker.info or {}

        name = info.get("shortName") or info.get("longName") or ticker
        raw_sector = info.get("sector", "")
        sector = SECTOR_MAP.get(raw_sector, raw_sector)
        sub_industry = info.get("industry")
        country = info.get("country")
        market_cap = Decimal(str(info.get("marketCap", 0)))
        shares_outstanding = info.get("sharesOutstanding")

        # Reject foreign-domiciled assets
        if country and country != "United States":
            logger.info("  SKIP %s — foreign domicile (%s)", ticker, country)
            return False

        # Upsert Asset row
        result = await session.execute(select(Asset).where(Asset.ticker == ticker))
        asset = result.scalar_one_or_none()

        if asset is None:
            asset = Asset(
                ticker=ticker,
                name=name,
                sector=sector,
                sub_industry=sub_industry,
                country=country,
                market_cap=market_cap,
                shares_outstanding=shares_outstanding,
            )
            session.add(asset)
            await session.flush()  # Get the id
        else:
            asset.name = name
            asset.sector = sector
            asset.sub_industry = sub_industry
            asset.country = country
            asset.market_cap = market_cap
            asset.shares_outstanding = shares_outstanding

        # Build financial data
        today_iso = datetime.now(UTC).strftime("%Y-%m-%d")

        income_statement = _sanitize_for_json(
            fundamentals.raw_data.get("income_statement") if fundamentals.success else None
        )
        balance_sheet = _sanitize_for_json(
            fundamentals.raw_data.get("balance_sheet") if fundamentals.success else None
        )
        cash_flow = _sanitize_for_json(
            fundamentals.raw_data.get("cash_flow") if fundamentals.success else None
        )
        price_data = _sanitize_for_json(
            price_history.raw_data if price_history.success else None
        )
        earnings_data = _sanitize_for_json(
            earnings.raw_data if earnings.success else None
        )

        # Upsert FinancialData row (by asset_id + period_end)
        fd_result = await session.execute(
            select(FinancialData).where(
                FinancialData.asset_id == asset.id,
                FinancialData.period_end == today_iso,
            )
        )
        fd = fd_result.scalar_one_or_none()

        if fd is None:
            fd = FinancialData(
                asset_id=asset.id,
                period_end=today_iso,
                filing_date=today_iso,
                income_statement=income_statement,
                balance_sheet=balance_sheet,
                cash_flow=cash_flow,
                price_history=price_data,
                earnings_data=earnings_data,
                source="yfinance",
                fetched_at=datetime.now(UTC),
            )
            session.add(fd)
        else:
            fd.income_statement = income_statement
            fd.balance_sheet = balance_sheet
            fd.cash_flow = cash_flow
            fd.price_history = price_data
            fd.earnings_data = earnings_data
            fd.fetched_at = datetime.now(UTC)

        await session.commit()
        return True

    except Exception:
        logger.exception("Failed to seed data for %s", ticker)
        await session.rollback()
        return False


async def _get_universe_tickers() -> list[str]:
    """Read ticker list from the active universe snapshot."""
    engine = get_engine()
    session_factory = get_session_factory(engine)
    async with session_factory() as session:
        snapshot = await get_active_snapshot(session)
    if snapshot is None:
        logger.error("No active universe snapshot. Run 'universe activate' first.")
        logger.error("Or use --tickers to seed a specific subset.")
        sys.exit(1)
    logger.info("Using universe v%s (%d tickers)", snapshot.version, snapshot.ticker_count)
    return list(snapshot.tickers)


async def run_seed(tickers: list[str] | None = None) -> None:
    """Seed financial data for all (or specified) tickers.

    Creates the provider, rate limiter, and DB session, then iterates
    through tickers and calls :func:`seed_ticker_data` for each one.
    """
    if tickers is None:
        tickers = await _get_universe_tickers()

    provider = YFinanceProvider()
    registry = RateLimiterRegistry()
    registry.register("yfinance", provider.info.requests_per_minute)
    limiter = registry.get("yfinance")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    successes = 0
    failures = 0
    total = len(tickers)

    for i, ticker in enumerate(tickers, start=1):
        limiter.wait_and_acquire()
        logger.info("[%d/%d] Seeding %s...", i, total, ticker)

        async with session_factory() as session:
            ok = await seed_ticker_data(ticker=ticker, provider=provider, session=session)

        if ok:
            successes += 1
            logger.info("  %s OK", ticker)
        else:
            failures += 1
            logger.error("  %s FAILED", ticker)

    logger.info("Seed complete: %d succeeded, %d failed out of %d tickers", successes, failures, total)


# ---------------------------------------------------------------------------
# Scoring logic
# ---------------------------------------------------------------------------


async def run_scoring(tickers: list[str] | None = None) -> None:
    """Score all (or specified) tickers from DB data.

    Two-pass approach:
      1. Compute raw factor scores for each ticker (percentile_rank=0.0).
      2. Rank across sector peers, compute composites, and persist.
    """
    from collections import defaultdict

    from margin_api.db.models import FinancialData, Score
    from margin_api.services.scoring import (
        build_asset_profile,
        build_financial_period,
        compute_raw_factor_scores,
        rank_and_compute_composites,
    )

    engine = get_engine()
    session_factory = get_session_factory(engine)

    if tickers is None:
        tickers = await _get_universe_tickers()

    if not tickers:
        logger.warning("No tickers found in database. Run 'seed' first.")
        return

    total = len(tickers)

    # --- Pass 1: Compute raw factor scores ---
    raw_results = []
    asset_ids: dict[str, int] = {}

    for i, ticker in enumerate(tickers, start=1):
        async with session_factory() as session:
            result = await session.execute(select(Asset).where(Asset.ticker == ticker))
            asset = result.scalar_one_or_none()
            if asset is None:
                logger.warning("[%d/%d] SKIP %s — no asset", i, total, ticker)
                continue

            result = await session.execute(
                select(FinancialData)
                .where(FinancialData.asset_id == asset.id)
                .order_by(FinancialData.fetched_at.desc())
                .limit(1)
            )
            fin_data = result.scalar_one_or_none()
            if fin_data is None:
                logger.warning("[%d/%d] SKIP %s — no financial data", i, total, ticker)
                continue

            try:
                period = build_financial_period(
                    income_raw=fin_data.income_statement or {},
                    balance_raw=fin_data.balance_sheet or {},
                    cashflow_raw=fin_data.cash_flow or {},
                    period_end=fin_data.period_end,
                    filing_date=fin_data.filing_date,
                )
                profile = build_asset_profile(
                    ticker=asset.ticker,
                    name=asset.name,
                    sector=asset.sector,
                    market_cap=asset.market_cap,
                    shares_outstanding=asset.shares_outstanding,
                )

                # price_history is stored as {"bars": [...]}
                price_data = fin_data.price_history or {}
                price_bars = price_data.get("bars", []) if isinstance(price_data, dict) else []

                raw = compute_raw_factor_scores(
                    ticker=ticker,
                    period=period,
                    profile=profile,
                    price_bars_raw=price_bars,
                    earnings_raw=fin_data.earnings_data or [],
                )
                raw_results.append(raw)
                asset_ids[ticker] = asset.id
                logger.info("[%d/%d] Raw scores: %s", i, total, ticker)
            except Exception as e:
                logger.error("[%d/%d] FAILED %s: %s", i, total, ticker, e)

    if not raw_results:
        logger.warning("No tickers could be scored.")
        await engine.dispose()
        return

    # --- Pass 2: Rank across sector peers and compute composites ---
    logger.info("Ranking %d tickers across sector peers...", len(raw_results))
    composites = rank_and_compute_composites(raw_results)

    # --- Pass 3: Persist scores ---
    successes = 0
    async with session_factory() as session:
        for composite in composites:
            score = Score(
                asset_id=asset_ids[composite.ticker],
                composite_percentile=composite.composite_percentile,
                composite_raw_score=composite.composite_raw_score,
                conviction_level=composite.conviction_level.value,
                signal=composite.signal.value,
                quality_percentile=composite.quality.average_percentile,
                value_percentile=composite.value.average_percentile,
                momentum_percentile=composite.momentum.average_percentile,
                data_coverage=composite.data_coverage,
                growth_stage=composite.growth_stage.value if composite.growth_stage else None,
                score_detail=composite.model_dump(mode="json"),
                scored_at=datetime.now(UTC),
                intrinsic_value=composite.intrinsic_value,
                buy_price=composite.buy_price,
                sell_price=composite.sell_price,
                actual_price=composite.actual_price,
                price_target_invalid_reason=composite.price_target_invalid_reason,
                opportunity_type=composite.opportunity_type.value if composite.opportunity_type else None,
                winning_track=composite.winning_track,
                asymmetry_ratio=composite.asymmetry_ratio,
                max_position_pct=composite.max_position_pct,
                timing_signal=composite.timing_signal,
            )
            session.add(score)
            successes += 1
        await session.commit()

    # Summary
    levels = defaultdict(int)
    for c in composites:
        levels[c.conviction_level.value] += 1
    logger.info("Scoring complete: %d scored out of %d tickers", successes, total)
    logger.info("Conviction levels:")
    for level in ("exceptional", "high", "watchlist", "none"):
        if levels[level]:
            logger.info("  %s: %d", level, levels[level])
    await engine.dispose()


# ---------------------------------------------------------------------------
# V3 Scoring logic
# ---------------------------------------------------------------------------


async def run_scoring_v3(tickers: list[str] | None = None, cape: float | None = None) -> None:
    """Score tickers using the v3 gate cascade pipeline."""
    from margin_api.data.fred_client import fetch_shiller_cape
    from margin_api.db.models import V3Score
    from margin_api.services.scoring import build_asset_profile, build_financial_history_from_rows
    from margin_engine.scoring.v3_pipeline import TickerV3Data, score_universe_v3

    engine = get_engine()
    session_factory = get_session_factory(engine)

    if tickers is None:
        tickers = await _get_universe_tickers()
    if not tickers:
        logger.warning("No tickers found. Run 'seed' first.")
        return

    # Fetch CAPE
    if cape is None:
        cape = await fetch_shiller_cape()
    logger.info("Using Shiller CAPE: %.1f", cape)

    # Build TickerV3Data for each ticker
    ticker_data_list: list[TickerV3Data] = []
    total = len(tickers)
    asset_ids: dict[str, int] = {}

    for i, ticker in enumerate(tickers, start=1):
        async with session_factory() as session:
            # Fetch asset
            result = await session.execute(select(Asset).where(Asset.ticker == ticker))
            asset = result.scalar_one_or_none()
            if not asset:
                logger.warning("[%d/%d] SKIP %s — no asset", i, total, ticker)
                continue

            # Fetch last 5 years of financial data
            result = await session.execute(
                select(FinancialData)
                .where(FinancialData.asset_id == asset.id)
                .order_by(FinancialData.period_end.desc())
                .limit(5)
            )
            fin_rows = result.scalars().all()
            if not fin_rows:
                logger.warning("[%d/%d] SKIP %s — no financial data", i, total, ticker)
                continue

            try:
                rows = [
                    {
                        "period_end": fd.period_end,
                        "filing_date": fd.filing_date,
                        "income_statement": fd.income_statement or {},
                        "balance_sheet": fd.balance_sheet or {},
                        "cash_flow": fd.cash_flow or {},
                    }
                    for fd in fin_rows
                ]
                history = build_financial_history_from_rows(ticker, rows)
                profile = build_asset_profile(
                    ticker=asset.ticker,
                    name=asset.name,
                    sector=asset.sector,
                    market_cap=asset.market_cap,
                    shares_outstanding=asset.shares_outstanding,
                )
                latest = history.periods[-1]

                # Get current price from most recent price bar
                latest_fd = max(fin_rows, key=lambda fd: fd.period_end)
                price_data = latest_fd.price_history or {}
                bars = price_data.get("bars", []) if isinstance(price_data, dict) else []
                current_price = (
                    float(bars[-1]["close"])
                    if bars
                    else float(profile.market_cap) / max(asset.shares_outstanding or 1, 1)
                )

                # FCF per share
                fcf = float(latest.current_cash_flow.free_cash_flow)
                shares = asset.shares_outstanding or 1
                fcf_ps = fcf / shares

                # DCF IV: compute intrinsic value from DCF margin of safety
                from margin_engine.scoring.quantitative.dcf_mos import dcf_margin_of_safety

                dcf_result = dcf_margin_of_safety(
                    latest, profile.market_cap, growth_rate=0.05, discount_rate=0.10
                )
                # MoS = (IV - mktcap) / IV  =>  IV = mktcap / (1 - MoS)
                if dcf_result.raw_value < 1.0 and dcf_result.raw_value != 0.0:
                    dcf_iv = float(profile.market_cap) / (1.0 - dcf_result.raw_value) / shares
                else:
                    dcf_iv = current_price

                td = TickerV3Data(
                    ticker=ticker,
                    history=history,
                    latest_period=latest,
                    profile=profile,
                    current_price=current_price,
                    current_fcf_per_share=fcf_ps,
                    sustainable_growth_rate=0.08,  # default
                    buyback_yield=None,
                    insider_ownership_pct=None,
                    sbc_pct=None,
                    recent_acquisition_count=0,
                    insider_percentile=50.0,
                    institutional_percentile=50.0,
                    sue_percentile=50.0,
                    momentum_percentile=50.0,
                    dcf_iv=dcf_iv,
                )
                ticker_data_list.append(td)
                asset_ids[ticker] = asset.id
                logger.info("[%d/%d] Prepared: %s", i, total, ticker)
            except Exception as e:
                logger.error("[%d/%d] FAILED %s: %s", i, total, ticker, e)

    if not ticker_data_list:
        logger.warning("No tickers could be prepared for v3 scoring.")
        await engine.dispose()
        return

    # Run v3 pipeline
    results = score_universe_v3(ticker_data_list, shiller_cape=cape)

    # Persist results
    from margin_engine.scoring.market_regime import detect_regime

    regime = detect_regime(cape)
    successes = 0
    async with session_factory() as session:
        for v3r in results:
            if v3r.ticker not in asset_ids:
                continue
            score = V3Score(
                asset_id=asset_ids[v3r.ticker],
                opportunity_type=v3r.opportunity_type,
                conviction=v3r.conviction.value,
                track_a=v3r.track_a.model_dump(mode="json"),
                track_b=v3r.track_b.model_dump(mode="json"),
                timing_signal=v3r.timing_signal,
                max_position_pct=v3r.max_position_pct,
                regime=regime.value,
                composite_score=max(v3r.track_a.score, v3r.track_b.score),
            )
            session.add(score)
            successes += 1
        await session.commit()

    logger.info("V3 scoring complete: %d scored out of %d tickers", successes, total)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Ingest precondition helpers
# ---------------------------------------------------------------------------


def validate_ingest_preconditions(
    active_snapshot: object | None,
    tickers_override: list[str] | None,
) -> None:
    """Validate that ingestion preconditions are met."""
    if tickers_override:
        return  # Explicit subset bypasses snapshot check
    if active_snapshot is None:
        raise SystemExit(
            "No active universe snapshot. Run 'universe activate' first.\n"
            "Or use --tickers to ingest a specific subset."
        )


def determine_run_type(tickers_override: list[str] | None) -> str:
    """Determine whether this is a 'full' or 'subset' run."""
    return "subset" if tickers_override else "full"


# ---------------------------------------------------------------------------
# Universe activation
# ---------------------------------------------------------------------------


def run_universe_generate(output: str | None = None) -> None:
    """Screen Yahoo Finance for US-domiciled equities and generate universe.yaml.

    Two layers of foreign-asset filtering:
      1. Currency filter (here): drops tickers with non-USD financialCurrency.
         Free — uses data already in the screener response.
      2. Country guard (in seed_ticker_data): rejects tickers whose yfinance
         country != "United States" at insert time. Reliable — one request
         per ticker with rate limiting.
    """
    from margin_engine.universe.screener import (
        US_EXCHANGES,
        generate_universe_yaml,
        screen_us_equities,
    )

    excluded_sectors = ["Financial Services", "Real Estate"]
    min_market_cap = 0
    min_avg_volume = 0

    logger.info("Screening Yahoo Finance for US-domiciled equities...")
    logger.info("  Exchanges: %s", ", ".join(US_EXCHANGES))
    logger.info("  Excluded sectors: %s", ", ".join(excluded_sectors))

    raw = screen_us_equities(
        min_market_cap=min_market_cap,
        min_avg_volume=min_avg_volume,
        excluded_sectors=excluded_sectors,
        exchanges=US_EXCHANGES,
        us_domiciled_only=True,
    )
    tickers = sorted(set(r["ticker"] for r in raw))
    logger.info("Found %d tickers after currency filter", len(tickers))
    logger.info("Note: remaining foreign tickers will be rejected during seed")

    yaml_content = generate_universe_yaml(
        tickers=tickers,
        excluded_sectors=excluded_sectors,
        min_market_cap=min_market_cap,
        min_avg_volume=min_avg_volume,
        exchanges=US_EXCHANGES,
        description="US-domiciled equities, excluding financials and REITs",
    )

    if output is None:
        output = str(Path(__file__).resolve().parents[3] / "engine" / "universe.yaml")

    Path(output).write_text(yaml_content)
    logger.info("Written to %s", output)


async def run_universe_activate(config_path: str | None = None) -> None:
    """Activate a universe from a YAML config file."""
    if config_path is None:
        # Default to engine/universe.yaml relative to repo root
        candidate = Path(__file__).resolve().parents[3] / "engine" / "universe.yaml"
        if not candidate.exists():
            logger.error("Default universe config not found at %s", candidate)
            logger.error("Use --config to specify a path.")
            sys.exit(1)
        config_path = str(candidate)

    path = Path(config_path)
    if not path.exists():
        logger.error("Config file not found: %s", path)
        sys.exit(1)

    engine = get_engine()
    session_factory = get_session_factory(engine)
    async with session_factory() as session:
        snapshot = await activate_universe(session, path)
    await engine.dispose()

    logger.info("Activated universe v%s", snapshot.version)
    logger.info("  Tickers: %d", snapshot.ticker_count)
    logger.info("  Hash: %s", snapshot.config_hash)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


async def run_backfill_country() -> None:
    """Backfill country field for existing assets using yfinance.

    Fetches country from yfinance Ticker.info for all assets where
    country is NULL. Uses rate limiting to avoid API throttling.
    """
    provider = YFinanceProvider()
    registry = RateLimiterRegistry()
    registry.register("yfinance", provider.info.requests_per_minute)
    limiter = registry.get("yfinance")

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Get all assets missing country
    async with session_factory() as session:
        result = await session.execute(
            select(Asset).where(Asset.country.is_(None)).order_by(Asset.ticker)
        )
        assets = result.scalars().all()

    total = len(assets)
    logger.info("Backfilling country for %d assets...", total)

    updated = 0
    for i, asset in enumerate(assets, start=1):
        limiter.wait_and_acquire()
        try:
            info = yfinance.Ticker(asset.ticker).info or {}
            country = info.get("country")
            if country:
                async with session_factory() as session:
                    result = await session.execute(
                        select(Asset).where(Asset.id == asset.id)
                    )
                    db_asset = result.scalar_one()
                    db_asset.country = country
                    await session.commit()
                updated += 1
                logger.info("[%d/%d] %s → %s", i, total, asset.ticker, country)
            else:
                logger.info("[%d/%d] %s → no country info", i, total, asset.ticker)
        except Exception as e:
            logger.warning("[%d/%d] %s failed: %s", i, total, asset.ticker, e)

    logger.info("Backfill complete: %d/%d updated", updated, total)
    await engine.dispose()


async def run_pipeline(tickers: list[str] | None = None) -> None:
    """Run the full pipeline: seed → score."""
    logger.info("=== Step 1/2: Seeding financial data ===")
    await run_seed(tickers=tickers)
    logger.info("=== Step 2/2: Scoring tickers ===")
    await run_scoring(tickers=tickers)
    logger.info("=== Pipeline complete ===")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point with argparse."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    parser = argparse.ArgumentParser(
        prog="margin-cli",
        description="Margin Invest data management CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    # universe subcommands
    universe_parser = subparsers.add_parser("universe", help="Universe management")
    universe_sub = universe_parser.add_subparsers(dest="universe_command")

    generate_parser = universe_sub.add_parser(
        "generate", help="Screen Yahoo Finance and generate universe.yaml"
    )
    generate_parser.add_argument(
        "--output", default=None, help="Output path (defaults to engine/universe.yaml)",
    )

    activate_parser = universe_sub.add_parser("activate", help="Activate universe from YAML")
    activate_parser.add_argument(
        "--config",
        default=None,
        help="Path to universe YAML (defaults to engine/universe.yaml)",
    )

    # seed
    seed_parser = subparsers.add_parser("seed", help="Seed financial data from yfinance")
    seed_parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Specific tickers to seed (defaults to active universe)",
    )

    # score
    score_parser = subparsers.add_parser("score", help="Score tickers")
    score_parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Specific tickers to score (defaults to active universe)",
    )

    # score-v3
    score_v3_parser = subparsers.add_parser(
        "score-v3", help="Score tickers using v3 conviction engine"
    )
    score_v3_parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Specific tickers to score (defaults to active universe)",
    )
    score_v3_parser.add_argument(
        "--cape",
        type=float,
        default=None,
        help="Shiller CAPE override (fetches from FRED if omitted)",
    )

    # backfill-country
    subparsers.add_parser(
        "backfill-country",
        help="Backfill country field for assets missing it (from yfinance)",
    )

    # pipeline (seed + score in one go)
    pipeline_parser = subparsers.add_parser("pipeline", help="Run full pipeline: seed → score")
    pipeline_parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Specific tickers (defaults to active universe)",
    )

    args = parser.parse_args()

    if args.command == "universe":
        if args.universe_command == "generate":
            run_universe_generate(output=args.output)
        elif args.universe_command == "activate":
            asyncio.run(run_universe_activate(config_path=args.config))
        else:
            universe_parser.print_help()
            sys.exit(1)
    elif args.command == "backfill-country":
        asyncio.run(run_backfill_country())
    elif args.command == "seed":
        asyncio.run(run_seed(tickers=args.tickers))
    elif args.command == "score":
        asyncio.run(run_scoring(tickers=args.tickers))
    elif args.command == "score-v3":
        asyncio.run(run_scoring_v3(tickers=args.tickers, cape=args.cape))
    elif args.command == "pipeline":
        asyncio.run(run_pipeline(tickers=args.tickers))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
