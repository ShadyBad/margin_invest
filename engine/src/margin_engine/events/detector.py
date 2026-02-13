"""Event detection protocol and configuration."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from margin_engine.events.models import EventRecord, EventType


@runtime_checkable
class EventDetector(Protocol):
    """Protocol for event detection implementations.

    Each detector is responsible for checking a single source
    (e.g., EDGAR RSS, Finnhub calendar) and returning any new
    events discovered for a given ticker.
    """

    def detect(self, ticker: str) -> list[EventRecord]:
        """Check for new events for the given ticker.

        Returns a list of EventRecord instances (may be empty).
        """
        ...


class DetectionConfig(BaseModel):
    """Configuration for event detection scheduling."""

    check_interval_seconds: int = Field(gt=0)
    enabled_event_types: list[EventType] = Field(default_factory=list)
