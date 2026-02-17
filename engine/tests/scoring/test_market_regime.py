"""Tests for market regime modifier -- CAPE-based threshold adjustment."""

import pytest
from margin_engine.scoring.market_regime import (
    MarketRegime,
    detect_regime,
    regime_adjustments,
)


class TestDetectRegime:
    def test_cheap(self):
        assert detect_regime(12.0) == MarketRegime.CHEAP

    def test_normal(self):
        assert detect_regime(20.0) == MarketRegime.NORMAL

    def test_expensive(self):
        assert detect_regime(30.0) == MarketRegime.EXPENSIVE

    def test_euphoria(self):
        assert detect_regime(40.0) == MarketRegime.EUPHORIA

    def test_boundary_15_is_normal(self):
        assert detect_regime(15.0) == MarketRegime.NORMAL

    def test_boundary_25_is_normal(self):
        assert detect_regime(25.0) == MarketRegime.NORMAL

    def test_boundary_25_01_is_expensive(self):
        assert detect_regime(25.01) == MarketRegime.EXPENSIVE

    def test_boundary_35_01_is_euphoria(self):
        assert detect_regime(35.01) == MarketRegime.EUPHORIA


class TestRegimeAdjustments:
    def test_cheap_relaxes_growth_gap(self):
        adj = regime_adjustments(MarketRegime.CHEAP)
        assert adj.track_a_growth_gap_adjustment == pytest.approx(-0.02)
        assert adj.track_b_asymmetry_adjustment == pytest.approx(-1.0)

    def test_normal_no_adjustment(self):
        adj = regime_adjustments(MarketRegime.NORMAL)
        assert adj.track_a_growth_gap_adjustment == 0.0
        assert adj.track_b_asymmetry_adjustment == 0.0
        assert adj.track_b_catalyst_percentile_override is None

    def test_expensive_tightens_growth_gap(self):
        adj = regime_adjustments(MarketRegime.EXPENSIVE)
        assert adj.track_a_growth_gap_adjustment == pytest.approx(0.02)

    def test_euphoria_tightens_both(self):
        adj = regime_adjustments(MarketRegime.EUPHORIA)
        assert adj.track_a_growth_gap_adjustment == pytest.approx(0.05)
        assert adj.track_b_catalyst_percentile_override == pytest.approx(90.0)
