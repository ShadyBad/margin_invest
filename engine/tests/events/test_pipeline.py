"""Tests for the event processing pipeline."""

from __future__ import annotations

from datetime import datetime

from margin_engine.events.models import EventRecord, EventSeverity, EventType
from margin_engine.events.pipeline import (
    EventPipeline,
    ImpactClassifier,
    ProcessedEvent,
    RelevanceFilter,
    RescoreTrigger,
    ScoreDeltaChecker,
    get_rescore_trigger,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    event_type: EventType = EventType.EARNINGS_RELEASE,
    ticker: str = "AAPL",
    severity: EventSeverity = EventSeverity.MAJOR,
    payload: dict | None = None,
) -> EventRecord:
    return EventRecord(
        event_type=event_type,
        ticker=ticker,
        timestamp=datetime(2026, 2, 10, 12, 0),
        severity=severity,
        source="test",
        payload=payload or {},
    )


# ---------------------------------------------------------------------------
# RelevanceFilter
# ---------------------------------------------------------------------------


class TestRelevanceFilter:
    def test_keeps_watched_tickers(self):
        rf = RelevanceFilter(watched_tickers={"AAPL", "GOOG"})
        events = [_make_event(ticker="AAPL"), _make_event(ticker="GOOG")]
        result = rf.filter(events)
        assert len(result) == 2
        assert {e.ticker for e in result} == {"AAPL", "GOOG"}

    def test_filters_out_unwatched_tickers(self):
        rf = RelevanceFilter(watched_tickers={"AAPL"})
        events = [_make_event(ticker="AAPL"), _make_event(ticker="TSLA")]
        result = rf.filter(events)
        assert len(result) == 1
        assert result[0].ticker == "AAPL"

    def test_empty_watched_set_filters_all(self):
        rf = RelevanceFilter(watched_tickers=set())
        events = [_make_event(ticker="AAPL")]
        result = rf.filter(events)
        assert result == []

    def test_empty_events_returns_empty(self):
        rf = RelevanceFilter(watched_tickers={"AAPL"})
        assert rf.filter([]) == []

    def test_watched_tickers_property(self):
        tickers = {"AAPL", "MSFT", "NVDA"}
        rf = RelevanceFilter(watched_tickers=tickers)
        assert rf.watched_tickers == tickers


# ---------------------------------------------------------------------------
# ImpactClassifier
# ---------------------------------------------------------------------------


class TestImpactClassifier:
    def setup_method(self):
        self.classifier = ImpactClassifier()

    # --- MAJOR types ---

    def test_earnings_release_is_major(self):
        event = _make_event(event_type=EventType.EARNINGS_RELEASE)
        assert self.classifier.classify(event) == EventSeverity.MAJOR

    # --- MODERATE types ---

    def test_analyst_rating_change_is_moderate(self):
        event = _make_event(event_type=EventType.ANALYST_RATING_CHANGE)
        assert self.classifier.classify(event) == EventSeverity.MODERATE

    def test_insider_transaction_is_moderate(self):
        event = _make_event(event_type=EventType.INSIDER_TRANSACTION)
        assert self.classifier.classify(event) == EventSeverity.MODERATE

    def test_sec_filing_is_moderate(self):
        event = _make_event(event_type=EventType.SEC_FILING)
        assert self.classifier.classify(event) == EventSeverity.MODERATE

    # --- MINOR types ---

    def test_price_alert_is_minor(self):
        event = _make_event(event_type=EventType.PRICE_ALERT)
        assert self.classifier.classify(event) == EventSeverity.MINOR

    def test_macro_event_is_minor(self):
        event = _make_event(event_type=EventType.MACRO_EVENT)
        assert self.classifier.classify(event) == EventSeverity.MINOR

    def test_material_news_is_minor(self):
        event = _make_event(event_type=EventType.MATERIAL_NEWS)
        assert self.classifier.classify(event) == EventSeverity.MINOR

    # --- score_change delta thresholds ---

    def test_score_change_delta_above_10_is_major(self):
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            payload={"delta": 15.0},
        )
        assert self.classifier.classify(event) == EventSeverity.MAJOR

    def test_score_change_delta_exactly_10_is_moderate(self):
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            payload={"delta": 10.0},
        )
        assert self.classifier.classify(event) == EventSeverity.MODERATE

    def test_score_change_delta_between_5_and_10_is_moderate(self):
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            payload={"delta": 7.5},
        )
        assert self.classifier.classify(event) == EventSeverity.MODERATE

    def test_score_change_delta_exactly_5_is_moderate(self):
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            payload={"delta": 5.0},
        )
        assert self.classifier.classify(event) == EventSeverity.MODERATE

    def test_score_change_delta_below_5_is_minor(self):
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            payload={"delta": 3.0},
        )
        assert self.classifier.classify(event) == EventSeverity.MINOR

    def test_score_change_negative_delta_uses_absolute_value(self):
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            payload={"delta": -12.0},
        )
        assert self.classifier.classify(event) == EventSeverity.MAJOR

    def test_score_change_missing_delta_defaults_to_minor(self):
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            payload={},
        )
        assert self.classifier.classify(event) == EventSeverity.MINOR

    def test_score_change_zero_delta_is_minor(self):
        event = _make_event(
            event_type=EventType.SCORE_CHANGE,
            payload={"delta": 0.0},
        )
        assert self.classifier.classify(event) == EventSeverity.MINOR


# ---------------------------------------------------------------------------
# get_rescore_trigger
# ---------------------------------------------------------------------------


