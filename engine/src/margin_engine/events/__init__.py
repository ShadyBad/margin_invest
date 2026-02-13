"""Event detection and notification system."""

from margin_engine.events.detector import DetectionConfig, EventDetector
from margin_engine.events.models import (
    EventRecord,
    EventSeverity,
    EventType,
    NotificationRecord,
    ScoreChangePayload,
)

__all__ = [
    "DetectionConfig",
    "EventDetector",
    "EventRecord",
    "EventSeverity",
    "EventType",
    "NotificationRecord",
    "ScoreChangePayload",
]
