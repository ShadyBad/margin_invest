"""Tests for v2 Score model columns."""

from datetime import UTC, datetime

from margin_api.db.models import Score


class TestV2ScoreColumns:
    def test_score_model_has_v2_columns(self):
        """Score model should have v2 columns as attributes."""
        s = Score(
            asset_id=1,
            composite_percentile=99.5,
            composite_raw_score=85.0,
            conviction_level="high",
            signal="buy",
            scored_at=datetime.now(UTC),
            opportunity_type="compounder",
            winning_track="compounder",
            asymmetry_ratio=4.2,
            max_position_pct=10.0,
            timing_signal="buy_now",
        )
        assert s.opportunity_type == "compounder"
        assert s.winning_track == "compounder"
        assert s.asymmetry_ratio == 4.2
        assert s.max_position_pct == 10.0
        assert s.timing_signal == "buy_now"

    def test_v2_columns_are_nullable(self):
        """V2 columns should all default to None for backward compat."""
        s = Score(
            asset_id=1,
            composite_percentile=50.0,
            conviction_level="none",
            signal="no_action",
            scored_at=datetime.now(UTC),
        )
        assert s.opportunity_type is None
        assert s.winning_track is None
        assert s.asymmetry_ratio is None
        assert s.max_position_pct is None
        assert s.timing_signal is None
