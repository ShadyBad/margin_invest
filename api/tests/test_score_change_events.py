"""Tests for score change event emission and WebSocket broadcasting."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, Event, Notification, Score
from margin_api.workers import _broadcast_score_events, _emit_score_change_events
from sqlalchemy import select
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


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


async def _create_asset(session: AsyncSession, ticker: str = "AAPL") -> Asset:
    """Create a test asset."""
    asset = Asset(
        ticker=ticker,
        name=f"{ticker} Inc.",
        sector="Technology",
        market_cap=Decimal("1000000000"),
    )
    session.add(asset)
    await session.flush()
    return asset


async def _create_score(
    session: AsyncSession,
    asset: Asset,
    composite_percentile: float,
    conviction_level: str = "moderate",
    scored_at: datetime | None = None,
) -> Score:
    """Create a test score."""
    score = Score(
        asset_id=asset.id,
        composite_percentile=composite_percentile,
        composite_raw_score=composite_percentile / 100.0,
        conviction_level=conviction_level,
        signal="strong" if composite_percentile > 50 else "stable",
        scored_at=scored_at or datetime.now(UTC),
    )
    session.add(score)
    await session.flush()
    return score


class TestEmitScoreChangeEvents:
    @pytest.mark.asyncio
    async def test_emit_score_change_events_creates_event(self, db_session):
        """When delta > 5, a score_change event should be created with correct payload."""
        asset = await _create_asset(db_session, "AAPL")
        now = datetime.now(UTC)
        await _create_score(
            db_session,
            asset,
            composite_percentile=50.0,
            conviction_level="moderate",
            scored_at=now - timedelta(days=1),
        )
        await _create_score(
            db_session,
            asset,
            composite_percentile=70.0,
            conviction_level="high",
            scored_at=now,
        )
        await db_session.commit()

        n_events = await _emit_score_change_events(db_session)

        assert n_events == 1

        result = await db_session.execute(select(Event))
        events = result.scalars().all()
        assert len(events) == 1

        event = events[0]
        assert event.event_type == "score_change"
        assert event.ticker == "AAPL"
        assert event.source == "scoring_pipeline"

        payload = event.payload
        assert payload["old_score"] == 50.0
        assert payload["new_score"] == 70.0
        assert payload["delta"] == 20.0
        assert payload["old_composite_tier"] == "moderate"
        assert payload["new_composite_tier"] == "high"

    @pytest.mark.asyncio
    async def test_emit_ignores_small_delta(self, db_session):
        """When abs(delta) <= 5, no event should be created."""
        asset = await _create_asset(db_session, "MSFT")
        now = datetime.now(UTC)
        await _create_score(
            db_session,
            asset,
            composite_percentile=50.0,
            scored_at=now - timedelta(days=1),
        )
        await _create_score(
            db_session,
            asset,
            composite_percentile=54.0,
            scored_at=now,
        )
        await db_session.commit()

        n_events = await _emit_score_change_events(db_session)

        assert n_events == 0

        result = await db_session.execute(select(Event))
        events = result.scalars().all()
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_emit_ignores_exact_threshold(self, db_session):
        """When abs(delta) == 5.0 exactly, no event should be created."""
        asset = await _create_asset(db_session, "GOOG")
        now = datetime.now(UTC)
        await _create_score(
            db_session,
            asset,
            composite_percentile=50.0,
            scored_at=now - timedelta(days=1),
        )
        await _create_score(
            db_session,
            asset,
            composite_percentile=55.0,
            scored_at=now,
        )
        await db_session.commit()

        n_events = await _emit_score_change_events(db_session)
        assert n_events == 0

    @pytest.mark.asyncio
    async def test_emit_creates_notification(self, db_session):
        """A Notification should also be created alongside the Event."""
        asset = await _create_asset(db_session, "NVDA")
        now = datetime.now(UTC)
        await _create_score(
            db_session,
            asset,
            composite_percentile=80.0,
            scored_at=now - timedelta(days=1),
        )
        await _create_score(
            db_session,
            asset,
            composite_percentile=60.0,
            scored_at=now,
        )
        await db_session.commit()

        n_events = await _emit_score_change_events(db_session)
        assert n_events == 1

        result = await db_session.execute(select(Notification))
        notifications = result.scalars().all()
        assert len(notifications) == 1

        # Verify the notification references the event
        notif = notifications[0]
        event_result = await db_session.execute(select(Event))
        event = event_result.scalar_one()
        assert notif.event_id == event.id

    @pytest.mark.asyncio
    async def test_emit_skips_assets_with_single_score(self, db_session):
        """Assets with only one score should be skipped (no previous to compare)."""
        asset = await _create_asset(db_session, "AMZN")
        await _create_score(
            db_session,
            asset,
            composite_percentile=90.0,
        )
        await db_session.commit()

        n_events = await _emit_score_change_events(db_session)
        assert n_events == 0

    @pytest.mark.asyncio
    async def test_emit_handles_multiple_assets(self, db_session):
        """Multiple assets with large deltas should each produce an event."""
        now = datetime.now(UTC)

        asset1 = await _create_asset(db_session, "AAPL")
        await _create_score(
            db_session, asset1, composite_percentile=30.0, scored_at=now - timedelta(days=1)
        )
        await _create_score(db_session, asset1, composite_percentile=50.0, scored_at=now)

        asset2 = await _create_asset(db_session, "GOOG")
        await _create_score(
            db_session, asset2, composite_percentile=70.0, scored_at=now - timedelta(days=1)
        )
        await _create_score(db_session, asset2, composite_percentile=40.0, scored_at=now)

        # Small delta -- should NOT produce event
        asset3 = await _create_asset(db_session, "MSFT")
        await _create_score(
            db_session, asset3, composite_percentile=50.0, scored_at=now - timedelta(days=1)
        )
        await _create_score(db_session, asset3, composite_percentile=52.0, scored_at=now)

        await db_session.commit()

        n_events = await _emit_score_change_events(db_session)
        assert n_events == 2

        result = await db_session.execute(select(Event).order_by(Event.ticker))
        events = result.scalars().all()
        tickers = [e.ticker for e in events]
        assert "AAPL" in tickers
        assert "GOOG" in tickers
        assert "MSFT" not in tickers

    @pytest.mark.asyncio
    async def test_emit_negative_delta(self, db_session):
        """A negative delta (score drop) > 5 should also create an event."""
        asset = await _create_asset(db_session, "META")
        now = datetime.now(UTC)
        await _create_score(
            db_session,
            asset,
            composite_percentile=75.0,
            conviction_level="high",
            scored_at=now - timedelta(days=1),
        )
        await _create_score(
            db_session,
            asset,
            composite_percentile=60.0,
            conviction_level="moderate",
            scored_at=now,
        )
        await db_session.commit()

        n_events = await _emit_score_change_events(db_session)
        assert n_events == 1

        result = await db_session.execute(select(Event))
        event = result.scalar_one()
        assert event.payload["delta"] == -15.0


class TestBroadcastScoreEvents:
    @pytest.mark.asyncio
    async def test_broadcast_score_events(self, db_session):
        """Broadcast should call manager.broadcast with correct ScoreChangeMessage."""
        # First create an asset and scores to generate events
        asset = await _create_asset(db_session, "TSLA")
        now = datetime.now(UTC)
        await _create_score(
            db_session,
            asset,
            composite_percentile=40.0,
            conviction_level="low",
            scored_at=now - timedelta(days=1),
        )
        await _create_score(
            db_session,
            asset,
            composite_percentile=65.0,
            conviction_level="high",
            scored_at=now,
        )
        await db_session.commit()

        # Emit the events first
        n_events = await _emit_score_change_events(db_session)
        assert n_events == 1

        # Now broadcast
        with patch("margin_api.workers.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            n_broadcast = await _broadcast_score_events(db_session)

        assert n_broadcast == 1
        mock_manager.broadcast.assert_called_once()

        msg = mock_manager.broadcast.call_args[0][0]
        assert msg.ticker == "TSLA"
        assert msg.old_score == 40.0
        assert msg.new_score == 65.0
        assert msg.delta == 25.0

    @pytest.mark.asyncio
    async def test_broadcast_ignores_old_events(self, db_session):
        """Events older than 5 minutes should not be broadcast."""
        from margin_api.routes.events import add_event

        event_db = await add_event(
            db_session,
            event_type="score_change",
            ticker="OLD",
            severity="minor",
            source="test",
            payload={"old_score": 50.0, "new_score": 60.0, "delta": 10.0},
            timestamp=datetime.now(UTC) - timedelta(minutes=10),
        )
        # Manually set created_at to be old
        event_db.created_at = datetime.now(UTC) - timedelta(minutes=10)
        await db_session.commit()

        with patch("margin_api.workers.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            n_broadcast = await _broadcast_score_events(db_session)

        assert n_broadcast == 0
        mock_manager.broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_only_score_change_events(self, db_session):
        """Only score_change events should be broadcast, not other event types."""
        from margin_api.routes.events import add_event

        # Create a non-score_change event
        await add_event(
            db_session,
            event_type="earnings_release",
            ticker="AAPL",
            severity="major",
            source="test",
        )
        await db_session.commit()

        with patch("margin_api.workers.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()
            n_broadcast = await _broadcast_score_events(db_session)

        assert n_broadcast == 0
        mock_manager.broadcast.assert_not_called()
