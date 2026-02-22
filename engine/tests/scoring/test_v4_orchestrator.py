"""Tests for v4 orchestrator — three-track scoring with style-aware promotion rules."""

from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_orchestrator import V3TrackResult
from margin_engine.scoring.v4_orchestrator import orchestrate_v4


class TestV4Orchestrator:
    def _make_track(
        self,
        track: str,
        qualifies: bool,
        conviction: ConvictionLevel,
        score: float = 1.0,
    ) -> V3TrackResult:
        return V3TrackResult(
            track=track,
            qualifies=qualifies,
            conviction=conviction,
            score=score,
            gates_passed=4 if qualifies else 1,
            total_gates=4,
        )

    def test_only_track_a_qualifies(self):
        result = orchestrate_v4(
            "TEST",
            track_a=self._make_track("compounder", True, ConvictionLevel.HIGH),
            track_b=self._make_track("mispricing", False, ConvictionLevel.NONE),
            track_c=self._make_track("efficient_growth", False, ConvictionLevel.NONE),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "compounder"
        assert result.conviction == ConvictionLevel.HIGH

    def test_only_track_c_qualifies(self):
        result = orchestrate_v4(
            "TEST",
            track_a=self._make_track("compounder", False, ConvictionLevel.NONE),
            track_b=self._make_track("mispricing", False, ConvictionLevel.NONE),
            track_c=self._make_track("efficient_growth", True, ConvictionLevel.HIGH),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "efficient_growth"
        assert result.conviction == ConvictionLevel.HIGH

    def test_track_a_plus_c_promotes_to_exceptional(self):
        result = orchestrate_v4(
            "TEST",
            track_a=self._make_track("compounder", True, ConvictionLevel.HIGH),
            track_b=self._make_track("mispricing", False, ConvictionLevel.NONE),
            track_c=self._make_track("efficient_growth", True, ConvictionLevel.HIGH),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "compounder_growth"
        assert result.conviction == ConvictionLevel.EXCEPTIONAL

    def test_track_a_plus_b_both_promotion(self):
        result = orchestrate_v4(
            "TEST",
            track_a=self._make_track("compounder", True, ConvictionLevel.HIGH),
            track_b=self._make_track("mispricing", True, ConvictionLevel.HIGH),
            track_c=self._make_track("efficient_growth", False, ConvictionLevel.NONE),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "both"
        assert result.conviction == ConvictionLevel.EXCEPTIONAL

    def test_all_three_qualify(self):
        result = orchestrate_v4(
            "TEST",
            track_a=self._make_track("compounder", True, ConvictionLevel.HIGH),
            track_b=self._make_track("mispricing", True, ConvictionLevel.HIGH),
            track_c=self._make_track("efficient_growth", True, ConvictionLevel.HIGH),
            timing_signal="buy_now",
        )
        assert result.conviction == ConvictionLevel.EXCEPTIONAL
        assert result.max_position_pct == 20.0

    def test_neither_qualifies(self):
        result = orchestrate_v4(
            "TEST",
            track_a=self._make_track("compounder", False, ConvictionLevel.NONE),
            track_b=self._make_track("mispricing", False, ConvictionLevel.NONE),
            track_c=self._make_track("efficient_growth", False, ConvictionLevel.NONE),
            timing_signal="buy_now",
        )
        assert result.opportunity_type == "neither"
        assert result.conviction == ConvictionLevel.NONE
        assert result.max_position_pct == 0.0

    def test_position_sizing_efficient_growth_high(self):
        result = orchestrate_v4(
            "TEST",
            track_a=self._make_track("compounder", False, ConvictionLevel.NONE),
            track_b=self._make_track("mispricing", False, ConvictionLevel.NONE),
            track_c=self._make_track("efficient_growth", True, ConvictionLevel.HIGH),
            timing_signal="buy_now",
        )
        assert result.max_position_pct == 8.0

    def test_position_sizing_compounder_growth_exceptional(self):
        result = orchestrate_v4(
            "TEST",
            track_a=self._make_track("compounder", True, ConvictionLevel.EXCEPTIONAL),
            track_b=self._make_track("mispricing", False, ConvictionLevel.NONE),
            track_c=self._make_track("efficient_growth", True, ConvictionLevel.HIGH),
            timing_signal="buy_now",
        )
        assert result.max_position_pct == 20.0
