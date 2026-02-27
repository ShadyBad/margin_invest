"""API integration tests for sector distribution on FactorScoreResponse.

Seeds an Asset + V4Score with detail containing sector_distribution,
then hits GET /api/v1/scores/{ticker} and asserts that sub-factors
have sector_p10, sector_p50, sector_p90, sector_count fields populated.
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


def _v4_detail_with_sector_dist() -> dict:
    """V4Score detail JSONB with sector_distribution populated."""
    return {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [
                {"name": "roe", "raw_value": 0.30, "percentile_rank": 80.0, "detail": ""},
                {
                    "name": "gross_profitability",
                    "raw_value": 0.45,
                    "percentile_rank": 75.0,
                    "detail": "",
                },
            ],
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [
                {"name": "ev_fcf", "raw_value": 18.0, "percentile_rank": 60.0, "detail": ""},
            ],
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [
                {"name": "price_mom", "raw_value": 0.12, "percentile_rank": 65.0, "detail": ""},
            ],
        },
        "filters_passed": [
            {"name": "market_cap", "passed": True, "detail": "", "verdict": "pass"}
        ],
        "data_coverage": 0.95,
        "signal": "buy",
        "composite_percentile": 85.0,
        "sector_distribution": {
            "roe": {"p10": 0.10, "p50": 0.22, "p90": 0.38, "count": 50},
            "gross_profitability": {"p10": 0.20, "p50": 0.40, "p90": 0.60, "count": 50},
            "ev_fcf": {"p10": 8.0, "p50": 15.0, "p90": 30.0, "count": 45},
            "price_mom": {"p10": -0.05, "p50": 0.08, "p90": 0.20, "count": 48},
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
async def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


def _make_client(session_factory):
    """Build an AsyncClient with DB override."""
    app = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
class TestSectorDistributionInScoreEndpoint:
    """Tests that GET /api/v1/scores/{ticker} returns sector distribution data."""

    async def test_sub_factors_have_sector_percentiles(self, session_factory):
        """Sub-factor scores should include sector_p10/p50/p90/count."""
        async with session_factory() as session:
            asset = Asset(
                ticker="AAPL",
                name="Apple Inc.",
                sector="Information Technology",
                market_cap=Decimal("3000000000000"),
            )
            session.add(asset)
            await session.flush()

            v4 = V4Score(
                asset_id=asset.id,
                opportunity_type="quality_compounder",
                conviction="high",
                rules_conviction="high",
                style="blend",
                timing_signal="neutral",
                max_position_pct=2.0,
                regime="normal",
                composite_score=85.0,
                ml_override="none",
                detail=_v4_detail_with_sector_dist(),
                scored_at=datetime.now(UTC),
                published=True,
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/scores/AAPL")

        assert resp.status_code == 200
        data = resp.json()

        # Check quality sub-factors
        quality_subs = data["quality"]["sub_scores"]
        roe_sub = next(s for s in quality_subs if s["name"] == "roe")
        assert roe_sub["sector_p10"] == 0.10
        assert roe_sub["sector_p50"] == 0.22
        assert roe_sub["sector_p90"] == 0.38
        assert roe_sub["sector_count"] == 50

        gp_sub = next(s for s in quality_subs if s["name"] == "gross_profitability")
        assert gp_sub["sector_p10"] == 0.20
        assert gp_sub["sector_p50"] == 0.40
        assert gp_sub["sector_p90"] == 0.60
        assert gp_sub["sector_count"] == 50

        # Check value sub-factors
        value_subs = data["value"]["sub_scores"]
        ev_fcf_sub = next(s for s in value_subs if s["name"] == "ev_fcf")
        assert ev_fcf_sub["sector_p10"] == 8.0
        assert ev_fcf_sub["sector_p50"] == 15.0
        assert ev_fcf_sub["sector_p90"] == 30.0
        assert ev_fcf_sub["sector_count"] == 45

        # Check momentum sub-factors
        mom_subs = data["momentum"]["sub_scores"]
        mom_sub = next(s for s in mom_subs if s["name"] == "price_mom")
        assert mom_sub["sector_p10"] == -0.05
        assert mom_sub["sector_p50"] == 0.08
        assert mom_sub["sector_p90"] == 0.20
        assert mom_sub["sector_count"] == 48

    async def test_sub_factors_null_when_no_sector_dist(self, session_factory):
        """When sector_distribution is absent from detail, fields should be null."""
        detail_no_dist = {
            "ticker": "MSFT",
            "name": "Microsoft Corp",
            "quality": {
                "factor_name": "quality",
                "weight": 0.35,
                "sub_scores": [
                    {"name": "roe", "raw_value": 0.35, "percentile_rank": 90.0, "detail": ""}
                ],
            },
            "value": {
                "factor_name": "value",
                "weight": 0.30,
                "sub_scores": [
                    {"name": "ev_fcf", "raw_value": 20.0, "percentile_rank": 50.0, "detail": ""}
                ],
            },
            "momentum": {
                "factor_name": "momentum",
                "weight": 0.35,
                "sub_scores": [
                    {"name": "price_mom", "raw_value": 0.05, "percentile_rank": 55.0, "detail": ""}
                ],
            },
            "filters_passed": [
                {"name": "market_cap", "passed": True, "detail": "", "verdict": "pass"}
            ],
            "data_coverage": 0.90,
            "signal": "watch",
            "composite_percentile": 70.0,
        }

        async with session_factory() as session:
            asset = Asset(
                ticker="MSFT",
                name="Microsoft Corp",
                sector="Information Technology",
                market_cap=Decimal("2500000000000"),
            )
            session.add(asset)
            await session.flush()

            v4 = V4Score(
                asset_id=asset.id,
                opportunity_type="quality_compounder",
                conviction="medium",
                rules_conviction="medium",
                style="growth",
                timing_signal="neutral",
                max_position_pct=2.0,
                regime="normal",
                composite_score=70.0,
                ml_override="none",
                detail=detail_no_dist,
                scored_at=datetime.now(UTC),
                published=True,
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/scores/MSFT")

        assert resp.status_code == 200
        data = resp.json()

        # Without sector_distribution, fields should be None/null
        roe_sub = data["quality"]["sub_scores"][0]
        assert roe_sub["sector_p10"] is None
        assert roe_sub["sector_p50"] is None
        assert roe_sub["sector_p90"] is None
        assert roe_sub["sector_count"] is None

    async def test_partial_sector_dist_coverage(self, session_factory):
        """When sector_distribution only covers some factors, others should be null."""
        detail_partial = {
            "ticker": "GOOG",
            "name": "Alphabet Inc.",
            "quality": {
                "factor_name": "quality",
                "weight": 0.35,
                "sub_scores": [
                    {"name": "roe", "raw_value": 0.28, "percentile_rank": 70.0, "detail": ""},
                    {
                        "name": "unknown_factor",
                        "raw_value": 1.0,
                        "percentile_rank": 50.0,
                        "detail": "",
                    },
                ],
            },
            "value": {
                "factor_name": "value",
                "weight": 0.30,
                "sub_scores": [
                    {"name": "ev_fcf", "raw_value": 22.0, "percentile_rank": 45.0, "detail": ""}
                ],
            },
            "momentum": {
                "factor_name": "momentum",
                "weight": 0.35,
                "sub_scores": [
                    {"name": "price_mom", "raw_value": 0.08, "percentile_rank": 60.0, "detail": ""}
                ],
            },
            "filters_passed": [
                {"name": "market_cap", "passed": True, "detail": "", "verdict": "pass"}
            ],
            "data_coverage": 0.85,
            "signal": "watch",
            "composite_percentile": 65.0,
            "sector_distribution": {
                # Only roe has distribution data; unknown_factor and ev_fcf do not
                "roe": {"p10": 0.12, "p50": 0.24, "p90": 0.40, "count": 30},
            },
        }

        async with session_factory() as session:
            asset = Asset(
                ticker="GOOG",
                name="Alphabet Inc.",
                sector="Communication Services",
                market_cap=Decimal("1800000000000"),
            )
            session.add(asset)
            await session.flush()

            v4 = V4Score(
                asset_id=asset.id,
                opportunity_type="quality_compounder",
                conviction="medium",
                rules_conviction="medium",
                style="growth",
                timing_signal="neutral",
                max_position_pct=2.0,
                regime="normal",
                composite_score=65.0,
                ml_override="none",
                detail=detail_partial,
                scored_at=datetime.now(UTC),
                published=True,
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/scores/GOOG")

        assert resp.status_code == 200
        data = resp.json()

        # roe should have distribution
        roe_sub = next(s for s in data["quality"]["sub_scores"] if s["name"] == "roe")
        assert roe_sub["sector_p10"] == 0.12
        assert roe_sub["sector_p50"] == 0.24
        assert roe_sub["sector_p90"] == 0.40
        assert roe_sub["sector_count"] == 30

        # unknown_factor should NOT have distribution
        unknown_sub = next(
            s for s in data["quality"]["sub_scores"] if s["name"] == "unknown_factor"
        )
        assert unknown_sub["sector_p10"] is None
        assert unknown_sub["sector_p50"] is None
        assert unknown_sub["sector_p90"] is None
        assert unknown_sub["sector_count"] is None

        # ev_fcf should NOT have distribution
        ev_sub = data["value"]["sub_scores"][0]
        assert ev_sub["sector_p10"] is None
