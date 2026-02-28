"""Tests for regime data models — enums, RegimeConfidence, RegimeState."""

from datetime import date
from enum import StrEnum

import pytest
from margin_engine.regime.models import (
    EXTREME_CONFIDENCE_THRESHOLD,
    CreditState,
    RegimeConfidence,
    RegimeState,
    TrendState,
    ValuationState,
    VolatilityState,
)
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestVolatilityState:
    def test_is_str_enum(self):
        assert issubclass(VolatilityState, StrEnum)

    def test_members(self):
        assert set(VolatilityState) == {
            VolatilityState.LOW,
            VolatilityState.NORMAL,
            VolatilityState.ELEVATED,
            VolatilityState.CRISIS,
        }

    def test_values_are_lowercase(self):
        assert VolatilityState.LOW.value == "low"
        assert VolatilityState.NORMAL.value == "normal"
        assert VolatilityState.ELEVATED.value == "elevated"
        assert VolatilityState.CRISIS.value == "crisis"

    def test_string_comparison(self):
        """StrEnum members compare equal to their string values."""
        assert VolatilityState.LOW == "low"
        assert VolatilityState.CRISIS == "crisis"


class TestTrendState:
    def test_is_str_enum(self):
        assert issubclass(TrendState, StrEnum)

    def test_members(self):
        assert set(TrendState) == {
            TrendState.BULL,
            TrendState.SIDEWAYS,
            TrendState.BEAR,
            TrendState.DRAWDOWN,
        }

    def test_values_are_lowercase(self):
        assert TrendState.BULL.value == "bull"
        assert TrendState.SIDEWAYS.value == "sideways"
        assert TrendState.BEAR.value == "bear"
        assert TrendState.DRAWDOWN.value == "drawdown"


class TestValuationState:
    def test_is_str_enum(self):
        assert issubclass(ValuationState, StrEnum)

    def test_members(self):
        assert set(ValuationState) == {
            ValuationState.CHEAP,
            ValuationState.NORMAL,
            ValuationState.EXPENSIVE,
            ValuationState.EUPHORIA,
        }

    def test_values_are_lowercase(self):
        assert ValuationState.CHEAP.value == "cheap"
        assert ValuationState.NORMAL.value == "normal"
        assert ValuationState.EXPENSIVE.value == "expensive"
        assert ValuationState.EUPHORIA.value == "euphoria"


class TestCreditState:
    def test_is_str_enum(self):
        assert issubclass(CreditState, StrEnum)

    def test_members(self):
        assert set(CreditState) == {
            CreditState.LOOSE,
            CreditState.NORMAL,
            CreditState.TIGHT,
            CreditState.STRESS,
        }

    def test_values_are_lowercase(self):
        assert CreditState.LOOSE.value == "loose"
        assert CreditState.NORMAL.value == "normal"
        assert CreditState.TIGHT.value == "tight"
        assert CreditState.STRESS.value == "stress"


# ---------------------------------------------------------------------------
# RegimeConfidence tests
# ---------------------------------------------------------------------------


class TestRegimeConfidence:
    def test_valid_construction(self):
        rc = RegimeConfidence(
            volatility=0.85,
            trend=0.90,
            valuation=0.75,
            credit=0.60,
        )
        assert rc.volatility == 0.85
        assert rc.trend == 0.90
        assert rc.valuation == 0.75
        assert rc.credit == 0.60

    def test_boundary_values_zero(self):
        rc = RegimeConfidence(volatility=0.0, trend=0.0, valuation=0.0, credit=0.0)
        assert rc.volatility == 0.0

    def test_boundary_values_one(self):
        rc = RegimeConfidence(volatility=1.0, trend=1.0, valuation=1.0, credit=1.0)
        assert rc.credit == 1.0

    def test_rejects_negative(self):
        with pytest.raises(ValidationError):
            RegimeConfidence(volatility=-0.01, trend=0.5, valuation=0.5, credit=0.5)

    def test_rejects_greater_than_one(self):
        with pytest.raises(ValidationError):
            RegimeConfidence(volatility=0.5, trend=1.01, valuation=0.5, credit=0.5)

    def test_rejects_negative_credit(self):
        with pytest.raises(ValidationError):
            RegimeConfidence(volatility=0.5, trend=0.5, valuation=0.5, credit=-0.1)

    def test_rejects_valuation_over_one(self):
        with pytest.raises(ValidationError):
            RegimeConfidence(volatility=0.5, trend=0.5, valuation=1.5, credit=0.5)

    def test_min_confidence_returns_minimum(self):
        rc = RegimeConfidence(volatility=0.85, trend=0.90, valuation=0.60, credit=0.75)
        assert rc.min_confidence == 0.60

    def test_min_confidence_all_same(self):
        rc = RegimeConfidence(volatility=0.50, trend=0.50, valuation=0.50, credit=0.50)
        assert rc.min_confidence == 0.50

    def test_min_confidence_first_field(self):
        rc = RegimeConfidence(volatility=0.10, trend=0.90, valuation=0.80, credit=0.70)
        assert rc.min_confidence == 0.10

    def test_min_confidence_last_field(self):
        rc = RegimeConfidence(volatility=0.90, trend=0.80, valuation=0.70, credit=0.05)
        assert rc.min_confidence == 0.05


