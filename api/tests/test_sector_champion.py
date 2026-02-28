"""Tests for sector champion feature on eliminated tickers.

Verifies that:
1. Eliminated tickers (with at least one failed filter) get a sector_champion
   populated with the highest-scoring passing ticker in the same sector.
2. Passing tickers have sector_champion == None.
3. Tickers from a different sector are never used as champion.
4. When no passing ticker exists in the sector, sector_champion is None.
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


def _v4_detail(
    ticker: str,
    filters_passed: list[dict] | None = None,
) -> dict:
    """Build a minimal V4Score.detail blob with the required fields."""
    if filters_passed is None:
        filters_passed = []
    return {
        "ticker": ticker,
        "composite_percentile": 50.0,
        "composite_raw_score": 0.5,
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
        "filters_passed": filters_passed,
        "data_coverage": 1.0,
        "growth_stage": None,
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


def _make_v4score(
    asset_id: int,
    composite_score: float = 0.5,
    filters_passed: list[dict] | None = None,
    ticker: str = "XXX",
) -> V4Score:
    """Create a V4Score with sensible defaults."""
    return V4Score(
        asset_id=asset_id,
        opportunity_type="quality_compounder",
        conviction="medium",
        rules_conviction="medium",
        style="blend",
        timing_signal="neutral",
        max_position_pct=2.0,
        regime="normal",
        composite_score=composite_score,
        ml_override="none",
        scored_at=datetime.now(UTC),
        detail=_v4_detail(ticker, filters_passed),
        published=True,
    )


async def _build_client(async_engine, seed_fn):
    """Seed the DB and return an AsyncClient with DI override."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed_fn(session)
        await session.commit()

    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
