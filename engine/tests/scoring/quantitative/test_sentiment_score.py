"""Tests for the Sentiment Score factor.

The sentiment score factor accepts a pre-computed sentiment value from -5 to +5
(produced by LLM analysis in the qualitative/ingestion layer) and normalizes it
to a 0-10 scale with an optional contrarian bonus.
"""

from __future__ import annotations

import pytest
from margin_engine.models.scoring import FactorScore
from margin_engine.scoring.quantitative.sentiment_score import sentiment_score


class TestSentimentScoreBasic:
    """Core normalization tests: score + 5.0 maps [-5, +5] to [0, 10]."""

    def test_positive_sentiment(self):
        """score=3.0 -> raw_value=8.0."""
        result = sentiment_score(3.0)
        assert result.raw_value == pytest.approx(8.0)

    def test_negative_sentiment(self):
        """score=-2.0 -> raw_value=3.0."""
        result = sentiment_score(-2.0)
        assert result.raw_value == pytest.approx(3.0)

    def test_neutral_sentiment(self):
        """score=0.0 -> raw_value=5.0."""
        result = sentiment_score(0.0)
        assert result.raw_value == pytest.approx(5.0)

    def test_extreme_positive(self):
        """score=5.0 -> raw_value=10.0."""
        result = sentiment_score(5.0)
        assert result.raw_value == pytest.approx(10.0)

    def test_extreme_negative(self):
        """score=-5.0 -> raw_value=0.0."""
        result = sentiment_score(-5.0)
        assert result.raw_value == pytest.approx(0.0)


class TestSentimentScoreClamping:
    """Scores outside [-5, +5] are clamped before normalization."""

    def test_clamping_above_5(self):
        """score=7.0 clamped to 5.0 -> raw_value=10.0."""
        result = sentiment_score(7.0)
        assert result.raw_value == pytest.approx(10.0)

    def test_clamping_below_negative_5(self):
        """score=-8.0 clamped to -5.0 -> raw_value=0.0."""
        result = sentiment_score(-8.0)
        assert result.raw_value == pytest.approx(0.0)

    def test_clamping_large_positive(self):
        """score=100.0 clamped to 5.0 -> raw_value=10.0."""
        result = sentiment_score(100.0)
        assert result.raw_value == pytest.approx(10.0)

    def test_clamping_large_negative(self):
        """score=-100.0 clamped to -5.0 -> raw_value=0.0."""
        result = sentiment_score(-100.0)
        assert result.raw_value == pytest.approx(0.0)


class TestSentimentScoreContrarian:
    """Contrarian bonus: +2.0 when has_contrarian_signal=True AND score < 0."""

    def test_contrarian_bonus_with_negative_sentiment(self):
        """score=-2.0, contrarian=True -> normalized=3.0 + bonus=2.0 = 5.0."""
        result = sentiment_score(-2.0, has_contrarian_signal=True)
        assert result.raw_value == pytest.approx(5.0)

    def test_contrarian_bonus_with_strongly_negative(self):
        """score=-4.0, contrarian=True -> normalized=1.0 + bonus=2.0 = 3.0."""
        result = sentiment_score(-4.0, has_contrarian_signal=True)
        assert result.raw_value == pytest.approx(3.0)

    def test_contrarian_not_applied_when_positive(self):
        """score=2.0, contrarian=True -> no bonus, raw_value=7.0."""
        result = sentiment_score(2.0, has_contrarian_signal=True)
        assert result.raw_value == pytest.approx(7.0)

    def test_contrarian_not_applied_when_zero(self):
        """score=0.0, contrarian=True -> no bonus (score is not < 0), raw_value=5.0."""
        result = sentiment_score(0.0, has_contrarian_signal=True)
        assert result.raw_value == pytest.approx(5.0)

    def test_contrarian_bonus_capped_at_10(self):
        """score=-0.5, contrarian=True -> normalized=4.5 + bonus=2.0 = 6.5 (under cap)."""
        result = sentiment_score(-0.5, has_contrarian_signal=True)
        assert result.raw_value == pytest.approx(6.5)

    def test_contrarian_bonus_cap_scenario(self):
        """Edge case: contrarian with mildly negative score near cap.

        score=-0.1, contrarian=True -> normalized=4.9 + bonus=2.0 = 6.9 (under cap).
        The cap at 10 only matters if normalized + 2.0 > 10, which requires
        normalized > 8.0 — impossible since score < 0 means normalized < 5.0.
        But we verify the cap logic anyway by testing with a clamped value.
        """
        result = sentiment_score(-0.1, has_contrarian_signal=True)
        assert result.raw_value == pytest.approx(6.9)
        assert result.raw_value <= 10.0

    def test_contrarian_not_applied_when_flag_is_false(self):
        """score=-3.0, contrarian=False -> no bonus, raw_value=2.0."""
        result = sentiment_score(-3.0, has_contrarian_signal=False)
        assert result.raw_value == pytest.approx(2.0)


class TestSentimentScoreFactorScoreFields:
    """Validate FactorScore metadata fields."""

    def test_returns_factor_score_type(self):
        """Should return a FactorScore instance."""
        result = sentiment_score(0.0)
        assert isinstance(result, FactorScore)

    def test_name_is_sentiment(self):
        """Factor name should be 'sentiment'."""
        result = sentiment_score(0.0)
        assert result.name == "sentiment"

    def test_percentile_rank_is_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6 composite scorer)."""
        result = sentiment_score(3.0)
        assert result.percentile_rank == 0.0

    def test_detail_contains_original_score(self):
        """Detail string should show the original score."""
        result = sentiment_score(2.5)
        assert "2.5" in result.detail

    def test_detail_contains_normalized_value(self):
        """Detail string should show the normalized value."""
        result = sentiment_score(2.5)
        assert "7.5" in result.detail

    def test_detail_contains_contrarian_info(self):
        """Detail string should mention contrarian bonus when applied."""
        result = sentiment_score(-2.0, has_contrarian_signal=True)
        assert "contrarian" in result.detail.lower()

    def test_detail_no_contrarian_when_not_applied(self):
        """Detail string should not mention contrarian when flag is False."""
        result = sentiment_score(-2.0, has_contrarian_signal=False)
        assert "contrarian" not in result.detail.lower()
