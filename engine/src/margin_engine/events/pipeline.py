"""Event processing pipeline — relevance filtering, impact classification, and re-score triggers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from margin_engine.events.models import EventRecord, EventSeverity, EventType


class RescoreTrigger(StrEnum):
    """When to trigger a re-score based on event severity."""

    IMMEDIATE = "immediate"
    DEFERRED_1H = "deferred_1h"
    NEXT_BATCH = "next_batch"


def get_rescore_trigger(severity: EventSeverity) -> RescoreTrigger:
    """Map event severity to the appropriate re-score trigger timing.

    MAJOR  -> immediate
    MODERATE -> deferred (1 hour)
    MINOR  -> next batch
    """
    _mapping: dict[EventSeverity, RescoreTrigger] = {
        EventSeverity.MAJOR: RescoreTrigger.IMMEDIATE,
        EventSeverity.MODERATE: RescoreTrigger.DEFERRED_1H,
        EventSeverity.MINOR: RescoreTrigger.NEXT_BATCH,
    }
    return _mapping[severity]


class RelevanceFilter:
    """Filters events to only those for recommended or watchlisted tickers."""

    def __init__(self, watched_tickers: set[str]) -> None:
        self._watched_tickers = watched_tickers

    @property
    def watched_tickers(self) -> set[str]:
        return self._watched_tickers

    def filter(self, events: list[EventRecord]) -> list[EventRecord]:
        """Return only events whose ticker is in the watched set."""
        return [e for e in events if e.ticker in self._watched_tickers]


class ImpactClassifier:
    """Deterministic rules to classify event impact as MAJOR / MODERATE / MINOR.

    Classification rules:
    - MAJOR: earnings_release, or score_change with |delta| > 10
    - MODERATE: analyst_rating_change, insider_transaction, sec_filing,
                or score_change with 5 <= |delta| <= 10
    - MINOR: price_alert, macro_event, material_news,
             or score_change with |delta| < 5
    """

    _MAJOR_TYPES: frozenset[EventType] = frozenset({EventType.EARNINGS_RELEASE})
    _MODERATE_TYPES: frozenset[EventType] = frozenset({
        EventType.ANALYST_RATING_CHANGE,
        EventType.INSIDER_TRANSACTION,
        EventType.SEC_FILING,
    })
    _MINOR_TYPES: frozenset[EventType] = frozenset({
        EventType.PRICE_ALERT,
        EventType.MACRO_EVENT,
        EventType.MATERIAL_NEWS,
    })

    def classify(self, event: EventRecord) -> EventSeverity:
        """Classify an event and return the appropriate severity."""
        if event.event_type == EventType.SCORE_CHANGE:
            return self._classify_score_change(event)

        if event.event_type in self._MAJOR_TYPES:
            return EventSeverity.MAJOR
        if event.event_type in self._MODERATE_TYPES:
            return EventSeverity.MODERATE
        return EventSeverity.MINOR

    def _classify_score_change(self, event: EventRecord) -> EventSeverity:
        """Classify a score_change event based on the absolute delta in its payload."""
        delta = abs(event.payload.get("delta", 0.0))
        if delta > 10:
            return EventSeverity.MAJOR
        if delta >= 5:
            return EventSeverity.MODERATE
        return EventSeverity.MINOR


@dataclass
class ProcessedEvent:
    """An event enriched with classification and re-score trigger information."""

    event: EventRecord
    classified_severity: EventSeverity
    rescore_trigger: RescoreTrigger


class ScoreDeltaChecker:
    """Checks whether a score delta exceeds a notification threshold."""

    def __init__(self, threshold: float = 5.0) -> None:
        self._threshold = threshold

    @property
    def threshold(self) -> float:
        return self._threshold

    def exceeds_threshold(self, delta: float) -> bool:
        """Return True if the absolute delta exceeds the threshold."""
        return abs(delta) > self._threshold


@dataclass
class EventPipeline:
    """Orchestrates the event processing pipeline.

    Steps:
    1. Filter events to only relevant (watched) tickers.
    2. Classify each event's impact severity.
    3. Determine the re-score trigger timing for each event.
    """

    relevance_filter: RelevanceFilter
    impact_classifier: ImpactClassifier = field(default_factory=ImpactClassifier)

    def process(self, events: list[EventRecord]) -> list[ProcessedEvent]:
        """Run the full pipeline: filter -> classify -> determine trigger."""
        relevant = self.relevance_filter.filter(events)
        results: list[ProcessedEvent] = []
        for event in relevant:
            severity = self.impact_classifier.classify(event)
            trigger = get_rescore_trigger(severity)
            results.append(
                ProcessedEvent(
                    event=event,
                    classified_severity=severity,
                    rescore_trigger=trigger,
                )
            )
        return results