class TestGetRescoreTrigger:
    def test_major_maps_to_immediate(self):
        assert get_rescore_trigger(EventSeverity.MAJOR) == RescoreTrigger.IMMEDIATE

    def test_moderate_maps_to_deferred_1h(self):
        assert get_rescore_trigger(EventSeverity.MODERATE) == RescoreTrigger.DEFERRED_1H

    def test_minor_maps_to_next_batch(self):
        assert get_rescore_trigger(EventSeverity.MINOR) == RescoreTrigger.NEXT_BATCH

    def test_all_severities_have_triggers(self):
        for severity in EventSeverity:
            trigger = get_rescore_trigger(severity)
            assert isinstance(trigger, RescoreTrigger)


# ---------------------------------------------------------------------------
# RescoreTrigger
# ---------------------------------------------------------------------------


class TestRescoreTrigger:
    def test_is_str_enum(self):
        assert isinstance(RescoreTrigger.IMMEDIATE, str)

    def test_has_three_members(self):
        assert len(list(RescoreTrigger)) == 3

    def test_values(self):
        assert RescoreTrigger.IMMEDIATE == "immediate"
        assert RescoreTrigger.DEFERRED_1H == "deferred_1h"
        assert RescoreTrigger.NEXT_BATCH == "next_batch"


# ---------------------------------------------------------------------------
# ScoreDeltaChecker
# ---------------------------------------------------------------------------


class TestScoreDeltaChecker:
    def test_delta_above_threshold_returns_true(self):
        checker = ScoreDeltaChecker(threshold=5.0)
        assert checker.exceeds_threshold(6.0) is True

    def test_delta_at_threshold_returns_false(self):
        checker = ScoreDeltaChecker(threshold=5.0)
        assert checker.exceeds_threshold(5.0) is False

    def test_delta_below_threshold_returns_false(self):
        checker = ScoreDeltaChecker(threshold=5.0)
        assert checker.exceeds_threshold(3.0) is False

    def test_negative_delta_uses_absolute_value(self):
        checker = ScoreDeltaChecker(threshold=5.0)
        assert checker.exceeds_threshold(-7.0) is True

    def test_custom_threshold(self):
        checker = ScoreDeltaChecker(threshold=10.0)
        assert checker.exceeds_threshold(8.0) is False
        assert checker.exceeds_threshold(11.0) is True

    def test_default_threshold_is_5(self):
        checker = ScoreDeltaChecker()
        assert checker.threshold == 5.0

    def test_zero_delta_does_not_exceed(self):
        checker = ScoreDeltaChecker(threshold=5.0)
        assert checker.exceeds_threshold(0.0) is False


# ---------------------------------------------------------------------------
# EventPipeline (end-to-end)
# ---------------------------------------------------------------------------


class TestEventPipeline:
    def setup_method(self):
        self.pipeline = EventPipeline(
            relevance_filter=RelevanceFilter(watched_tickers={"AAPL", "GOOG", "MSFT"}),
        )

    def test_filters_and_classifies_events(self):
        events = [
            _make_event(event_type=EventType.EARNINGS_RELEASE, ticker="AAPL"),
            _make_event(event_type=EventType.PRICE_ALERT, ticker="TSLA"),  # not watched
            _make_event(event_type=EventType.SEC_FILING, ticker="GOOG"),
        ]
        results = self.pipeline.process(events)
        assert len(results) == 2

        # AAPL earnings -> MAJOR -> immediate
        aapl = results[0]
        assert aapl.event.ticker == "AAPL"
        assert aapl.classified_severity == EventSeverity.MAJOR
        assert aapl.rescore_trigger == RescoreTrigger.IMMEDIATE

        # GOOG SEC filing -> MODERATE -> deferred_1h
        goog = results[1]
        assert goog.event.ticker == "GOOG"
        assert goog.classified_severity == EventSeverity.MODERATE
        assert goog.rescore_trigger == RescoreTrigger.DEFERRED_1H

    def test_empty_input_returns_empty(self):
        assert self.pipeline.process([]) == []

    def test_all_filtered_out_returns_empty(self):
        events = [_make_event(ticker="TSLA"), _make_event(ticker="RIVN")]
        assert self.pipeline.process(events) == []

    def test_score_change_classification_in_pipeline(self):
        events = [
            _make_event(
                event_type=EventType.SCORE_CHANGE,
                ticker="MSFT",
                payload={"delta": 12.0},
            ),
        ]
        results = self.pipeline.process(events)
        assert len(results) == 1
        assert results[0].classified_severity == EventSeverity.MAJOR
        assert results[0].rescore_trigger == RescoreTrigger.IMMEDIATE

    def test_returns_processed_event_instances(self):
        events = [_make_event(ticker="AAPL")]
        results = self.pipeline.process(events)
        assert len(results) == 1
        assert isinstance(results[0], ProcessedEvent)

    def test_pipeline_preserves_original_event(self):
        original = _make_event(ticker="AAPL", event_type=EventType.MACRO_EVENT)
        results = self.pipeline.process([original])
        assert results[0].event is original

    def test_minor_event_gets_next_batch_trigger(self):
        events = [
            _make_event(event_type=EventType.PRICE_ALERT, ticker="GOOG"),
        ]
        results = self.pipeline.process(events)
        assert results[0].classified_severity == EventSeverity.MINOR
        assert results[0].rescore_trigger == RescoreTrigger.NEXT_BATCH
