"""Tests for sentiment score wiring — validates the sentiment_score() function behavior."""

from __future__ import annotations

import pytest
from margin_engine.scoring.quantitative.sentiment_score import sentiment_score


class TestSentimentScoreWiring:
    def test_sentiment_score_with_real_value(self) -> None:
        """Positive sentiment (3.0) produces a non-stub score with expected properties."""
        result = sentiment_score(score=3.0)
        assert result.stub is False
        assert result.name == "sentiment"
        assert result.raw_value > 0

    def test_sentiment_score_with_contrarian_bonus(self) -> None:
        """Contrarian signal should boost raw_value for negative sentiment."""
        without_contrarian = sentiment_score(score=-2.0, has_contrarian_signal=False)
        with_contrarian = sentiment_score(score=-2.0, has_contrarian_signal=True)
        assert with_contrarian.raw_value > without_contrarian.raw_value

    def test_sentiment_score_neutral(self) -> None:
        """Neutral sentiment (0.0) maps to normalized 5.0."""
        result = sentiment_score(score=0.0)
        assert result.raw_value == pytest.approx(5.0)


class TestContrarianSignal:
    def test_contrarian_bonus_applied_when_negative_sentiment(self):
        """Negative sentiment + contrarian signal gives higher raw_value."""
        from margin_engine.scoring.quantitative.sentiment_score import sentiment_score
        base = sentiment_score(score=-3.0, has_contrarian_signal=False)
        boosted = sentiment_score(score=-3.0, has_contrarian_signal=True)
        assert boosted.raw_value > base.raw_value

    def test_no_meaningful_contrarian_on_positive_sentiment(self):
        """Positive sentiment: contrarian bonus only applies to negative values."""
        from margin_engine.scoring.quantitative.sentiment_score import sentiment_score
        base = sentiment_score(score=3.0, has_contrarian_signal=False)
        with_flag = sentiment_score(score=3.0, has_contrarian_signal=True)
        # Contrarian bonus only triggers on negative sentiment
        assert base.raw_value == with_flag.raw_value
