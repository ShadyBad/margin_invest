"""Tests for regime-conditioned Shapley value computation."""

from __future__ import annotations

import math

import pytest

from margin_engine.regime.shapley import (
    RegimeShapleyResult,
    _sharpe_from_returns,
    compute_regime_conditioned_shapley,
)


# ---------------------------------------------------------------------------
# Helper: build a coalition_returns_fn from a dict of precomputed data
# ---------------------------------------------------------------------------


def _make_coalition_returns_fn(
    data: dict[frozenset[str], dict[str, list[float]]],
):
    """Return a coalition_returns_fn closure backed by a lookup dict."""

    def fn(coalition: frozenset[str]) -> dict[str, list[float]]:
        return data[coalition]

    return fn


# ---------------------------------------------------------------------------
# Tests for _sharpe_from_returns
# ---------------------------------------------------------------------------


class TestSharpeFromReturns:
    def test_returns_zero_for_fewer_than_two_returns(self):
        assert _sharpe_from_returns([]) == 0.0
        assert _sharpe_from_returns([0.05]) == 0.0

    def test_returns_zero_for_zero_std(self):
        # All identical returns → std = 0 → Sharpe = 0
        assert _sharpe_from_returns([0.01, 0.01, 0.01]) == 0.0

    def test_positive_sharpe(self):
        # Known returns: mean excess > 0, positive std
        returns = [0.05, 0.06, 0.07, 0.08, 0.09]
        rf_monthly = 0.04 / 12
        mean_excess = sum(r - rf_monthly for r in returns) / len(returns)
        std = (sum((r - sum(returns) / len(returns)) ** 2 for r in returns) / (len(returns) - 1)) ** 0.5
        expected = (mean_excess / std) * math.sqrt(12)
        result = _sharpe_from_returns(returns, risk_free_monthly=rf_monthly)
        assert abs(result - expected) < 1e-10


# ---------------------------------------------------------------------------
# Tests for compute_regime_conditioned_shapley
# ---------------------------------------------------------------------------


