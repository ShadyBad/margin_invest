"""Event detection and notification system."""

from margin_engine.events.detector import DetectionConfig, EventDetector
from margin_engine.events.models import (
    EventRecord,
    EventSeverity,
    EventType,
    NotificationRecord,
    ScoreChangePayload,
)
from margin_engine.events.pipeline import (
    EventPipeline,
    ImpactClassifier,
    ProcessedEvent,
    RelevanceFilter,
    RescoreTrigger,
    ScoreDeltaChecker,
)
from margin_engine.events.throttle import NotificationThrottle

__all__ = [
    "DetectionConfig",
    "EventDetector",
    "EventPipeline",
    "EventRecord",
    "EventSeverity",
    "EventType",
    "ImpactClassifier",
    "NotificationRecord",
    "NotificationThrottle",
    "ProcessedEvent",
    "RelevanceFilter",
    "RescoreTrigger",
    "ScoreChangePayload",
    "ScoreDeltaChecker",
]
