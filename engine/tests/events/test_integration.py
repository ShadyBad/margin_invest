"""Integration tests for the event processing pipeline end-to-end."""

from __future__ import annotations

from datetime import datetime, timedelta

from margin_engine.events.models import EventRecord, EventSeverity, EventType, NotificationRecord
from margin_engine.events.pipeline import (
    EventPipeline,
    ImpactClassifier,
    ProcessedEvent,
    RelevanceFilter,
    RescoreTrigger,
    ScoreDeltaChecker,
)
from margin_engine.events.throttle import NotificationThrottle

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    event_type: EventType = EventType.EARNINGS_RELEASE,
    ticker: str = "AAPL",
    severity: EventSeverity = EventSeverity.MAJOR,
    payload: dict | None = None,
    timestamp: datetime | None = None,
) -> EventRecord:
    return EventRecord(
        event_type=event_type,
        ticker=ticker,
        timestamp=timestamp or datetime(2026, 2, 10, 12, 0),
        severity=severity,
        source="test",
        payload=payload or {},
    )


# ---------------------------------------------------------------------------
# Full pipeline flow: create -> filter -> classify -> get rescore triggers
# ---------------------------------------------------------------------------


class TestPipelineEndToEnd:
    """Test the complete flow: events created -> filtered -> classified -> triggers assigned."""

    def test_full_flow_multiple_event_types(self):
        """Mixed events pass through the pipeline and get correct classifications."""
        pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL", "GOOG", "MSFT", "NVDA"}),
        )

        events = [
            _make_event(event_type=EventType.EARNINGS_RELEASE, ticker="AAPL"),
            _make_event(event_type=EventType.SEC_FILING, ticker="GOOG"),
            _make_event(event_type=EventType.PRICE_ALERT, ticker="MSFT"),
            _make_event(
                event_type=EventType.SCORE_CHANGE,
                ticker="NVDA",
                payload={"delta": 15.0},
            ),
            # This one should be filtered out (not watched)
            _make_event(event_type=EventType.EARNINGS_RELEASE, ticker="TSLA"),
        ]

        results = pipeline.process(events)

        assert len(results) == 4

        # AAPL earnings -> MAJOR -> IMMEDIATE
        assert results[0].event.ticker == "AAPL"
        assert results[0].classified_severity == EventSeverity.MAJOR
        assert results[0].rescore_trigger == RescoreTrigger.IMMEDIATE

        # GOOG SEC filing -> MODERATE -> DEFERRED_1H
        assert results[1].event.ticker == "GOOG"
        assert results[1].classified_severity == EventSeverity.MODERATE
        assert results[1].rescore_trigger == RescoreTrigger.DEFERRED_1H

        # MSFT price alert -> MINOR -> NEXT_BATCH
        assert results[2].event.ticker == "MSFT"
        assert results[2].classified_severity == EventSeverity.MINOR
        assert results[2].rescore_trigger == RescoreTrigger.NEXT_BATCH

        # NVDA score change delta=15 -> MAJOR -> IMMEDIATE
        assert results[3].event.ticker == "NVDA"
        assert results[3].classified_severity == EventSeverity.MAJOR
        assert results[3].rescore_trigger == RescoreTrigger.IMMEDIATE

    def test_pipeline_with_only_unwatched_tickers_yields_nothing(self):
        """If no events match watched tickers, the pipeline returns empty."""
        pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL"}),
        )
        events = [
            _make_event(ticker="TSLA"),
            _make_event(ticker="RIVN"),
            _make_event(ticker="GOOG"),
        ]
        assert pipeline.process(events) == []

    def test_pipeline_preserves_event_payload(self):
        """Payload data survives the full pipeline pass."""
        pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL"}),
        )
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            ticker="AAPL",
            payload={"delta": 8.0, "old_score": 72.0, "new_score": 80.0},
        )
        results = pipeline.process([event])
        assert len(results) == 1
        assert results[0].event.payload["delta"] == 8.0
        assert results[0].event.payload["old_score"] == 72.0
        assert results[0].event.payload["new_score"] == 80.0

    def test_all_processed_events_are_correct_type(self):
        """Every result from the pipeline is a ProcessedEvent instance."""
        pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL", "GOOG"}),
        )
        events = [
            _make_event(ticker="AAPL"),
            _make_event(ticker="GOOG"),
        ]
        results = pipeline.process(events)
        for result in results:
            assert isinstance(result, ProcessedEvent)
            assert isinstance(result.classified_severity, EventSeverity)
            assert isinstance(result.rescore_trigger, RescoreTrigger)


