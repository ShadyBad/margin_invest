"""Test that score-serving endpoints only return published V4Scores.

Seeds an asset with two V4Scores:
- An older published score (composite_score=55)
- A newer unpublished score (composite_score=82)

Verifies GET /scores/AAPL returns the published score (55), not the
staged/unpublished one (82).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _v4_detail(ticker: str, composite_score: float) -> dict:
    """Minimal V4Score detail JSONB payload."""
    return {
        "ticker": ticker,
        "name": f"{ticker} Corp",
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [
                {"name": "roe", "raw_value": 0.3, "percentile_rank": 80.0, "detail": ""}
            ],
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [
                {"name": "ev_ebit", "raw_value": 12.0, "percentile_rank": 70.0, "detail": ""}
            ],
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [
                {"name": "price_mom", "raw_value": 0.1, "percentile_rank": 65.0, "detail": ""}
            ],
        },
        "filters_passed": [{"name": "market_cap", "passed": True, "detail": "", "verdict": "pass"}],
        "data_coverage": 0.95,
        "signal": "buy",
        "composite_percentile": composite_score,
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
class TestPublishedScoreFilter:
    async def test_serves_published_score_not_unpublished(self, session_factory):
        """GET /scores/AAPL returns the published score, not the newer unpublished one."""
        now = datetime.now(UTC)
        old_time = now - timedelta(hours=6)

        async with session_factory() as session:
            asset = Asset(
                ticker="AAPL",
                name="Apple Inc.",
                sector="Technology",
                market_cap=Decimal("3000000000000"),
            )
            session.add(asset)
            await session.flush()

            # Older, published score (composite_score=55)
            published_v4 = V4Score(
                asset_id=asset.id,
                scored_at=old_time,
                opportunity_type="compounder",
                conviction="medium",
                rules_conviction="medium",
                style="value",
                timing_signal="hold",
                max_position_pct=3.0,
                regime="normal",
                composite_score=55.0,
                ml_alpha=0.01,
                ml_confidence=0.5,
                ml_override="none",
                detail=_v4_detail("AAPL", 55.0),
                published=True,
            )

            # Newer, unpublished (staged) score (composite_score=82)
            unpublished_v4 = V4Score(
                asset_id=asset.id,
                scored_at=now,
                opportunity_type="compounder",
                conviction="high",
                rules_conviction="high",
                style="growth",
                timing_signal="buy_now",
                max_position_pct=5.0,
                regime="normal",
                composite_score=82.0,
                ml_alpha=0.08,
                ml_confidence=0.9,
                ml_override="promoted",
                detail=_v4_detail("AAPL", 82.0),
                published=False,
            )
            session.add_all([published_v4, unpublished_v4])
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/scores/AAPL")
            assert resp.status_code == 200
            data = resp.json()
            # Should get the published score (55), NOT the unpublished one (82)
            assert data["composite_percentile"] == 55.0
            assert data["ml_override"] == "none"
            assert data["style"] == "value"

    async def test_404_when_only_unpublished_v4_and_no_v2(self, session_factory):
        """When only unpublished V4Scores exist and no v2 Score, returns 404."""
        async with session_factory() as session:
            asset = Asset(
                ticker="NOPR",
                name="No Published Corp",
                sector="Technology",
                market_cap=Decimal("50000000000"),
            )
            session.add(asset)
            await session.flush()

            # Only unpublished score
            v4 = V4Score(
                asset_id=asset.id,
                scored_at=datetime.now(UTC),
                opportunity_type="compounder",
                conviction="high",
                rules_conviction="high",
                style="growth",
                timing_signal="buy_now",
                max_position_pct=5.0,
                regime="normal",
                composite_score=80.0,
                ml_alpha=0.05,
                ml_confidence=0.8,
                ml_override="none",
                detail=_v4_detail("NOPR", 80.0),
                published=False,
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/scores/NOPR")
            assert resp.status_code == 404

    async def test_sector_champion_uses_published_only(self, session_factory):
        """Sector champion query should only consider published V4Scores."""
        now = datetime.now(UTC)

        async with session_factory() as session:
            # Eliminated ticker
            tsla = Asset(
                ticker="TSLA",
                name="Tesla Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("800000000000"),
            )
            # Champion candidate (published)
            amzn = Asset(
                ticker="AMZN",
                name="Amazon.com Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("1500000000000"),
            )
            # Higher-scoring but unpublished
            hd = Asset(
                ticker="HD",
                name="Home Depot Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("350000000000"),
            )
            session.add_all([tsla, amzn, hd])
            await session.flush()

            fail_filters = [
                {
                    "name": "profitability_screen",
                    "passed": False,
                    "value": -0.02,
                    "threshold": 0.0,
                    "verdict": "fail",
                },
            ]
            pass_filters = [
                {
                    "name": "profitability_screen",
                    "passed": True,
                    "value": 0.08,
                    "threshold": 0.0,
                    "verdict": "pass",
                },
            ]

            def _detail(ticker, filters, score):
                return {
                    "ticker": ticker,
                    "composite_percentile": score,
                    "composite_raw_score": score / 100,
                    "composite_tier": "medium",
                    "signal": "watch",
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
                        "average_percentile": 50.0,
                    },
                    "momentum": {
                        "factor_name": "momentum",
                        "weight": 0.35,
                        "sub_scores": [],
                        "average_percentile": 50.0,
                    },
                    "filters_passed": filters,
                    "data_coverage": 1.0,
                    "growth_stage": None,
                }

            # TSLA: eliminated, published
            tsla_score = V4Score(
                asset_id=tsla.id,
                scored_at=now,
                opportunity_type="quality_compounder",
                conviction="medium",
                rules_conviction="medium",
                style="blend",
                timing_signal="neutral",
                max_position_pct=2.0,
                regime="normal",
                composite_score=40.0,
                ml_override="none",
                detail=_detail("TSLA", fail_filters, 40.0),
                published=True,
            )

            # AMZN: passing, published, composite=75
            amzn_score = V4Score(
                asset_id=amzn.id,
                scored_at=now,
                opportunity_type="quality_compounder",
                conviction="high",
                rules_conviction="high",
                style="blend",
                timing_signal="neutral",
                max_position_pct=3.0,
                regime="normal",
                composite_score=75.0,
                ml_override="none",
                detail=_detail("AMZN", pass_filters, 75.0),
                published=True,
            )

            # HD: passing, UNPUBLISHED, composite=95 (higher than AMZN)
            hd_score = V4Score(
                asset_id=hd.id,
                scored_at=now,
                opportunity_type="quality_compounder",
                conviction="exceptional",
                rules_conviction="exceptional",
                style="value",
                timing_signal="buy_now",
                max_position_pct=5.0,
                regime="normal",
                composite_score=95.0,
                ml_override="none",
                detail=_detail("HD", pass_filters, 95.0),
                published=False,
            )
            session.add_all([tsla_score, amzn_score, hd_score])
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/scores/TSLA")
            assert resp.status_code == 200
            data = resp.json()
            champion = data.get("sector_champion")
            assert champion is not None
            # AMZN should be champion (published), NOT HD (unpublished even though higher score)
            assert champion["ticker"] == "AMZN"
