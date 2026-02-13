"""Event and notification API response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventResponse(BaseModel):
    """API representation of a single event."""

    event_id: str
    event_type: str
    ticker: str
    timestamp: datetime
    severity: str
    source: str
    payload: dict[str, Any] = {}


class EventListResponse(BaseModel):
    """List of events with total count."""

    events: list[EventResponse]
    total: int


class NotificationResponse(BaseModel):
    """API representation of a single notification."""

    notification_id: str
    event: EventResponse
    read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    """List of notifications with unread count."""

    notifications: list[NotificationResponse]
    unread_count: int
