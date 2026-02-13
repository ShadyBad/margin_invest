"""Event and notification endpoints for the Margin Invest API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from margin_api.schemas.events import (
    EventListResponse,
    EventResponse,
    EventTypeEnum,
    NotificationListResponse,
    NotificationResponse,
    SeverityEnum,
)

router = APIRouter(prefix="/api/v1", tags=["events"])

# In-memory stores (replaced by DB in later phase)
_event_store: dict[str, list[EventResponse]] = {}  # ticker -> events
_notification_store: dict[str, NotificationResponse] = {}  # notification_id -> notification


def add_event(
    event_type: str,
    ticker: str,
    severity: str,
    source: str,
    payload: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
    event_id: str | None = None,
) -> EventResponse:
    """Programmatically add an event to the store.

    Returns the created EventResponse.
    """
    event = EventResponse(
        event_id=event_id or str(uuid4()),
        event_type=event_type,
        ticker=ticker.upper(),
        timestamp=timestamp or datetime.now(UTC),
        severity=severity,
        source=source,
        payload=payload or {},
    )
    ticker_key = event.ticker
    if ticker_key not in _event_store:
        _event_store[ticker_key] = []
    _event_store[ticker_key].append(event)
    return event


def add_notification(event: EventResponse) -> NotificationResponse:
    """Create a notification from an event and add it to the store.

    Returns the created NotificationResponse.
    """
    notification = NotificationResponse(
        notification_id=str(uuid4()),
        event=event,
        read=False,
        created_at=datetime.now(UTC),
    )
    _notification_store[notification.notification_id] = notification
    return notification


class CreateEventRequest(BaseModel):
    """Request body for creating an event."""

    event_type: EventTypeEnum
    ticker: str
    severity: SeverityEnum
    source: str
    payload: dict[str, Any] | None = None


@router.post("/events", response_model=EventResponse, status_code=201)
async def create_event(body: CreateEventRequest) -> EventResponse:
    """Create a new event.

    Accepts event fields as a JSON request body and stores the event.
    Also creates a corresponding notification.
    """
    event = add_event(
        event_type=body.event_type,
        ticker=body.ticker,
        severity=body.severity,
        source=body.source,
        payload=body.payload,
    )
    add_notification(event)
    return event


@router.get("/events", response_model=EventListResponse)
async def list_events(
    ticker: str = Query(..., description="Ticker symbol to filter events"),
) -> EventListResponse:
    """List events for a specific ticker, sorted by timestamp descending."""
    ticker = ticker.upper()
    events = _event_store.get(ticker, [])
    # Sort by timestamp descending
    sorted_events = sorted(events, key=lambda e: e.timestamp, reverse=True)
    return EventListResponse(events=sorted_events, total=len(sorted_events))


@router.get("/events/recent", response_model=EventListResponse)
async def list_recent_events(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
) -> EventListResponse:
    """List recent events across all tickers.

    Returns events from the last N hours (default 24), sorted by timestamp descending.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    recent: list[EventResponse] = []
    for events in _event_store.values():
        for event in events:
            # Compare timezone-aware datetimes; if event.timestamp is naive, treat as UTC
            ts = event.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts >= cutoff:
                recent.append(event)
    # Sort by timestamp descending
    recent.sort(key=lambda e: e.timestamp, reverse=True)
    return EventListResponse(events=recent, total=len(recent))


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications() -> NotificationListResponse:
    """List all notifications, sorted by created_at descending."""
    notifications = list(_notification_store.values())
    notifications.sort(key=lambda n: n.created_at, reverse=True)
    unread_count = sum(1 for n in notifications if not n.read)
    return NotificationListResponse(
        notifications=notifications,
        unread_count=unread_count,
    )


@router.put("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(notification_id: str) -> NotificationResponse:
    """Mark a notification as read."""
    if notification_id not in _notification_store:
        raise HTTPException(
            status_code=404, detail=f"Notification {notification_id} not found"
        )
    notification = _notification_store[notification_id]
    updated = notification.model_copy(update={"read": True})
    _notification_store[notification_id] = updated
    return updated


@router.delete("/notifications/{notification_id}", status_code=204)
async def delete_notification(notification_id: str) -> None:
    """Delete a notification."""
    if notification_id not in _notification_store:
        raise HTTPException(
            status_code=404, detail=f"Notification {notification_id} not found"
        )
    del _notification_store[notification_id]
