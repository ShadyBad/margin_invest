"""Tests for dashboard endpoint — DB-backed."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, Score, UniverseSnapshot
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


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


@pytest_asyncio.fixture
async def seeded_session(async_engine):
    """Seed DB with mixed conviction levels, return session factory."""
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
        msft = Asset(
            ticker="MSFT",
            name="Microsoft Corp",
            sector="Information Technology",
            market_cap=Decimal("2800000000000"),
        )
        low = Asset(
            ticker="LOW",
            name="Lowes Companies",
            sector="Consumer Discretionary",
            market_cap=Decimal("50000000000"),
        )
        session.add_all([aapl, nvda, msft, low])
        await session.flush()

        now = datetime.now(UTC)

        aapl_score = Score(
            asset_id=aapl.id,
            composite_percentile=99.5,
            conviction_level="exceptional",
            signal="buy",
            quality_percentile=98.0,
            value_percentile=95.0,
            momentum_percentile=97.0,
            data_coverage=1.0,
            scored_at=now,
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
            scored_at=now,
        )
        msft_score = Score(
            asset_id=msft.id,
            composite_percentile=80.0,
            conviction_level="watchlist",
            signal="hold",
            quality_percentile=78.0,
            value_percentile=82.0,
            momentum_percentile=75.0,
            data_coverage=1.0,
            scored_at=now,
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
            scored_at=now,
        )
        session.add_all([aapl_score, nvda_score, msft_score, low_score])
        await session.commit()

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


@pytest.mark.asyncio
class TestDashboardEmpty:
    async def test_empty_dashboard(self, empty_client):
        """No scores in DB -> picks=[], watchlist=[], total_scored=0."""
        response = await empty_client.get("/api/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["picks"] == []
        assert data["watchlist"] == []
        assert data["total_scored"] == 0
        # last_updated should still be a valid ISO datetime string
        assert "T" in data["last_updated"]


@pytest.mark.asyncio
class TestDashboardPicks:
    async def test_picks_populated(self, client):
        """Exceptional + high conviction scores appear as picks."""
        response = await client.get("/api/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        picks = data["picks"]
        assert len(picks) == 2
        tickers = {p["ticker"] for p in picks}
        assert tickers == {"AAPL", "NVDA"}

    async def test_picks_sorted_by_percentile_desc(self, client):
        """Picks are sorted by composite_percentile descending."""
        response = await client.get("/api/v1/dashboard")
        data = response.json()
        picks = data["picks"]
        assert len(picks) == 2
        assert picks[0]["ticker"] == "AAPL"
        assert picks[0]["composite_percentile"] == 99.5
        assert picks[1]["ticker"] == "NVDA"
        assert picks[1]["composite_percentile"] == 96.0

    async def test_pick_includes_factor_percentiles(self, client):
        """Each pick includes quality, value, momentum percentiles."""
        response = await client.get("/api/v1/dashboard")
        data = response.json()
        aapl_pick = data["picks"][0]
        assert aapl_pick["quality_percentile"] == 98.0
        assert aapl_pick["value_percentile"] == 95.0
        assert aapl_pick["momentum_percentile"] == 97.0

    async def test_pick_includes_signal_and_conviction(self, client):
        """Each pick includes signal and conviction_level."""
        response = await client.get("/api/v1/dashboard")
        data = response.json()
        aapl_pick = data["picks"][0]
        assert aapl_pick["signal"] == "buy"
        assert aapl_pick["conviction_level"] == "exceptional"
        assert aapl_pick["name"] == "Apple Inc."


@pytest.mark.asyncio
class TestDashboardWatchlist:
    async def test_watchlist_populated(self, client):
        """Watchlist conviction scores appear in watchlist."""
        response = await client.get("/api/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        watchlist = data["watchlist"]
        assert len(watchlist) == 1
        assert watchlist[0]["ticker"] == "MSFT"
        assert watchlist[0]["name"] == "Microsoft Corp"
        assert watchlist[0]["composite_percentile"] == 80.0
        assert watchlist[0]["conviction_level"] == "watchlist"


@pytest.mark.asyncio
class TestDashboardMixed:
    async def test_mixed_conviction_levels(self, client):
        """Exceptional/high -> picks, watchlist -> watchlist, none -> excluded."""
        response = await client.get("/api/v1/dashboard")
        data = response.json()

        # 2 picks (exceptional + high)
        assert len(data["picks"]) == 2

        # 1 watchlist
        assert len(data["watchlist"]) == 1

        # "none" conviction excluded from both
        all_tickers = (
            [p["ticker"] for p in data["picks"]]
            + [w["ticker"] for w in data["watchlist"]]
        )
        assert "LOW" not in all_tickers

    async def test_total_scored_counts_all(self, client):
        """total_scored includes ALL scored assets, not just picks/watchlist."""
        response = await client.get("/api/v1/dashboard")
        data = response.json()
        assert data["total_scored"] == 4

    async def test_last_updated_is_valid(self, client):
        """last_updated is a valid ISO datetime string."""
        response = await client.get("/api/v1/dashboard")
        data = response.json()
        # Should parse without error
        dt = datetime.fromisoformat(data["last_updated"])
        assert isinstance(dt, datetime)


@pytest_asyncio.fixture
async def universe_seeded_session(async_engine):
    """Seed DB with scores AND an active universe snapshot."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        # Create universe snapshot with 10 tickers
        snapshot = UniverseSnapshot(
            version="2026.02.15",
            config_hash="abc123",
            ticker_count=10,
            tickers=["AAPL", "NVDA", "MSFT", "LOW", "GOOG", "AMZN", "META", "TSLA", "JPM", "V"],
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        session.add(snapshot)

        # Create 4 scored assets
        aapl = Asset(
            ticker="AAPL", name="Apple Inc.",
            sector="Information Technology", market_cap=Decimal("3500000000000"),
        )
        nvda = Asset(
            ticker="NVDA", name="NVIDIA Corp",
            sector="Information Technology", market_cap=Decimal("1500000000000"),
        )
        msft = Asset(
            ticker="MSFT", name="Microsoft Corp",
            sector="Information Technology", market_cap=Decimal("2800000000000"),
        )
        low = Asset(
            ticker="LOW", name="Lowes Companies",
            sector="Consumer Discretionary", market_cap=Decimal("50000000000"),
        )
        session.add_all([aapl, nvda, msft, low])
        await session.flush()

        now = datetime.now(UTC)
        scores = [
            Score(
                asset_id=aapl.id, composite_percentile=99.5,
                conviction_level="exceptional", signal="buy",
                quality_percentile=98.0, value_percentile=95.0,
                momentum_percentile=97.0, data_coverage=1.0, scored_at=now,
            ),
            Score(
                asset_id=nvda.id, composite_percentile=96.0,
                conviction_level="high", signal="buy",
                quality_percentile=94.0, value_percentile=93.0,
                momentum_percentile=95.0, data_coverage=1.0, scored_at=now,
            ),
            Score(
                asset_id=msft.id, composite_percentile=80.0,
                conviction_level="watchlist", signal="hold",
                quality_percentile=78.0, value_percentile=82.0,
                momentum_percentile=75.0, data_coverage=1.0, scored_at=now,
            ),
            Score(
                asset_id=low.id, composite_percentile=50.0,
                conviction_level="none", signal="no_action",
                quality_percentile=45.0, value_percentile=50.0,
                momentum_percentile=55.0, data_coverage=1.0, scored_at=now,
            ),
        ]
        session.add_all(scores)
        await session.commit()

    return factory


@pytest_asyncio.fixture
async def universe_client(universe_seeded_session):
    """AsyncClient with universe snapshot and scored assets."""
    app = create_app()

    async def override_get_db():
        async with universe_seeded_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestDashboardUniverseMetadata:
    async def test_no_universe_returns_warning(self, empty_client):
        """When no universe snapshot exists, universe is None and warning is returned."""
        response = await empty_client.get("/api/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["universe"] is None
        assert len(data["warnings"]) == 1
        assert data["warnings"][0]["code"] == "NO_UNIVERSE"
        assert data["warnings"][0]["severity"] == "warning"

    async def test_no_universe_without_snapshot_seeded(self, client):
        """Seeded DB without universe snapshot returns NO_UNIVERSE warning."""
        response = await client.get("/api/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["universe"] is None
        assert any(w["code"] == "NO_UNIVERSE" for w in data["warnings"])

    async def test_universe_metadata_with_active_snapshot(self, universe_client):
        """With an active snapshot, universe field is populated."""
        response = await universe_client.get("/api/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["universe"] is not None
        assert data["universe"]["version"] == "2026.02.15"
        assert data["universe"]["size"] == 10

    async def test_low_coverage_warning(self, universe_client):
        """4 scored out of 10 universe tickers -> LOW_COVERAGE warning."""
        response = await universe_client.get("/api/v1/dashboard")
        data = response.json()
        assert data["universe"]["scoring_coverage"] == 0.4
        assert data["universe"]["is_complete"] is False
        low_cov = [w for w in data["warnings"] if w["code"] == "LOW_COVERAGE"]
        assert len(low_cov) == 1
        assert low_cov[0]["severity"] == "error"  # <50% coverage -> error

    async def test_existing_fields_still_work(self, universe_client):
        """Existing dashboard fields remain intact."""
        response = await universe_client.get("/api/v1/dashboard")
        data = response.json()
        assert data["total_scored"] == 4
        assert len(data["picks"]) == 2
        assert len(data["watchlist"]) == 1