class TestSectorChampionEliminated:
    """Eliminated ticker gets sector champion from same sector."""

    async def test_eliminated_ticker_gets_sector_champion(self, async_engine):
        """TSLA (failed filters) should get AMZN (same sector, all passed) as champion."""

        async def seed(session: AsyncSession):
            tsla = Asset(
                ticker="TSLA",
                name="Tesla Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("800000000000"),
            )
            amzn = Asset(
                ticker="AMZN",
                name="Amazon.com Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("1500000000000"),
            )
            session.add_all([tsla, amzn])
            await session.flush()

            # TSLA: failed 2 filters
            tsla_filters = [
                {
                    "name": "min_market_cap",
                    "passed": True,
                    "value": 800.0,
                    "threshold": 500.0,
                    "verdict": "pass",
                },
                {
                    "name": "profitability_screen",
                    "passed": False,
                    "value": -0.02,
                    "threshold": 0.0,
                    "verdict": "fail",
                },
                {
                    "name": "liquidity_screen",
                    "passed": False,
                    "value": 0.3,
                    "threshold": 0.5,
                    "verdict": "fail",
                },
            ]
            tsla_score = _make_v4score(
                tsla.id,
                composite_score=0.45,
                filters_passed=tsla_filters,
                ticker="TSLA",
            )

            # AMZN: all filters passed, higher composite
            amzn_filters = [
                {
                    "name": "min_market_cap",
                    "passed": True,
                    "value": 1500.0,
                    "threshold": 500.0,
                    "verdict": "pass",
                },
                {
                    "name": "profitability_screen",
                    "passed": True,
                    "value": 0.08,
                    "threshold": 0.0,
                    "verdict": "pass",
                },
                {
                    "name": "liquidity_screen",
                    "passed": True,
                    "value": 0.9,
                    "threshold": 0.5,
                    "verdict": "pass",
                },
            ]
            amzn_score = _make_v4score(
                amzn.id,
                composite_score=0.88,
                filters_passed=amzn_filters,
                ticker="AMZN",
            )
            session.add_all([tsla_score, amzn_score])

        async with await _build_client(async_engine, seed) as client:
            resp = await client.get("/api/v1/scores/TSLA")

        assert resp.status_code == 200
        data = resp.json()
        assert data["sector_champion"] is not None
        assert data["sector_champion"]["ticker"] == "AMZN"
        # Verify filter_values contains the champion's filter data
        fv = data["sector_champion"]["filter_values"]
        assert "min_market_cap" in fv
        assert "profitability_screen" in fv
        assert "liquidity_screen" in fv
        assert fv["profitability_screen"] == 0.08
        assert fv["liquidity_screen"] == 0.9

    async def test_passing_ticker_has_no_sector_champion(self, async_engine):
        """A ticker that passed all filters should have sector_champion == None."""

        async def seed(session: AsyncSession):
            amzn = Asset(
                ticker="AMZN",
                name="Amazon.com Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("1500000000000"),
            )
            session.add(amzn)
            await session.flush()

            amzn_filters = [
                {
                    "name": "min_market_cap",
                    "passed": True,
                    "value": 1500.0,
                    "threshold": 500.0,
                    "verdict": "pass",
                },
                {
                    "name": "profitability_screen",
                    "passed": True,
                    "value": 0.08,
                    "threshold": 0.0,
                    "verdict": "pass",
                },
            ]
            amzn_score = _make_v4score(
                amzn.id,
                composite_score=0.88,
                filters_passed=amzn_filters,
                ticker="AMZN",
            )
            session.add(amzn_score)

        async with await _build_client(async_engine, seed) as client:
            resp = await client.get("/api/v1/scores/AMZN")

        assert resp.status_code == 200
        data = resp.json()
        assert data["sector_champion"] is None

    async def test_different_sector_not_used_as_champion(self, async_engine):
        """Champion must be from the same sector, not a higher-scoring ticker elsewhere."""

        async def seed(session: AsyncSession):
            tsla = Asset(
                ticker="TSLA",
                name="Tesla Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("800000000000"),
            )
            amzn = Asset(
                ticker="AMZN",
                name="Amazon.com Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("1500000000000"),
            )
            msft = Asset(
                ticker="MSFT",
                name="Microsoft Corp",
                sector="Information Technology",
                market_cap=Decimal("3000000000000"),
            )
            session.add_all([tsla, amzn, msft])
            await session.flush()

            # TSLA: failed a filter
            tsla_filters = [
                {
                    "name": "profitability_screen",
                    "passed": False,
                    "value": -0.02,
                    "threshold": 0.0,
                    "verdict": "fail",
                },
            ]
            tsla_score = _make_v4score(
                tsla.id, composite_score=0.40, filters_passed=tsla_filters, ticker="TSLA"
            )

            # AMZN: same sector, all passed, composite=0.75
            amzn_filters = [
                {
                    "name": "profitability_screen",
                    "passed": True,
                    "value": 0.08,
                    "threshold": 0.0,
                    "verdict": "pass",
                },
            ]
            amzn_score = _make_v4score(
                amzn.id, composite_score=0.75, filters_passed=amzn_filters, ticker="AMZN"
            )

            # MSFT: different sector, all passed, HIGHER composite=0.95
            msft_filters = [
                {
                    "name": "profitability_screen",
                    "passed": True,
                    "value": 0.12,
                    "threshold": 0.0,
                    "verdict": "pass",
                },
            ]
            msft_score = _make_v4score(
                msft.id, composite_score=0.95, filters_passed=msft_filters, ticker="MSFT"
            )
            session.add_all([tsla_score, amzn_score, msft_score])

        async with await _build_client(async_engine, seed) as client:
            resp = await client.get("/api/v1/scores/TSLA")

        assert resp.status_code == 200
        data = resp.json()
        champion = data["sector_champion"]
        assert champion is not None
        # Should pick AMZN (same sector), NOT MSFT (different sector, higher score)
        assert champion["ticker"] == "AMZN"

    async def test_no_champion_when_no_passing_ticker_in_sector(self, async_engine):
        """When all tickers in the sector fail filters, sector_champion should be None."""

        async def seed(session: AsyncSession):
            tsla = Asset(
                ticker="TSLA",
                name="Tesla Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("800000000000"),
            )
            gm = Asset(
                ticker="GM",
                name="General Motors Co.",
                sector="Consumer Discretionary",
                market_cap=Decimal("50000000000"),
            )
            session.add_all([tsla, gm])
            await session.flush()

            fail_filters = [
                {
                    "name": "profitability_screen",
                    "passed": False,
                    "value": -0.01,
                    "threshold": 0.0,
                    "verdict": "fail",
                },
            ]
            tsla_score = _make_v4score(
                tsla.id, composite_score=0.40, filters_passed=fail_filters, ticker="TSLA"
            )
            gm_score = _make_v4score(
                gm.id, composite_score=0.55, filters_passed=fail_filters, ticker="GM"
            )
            session.add_all([tsla_score, gm_score])

        async with await _build_client(async_engine, seed) as client:
            resp = await client.get("/api/v1/scores/TSLA")

        assert resp.status_code == 200
        data = resp.json()
        assert data["sector_champion"] is None

    async def test_champion_picks_highest_scorer_among_passing(self, async_engine):
        """When multiple tickers pass all filters, champion should be the one with highest score."""

        async def seed(session: AsyncSession):
            tsla = Asset(
                ticker="TSLA",
                name="Tesla Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("800000000000"),
            )
            amzn = Asset(
                ticker="AMZN",
                name="Amazon.com Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("1500000000000"),
            )
            hd = Asset(
                ticker="HD",
                name="Home Depot Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("350000000000"),
            )
            session.add_all([tsla, amzn, hd])
            await session.flush()

            # TSLA: failed
            tsla_filters = [
                {
                    "name": "profitability_screen",
                    "passed": False,
                    "value": -0.01,
                    "threshold": 0.0,
                    "verdict": "fail",
                },
            ]
            tsla_score = _make_v4score(
                tsla.id, composite_score=0.40, filters_passed=tsla_filters, ticker="TSLA"
            )

            # AMZN: all passed, composite=0.88
            pass_filters = [
                {
                    "name": "profitability_screen",
                    "passed": True,
                    "value": 0.08,
                    "threshold": 0.0,
                    "verdict": "pass",
                },
            ]
            amzn_score = _make_v4score(
                amzn.id, composite_score=0.88, filters_passed=pass_filters, ticker="AMZN"
            )

            # HD: all passed, composite=0.72 (lower than AMZN)
            hd_score = _make_v4score(
                hd.id, composite_score=0.72, filters_passed=pass_filters, ticker="HD"
            )
            session.add_all([tsla_score, amzn_score, hd_score])

        async with await _build_client(async_engine, seed) as client:
            resp = await client.get("/api/v1/scores/TSLA")

        assert resp.status_code == 200
        data = resp.json()
        champion = data["sector_champion"]
        assert champion is not None
        # AMZN has higher composite_score than HD
        assert champion["ticker"] == "AMZN"

    async def test_champion_skips_failing_higher_scorer(self, async_engine):
        """If the highest-scoring ticker also fails filters, skip it and pick the next one."""

        async def seed(session: AsyncSession):
            tsla = Asset(
                ticker="TSLA",
                name="Tesla Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("800000000000"),
            )
            amzn = Asset(
                ticker="AMZN",
                name="Amazon.com Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("1500000000000"),
            )
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
                    "value": -0.01,
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

            # TSLA: failed
            tsla_score = _make_v4score(
                tsla.id, composite_score=0.40, filters_passed=fail_filters, ticker="TSLA"
            )
            # AMZN: highest score but ALSO failed
            amzn_score = _make_v4score(
                amzn.id, composite_score=0.90, filters_passed=fail_filters, ticker="AMZN"
            )
            # HD: lower score but passed all filters
            hd_score = _make_v4score(
                hd.id, composite_score=0.72, filters_passed=pass_filters, ticker="HD"
            )
            session.add_all([tsla_score, amzn_score, hd_score])

        async with await _build_client(async_engine, seed) as client:
            resp = await client.get("/api/v1/scores/TSLA")

        assert resp.status_code == 200
        data = resp.json()
        champion = data["sector_champion"]
        assert champion is not None
        # AMZN has higher score but fails filters; HD passes
        assert champion["ticker"] == "HD"

    async def test_champion_none_when_no_filters_on_champion(self, async_engine):
        """If potential champion has empty filters_passed, it should not be selected."""

        async def seed(session: AsyncSession):
            tsla = Asset(
                ticker="TSLA",
                name="Tesla Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("800000000000"),
            )
            amzn = Asset(
                ticker="AMZN",
                name="Amazon.com Inc.",
                sector="Consumer Discretionary",
                market_cap=Decimal("1500000000000"),
            )
            session.add_all([tsla, amzn])
            await session.flush()

            fail_filters = [
                {
                    "name": "profitability_screen",
                    "passed": False,
                    "value": -0.01,
                    "threshold": 0.0,
                    "verdict": "fail",
                },
            ]
            tsla_score = _make_v4score(
                tsla.id, composite_score=0.40, filters_passed=fail_filters, ticker="TSLA"
            )
            # AMZN: no filters (empty list) — should not be champion
            amzn_score = _make_v4score(
                amzn.id, composite_score=0.88, filters_passed=[], ticker="AMZN"
            )
            session.add_all([tsla_score, amzn_score])

        async with await _build_client(async_engine, seed) as client:
            resp = await client.get("/api/v1/scores/TSLA")

        assert resp.status_code == 200
        data = resp.json()
        assert data["sector_champion"] is None