# ---------------------------------------------------------------------------
# Throttle integration: pipeline -> throttle
# ---------------------------------------------------------------------------


class TestPipelineWithThrottle:
    """Events processed through pipeline, then throttled for notification delivery."""

    def test_pipeline_results_throttled_for_minor_events(self):
        """Minor events within the cooldown window are suppressed by the throttle."""
        pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL"}),
        )
        throttle = NotificationThrottle(cooldown=timedelta(hours=1))
        base_time = datetime(2026, 2, 10, 12, 0, 0)

        # First minor event — should be allowed
        events_batch_1 = [
            _make_event(
                event_type=EventType.PRICE_ALERT,
                ticker="AAPL",
                timestamp=base_time,
            ),
        ]
        results_1 = pipeline.process(events_batch_1)
        assert len(results_1) == 1
        assert results_1[0].classified_severity == EventSeverity.MINOR

        allowed = throttle.should_notify("AAPL", results_1[0].classified_severity, base_time)
        assert allowed is True
        throttle.record_notification("AAPL", base_time)

        # Second minor event 30 min later — should be blocked
        later = base_time + timedelta(minutes=30)
        events_batch_2 = [
            _make_event(
                event_type=EventType.MACRO_EVENT,
                ticker="AAPL",
                timestamp=later,
            ),
        ]
        results_2 = pipeline.process(events_batch_2)
        assert len(results_2) == 1
        assert results_2[0].classified_severity == EventSeverity.MINOR

        blocked = throttle.should_notify("AAPL", results_2[0].classified_severity, later)
        assert blocked is False

    def test_major_events_bypass_throttle_after_minor(self):
        """A MAJOR event bypasses the throttle even within cooldown window."""
        pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL"}),
        )
        throttle = NotificationThrottle(cooldown=timedelta(hours=1))
        base_time = datetime(2026, 2, 10, 12, 0, 0)

        # Minor event first
        minor_events = [
            _make_event(event_type=EventType.PRICE_ALERT, ticker="AAPL", timestamp=base_time),
        ]
        _minor_results = pipeline.process(minor_events)
        throttle.record_notification("AAPL", base_time)

        # Major event 5 minutes later — should bypass throttle
        soon_after = base_time + timedelta(minutes=5)
        major_events = [
            _make_event(event_type=EventType.EARNINGS_RELEASE, ticker="AAPL", timestamp=soon_after),
        ]
        major_results = pipeline.process(major_events)
        assert major_results[0].classified_severity == EventSeverity.MAJOR
        assert throttle.should_notify("AAPL", EventSeverity.MAJOR, soon_after) is True

    def test_different_tickers_throttled_independently(self):
        """Throttle tracks each ticker separately through the pipeline."""
        pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL", "GOOG"}),
        )
        throttle = NotificationThrottle(cooldown=timedelta(hours=1))
        base_time = datetime(2026, 2, 10, 12, 0, 0)

        # AAPL event
        aapl_events = [_make_event(event_type=EventType.PRICE_ALERT, ticker="AAPL")]
        aapl_results = pipeline.process(aapl_events)
        throttle.record_notification("AAPL", base_time)

        # GOOG event 10 minutes later — different ticker, should be allowed
        later = base_time + timedelta(minutes=10)
        goog_events = [_make_event(event_type=EventType.PRICE_ALERT, ticker="GOOG")]
        goog_results = pipeline.process(goog_events)
        assert throttle.should_notify("GOOG", goog_results[0].classified_severity, later) is True

        # AAPL again 10 minutes later — same ticker, should be blocked
        assert throttle.should_notify("AAPL", aapl_results[0].classified_severity, later) is False


# ---------------------------------------------------------------------------
# Score change events classified correctly based on delta
# ---------------------------------------------------------------------------


