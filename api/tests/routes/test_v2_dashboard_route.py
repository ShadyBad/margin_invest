"""Tests for v2 fields in dashboard route responses."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from margin_api.routes.dashboard import _pick_summary_from_row


class TestV2DashboardRoute:
    def test_pick_summary_includes_v2_fields(self):
        """PickSummary should include v2 conviction engine fields."""
        score = MagicMock()
        score.composite_percentile = 95.0
        score.composite_raw_score = 82.0
        score.conviction_level = "exceptional"
        score.signal = "buy"
        score.quality_percentile = 88.0
        score.value_percentile = 75.0
        score.momentum_percentile = 92.0
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)
        score.intrinsic_value = 500.0
        score.buy_price = 400.0
        score.sell_price = 600.0
        score.actual_price = 350.0
        score.price_target_invalid_reason = None
        score.opportunity_type = "compounder"
        score.winning_track = "compounder"
        score.max_position_pct = 10.0
        score.timing_signal = "buy_now"

        row = MagicMock()
        row.Score = score
        row.ticker = "COST"
        row.asset_name = "Costco"
        row.asset_sector = "Consumer Staples"

        pick = _pick_summary_from_row(row)

        assert pick.opportunity_type == "compounder"
        assert pick.winning_track == "compounder"
        assert pick.max_position_pct == 10.0
        assert pick.timing_signal == "buy_now"
        assert pick.price_upside is not None
        assert pick.margin_of_safety is not None

    def test_pick_summary_v2_fields_none_for_v1(self):
        """V1 scores should have None v2 fields in PickSummary."""
        score = MagicMock()
        score.composite_percentile = 50.0
        score.composite_raw_score = 40.0
        score.conviction_level = "none"
        score.signal = "no_action"
        score.quality_percentile = 50.0
        score.value_percentile = 50.0
        score.momentum_percentile = 50.0
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)
        score.intrinsic_value = None
        score.buy_price = None
        score.sell_price = None
        score.actual_price = None
        score.price_target_invalid_reason = None
        score.opportunity_type = None
        score.winning_track = None
        score.max_position_pct = None
        score.timing_signal = None

        row = MagicMock()
        row.Score = score
        row.ticker = "TEST"
        row.asset_name = "Test Inc"
        row.asset_sector = "Information Technology"

        pick = _pick_summary_from_row(row)

        assert pick.opportunity_type is None
        assert pick.winning_track is None
        assert pick.max_position_pct is None
        assert pick.timing_signal is None
        assert pick.price_upside is None
        assert pick.margin_of_safety is None

    def test_pick_summary_margin_of_safety_only_when_below_intrinsic(self):
        """margin_of_safety should be None when actual_price >= intrinsic_value."""
        score = MagicMock()
        score.composite_percentile = 80.0
        score.composite_raw_score = 70.0
        score.conviction_level = "high"
        score.signal = "buy"
        score.quality_percentile = 75.0
        score.value_percentile = 70.0
        score.momentum_percentile = 85.0
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)
        score.intrinsic_value = 100.0
        score.buy_price = 80.0
        score.sell_price = 120.0
        score.actual_price = 110.0  # above intrinsic
        score.price_target_invalid_reason = None
        score.opportunity_type = "mispricing"
        score.winning_track = "mispricing"
        score.max_position_pct = 5.0
        score.timing_signal = "add_on_pullback"

        row = MagicMock()
        row.Score = score
        row.ticker = "OVER"
        row.asset_name = "Overpriced Inc"
        row.asset_sector = "Information Technology"

        pick = _pick_summary_from_row(row)

        assert pick.margin_of_safety is None
        assert pick.price_upside is not None  # still computed (can be negative)

    def test_pick_summary_no_price_targets_when_invalid(self):
        """When price_target_invalid_reason is set, upside and MoS should be None."""
        score = MagicMock()
        score.composite_percentile = 80.0
        score.composite_raw_score = 70.0
        score.conviction_level = "high"
        score.signal = "buy"
        score.quality_percentile = 75.0
        score.value_percentile = 70.0
        score.momentum_percentile = 85.0
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)
        score.intrinsic_value = 200.0
        score.buy_price = 160.0
        score.sell_price = 240.0
        score.actual_price = 150.0
        score.price_target_invalid_reason = "negative_earnings"
        score.opportunity_type = "compounder"
        score.winning_track = "compounder"
        score.max_position_pct = 8.0
        score.timing_signal = "buy_now"

        row = MagicMock()
        row.Score = score
        row.ticker = "INV"
        row.asset_name = "Invalid Targets Inc"
        row.asset_sector = "Information Technology"

        pick = _pick_summary_from_row(row)

        assert pick.price_upside is None
        assert pick.margin_of_safety is None
        # v2 fields still populated
        assert pick.opportunity_type == "compounder"
