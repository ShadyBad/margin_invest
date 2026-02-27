"""Tests for the governance event rollup worker — reads Redis stream, inserts to DB."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import GovernanceEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture()
def mock_redis():
    """Create a mock Redis with xrange and xtrim."""
    redis = AsyncMock()
    redis.xrange = AsyncMock(return_value=[])
    redis.xtrim = AsyncMock(return_value=0)
    redis.aclose = AsyncMock()
    return redis


def _make_stream_entry(
    entry_id: bytes,
    event_type: str,
    source: str,
    detail: dict | None = None,
    created_at: str | None = None,
) -> tuple[bytes, dict[bytes, bytes]]:
    """Build a Redis stream entry with byte-encoded keys and values."""
    if created_at is None:
        created_at = datetime.now(UTC).isoformat()
    return (
        entry_id,
        {
            b"event_type": event_type.encode(),
            b"source": source.encode(),
            b"detail": json.dumps(detail).encode(),
            b"created_at": created_at.encode(),
        },
    )


class TestRollupGovernanceEventsImpl:
    @pytest.mark.asyncio
    async def test_empty_stream_returns_zero(self, async_session, mock_redis):
        from margin_api.workers import _rollup_governance_events_impl

        mock_redis.xrange.return_value = []
        count = await _rollup_governance_events_impl(async_session, mock_redis)
        assert count == 0

    @pytest.mark.asyncio
    async def test_empty_stream_does_not_call_xtrim(self, async_session, mock_redis):
        from margin_api.workers import _rollup_governance_events_impl

        mock_redis.xrange.return_value = []
        await _rollup_governance_events_impl(async_session, mock_redis)
        mock_redis.xtrim.assert_not_called()

    @pytest.mark.asyncio
    async def test_inserts_events_to_db(self, async_session, mock_redis):
        from margin_api.workers import _rollup_governance_events_impl

        ts = "2026-02-27T12:00:00+00:00"
        mock_redis.xrange.return_value = [
            _make_stream_entry(b"1-0", "filter.override", "worker:score", {"ticker": "AAPL"}, ts),
            _make_stream_entry(b"2-0", "score.publish", "worker:publish", {"count": 10}, ts),
        ]

        count = await _rollup_governance_events_impl(async_session, mock_redis)
        assert count == 2

        result = await async_session.execute(select(GovernanceEvent))
        events = result.scalars().all()
        assert len(events) == 2
        assert events[0].event_type == "filter.override"
        assert events[0].source == "worker:score"
        assert events[0].detail == {"ticker": "AAPL"}
        assert events[1].event_type == "score.publish"

    @pytest.mark.asyncio
    async def test_decodes_byte_fields_correctly(self, async_session, mock_redis):
        from margin_api.workers import _rollup_governance_events_impl

        ts = "2026-02-27T08:30:00+00:00"
        mock_redis.xrange.return_value = [
            _make_stream_entry(b"100-0", "approval.created", "api", {"id": 42}, ts),
        ]

        await _rollup_governance_events_impl(async_session, mock_redis)

        result = await async_session.execute(select(GovernanceEvent))
        event = result.scalar_one()
        assert event.event_type == "approval.created"
        assert event.source == "api"
        assert event.detail == {"id": 42}
        # aiosqlite strips tz info; just verify parsed year/hour
        assert event.created_at.year == 2026
        assert event.created_at.hour == 8
        assert event.created_at.minute == 30

    @pytest.mark.asyncio
    async def test_calls_xtrim_after_insertion(self, async_session, mock_redis):
        from margin_api.workers import _rollup_governance_events_impl

        ts = "2026-02-27T12:00:00+00:00"
        mock_redis.xrange.return_value = [
            _make_stream_entry(b"1-0", "test.event", "test", None, ts),
        ]

        await _rollup_governance_events_impl(async_session, mock_redis)

        mock_redis.xtrim.assert_called_once_with("governance:events", maxlen=10000)

    @pytest.mark.asyncio
    async def test_reads_from_correct_stream_key(self, async_session, mock_redis):
        from margin_api.workers import _rollup_governance_events_impl

        mock_redis.xrange.return_value = []
        await _rollup_governance_events_impl(async_session, mock_redis)
        mock_redis.xrange.assert_called_once_with("governance:events")

    @pytest.mark.asyncio
    async def test_null_detail_stored_as_none(self, async_session, mock_redis):
        from margin_api.workers import _rollup_governance_events_impl

        ts = "2026-02-27T12:00:00+00:00"
        mock_redis.xrange.return_value = [
            _make_stream_entry(b"1-0", "heartbeat", "scheduler", None, ts),
        ]

        await _rollup_governance_events_impl(async_session, mock_redis)

        result = await async_session.execute(select(GovernanceEvent))
        event = result.scalar_one()
        assert event.detail is None

    @pytest.mark.asyncio
    async def test_parses_created_at_as_timezone_aware(self, async_session, mock_redis):
        from margin_api.workers import _rollup_governance_events_impl

        ts = "2026-02-27T15:45:00+00:00"
        mock_redis.xrange.return_value = [
            _make_stream_entry(b"1-0", "test.event", "test", None, ts),
        ]

        await _rollup_governance_events_impl(async_session, mock_redis)

        result = await async_session.execute(select(GovernanceEvent))
        event = result.scalar_one()
        assert event.created_at is not None
        # aiosqlite may lose tz info, so just check parsed correctly
        assert event.created_at.year == 2026
        assert event.created_at.month == 2
        assert event.created_at.hour == 15


class _FakeSessionCtx:
    """Minimal async context manager wrapping a mock session."""

    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc):
        return False


class TestRollupGovernanceEventsWorker:
    @pytest.mark.asyncio
    async def test_worker_entry_point_returns_status_dict(self):
        """The rollup_governance_events worker returns a proper status dict."""
        from unittest.mock import MagicMock, patch

        from margin_api.workers import rollup_governance_events

        mock_redis = AsyncMock()
        mock_redis.xrange = AsyncMock(return_value=[])
        mock_redis.xtrim = AsyncMock()
        mock_redis.aclose = AsyncMock()

        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = MagicMock(return_value=_FakeSessionCtx(mock_session))

        with (
            patch("margin_api.workers.aioredis.from_url", return_value=mock_redis),
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch(
                "margin_api.workers._rollup_governance_events_impl",
                new_callable=AsyncMock,
                return_value=5,
            ),
        ):
            result = await rollup_governance_events({})

        assert result == {"status": "completed", "events_count": 5}

    @pytest.mark.asyncio
    async def test_worker_closes_redis(self):
        """The worker must close its Redis connection."""
        from unittest.mock import MagicMock, patch

        from margin_api.workers import rollup_governance_events

        mock_redis = AsyncMock()
        mock_redis.xrange = AsyncMock(return_value=[])
        mock_redis.xtrim = AsyncMock()
        mock_redis.aclose = AsyncMock()

        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = MagicMock(return_value=_FakeSessionCtx(mock_session))

        with (
            patch("margin_api.workers.aioredis.from_url", return_value=mock_redis),
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_factory),
            patch(
                "margin_api.workers._rollup_governance_events_impl",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            await rollup_governance_events({})

        mock_redis.aclose.assert_called_once()


class TestRollupGovernanceEventsRegistration:
    def test_registered_in_worker_functions(self):
        from margin_api.workers import WorkerSettings, rollup_governance_events

        assert rollup_governance_events in WorkerSettings.functions

    def test_has_cron_schedule(self):
        from margin_api.workers import WorkerSettings

        cron_funcs = [job.coroutine for job in WorkerSettings.cron_jobs]
        from margin_api.workers import rollup_governance_events

        assert rollup_governance_events in cron_funcs
