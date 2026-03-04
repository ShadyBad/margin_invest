"""Tests for V4 authority fields in _v4_score_response_from_row."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from margin_api.routes.scores import _v4_score_response_from_row


def _make_v4_row(
    detail: dict | None = None,
    composite_score: float = 80.0,
    conviction: str = "high",
    opportunity_type: str | None = "deep_value",
    timing_signal: str | None = "neutral",
    max_position_pct: float | None = 5.0,
    ml_alpha: float | None = None,
    ml_confidence: float | None = None,
    ml_override: str | None = None,
    rules_conviction: str | None = None,
    style: str | None = None,
    regime: str | None = None,
    track_a: dict | None = None,
    track_b: dict | None = None,
    track_c: dict | None = None,
) -> MagicMock:
    """Create a mock DB row that looks like (V4Score, ticker, asset_name, asset_sector)."""
    v4 = MagicMock()
    v4.scored_at = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    v4.composite_score = composite_score
    v4.conviction = conviction
    v4.opportunity_type = opportunity_type
    v4.timing_signal = timing_signal
    v4.max_position_pct = max_position_pct
    v4.ml_alpha = ml_alpha
    v4.ml_confidence = ml_confidence
    v4.ml_override = ml_override
    v4.rules_conviction = rules_conviction
    v4.style = style
    v4.regime = regime
    v4.track_a = track_a
    v4.track_b = track_b
    v4.track_c = track_c
    v4.detail = detail if detail is not None else _minimal_detail()

    row = MagicMock()
    row.__getitem__ = lambda self, idx: {0: v4, 1: "AAPL", 2: "Apple Inc.", 3: "Technology"}[idx]
    row.ticker = "AAPL"
    row.asset_name = "Apple Inc."
    row.asset_sector = "Technology"

    # Make hasattr work correctly for the V4Score mock
    v4.conviction  # already set above
    # hasattr(row[0], "conviction") needs to return True
    return row


def _minimal_detail() -> dict:
    """Build a minimal V4Score detail dict that produces a valid ScoreResponse."""
    return {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [
                {"name": "roe", "raw_value": 0.25, "percentile_rank": 82.0, "detail": ""},
            ],
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [
                {"name": "ev_ebit", "raw_value": 14.0, "percentile_rank": 72.0, "detail": ""},
            ],
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [
                {"name": "price_mom", "raw_value": 0.15, "percentile_rank": 68.0, "detail": ""},
            ],
        },
        "filters_passed": [
            {"name": "market_cap", "passed": True, "detail": "", "verdict": "pass"},
        ],
        "data_coverage": 0.95,
        "signal": "strong",
        "composite_percentile": 85.0,
        "composite_raw_score": 80.0,
    }


class TestV4ResponseBuilderAuthorityFields:
    """_v4_score_response_from_row should populate scoring_version, conviction_source,
    screening_score."""

    def test_scoring_version_is_v4(self):
        row = _make_v4_row()
        resp = _v4_score_response_from_row(row)
        assert resp.scoring_version == "v4"

    def test_conviction_source_is_v4_gate_cascade(self):
        row = _make_v4_row()
        resp = _v4_score_response_from_row(row)
        assert resp.conviction_source == "v4_gate_cascade"

    def test_screening_score_defaults_to_score(self):
        """When detail has no screening_score, it should fall back to the score field."""
        detail = _minimal_detail()
        # score will be set via detail.setdefault("score", ...) which uses composite_raw_score
        row = _make_v4_row(detail=detail)
        resp = _v4_score_response_from_row(row)
        # screening_score should equal the score value
        assert resp.screening_score == resp.score

    def test_screening_score_preserves_explicit_value(self):
        """If detail already has screening_score, setdefault should not overwrite it."""
        detail = _minimal_detail()
        detail["screening_score"] = 92.5
        row = _make_v4_row(detail=detail)
        resp = _v4_score_response_from_row(row)
        assert resp.screening_score == 92.5

    def test_fields_present_in_serialized_output(self):
        row = _make_v4_row()
        resp = _v4_score_response_from_row(row)
        data = resp.model_dump()
        assert "scoring_version" in data
        assert "conviction_source" in data
        assert "screening_score" in data
        assert data["scoring_version"] == "v4"
        assert data["conviction_source"] == "v4_gate_cascade"

    def test_with_ml_model_metadata(self):
        """V4 authority fields should still be present when ml_model is provided."""
        ml_model = MagicMock()
        ml_model.model_qualifies = True
        ml_model.overall_rank_ic = 0.22
        ml_model.created_at = datetime(2026, 2, 28, 2, 0, 0, tzinfo=UTC)

        row = _make_v4_row()
        resp = _v4_score_response_from_row(row, ml_model=ml_model)
        assert resp.scoring_version == "v4"
        assert resp.conviction_source == "v4_gate_cascade"
        assert resp.screening_score > 0

    def test_with_live_price_data(self):
        """V4 authority fields should still be present when live_price_data is provided."""
        live_price = {"price": 185.50, "updated_at": "2026-03-01T12:30:00Z"}
        row = _make_v4_row()
        resp = _v4_score_response_from_row(row, live_price_data=live_price)
        assert resp.scoring_version == "v4"
        assert resp.conviction_source == "v4_gate_cascade"
        assert resp.actual_price == 185.50