class TestScoreChangeClassification:
    """Verify score_change events are classified by delta through the full pipeline."""

    def setup_method(self):
        self.pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL"}),
        )

    def test_large_positive_delta_is_major(self):
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            ticker="AAPL",
            payload={"delta": 15.0, "old_score": 60.0, "new_score": 75.0},
        )
        results = self.pipeline.process([event])
        assert results[0].classified_severity == EventSeverity.MAJOR
        assert results[0].rescore_trigger == RescoreTrigger.IMMEDIATE

    def test_large_negative_delta_is_major(self):
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            ticker="AAPL",
            payload={"delta": -12.0, "old_score": 80.0, "new_score": 68.0},
        )
        results = self.pipeline.process([event])
        assert results[0].classified_severity == EventSeverity.MAJOR

    def test_moderate_delta_is_moderate(self):
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            ticker="AAPL",
            payload={"delta": 7.0},
        )
        results = self.pipeline.process([event])
        assert results[0].classified_severity == EventSeverity.MODERATE
        assert results[0].rescore_trigger == RescoreTrigger.DEFERRED_1H

    def test_small_delta_is_minor(self):
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            ticker="AAPL",
            payload={"delta": 2.0},
        )
        results = self.pipeline.process([event])
        assert results[0].classified_severity == EventSeverity.MINOR
        assert results[0].rescore_trigger == RescoreTrigger.NEXT_BATCH

    def test_score_delta_checker_agrees_with_classifier(self):
        """ScoreDeltaChecker threshold alignment with ImpactClassifier for score changes."""
        checker = ScoreDeltaChecker(threshold=5.0)
        classifier = ImpactClassifier()

        # Delta of 6.0 -> exceeds 5.0 threshold and classifier gives MODERATE
        event_moderate = _make_event(
            event_type=EventType.SCORE_CHANGE,
            ticker="AAPL",
            payload={"delta": 6.0},
        )
        assert checker.exceeds_threshold(6.0) is True
        assert classifier.classify(event_moderate) == EventSeverity.MODERATE

        # Delta of 3.0 -> does NOT exceed 5.0 threshold, classifier gives MINOR
        event_minor = _make_event(
            event_type=EventType.SCORE_CHANGE,
            ticker="AAPL",
            payload={"delta": 3.0},
        )
        assert checker.exceeds_threshold(3.0) is False
        assert classifier.classify(event_minor) == EventSeverity.MINOR


# ---------------------------------------------------------------------------
# Full flow: events -> pipeline -> notifications with throttling
# ---------------------------------------------------------------------------


