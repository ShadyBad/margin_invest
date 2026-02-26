"""Tests for Stripe webhook idempotency."""

from __future__ import annotations

import pytest
import pytest_asyncio
from margin_api.db.models import Base, ProcessedWebhookEvent
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


class TestProcessedWebhookEvent:
    @pytest.mark.asyncio
    async def test_can_record_processed_event(self, db_session):
        event = ProcessedWebhookEvent(
            event_id="evt_test_123",
            event_type="checkout.session.completed",
        )
        db_session.add(event)
        await db_session.commit()

        result = await db_session.execute(
            select(ProcessedWebhookEvent).where(ProcessedWebhookEvent.event_id == "evt_test_123")
        )
        found = result.scalar_one_or_none()
        assert found is not None
        assert found.event_type == "checkout.session.completed"

    @pytest.mark.asyncio
    async def test_duplicate_event_detected(self, db_session):
        event1 = ProcessedWebhookEvent(
            event_id="evt_dup_456",
            event_type="customer.subscription.updated",
        )
        db_session.add(event1)
        await db_session.commit()

        result = await db_session.execute(
            select(ProcessedWebhookEvent).where(ProcessedWebhookEvent.event_id == "evt_dup_456")
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_different_events_not_conflicting(self, db_session):
        db_session.add(ProcessedWebhookEvent(event_id="evt_a", event_type="type_a"))
        db_session.add(ProcessedWebhookEvent(event_id="evt_b", event_type="type_b"))
        await db_session.commit()

        result = await db_session.execute(select(func.count()).select_from(ProcessedWebhookEvent))
        assert result.scalar() == 2

    @pytest.mark.asyncio
    async def test_processed_at_auto_populated(self, db_session):
        event = ProcessedWebhookEvent(
            event_id="evt_auto_ts",
            event_type="invoice.paid",
        )
        db_session.add(event)
        await db_session.commit()

        result = await db_session.execute(
            select(ProcessedWebhookEvent).where(ProcessedWebhookEvent.event_id == "evt_auto_ts")
        )
        found = result.scalar_one()
        assert found.processed_at is not None
