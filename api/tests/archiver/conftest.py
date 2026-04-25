"""Shared fixtures for archiver tests."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score

SCORED_AT = datetime(2026, 4, 21, 20, 15, 0, tzinfo=timezone.utc)

DEFAULT_TRACK_A = {
    "score": 87.3,
    "qualifies": True,
    "gates_passed": 5,
    "total_gates": 5,
    "conviction": "exceptional",
    "conditional": False,
}
DEFAULT_TRACK_B = {
    "score": 79.1,
    "qualifies": True,
    "gates_passed": 4,
    "total_gates": 5,
    "conviction": "high",
    "conditional": False,
}
DEFAULT_TRACK_C = {
    "score": 65.2,
    "qualifies": True,
    "gates_passed": 3,
    "total_gates": 5,
    "conviction": "medium",
    "conditional": True,
}

DEFAULT_DETAIL: dict = {
    "quality": {
        "factor_name": "quality",
        "weight": 0.30,
        "sub_scores": [
            {
                "name": "gross_profitability",
                "percentile_rank": 92.1,
                "raw_value": 0.58,
                "detail": "",
                "weight": 1.0,
                "stub": False,
                "metadata": None,
            },
            {
                "name": "roic_wacc",
                "percentile_rank": 88.4,
                "raw_value": 2.15,
                "detail": "",
                "weight": 1.0,
                "stub": False,
                "metadata": None,
            },
        ],
    },
    "value": {
        "factor_name": "value",
        "weight": 0.25,
        "sub_scores": [
            {
                "name": "ev_fcf",
                "percentile_rank": 71.0,
                "raw_value": 22.3,
                "detail": "",
                "weight": 1.0,
                "stub": False,
                "metadata": None,
            },
        ],
    },
    "momentum": {
        "factor_name": "momentum",
        "weight": 0.20,
        "sub_scores": [
            {
                "name": "price_momentum",
                "percentile_rank": 80.1,
                "raw_value": 0.15,
                "detail": "",
                "weight": 1.0,
                "stub": False,
                "metadata": None,
            },
        ],
    },
    "growth": {
        "factor_name": "growth",
        "weight": 0.25,
        "sub_scores": [
            {
                "name": "revenue_cagr",
                "percentile_rank": 68.9,
                "raw_value": 0.12,
                "detail": "",
                "weight": 1.0,
                "stub": False,
                "metadata": None,
            },
        ],
    },
    "actual_price": 198.45,
}


def _make_asset(
    id: int,
    ticker: str,
    sector: str = "TECHNOLOGY",
    market_cap: Decimal = Decimal("3200000000000"),
) -> Asset:
    return Asset(
        id=id,
        ticker=ticker,
        name=f"{ticker} Inc.",
        sector=sector,
        market_cap=market_cap,
    )


def _make_v4score(
    asset_id: int,
    conviction: str = "exceptional",
    composite_score: float = 87.3,
    detail: dict | None = None,
) -> V4Score:
    return V4Score(
        asset_id=asset_id,
        scored_at=SCORED_AT,
        opportunity_type="core",
        conviction=conviction,
        rules_conviction=conviction,
        track_a=DEFAULT_TRACK_A.copy(),
        track_b=DEFAULT_TRACK_B.copy(),
        track_c=DEFAULT_TRACK_C.copy(),
        style="blend",
        timing_signal="neutral",
        max_position_pct=5.0,
        regime="normal",
        composite_score=composite_score,
        ml_alpha=0.12,
        ml_confidence=0.85,
        ml_override="none",
        detail=detail if detail is not None else DEFAULT_DETAIL.copy(),
        published=True,
    )


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_session(async_session: AsyncSession):
    # AAPL — exceptional, 87.3
    aapl = _make_asset(1, "AAPL")
    aapl_score = _make_v4score(1, conviction="exceptional", composite_score=87.3)

    # MSFT — high, 82.1
    msft = _make_asset(2, "MSFT")
    msft_detail = DEFAULT_DETAIL.copy()
    msft_detail["actual_price"] = 415.20
    msft_score = _make_v4score(2, conviction="high", composite_score=82.1, detail=msft_detail)

    # XYZ — none, 55.0 (excluded)
    xyz = _make_asset(3, "XYZ")
    xyz_detail = DEFAULT_DETAIL.copy()
    xyz_detail["actual_price"] = 32.10
    xyz_score = _make_v4score(3, conviction="none", composite_score=55.0, detail=xyz_detail)

    async_session.add_all([aapl, msft, xyz, aapl_score, msft_score, xyz_score])
    await async_session.commit()

    yield async_session
