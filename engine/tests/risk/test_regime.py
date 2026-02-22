"""Tests for multi-dimensional regime detection."""

from __future__ import annotations

from margin_engine.risk.regime import (
    RegimeDimension,
    RegimeLevel,
    detect_composite_regime,
    detect_correlation_regime,
    detect_credit_regime,
    detect_valuation_regime,
    detect_volatility_regime,
)
from margin_engine.scoring.market_regime import MarketRegime

# ---------------------------------------------------------------------------
# Valuation (CAPE)
# ---------------------------------------------------------------------------


class TestValuationRegime:
    def test_cheap(self) -> None:
        state = detect_valuation_regime(cape=10)
        assert state.dimension == RegimeDimension.VALUATION
        assert state.level == RegimeLevel.CHEAP
        assert state.raw_value == 10

    def test_normal(self) -> None:
        state = detect_valuation_regime(cape=20)
        assert state.level == RegimeLevel.NORMAL

    def test_elevated(self) -> None:
        state = detect_valuation_regime(cape=30)
        assert state.level == RegimeLevel.ELEVATED

    def test_extreme(self) -> None:
        state = detect_valuation_regime(cape=40)
        assert state.level == RegimeLevel.EXTREME

    def test_boundary_15(self) -> None:
        """cape=15.0 should be NORMAL (inclusive lower bound)."""
        state = detect_valuation_regime(cape=15.0)
        assert state.level == RegimeLevel.NORMAL

    def test_boundary_25(self) -> None:
        """cape=25.0 should be NORMAL (inclusive upper bound)."""
        state = detect_valuation_regime(cape=25.0)
        assert state.level == RegimeLevel.NORMAL

    def test_boundary_35(self) -> None:
        """cape=35.0 should be ELEVATED (inclusive upper bound)."""
        state = detect_valuation_regime(cape=35.0)
        assert state.level == RegimeLevel.ELEVATED


# ---------------------------------------------------------------------------
# Volatility (VIX)
# ---------------------------------------------------------------------------


class TestVolatilityRegime:
    def test_cheap(self) -> None:
        state = detect_volatility_regime(vix=10)
        assert state.level == RegimeLevel.CHEAP

    def test_normal(self) -> None:
        state = detect_volatility_regime(vix=18)
        assert state.level == RegimeLevel.NORMAL

    def test_elevated(self) -> None:
        state = detect_volatility_regime(vix=25)
        assert state.level == RegimeLevel.ELEVATED

    def test_extreme(self) -> None:
        state = detect_volatility_regime(vix=40)
        assert state.level == RegimeLevel.EXTREME


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------


class TestCorrelationRegime:
    def test_normal_low(self) -> None:
        state = detect_correlation_regime(cross_corr=0.3)
        assert state.level == RegimeLevel.NORMAL

    def test_normal_mid(self) -> None:
        state = detect_correlation_regime(cross_corr=0.5)
        assert state.level == RegimeLevel.NORMAL

    def test_elevated(self) -> None:
        state = detect_correlation_regime(cross_corr=0.7)
        assert state.level == RegimeLevel.ELEVATED

    def test_extreme(self) -> None:
        state = detect_correlation_regime(cross_corr=0.9)
        assert state.level == RegimeLevel.EXTREME


# ---------------------------------------------------------------------------
# Credit
# ---------------------------------------------------------------------------


class TestCreditRegime:
    def test_normal_tight(self) -> None:
        state = detect_credit_regime(credit_spread_oas=1.0)
        assert state.level == RegimeLevel.NORMAL

    def test_normal(self) -> None:
        state = detect_credit_regime(credit_spread_oas=2.5)
        assert state.level == RegimeLevel.NORMAL

    def test_elevated(self) -> None:
        state = detect_credit_regime(credit_spread_oas=4.0)
        assert state.level == RegimeLevel.ELEVATED

    def test_extreme(self) -> None:
        state = detect_credit_regime(credit_spread_oas=6.0)
        assert state.level == RegimeLevel.EXTREME


# ---------------------------------------------------------------------------
# Composite regime
# ---------------------------------------------------------------------------


class TestCompositeRegime:
    def test_cape_only_normal(self) -> None:
        """cape=20, no other dims -> NORMAL, kappa=1.0"""
        result = detect_composite_regime(cape=20)
        assert result.overall == MarketRegime.NORMAL
        assert len(result.states) == 1
        assert result.kappa_adjustment == 1.0

    def test_cape_only_cheap(self) -> None:
        result = detect_composite_regime(cape=10)
        assert result.overall == MarketRegime.CHEAP
        assert result.risk_budget_multiplier == 1.2

    def test_worst_of_logic(self) -> None:
        """cape=20(NORMAL) + vix=35(EXTREME) -> EXTREME overall -> EUPHORIA MarketRegime"""
        result = detect_composite_regime(cape=20, vix=35)
        assert result.overall == MarketRegime.EUPHORIA
        assert result.kappa_adjustment == 2.5

    def test_all_dimensions(self) -> None:
        """All 4 dimensions active."""
        result = detect_composite_regime(cape=20, vix=18, cross_corr=0.5, credit_spread=2.0)
        assert len(result.states) == 4
        assert result.overall == MarketRegime.NORMAL

    def test_backward_compat_cape_only(self) -> None:
        """CAPE-only should match existing detect_regime behavior."""
        from margin_engine.scoring.market_regime import detect_regime

        for cape in [10, 20, 30, 40]:
            existing = detect_regime(cape)
            composite = detect_composite_regime(cape=cape)
            assert composite.overall == existing, (
                f"Mismatch at CAPE={cape}: detect_regime={existing}, "
                f"composite.overall={composite.overall}"
            )

    def test_missing_dims_default_normal(self) -> None:
        """Missing dimensions don't escalate severity."""
        result = detect_composite_regime(cape=10)  # CHEAP
        assert result.overall == MarketRegime.CHEAP  # Only valuation counts

    def test_kappa_scaling(self) -> None:
        """Check all kappa values."""
        assert detect_composite_regime(cape=10).kappa_adjustment == 0.7  # CHEAP
        assert detect_composite_regime(cape=20).kappa_adjustment == 1.0  # NORMAL
        assert detect_composite_regime(cape=30).kappa_adjustment == 1.5  # EXPENSIVE
        assert detect_composite_regime(cape=40).kappa_adjustment == 2.5  # EUPHORIA

    def test_risk_budget_scaling(self) -> None:
        """Check all risk budget values."""
        assert detect_composite_regime(cape=10).risk_budget_multiplier == 1.2
        assert detect_composite_regime(cape=20).risk_budget_multiplier == 1.0
        assert detect_composite_regime(cape=30).risk_budget_multiplier == 0.7
        assert detect_composite_regime(cape=40).risk_budget_multiplier == 0.5
