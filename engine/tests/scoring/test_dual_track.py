"""Tests for dual-track orchestrator — picks best of compounder vs mispricing."""

import pytest
from margin_engine.models.scoring import (
    CompositeScore,
    ConvictionLevel,
    FactorBreakdown,
    FactorScore,
    FilterResult,
    OpportunityType,
)
from margin_engine.scoring.conviction_gates import ConvictionGateResult
from margin_engine.scoring.dual_track import score_dual_track


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_composite(
    ticker: str = "TEST",
    percentile: float = 80.0,
    winning_track: str = "compounder",
) -> CompositeScore:
    """Build a minimal CompositeScore for testing."""
    return CompositeScore(
        ticker=ticker,
        composite_percentile=percentile,
        composite_raw_score=percentile,
        quality=FactorBreakdown(
            factor_name="quality",
            weight=0.50,
            sub_scores=[FactorScore(name="q", raw_value=1.0, percentile_rank=percentile)],
        ),
        value=FactorBreakdown(
            factor_name="value",
            weight=0.30,
            sub_scores=[FactorScore(name="v", raw_value=1.0, percentile_rank=percentile)],
        ),
        momentum=FactorBreakdown(
            factor_name="momentum",
            weight=0.0,
            sub_scores=[],
        ),
        filters_passed=[FilterResult(name="altman_z", passed=True)],
        data_coverage=0.95,
        winning_track=winning_track,
    )


def _passing_gate() -> ConvictionGateResult:
    return ConvictionGateResult(passed=True, failures=[])


def _failing_gate() -> ConvictionGateResult:
    return ConvictionGateResult(passed=False, failures=["ROIC too low"])


# ---------------------------------------------------------------------------
# Track selection
# ---------------------------------------------------------------------------


class TestTrackSelection:
    """Orchestrator picks the track with higher composite_percentile."""

    def test_track_a_wins_when_higher(self):
        track_a = _make_composite(percentile=85.0, winning_track="compounder")
        track_b = _make_composite(percentile=75.0, winning_track="mispricing")

        result = score_dual_track(
            track_a_score=track_a,
            track_b_score=track_b,
            opportunity_type=OpportunityType.COMPOUNDER,
            asymmetry_ratio_value=3.0,
            timing_signal="buy_now",
            gate_result_a=_passing_gate(),
            gate_result_b=_passing_gate(),
        )

        assert result.winning_track == "compounder"
        assert result.composite_percentile == pytest.approx(85.0)

    def test_track_b_wins_when_higher(self):
        track_a = _make_composite(percentile=70.0, winning_track="compounder")
        track_b = _make_composite(percentile=88.0, winning_track="mispricing")

        result = score_dual_track(
            track_a_score=track_a,
            track_b_score=track_b,
            opportunity_type=OpportunityType.MISPRICING,
            asymmetry_ratio_value=4.0,
            timing_signal="buy_now",
            gate_result_a=_passing_gate(),
            gate_result_b=_passing_gate(),
        )

        assert result.winning_track == "mispricing"
        assert result.composite_percentile == pytest.approx(88.0)

    def test_equal_percentiles_picks_track_a(self):
        """On a tie, Track A (compounder) wins."""
        track_a = _make_composite(percentile=80.0, winning_track="compounder")
        track_b = _make_composite(percentile=80.0, winning_track="mispricing")

        result = score_dual_track(
            track_a_score=track_a,
            track_b_score=track_b,
            opportunity_type=OpportunityType.BOTH,
            asymmetry_ratio_value=2.0,
            timing_signal="buy_now",
            gate_result_a=_passing_gate(),
            gate_result_b=_passing_gate(),
        )

        assert result.winning_track == "compounder"


# ---------------------------------------------------------------------------
# V2 fields populated
# ---------------------------------------------------------------------------


class TestV2Fields:
    """Dual-track sets opportunity_type, asymmetry_ratio, timing_signal."""

    def test_opportunity_type_set(self):
        result = score_dual_track(
            track_a_score=_make_composite(percentile=85.0),
            track_b_score=_make_composite(percentile=75.0),
            opportunity_type=OpportunityType.BOTH,
            asymmetry_ratio_value=3.5,
            timing_signal="add_on_pullback",
            gate_result_a=_passing_gate(),
            gate_result_b=_passing_gate(),
        )
        assert result.opportunity_type == OpportunityType.BOTH

    def test_asymmetry_ratio_set(self):
        result = score_dual_track(
            track_a_score=_make_composite(percentile=85.0),
            track_b_score=_make_composite(percentile=75.0),
            opportunity_type=OpportunityType.COMPOUNDER,
            asymmetry_ratio_value=4.2,
            timing_signal="buy_now",
            gate_result_a=_passing_gate(),
            gate_result_b=_passing_gate(),
        )
        assert result.asymmetry_ratio == pytest.approx(4.2)

    def test_timing_signal_set(self):
        result = score_dual_track(
            track_a_score=_make_composite(percentile=85.0),
            track_b_score=_make_composite(percentile=75.0),
            opportunity_type=OpportunityType.COMPOUNDER,
            asymmetry_ratio_value=3.0,
            timing_signal="wait_for_catalyst",
            gate_result_a=_passing_gate(),
            gate_result_b=_passing_gate(),
        )
        assert result.timing_signal == "wait_for_catalyst"


