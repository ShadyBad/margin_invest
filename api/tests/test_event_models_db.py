"""Tests for Event and Notification DB models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Event, Notification
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def _make_event(**overrides) -> Event:
    """Build an Event with sensible defaults, overridable via kwargs."""
    defaults = dict(
        event_id="evt-001",
        event_type="score_change",
        ticker="AAPL",
        timestamp=datetime.now(UTC),
        severity="medium",
        source="v4_worker",
        payload=None,
    )
    defaults.update(overrides)
    return Event(**defaults)


class TestEventModel:
    @pytest.mark.asyncio
    async def test_insert_and_retrieve_by_event_id(self, db):
        event = _make_event()
        db.add(event)
        await db.commit()

        result = await db.execute(select(Event).where(Event.event_id == "evt-001"))
        loaded = result.scalar_one()
        assert loaded.event_type == "score_change"
        assert loaded.ticker == "AAPL"
        assert loaded.severity == "medium"
        assert loaded.source == "v4_worker"

    @pytest.mark.asyncio
    async def test_payload_json_roundtrip(self, db):
        payload = {
            "old_score": 42.5,
            "new_score": 67.8,
            "delta": 25.3,
            "factors": ["quality", "momentum"],
        }
        event = _make_event(event_id="evt-json", payload=payload)
        db.add(event)
        await db.commit()

        result = await db.execute(select(Event).where(Event.event_id == "evt-json"))
        loaded = result.scalar_one()
        assert loaded.payload == payload
        assert loaded.payload["factors"] == ["quality", "momentum"]

    @pytest.mark.asyncio
    async def test_created_at_defaults_to_now(self, db):
        before = datetime.now(UTC)
        event = _make_event(event_id="evt-ts")
        db.add(event)
        await db.commit()
        await db.refresh(event)
        after = datetime.now(UTC)
        assert before <= event.created_at.replace(tzinfo=UTC) <= after


class TestNotificationModel:
    @pytest.mark.asyncio
    async def test_notification_links_to_event(self, db):
        event = _make_event(event_id="evt-notif")
        db.add(event)
        await db.commit()
        await db.refresh(event)

        notif = Notification(
            notification_id="ntf-001",
            event_id=event.id,
        )
        db.add(notif)
        await db.commit()
        await db.refresh(notif, ["event"])

        assert notif.event.event_id == "evt-notif"
        assert notif.event.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_notification_defaults_to_unread(self, db):
        event = _make_event(event_id="evt-read")
        db.add(event)
        await db.commit()
        await db.refresh(event)

        notif = Notification(
            notification_id="ntf-read",
            event_id=event.id,
        )
        db.add(notif)
        await db.commit()
        await db.refresh(notif)

        assert notif.read is False

    @pytest.mark.asyncio
    async def test_event_notifications_relationship(self, db):
        event = _make_event(event_id="evt-rel")
        db.add(event)
        await db.commit()
        await db.refresh(event)

        n1 = Notification(notification_id="ntf-a", event_id=event.id)
        n2 = Notification(notification_id="ntf-b", event_id=event.id)
        db.add_all([n1, n2])
        await db.commit()

        result = await db.execute(select(Event).where(Event.event_id == "evt-rel"))
        loaded_event = result.scalar_one()
        await db.refresh(loaded_event, ["notifications"])
        assert len(loaded_event.notifications) == 2
        ids = {n.notification_id for n in loaded_event.notifications}
        assert ids == {"ntf-a", "ntf-b"}
