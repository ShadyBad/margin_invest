"""Event system models — event types, records, and notifications."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    EARNINGS_RELEASE = "earnings_release"
    SEC_FILING = "sec_filing"
    INSIDER_TRANSACTION = "insider_transaction"
    PRICE_ALERT = "price_alert"
    ANALYST_RATING_CHANGE = "analyst_rating_change"
    MACRO_EVENT = "macro_event"
    MATERIAL_NEWS = "material_news"
    SCORE_CHANGE = "score_change"


class EventSeverity(StrEnum):
    MAJOR = "major"
    MODERATE = "moderate"
    MINOR = "minor"


class EventRecord(BaseModel):
    """A single detected event tied to a ticker."""

    event_type: EventType
    ticker: str
    timestamp: datetime
    severity: EventSeverity
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    event_id: str = Field(default_factory=lambda: str(uuid4()))


class ScoreChangePayload(BaseModel):
    """Structured payload for score_change events."""

    old_score: float
    new_score: float
    delta: float
    conviction_change: str | None = None


class NotificationRecord(BaseModel):
    """A user-facing notification derived from an event."""

    event: EventRecord
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notification_id: str = Field(default_factory=lambda: str(uuid4()))