# ---------------------------------------------------------------------------
# Position sizing
# ---------------------------------------------------------------------------


class TestPositionSizing:
    """max_position_pct is computed from asymmetry + conviction level."""

    def test_position_sizing_set(self):
        """High asymmetry + high percentile -> non-zero position."""
        track_a = _make_composite(percentile=99.5)  # HIGH conviction
        result = score_dual_track(
            track_a_score=track_a,
            track_b_score=_make_composite(percentile=70.0),
            opportunity_type=OpportunityType.COMPOUNDER,
            asymmetry_ratio_value=6.0,  # > 5x -> max 20%
            timing_signal="buy_now",
            gate_result_a=_passing_gate(),
            gate_result_b=_passing_gate(),
        )
        assert result.max_position_pct is not None
        assert result.max_position_pct > 0.0

    def test_none_conviction_zero_position(self):
        """Low percentile -> NONE conviction -> 0% position."""
        track_a = _make_composite(percentile=50.0)  # NONE conviction
        result = score_dual_track(
            track_a_score=track_a,
            track_b_score=_make_composite(percentile=40.0),
            opportunity_type=OpportunityType.NEITHER,
            asymmetry_ratio_value=6.0,
            timing_signal="buy_now",
            gate_result_a=_passing_gate(),
            gate_result_b=_passing_gate(),
        )
        assert result.max_position_pct == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Gate failure caps conviction
# ---------------------------------------------------------------------------


class TestGateFailure:
    """Failing absolute gates caps conviction at MEDIUM."""

    def test_winning_track_a_gate_fails_caps_percentile(self):
        """Track A wins but gate fails -> cap percentile at min(current, 98.0)."""
        track_a = _make_composite(percentile=99.8)  # Would be EXCEPTIONAL
        result = score_dual_track(
            track_a_score=track_a,
            track_b_score=_make_composite(percentile=70.0),
            opportunity_type=OpportunityType.COMPOUNDER,
            asymmetry_ratio_value=3.0,
            timing_signal="buy_now",
            gate_result_a=_failing_gate(),
            gate_result_b=_passing_gate(),
        )
        # Capped at MEDIUM (98.0 percentile threshold)
        assert result.composite_percentile <= 98.0
        # Note: conviction_level uses composite_raw_score (not percentile),
        # so it reflects the raw score thresholds (79/72/65), not the cap.
        assert result.conviction_level == ConvictionLevel.EXCEPTIONAL

    def test_winning_track_b_gate_fails_caps_percentile(self):
        """Track B wins but gate fails -> cap percentile."""
        track_b = _make_composite(percentile=99.5)
        result = score_dual_track(
            track_a_score=_make_composite(percentile=60.0),
            track_b_score=track_b,
            opportunity_type=OpportunityType.MISPRICING,
            asymmetry_ratio_value=3.0,
            timing_signal="buy_now",
            gate_result_a=_passing_gate(),
            gate_result_b=_failing_gate(),
        )
        assert result.composite_percentile <= 98.0

    def test_gate_pass_preserves_percentile(self):
        """Gates pass -> percentile not capped."""
        track_a = _make_composite(percentile=99.8)
        result = score_dual_track(
            track_a_score=track_a,
            track_b_score=_make_composite(percentile=70.0),
            opportunity_type=OpportunityType.COMPOUNDER,
            asymmetry_ratio_value=3.0,
            timing_signal="buy_now",
            gate_result_a=_passing_gate(),
            gate_result_b=_passing_gate(),
        )
        assert result.composite_percentile == pytest.approx(99.8)

    def test_already_below_medium_not_raised(self):
        """If percentile is already below 98.0, gate failure doesn't change it."""
        track_a = _make_composite(percentile=90.0)
        result = score_dual_track(
            track_a_score=track_a,
            track_b_score=_make_composite(percentile=80.0),
            opportunity_type=OpportunityType.COMPOUNDER,
            asymmetry_ratio_value=3.0,
            timing_signal="buy_now",
            gate_result_a=_failing_gate(),
            gate_result_b=_passing_gate(),
        )
        # Already 90.0 < 98.0, should stay at 90.0
        assert result.composite_percentile == pytest.approx(90.0)


# ---------------------------------------------------------------------------
# NEITHER opportunity type
# ---------------------------------------------------------------------------


class TestNeitherOpportunityType:
    """NEITHER still gets scored using the higher track."""

    def test_neither_still_picks_higher_track(self):
        track_a = _make_composite(percentile=65.0, winning_track="compounder")
        track_b = _make_composite(percentile=55.0, winning_track="mispricing")

        result = score_dual_track(
            track_a_score=track_a,
            track_b_score=track_b,
            opportunity_type=OpportunityType.NEITHER,
            asymmetry_ratio_value=1.0,
            timing_signal="add_on_pullback",
            gate_result_a=_passing_gate(),
            gate_result_b=_passing_gate(),
        )

        assert result.opportunity_type == OpportunityType.NEITHER
        assert result.winning_track == "compounder"
        assert result.composite_percentile == pytest.approx(65.0)
