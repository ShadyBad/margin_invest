"""Exact Shapley value computation for filter ablation studies.

Computes the marginal contribution of each filter, averaged over all orderings.
For N filters, pre-computes all 2^N coalition values. For 6 filters this is
2^6 = 64 coalitions — easily tractable.

The Shapley value satisfies the efficiency axiom: values sum to v(N) - v(empty).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from itertools import combinations

from pydantic import BaseModel


class ShapleyResult(BaseModel):
    """Result of exact Shapley value computation."""

    values: dict[str, float]  # per-filter Shapley values
    coalition_values: dict[
        str, float
    ]  # frozenset key as comma-joined string, "(empty)" for empty set
    n_coalitions: int


def _coalition_key(coalition: frozenset[str]) -> str:
    """Convert a frozenset coalition to a stable, human-readable string key.

    The empty set is represented as ``"(empty)"``. Non-empty sets are
    comma-joined in sorted order for deterministic keys.
    """
    if not coalition:
        return "(empty)"
    return ",".join(sorted(coalition))


def compute_shapley_values(
    filters: list[str],
    value_fn: Callable[[frozenset[str]], float],
) -> ShapleyResult:
    """Compute exact Shapley values for a set of filters.

    Parameters
    ----------
    filters:
        List of filter names.
    value_fn:
        Coalition value function. Takes a frozenset of filter names and
        returns a scalar value (e.g. Sharpe ratio of the portfolio that
        uses only those filters).

    Returns
    -------
    ShapleyResult with per-filter Shapley values, all coalition values,
    and the total number of coalitions evaluated.
    """
    n = len(filters)

    # Pre-compute all 2^N coalition values
    coalition_values: dict[frozenset[str], float] = {}
    for size in range(n + 1):
        for combo in combinations(filters, size):
            coalition = frozenset(combo)
            coalition_values[coalition] = value_fn(coalition)
    # Include the empty set explicitly (combinations with size=0 yields one empty tuple)
    # Already handled above since combinations(filters, 0) = [()]

    n_coalitions = len(coalition_values)

    # Compute Shapley values
    n_factorial = math.factorial(n)
    values: dict[str, float] = {}

    for i in filters:
        phi_i = 0.0
        others = [f for f in filters if f != i]

        # Iterate over all subsets S of N \ {i}
        for size in range(len(others) + 1):
            weight = math.factorial(size) * math.factorial(n - size - 1) / n_factorial
            for combo in combinations(others, size):
                s = frozenset(combo)
                s_with_i = s | {i}
                marginal = coalition_values[s_with_i] - coalition_values[s]
                phi_i += weight * marginal

        values[i] = phi_i

    # Build human-readable coalition value dict
    readable_coalitions: dict[str, float] = {}
    for coalition, val in coalition_values.items():
        readable_coalitions[_coalition_key(coalition)] = val

    return ShapleyResult(
        values=values,
        coalition_values=readable_coalitions,
        n_coalitions=n_coalitions,
    )
