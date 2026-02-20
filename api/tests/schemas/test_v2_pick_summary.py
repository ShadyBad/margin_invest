"""Tests for v2 fields in PickSummary schema."""

from margin_api.schemas.dashboard import PickSummary


class TestV2PickSummary:
    def test_v2_fields_default_to_none(self):
        ps = PickSummary(
            score_id=1,
            ticker="TEST",
            name="Test",
            composite_percentile=50.0,
            conviction_level="none",
            signal="no_action",
            quality_percentile=50.0,
            value_percentile=50.0,
            momentum_percentile=50.0,
        )
        assert ps.opportunity_type is None
        assert ps.winning_track is None
        assert ps.margin_of_safety is None
        assert ps.max_position_pct is None
        assert ps.timing_signal is None

    def test_v2_fields_populated(self):
        ps = PickSummary(
            score_id=1,
            ticker="COST",
            name="Costco",
            composite_percentile=99.5,
            conviction_level="high",
            signal="buy",
            quality_percentile=85.0,
            value_percentile=70.0,
            momentum_percentile=90.0,
            opportunity_type="compounder",
            winning_track="compounder",
            margin_of_safety=0.32,
            max_position_pct=10.0,
            timing_signal="buy_now",
        )
        assert ps.opportunity_type == "compounder"
        assert ps.margin_of_safety == 0.32
        assert ps.max_position_pct == 10.0
