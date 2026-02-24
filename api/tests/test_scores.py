"""Tests for score endpoints — DB-backed."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _score_detail(
    ticker: str = "AAPL",
    percentile: float = 99.5,
    conviction: str = "exceptional",
    signal: str = "buy",
) -> dict:
    """Create a score_detail JSONB payload."""
    return {
        "ticker": ticker,
        "composite_percentile": percentile,
        "conviction_level": conviction,
        "signal": signal,
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 98.0,
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [],
            "average_percentile": 95.0,
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 97.0,
        },
        "filters_passed": [],
        "data_coverage": 1.0,
        "growth_stage": None,
    }


@pytest_asyncio.fixture
async def async_engine():
    """Create an async in-memory SQLite engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    """Create an async session bound to the in-memory SQLite engine."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def seeded_session(async_engine):
    """Seed the DB with test assets and scores, return a session factory."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        nvda = Asset(
            ticker="NVDA",
            name="NVIDIA Corp",
            sector="Information Technology",
            market_cap=Decimal("1500000000000"),
        )
        low = Asset(
            ticker="LOW",
            name="Low Score Inc.",
            sector="Consumer Discretionary",
            market_cap=Decimal("50000000000"),
        )
        session.add_all([aapl, nvda, low])
        await session.flush()

        aapl_score = Score(
            asset_id=aapl.id,
            composite_percentile=99.5,
            conviction_level="exceptional",
            signal="buy",
            quality_percentile=98.0,
            value_percentile=95.0,
            momentum_percentile=97.0,
            data_coverage=1.0,
            score_detail=_score_detail("AAPL", 99.5, "exceptional", "buy"),
        )
        nvda_score = Score(
            asset_id=nvda.id,
            composite_percentile=96.0,
            conviction_level="high",
            signal="buy",
            quality_percentile=94.0,
            value_percentile=93.0,
            momentum_percentile=95.0,
            data_coverage=1.0,
            score_detail=_score_detail("NVDA", 96.0, "high", "buy"),
        )
        low_score = Score(
            asset_id=low.id,
            composite_percentile=50.0,
            conviction_level="none",
            signal="no_action",
            quality_percentile=45.0,
            value_percentile=50.0,
            momentum_percentile=55.0,
            data_coverage=1.0,
            score_detail=_score_detail("LOW", 50.0, "none", "no_action"),
        )
        session.add_all([aapl_score, nvda_score, low_score])
        await session.commit()

    # Return factory so each request gets a fresh session from the same engine
    return factory


