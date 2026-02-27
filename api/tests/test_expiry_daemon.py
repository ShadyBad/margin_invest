"""Tests for expire_stale_approvals worker job and _expire_stale_approvals_impl."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import PipelineApproval
from margin_api.workers import _expire_stale_approvals_impl
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


def _make_approval(
    *,
    status: str = "staged",
    expires_at: datetime | None = None,
    decided_at: datetime | None = None,
    gate_type: str = "score_publish",
) -> PipelineApproval:
    """Create a PipelineApproval instance for testing."""
    return PipelineApproval(
        gate_type=gate_type,
        status=status,
        expires_at=expires_at,
        decided_at=decided_at,
    )


class TestExpireStaleApprovalsImpl:
    """Tests for _expire_stale_approvals_impl."""

    @pytest.mark.asyncio
    async def test_expires_staged_approval_past_deadline(self, db_session: AsyncSession):
        """A staged approval past its expires_at should be expired."""
        past = datetime.now(UTC) - timedelta(hours=1)
        approval = _make_approval(status="staged", expires_at=past)
        db_session.add(approval)
        await db_session.flush()
        approval_id = approval.id

        count = await _expire_stale_approvals_impl(db_session)

        assert count == 1
        result = await db_session.execute(
            select(PipelineApproval).where(PipelineApproval.id == approval_id)
        )
        expired = result.scalar_one()
        assert expired.status == "expired"
        assert expired.decided_at is not None

    @pytest.mark.asyncio
    async def test_does_not_expire_staged_with_future_deadline(self, db_session: AsyncSession):
        """A staged approval with a future expires_at should NOT be expired."""
        future = datetime.now(UTC) + timedelta(hours=6)
        approval = _make_approval(status="staged", expires_at=future)
        db_session.add(approval)
        await db_session.flush()
        approval_id = approval.id

        count = await _expire_stale_approvals_impl(db_session)

        assert count == 0
        result = await db_session.execute(
            select(PipelineApproval).where(PipelineApproval.id == approval_id)
        )
        still_staged = result.scalar_one()
        assert still_staged.status == "staged"
        assert still_staged.decided_at is None

    @pytest.mark.asyncio
    async def test_does_not_touch_approved_even_if_past_deadline(self, db_session: AsyncSession):
        """An already-approved approval should not be expired even if past expires_at."""
        past = datetime.now(UTC) - timedelta(hours=1)
        decided = datetime.now(UTC) - timedelta(minutes=30)
        approval = _make_approval(status="approved", expires_at=past, decided_at=decided)
        db_session.add(approval)
        await db_session.flush()
        approval_id = approval.id

        count = await _expire_stale_approvals_impl(db_session)

        assert count == 0
        result = await db_session.execute(
            select(PipelineApproval).where(PipelineApproval.id == approval_id)
        )
        still_approved = result.scalar_one()
        assert still_approved.status == "approved"
        assert still_approved.decided_at == decided

    @pytest.mark.asyncio
    async def test_does_not_touch_rejected_even_if_past_deadline(self, db_session: AsyncSession):
        """An already-rejected approval should not be expired even if past expires_at."""
        past = datetime.now(UTC) - timedelta(hours=1)
        decided = datetime.now(UTC) - timedelta(minutes=30)
        approval = _make_approval(status="rejected", expires_at=past, decided_at=decided)
        db_session.add(approval)
        await db_session.flush()
        approval_id = approval.id

        count = await _expire_stale_approvals_impl(db_session)

        assert count == 0
        result = await db_session.execute(
            select(PipelineApproval).where(PipelineApproval.id == approval_id)
        )
        still_rejected = result.scalar_one()
        assert still_rejected.status == "rejected"

    @pytest.mark.asyncio
    async def test_returns_correct_count_multiple(self, db_session: AsyncSession):
        """When multiple staged approvals are past deadline, count should reflect all."""
        past = datetime.now(UTC) - timedelta(hours=2)
        future = datetime.now(UTC) + timedelta(hours=2)

        # Two expired, one still valid, one already approved
        db_session.add(_make_approval(status="staged", expires_at=past))
        db_session.add(_make_approval(status="staged", expires_at=past))
        db_session.add(_make_approval(status="staged", expires_at=future))
        db_session.add(
            _make_approval(
                status="approved",
                expires_at=past,
                decided_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        await db_session.flush()

        count = await _expire_stale_approvals_impl(db_session)

        assert count == 2

    @pytest.mark.asyncio
    async def test_returns_zero_when_nothing_to_expire(self, db_session: AsyncSession):
        """When no approvals are stale, should return 0."""
        count = await _expire_stale_approvals_impl(db_session)
        assert count == 0
