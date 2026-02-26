"""Tests for event and notification endpoints — DB-backed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Event, Notification
from margin_api.db.session import get_db
from margin_api.routes.events import add_event, add_notification
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
async def client(async_engine, session_factory):
    app = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


async def _add_event_via_db(
    session: AsyncSession,
    ticker: str = "AAPL",
    event_type: str = "earnings_release",
    severity: str = "major",
    source: str = "sec_api",
    payload: dict | None = None,
    timestamp: datetime | None = None,
) -> Event:
    """Add an event directly via the add_event helper and commit."""
    event_db = await add_event(
        session,
        event_type=event_type,
        ticker=ticker,
        severity=severity,
        source=source,
        payload=payload,
        timestamp=timestamp,
    )
    await session.commit()
    return event_db


async def _add_event_with_notification_via_db(
    session: AsyncSession,
    ticker: str = "AAPL",
    event_type: str = "earnings_release",
    severity: str = "major",
    source: str = "sec_api",
    payload: dict | None = None,
    timestamp: datetime | None = None,
) -> Notification:
    """Add an event + notification directly via helpers and commit."""
    event_db = await add_event(
        session,
        event_type=event_type,
        ticker=ticker,
        severity=severity,
        source=source,
        payload=payload,
        timestamp=timestamp,
    )
    notif_db = await add_notification(session, event_db)
    await session.commit()
    await session.refresh(notif_db, ["event"])
    return notif_db


class TestCreateEvent:
    @pytest.mark.asyncio
    async def test_create_event_success(self, client):
        response = await client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "AAPL",
                "severity": "major",
                "source": "sec_api",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["event_type"] == "earnings_release"
        assert data["severity"] == "major"  # earnings_release -> MAJOR
        assert data["source"] == "sec_api"
        assert "event_id" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_create_event_normalizes_ticker(self, client):
        response = await client.post(
            "/api/v1/events",
            json={
                "event_type": "price_alert",
                "ticker": "aapl",
                "severity": "minor",
                "source": "internal",
            },
        )
        assert response.status_code == 201
        assert response.json()["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_create_event_also_creates_notification(self, client):
        await client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "AAPL",
                "severity": "major",
                "source": "sec_api",
            },
        )
        response = await client.get("/api/v1/notifications")
        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) == 1
        assert data["unread_count"] == 1


class TestListEvents:
    @pytest.mark.asyncio
    async def test_list_events_empty(self, client):
        response = await client.get("/api/v1/events?ticker=AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_events_by_ticker(self, client, db_session):
        await _add_event_via_db(db_session, ticker="AAPL")
        await _add_event_via_db(db_session, ticker="NVDA")
        response = await client.get("/api/v1/events?ticker=AAPL")
        data = response.json()
        assert data["total"] == 1
        assert data["events"][0]["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_list_events_case_insensitive(self, client, db_session):
        await _add_event_via_db(db_session, ticker="AAPL")
        response = await client.get("/api/v1/events?ticker=aapl")
        data = response.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_list_events_sorted_by_timestamp_desc(self, client, db_session):
        now = datetime.now(UTC)
        await _add_event_via_db(db_session, ticker="AAPL", timestamp=now - timedelta(hours=2))
        await _add_event_via_db(db_session, ticker="AAPL", timestamp=now)
        await _add_event_via_db(db_session, ticker="AAPL", timestamp=now - timedelta(hours=1))
        response = await client.get("/api/v1/events?ticker=AAPL")
        data = response.json()
        assert data["total"] == 3
        timestamps = [e["timestamp"] for e in data["events"]]
        assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_list_events_requires_ticker(self, client):
        response = await client.get("/api/v1/events")
        assert response.status_code == 422


class TestRecentEvents:
    @pytest.mark.asyncio
    async def test_recent_events_empty(self, client):
        response = await client.get("/api/v1/events/recent")
        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_recent_events_default_24h(self, client, db_session):
        now = datetime.now(UTC)
        await _add_event_via_db(db_session, ticker="AAPL", timestamp=now - timedelta(hours=1))
        await _add_event_via_db(db_session, ticker="NVDA", timestamp=now - timedelta(hours=2))
        # Older than 24h
        await _add_event_via_db(db_session, ticker="GOOG", timestamp=now - timedelta(hours=25))
        response = await client.get("/api/v1/events/recent")
        data = response.json()
        assert data["total"] == 2
        tickers = [e["ticker"] for e in data["events"]]
        assert "AAPL" in tickers
        assert "NVDA" in tickers
        assert "GOOG" not in tickers

    @pytest.mark.asyncio
    async def test_recent_events_custom_hours(self, client, db_session):
        now = datetime.now(UTC)
        await _add_event_via_db(db_session, ticker="AAPL", timestamp=now - timedelta(hours=1))
        await _add_event_via_db(db_session, ticker="NVDA", timestamp=now - timedelta(hours=3))
        response = await client.get("/api/v1/events/recent?hours=2")
        data = response.json()
        assert data["total"] == 1
        assert data["events"][0]["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_recent_events_across_tickers(self, client, db_session):
        now = datetime.now(UTC)
        await _add_event_via_db(db_session, ticker="AAPL", timestamp=now)
        await _add_event_via_db(db_session, ticker="NVDA", timestamp=now - timedelta(minutes=30))
        await _add_event_via_db(db_session, ticker="GOOG", timestamp=now - timedelta(minutes=15))
        response = await client.get("/api/v1/events/recent")
        data = response.json()
        assert data["total"] == 3
        # Should be sorted by timestamp descending
        tickers = [e["ticker"] for e in data["events"]]
        assert tickers == ["AAPL", "GOOG", "NVDA"]

    @pytest.mark.asyncio
    async def test_recent_events_sorted_desc(self, client, db_session):
        now = datetime.now(UTC)
        await _add_event_via_db(db_session, ticker="AAPL", timestamp=now - timedelta(hours=5))
        await _add_event_via_db(db_session, ticker="NVDA", timestamp=now - timedelta(hours=1))
        await _add_event_via_db(db_session, ticker="GOOG", timestamp=now - timedelta(hours=3))
        response = await client.get("/api/v1/events/recent")
        data = response.json()
        timestamps = [e["timestamp"] for e in data["events"]]
        assert timestamps == sorted(timestamps, reverse=True)


class TestListNotifications:
    @pytest.mark.asyncio
    async def test_list_notifications_empty(self, client):
        response = await client.get("/api/v1/notifications")
        assert response.status_code == 200
        data = response.json()
        assert data["notifications"] == []
        assert data["unread_count"] == 0

    @pytest.mark.asyncio
    async def test_list_notifications_with_data(self, client, db_session):
        await _add_event_with_notification_via_db(db_session, ticker="AAPL")
        await _add_event_with_notification_via_db(db_session, ticker="NVDA")
        response = await client.get("/api/v1/notifications")
        data = response.json()
        assert len(data["notifications"]) == 2
        assert data["unread_count"] == 2

    @pytest.mark.asyncio
    async def test_list_notifications_sorted_by_created_at_desc(self, client, db_session):
        await _add_event_with_notification_via_db(db_session, ticker="AAPL")
        await _add_event_with_notification_via_db(db_session, ticker="NVDA")
        await _add_event_with_notification_via_db(db_session, ticker="GOOG")
        response = await client.get("/api/v1/notifications")
        data = response.json()
        created_ats = [n["created_at"] for n in data["notifications"]]
        assert created_ats == sorted(created_ats, reverse=True)

    @pytest.mark.asyncio
    async def test_list_notifications_unread_count(self, client, db_session):
        n1 = await _add_event_with_notification_via_db(db_session, ticker="AAPL")
        await _add_event_with_notification_via_db(db_session, ticker="NVDA")
        # Mark one as read directly in DB
        n1.read = True
        await db_session.commit()

        response = await client.get("/api/v1/notifications")
        data = response.json()
        assert len(data["notifications"]) == 2
        assert data["unread_count"] == 1


class TestMarkNotificationRead:
    @pytest.mark.asyncio
    async def test_mark_notification_read(self, client, db_session):
        n = await _add_event_with_notification_via_db(db_session, ticker="AAPL")
        nid = n.notification_id
        response = await client.put(f"/api/v1/notifications/{nid}/read")
        assert response.status_code == 200
        data = response.json()
        assert data["read"] is True
        assert data["notification_id"] == nid

    @pytest.mark.asyncio
    async def test_mark_notification_read_not_found(self, client):
        response = await client.put("/api/v1/notifications/nonexistent-id/read")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_notification_read_idempotent(self, client, db_session):
        n = await _add_event_with_notification_via_db(db_session, ticker="AAPL")
        nid = n.notification_id
        await client.put(f"/api/v1/notifications/{nid}/read")
        response = await client.put(f"/api/v1/notifications/{nid}/read")
        assert response.status_code == 200
        assert response.json()["read"] is True


class TestDeleteNotification:
    @pytest.mark.asyncio
    async def test_delete_notification(self, client, db_session):
        n = await _add_event_with_notification_via_db(db_session, ticker="AAPL")
        nid = n.notification_id
        response = await client.delete(f"/api/v1/notifications/{nid}")
        assert response.status_code == 204
        # Verify it's gone
        response = await client.get("/api/v1/notifications")
        assert response.json()["notifications"] == []

    @pytest.mark.asyncio
    async def test_delete_notification_not_found(self, client):
        response = await client.delete("/api/v1/notifications/nonexistent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_notification_reduces_count(self, client, db_session):
        n1 = await _add_event_with_notification_via_db(db_session, ticker="AAPL")
        await _add_event_with_notification_via_db(db_session, ticker="NVDA")
        nid = n1.notification_id
        await client.delete(f"/api/v1/notifications/{nid}")
        response = await client.get("/api/v1/notifications")
        data = response.json()
        assert len(data["notifications"]) == 1
        assert data["unread_count"] == 1


class TestAutoClassification:
    @pytest.mark.asyncio
    async def test_score_change_event_auto_classified_major(self, client):
        """Score change events get severity auto-classified by ImpactClassifier."""
        resp = await client.post(
            "/api/v1/events",
            json={
                "event_type": "score_change",
                "ticker": "AAPL",
                "severity": "minor",  # will be overridden by classifier
                "source": "test",
                "payload": {"delta": 15.0},
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["severity"] == "major"  # delta > 10 -> MAJOR

    @pytest.mark.asyncio
    async def test_score_change_event_auto_classified_moderate(self, client):
        """Score change with 5 <= delta <= 10 classified as moderate."""
        resp = await client.post(
            "/api/v1/events",
            json={
                "event_type": "score_change",
                "ticker": "AAPL",
                "severity": "minor",
                "source": "test",
                "payload": {"delta": 7.0},
            },
        )
        assert resp.status_code == 201
        assert resp.json()["severity"] == "moderate"

    @pytest.mark.asyncio
    async def test_score_change_event_auto_classified_minor(self, client):
        """Score change with delta < 5 classified as minor."""
        resp = await client.post(
            "/api/v1/events",
            json={
                "event_type": "score_change",
                "ticker": "AAPL",
                "severity": "major",  # will be overridden
                "source": "test",
                "payload": {"delta": 2.0},
            },
        )
        assert resp.status_code == 201
        assert resp.json()["severity"] == "minor"

    @pytest.mark.asyncio
    async def test_earnings_release_always_major(self, client):
        """earnings_release is always classified as major regardless of input."""
        resp = await client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "AAPL",
                "severity": "minor",  # will be overridden
                "source": "test",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["severity"] == "major"

    @pytest.mark.asyncio
    async def test_analyst_rating_change_moderate(self, client):
        """analyst_rating_change is always classified as moderate."""
        resp = await client.post(
            "/api/v1/events",
            json={
                "event_type": "analyst_rating_change",
                "ticker": "AAPL",
                "severity": "major",  # will be overridden
                "source": "test",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["severity"] == "moderate"

    @pytest.mark.asyncio
    async def test_price_alert_minor(self, client):
        """price_alert is always classified as minor."""
        resp = await client.post(
            "/api/v1/events",
            json={
                "event_type": "price_alert",
                "ticker": "AAPL",
                "severity": "major",  # will be overridden
                "source": "test",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["severity"] == "minor"
