"""CLI for seeding financial data from yfinance into the database.

Fetches fundamentals, price history, and earnings for ~50 S&P 500 tickers
across all 11 GICS sectors and upserts them into the database.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime
from decimal import Decimal

import yfinance
from sqlalchemy import select

from margin_api.db.models import Asset, FinancialData
from margin_api.db.session import get_engine, get_session_factory
from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider
from margin_engine.ingestion.rate_limiter import RateLimiterRegistry

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
            )
            session.add(asset)
            await session.flush()  # Get the id
        else:
            asset.name = name
            asset.sector = sector
            asset.sub_industry = sub_industry
            asset.market_cap = market_cap

        # Build financial data
        today_iso = datetime.now(UTC).strftime("%Y-%m-%d")

        income_statement = (
            fundamentals.raw_data.get("income_statement") if fundamentals.success else None
        )
        balance_sheet = (
            fundamentals.raw_data.get("balance_sheet") if fundamentals.success else None
        )
        cash_flow = fundamentals.raw_data.get("cash_flow") if fundamentals.success else None
        price_data = price_history.raw_data if price_history.success else None
        earnings_data = earnings.raw_data if earnings.success else None

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

    Loads financial data from the database, runs the engine scoring pipeline,
    and persists scores back to the scores table.
    """
    from margin_api.worker import score_ticker

    engine = get_engine()
    session_factory = get_session_factory(engine)

    if tickers is None:
        async with session_factory() as session:
            result = await session.execute(select(Asset.ticker))
            tickers = [row[0] for row in result.all()]

    if not tickers:
        print("No tickers found in database. Run 'seed' first.")
        return

    successes = 0
    failures = 0
    total = len(tickers)

    for i, ticker in enumerate(tickers, start=1):
        async with session_factory() as session:
            ok = await score_ticker(ticker=ticker, session=session)

        if ok:
            successes += 1
            print(f"[{i}/{total}] Scored {ticker}")
        else:
            failures += 1
            print(f"[{i}/{total}] FAILED {ticker}")

    print(f"\nScoring complete: {successes} scored, {failures} failed out of {total} tickers.")
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
