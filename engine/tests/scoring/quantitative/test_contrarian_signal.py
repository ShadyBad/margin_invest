"""Tests for Contrarian Signal — negative momentum + strong quality."""

import pytest
from margin_engine.scoring.quantitative.contrarian_signal import contrarian_signal


class TestContrarianSignal:
    def test_negative_momentum_high_quality(self):
        """Negative momentum + high quality = strong contrarian signal."""
        # momentum_percentile = 15 (bad), quality_percentile = 90 (great)
        # signal = (100 - 15) * 90 / 100 = 85 * 0.9 = 76.5
        result = contrarian_signal(momentum_percentile=15.0, quality_percentile=90.0)
        assert result.name == "contrarian_signal"
        assert result.raw_value == pytest.approx(76.5)

    def test_positive_momentum_returns_zero(self):
        """Positive momentum (> 50th percentile) = no contrarian signal."""
        result = contrarian_signal(momentum_percentile=70.0, quality_percentile=90.0)
        assert result.raw_value == 0.0

    def test_low_quality_returns_low_signal(self):
        """Negative momentum but low quality = not contrarian, just bad."""
        result = contrarian_signal(momentum_percentile=10.0, quality_percentile=20.0)
        # (100 - 10) * 20 / 100 = 90 * 0.2 = 18.0
        assert result.raw_value == pytest.approx(18.0)
