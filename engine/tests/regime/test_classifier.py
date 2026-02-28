"""Tests for multi-dimensional regime classifier.

Covers each classify function independently, compute_confidence,
RegimeClassifierConfig, and the MultiDimensionalRegimeClassifier class.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest
from margin_engine.regime.classifier import (
    MultiDimensionalRegimeClassifier,
    RegimeClassifierConfig,
    classify_credit,
    classify_trend,
    classify_valuation,
    classify_volatility,
    compute_confidence,
)
from margin_engine.regime.models import (
    CreditState,
    RegimeConfidence,
    RegimeState,
    TrendState,
    ValuationState,
    VolatilityState,
)

# ---------------------------------------------------------------------------
# Helper — build synthetic history arrays with known percentiles
# ---------------------------------------------------------------------------


def _uniform_history(low: float, high: float, n: int = 120) -> np.ndarray:
    """Create a uniformly-spaced history array of length *n* from *low* to *high*."""
    return np.linspace(low, high, n)


# ---------------------------------------------------------------------------
# compute_confidence tests
# ---------------------------------------------------------------------------


class TestComputeConfidence:
    """Distance-from-boundary confidence metric."""

    def test_at_lower_boundary_returns_zero(self):
        """Value exactly at lower boundary -> 0.0 confidence."""
        assert compute_confidence(value=10.0, lower_bound=10.0, upper_bound=20.0) == 0.0

    def test_at_upper_boundary_returns_zero(self):
        """Value exactly at upper boundary -> 0.0 confidence."""
        assert compute_confidence(value=20.0, lower_bound=10.0, upper_bound=20.0) == 0.0

    def test_midpoint_returns_one(self):
        """Value at exact midpoint -> 1.0 confidence (farthest from both boundaries)."""
        result = compute_confidence(value=15.0, lower_bound=10.0, upper_bound=20.0)
        assert result == pytest.approx(1.0)

    def test_at_far_boundary_returns_one(self):
        """Value far beyond the range -> clamped to 1.0."""
        result = compute_confidence(value=100.0, lower_bound=10.0, upper_bound=20.0)
        assert result == 1.0

    def test_clamps_above_one(self):
        """Values well beyond the half-range still clamp at 1.0."""
        result = compute_confidence(value=0.0, lower_bound=10.0, upper_bound=20.0)
        assert result == 1.0

    def test_quarter_distance_from_lower(self):
        """Value at 25% of the way from lower to midpoint -> 0.25."""
        # Range is 10..20, midpoint is 15, half-range is 5
        # value = 11.25 -> distance from lower = 1.25, confidence = 1.25 / 5 = 0.25
        result = compute_confidence(value=11.25, lower_bound=10.0, upper_bound=20.0)
        assert result == pytest.approx(0.25)

    def test_quarter_distance_from_upper(self):
        """Value at 25% of the way from upper to midpoint -> 0.25."""
        result = compute_confidence(value=18.75, lower_bound=10.0, upper_bound=20.0)
        assert result == pytest.approx(0.25)

    def test_equal_bounds_returns_one(self):
        """When lower == upper, any value should return 1.0 (degenerate case)."""
        result = compute_confidence(value=5.0, lower_bound=5.0, upper_bound=5.0)
        assert result == 1.0


# ---------------------------------------------------------------------------
# classify_volatility tests
# ---------------------------------------------------------------------------


class TestClassifyVolatility:
    """Expanding-window percentile thresholds: LOW < P10, NORMAL P10-P75,
    ELEVATED P75-P95, CRISIS > P95."""

    def test_low_volatility(self):
        """Current vol below P10 of history -> LOW."""
        # Create history 10..30, P10 = ~12.0
        history = _uniform_history(10.0, 30.0, n=120)
        state, conf = classify_volatility(current=9.0, history=history)
        assert state == VolatilityState.LOW
        assert 0.0 <= conf <= 1.0

    def test_normal_volatility(self):
        """Current vol in P10-P75 range -> NORMAL."""
        history = _uniform_history(10.0, 30.0, n=120)
        # Median ~ 20.0, which is between P10 (~12) and P75 (~25)
        state, conf = classify_volatility(current=20.0, history=history)
        assert state == VolatilityState.NORMAL
        assert 0.0 <= conf <= 1.0

    def test_elevated_volatility(self):
        """Current vol in P75-P95 range -> ELEVATED."""
        history = _uniform_history(10.0, 30.0, n=120)
        # P75 ~ 25, P95 ~ 29.0 -> pick 27.0
        state, conf = classify_volatility(current=27.0, history=history)
        assert state == VolatilityState.ELEVATED
        assert 0.0 <= conf <= 1.0

    def test_crisis_volatility(self):
        """Current vol above P95 of history -> CRISIS."""
        history = _uniform_history(10.0, 30.0, n=120)
        # P95 ~ 29.0
        state, conf = classify_volatility(current=35.0, history=history)
        assert state == VolatilityState.CRISIS
        assert 0.0 <= conf <= 1.0

    def test_confidence_near_boundary_is_low(self):
        """Value right at a percentile boundary should have low confidence."""
        history = _uniform_history(10.0, 30.0, n=120)
        p75 = float(np.percentile(history, 75))
        # Put current exactly at P75 boundary
        state, conf = classify_volatility(current=p75, history=history)
        # Confidence should be low (near 0) since we are at a boundary
        assert conf < 0.15

    def test_confidence_far_from_boundary_is_high(self):
        """Value far from any boundary should have high confidence."""
        history = _uniform_history(10.0, 30.0, n=120)
        # Very deep in LOW regime
        state, conf = classify_volatility(current=1.0, history=history)
        assert state == VolatilityState.LOW
        assert conf > 0.5


# ---------------------------------------------------------------------------
# classify_trend tests
# ---------------------------------------------------------------------------


class TestClassifyTrend:
    """DRAWDOWN overrides if drawdown >= 0.20.
    BULL: return > +0.10, BEAR: return < -0.10, SIDEWAYS: between."""

    def test_bull_trend(self):
        """Trailing return > +10% and no major drawdown -> BULL."""
        state, conf = classify_trend(trailing_12m_return=0.15, drawdown_from_peak=0.05)
        assert state == TrendState.BULL
        assert 0.0 <= conf <= 1.0

    def test_bear_trend(self):
        """Trailing return < -10% -> BEAR."""
        state, conf = classify_trend(trailing_12m_return=-0.20, drawdown_from_peak=0.15)
        assert state == TrendState.BEAR
        assert 0.0 <= conf <= 1.0

    def test_sideways_trend(self):
        """Trailing return between -10% and +10% -> SIDEWAYS."""
        state, conf = classify_trend(trailing_12m_return=0.03, drawdown_from_peak=0.05)
        assert state == TrendState.SIDEWAYS
        assert 0.0 <= conf <= 1.0

    def test_drawdown_overrides_bull(self):
        """Even with positive return, drawdown >= 20% overrides to DRAWDOWN."""
        state, conf = classify_trend(trailing_12m_return=0.15, drawdown_from_peak=0.25)
        assert state == TrendState.DRAWDOWN
        assert 0.0 <= conf <= 1.0

    def test_drawdown_overrides_sideways(self):
        """Drawdown >= 20% with sideways return -> DRAWDOWN."""
        state, conf = classify_trend(trailing_12m_return=0.02, drawdown_from_peak=0.22)
        assert state == TrendState.DRAWDOWN

    def test_drawdown_exact_threshold(self):
        """Drawdown of exactly 0.20 -> DRAWDOWN."""
        state, conf = classify_trend(trailing_12m_return=0.0, drawdown_from_peak=0.20)
        assert state == TrendState.DRAWDOWN

    def test_drawdown_below_threshold_does_not_override(self):
        """Drawdown of 0.19 should NOT override."""
        state, conf = classify_trend(trailing_12m_return=0.15, drawdown_from_peak=0.19)
        assert state == TrendState.BULL

    def test_bull_confidence_increases_with_return(self):
        """Stronger bull return should have higher confidence."""
        _, conf_low = classify_trend(trailing_12m_return=0.11, drawdown_from_peak=0.0)
        _, conf_high = classify_trend(trailing_12m_return=0.30, drawdown_from_peak=0.0)
        assert conf_high > conf_low

    def test_bear_boundary_confidence_is_low(self):
        """Return right at -0.10 boundary should have low confidence."""
        state, conf = classify_trend(trailing_12m_return=-0.10, drawdown_from_peak=0.0)
        # At the boundary, confidence should be near 0
        assert conf < 0.15

    def test_sideways_at_zero_has_high_confidence(self):
        """Zero return with no drawdown is deep in SIDEWAYS territory -> high confidence."""
        state, conf = classify_trend(trailing_12m_return=0.0, drawdown_from_peak=0.0)
        assert state == TrendState.SIDEWAYS
        assert conf > 0.3


# ---------------------------------------------------------------------------
# classify_valuation tests
# ---------------------------------------------------------------------------


class TestClassifyValuation:
    """Fixed thresholds: CHEAP < 15, NORMAL 15-25, EXPENSIVE 25-35, EUPHORIA > 35."""

    def test_cheap(self):
        state, conf = classify_valuation(shiller_cape=10.0)
        assert state == ValuationState.CHEAP
        assert 0.0 <= conf <= 1.0

    def test_normal(self):
        state, conf = classify_valuation(shiller_cape=20.0)
        assert state == ValuationState.NORMAL
        assert 0.0 <= conf <= 1.0

    def test_expensive(self):
        state, conf = classify_valuation(shiller_cape=30.0)
        assert state == ValuationState.EXPENSIVE
        assert 0.0 <= conf <= 1.0

    def test_euphoria(self):
        state, conf = classify_valuation(shiller_cape=40.0)
        assert state == ValuationState.EUPHORIA
        assert 0.0 <= conf <= 1.0

    def test_at_cheap_normal_boundary(self):
        """CAPE of exactly 15 -> NORMAL (boundary belongs to upper bucket)."""
        state, conf = classify_valuation(shiller_cape=15.0)
        assert state == ValuationState.NORMAL
        assert conf < 0.15  # at boundary

    def test_at_normal_expensive_boundary(self):
        """CAPE of exactly 25 -> EXPENSIVE."""
        state, conf = classify_valuation(shiller_cape=25.0)
        assert state == ValuationState.EXPENSIVE
        assert conf < 0.15

    def test_at_expensive_euphoria_boundary(self):
        """CAPE of exactly 35 -> EUPHORIA."""
        state, conf = classify_valuation(shiller_cape=35.0)
        assert state == ValuationState.EUPHORIA
        assert conf < 0.15

    def test_deep_cheap_high_confidence(self):
        """CAPE of 5 is far from boundary -> high confidence."""
        state, conf = classify_valuation(shiller_cape=5.0)
        assert state == ValuationState.CHEAP
        assert conf > 0.5

    def test_deep_euphoria_high_confidence(self):
        """CAPE of 50 is far from boundary -> high confidence."""
        state, conf = classify_valuation(shiller_cape=50.0)
        assert state == ValuationState.EUPHORIA
        assert conf > 0.5


# ---------------------------------------------------------------------------
# classify_credit tests
# ---------------------------------------------------------------------------


class TestClassifyCredit:
    """Percentile thresholds: LOOSE < P25, NORMAL P25-P75, TIGHT P75-P90, STRESS > P90."""

    def test_loose_credit(self):
        """Spread below P25 of history -> LOOSE."""
        history = _uniform_history(100.0, 500.0, n=120)
        state, conf = classify_credit(current_spread_bps=110.0, history=history)
        assert state == CreditState.LOOSE
        assert 0.0 <= conf <= 1.0

    def test_normal_credit(self):
        """Spread in P25-P75 range -> NORMAL."""
        history = _uniform_history(100.0, 500.0, n=120)
        state, conf = classify_credit(current_spread_bps=300.0, history=history)
        assert state == CreditState.NORMAL
        assert 0.0 <= conf <= 1.0

    def test_tight_credit(self):
        """Spread in P75-P90 range -> TIGHT."""
        history = _uniform_history(100.0, 500.0, n=120)
        # P75 = 400, P90 = 460 -> pick 430
        state, conf = classify_credit(current_spread_bps=430.0, history=history)
        assert state == CreditState.TIGHT
        assert 0.0 <= conf <= 1.0

    def test_stress_credit(self):
        """Spread above P90 of history -> STRESS."""
        history = _uniform_history(100.0, 500.0, n=120)
        state, conf = classify_credit(current_spread_bps=600.0, history=history)
        assert state == CreditState.STRESS
        assert 0.0 <= conf <= 1.0

    def test_confidence_near_boundary_is_low(self):
        """Spread right at P25 boundary should have low confidence."""
        history = _uniform_history(100.0, 500.0, n=120)
        p25 = float(np.percentile(history, 25))
        state, conf = classify_credit(current_spread_bps=p25, history=history)
        assert conf < 0.15

    def test_confidence_deep_stress_is_high(self):
        """Spread far above P90 -> high confidence."""
        history = _uniform_history(100.0, 500.0, n=120)
        state, conf = classify_credit(current_spread_bps=1000.0, history=history)
        assert state == CreditState.STRESS
        assert conf > 0.5


# ---------------------------------------------------------------------------
# RegimeClassifierConfig tests
# ---------------------------------------------------------------------------


class TestRegimeClassifierConfig:
    def test_default_min_history_months(self):
        config = RegimeClassifierConfig()
        assert config.min_history_months == 60

    def test_custom_min_history_months(self):
        config = RegimeClassifierConfig(min_history_months=36)
        assert config.min_history_months == 36


# ---------------------------------------------------------------------------
# MultiDimensionalRegimeClassifier tests
# ---------------------------------------------------------------------------


class TestMultiDimensionalRegimeClassifier:
    """Integration tests for the full classifier."""

    @pytest.fixture()
    def vol_history(self) -> np.ndarray:
        """120-month volatility history (10..30)."""
        return _uniform_history(10.0, 30.0, n=120)

    @pytest.fixture()
    def credit_history(self) -> np.ndarray:
        """120-month credit spread history (100..500 bps)."""
        return _uniform_history(100.0, 500.0, n=120)

    @pytest.fixture()
    def classifier(self) -> MultiDimensionalRegimeClassifier:
        return MultiDimensionalRegimeClassifier()

    def test_crisis_conditions(
        self,
        classifier: MultiDimensionalRegimeClassifier,
        vol_history: np.ndarray,
        credit_history: np.ndarray,
    ):
        """High vol + deep drawdown + euphoria valuation + stress credit -> crisis regime."""
        result = classifier.classify(
            as_of_date=date(2020, 3, 23),
            realized_vol=35.0,  # far above P95
            trailing_12m_return=-0.30,
            drawdown_from_peak=0.35,
            shiller_cape=40.0,  # EUPHORIA
            credit_spread_bps=600.0,  # above P90
            vol_history=vol_history,
            credit_history=credit_history,
        )
        assert isinstance(result, RegimeState)
        assert result.as_of_date == date(2020, 3, 23)
        assert result.volatility == VolatilityState.CRISIS
        assert result.trend == TrendState.DRAWDOWN  # drawdown overrides bear
        assert result.valuation == ValuationState.EUPHORIA
        assert result.credit == CreditState.STRESS

    def test_normal_conditions(
        self,
        classifier: MultiDimensionalRegimeClassifier,
        vol_history: np.ndarray,
        credit_history: np.ndarray,
    ):
        """Normal vol + bull trend + normal valuation + normal credit."""
        result = classifier.classify(
            as_of_date=date(2024, 6, 15),
            realized_vol=20.0,  # between P10 and P75
            trailing_12m_return=0.15,
            drawdown_from_peak=0.05,
            shiller_cape=20.0,  # NORMAL
            credit_spread_bps=300.0,  # between P25 and P75
            vol_history=vol_history,
            credit_history=credit_history,
        )
        assert isinstance(result, RegimeState)
        assert result.volatility == VolatilityState.NORMAL
        assert result.trend == TrendState.BULL
        assert result.valuation == ValuationState.NORMAL
        assert result.credit == CreditState.NORMAL

    def test_returns_regime_state_type(
        self,
        classifier: MultiDimensionalRegimeClassifier,
        vol_history: np.ndarray,
        credit_history: np.ndarray,
    ):
        result = classifier.classify(
            as_of_date=date(2025, 1, 1),
            realized_vol=15.0,
            trailing_12m_return=0.05,
            drawdown_from_peak=0.02,
            shiller_cape=22.0,
            credit_spread_bps=250.0,
            vol_history=vol_history,
            credit_history=credit_history,
        )
        assert isinstance(result, RegimeState)
        assert isinstance(result.confidence, RegimeConfidence)

    def test_confidence_all_in_valid_range(
        self,
        classifier: MultiDimensionalRegimeClassifier,
        vol_history: np.ndarray,
        credit_history: np.ndarray,
    ):
        result = classifier.classify(
            as_of_date=date(2025, 1, 1),
            realized_vol=20.0,
            trailing_12m_return=0.05,
            drawdown_from_peak=0.02,
            shiller_cape=22.0,
            credit_spread_bps=250.0,
            vol_history=vol_history,
            credit_history=credit_history,
        )
        assert 0.0 <= result.confidence.volatility <= 1.0
        assert 0.0 <= result.confidence.trend <= 1.0
        assert 0.0 <= result.confidence.valuation <= 1.0
        assert 0.0 <= result.confidence.credit <= 1.0

    def test_minimum_history_enforcement_vol(self, classifier: MultiDimensionalRegimeClassifier):
        """Vol history shorter than min_history_months should raise ValueError."""
        short_vol = np.array([15.0] * 50)  # only 50 months, default requires 60
        credit = np.array([200.0] * 120)
        with pytest.raises(ValueError, match="vol_history"):
            classifier.classify(
                as_of_date=date(2025, 1, 1),
                realized_vol=15.0,
                trailing_12m_return=0.05,
                drawdown_from_peak=0.02,
                shiller_cape=22.0,
                credit_spread_bps=250.0,
                vol_history=short_vol,
                credit_history=credit,
            )

    def test_minimum_history_enforcement_credit(self, classifier: MultiDimensionalRegimeClassifier):
        """Credit history shorter than min_history_months should raise ValueError."""
        vol = np.array([15.0] * 120)
        short_credit = np.array([200.0] * 50)
        with pytest.raises(ValueError, match="credit_history"):
            classifier.classify(
                as_of_date=date(2025, 1, 1),
                realized_vol=15.0,
                trailing_12m_return=0.05,
                drawdown_from_peak=0.02,
                shiller_cape=22.0,
                credit_spread_bps=250.0,
                vol_history=vol,
                credit_history=short_credit,
            )

    def test_custom_min_history(self):
        """Custom config with shorter history requirement should work."""
        config = RegimeClassifierConfig(min_history_months=30)
        clf = MultiDimensionalRegimeClassifier(config=config)
        short_vol = np.array([15.0] * 40)
        short_credit = np.array([200.0] * 40)
        # Should NOT raise with 40 months and min of 30
        result = clf.classify(
            as_of_date=date(2025, 1, 1),
            realized_vol=15.0,
            trailing_12m_return=0.05,
            drawdown_from_peak=0.02,
            shiller_cape=22.0,
            credit_spread_bps=200.0,
            vol_history=short_vol,
            credit_history=short_credit,
        )
        assert isinstance(result, RegimeState)

    def test_regime_key_format(
        self,
        classifier: MultiDimensionalRegimeClassifier,
        vol_history: np.ndarray,
        credit_history: np.ndarray,
    ):
        """Regime key should be pipe-delimited string of four axis values."""
        result = classifier.classify(
            as_of_date=date(2025, 1, 1),
            realized_vol=20.0,
            trailing_12m_return=0.15,
            drawdown_from_peak=0.05,
            shiller_cape=20.0,
            credit_spread_bps=300.0,
            vol_history=vol_history,
            credit_history=credit_history,
        )
        parts = result.regime_key.split("|")
        assert len(parts) == 4

    def test_low_vol_bear_cheap_loose(
        self,
        vol_history: np.ndarray,
        credit_history: np.ndarray,
    ):
        """Edge case: benign vol/credit but bearish trend + cheap valuation."""
        clf = MultiDimensionalRegimeClassifier()
        result = clf.classify(
            as_of_date=date(2009, 3, 9),
            realized_vol=9.0,  # below P10
            trailing_12m_return=-0.40,
            drawdown_from_peak=0.10,  # not enough for drawdown override
            shiller_cape=12.0,  # CHEAP
            credit_spread_bps=110.0,  # below P25
            vol_history=vol_history,
            credit_history=credit_history,
        )
        assert result.volatility == VolatilityState.LOW
        assert result.trend == TrendState.BEAR
        assert result.valuation == ValuationState.CHEAP
        assert result.credit == CreditState.LOOSE
