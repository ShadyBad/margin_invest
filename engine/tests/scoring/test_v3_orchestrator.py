"""Tests for v3 orchestrator — runs both tracks, assigns conviction, handles 'both'."""

import pytest
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_orchestrator import (
    V3Result,
    V3TrackResult,
    orchestrate_v3,
)


def _track_a_exceptional() -> V3TrackResult:
    return V3TrackResult(
        track="compounder",
        qualifies=True,
        conviction=ConvictionLevel.EXCEPTIONAL,
        score=0.048,
        gates_passed=4,
        total_gates=4,
    )


def _track_b_exceptional() -> V3TrackResult:
    return V3TrackResult(
        track="mispricing",
        qualifies=True,
        conviction=ConvictionLevel.EXCEPTIONAL,
        score=9.0,
        gates_passed=4,
        total_gates=4,
    )


def _track_a_high() -> V3TrackResult:
    return V3TrackResult(
        track="compounder",
        qualifies=True,
        conviction=ConvictionLevel.HIGH,
        score=0.012,
        gates_passed=4,
        total_gates=4,
    )


def _track_b_high() -> V3TrackResult:
    return V3TrackResult(
        track="mispricing",
        qualifies=True,
        conviction=ConvictionLevel.HIGH,
        score=5.0,
        gates_passed=4,
        total_gates=4,
    )


def _track_a_medium() -> V3TrackResult:
    return V3TrackResult(
        track="compounder",
        qualifies=True,
        conviction=ConvictionLevel.MEDIUM,
        score=0.005,
        gates_passed=3,
        total_gates=4,
    )


def _track_b_medium() -> V3TrackResult:
    return V3TrackResult(
        track="mispricing",
        qualifies=True,
        conviction=ConvictionLevel.MEDIUM,
        score=2.5,
        gates_passed=3,
        total_gates=4,
    )


def _track_not_qualified() -> V3TrackResult:
    return V3TrackResult(
        track="compounder",
        qualifies=False,
        conviction=ConvictionLevel.NONE,
        score=0.0,
        gates_passed=1,
        total_gates=4,
    )


def _track_b_not_qualified() -> V3TrackResult:
    return V3TrackResult(
        track="mispricing",
        qualifies=False,
        conviction=ConvictionLevel.NONE,
        score=0.0,
        gates_passed=1,
        total_gates=4,
    )


class TestOrchestrate:
    def test_both_exceptional_promotes_to_both(self):
        result = orchestrate_v3(
            ticker="RARE",
            track_a=_track_a_exceptional(),
            track_b=_track_b_exceptional(),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "both"
        assert result.conviction == ConvictionLevel.EXCEPTIONAL
        assert result.max_position_pct == 20.0

    def test_both_high_promotes_to_both(self):
        result = orchestrate_v3(
            ticker="DUAL",
            track_a=_track_a_high(),
            track_b=_track_b_high(),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "both"
        assert result.conviction == ConvictionLevel.EXCEPTIONAL
        assert result.max_position_pct == 20.0

    def test_mixed_exceptional_high_promotes_to_both(self):
        result = orchestrate_v3(
            ticker="MIX",
            track_a=_track_a_exceptional(),
            track_b=_track_b_high(),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "both"
        assert result.conviction == ConvictionLevel.EXCEPTIONAL
        assert result.max_position_pct == 20.0

    def test_only_track_a_qualifies(self):
        result = orchestrate_v3(
            ticker="COMP",
            track_a=_track_a_high(),
            track_b=_track_b_not_qualified(),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "compounder"
        assert result.conviction == ConvictionLevel.HIGH
        assert result.max_position_pct == 8.0

    def test_only_track_b_qualifies(self):
        result = orchestrate_v3(
            ticker="MISP",
            track_a=_track_not_qualified(),
            track_b=_track_b_exceptional(),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "mispricing"
        assert result.conviction == ConvictionLevel.EXCEPTIONAL
        assert result.max_position_pct == 12.0

    def test_neither_qualifies(self):
        result = orchestrate_v3(
            ticker="MEDI",
            track_a=_track_not_qualified(),
            track_b=_track_b_not_qualified(),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "neither"
        assert result.conviction == ConvictionLevel.NONE
        assert result.max_position_pct == 0.0

    def test_zero_output_valid(self):
        """System can output zero actionable results."""
        result = orchestrate_v3(
            ticker="NONE",
            track_a=_track_not_qualified(),
            track_b=_track_b_not_qualified(),
            timing_signal="buy_now",
        )
        assert result.max_position_pct == 0.0

    def test_medium_both_tracks_no_promotion(self):
        """Both at MEDIUM should NOT promote to 'both' — requires HIGH+."""
        result = orchestrate_v3(
            ticker="WATCH",
            track_a=_track_a_medium(),
            track_b=_track_b_medium(),
            timing_signal="buy_now",
        )
        # Both qualify but neither is HIGH+, so no "both" promotion
        assert result.opportunity_type != "both"
        assert result.conviction == ConvictionLevel.MEDIUM
        assert result.max_position_pct == 4.0  # Medium compounder starter

    def test_one_medium_one_high_no_promotion(self):
        """One MEDIUM + one HIGH should NOT promote — both need HIGH+."""
        result = orchestrate_v3(
            ticker="HALF",
            track_a=_track_a_medium(),
            track_b=_track_b_high(),
            timing_signal="buy_now",
        )
        # Track B is stronger (HIGH vs MEDIUM), so mispricing wins
        assert result.opportunity_type == "mispricing"
        assert result.conviction == ConvictionLevel.HIGH


class TestV3ResultModel:
    def test_result_contains_both_tracks(self):
        result = orchestrate_v3(
            ticker="TEST",
            track_a=_track_a_high(),
            track_b=_track_b_not_qualified(),
            timing_signal="add_on_pullback",
        )
        assert result.track_a.track == "compounder"
        assert result.track_b.track == "mispricing"
        assert result.timing_signal == "add_on_pullback"
        assert result.ticker == "TEST"

    def test_result_serialization(self):
        result = orchestrate_v3(
            ticker="SER",
            track_a=_track_a_exceptional(),
            track_b=_track_b_exceptional(),
            timing_signal="buy_now",
        )
        data = result.model_dump()
        assert data["ticker"] == "SER"
        assert data["opportunity_type"] == "both"
        assert data["conviction"] == "exceptional"
        assert data["max_position_pct"] == 20.0
        assert data["track_a"]["track"] == "compounder"
        assert data["track_b"]["track"] == "mispricing"


class TestV3TrackResultModel:
    def test_track_result_fields(self):
        tr = V3TrackResult(
            track="compounder",
            qualifies=True,
            conviction=ConvictionLevel.HIGH,
            score=0.012,
            gates_passed=4,
            total_gates=4,
        )
        assert tr.track == "compounder"
        assert tr.qualifies is True
        assert tr.conviction == ConvictionLevel.HIGH
        assert tr.score == 0.012
        assert tr.gates_passed == 4
        assert tr.total_gates == 4
