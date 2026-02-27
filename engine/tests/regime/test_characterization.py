"""Tests for gate characterization module."""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pytest

from margin_engine.regime.characterization import (
    GateRegimeStats,
    GateRegimeProfile,
    RegimeCharacterizationReport,
    compute_gate_profiles,
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
# Helpers
# ---------------------------------------------------------------------------


def _make_regime(
    trend: TrendState = TrendState.BULL,
    volatility: VolatilityState = VolatilityState.NORMAL,
    valuation: ValuationState = ValuationState.NORMAL,
    credit: CreditState = CreditState.NORMAL,
    as_of_date: date | None = None,
) -> RegimeState:
    """Build a RegimeState with sensible defaults."""
    return RegimeState(
        as_of_date=as_of_date or date(2024, 1, 1),
        volatility=volatility,
        trend=trend,
        valuation=valuation,
        credit=credit,
        confidence=RegimeConfidence(
            volatility=0.8, trend=0.8, valuation=0.8, credit=0.8
        ),
    )


# ---------------------------------------------------------------------------
# Test: empty gate_data -> empty report
# ---------------------------------------------------------------------------


class TestEmptyGateData:
    def test_empty_gate_data_returns_empty_report(self):
        result = compute_gate_profiles(gate_data={})
        assert isinstance(result, RegimeCharacterizationReport)
        assert result.profiles == {}


# ---------------------------------------------------------------------------
# Test: 2 gates -> 2 profiles in report
# ---------------------------------------------------------------------------


class TestTwoGatesProduceTwoProfiles:
    def test_two_gates_produce_two_profiles(self):
        bull = _make_regime(trend=TrendState.BULL)
        n = 12
        regimes = [bull] * n
        returns_with = [0.02] * n
        returns_without = [0.015] * n
        bench = [0.01] * n
        elim_rates = [0.3] * n

        gate_data = {
            "pe_filter": {
                "with": {
                    "regimes": regimes,
                    "returns": returns_with,
                    "benchmark": bench,
                    "elimination_rates": elim_rates,
                },
                "without": {
                    "returns": returns_without,
                    "benchmark": bench,
                },
            },
            "debt_filter": {
                "with": {
                    "regimes": regimes,
                    "returns": returns_with,
                    "benchmark": bench,
                    "elimination_rates": elim_rates,
                },
                "without": {
                    "returns": returns_without,
                    "benchmark": bench,
                },
            },
        }

        result = compute_gate_profiles(gate_data=gate_data)
        assert len(result.profiles) == 2
        assert "pe_filter" in result.profiles
        assert "debt_filter" in result.profiles
        assert result.profiles["pe_filter"].gate_name == "pe_filter"
        assert result.profiles["debt_filter"].gate_name == "debt_filter"


# ---------------------------------------------------------------------------
# Test: profile has stats per regime (2 regimes -> 2 stats)
# ---------------------------------------------------------------------------


class TestProfileHasStatsPerRegime:
    def test_two_regimes_produce_two_stats(self):
        bull = _make_regime(trend=TrendState.BULL)
        bear = _make_regime(trend=TrendState.BEAR)

        n = 12
        regimes = [bull] * 6 + [bear] * 6
        # Bull months: strong returns; Bear months: weak returns
        returns_with = [0.03, 0.04, 0.02, 0.05, 0.03, 0.04] + [
            -0.01, -0.02, 0.00, -0.03, -0.01, -0.02,
        ]
        returns_without = [0.02] * 6 + [-0.02] * 6
        bench = [0.01] * n
        elim_rates = [0.2] * 6 + [0.5] * 6

        gate_data = {
            "pe_filter": {
                "with": {
                    "regimes": regimes,
                    "returns": returns_with,
                    "benchmark": bench,
                    "elimination_rates": elim_rates,
                },
                "without": {
                    "returns": returns_without,
                    "benchmark": bench,
                },
            },
        }

        result = compute_gate_profiles(gate_data=gate_data)
        profile = result.profiles["pe_filter"]
        assert len(profile.regime_stats) == 2

        # Find the stats by regime_key
        keys = {s.regime_key for s in profile.regime_stats}
        assert bull.regime_key in keys
        assert bear.regime_key in keys

        # Check n_months per regime
        for s in profile.regime_stats:
            assert s.n_months == 6


# ---------------------------------------------------------------------------
# Test: PDR = 0 when no degradation, PDR < 0 when degraded
# ---------------------------------------------------------------------------


class TestPerformanceDegradationRatio:
    def test_pdr_zero_when_no_degradation(self):
        """If per-regime Sharpe equals unconditional Sharpe, PDR = 0."""
        bull = _make_regime(trend=TrendState.BULL)
        n = 12
        # Use varying returns so Sharpe is non-zero, but only one regime
        # so per-regime == unconditional
        returns_with = [0.03, 0.01, 0.04, 0.02, 0.05, 0.00,
                        0.03, 0.01, 0.04, 0.02, 0.05, 0.00]
        returns_without = [0.02] * n
        bench = [0.01] * n
        elim_rates = [0.3] * n

        gate_data = {
            "pe_filter": {
                "with": {
                    "regimes": [bull] * n,
                    "returns": returns_with,
                    "benchmark": bench,
                    "elimination_rates": elim_rates,
                },
                "without": {
                    "returns": returns_without,
                    "benchmark": bench,
                },
            },
        }

        result = compute_gate_profiles(gate_data=gate_data)
        profile = result.profiles["pe_filter"]
        # Single regime -> PDR should be exactly 0
        assert len(profile.regime_stats) == 1
        stats = profile.regime_stats[0]
        assert stats.pdr == pytest.approx(0.0, abs=1e-9)

    def test_pdr_negative_when_degraded(self):
        """If per-regime Sharpe is lower than unconditional, PDR < 0."""
        bull = _make_regime(trend=TrendState.BULL)
        bear = _make_regime(trend=TrendState.BEAR)

        # Bull: strong positive returns (high Sharpe in-regime)
        # Bear: weak/negative returns (low Sharpe in-regime)
        # Unconditional Sharpe will be somewhere in between
        # So bear regime will have PDR < 0
        bull_returns = [0.04, 0.05, 0.03, 0.06, 0.04, 0.05]
        bear_returns = [-0.03, -0.04, -0.02, -0.05, -0.03, -0.04]
        returns_with = bull_returns + bear_returns
        returns_without = [0.01] * 12
        bench = [0.01] * 12
        elim_rates = [0.3] * 12

        gate_data = {
            "pe_filter": {
                "with": {
                    "regimes": [bull] * 6 + [bear] * 6,
                    "returns": returns_with,
                    "benchmark": bench,
                    "elimination_rates": elim_rates,
                },
                "without": {
                    "returns": returns_without,
                    "benchmark": bench,
                },
            },
        }

        result = compute_gate_profiles(gate_data=gate_data)
        profile = result.profiles["pe_filter"]

        # Find the bear regime stats
        bear_stats = next(
            s for s in profile.regime_stats if s.regime_key == bear.regime_key
        )
        # Bear sharpe < unconditional sharpe => PDR < 0
        assert bear_stats.pdr < 0.0

        # Most degraded regime should be the bear regime
        assert profile.most_degraded_regime == bear.regime_key
        assert profile.max_pdr < 0.0


# ---------------------------------------------------------------------------
# Test: VIF > 1 when variance inflated
# ---------------------------------------------------------------------------


class TestVarianceInflationFactor:
    def test_vif_greater_than_one_when_variance_inflated(self):
        """When a regime has higher variance than unconditional, VIF > 1."""
        bull = _make_regime(trend=TrendState.BULL)
        bear = _make_regime(trend=TrendState.BEAR)

        # Bull: low-variance returns
        bull_returns = [0.02, 0.02, 0.02, 0.02, 0.02, 0.02]
        # Bear: high-variance returns (variance inflated relative to unconditional)
        bear_returns = [0.10, -0.08, 0.12, -0.10, 0.09, -0.07]
        returns_with = bull_returns + bear_returns
        returns_without = [0.01] * 12
        bench = [0.01] * 12
        elim_rates = [0.3] * 12

        gate_data = {
            "pe_filter": {
                "with": {
                    "regimes": [bull] * 6 + [bear] * 6,
                    "returns": returns_with,
                    "benchmark": bench,
                    "elimination_rates": elim_rates,
                },
                "without": {
                    "returns": returns_without,
                    "benchmark": bench,
                },
            },
        }

        result = compute_gate_profiles(gate_data=gate_data)
        profile = result.profiles["pe_filter"]

        bear_stats = next(
            s for s in profile.regime_stats if s.regime_key == bear.regime_key
        )
        # Bear regime has much higher variance than unconditional
        assert bear_stats.vif > 1.0

        # Max VIF on the profile should reflect the bear regime
        assert profile.max_vif > 1.0


# ---------------------------------------------------------------------------
# Test: elimination rate ratio = 2.0 when regime rate is 2x unconditional
# ---------------------------------------------------------------------------


class TestEliminationRateRatio:
    def test_elimination_rate_ratio_two_when_double(self):
        """When regime elimination rate is 2x unconditional, ratio = 2.0."""
        bull = _make_regime(trend=TrendState.BULL)
        bear = _make_regime(trend=TrendState.BEAR)

        # Unconditional elimination rate will be mean of all rates
        # Bull: 0.2 each, Bear: 0.4 each
        # Unconditional mean = (0.2*6 + 0.4*6) / 12 = 0.3
        # Bear ratio = 0.4 / 0.3 = 4/3 ... not 2.0
        #
        # To get exactly 2.0: regime_rate / unconditional = 2.0
        # Use: Bull: 0.1 (6 months), Bear: 0.3 (6 months)
        # Unconditional = (0.1*6 + 0.3*6)/12 = 0.2
        # Bear ratio = 0.3 / 0.2 = 1.5 ... still not 2.0
        #
        # Try: Bull: 0.0 (6 months), Bear: 0.4 (6 months)
        # Unconditional = (0.0*6 + 0.4*6)/12 = 0.2
        # Bear ratio = 0.4 / 0.2 = 2.0  YES!
        bull_elim = [0.0] * 6
        bear_elim = [0.4] * 6
        elim_rates = bull_elim + bear_elim

        returns_with = [0.02] * 6 + [0.01] * 6
        returns_without = [0.015] * 12
        bench = [0.01] * 12

        gate_data = {
            "pe_filter": {
                "with": {
                    "regimes": [bull] * 6 + [bear] * 6,
                    "returns": returns_with,
                    "benchmark": bench,
                    "elimination_rates": elim_rates,
                },
                "without": {
                    "returns": returns_without,
                    "benchmark": bench,
                },
            },
        }

        result = compute_gate_profiles(gate_data=gate_data)
        profile = result.profiles["pe_filter"]

        bear_stats = next(
            s for s in profile.regime_stats if s.regime_key == bear.regime_key
        )
        assert bear_stats.elimination_rate_ratio == pytest.approx(2.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Test: GateRegimeStats properties edge cases
# ---------------------------------------------------------------------------


class TestGateRegimeStatsProperties:
    def test_pdr_zero_when_unconditional_sharpe_zero(self):
        """PDR returns 0 when unconditional Sharpe is 0 (division by zero guard)."""
        stats = GateRegimeStats(
            regime_key="test",
            n_months=6,
            sharpe_with_gate=1.5,
            sharpe_without_gate=1.0,
            unconditional_sharpe_with_gate=0.0,
            elimination_rate=0.3,
            unconditional_elimination_rate=0.3,
            variance_with_gate=0.01,
            unconditional_variance=0.01,
        )
        assert stats.pdr == 0.0

    def test_vif_one_when_unconditional_variance_zero(self):
        """VIF returns 1.0 when unconditional variance is 0 (guard)."""
        stats = GateRegimeStats(
            regime_key="test",
            n_months=6,
            sharpe_with_gate=1.5,
            sharpe_without_gate=1.0,
            unconditional_sharpe_with_gate=1.2,
            elimination_rate=0.3,
            unconditional_elimination_rate=0.3,
            variance_with_gate=0.01,
            unconditional_variance=0.0,
        )
        assert stats.vif == 1.0

    def test_elimination_rate_ratio_one_when_unconditional_zero(self):
        """Elimination rate ratio returns 1.0 when unconditional is 0."""
        stats = GateRegimeStats(
            regime_key="test",
            n_months=6,
            sharpe_with_gate=1.5,
            sharpe_without_gate=1.0,
            unconditional_sharpe_with_gate=1.2,
            elimination_rate=0.3,
            unconditional_elimination_rate=0.0,
            variance_with_gate=0.01,
            unconditional_variance=0.01,
        )
        assert stats.elimination_rate_ratio == 1.0

    def test_pdr_computed_correctly(self):
        """PDR = sharpe_with_gate / unconditional_sharpe_with_gate - 1.0."""
        stats = GateRegimeStats(
            regime_key="test",
            n_months=6,
            sharpe_with_gate=0.8,
            sharpe_without_gate=1.0,
            unconditional_sharpe_with_gate=1.0,
            elimination_rate=0.3,
            unconditional_elimination_rate=0.3,
            variance_with_gate=0.01,
            unconditional_variance=0.01,
        )
        # 0.8 / 1.0 - 1.0 = -0.2
        assert stats.pdr == pytest.approx(-0.2, abs=1e-9)

    def test_vif_computed_correctly(self):
        """VIF = variance_with_gate / unconditional_variance."""
        stats = GateRegimeStats(
            regime_key="test",
            n_months=6,
            sharpe_with_gate=1.0,
            sharpe_without_gate=1.0,
            unconditional_sharpe_with_gate=1.0,
            elimination_rate=0.3,
            unconditional_elimination_rate=0.3,
            variance_with_gate=0.04,
            unconditional_variance=0.02,
        )
        # 0.04 / 0.02 = 2.0
        assert stats.vif == pytest.approx(2.0, abs=1e-9)
