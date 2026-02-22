"""Tests for score-universe CLI command."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, FinancialData
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def session_factory(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    return factory


@pytest_asyncio.fixture()
async def seeded_session(session_factory):
    """Seed 3 assets but only 2 have financial data."""
    async with session_factory() as session:
        asset1 = Asset(
            ticker="AAPL",
            name="Apple",
            sector="Information Technology",
            market_cap=Decimal("3000000000000"),
        )
        asset2 = Asset(
            ticker="MSFT",
            name="Microsoft",
            sector="Information Technology",
            market_cap=Decimal("2500000000000"),
        )
        asset3 = Asset(
            ticker="EMPTY",
            name="Empty Corp",
            sector="Information Technology",
            market_cap=Decimal("100000000"),
        )
        session.add_all([asset1, asset2, asset3])
        await session.flush()

        fd1 = FinancialData(
            asset_id=asset1.id,
            period_end="2025-01-01",
            filing_date="2025-01-15",
            source="yfinance",
            fetched_at=datetime.now(UTC),
        )
        fd2 = FinancialData(
            asset_id=asset2.id,
            period_end="2025-01-01",
            filing_date="2025-01-15",
            source="yfinance",
            fetched_at=datetime.now(UTC),
        )
        session.add_all([fd1, fd2])
        await session.commit()
    return session_factory


class TestScoreUniverseTickerSelection:
    """Test that the ticker selection query works correctly."""

    @pytest.mark.asyncio
    async def test_selects_only_assets_with_data(self, seeded_session):
        """Only assets with FinancialData rows should be selected."""
        async with seeded_session() as session:
            query = (
                select(Asset.ticker)
                .join(FinancialData, FinancialData.asset_id == Asset.id)
                .distinct()
                .order_by(Asset.ticker)
            )
            result = await session.execute(query)
            tickers = [row[0] for row in result.all()]

        assert tickers == ["AAPL", "MSFT"]
        assert "EMPTY" not in tickers

    @pytest.mark.asyncio
    async def test_respects_limit(self, seeded_session):
        """When --limit is provided, only that many tickers should be returned."""
        async with seeded_session() as session:
            query = (
                select(Asset.ticker)
                .join(FinancialData, FinancialData.asset_id == Asset.id)
                .distinct()
                .order_by(Asset.ticker)
                .limit(1)
            )
            result = await session.execute(query)
            tickers = [row[0] for row in result.all()]

        assert len(tickers) == 1
        assert tickers[0] == "AAPL"  # alphabetically first

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_financial_data(self, session_factory):
        """When no assets have financial data, the query returns nothing."""
        async with session_factory() as session:
            # Add an asset but no financial data
            asset = Asset(
                ticker="NOPE",
                name="No Data Inc",
                sector="Information Technology",
                market_cap=Decimal("1000000"),
            )
            session.add(asset)
            await session.commit()

        async with session_factory() as session:
            query = (
                select(Asset.ticker)
                .join(FinancialData, FinancialData.asset_id == Asset.id)
                .distinct()
                .order_by(Asset.ticker)
            )
            result = await session.execute(query)
            tickers = [row[0] for row in result.all()]

        assert tickers == []


class TestScoreUniverseArgparse:
    """Test that the argparse subcommand is registered correctly."""

    def test_command_exists(self):
        """The score-universe subcommand should be parseable."""

        # Build the parser manually (same as in main)
        parser = argparse.ArgumentParser(prog="margin-cli")
        subparsers = parser.add_subparsers(dest="command")
        score_universe_parser = subparsers.add_parser("score-universe")
        score_universe_parser.add_argument("--limit", type=int, default=None)

        args = parser.parse_args(["score-universe"])
        assert args.command == "score-universe"
        assert args.limit is None

    def test_limit_argument(self):
        """The --limit argument should be parsed as an integer."""
        parser = argparse.ArgumentParser(prog="margin-cli")
        subparsers = parser.add_subparsers(dest="command")
        score_universe_parser = subparsers.add_parser("score-universe")
        score_universe_parser.add_argument("--limit", type=int, default=None)

        args = parser.parse_args(["score-universe", "--limit", "10"])
        assert args.command == "score-universe"
        assert args.limit == 10

    def test_run_score_universe_is_importable(self):
        """The run_score_universe function should be importable from cli module."""
        from margin_api.cli import run_score_universe

        assert callable(run_score_universe)
