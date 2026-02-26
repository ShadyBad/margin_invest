"""Tests for audit logging."""

from __future__ import annotations

import pytest
import pytest_asyncio
from margin_api.db.models import AuditLog, Base
from margin_api.services.audit import audit_log
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


class TestAuditLog:
    @pytest.mark.asyncio
    async def test_creates_log_entry(self, db_session):
        await audit_log(db_session, "login_success", user_id=42)
        await db_session.commit()

        result = await db_session.execute(select(AuditLog))
        entry = result.scalar_one()
        assert entry.event_type == "login_success"
        assert entry.user_id == 42

    @pytest.mark.asyncio
    async def test_stores_detail_dict(self, db_session):
        await audit_log(
            db_session,
            "login_failure",
            detail={"email": "test@test.com", "reason": "bad password"},
        )
        await db_session.commit()

        result = await db_session.execute(select(AuditLog))
        entry = result.scalar_one()
        assert entry.detail["email"] == "test@test.com"
        assert entry.detail["reason"] == "bad password"

    @pytest.mark.asyncio
    async def test_handles_none_request(self, db_session):
        await audit_log(db_session, "test_event", request=None, user_id=1)
        await db_session.commit()

        result = await db_session.execute(select(AuditLog))
        entry = result.scalar_one()
        assert entry.ip_address is None
        assert entry.user_agent is None

    @pytest.mark.asyncio
    async def test_multiple_entries(self, db_session):
        await audit_log(db_session, "event_a", user_id=1)
        await audit_log(db_session, "event_b", user_id=2)
        await db_session.commit()

        result = await db_session.execute(select(func.count()).select_from(AuditLog))
        assert result.scalar() == 2

    @pytest.mark.asyncio
    async def test_created_at_auto_populated(self, db_session):
        await audit_log(db_session, "register", user_id=10)
        await db_session.commit()

        result = await db_session.execute(select(AuditLog))
        entry = result.scalar_one()
        assert entry.created_at is not None

    @pytest.mark.asyncio
    async def test_does_not_commit(self, db_session):
        """audit_log should add but not commit -- caller controls transaction."""
        await audit_log(db_session, "uncommitted_event", user_id=99)
        # Rollback instead of commit
        await db_session.rollback()

        result = await db_session.execute(select(func.count()).select_from(AuditLog))
        assert result.scalar() == 0