class TestFullNotificationFlow:
    """End-to-end: create events, process through pipeline, generate notifications
    with throttle enforcement."""

    def test_full_notification_generation_flow(self):
        """Create events, run pipeline, generate notifications respecting the throttle."""
        pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL", "GOOG", "MSFT"}),
        )
        throttle = NotificationThrottle(cooldown=timedelta(hours=1))
        base_time = datetime(2026, 2, 10, 12, 0, 0)

        events = [
            _make_event(event_type=EventType.EARNINGS_RELEASE, ticker="AAPL", timestamp=base_time),
            _make_event(event_type=EventType.SEC_FILING, ticker="GOOG", timestamp=base_time),
            _make_event(event_type=EventType.PRICE_ALERT, ticker="MSFT", timestamp=base_time),
        ]

        processed = pipeline.process(events)
        assert len(processed) == 3

        # Generate notifications for each processed event, respecting throttle
        notifications: list[NotificationRecord] = []
        for pe in processed:
            if throttle.should_notify(pe.event.ticker, pe.classified_severity, base_time):
                notification = NotificationRecord(event=pe.event)
                notifications.append(notification)
                throttle.record_notification(pe.event.ticker, base_time)

        # All three should get notifications (first time for each ticker)
        assert len(notifications) == 3
        assert all(not n.read for n in notifications)
        assert all(n.notification_id for n in notifications)

    def test_second_batch_within_cooldown_throttled(self):
        """A second batch of minor events for the same tickers within
        the cooldown is suppressed."""
        pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL"}),
        )
        throttle = NotificationThrottle(cooldown=timedelta(hours=1))
        base_time = datetime(2026, 2, 10, 12, 0, 0)

        # First batch
        batch_1 = [_make_event(event_type=EventType.PRICE_ALERT, ticker="AAPL")]
        processed_1 = pipeline.process(batch_1)
        notifications_1: list[NotificationRecord] = []
        for pe in processed_1:
            if throttle.should_notify(pe.event.ticker, pe.classified_severity, base_time):
                notifications_1.append(NotificationRecord(event=pe.event))
                throttle.record_notification(pe.event.ticker, base_time)
        assert len(notifications_1) == 1

        # Second batch 30 minutes later — minor event for same ticker
        later = base_time + timedelta(minutes=30)
        batch_2 = [_make_event(event_type=EventType.MACRO_EVENT, ticker="AAPL")]
        processed_2 = pipeline.process(batch_2)
        notifications_2: list[NotificationRecord] = []
        for pe in processed_2:
            if throttle.should_notify(pe.event.ticker, pe.classified_severity, later):
                notifications_2.append(NotificationRecord(event=pe.event))
                throttle.record_notification(pe.event.ticker, later)
        # Should be throttled
        assert len(notifications_2) == 0

    def test_major_event_in_second_batch_bypasses_throttle(self):
        """A MAJOR event in a second batch bypasses the throttle."""
        pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL"}),
        )
        throttle = NotificationThrottle(cooldown=timedelta(hours=1))
        base_time = datetime(2026, 2, 10, 12, 0, 0)

        # First batch: minor event
        batch_1 = [_make_event(event_type=EventType.PRICE_ALERT, ticker="AAPL")]
        processed_1 = pipeline.process(batch_1)
        for pe in processed_1:
            if throttle.should_notify(pe.event.ticker, pe.classified_severity, base_time):
                throttle.record_notification(pe.event.ticker, base_time)

        # Second batch: MAJOR event 10 min later
        later = base_time + timedelta(minutes=10)
        batch_2 = [_make_event(event_type=EventType.EARNINGS_RELEASE, ticker="AAPL")]
        processed_2 = pipeline.process(batch_2)
        notifications: list[NotificationRecord] = []
        for pe in processed_2:
            if throttle.should_notify(pe.event.ticker, pe.classified_severity, later):
                notifications.append(NotificationRecord(event=pe.event))
                throttle.record_notification(pe.event.ticker, later)
        # MAJOR bypasses throttle
        assert len(notifications) == 1
        assert notifications[0].event.event_type == EventType.EARNINGS_RELEASE

    def test_notifications_after_cooldown_expires(self):
        """Once the cooldown expires, notifications are allowed again."""
        pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL"}),
        )
        throttle = NotificationThrottle(cooldown=timedelta(hours=1))
        base_time = datetime(2026, 2, 10, 12, 0, 0)

        # First batch
        batch_1 = [_make_event(event_type=EventType.PRICE_ALERT, ticker="AAPL")]
        processed_1 = pipeline.process(batch_1)
        for pe in processed_1:
            if throttle.should_notify(pe.event.ticker, pe.classified_severity, base_time):
                throttle.record_notification(pe.event.ticker, base_time)

        # Second batch after 1 hour — cooldown expired
        after_cooldown = base_time + timedelta(hours=1)
        batch_2 = [_make_event(event_type=EventType.PRICE_ALERT, ticker="AAPL")]
        processed_2 = pipeline.process(batch_2)
        notifications: list[NotificationRecord] = []
        for pe in processed_2:
            if throttle.should_notify(pe.event.ticker, pe.classified_severity, after_cooldown):
                notifications.append(NotificationRecord(event=pe.event))
                throttle.record_notification(pe.event.ticker, after_cooldown)
        assert len(notifications) == 1


# ---------------------------------------------------------------------------
# Import verification — ensure all exports work from the events package
# ---------------------------------------------------------------------------


class TestEventsPackageExports:
    """Verify that all expected symbols are importable from the events package."""

    def test_models_importable(self):
        from margin_engine.events import (
            EventRecord,
            EventSeverity,
            EventType,
            NotificationRecord,
            ScoreChangePayload,
        )

        assert EventType.EARNINGS_RELEASE == "earnings_release"
        assert EventSeverity.MAJOR == "major"
        assert EventRecord is not None
        assert NotificationRecord is not None
        assert ScoreChangePayload is not None

    def test_detector_importable(self):
        from margin_engine.events import DetectionConfig, EventDetector

        assert DetectionConfig is not None
        assert EventDetector is not None

    def test_pipeline_importable(self):
        from margin_engine.events import (
            EventPipeline,
            ImpactClassifier,
            ProcessedEvent,
            RelevanceFilter,
            RescoreTrigger,
            ScoreDeltaChecker,
        )

        assert EventPipeline is not None
        assert ImpactClassifier is not None
        assert ProcessedEvent is not None
        assert RelevanceFilter is not None
        assert RescoreTrigger is not None
        assert ScoreDeltaChecker is not None

    def test_throttle_importable(self):
        from margin_engine.events import NotificationThrottle

        assert NotificationThrottle is not None

    def test_events_module_accessible_from_engine(self):
        import margin_engine

        assert hasattr(margin_engine, "events")
        assert hasattr(margin_engine.events, "EventPipeline")
        assert hasattr(margin_engine.events, "NotificationThrottle")
