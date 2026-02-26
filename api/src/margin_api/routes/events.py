"""Event and notification endpoints for the Margin Invest API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from margin_engine.events.models import EventRecord
from margin_engine.events.models import EventType as EngineEventType
from margin_engine.events.pipeline import ImpactClassifier
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from margin_api.db.models import Event, Notification
from margin_api.db.session import get_db
from margin_api.schemas.events import (
    EventListResponse,
    EventResponse,
    EventTypeEnum,
    NotificationListResponse,
    NotificationResponse,
    SeverityEnum,
)

router = APIRouter(prefix="/api/v1", tags=["events"])

_classifier = ImpactClassifier()


def _event_db_to_response(event_db: Event) -> EventResponse:
    """Convert an Event ORM model to an EventResponse schema."""
    return EventResponse(
        event_id=event_db.event_id,
        event_type=event_db.event_type,
        ticker=event_db.ticker,
        timestamp=event_db.timestamp,
        severity=event_db.severity,
        source=event_db.source,
        payload=event_db.payload or {},
    )


def _notification_db_to_response(notif_db: Notification) -> NotificationResponse:
    """Convert a Notification ORM model to a NotificationResponse schema."""
    return NotificationResponse(
        notification_id=notif_db.notification_id,
        event=_event_db_to_response(notif_db.event),
        read=notif_db.read,
        created_at=notif_db.created_at,
    )


def _classify_severity(
    event_type: str,
    payload: dict[str, Any] | None,
) -> str:
    """Run the engine ImpactClassifier to determine event severity."""
    engine_record = EventRecord(
        event_type=EngineEventType(event_type),
        ticker="X",  # ticker irrelevant for classification
        timestamp=datetime.now(UTC),
        severity="minor",  # placeholder; classifier overrides
        source="",
        payload=payload or {},
    )
    classified = _classifier.classify(engine_record)
    return str(classified)


async def add_event(
    session: AsyncSession,
    event_type: str,
    ticker: str,
    severity: str,
    source: str,
    payload: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
    event_id: str | None = None,
) -> Event:
    """Programmatically add an event to the database.

    Auto-classifies severity via ImpactClassifier.
    Returns the created Event ORM object (with id populated).
    """
    classified_severity = _classify_severity(event_type, payload)

    event_db = Event(
        event_id=event_id or str(uuid4()),
        event_type=event_type,
        ticker=ticker.upper(),
        timestamp=timestamp or datetime.now(UTC),
        severity=classified_severity,
        source=source,
        payload=payload or {},
    )
    session.add(event_db)
    await session.flush()
    return event_db


async def add_notification(session: AsyncSession, event_db: Event) -> Notification:
    """Create a notification from a DB event and persist it.

    Returns the created Notification ORM object.
    """
    notif_db = Notification(
        notification_id=str(uuid4()),
        event_id=event_db.id,
    )
    session.add(notif_db)
    await session.flush()
    return notif_db


class CreateEventRequest(BaseModel):
    """Request body for creating an event."""

    event_type: EventTypeEnum
    ticker: str
    severity: SeverityEnum
    source: str
    payload: dict[str, Any] | None = None


@router.post("/events", response_model=EventResponse, status_code=201)
async def create_event(
    body: CreateEventRequest,
    session: AsyncSession = Depends(get_db),
) -> EventResponse:
    """Create a new event.

    Accepts event fields as a JSON request body, auto-classifies severity
    via ImpactClassifier, persists the event, and creates a notification.
    """
    event_db = await add_event(
        session,
        event_type=body.event_type,
        ticker=body.ticker,
        severity=body.severity,
        source=body.source,
        payload=body.payload,
    )
    await add_notification(session, event_db)
    await session.commit()
    await session.refresh(event_db)
    return _event_db_to_response(event_db)


@router.get("/events", response_model=EventListResponse)
async def list_events(
    ticker: str = Query(..., description="Ticker symbol to filter events"),
    session: AsyncSession = Depends(get_db),
) -> EventListResponse:
    """List events for a specific ticker, sorted by timestamp descending."""
    ticker = ticker.upper()
    stmt = select(Event).where(Event.ticker == ticker).order_by(Event.timestamp.desc())
    result = await session.execute(stmt)
    events = result.scalars().all()
    responses = [_event_db_to_response(e) for e in events]
    return EventListResponse(events=responses, total=len(responses))


@router.get("/events/recent", response_model=EventListResponse)
async def list_recent_events(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    session: AsyncSession = Depends(get_db),
) -> EventListResponse:
    """List recent events across all tickers.

    Returns events from the last N hours (default 24), sorted by timestamp descending.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    stmt = select(Event).where(Event.timestamp >= cutoff).order_by(Event.timestamp.desc())
    result = await session.execute(stmt)
    events = result.scalars().all()
    responses = [_event_db_to_response(e) for e in events]
    return EventListResponse(events=responses, total=len(responses))


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    session: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    """List all notifications, sorted by created_at descending."""
    stmt = (
        select(Notification)
        .options(selectinload(Notification.event))
        .order_by(Notification.created_at.desc())
    )
    result = await session.execute(stmt)
    notifications = result.scalars().all()

    unread_count = sum(1 for n in notifications if not n.read)
    responses = [_notification_db_to_response(n) for n in notifications]
    return NotificationListResponse(
        notifications=responses,
        unread_count=unread_count,
    )


@router.put("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    session: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """Mark a notification as read."""
    stmt = (
        select(Notification)
        .options(selectinload(Notification.event))
        .where(Notification.notification_id == notification_id)
    )
    result = await session.execute(stmt)
    notif = result.scalar_one_or_none()
    if notif is None:
        raise HTTPException(status_code=404, detail=f"Notification {notification_id} not found")
    notif.read = True
    await session.commit()
    await session.refresh(notif, ["event"])
    return _notification_db_to_response(notif)


@router.delete("/notifications/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: str,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a notification."""
    stmt = select(Notification).where(Notification.notification_id == notification_id)
    result = await session.execute(stmt)
    notif = result.scalar_one_or_none()
    if notif is None:
        raise HTTPException(status_code=404, detail=f"Notification {notification_id} not found")
    await session.delete(notif)
    await session.commit()