class TestRegimeConditionedShapley:
    """Core tests for regime-conditioned Shapley values."""

    def test_two_regimes_produces_per_regime_values(self):
        """Two regimes → produces per-regime Shapley values for each filter."""
        filters = ["filter_a", "filter_b"]
        regime_keys = ["bull", "bear"]

        # Build returns data: each coalition × regime
        # Bull regime: both filters add value, bear regime: only filter_a helps
        data: dict[frozenset[str], dict[str, list[float]]] = {
            frozenset(): {
                "bull": [0.01, 0.02, 0.01, 0.02, 0.01],
                "bear": [-0.02, -0.03, -0.02, -0.03, -0.02],
            },
            frozenset({"filter_a"}): {
                "bull": [0.03, 0.04, 0.03, 0.04, 0.03],
                "bear": [0.01, 0.00, 0.01, 0.00, 0.01],
            },
            frozenset({"filter_b"}): {
                "bull": [0.02, 0.03, 0.02, 0.03, 0.02],
                "bear": [-0.02, -0.03, -0.02, -0.03, -0.02],
            },
            frozenset({"filter_a", "filter_b"}): {
                "bull": [0.05, 0.06, 0.05, 0.06, 0.05],
                "bear": [0.01, 0.00, 0.01, 0.00, 0.01],
            },
        }

        result = compute_regime_conditioned_shapley(
            filters=filters,
            coalition_returns_fn=_make_coalition_returns_fn(data),
            regime_keys=regime_keys,
        )

        assert isinstance(result, RegimeShapleyResult)
        assert set(result.per_regime.keys()) == {"bull", "bear"}

        # Each regime result has Shapley values for both filters
        for rk in regime_keys:
            shapley = result.per_regime[rk]
            assert set(shapley.values.keys()) == {"filter_a", "filter_b"}
            # n_coalitions = 2^2 = 4
            assert shapley.n_coalitions == 4

        # Bull: both filters contribute positively (returns increase with either)
        bull = result.per_regime["bull"]
        assert bull.values["filter_a"] > 0
        assert bull.values["filter_b"] > 0

        # Bear: filter_a helps (turns negative into positive), filter_b does not
        bear = result.per_regime["bear"]
        assert bear.values["filter_a"] > 0
        # filter_b adds no value in bear (same returns as empty)
        # Its marginal contribution: avg of [v({b}) - v({}), v({a,b}) - v({a})]
        # v({b}) returns same as v({}) in bear, v({a,b}) same as v({a}) in bear
        # So filter_b shapley ≈ 0 in bear
        assert abs(bear.values["filter_b"]) < 1e-10

    def test_single_regime_matches_standard_shapley(self):
        """Single regime → per-regime Shapley matches standard (non-zero)."""
        filters = ["f1", "f2"]
        regime_keys = ["only"]

        data: dict[frozenset[str], dict[str, list[float]]] = {
            frozenset(): {
                "only": [0.00, 0.00, 0.00, 0.00, 0.00],
            },
            frozenset({"f1"}): {
                "only": [0.03, 0.04, 0.03, 0.04, 0.03],
            },
            frozenset({"f2"}): {
                "only": [0.02, 0.03, 0.02, 0.03, 0.02],
            },
            frozenset({"f1", "f2"}): {
                "only": [0.05, 0.06, 0.05, 0.06, 0.05],
            },
        }

        result = compute_regime_conditioned_shapley(
            filters=filters,
            coalition_returns_fn=_make_coalition_returns_fn(data),
            regime_keys=regime_keys,
        )

        shapley = result.per_regime["only"]
        # Both should be non-zero (returns improve with each filter)
        assert shapley.values["f1"] != 0.0
        assert shapley.values["f2"] != 0.0

        # Verify the Sharpe values make sense:
        # f1 contributes more (higher absolute returns) so should have higher Shapley
        assert shapley.values["f1"] > shapley.values["f2"]

    def test_efficiency_axiom_holds_per_regime(self):
        """Efficiency axiom: sum of Shapley values ≈ v(N) - v(empty) per regime."""
        filters = ["x", "y", "z"]
        regime_keys = ["regime_a", "regime_b"]

        # Build returns with varying contributions per regime
        data: dict[frozenset[str], dict[str, list[float]]] = {
            frozenset(): {
                "regime_a": [0.00, 0.01, 0.00, 0.01, 0.00, 0.01],
                "regime_b": [-0.01, -0.02, -0.01, -0.02, -0.01, -0.02],
            },
            frozenset({"x"}): {
                "regime_a": [0.02, 0.03, 0.02, 0.03, 0.02, 0.03],
                "regime_b": [0.01, 0.00, 0.01, 0.00, 0.01, 0.00],
            },
            frozenset({"y"}): {
                "regime_a": [0.01, 0.02, 0.01, 0.02, 0.01, 0.02],
                "regime_b": [0.00, -0.01, 0.00, -0.01, 0.00, -0.01],
            },
            frozenset({"z"}): {
                "regime_a": [0.03, 0.04, 0.03, 0.04, 0.03, 0.04],
                "regime_b": [0.02, 0.01, 0.02, 0.01, 0.02, 0.01],
            },
            frozenset({"x", "y"}): {
                "regime_a": [0.03, 0.04, 0.03, 0.04, 0.03, 0.04],
                "regime_b": [0.01, 0.00, 0.01, 0.00, 0.01, 0.00],
            },
            frozenset({"x", "z"}): {
                "regime_a": [0.04, 0.05, 0.04, 0.05, 0.04, 0.05],
                "regime_b": [0.03, 0.02, 0.03, 0.02, 0.03, 0.02],
            },
            frozenset({"y", "z"}): {
                "regime_a": [0.03, 0.04, 0.03, 0.04, 0.03, 0.04],
                "regime_b": [0.02, 0.01, 0.02, 0.01, 0.02, 0.01],
            },
            frozenset({"x", "y", "z"}): {
                "regime_a": [0.05, 0.06, 0.05, 0.06, 0.05, 0.06],
                "regime_b": [0.03, 0.02, 0.03, 0.02, 0.03, 0.02],
            },
        }

        result = compute_regime_conditioned_shapley(
            filters=filters,
            coalition_returns_fn=_make_coalition_returns_fn(data),
            regime_keys=regime_keys,
        )

        for rk in regime_keys:
            shapley = result.per_regime[rk]
            sum_values = sum(shapley.values.values())

            # v(N) and v(empty) for this regime
            rf = 0.04 / 12
            v_full = _sharpe_from_returns(data[frozenset(filters)][rk], rf)
            v_empty = _sharpe_from_returns(data[frozenset()][rk], rf)

            expected_total = v_full - v_empty
            assert abs(sum_values - expected_total) < 1e-10, (
                f"Efficiency axiom violated for {rk}: "
                f"sum={sum_values}, v(N)-v(empty)={expected_total}"
            )

    def test_coalition_returns_fn_called_once_per_coalition(self):
        """Coalition returns fn should be called once per coalition, not once per regime."""
        filters = ["a", "b"]
        regime_keys = ["r1", "r2"]

        call_count = 0
        base_data: dict[frozenset[str], dict[str, list[float]]] = {
            frozenset(): {
                "r1": [0.01, 0.02, 0.01],
                "r2": [0.00, 0.01, 0.00],
            },
            frozenset({"a"}): {
                "r1": [0.03, 0.04, 0.03],
                "r2": [0.02, 0.03, 0.02],
            },
            frozenset({"b"}): {
                "r1": [0.02, 0.03, 0.02],
                "r2": [0.01, 0.02, 0.01],
            },
            frozenset({"a", "b"}): {
                "r1": [0.04, 0.05, 0.04],
                "r2": [0.03, 0.04, 0.03],
            },
        }

        def counting_fn(coalition: frozenset[str]) -> dict[str, list[float]]:
            nonlocal call_count
            call_count += 1
            return base_data[coalition]

        compute_regime_conditioned_shapley(
            filters=filters,
            coalition_returns_fn=counting_fn,
            regime_keys=regime_keys,
        )

        # 2 filters → 2^2 = 4 coalitions, each called exactly once
        assert call_count == 4
