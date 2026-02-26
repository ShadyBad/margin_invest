"""Tests for historical regime classifier."""

from datetime import date

from margin_engine.backtesting.regime_classifier import (
    MarketRegimeHistorical,
    classify_regime,
    get_nber_recessions,
    segment_by_regime,
)


class TestClassifyRegime:
    def test_bull_when_above_trough(self):
        regime = classify_regime(drawdown_from_peak=0.05, vix=15.0, in_nber_recession=False)
        assert regime == MarketRegimeHistorical.BULL

    def test_bear_when_deep_drawdown(self):
        regime = classify_regime(drawdown_from_peak=0.25, vix=25.0, in_nber_recession=False)
        assert regime == MarketRegimeHistorical.BEAR

    def test_crisis_when_vix_high_and_drawdown(self):
        regime = classify_regime(drawdown_from_peak=0.30, vix=45.0, in_nber_recession=True)
        assert regime == MarketRegimeHistorical.CRISIS

    def test_sideways_moderate_drawdown(self):
        regime = classify_regime(drawdown_from_peak=0.12, vix=18.0, in_nber_recession=False)
        assert regime == MarketRegimeHistorical.SIDEWAYS

    def test_crisis_takes_priority_over_bear(self):
        regime = classify_regime(drawdown_from_peak=0.35, vix=50.0, in_nber_recession=True)
        assert regime == MarketRegimeHistorical.CRISIS


class TestSegmentByRegime:
    def test_segments_returns_by_regime(self):
        dates = [
            date(2008, 1, 1),
            date(2008, 6, 1),
            date(2009, 3, 1),
            date(2010, 1, 1),
        ]
        regimes = [
            MarketRegimeHistorical.BULL,
            MarketRegimeHistorical.CRISIS,
            MarketRegimeHistorical.CRISIS,
            MarketRegimeHistorical.BULL,
        ]
        portfolio_returns = [0.02, -0.15, -0.08, 0.05]
        benchmark_returns = [0.01, -0.10, -0.05, 0.03]

        segments = segment_by_regime(dates, regimes, portfolio_returns, benchmark_returns)
        assert MarketRegimeHistorical.CRISIS in segments
        assert MarketRegimeHistorical.BULL in segments
        crisis = segments[MarketRegimeHistorical.CRISIS]
        assert crisis.num_months == 2
        assert len(crisis.portfolio_returns) == 2

    def test_empty_input_returns_empty(self):
        segments = segment_by_regime([], [], [], [])
        assert len(segments) == 0


class TestNBERRecessions:
    def test_gfc_is_recession(self):
        recessions = get_nber_recessions()
        # Dec 2007 - Jun 2009
        gfc = [r for r in recessions if r[0].year == 2007]
        assert len(gfc) == 1
        assert gfc[0][0] == date(2007, 12, 1)
        assert gfc[0][1] == date(2009, 6, 30)

    def test_date_in_recession(self):
        recessions = get_nber_recessions()
        # March 2009 should be in GFC recession
        in_recession = any(start <= date(2009, 3, 1) <= end for start, end in recessions)
        assert in_recession
