"""Tests for event and notification endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.routes import events as events_module


@pytest.fixture(autouse=True)
def clean_event_stores():
    """Clear the in-memory event and notification stores before each test."""
    events_module._event_store.clear()
    events_module._notification_store.clear()
    yield
    events_module._event_store.clear()
    events_module._notification_store.clear()


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def _add_event(
    ticker: str = "AAPL",
    event_type: str = "earnings_release",
    severity: str = "major",
    source: str = "sec_api",
    payload: dict | None = None,
    timestamp: datetime | None = None,
) -> dict:
    """Add an event directly to the store and return its dict representation."""
    event = events_module.add_event(
        event_type=event_type,
        ticker=ticker,
        severity=severity,
        source=source,
        payload=payload,
        timestamp=timestamp,
    )
    return event.model_dump(mode="json")


def _add_event_with_notification(
    ticker: str = "AAPL",
    event_type: str = "earnings_release",
    severity: str = "major",
    source: str = "sec_api",
    payload: dict | None = None,
    timestamp: datetime | None = None,
) -> dict:
    """Add an event and its notification, return notification dict."""
    event = events_module.add_event(
        event_type=event_type,
        ticker=ticker,
        severity=severity,
        source=source,
        payload=payload,
        timestamp=timestamp,
    )
    notification = events_module.add_notification(event)
    return notification.model_dump(mode="json")


class TestCreateEvent:
    def test_create_event_success(self, client):
        response = client.post(
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
        assert data["severity"] == "major"
        assert data["source"] == "sec_api"
        assert "event_id" in data
        assert "timestamp" in data

    def test_create_event_normalizes_ticker(self, client):
        response = client.post(
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

    def test_create_event_also_creates_notification(self, client):
        client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "AAPL",
                "severity": "major",
                "source": "sec_api",
            },
        )
        response = client.get("/api/v1/notifications")
        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) == 1
        assert data["unread_count"] == 1


class TestListEvents:
    def test_list_events_empty(self, client):
        response = client.get("/api/v1/events?ticker=AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []
        assert data["total"] == 0

    def test_list_events_by_ticker(self, client):
        _add_event(ticker="AAPL")
        _add_event(ticker="NVDA")
        response = client.get("/api/v1/events?ticker=AAPL")
        data = response.json()
        assert data["total"] == 1
        assert data["events"][0]["ticker"] == "AAPL"

    def test_list_events_case_insensitive(self, client):
        _add_event(ticker="AAPL")
        response = client.get("/api/v1/events?ticker=aapl")
        data = response.json()
        assert data["total"] == 1

    def test_list_events_sorted_by_timestamp_desc(self, client):
        now = datetime.now(UTC)
        _add_event(ticker="AAPL", timestamp=now - timedelta(hours=2))
        _add_event(ticker="AAPL", timestamp=now)
        _add_event(ticker="AAPL", timestamp=now - timedelta(hours=1))
        response = client.get("/api/v1/events?ticker=AAPL")
        data = response.json()
        assert data["total"] == 3
        timestamps = [e["timestamp"] for e in data["events"]]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_list_events_requires_ticker(self, client):
        response = client.get("/api/v1/events")
        assert response.status_code == 422


class TestRecentEvents:
    def test_recent_events_empty(self, client):
        response = client.get("/api/v1/events/recent")
        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []
        assert data["total"] == 0

    def test_recent_events_default_24h(self, client):
        now = datetime.now(UTC)
        _add_event(ticker="AAPL", timestamp=now - timedelta(hours=1))
        _add_event(ticker="NVDA", timestamp=now - timedelta(hours=2))
        # This one is older than 24h
        _add_event(ticker="GOOG", timestamp=now - timedelta(hours=25))
        response = client.get("/api/v1/events/recent")
        data = response.json()
        assert data["total"] == 2
        tickers = [e["ticker"] for e in data["events"]]
        assert "AAPL" in tickers
        assert "NVDA" in tickers
        assert "GOOG" not in tickers

    def test_recent_events_custom_hours(self, client):
        now = datetime.now(UTC)
        _add_event(ticker="AAPL", timestamp=now - timedelta(hours=1))
        _add_event(ticker="NVDA", timestamp=now - timedelta(hours=3))
        response = client.get("/api/v1/events/recent?hours=2")
        data = response.json()
        assert data["total"] == 1
        assert data["events"][0]["ticker"] == "AAPL"

    def test_recent_events_across_tickers(self, client):
        now = datetime.now(UTC)
        _add_event(ticker="AAPL", timestamp=now)
        _add_event(ticker="NVDA", timestamp=now - timedelta(minutes=30))
        _add_event(ticker="GOOG", timestamp=now - timedelta(minutes=15))
        response = client.get("/api/v1/events/recent")
        data = response.json()
        assert data["total"] == 3
        # Should be sorted by timestamp descending
        tickers = [e["ticker"] for e in data["events"]]
        assert tickers == ["AAPL", "GOOG", "NVDA"]

    def test_recent_events_sorted_desc(self, client):
        now = datetime.now(UTC)
        _add_event(ticker="AAPL", timestamp=now - timedelta(hours=5))
        _add_event(ticker="NVDA", timestamp=now - timedelta(hours=1))
        _add_event(ticker="GOOG", timestamp=now - timedelta(hours=3))
        response = client.get("/api/v1/events/recent")
        data = response.json()
        timestamps = [e["timestamp"] for e in data["events"]]
        assert timestamps == sorted(timestamps, reverse=True)


class TestListNotifications:
    def test_list_notifications_empty(self, client):
        response = client.get("/api/v1/notifications")
        assert response.status_code == 200
        data = response.json()
        assert data["notifications"] == []
        assert data["unread_count"] == 0

    def test_list_notifications_with_data(self, client):
        _add_event_with_notification(ticker="AAPL")
        _add_event_with_notification(ticker="NVDA")
        response = client.get("/api/v1/notifications")
        data = response.json()
        assert len(data["notifications"]) == 2
        assert data["unread_count"] == 2

    def test_list_notifications_sorted_by_created_at_desc(self, client):
        _add_event_with_notification(ticker="AAPL")
        _add_event_with_notification(ticker="NVDA")
        _add_event_with_notification(ticker="GOOG")
        response = client.get("/api/v1/notifications")
        data = response.json()
        created_ats = [n["created_at"] for n in data["notifications"]]
        assert created_ats == sorted(created_ats, reverse=True)

    def test_list_notifications_unread_count(self, client):
        n1 = _add_event_with_notification(ticker="AAPL")
        _add_event_with_notification(ticker="NVDA")
        # Mark one as read
        nid = n1["notification_id"]
        events_module._notification_store[nid] = (
            events_module._notification_store[nid].model_copy(update={"read": True})
        )
        response = client.get("/api/v1/notifications")
        data = response.json()
        assert len(data["notifications"]) == 2
        assert data["unread_count"] == 1


class TestMarkNotificationRead:
    def test_mark_notification_read(self, client):
        n = _add_event_with_notification(ticker="AAPL")
        nid = n["notification_id"]
        response = client.put(f"/api/v1/notifications/{nid}/read")
        assert response.status_code == 200
        data = response.json()
        assert data["read"] is True
        assert data["notification_id"] == nid

    def test_mark_notification_read_not_found(self, client):
        response = client.put("/api/v1/notifications/nonexistent-id/read")
        assert response.status_code == 404

    def test_mark_notification_read_idempotent(self, client):
        n = _add_event_with_notification(ticker="AAPL")
        nid = n["notification_id"]
        client.put(f"/api/v1/notifications/{nid}/read")
        response = client.put(f"/api/v1/notifications/{nid}/read")
        assert response.status_code == 200
        assert response.json()["read"] is True


class TestDeleteNotification:
    def test_delete_notification(self, client):
        n = _add_event_with_notification(ticker="AAPL")
        nid = n["notification_id"]
        response = client.delete(f"/api/v1/notifications/{nid}")
        assert response.status_code == 204
        # Verify it's gone
        response = client.get("/api/v1/notifications")
        assert response.json()["notifications"] == []

    def test_delete_notification_not_found(self, client):
        response = client.delete("/api/v1/notifications/nonexistent-id")
        assert response.status_code == 404

    def test_delete_notification_reduces_count(self, client):
        n1 = _add_event_with_notification(ticker="AAPL")
        _add_event_with_notification(ticker="NVDA")
        nid = n1["notification_id"]
        client.delete(f"/api/v1/notifications/{nid}")
        response = client.get("/api/v1/notifications")
        data = response.json()
        assert len(data["notifications"]) == 1
        assert data["unread_count"] == 1
