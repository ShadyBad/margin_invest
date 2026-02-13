"""Tests for event system models and detection interfaces."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest
from margin_engine.events.detector import DetectionConfig, EventDetector
from margin_engine.events.models import (
    EventRecord,
    EventSeverity,
    EventType,
    NotificationRecord,
    ScoreChangePayload,
)


class TestEventType:
    def test_has_all_eight_members(self):
        members = list(EventType)
        assert len(members) == 8

    def test_member_values(self):
        assert EventType.EARNINGS_RELEASE == "earnings_release"
        assert EventType.SEC_FILING == "sec_filing"
        assert EventType.INSIDER_TRANSACTION == "insider_transaction"
        assert EventType.PRICE_ALERT == "price_alert"
        assert EventType.ANALYST_RATING_CHANGE == "analyst_rating_change"
        assert EventType.MACRO_EVENT == "macro_event"
        assert EventType.MATERIAL_NEWS == "material_news"
        assert EventType.SCORE_CHANGE == "score_change"

    def test_is_str_enum(self):
        assert isinstance(EventType.EARNINGS_RELEASE, str)


class TestEventSeverity:
    def test_has_three_members(self):
        members = list(EventSeverity)
        assert len(members) == 3

    def test_member_values(self):
        assert EventSeverity.MAJOR == "major"
        assert EventSeverity.MODERATE == "moderate"
        assert EventSeverity.MINOR == "minor"

    def test_is_str_enum(self):
        assert isinstance(EventSeverity.MAJOR, str)


class TestEventRecord:
    def test_creates_with_valid_data(self):
        record = EventRecord(
            event_type=EventType.EARNINGS_RELEASE,
            ticker="AAPL",
            timestamp=datetime(2026, 1, 30, 16, 30),
            severity=EventSeverity.MAJOR,
            source="finnhub_calendar",
            payload={"eps_actual": 2.18, "eps_estimate": 2.10},
        )
        assert record.event_type == EventType.EARNINGS_RELEASE
        assert record.ticker == "AAPL"
        assert record.severity == EventSeverity.MAJOR
        assert record.source == "finnhub_calendar"
        assert record.payload["eps_actual"] == 2.18

    def test_auto_generates_event_id(self):
        record = EventRecord(
            event_type=EventType.SEC_FILING,
            ticker="MSFT",
            timestamp=datetime(2026, 2, 1, 9, 0),
            severity=EventSeverity.MODERATE,
            source="edgar_rss",
        )
        # event_id should be a valid UUID string
        uuid_obj = UUID(record.event_id)
        assert uuid_obj.version == 4

    def test_two_records_get_different_ids(self):
        kwargs = dict(
            event_type=EventType.PRICE_ALERT,
            ticker="NVDA",
            timestamp=datetime(2026, 2, 1, 10, 0),
            severity=EventSeverity.MINOR,
            source="price_monitor",
        )
        r1 = EventRecord(**kwargs)
        r2 = EventRecord(**kwargs)
        assert r1.event_id != r2.event_id

    def test_payload_defaults_to_empty_dict(self):
        record = EventRecord(
            event_type=EventType.MACRO_EVENT,
            ticker="SPY",
            timestamp=datetime(2026, 2, 1, 8, 30),
            severity=EventSeverity.MAJOR,
            source="fred_calendar",
        )
        assert record.payload == {}

    def test_serializes_to_json(self):
        record = EventRecord(
            event_type=EventType.ANALYST_RATING_CHANGE,
            ticker="GOOG",
            timestamp=datetime(2026, 2, 5, 12, 0),
            severity=EventSeverity.MODERATE,
            source="finnhub",
            payload={"old_rating": "hold", "new_rating": "buy"},
        )
        data = record.model_dump()
        assert data["event_type"] == "analyst_rating_change"
        assert data["severity"] == "moderate"
        assert data["ticker"] == "GOOG"


class TestScoreChangePayload:
    def test_creates_with_valid_data(self):
        payload = ScoreChangePayload(
            old_score=82.5,
            new_score=91.3,
            delta=8.8,
            conviction_change="none -> watchlist",
        )
        assert payload.old_score == 82.5
        assert payload.new_score == 91.3
        assert payload.delta == 8.8
        assert payload.conviction_change == "none -> watchlist"

    def test_conviction_change_is_optional(self):
        payload = ScoreChangePayload(
            old_score=90.0,
            new_score=96.0,
            delta=6.0,
        )
        assert payload.conviction_change is None

    def test_delta_matches_score_difference(self):
        """Verify that delta accurately represents the score change."""
        old, new = 85.0, 92.5
        payload = ScoreChangePayload(
            old_score=old,
            new_score=new,
            delta=new - old,
        )
        assert payload.delta == pytest.approx(new - old)

    def test_negative_delta(self):
        payload = ScoreChangePayload(
            old_score=95.0,
            new_score=88.0,
            delta=-7.0,
        )
        assert payload.delta == -7.0


class TestNotificationRecord:
    def test_defaults_to_unread(self):
        event = EventRecord(
            event_type=EventType.MATERIAL_NEWS,
            ticker="TSLA",
            timestamp=datetime(2026, 2, 10, 14, 0),
            severity=EventSeverity.MAJOR,
            source="finnhub_ai",
            payload={"headline": "Tesla announces new factory"},
        )
        notification = NotificationRecord(event=event)
        assert notification.read is False

    def test_auto_generates_notification_id(self):
        event = EventRecord(
            event_type=EventType.INSIDER_TRANSACTION,
            ticker="AMZN",
            timestamp=datetime(2026, 2, 10, 15, 0),
            severity=EventSeverity.MODERATE,
            source="edgar_rss",
        )
        notification = NotificationRecord(event=event)
        uuid_obj = UUID(notification.notification_id)
        assert uuid_obj.version == 4

    def test_auto_generates_created_at(self):
        event = EventRecord(
            event_type=EventType.SCORE_CHANGE,
            ticker="META",
            timestamp=datetime(2026, 2, 10, 16, 0),
            severity=EventSeverity.MAJOR,
            source="internal",
        )
        notification = NotificationRecord(event=event)
        assert isinstance(notification.created_at, datetime)

    def test_can_mark_as_read(self):
        event = EventRecord(
            event_type=EventType.EARNINGS_RELEASE,
            ticker="AAPL",
            timestamp=datetime(2026, 1, 30, 16, 30),
            severity=EventSeverity.MAJOR,
            source="finnhub_calendar",
        )
        notification = NotificationRecord(event=event, read=True)
        assert notification.read is True


class TestDetectionConfig:
    def test_creates_with_valid_data(self):
        config = DetectionConfig(
            check_interval_seconds=300,
            enabled_event_types=[EventType.EARNINGS_RELEASE, EventType.SEC_FILING],
        )
        assert config.check_interval_seconds == 300
        assert len(config.enabled_event_types) == 2
        assert EventType.EARNINGS_RELEASE in config.enabled_event_types

    def test_enabled_event_types_defaults_to_empty(self):
        config = DetectionConfig(check_interval_seconds=60)
        assert config.enabled_event_types == []

    def test_check_interval_must_be_positive(self):
        with pytest.raises(ValueError):
            DetectionConfig(check_interval_seconds=0)
        with pytest.raises(ValueError):
            DetectionConfig(check_interval_seconds=-1)

    def test_all_event_types_can_be_enabled(self):
        config = DetectionConfig(
            check_interval_seconds=60,
            enabled_event_types=list(EventType),
        )
        assert len(config.enabled_event_types) == 8


class TestEventDetectorProtocol:
    def test_class_satisfies_protocol(self):
        """A class with a detect method satisfies the EventDetector protocol."""

        class DummyDetector:
            def detect(self, ticker: str) -> list[EventRecord]:
                return []

        detector = DummyDetector()
        assert isinstance(detector, EventDetector)

    def test_class_without_detect_does_not_satisfy(self):
        """A class without detect does not satisfy the protocol."""

        class NotADetector:
            pass

        obj = NotADetector()
        assert not isinstance(obj, EventDetector)

    def test_detector_returns_events(self):
        """A detector can return a list of EventRecord instances."""

        class EarningsDetector:
            def detect(self, ticker: str) -> list[EventRecord]:
                return [
                    EventRecord(
                        event_type=EventType.EARNINGS_RELEASE,
                        ticker=ticker,
                        timestamp=datetime(2026, 1, 30, 16, 30),
                        severity=EventSeverity.MAJOR,
                        source="finnhub_calendar",
                        payload={"eps_actual": 2.18},
                    )
                ]

        detector = EarningsDetector()
        events = detector.detect("AAPL")
        assert len(events) == 1
        assert events[0].event_type == EventType.EARNINGS_RELEASE
        assert events[0].ticker == "AAPL"
