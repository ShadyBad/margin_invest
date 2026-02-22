"""Tests for the DNA visual parameters endpoint."""

from __future__ import annotations

import re
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


@pytest_asyncio.fixture
async def async_engine():
    """Create an async in-memory SQLite engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
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
    """Seed DB with assets and scores across multiple sectors."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        jnj = Asset(
            ticker="JNJ",
            name="Johnson & Johnson",
            sector="Health Care",
            market_cap=Decimal("400000000000"),
        )
        jpm = Asset(
            ticker="JPM",
            name="JPMorgan Chase",
            sector="Financials",
            market_cap=Decimal("500000000000"),
        )
        session.add_all([aapl, jnj, jpm])
        await session.flush()

        for asset in [aapl, jnj, jpm]:
            score = Score(
                asset_id=asset.id,
                composite_percentile=80.0,
                composite_raw_score=70.0,
                conviction_level="high",
                signal="buy",
                quality_percentile=75.0,
                value_percentile=70.0,
                momentum_percentile=85.0,
                scored_at=datetime(2026, 2, 17, 10, 0, 0, tzinfo=UTC),
            )
            session.add(score)
        await session.commit()

    return factory


@pytest_asyncio.fixture
async def seeded_client(seeded_session):
    """AsyncClient with seeded DB containing scored assets."""
    app = create_app()

    async def override_get_db():
        async with seeded_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


HEX_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


@pytest.mark.asyncio
class TestDNAEndpoint:
    async def test_requires_auth(self, empty_client: AsyncClient):
        """Request without auth headers returns 401."""
        response = await empty_client.get("/api/v1/users/me/dna")
        assert response.status_code == 401

    async def test_returns_defaults_for_user_with_no_scores(self, empty_client: AsyncClient):
        """User with no scored tickers gets default DNA values."""
        response = await empty_client.get(
            "/api/v1/users/me/dna",
            headers={"X-User-Id": "1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "base" in data
        assert "mid" in data
        assert "accent" in data
        assert "density" in data
        assert "tempo" in data
        assert isinstance(data["density"], (int, float))
        assert isinstance(data["tempo"], (int, float))

    async def test_response_has_valid_hex_colors(self, empty_client: AsyncClient):
        """All color fields must be valid 6-digit hex strings."""
        response = await empty_client.get(
            "/api/v1/users/me/dna",
            headers={"X-User-Id": "1"},
        )
        data = response.json()
        assert HEX_PATTERN.match(data["base"])
        assert HEX_PATTERN.match(data["mid"])
        assert HEX_PATTERN.match(data["accent"])

    async def test_density_and_tempo_ranges(self, empty_client: AsyncClient):
        """Density is 0-1, tempo is 0.5-1.5."""
        response = await empty_client.get(
            "/api/v1/users/me/dna",
            headers={"X-User-Id": "1"},
        )
        data = response.json()
        assert 0.0 <= data["density"] <= 1.0
        assert 0.5 <= data["tempo"] <= 1.5

    async def test_seeded_portfolio_returns_blended_colors(self, seeded_client: AsyncClient):
        """Portfolio with real scored assets returns sector-blended DNA."""
        response = await seeded_client.get(
            "/api/v1/users/me/dna",
            headers={"X-User-Id": "1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert HEX_PATTERN.match(data["base"])
        assert HEX_PATTERN.match(data["mid"])
        assert HEX_PATTERN.match(data["accent"])
        # 3 tickers -> density = 3/30 = 0.1
        assert data["density"] == pytest.approx(0.1, abs=0.01)
        # avg_beta defaults to 1.0 -> tempo = 0.4 + 1.0*0.6 = 1.0
        assert data["tempo"] == pytest.approx(1.0, abs=0.01)

    async def test_seeded_colors_differ_from_defaults(self, seeded_client: AsyncClient):
        """A portfolio with known sectors should produce different colors than defaults."""
        response = await seeded_client.get(
            "/api/v1/users/me/dna",
            headers={"X-User-Id": "1"},
        )
        data = response.json()
        # Default base is #0F0D0B, seeded portfolio should be different
        assert data["base"] != "#0F0D0B" or data["base"] != "#0f0d0b"


class TestComputeDNA:
    """Unit tests for the compute_dna function."""

    def test_empty_weights_returns_default(self):
        from margin_api.routes.dna import DEFAULT_DNA, compute_dna

        result = compute_dna({}, 0, 1.0)
        assert result == DEFAULT_DNA

    def test_unknown_sectors_returns_default(self):
        from margin_api.routes.dna import DEFAULT_DNA, compute_dna

        result = compute_dna({"Unknown Sector": 1.0}, 5, 1.0)
        assert result == DEFAULT_DNA

    def test_single_sector_uses_sector_color(self):
        from margin_api.routes.dna import SECTOR_COLORS, compute_dna

        result = compute_dna({"Information Technology": 1.0}, 10, 1.0)
        assert HEX_PATTERN.match(result.base)
        # Base should be the IT sector color
        assert result.base == SECTOR_COLORS["Information Technology"].lower()

    def test_density_scales_with_ticker_count(self):
        from margin_api.routes.dna import compute_dna

        low = compute_dna({"Information Technology": 1.0}, 3, 1.0)
        high = compute_dna({"Information Technology": 1.0}, 25, 1.0)
        assert low.density < high.density

    def test_tempo_scales_with_beta(self):
        from margin_api.routes.dna import compute_dna

        low_beta = compute_dna({"Information Technology": 1.0}, 10, 0.5)
        high_beta = compute_dna({"Information Technology": 1.0}, 10, 1.5)
        assert low_beta.tempo < high_beta.tempo
