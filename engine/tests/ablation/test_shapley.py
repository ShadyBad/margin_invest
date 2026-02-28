"""Tests for ablation Shapley value computation."""

from __future__ import annotations

import pytest
from margin_engine.ablation.shapley import compute_shapley_values


class TestShapleyValues:
    """Tests for compute_shapley_values."""

    def test_shapley_values_sum_to_grand_coalition(self) -> None:
        """Sum of all Shapley values == v(full set) - v(empty).

        Uses v(S) = len(S), a linear value function with no interaction effects.
        """
        filters = ["a", "b", "c"]

        def value_fn(s: frozenset[str]) -> float:
            return float(len(s))

        result = compute_shapley_values(filters, value_fn)

        grand = value_fn(frozenset(filters))
        empty = value_fn(frozenset())

        assert sum(result.values.values()) == pytest.approx(grand - empty)

    def test_shapley_symmetric_players(self) -> None:
        """If all filters contribute equally (v(S) = len(S)), Shapley values are all equal."""
        filters = ["a", "b", "c"]

        def value_fn(s: frozenset[str]) -> float:
            return float(len(s))

        result = compute_shapley_values(filters, value_fn)

        # Each player contributes exactly 1.0 in a linear game
        for name in filters:
            assert result.values[name] == pytest.approx(1.0)

    def test_shapley_null_player(self) -> None:
        """A filter that never changes v(S) should have Shapley value = 0.

        Filter "c" is a null player: v(S) = len(S - {"c"}).
        """
        filters = ["a", "b", "c"]

        def value_fn(s: frozenset[str]) -> float:
            return float(len(s - {"c"}))

        result = compute_shapley_values(filters, value_fn)

        # "c" contributes nothing — Shapley value should be 0
        assert result.values["c"] == pytest.approx(0.0)

        # "a" and "b" should each get 1.0 (symmetric, non-null)
        assert result.values["a"] == pytest.approx(1.0)
        assert result.values["b"] == pytest.approx(1.0)

        # Efficiency still holds: sum = v(N) - v(empty) = 2 - 0 = 2
        assert sum(result.values.values()) == pytest.approx(2.0)

    def test_shapley_records_coalition_values(self) -> None:
        """With 2 filters, should record 2^2 = 4 coalition values."""
        filters = ["x", "y"]

        def value_fn(s: frozenset[str]) -> float:
            return float(len(s))

        result = compute_shapley_values(filters, value_fn)

        assert result.n_coalitions == 4
        assert len(result.coalition_values) == 4

        # Verify all expected coalitions are present
        assert "(empty)" in result.coalition_values
        assert "x" in result.coalition_values
        assert "y" in result.coalition_values
        assert "x,y" in result.coalition_values

        # Verify coalition values are correct
        assert result.coalition_values["(empty)"] == pytest.approx(0.0)
        assert result.coalition_values["x"] == pytest.approx(1.0)
        assert result.coalition_values["y"] == pytest.approx(1.0)
        assert result.coalition_values["x,y"] == pytest.approx(2.0)
