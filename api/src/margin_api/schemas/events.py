"""Event and notification API response schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventTypeEnum(StrEnum):
    """Valid event types for the API."""

    earnings_release = "earnings_release"
    sec_filing = "sec_filing"
    insider_transaction = "insider_transaction"
    price_alert = "price_alert"
    analyst_rating_change = "analyst_rating_change"
    macro_event = "macro_event"
    material_news = "material_news"
    score_change = "score_change"


class SeverityEnum(StrEnum):
    """Valid severity levels for the API."""

    major = "major"
    moderate = "moderate"
    minor = "minor"


class EventResponse(BaseModel):
    """API representation of a single event."""

    event_id: str
    event_type: EventTypeEnum
    ticker: str
    timestamp: datetime
    severity: SeverityEnum
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)


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
