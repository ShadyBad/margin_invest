"""Tests for v2 fields in score route responses."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from margin_api.routes.scores import _score_response_from_row


class TestV2ScoreRoute:
    def test_fallback_path_includes_v2_fields(self):
        """When score_detail is None, v2 fields come from DB columns."""
        score = MagicMock()
        score.score_detail = None
        score.composite_percentile = 99.5
        score.composite_raw_score = 85.0
        score.conviction_level = "high"
        score.signal = "buy"
        score.quality_percentile = 80.0
        score.value_percentile = 70.0
        score.momentum_percentile = 90.0
        score.data_coverage = 1.0
        score.growth_stage = "steady_growth"
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)
        score.margin_invest_value = 500.0
        score.buy_price = 400.0
        score.sell_price = 600.0
        score.actual_price = 350.0
        score.price_target_invalid_reason = None
        score.opportunity_type = "compounder"
        score.winning_track = "compounder"
        score.asymmetry_ratio = 4.2
        score.max_position_pct = 10.0
        score.timing_signal = "buy_now"

        row = MagicMock()
        row.__getitem__ = lambda self, idx: score if idx == 0 else None
        row.Score = score
        row.ticker = "COST"
        row.asset_name = "Costco"

        resp = _score_response_from_row(row)

        assert resp.opportunity_type == "compounder"
        assert resp.winning_track == "compounder"
        assert resp.asymmetry_ratio == 4.2
        assert resp.max_position_pct == 10.0
        assert resp.timing_signal == "buy_now"

    def test_jsonb_path_includes_v2_fields(self):
        """When score_detail has v2 fields, they pass through to response."""
        score = MagicMock()
        score.score_detail = {
            "ticker": "COST",
            "composite_percentile": 99.5,
            "composite_raw_score": 85.0,
            "quality": {
                "factor_name": "quality",
                "weight": 0.5,
                "sub_scores": [],
                "average_percentile": 80.0,
            },
            "value": {
                "factor_name": "value",
                "weight": 0.3,
                "sub_scores": [],
                "average_percentile": 70.0,
            },
            "momentum": {
                "factor_name": "momentum",
                "weight": 0.2,
                "sub_scores": [],
                "average_percentile": 90.0,
            },
            "filters_passed": [],
            "data_coverage": 1.0,
            "opportunity_type": "compounder",
            "winning_track": "compounder",
            "asymmetry_ratio": 4.2,
            "max_position_pct": 10.0,
            "timing_signal": "buy_now",
            "capital_allocation": {
                "factor_name": "capital_allocation",
                "weight": 0.2,
                "sub_scores": [
                    {
                        "name": "buyback",
                        "raw_value": 0.8,
                        "percentile_rank": 72.0,
                        "detail": "",
                    },
                ],
            },
        }
        score.conviction_level = "high"
        score.signal = "buy"
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)
        score.margin_invest_value = 500.0
        score.buy_price = 400.0
        score.sell_price = 600.0
        score.actual_price = 350.0
        score.price_target_invalid_reason = None
        score.composite_raw_score = 85.0
        score.composite_percentile = 99.5
        score.opportunity_type = "compounder"
        score.winning_track = "compounder"
        score.asymmetry_ratio = 4.2
        score.max_position_pct = 10.0
        score.timing_signal = "buy_now"

        row = MagicMock()
        row.__getitem__ = lambda self, idx: score if idx == 0 else None
        row.Score = score
        row.ticker = "COST"
        row.asset_name = "Costco"

        resp = _score_response_from_row(row)

        assert resp.opportunity_type == "compounder"
        assert resp.winning_track == "compounder"
        assert resp.asymmetry_ratio == 4.2
        assert resp.capital_allocation is not None
        assert resp.capital_allocation.average_percentile == 72.0

    def test_v2_fields_none_for_v1_scores(self):
        """V1 scores (no v2 columns) should have None v2 fields."""
        score = MagicMock()
        score.score_detail = None
        score.composite_percentile = 50.0
        score.composite_raw_score = 40.0
        score.conviction_level = "none"
        score.signal = "no_action"
        score.quality_percentile = 50.0
        score.value_percentile = 50.0
        score.momentum_percentile = 50.0
        score.data_coverage = 1.0
        score.growth_stage = None
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)
        score.margin_invest_value = None
        score.buy_price = None
        score.sell_price = None
        score.actual_price = None
        score.price_target_invalid_reason = None
        score.opportunity_type = None
        score.winning_track = None
        score.asymmetry_ratio = None
        score.max_position_pct = None
        score.timing_signal = None

        row = MagicMock()
        row.__getitem__ = lambda self, idx: score if idx == 0 else None
        row.Score = score
        row.ticker = "TEST"
        row.asset_name = "Test Inc"

        resp = _score_response_from_row(row)
        assert resp.opportunity_type is None
        assert resp.winning_track is None
        assert resp.asymmetry_ratio is None

    def test_jsonb_path_setdefaults_v2_from_db_columns(self):
        """When score_detail lacks v2 fields, they come from DB columns via setdefault."""
        score = MagicMock()
        score.score_detail = {
            "ticker": "AAPL",
            "composite_percentile": 80.0,
            "composite_raw_score": 70.0,
            "quality": {
                "factor_name": "quality",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 75.0,
            },
            "value": {
                "factor_name": "value",
                "weight": 0.30,
                "sub_scores": [],
                "average_percentile": 65.0,
            },
            "momentum": {
                "factor_name": "momentum",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 85.0,
            },
            "filters_passed": [],
            "data_coverage": 1.0,
            # v2 fields NOT in JSONB
        }
        score.conviction_level = "high"
        score.signal = "buy"
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)
        score.margin_invest_value = None
        score.buy_price = None
        score.sell_price = None
        score.actual_price = None
        score.price_target_invalid_reason = None
        score.composite_raw_score = 70.0
        score.composite_percentile = 80.0
        # v2 DB columns
        score.opportunity_type = "mispricing"
        score.winning_track = "mispricing"
        score.asymmetry_ratio = 3.5
        score.max_position_pct = 8.0
        score.timing_signal = "add_on_pullback"

        row = MagicMock()
        row.__getitem__ = lambda self, idx: score if idx == 0 else None
        row.Score = score
        row.ticker = "AAPL"
        row.asset_name = "Apple Inc"

        resp = _score_response_from_row(row)

        assert resp.opportunity_type == "mispricing"
        assert resp.winning_track == "mispricing"
        assert resp.asymmetry_ratio == 3.5
        assert resp.max_position_pct == 8.0
        assert resp.timing_signal == "add_on_pullback"

    def test_jsonb_path_catalyst_average_percentile(self):
        """catalyst factor breakdown should get average_percentile computed."""
        score = MagicMock()
        score.score_detail = {
            "ticker": "MSFT",
            "composite_percentile": 90.0,
            "composite_raw_score": 78.0,
            "quality": {
                "factor_name": "quality",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 80.0,
            },
            "value": {
                "factor_name": "value",
                "weight": 0.30,
                "sub_scores": [],
                "average_percentile": 70.0,
            },
            "momentum": {
                "factor_name": "momentum",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 85.0,
            },
            "filters_passed": [],
            "data_coverage": 1.0,
            "catalyst": {
                "factor_name": "catalyst",
                "weight": 0.1,
                "sub_scores": [
                    {
                        "name": "earnings_surprise",
                        "raw_value": 0.5,
                        "percentile_rank": 60.0,
                        "detail": "",
                    },
                    {
                        "name": "guidance",
                        "raw_value": 0.7,
                        "percentile_rank": 80.0,
                        "detail": "",
                    },
                ],
            },
        }
        score.conviction_level = "high"
        score.signal = "buy"
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)
        score.margin_invest_value = None
        score.buy_price = None
        score.sell_price = None
        score.actual_price = None
        score.price_target_invalid_reason = None
        score.composite_raw_score = 78.0
        score.composite_percentile = 90.0
        score.opportunity_type = None
        score.winning_track = None
        score.asymmetry_ratio = None
        score.max_position_pct = None
        score.timing_signal = None

        row = MagicMock()
        row.__getitem__ = lambda self, idx: score if idx == 0 else None
        row.Score = score
        row.ticker = "MSFT"
        row.asset_name = "Microsoft"

        resp = _score_response_from_row(row)

        assert resp.catalyst is not None
        assert resp.catalyst.average_percentile == 70.0  # (60 + 80) / 2
