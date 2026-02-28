"""Integration test: all 4 sector enhancements work together.

Seeds two tickers in the same sector (Consumer Discretionary):
- TSLA: eliminated (has failed filters) with market_cap, sector_filter_pass_rates,
  sector_distribution, and a peer (AMZN) that qualifies as sector_champion.
- AMZN: passing (all filters pass) with the same sector metadata.

Verifies:
1. market_cap is surfaced from Asset table
2. sector_pass_rate is injected into FilterResultResponse
3. sector distribution (p10/p50/p90/count) is injected into sub-factor scores
4. sector_champion is populated for eliminated tickers and absent for passing tickers
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SECTOR = "Consumer Discretionary"


def _v4_detail(
    ticker: str,
    filters_passed: list[dict],
    sector_filter_pass_rates: dict | None = None,
    sector_distribution: dict | None = None,
) -> dict:
    """Build a V4Score.detail JSONB blob with all sector enhancement fields."""
    detail: dict = {
        "ticker": ticker,
        "composite_percentile": 50.0,
        "composite_raw_score": 0.5,
        "composite_tier": "medium",
        "signal": "watch",
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [
                {
                    "name": "gross_profitability",
                    "raw_value": 0.32,
                    "percentile_rank": 68.0,
                    "detail": "",
                },
            ],
            "average_percentile": 68.0,
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
        "filters_passed": filters_passed,
        "data_coverage": 1.0,
        "growth_stage": None,
    }
    if sector_filter_pass_rates is not None:
        detail["sector_filter_pass_rates"] = sector_filter_pass_rates
    if sector_distribution is not None:
        detail["sector_distribution"] = sector_distribution
    return detail


SHARED_PASS_RATES = {
    SECTOR: {
        "beneish_m_score": 0.72,
        "z_score": 0.91,
    },
}

SHARED_SECTOR_DIST = {
    "gross_profitability": {
        "p10": 0.12,
        "p50": 0.28,
        "p90": 0.48,
        "count": 85,
    },
}

TSLA_FILTERS = [
    {
        "name": "beneish_m_score",
        "passed": False,
        "value": -1.42,
        "threshold": -1.78,
        "detail": "Possible earnings manipulation",
        "verdict": "fail",
    },
    {
        "name": "z_score",
        "passed": True,
        "value": 4.5,
        "threshold": 1.81,
        "detail": "No bankruptcy risk",
        "verdict": "pass",
    },
]

AMZN_FILTERS = [
    {
        "name": "beneish_m_score",
        "passed": True,
        "value": -3.1,
        "threshold": -1.78,
        "detail": "No earnings manipulation",
        "verdict": "pass",
    },
    {
        "name": "z_score",
        "passed": True,
        "value": 6.2,
        "threshold": 1.81,
        "detail": "No bankruptcy risk",
        "verdict": "pass",
    },
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
    """Seed TSLA (eliminated) and AMZN (passing) in Consumer Discretionary."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        tsla = Asset(
            ticker="TSLA",
            name="Tesla Inc.",
            sector=SECTOR,
            market_cap=Decimal("800000000000"),
        )
        amzn = Asset(
            ticker="AMZN",
            name="Amazon.com Inc.",
            sector=SECTOR,
            market_cap=Decimal("2000000000000"),
        )
        session.add_all([tsla, amzn])
        await session.flush()

        tsla_score = V4Score(
            asset_id=tsla.id,
            opportunity_type="quality_compounder",
            conviction="medium",
            rules_conviction="medium",
            style="blend",
            timing_signal="neutral",
            max_position_pct=2.0,
            regime="normal",
            composite_score=0.45,
            ml_override="none",
            scored_at=datetime.now(UTC),
            published=True,
            detail=_v4_detail(
                "TSLA",
                TSLA_FILTERS,
                sector_filter_pass_rates=SHARED_PASS_RATES,
                sector_distribution=SHARED_SECTOR_DIST,
            ),
        )

        amzn_score = V4Score(
            asset_id=amzn.id,
            opportunity_type="quality_compounder",
            conviction="high",
            rules_conviction="high",
            style="blend",
            timing_signal="neutral",
            max_position_pct=3.0,
            regime="normal",
            composite_score=0.88,
            ml_override="none",
            scored_at=datetime.now(UTC),
            published=True,
            detail=_v4_detail(
                "AMZN",
                AMZN_FILTERS,
                sector_filter_pass_rates=SHARED_PASS_RATES,
                sector_distribution=SHARED_SECTOR_DIST,
            ),
        )

        session.add_all([tsla_score, amzn_score])
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAllSectorEnhancementsOnEliminatedTicker:
    """TSLA is eliminated (has a failed filter). All 4 enhancements should appear."""

    async def test_market_cap(self, client: AsyncClient):
        """Enhancement 1: market_cap from Asset table."""
        resp = await client.get("/api/v1/scores/TSLA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["market_cap"] == 800_000_000_000.0

    async def test_sector_pass_rate_on_filters(self, client: AsyncClient):
        """Enhancement 2: sector_pass_rate injected into filter results."""
        resp = await client.get("/api/v1/scores/TSLA")
        assert resp.status_code == 200
        data = resp.json()

        beneish = next(f for f in data["filters_passed"] if f["name"] == "beneish_m_score")
        assert beneish["sector_pass_rate"] == pytest.approx(0.72)

        z_score = next(f for f in data["filters_passed"] if f["name"] == "z_score")
        assert z_score["sector_pass_rate"] == pytest.approx(0.91)

    async def test_sector_distribution_on_sub_factors(self, client: AsyncClient):
        """Enhancement 3: sector distribution (p10/p50/p90/count) on sub-factors."""
        resp = await client.get("/api/v1/scores/TSLA")
        assert resp.status_code == 200
        data = resp.json()

        quality_subs = data["quality"]["sub_scores"]
        assert len(quality_subs) >= 1
        gp = next(s for s in quality_subs if s["name"] == "gross_profitability")
        assert gp["sector_p10"] == pytest.approx(0.12)
        assert gp["sector_p50"] == pytest.approx(0.28)
        assert gp["sector_p90"] == pytest.approx(0.48)
        assert gp["sector_count"] == 85

    async def test_sector_champion(self, client: AsyncClient):
        """Enhancement 4: sector_champion populated with AMZN (highest-scoring passer)."""
        resp = await client.get("/api/v1/scores/TSLA")
        assert resp.status_code == 200
        data = resp.json()

        champion = data["sector_champion"]
        assert champion is not None
        assert champion["ticker"] == "AMZN"
        # Champion filter_values should contain the champion's filter data
        fv = champion["filter_values"]
        assert "beneish_m_score" in fv
        assert "z_score" in fv
        assert fv["beneish_m_score"] == pytest.approx(-3.1)
        assert fv["z_score"] == pytest.approx(6.2)

    async def test_all_four_enhancements_in_single_response(self, client: AsyncClient):
        """All 4 enhancements coexist in one response for an eliminated ticker."""
        resp = await client.get("/api/v1/scores/TSLA")
        assert resp.status_code == 200
        data = resp.json()

        # 1. market_cap
        assert data["market_cap"] == 800_000_000_000.0

        # 2. sector_pass_rate
        beneish = next(f for f in data["filters_passed"] if f["name"] == "beneish_m_score")
        assert beneish["sector_pass_rate"] == pytest.approx(0.72)

        # 3. sector distribution
        gp = next(s for s in data["quality"]["sub_scores"] if s["name"] == "gross_profitability")
        assert gp["sector_p10"] == pytest.approx(0.12)
        assert gp["sector_p50"] == pytest.approx(0.28)
        assert gp["sector_p90"] == pytest.approx(0.48)
        assert gp["sector_count"] == 85

        # 4. sector_champion
        champion = data["sector_champion"]
        assert champion is not None
        assert champion["ticker"] == "AMZN"


@pytest.mark.asyncio
class TestAllSectorEnhancementsOnPassingTicker:
    """AMZN passes all filters. Should get enhancements 1-3 but NOT sector champion."""

    async def test_market_cap(self, client: AsyncClient):
        """Enhancement 1: market_cap from Asset table."""
        resp = await client.get("/api/v1/scores/AMZN")
        assert resp.status_code == 200
        data = resp.json()
        assert data["market_cap"] == 2_000_000_000_000.0

    async def test_sector_pass_rate_on_filters(self, client: AsyncClient):
        """Enhancement 2: sector_pass_rate injected into filter results."""
        resp = await client.get("/api/v1/scores/AMZN")
        assert resp.status_code == 200
        data = resp.json()

        beneish = next(f for f in data["filters_passed"] if f["name"] == "beneish_m_score")
        assert beneish["sector_pass_rate"] is not None
        assert beneish["sector_pass_rate"] == pytest.approx(0.72)

    async def test_sector_distribution_on_sub_factors(self, client: AsyncClient):
        """Enhancement 3: sector distribution on sub-factors."""
        resp = await client.get("/api/v1/scores/AMZN")
        assert resp.status_code == 200
        data = resp.json()

        quality_subs = data["quality"]["sub_scores"]
        gp = next(s for s in quality_subs if s["name"] == "gross_profitability")
        assert gp["sector_p10"] is not None
        assert gp["sector_p10"] == pytest.approx(0.12)
        assert gp["sector_p50"] == pytest.approx(0.28)
        assert gp["sector_p90"] == pytest.approx(0.48)
        assert gp["sector_count"] == 85

    async def test_no_sector_champion(self, client: AsyncClient):
        """Enhancement 4: passing ticker should NOT get a sector champion."""
        resp = await client.get("/api/v1/scores/AMZN")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("sector_champion") is None

    async def test_all_enhancements_on_passing_ticker(self, client: AsyncClient):
        """Enhancements 1-3 present, enhancement 4 absent, in one response."""
        resp = await client.get("/api/v1/scores/AMZN")
        assert resp.status_code == 200
        data = resp.json()

        # 1. market_cap
        assert data["market_cap"] == 2_000_000_000_000.0

        # 2. sector_pass_rate
        beneish = next(f for f in data["filters_passed"] if f["name"] == "beneish_m_score")
        assert beneish["sector_pass_rate"] is not None

        # 3. sector distribution
        gp = next(s for s in data["quality"]["sub_scores"] if s["name"] == "gross_profitability")
        assert gp["sector_p10"] is not None

        # 4. NO sector champion for passing tickers
        assert data.get("sector_champion") is None
