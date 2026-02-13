"""Integration tests for event and notification API endpoints.

Tests verify end-to-end flows: creating events, fetching them,
filtering by ticker, notification lifecycle (create -> mark read -> delete).
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Create event via POST, then fetch via GET
# ---------------------------------------------------------------------------


class TestCreateAndFetchEvent:
    """Create an event via POST, then verify it appears in GET responses."""

    def test_create_event_then_fetch_by_ticker(self, client: TestClient):
        """POST /events creates an event, GET /events?ticker= returns it."""
        # Create
        resp = client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "AAPL",
                "severity": "major",
                "source": "sec_api",
            },
        )
        assert resp.status_code == 201
        created = resp.json()
        event_id = created["event_id"]

        # Fetch
        resp = client.get("/api/v1/events?ticker=AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["events"][0]["event_id"] == event_id
        assert data["events"][0]["ticker"] == "AAPL"
        assert data["events"][0]["event_type"] == "earnings_release"
        assert data["events"][0]["severity"] == "major"

    def test_create_event_appears_in_recent(self, client: TestClient):
        """A newly created event should appear in the recent events endpoint."""
        client.post(
            "/api/v1/events",
            json={
                "event_type": "sec_filing",
                "ticker": "GOOG",
                "severity": "moderate",
                "source": "edgar",
            },
        )
        resp = client.get("/api/v1/events/recent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["events"][0]["ticker"] == "GOOG"

    def test_create_multiple_events_correct_count(self, client: TestClient):
        """Creating multiple events for a ticker returns the correct total count."""
        for i in range(3):
            client.post(
                "/api/v1/events",
                json={
                    "event_type": "price_alert",
                    "ticker": "MSFT",
                    "severity": "minor",
                    "source": "internal",
                },
            )
        resp = client.get("/api/v1/events?ticker=MSFT")
        data = resp.json()
        assert data["total"] == 3


# ---------------------------------------------------------------------------
# Create events for different tickers, filter by ticker
# ---------------------------------------------------------------------------


class TestFilterByTicker:
    """Create events for multiple tickers and verify filtering works."""

    def test_filter_returns_only_matching_ticker(self, client: TestClient):
        """GET /events?ticker=X only returns events for ticker X."""
        client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "AAPL",
                "severity": "major",
                "source": "sec_api",
            },
        )
        client.post(
            "/api/v1/events",
            json={
                "event_type": "sec_filing",
                "ticker": "GOOG",
                "severity": "moderate",
                "source": "edgar",
            },
        )
        client.post(
            "/api/v1/events",
            json={
                "event_type": "price_alert",
                "ticker": "NVDA",
                "severity": "minor",
                "source": "internal",
            },
        )

        # Only AAPL
        resp = client.get("/api/v1/events?ticker=AAPL")
        data = resp.json()
        assert data["total"] == 1
        assert all(e["ticker"] == "AAPL" for e in data["events"])

        # Only GOOG
        resp = client.get("/api/v1/events?ticker=GOOG")
        data = resp.json()
        assert data["total"] == 1
        assert all(e["ticker"] == "GOOG" for e in data["events"])

        # Only NVDA
        resp = client.get("/api/v1/events?ticker=NVDA")
        data = resp.json()
        assert data["total"] == 1
        assert all(e["ticker"] == "NVDA" for e in data["events"])

    def test_filter_case_insensitive(self, client: TestClient):
        """Ticker filtering is case-insensitive."""
        client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "aapl",
                "severity": "major",
                "source": "sec_api",
            },
        )
        resp = client.get("/api/v1/events?ticker=AAPL")
        assert resp.json()["total"] == 1

        resp = client.get("/api/v1/events?ticker=aapl")
        assert resp.json()["total"] == 1

    def test_filter_nonexistent_ticker_returns_empty(self, client: TestClient):
        """Filtering by a ticker that has no events returns an empty list."""
        client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "AAPL",
                "severity": "major",
                "source": "sec_api",
            },
        )
        resp = client.get("/api/v1/events?ticker=TSLA")
        data = resp.json()
        assert data["total"] == 0
        assert data["events"] == []

    def test_recent_returns_events_across_all_tickers(self, client: TestClient):
        """The recent endpoint returns events across all tickers."""
        client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "AAPL",
                "severity": "major",
                "source": "sec_api",
            },
        )
        client.post(
            "/api/v1/events",
            json={
                "event_type": "sec_filing",
                "ticker": "GOOG",
                "severity": "moderate",
                "source": "edgar",
            },
        )
        resp = client.get("/api/v1/events/recent")
        data = resp.json()
        assert data["total"] == 2
        tickers = {e["ticker"] for e in data["events"]}
        assert tickers == {"AAPL", "GOOG"}


# ---------------------------------------------------------------------------
# Full notification lifecycle: create -> read -> delete
# ---------------------------------------------------------------------------


class TestNotificationLifecycle:
    """Create event -> auto-notification -> mark read -> delete."""

    def test_event_creation_auto_creates_notification(self, client: TestClient):
        """Creating an event also creates a corresponding notification."""
        resp = client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "AAPL",
                "severity": "major",
                "source": "sec_api",
            },
        )
        assert resp.status_code == 201
        event_data = resp.json()

        resp = client.get("/api/v1/notifications")
        data = resp.json()
        assert len(data["notifications"]) == 1
        assert data["unread_count"] == 1
        notification = data["notifications"][0]
        assert notification["read"] is False
        assert notification["event"]["event_id"] == event_data["event_id"]

    def test_mark_notification_read(self, client: TestClient):
        """Mark a notification as read and verify the unread count decreases."""
        client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "AAPL",
                "severity": "major",
                "source": "sec_api",
            },
        )
        # Get the notification ID
        resp = client.get("/api/v1/notifications")
        nid = resp.json()["notifications"][0]["notification_id"]

        # Mark as read
        resp = client.put(f"/api/v1/notifications/{nid}/read")
        assert resp.status_code == 200
        assert resp.json()["read"] is True

        # Verify unread count
        resp = client.get("/api/v1/notifications")
        data = resp.json()
        assert data["unread_count"] == 0
        assert data["notifications"][0]["read"] is True

    def test_delete_notification(self, client: TestClient):
        """Delete a notification and verify it's gone."""
        client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "AAPL",
                "severity": "major",
                "source": "sec_api",
            },
        )
        resp = client.get("/api/v1/notifications")
        nid = resp.json()["notifications"][0]["notification_id"]

        # Delete
        resp = client.delete(f"/api/v1/notifications/{nid}")
        assert resp.status_code == 204

        # Verify it's gone
        resp = client.get("/api/v1/notifications")
        data = resp.json()
        assert len(data["notifications"]) == 0
        assert data["unread_count"] == 0

    def test_full_notification_lifecycle(self, client: TestClient):
        """End-to-end: create event -> notification auto-created ->
        mark notification read -> delete notification."""
        # Step 1: Create event
        resp = client.post(
            "/api/v1/events",
            json={
                "event_type": "sec_filing",
                "ticker": "NVDA",
                "severity": "moderate",
                "source": "edgar",
            },
        )
        assert resp.status_code == 201
        event_id = resp.json()["event_id"]

        # Step 2: Verify notification was auto-created (unread)
        resp = client.get("/api/v1/notifications")
        data = resp.json()
        assert len(data["notifications"]) == 1
        assert data["unread_count"] == 1
        notification = data["notifications"][0]
        nid = notification["notification_id"]
        assert notification["read"] is False
        assert notification["event"]["event_id"] == event_id
        assert notification["event"]["ticker"] == "NVDA"

        # Step 3: Mark as read
        resp = client.put(f"/api/v1/notifications/{nid}/read")
        assert resp.status_code == 200
        assert resp.json()["read"] is True

        # Verify unread count decreased
        resp = client.get("/api/v1/notifications")
        assert resp.json()["unread_count"] == 0

        # Step 4: Delete notification
        resp = client.delete(f"/api/v1/notifications/{nid}")
        assert resp.status_code == 204

        # Verify notification is gone
        resp = client.get("/api/v1/notifications")
        data = resp.json()
        assert len(data["notifications"]) == 0

        # Step 5: Original event still exists
        resp = client.get("/api/v1/events?ticker=NVDA")
        data = resp.json()
        assert data["total"] == 1
        assert data["events"][0]["event_id"] == event_id

    def test_multiple_events_create_multiple_notifications(self, client: TestClient):
        """Multiple events create independent notifications."""
        client.post(
            "/api/v1/events",
            json={
                "event_type": "earnings_release",
                "ticker": "AAPL",
                "severity": "major",
                "source": "sec_api",
            },
        )
        client.post(
            "/api/v1/events",
            json={
                "event_type": "sec_filing",
                "ticker": "GOOG",
                "severity": "moderate",
                "source": "edgar",
            },
        )
        client.post(
            "/api/v1/events",
            json={
                "event_type": "price_alert",
                "ticker": "NVDA",
                "severity": "minor",
                "source": "internal",
            },
        )

        resp = client.get("/api/v1/notifications")
        data = resp.json()
        assert len(data["notifications"]) == 3
        assert data["unread_count"] == 3

        # Mark one as read, delete another
        nids = [n["notification_id"] for n in data["notifications"]]
        client.put(f"/api/v1/notifications/{nids[0]}/read")
        client.delete(f"/api/v1/notifications/{nids[1]}")

        resp = client.get("/api/v1/notifications")
        data = resp.json()
        assert len(data["notifications"]) == 2
        assert data["unread_count"] == 1

    def test_delete_nonexistent_notification_returns_404(self, client: TestClient):
        """Attempting to delete a non-existent notification returns 404."""
        resp = client.delete("/api/v1/notifications/does-not-exist")
        assert resp.status_code == 404

    def test_mark_read_nonexistent_notification_returns_404(self, client: TestClient):
        """Attempting to mark a non-existent notification as read returns 404."""
        resp = client.put("/api/v1/notifications/does-not-exist/read")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Router export verification
# ---------------------------------------------------------------------------


class TestRouterExports:
    """Verify that the events router is properly exported from routes package."""

    def test_events_router_importable_from_routes(self):
        from margin_api.routes import events_router

        assert events_router is not None

    def test_ws_router_importable_from_ws(self):
        from margin_api.ws import ws_router

        assert ws_router is not None

    def test_all_routers_importable(self):
        from margin_api.routes import dashboard_router, events_router, health_router, scores_router

        assert dashboard_router is not None
        assert events_router is not None
        assert health_router is not None
        assert scores_router is not None
