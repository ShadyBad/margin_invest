"""Tests for PEG Ratio (Price/Earnings-to-Growth) factor."""

import pytest
from margin_engine.scoring.quantitative.peg_ratio import peg_ratio


class TestPegRatio:
    def test_normal_peg(self):
        """PE 20, growth 20% -> PEG = 20 / 20 = 1.0."""
        result = peg_ratio(pe_ratio=20.0, earnings_growth_rate=0.20)
        assert result.raw_value == pytest.approx(1.0, rel=1e-6)
        assert result.name == "peg_ratio"
        assert result.percentile_rank == 0.0

    def test_cheap_growth(self):
        """PE 15, growth 30% -> PEG = 15 / 30 = 0.5."""
        result = peg_ratio(pe_ratio=15.0, earnings_growth_rate=0.30)
        assert result.raw_value == pytest.approx(0.5, rel=1e-6)

    def test_expensive(self):
        """PE 60, growth 15% -> PEG = 60 / 15 = 4.0."""
        result = peg_ratio(pe_ratio=60.0, earnings_growth_rate=0.15)
        assert result.raw_value == pytest.approx(4.0, rel=1e-6)

    def test_negative_growth(self):
        """Negative earnings growth -> 0.0 sentinel."""
        result = peg_ratio(pe_ratio=20.0, earnings_growth_rate=-0.10)
        assert result.raw_value == 0.0
        assert "negative" in result.detail.lower() or "zero" in result.detail.lower()

    def test_zero_growth(self):
        """Zero earnings growth -> 0.0 sentinel."""
        result = peg_ratio(pe_ratio=20.0, earnings_growth_rate=0.0)
        assert result.raw_value == 0.0

    def test_negative_pe(self):
        """Negative PE -> 0.0 sentinel."""
        result = peg_ratio(pe_ratio=-5.0, earnings_growth_rate=0.20)
        assert result.raw_value == 0.0
        assert "negative" in result.detail.lower() or "zero" in result.detail.lower()
