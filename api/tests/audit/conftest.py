"""Shared fixtures for audit tests."""

from __future__ import annotations

import random
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, PITDailyPrice, Score
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture(autouse=True)
def deterministic_random() -> None:
    """Pin the RNG seed for every audit test. Determinism is a correctness invariant."""
    random.seed(42)
    np.random.seed(42)


@pytest_asyncio.fixture
async def synthetic_audit_db() -> AsyncIterator[AsyncSession]:
    """In-memory SQLite fixture with representative candidates and price data.

    Contains:
    - AAPL: conviction=high, composite_percentile=87.0
    - MSFT: conviction=exceptional, composite_percentile=95.0
    - DEAD: conviction=medium, composite_percentile=71.0 (data-unavailable candidate)
    - SPY: benchmark (no score, prices only)

    120 trading days of price data from 2026-01-05 onward.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(ticker="AAPL", name="Apple Inc.", sector="Technology")
        msft = Asset(ticker="MSFT", name="Microsoft Corp.", sector="Technology")
        dead = Asset(ticker="DEAD", name="Dead Corp.", sector="Industrials")
        spy = Asset(ticker="SPY", name="SPDR S&P 500", sector="Financials")
        session.add_all([aapl, msft, dead, spy])
        await session.flush()
        # Use Monday 2026-02-16 as score date (2026-02-15 is Sunday)
        scored_at = datetime(2026, 2, 16, tzinfo=UTC)
        session.add_all(
            [
                Score(
                    asset_id=aapl.id,
                    scored_at=scored_at,
                    conviction_level="high",
                    composite_percentile=87.0,
                    opportunity_type="compounder",
                    asymmetry_ratio=2.0,
                    signal="strong",
                ),
                Score(
                    asset_id=msft.id,
                    scored_at=scored_at,
                    conviction_level="exceptional",
                    composite_percentile=95.0,
                    opportunity_type="compounder",
                    asymmetry_ratio=3.0,
                    signal="strong",
                ),
                Score(
                    asset_id=dead.id,
                    scored_at=scored_at,
                    conviction_level="medium",
                    composite_percentile=71.0,
                    opportunity_type=None,
                    asymmetry_ratio=None,
                    signal="stable",
                ),
            ]
        )
        start = date(2026, 1, 5)
        for i in range(120):
            d = start + timedelta(days=i)
            if d.weekday() >= 5:
                continue
            session.add_all(
                [
                    PITDailyPrice(
                        ticker="AAPL",
                        date=d,
                        open=100.0,
                        high=101.0,
                        low=99.0,
                        close=100.0 + i * 0.5,
                        adj_close=100.0 + i * 0.5,
                        volume=1_000_000,
                    ),
                    PITDailyPrice(
                        ticker="MSFT",
                        date=d,
                        open=200.0,
                        high=201.0,
                        low=199.0,
                        close=200.0 + i * 0.8,
                        adj_close=200.0 + i * 0.8,
                        volume=1_500_000,
                    ),
                    PITDailyPrice(
                        ticker="SPY",
                        date=d,
                        open=400.0,
                        high=401.0,
                        low=399.0,
                        close=400.0 + i * 0.2,
                        adj_close=400.0 + i * 0.2,
                        volume=10_000_000,
                    ),
                ]
            )
        await session.commit()
        yield session
    await engine.dispose()