# ---------------------------------------------------------------------------
# RegimeState tests
# ---------------------------------------------------------------------------


class TestRegimeState:
    @pytest.fixture()
    def default_confidence(self) -> RegimeConfidence:
        return RegimeConfidence(volatility=0.85, trend=0.90, valuation=0.75, credit=0.80)

    @pytest.fixture()
    def default_state(self, default_confidence: RegimeConfidence) -> RegimeState:
        return RegimeState(
            as_of_date=date(2025, 6, 15),
            volatility=VolatilityState.NORMAL,
            trend=TrendState.BULL,
            valuation=ValuationState.EXPENSIVE,
            credit=CreditState.NORMAL,
            confidence=default_confidence,
        )

    def test_valid_construction(self, default_state: RegimeState):
        assert default_state.as_of_date == date(2025, 6, 15)
        assert default_state.volatility == VolatilityState.NORMAL
        assert default_state.trend == TrendState.BULL
        assert default_state.valuation == ValuationState.EXPENSIVE
        assert default_state.credit == CreditState.NORMAL

    def test_regime_tuple(self, default_state: RegimeState):
        expected = ("normal", "bull", "expensive", "normal")
        assert default_state.regime_tuple == expected

    def test_regime_tuple_type(self, default_state: RegimeState):
        t = default_state.regime_tuple
        assert isinstance(t, tuple)
        assert len(t) == 4
        assert all(isinstance(s, str) for s in t)

    def test_regime_key(self, default_state: RegimeState):
        assert default_state.regime_key == "normal|bull|expensive|normal"

    def test_regime_key_crisis_scenario(self):
        state = RegimeState(
            as_of_date=date(2020, 3, 23),
            volatility=VolatilityState.CRISIS,
            trend=TrendState.DRAWDOWN,
            valuation=ValuationState.CHEAP,
            credit=CreditState.STRESS,
            confidence=RegimeConfidence(volatility=0.99, trend=0.95, valuation=0.80, credit=0.92),
        )
        assert state.regime_key == "crisis|drawdown|cheap|stress"

    def test_has_extreme_axis_false(self, default_state: RegimeState):
        """No confidence above 0.98 → has_extreme_axis is False."""
        assert default_state.has_extreme_axis is False

    def test_has_extreme_axis_true_at_boundary(self):
        """Confidence of exactly 0.99 (> 0.98) → has_extreme_axis is True."""
        state = RegimeState(
            as_of_date=date(2025, 1, 1),
            volatility=VolatilityState.CRISIS,
            trend=TrendState.BEAR,
            valuation=ValuationState.CHEAP,
            credit=CreditState.TIGHT,
            confidence=RegimeConfidence(volatility=0.99, trend=0.50, valuation=0.50, credit=0.50),
        )
        assert state.has_extreme_axis is True

    def test_has_extreme_axis_false_at_threshold(self):
        """Confidence of exactly 0.98 (not > 0.98) → has_extreme_axis is False."""
        state = RegimeState(
            as_of_date=date(2025, 1, 1),
            volatility=VolatilityState.NORMAL,
            trend=TrendState.SIDEWAYS,
            valuation=ValuationState.NORMAL,
            credit=CreditState.NORMAL,
            confidence=RegimeConfidence(volatility=0.98, trend=0.98, valuation=0.98, credit=0.98),
        )
        assert state.has_extreme_axis is False

    def test_has_extreme_axis_true_with_multiple_extremes(self):
        state = RegimeState(
            as_of_date=date(2025, 1, 1),
            volatility=VolatilityState.CRISIS,
            trend=TrendState.DRAWDOWN,
            valuation=ValuationState.EUPHORIA,
            credit=CreditState.STRESS,
            confidence=RegimeConfidence(volatility=0.99, trend=0.99, valuation=0.99, credit=0.99),
        )
        assert state.has_extreme_axis is True

    def test_rejects_wrong_enum_type(self, default_confidence: RegimeConfidence):
        with pytest.raises(ValidationError):
            RegimeState(
                as_of_date=date(2025, 1, 1),
                volatility="invalid_value",
                trend=TrendState.BULL,
                valuation=ValuationState.NORMAL,
                credit=CreditState.NORMAL,
                confidence=default_confidence,
            )

    def test_requires_all_fields(self):
        with pytest.raises(ValidationError):
            RegimeState(
                as_of_date=date(2025, 1, 1),
                volatility=VolatilityState.NORMAL,
                # missing trend, valuation, credit, confidence
            )

    def test_frozen_model(self, default_state: RegimeState):
        """RegimeState should be immutable (frozen)."""
        with pytest.raises(ValidationError):
            default_state.volatility = VolatilityState.CRISIS


# ---------------------------------------------------------------------------
# Constant tests
# ---------------------------------------------------------------------------


class TestConstants:
    def test_extreme_confidence_threshold_value(self):
        assert EXTREME_CONFIDENCE_THRESHOLD == 0.98

    def test_extreme_confidence_threshold_type(self):
        assert isinstance(EXTREME_CONFIDENCE_THRESHOLD, float)
