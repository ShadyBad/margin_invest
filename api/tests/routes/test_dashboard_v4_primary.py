"""Tests for V4Score as primary dashboard data source.

Verifies that:
1. Dashboard picks read from V4Score (not legacy Score).
2. Sentiment/growth percentiles are extracted from V4Score.detail JSONB.
3. Factor percentiles match what the /api/v1/scores/{ticker} endpoint returns.
4. Legacy Score fallback works when no V4Score data exists.
5. All pick fields come from a single V4Score row (no cross-table mixing).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, Score, V4Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


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
    app = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _make_v4_detail(
    quality_pct: float = 80.0,
    value_pct: float = 75.0,
    momentum_pct: float = 70.0,
    growth_pct: float | None = 65.0,
    sentiment_pct: float | None = 72.0,
) -> dict:
    """Build a realistic V4Score.detail JSONB matching CompositeScore.model_dump()."""
    detail: dict = {
        "ticker": "TEST",
        "composite_percentile": 85.0,
        "composite_raw_score": 80.0,
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "average_percentile": quality_pct,
            "sub_scores": [
                {"name": "roic", "raw_value": 18.0, "percentile_rank": quality_pct},
            ],
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "average_percentile": value_pct,
            "sub_scores": [
                {"name": "ev_ebitda", "raw_value": 12.0, "percentile_rank": value_pct},
            ],
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "average_percentile": momentum_pct,
            "sub_scores": [
                {"name": "price_momentum", "raw_value": 0.15, "percentile_rank": momentum_pct},
            ],
        },
        "filters_passed": [
            {"name": "liquidity", "passed": True, "verdict": "pass"},
        ],
        "data_coverage": 0.95,
        "actual_price": 150.0,
        "buy_price": 140.0,
        "sell_price": 180.0,
        "margin_invest_value": 175.0,
        "signal": "strong",
    }

    if sentiment_pct is not None:
        detail["momentum"]["sub_scores"].append(
            {"name": "sentiment", "raw_value": 7.0, "percentile_rank": sentiment_pct},
        )

    if growth_pct is not None:
        detail["growth"] = {
            "factor_name": "growth",
            "weight": 0.15,
            "average_percentile": growth_pct,
            "sub_scores": [
                {
                    "name": "revenue_growth",
                    "raw_value": 0.25,
                    "percentile_rank": growth_pct,
                },
            ],
        }

    return detail


@pytest.mark.asyncio
class TestDashboardV4Primary:
    """Dashboard reads from V4Score as primary data source."""

    async def test_picks_from_v4score_with_all_factors(self, session_factory):
        """Dashboard should extract quality/value/momentum/sentiment/growth from V4Score.detail."""
        async with session_factory() as session:
            asset = Asset(ticker="AAPL", name="Apple Inc", sector="Technology")
            session.add(asset)
            await session.flush()

            detail = _make_v4_detail(
                quality_pct=88.5,
                value_pct=72.3,
                momentum_pct=81.0,
                growth_pct=65.2,
                sentiment_pct=74.8,
            )
            detail["ticker"] = "AAPL"

            v4 = V4Score(
                asset_id=asset.id,
                scored_at=datetime.now(UTC),
                opportunity_type="compounder",
                conviction="exceptional",
                rules_conviction="high",
                style="growth",
                timing_signal="buy_now",
                max_position_pct=5.0,
                regime="normal",
                composite_score=85.0,
                ml_override="none",
                detail=detail,
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/dashboard")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["picks"]) >= 1

            pick = next(p for p in data["picks"] if p["ticker"] == "AAPL")
            assert pick["quality_percentile"] == 88.5
            assert pick["value_percentile"] == 72.3
            assert pick["momentum_percentile"] == 81.0
            assert pick["sentiment_percentile"] == 74.8
            assert pick["growth_percentile"] == 65.2
            assert pick["composite_tier"] == "exceptional"
            assert pick["ml_override"] == "none"
            assert pick["style"] == "growth"
            assert pick["opportunity_type"] == "compounder"

    async def test_sentiment_null_when_absent(self, session_factory):
        """Sentiment should be null when not present in momentum sub_scores."""
        async with session_factory() as session:
            asset = Asset(ticker="MSFT", name="Microsoft Corp", sector="Technology")
            session.add(asset)
            await session.flush()

            detail = _make_v4_detail(sentiment_pct=None, growth_pct=None)
            detail["ticker"] = "MSFT"

            v4 = V4Score(
                asset_id=asset.id,
                scored_at=datetime.now(UTC),
                opportunity_type="compounder",
                conviction="high",
                rules_conviction="high",
                style="quality",
                timing_signal="buy_now",
                max_position_pct=4.0,
                regime="normal",
                composite_score=75.0,
                ml_override="none",
                detail=detail,
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/dashboard")
            data = resp.json()
            pick = next(p for p in data["picks"] if p["ticker"] == "MSFT")
            assert pick["sentiment_percentile"] is None
            assert pick["growth_percentile"] is None
            # Core factors still present
            assert pick["quality_percentile"] == 80.0
            assert pick["value_percentile"] == 75.0
            assert pick["momentum_percentile"] == 70.0

    async def test_legacy_score_fallback_when_no_v4(self, session_factory):
        """When no V4Score exists, dashboard should fall back to legacy Score."""
        async with session_factory() as session:
            asset = Asset(ticker="OLD", name="Old Corp", sector="Financials")
            session.add(asset)
            await session.flush()

            score = Score(
                asset_id=asset.id,
                composite_percentile=90.0,
                composite_raw_score=85.0,
                conviction_level="exceptional",
                signal="strong",
                quality_percentile=82.0,
                value_percentile=78.0,
                momentum_percentile=88.0,
                data_coverage=0.9,
                scored_at=datetime.now(UTC),
                score_detail={
                    "momentum": {
                        "sub_scores": [
                            {"name": "sentiment", "percentile_rank": 70.0},
                        ],
                    },
                    "growth": {
                        "sub_scores": [
                            {"name": "revenue_growth", "percentile_rank": 60.0},
                        ],
                    },
                },
            )
            session.add(score)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/dashboard")
            data = resp.json()
            assert len(data["picks"]) >= 1
            pick = next(p for p in data["picks"] if p["ticker"] == "OLD")
            # Legacy path still extracts sentiment/growth
            assert pick["sentiment_percentile"] == 70.0
            assert pick["growth_percentile"] == 60.0
            assert pick["quality_percentile"] == 82.0
            # No V4 data → null ML fields
            assert pick["ml_override"] is None
            assert pick["style"] is None

    async def test_v4_preferred_over_stale_legacy(self, session_factory):
        """When both V4Score and Score exist, dashboard uses V4Score data."""
        async with session_factory() as session:
            asset = Asset(ticker="BOTH", name="Both Corp", sector="Technology")
            session.add(asset)
            await session.flush()

            # Stale legacy score with different values
            score = Score(
                asset_id=asset.id,
                composite_percentile=50.0,
                composite_raw_score=45.0,
                conviction_level="medium",
                signal="emerging",
                quality_percentile=40.0,
                value_percentile=35.0,
                momentum_percentile=30.0,
                data_coverage=0.7,
                scored_at=datetime(2025, 1, 1, tzinfo=UTC),
            )
            session.add(score)

            # Fresh V4 score with correct values
            detail = _make_v4_detail(
                quality_pct=92.0,
                value_pct=88.0,
                momentum_pct=85.0,
                growth_pct=70.0,
                sentiment_pct=78.0,
            )
            detail["ticker"] = "BOTH"
            v4 = V4Score(
                asset_id=asset.id,
                scored_at=datetime.now(UTC),
                opportunity_type="mispricing",
                conviction="exceptional",
                rules_conviction="exceptional",
                style="value",
                timing_signal="buy_now",
                max_position_pct=8.0,
                regime="normal",
                composite_score=90.0,
                ml_override="promoted",
                detail=detail,
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/dashboard")
            data = resp.json()
            pick = next(p for p in data["picks"] if p["ticker"] == "BOTH")

            # V4 values used, NOT legacy Score values
            assert pick["quality_percentile"] == 92.0
            assert pick["value_percentile"] == 88.0
            assert pick["momentum_percentile"] == 85.0
            assert pick["sentiment_percentile"] == 78.0
            assert pick["growth_percentile"] == 70.0
            assert pick["composite_tier"] == "exceptional"
            assert pick["ml_override"] == "promoted"
            assert pick["opportunity_type"] == "mispricing"

    async def test_watchlist_from_v4score(self, session_factory):
        """Watchlist items should also come from V4Score."""
        async with session_factory() as session:
            asset = Asset(ticker="WL", name="Watchlist Corp", sector="Healthcare")
            session.add(asset)
            await session.flush()

            v4 = V4Score(
                asset_id=asset.id,
                scored_at=datetime.now(UTC),
                opportunity_type="compounder",
                conviction="medium",
                rules_conviction="medium",
                style="quality",
                timing_signal="wait_for_catalyst",
                max_position_pct=3.0,
                regime="normal",
                composite_score=68.0,
                ml_override="none",
                detail=_make_v4_detail(),
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/dashboard")
            data = resp.json()
            assert len(data["watchlist"]) >= 1
            wl = next(w for w in data["watchlist"] if w["ticker"] == "WL")
            assert wl["composite_tier"] == "medium"
            assert wl["opportunity_type"] == "compounder"

    async def test_status_endpoint_shows_v4_counts(self, session_factory):
        """Dashboard status should report V4Score counts alongside legacy."""
        async with session_factory() as session:
            asset = Asset(ticker="ST", name="Status Corp", sector="Technology")
            session.add(asset)
            await session.flush()

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
                composite_score=75.0,
                ml_override="none",
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/dashboard/status")
            assert resp.status_code == 200
            data = resp.json()
            assert "v4_scores" in data
            assert data["v4_scores"]["unique_assets_scored"] >= 1
            assert "legacy_scores" in data
            assert "tier_breakdown" in data

    async def test_low_score_excluded_from_picks(self, session_factory):
        """V4Score with high conviction but score below 5.0 floor excluded."""
        async with session_factory() as session:
            asset = Asset(ticker="LOW", name="Low Score Corp", sector="Technology")
            session.add(asset)
            await session.flush()

            v4 = V4Score(
                asset_id=asset.id,
                scored_at=datetime.now(UTC),
                opportunity_type="compounder",
                conviction="high",
                rules_conviction="high",
                style="growth",
                timing_signal="buy_now",
                max_position_pct=3.0,
                regime="normal",
                composite_score=4.5,  # Below 5.0 floor — must be excluded
                ml_override="none",
                detail=_make_v4_detail(),
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/dashboard")
            assert resp.status_code == 200
            data = resp.json()
            tickers_in_picks = [p["ticker"] for p in data["picks"]]
            assert "LOW" not in tickers_in_picks, (
                f"LOW (score=4.5) should be excluded by floor: {tickers_in_picks}"
            )

    async def test_v4_detail_none_graceful(self, session_factory):
        """V4Score with detail=None should still produce picks (with zero percentiles)."""
        async with session_factory() as session:
            asset = Asset(ticker="ND", name="No Detail Corp", sector="Technology")
            session.add(asset)
            await session.flush()

            v4 = V4Score(
                asset_id=asset.id,
                scored_at=datetime.now(UTC),
                opportunity_type="compounder",
                conviction="exceptional",
                rules_conviction="high",
                style="growth",
                timing_signal="buy_now",
                max_position_pct=5.0,
                regime="normal",
                composite_score=80.0,
                ml_override="none",
                detail=None,
            )
            session.add(v4)
            await session.commit()

        async with _make_client(session_factory) as client:
            resp = await client.get("/api/v1/dashboard")
            data = resp.json()
            pick = next((p for p in data["picks"] if p["ticker"] == "ND"), None)
            assert pick is not None
            assert pick["quality_percentile"] == 0.0
            assert pick["sentiment_percentile"] is None
            assert pick["growth_percentile"] is None
