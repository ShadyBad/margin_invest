"""Tests for V4 authority fields added to score schemas."""

from __future__ import annotations

from datetime import datetime

from margin_api.schemas.score_history import ScoreHistoryPoint
from margin_api.schemas.scores import PublicScoreFactorSummary, PublicScoreResponse, ScoreResponse


class TestScoreResponseV4Fields:
    """ScoreResponse should accept scoring_version, conviction_source, screening_score."""

    def test_defaults(self):
        """New V4 fields should have sensible defaults."""
        resp = ScoreResponse(
            ticker="AAPL",
            composite_percentile=85.0,
            composite_tier="high",
            signal="strong",
            quality={
                "factor_name": "quality",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 80.0,
            },
            value={
                "factor_name": "value",
                "weight": 0.30,
                "sub_scores": [],
                "average_percentile": 70.0,
            },
            momentum={
                "factor_name": "momentum",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 75.0,
            },
            filters_passed=[],
            data_coverage=0.95,
        )
        assert resp.scoring_version == "v4"
        assert resp.conviction_source == "v4_gate_cascade"
        assert resp.screening_score == 0.0

    def test_custom_values(self):
        """New V4 fields should accept custom values."""
        resp = ScoreResponse(
            ticker="MSFT",
            composite_percentile=90.0,
            composite_tier="exceptional",
            signal="strong",
            scoring_version="v4.1",
            conviction_source="ml_override",
            screening_score=87.5,
            quality={
                "factor_name": "quality",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 90.0,
            },
            value={
                "factor_name": "value",
                "weight": 0.30,
                "sub_scores": [],
                "average_percentile": 85.0,
            },
            momentum={
                "factor_name": "momentum",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 88.0,
            },
            filters_passed=[],
            data_coverage=0.98,
        )
        assert resp.scoring_version == "v4.1"
        assert resp.conviction_source == "ml_override"
        assert resp.screening_score == 87.5

    def test_serialization_includes_v4_fields(self):
        """V4 fields should appear in model_dump() output."""
        resp = ScoreResponse(
            ticker="GOOG",
            composite_percentile=75.0,
            composite_tier="medium",
            signal="emerging",
            quality={
                "factor_name": "quality",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 70.0,
            },
            value={
                "factor_name": "value",
                "weight": 0.30,
                "sub_scores": [],
                "average_percentile": 65.0,
            },
            momentum={
                "factor_name": "momentum",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 72.0,
            },
            filters_passed=[],
            data_coverage=0.90,
        )
        data = resp.model_dump()
        assert "scoring_version" in data
        assert "conviction_source" in data
        assert "screening_score" in data


class TestPublicScoreResponseOpportunityType:
    """PublicScoreResponse should accept opportunity_type (nullable)."""

    def test_default_none(self):
        resp = PublicScoreResponse(
            ticker="AAPL",
            company_name="Apple Inc.",
            composite_score=85.0,
            composite_tier="high",
            signal="strong",
            factor_summary=PublicScoreFactorSummary(
                quality_percentile=80.0,
                value_percentile=70.0,
                momentum_percentile=75.0,
            ),
            eliminated=False,
            scored_at="2026-03-01T00:00:00Z",
        )
        assert resp.opportunity_type is None

    def test_with_value(self):
        resp = PublicScoreResponse(
            ticker="MSFT",
            company_name="Microsoft Corp.",
            composite_score=90.0,
            composite_tier="exceptional",
            signal="strong",
            factor_summary=PublicScoreFactorSummary(
                quality_percentile=90.0,
                value_percentile=85.0,
                momentum_percentile=88.0,
            ),
            eliminated=False,
            opportunity_type="deep_value",
            scored_at="2026-03-01T00:00:00Z",
        )
        assert resp.opportunity_type == "deep_value"

    def test_serialization_includes_opportunity_type(self):
        resp = PublicScoreResponse(
            ticker="GOOG",
            company_name="Alphabet Inc.",
            composite_score=75.0,
            composite_tier="medium",
            signal="emerging",
            factor_summary=PublicScoreFactorSummary(
                quality_percentile=70.0,
                value_percentile=65.0,
                momentum_percentile=72.0,
            ),
            eliminated=False,
            opportunity_type="momentum_breakout",
            scored_at="2026-03-01T00:00:00Z",
        )
        data = resp.model_dump()
        assert "opportunity_type" in data
        assert data["opportunity_type"] == "momentum_breakout"


class TestScoreHistoryPointScoringVersion:
    """ScoreHistoryPoint should accept scoring_version (nullable)."""

    def test_default_none(self):
        point = ScoreHistoryPoint(
            scored_at=datetime(2026, 3, 1),
            score=85.0,
            composite_percentile=85.0,
            composite_tier="high",
            signal="strong",
        )
        assert point.scoring_version is None

    def test_with_value(self):
        point = ScoreHistoryPoint(
            scored_at=datetime(2026, 3, 1),
            score=85.0,
            composite_percentile=85.0,
            composite_tier="high",
            signal="strong",
            scoring_version="v4",
        )
        assert point.scoring_version == "v4"

    def test_serialization_includes_scoring_version(self):
        point = ScoreHistoryPoint(
            scored_at=datetime(2026, 3, 1),
            score=85.0,
            composite_percentile=85.0,
            composite_tier="high",
            signal="strong",
            scoring_version="v4",
        )
        data = point.model_dump()
        assert "scoring_version" in data
        assert data["scoring_version"] == "v4"
