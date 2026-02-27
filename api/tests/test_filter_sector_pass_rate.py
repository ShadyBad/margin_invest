"""API integration test: sector_pass_rate on FilterResultResponse.

Seeds an Asset + V4Score with detail containing sector_filter_pass_rates,
hits GET /api/v1/scores/TSLA, and asserts each filter result has the
correct sector_pass_rate value.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _v4_detail_with_pass_rates() -> dict:
    """Build a V4Score.detail dict with sector_filter_pass_rates."""
    return {
        "ticker": "TSLA",
        "composite_percentile": 72.0,
        "composite_raw_score": 68.5,
        "data_coverage": 0.95,
        "growth_stage": None,
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 70.0,
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [],
            "average_percentile": 65.0,
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 75.0,
        },
        "filters_passed": [
            {
                "name": "liquidity",
                "passed": True,
                "value": 5000000.0,
                "threshold": 1000000.0,
                "detail": "Sufficient daily volume",
            },
            {
                "name": "market_cap",
                "passed": False,
                "value": 500000000.0,
                "threshold": 1000000000.0,
                "detail": "Below minimum market cap",
            },
        ],
        "sector_filter_pass_rates": {
            "Consumer Discretionary": {
                "liquidity": 0.8,
                "market_cap": 0.6,
            },
            "Information Technology": {
                "liquidity": 0.9,
                "market_cap": 0.75,
            },
        },
    }


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        asset = Asset(
            ticker="TSLA",
            name="Tesla Inc.",
            sector="Consumer Discretionary",
            market_cap=Decimal("800000000000"),
        )
        session.add(asset)
        await session.flush()

        v4 = V4Score(
            asset_id=asset.id,
            opportunity_type="quality_compounder",
            conviction="high",
            rules_conviction="high",
            track_a={"score": 0.7},
            track_b={"score": 0.6},
            track_c={"score": 0.5},
            style="growth",
            timing_signal="neutral",
            max_position_pct=2.0,
            regime="normal",
            composite_score=72.0,
            ml_override="none",
            scored_at=datetime.now(UTC),
            detail=_v4_detail_with_pass_rates(),
        )
        session.add(v4)
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def client(seeded_session):
    app = create_app()

    async def override_get_db():
        async with seeded_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestFilterSectorPassRate:
    async def test_filters_have_sector_pass_rate(self, client):
        """GET /api/v1/scores/TSLA returns filter results with sector_pass_rate."""
        response = await client.get("/api/v1/scores/TSLA")
        assert response.status_code == 200
        data = response.json()

        filters = data["filters_passed"]
        assert len(filters) == 2

        # The asset sector is "Consumer Discretionary" — rates should match that sector
        liquidity_filter = next(f for f in filters if f["name"] == "liquidity")
        assert liquidity_filter["sector_pass_rate"] == 0.8

        market_cap_filter = next(f for f in filters if f["name"] == "market_cap")
        assert market_cap_filter["sector_pass_rate"] == 0.6

    async def test_filter_verdict_still_present(self, client):
        """Verdicts are still set alongside sector_pass_rate."""
        response = await client.get("/api/v1/scores/TSLA")
        data = response.json()

        filters = data["filters_passed"]
        liquidity_filter = next(f for f in filters if f["name"] == "liquidity")
        assert liquidity_filter["verdict"] == "pass"

        market_cap_filter = next(f for f in filters if f["name"] == "market_cap")
        assert market_cap_filter["verdict"] == "fail"

    async def test_sector_pass_rate_null_when_no_rates_stored(self, seeded_session):
        """When detail has no sector_filter_pass_rates, sector_pass_rate is null."""
        # Create a V4Score without sector_filter_pass_rates
        async with seeded_session() as session:
            from sqlalchemy import select

            result = await session.execute(select(Asset).where(Asset.ticker == "TSLA"))
            asset = result.scalar_one()

            v4_no_rates = V4Score(
                asset_id=asset.id,
                opportunity_type="quality_compounder",
                conviction="medium",
                rules_conviction="medium",
                style="blend",
                timing_signal="neutral",
                max_position_pct=2.0,
                regime="normal",
                composite_score=60.0,
                ml_override="none",
                scored_at=datetime(2099, 1, 1, tzinfo=UTC),  # future so it's "latest"
                detail={
                    "ticker": "TSLA",
                    "composite_percentile": 60.0,
                    "composite_raw_score": 55.0,
                    "data_coverage": 0.9,
                    "quality": {
                        "factor_name": "quality",
                        "weight": 0.35,
                        "sub_scores": [],
                        "average_percentile": 50.0,
                    },
                    "value": {
                        "factor_name": "value",
                        "weight": 0.30,
                        "sub_scores": [],
                        "average_percentile": 55.0,
                    },
                    "momentum": {
                        "factor_name": "momentum",
                        "weight": 0.35,
                        "sub_scores": [],
                        "average_percentile": 60.0,
                    },
                    "filters_passed": [
                        {"name": "liquidity", "passed": True},
                    ],
                    # No sector_filter_pass_rates key
                },
            )
            session.add(v4_no_rates)
            await session.commit()

        app = create_app()

        async def override_get_db():
            async with seeded_session() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/v1/scores/TSLA")
            assert response.status_code == 200
            data = response.json()

            liquidity_filter = next(f for f in data["filters_passed"] if f["name"] == "liquidity")
            assert liquidity_filter["sector_pass_rate"] is None
