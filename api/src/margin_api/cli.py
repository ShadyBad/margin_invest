"""CLI for seeding financial data from yfinance into the database.

Fetches fundamentals, price history, and earnings for ~50 S&P 500 tickers
across all 11 GICS sectors and upserts them into the database.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
import sys
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import yfinance
from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider
from margin_engine.ingestion.rate_limiter import RateLimiterRegistry
from sqlalchemy import select

from margin_api.db.models import Asset, FinancialData
from margin_api.db.session import get_engine, get_session_factory

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


async def run_seed(tickers: list[str] | None = None) -> None:
    """Seed financial data for all (or specified) tickers.

    Creates the provider, rate limiter, and DB session, then iterates
    through tickers and calls :func:`seed_ticker_data` for each one.
    """
    if tickers is None:
        tickers = SP500_TICKERS

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
        async with session_factory() as session:
            result = await session.execute(select(Asset.ticker))
            tickers = [row[0] for row in result.all()]

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
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point with argparse."""
    parser = argparse.ArgumentParser(
        prog="margin-cli",
        description="Margin Invest data management CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    seed_parser = subparsers.add_parser("seed", help="Seed financial data from yfinance")
    seed_parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Specific tickers to seed (defaults to ~50 S&P 500 tickers)",
    )

    score_parser = subparsers.add_parser("score", help="Score all seeded tickers")
    score_parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Specific tickers to score (defaults to all seeded tickers)",
    )

    args = parser.parse_args()

    if args.command == "seed":
        asyncio.run(run_seed(tickers=args.tickers))
    elif args.command == "score":
        asyncio.run(run_scoring(tickers=args.tickers))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
