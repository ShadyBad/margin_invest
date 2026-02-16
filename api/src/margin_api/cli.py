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
        market_cap = Decimal(str(info.get("marketCap", 0)))
        shares_outstanding = info.get("sharesOutstanding")

        # Upsert Asset row
        result = await session.execute(select(Asset).where(Asset.ticker == ticker))
        asset = result.scalar_one_or_none()

        if asset is None:
            asset = Asset(
                ticker=ticker,
                name=name,
                sector=sector,
                sub_industry=sub_industry,
                market_cap=market_cap,
                shares_outstanding=shares_outstanding,
            )
            session.add(asset)
            await session.flush()  # Get the id
        else:
            asset.name = name
            asset.sector = sector
            asset.sub_industry = sub_industry
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
        print("No active universe snapshot. Run 'universe activate' first.")
        print("Or use --tickers to seed a specific subset.")
        sys.exit(1)
    print(f"Using universe v{snapshot.version} ({snapshot.ticker_count} tickers)")
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
        print(f"[{i}/{total}] Seeding {ticker}...")

        async with session_factory() as session:
            ok = await seed_ticker_data(ticker=ticker, provider=provider, session=session)

        if ok:
            successes += 1
            print(f"  {ticker} OK")
        else:
            failures += 1
            print(f"  {ticker} FAILED")

    print(f"\nSeed complete: {successes} succeeded, {failures} failed out of {total} tickers.")


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
        print("No tickers found in database. Run 'seed' first.")
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
                print(f"[{i}/{total}] SKIP {ticker} — no asset")
                continue

            result = await session.execute(
                select(FinancialData)
                .where(FinancialData.asset_id == asset.id)
                .order_by(FinancialData.fetched_at.desc())
                .limit(1)
            )
            fin_data = result.scalar_one_or_none()
            if fin_data is None:
                print(f"[{i}/{total}] SKIP {ticker} — no financial data")
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
                print(f"[{i}/{total}] Raw scores: {ticker}")
            except Exception as e:
                print(f"[{i}/{total}] FAILED {ticker}: {e}")

    if not raw_results:
        print("No tickers could be scored.")
        await engine.dispose()
        return

    # --- Pass 2: Rank across sector peers and compute composites ---
    print(f"\nRanking {len(raw_results)} tickers across sector peers...")
    composites = rank_and_compute_composites(raw_results)

    # --- Pass 3: Persist scores ---
    successes = 0
    async with session_factory() as session:
        for composite in composites:
            score = Score(
                asset_id=asset_ids[composite.ticker],
                composite_percentile=composite.composite_percentile,
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
            )
            session.add(score)
            successes += 1
        await session.commit()

    # Summary
    levels = defaultdict(int)
    for c in composites:
        levels[c.conviction_level.value] += 1
    print(f"\nScoring complete: {successes} scored out of {total} tickers.")
    print("Conviction levels:")
    for level in ("exceptional", "high", "watchlist", "none"):
        if levels[level]:
            print(f"  {level}: {levels[level]}")
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
    """Screen Yahoo Finance for all US equities and generate universe.yaml."""
    from margin_engine.universe.screener import generate_universe_yaml, screen_us_equities

    excluded_sectors = ["Financial Services", "Real Estate"]
    min_market_cap = 0
    min_avg_volume = 0

    print("Screening Yahoo Finance for all US publicly traded equities...")
    print(f"  Excluded sectors: {', '.join(excluded_sectors)}")
    print()

    raw = screen_us_equities(
        min_market_cap=min_market_cap,
        min_avg_volume=min_avg_volume,
        excluded_sectors=excluded_sectors,
    )
    tickers = sorted(set(r["ticker"] for r in raw))
    print(f"\nFound {len(tickers)} tickers after filtering")

    yaml_content = generate_universe_yaml(
        tickers=tickers,
        excluded_sectors=excluded_sectors,
        min_market_cap=min_market_cap,
        min_avg_volume=min_avg_volume,
        description="All US equities, excluding financials and REITs",
    )

    if output is None:
        output = str(Path(__file__).resolve().parents[3] / "engine" / "universe.yaml")

    Path(output).write_text(yaml_content)
    print(f"Written to {output}")


async def run_universe_activate(config_path: str | None = None) -> None:
    """Activate a universe from a YAML config file."""
    if config_path is None:
        # Default to engine/universe.yaml relative to repo root
        candidate = Path(__file__).resolve().parents[3] / "engine" / "universe.yaml"
        if not candidate.exists():
            print(f"Default universe config not found at {candidate}")
            print("Use --config to specify a path.")
            sys.exit(1)
        config_path = str(candidate)

    path = Path(config_path)
    if not path.exists():
        print(f"Config file not found: {path}")
        sys.exit(1)

    engine = get_engine()
    session_factory = get_session_factory(engine)
    async with session_factory() as session:
        snapshot = await activate_universe(session, path)
    await engine.dispose()

    print(f"Activated universe v{snapshot.version}")
    print(f"  Tickers: {snapshot.ticker_count}")
    print(f"  Hash: {snapshot.config_hash}")


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


async def run_pipeline(tickers: list[str] | None = None) -> None:
    """Run the full pipeline: seed → score."""
    print("=== Step 1/2: Seeding financial data ===\n")
    await run_seed(tickers=tickers)
    print("\n=== Step 2/2: Scoring tickers ===\n")
    await run_scoring(tickers=tickers)
    print("\n=== Pipeline complete ===")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point with argparse."""
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
    elif args.command == "seed":
        asyncio.run(run_seed(tickers=args.tickers))
    elif args.command == "score":
        asyncio.run(run_scoring(tickers=args.tickers))
    elif args.command == "pipeline":
        asyncio.run(run_pipeline(tickers=args.tickers))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
