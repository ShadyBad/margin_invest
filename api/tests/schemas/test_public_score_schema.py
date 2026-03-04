"""Tests for PublicScoreResponse schema."""

from margin_api.schemas.scores import PublicScoreFactorSummary, PublicScoreResponse


class TestPublicScoreResponse:
    def test_valid_scored_ticker(self):
        data = PublicScoreResponse(
            ticker="AAPL",
            company_name="Apple Inc",
            composite_score=78.5,
            composite_tier="high",
            signal="strong",
            factor_summary=PublicScoreFactorSummary(
                quality_percentile=72.0,
                value_percentile=81.0,
                momentum_percentile=65.0,
            ),
            eliminated=False,
            elimination_reason=None,
            scored_at="2026-02-27T12:00:00+00:00",
        )
        assert data.ticker == "AAPL"
        assert data.composite_score == 78.5
        assert data.factor_summary.quality_percentile == 72.0
        assert data.eliminated is False

    def test_eliminated_ticker(self):
        data = PublicScoreResponse(
            ticker="XYZ",
            company_name="XYZ Corp",
            composite_score=22.0,
            composite_tier="none",
            signal="failed",
            factor_summary=PublicScoreFactorSummary(
                quality_percentile=15.0,
                value_percentile=30.0,
                momentum_percentile=10.0,
            ),
            eliminated=True,
            elimination_reason="negative_earnings",
            scored_at="2026-02-27T12:00:00+00:00",
        )
        assert data.eliminated is True
        assert data.elimination_reason == "negative_earnings"

    def test_schema_does_not_leak_forensic_fields(self):
        """PublicScoreResponse must NOT have fields from ScoreResponse."""
        fields = set(PublicScoreResponse.model_fields.keys())
        forbidden = {
            "ml_alpha",
            "ml_confidence",
            "price_history",
            "signal_history",
            "sub_scores",
            "buy_price",
            "sell_price",
            "margin_invest_value",
            "track_a",
            "track_b",
            "track_c",
        }
        assert fields & forbidden == set()