@pytest_asyncio.fixture
async def client(seeded_session):
    """AsyncClient with DB dependency overridden to use seeded async SQLite."""
    app = create_app()

    async def override_get_db():
        async with seeded_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def empty_client(async_engine):
    """AsyncClient with empty DB (no assets or scores)."""
    app = create_app()
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestGetScore:
    async def test_get_score_success(self, client):
        response = await client.get("/api/v1/scores/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["composite_percentile"] == 99.5
        assert data["conviction_level"] == "exceptional"
        assert data["signal"] == "buy"

    async def test_get_score_not_found(self, client):
        response = await client.get("/api/v1/scores/UNKNOWN")
        assert response.status_code == 404

    async def test_get_score_case_insensitive(self, client):
        response = await client.get("/api/v1/scores/aapl")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"


@pytest.mark.asyncio
class TestListScores:
    async def test_list_scores_empty(self, empty_client):
        response = await empty_client.get("/api/v1/scores")
        assert response.status_code == 200
        data = response.json()
        assert data["scores"] == []
        assert data["total"] == 0

    async def test_list_scores_with_data(self, client):
        response = await client.get("/api/v1/scores")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        # Should be sorted by composite_percentile descending
        tickers = [s["ticker"] for s in data["scores"]]
        assert tickers[0] == "AAPL"
        assert tickers[1] == "NVDA"
        assert tickers[2] == "LOW"

    async def test_list_scores_filter_by_percentile(self, client):
        response = await client.get("/api/v1/scores?min_percentile=98")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["scores"][0]["ticker"] == "AAPL"

    async def test_list_scores_filter_by_conviction(self, client):
        response = await client.get("/api/v1/scores?conviction=exceptional")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["scores"][0]["ticker"] == "AAPL"

    async def test_list_scores_pagination(self, client):
        response = await client.get("/api/v1/scores?page=1&page_size=1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["scores"]) == 1
        assert data["page"] == 1
        assert data["page_size"] == 1
        # First page should have highest score
        assert data["scores"][0]["ticker"] == "AAPL"

    async def test_list_scores_pagination_page_2(self, client):
        response = await client.get("/api/v1/scores?page=2&page_size=1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["scores"]) == 1
        assert data["scores"][0]["ticker"] == "NVDA"


@pytest.mark.asyncio
class TestScoreFreshness:
    async def test_score_response_includes_freshness(self, client):
        """Score responses include data_freshness field."""
        response = await client.get("/api/v1/scores/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "data_freshness" in data
        assert data["data_freshness"] in ("fresh", "stale", "expired")

    async def test_score_response_includes_price_source(self, client):
        """Score responses include price_source field (daily_close when no Redis)."""
        response = await client.get("/api/v1/scores/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "price_source" in data
        assert data["price_source"] == "daily_close"

    async def test_score_response_includes_price_updated_at(self, client):
        """Score responses include price_updated_at field."""
        response = await client.get("/api/v1/scores/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "price_updated_at" in data

    async def test_list_scores_include_freshness(self, client):
        """List score responses also include data_freshness."""
        response = await client.get("/api/v1/scores")
        assert response.status_code == 200
        data = response.json()
        for score in data["scores"]:
            assert "data_freshness" in score
            assert score["data_freshness"] in ("fresh", "stale", "expired")
            assert "price_source" in score
            assert "price_updated_at" in score


@pytest.mark.asyncio
class TestMalformedScoreDetail:
    async def test_get_score_with_malformed_detail_returns_fallback(self, async_engine):
        """If score_detail JSONB is malformed, endpoint returns degraded response instead of 500."""
        factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as session:
            asset = Asset(ticker="BROKEN", name="Broken Corp", sector="Information Technology")
            session.add(asset)
            await session.flush()
            score = Score(
                asset_id=asset.id,
                composite_percentile=75.0,
                composite_raw_score=0.60,
                conviction_level="high",
                signal="buy",
                quality_percentile=80.0,
                value_percentile=70.0,
                momentum_percentile=75.0,
                data_coverage=0.9,
                score_detail={"garbage": True},  # Missing all required fields
                scored_at=datetime.now(UTC),
            )
            session.add(score)
            await session.commit()

        app = create_app()

        async def override_get_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/scores/BROKEN")

        assert resp.status_code == 200  # Not 500!
        body = resp.json()
        assert body["ticker"] == "BROKEN"
        assert body["conviction_level"] == "high"


@pytest.mark.asyncio
class TestScoreAssetContext:
    """Tests for sector, universe_size, total_scored, sector_survivor_count."""

    async def test_score_includes_sector(self, client):
        """Score response includes the asset's sector."""
        response = await client.get("/api/v1/scores/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["sector"] == "Information Technology"

    async def test_score_includes_total_scored(self, client):
        """Score response includes total scored count across all assets."""
        response = await client.get("/api/v1/scores/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["total_scored"] == 3  # AAPL, NVDA, LOW

    async def test_score_universe_size_null_without_snapshot(self, client):
        """universe_size is null when no active universe snapshot exists."""
        response = await client.get("/api/v1/scores/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["universe_size"] is None

    async def test_score_includes_filters_survived_count(self, client):
        """filters_survived_count counts stocks that passed all filters."""
        response = await client.get("/api/v1/scores/AAPL")
        assert response.status_code == 200
        data = response.json()
        # All seeded stocks have empty filters_passed, so none survive
        assert data["filters_survived_count"] == 0

    async def test_score_sector_survivor_count(self, client):
        """sector_survivor_count counts same-sector stocks that passed all filters."""
        response = await client.get("/api/v1/scores/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["sector_survivor_count"] == 0

    async def test_score_sector_survivor_excludes_self(self, async_engine):
        """Sector survivor count excludes the ticker itself."""
        factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as session:
            a1 = Asset(ticker="TST1", name="Test 1", sector="Tech", market_cap=Decimal("1000000"))
            a2 = Asset(ticker="TST2", name="Test 2", sector="Tech", market_cap=Decimal("1000000"))
            session.add_all([a1, a2])
            await session.flush()
            # Both pass all filters
            passing_filters = [{"name": "f1", "passed": True, "verdict": "pass"}]
            session.add_all([
                Score(
                    asset_id=a1.id,
                    composite_percentile=80.0,
                    conviction_level="high",
                    signal="buy",
                    quality_percentile=80.0,
                    value_percentile=80.0,
                    momentum_percentile=80.0,
                    data_coverage=1.0,
                    score_detail={
                        **_score_detail("TST1", 80.0, "high", "buy"),
                        "filters_passed": passing_filters,
                    },
                    scored_at=datetime.now(UTC),
                ),
                Score(
                    asset_id=a2.id,
                    composite_percentile=75.0,
                    conviction_level="high",
                    signal="buy",
                    quality_percentile=75.0,
                    value_percentile=75.0,
                    momentum_percentile=75.0,
                    data_coverage=1.0,
                    score_detail={
                        **_score_detail("TST2", 75.0, "high", "buy"),
                        "filters_passed": passing_filters,
                    },
                    scored_at=datetime.now(UTC),
                ),
            ])
            await session.commit()

        app = create_app()

        async def override_get_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/scores/TST1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["sector"] == "Tech"
        assert body["filters_survived_count"] == 2  # Both pass all filters
        assert body["sector_survivor_count"] == 1  # TST2, not self
        assert body["total_scored"] == 2
