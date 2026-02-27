"""Interference detection for ablation studies.

Consumes ablation study results (Sharpe ratios, failure vectors, return series)
and produces structured interference signals. These detectors answer the five
key questions from Section 3 of the ablation design:

1. Does the full filter stack degrade performance vs. the best single filter?
2. Does any filter have a negative marginal contribution in the greedy stack?
3. Do any two filters destroy value when paired?
4. Does any filter kill stocks that no other filter kills (low unique-kill)?
5. Does any filter inject volatility without improving returns?
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class DegradationResult(BaseModel):
    """Result of stack-vs-best-single degradation test."""

    detected: bool
    severity: float  # |delta| / best_single_sharpe
    best_single: str
    best_single_sharpe: float
    full_stack_sharpe: float


class NegativeMarginalResult(BaseModel):
    """A filter whose marginal contribution to the greedy stack is negative."""

    filter_name: str
    marginal_contribution: float
    position_in_stack: int


class PairwiseDestructionResult(BaseModel):
    """A pair of filters that destroy value when combined."""

    filter_a: str
    filter_b: str
    pair_sharpe: float
    best_single_sharpe: float
    interaction_effect: float  # pair_sharpe - max(single_a, single_b)


class CollapseResult(BaseModel):
    """A filter flagged for low unique-kill rate (universe collapse risk)."""

    filter_name: str
    total_kills: int
    unique_kills: int
    unique_kill_rate: float


class VolatilityInjectionResult(BaseModel):
    """A filter that injects volatility without improving returns."""

    filter_name: str
    vol_with: float
    vol_without: float
    return_with: float
    return_without: float
    detected: bool


class InterferenceReport(BaseModel):
    """Aggregate report from all five interference detectors."""

    degradation: DegradationResult | None = None
    negative_marginals: list[NegativeMarginalResult] = []
    destructive_pairs: list[PairwiseDestructionResult] = []
    collapse_flags: list[CollapseResult] = []
    volatility_injections: list[VolatilityInjectionResult] = []


# ---------------------------------------------------------------------------
# Detection functions
# ---------------------------------------------------------------------------


def detect_degradation(
    full_stack_sharpe: float,
    single_sharpes: dict[str, float],
) -> DegradationResult:
    """Detect whether the full filter stack degrades performance vs. best single.

    Parameters
    ----------
    full_stack_sharpe:
        Annualized Sharpe of the portfolio with all filters applied.
    single_sharpes:
        Mapping of filter_name -> Sharpe with only that filter applied.

    Returns
    -------
    DegradationResult with detected=True if full_stack < best_single.
    """
    best_name = max(single_sharpes, key=single_sharpes.get)  # type: ignore[arg-type]
    best_sharpe = single_sharpes[best_name]

    delta = full_stack_sharpe - best_sharpe
    detected = delta < 0
    severity = abs(delta) / best_sharpe if detected and best_sharpe != 0 else 0.0

    return DegradationResult(
        detected=detected,
        severity=severity,
        best_single=best_name,
        best_single_sharpe=best_sharpe,
        full_stack_sharpe=full_stack_sharpe,
    )


def detect_negative_marginal(
    stack_sharpes: list[float],
    filter_order: list[str],
    threshold: float = -0.02,
) -> list[NegativeMarginalResult]:
    """Detect filters with negative marginal contribution in the greedy stack.

    Parameters
    ----------
    stack_sharpes:
        stack_sharpes[0] is the control (no filters).
        stack_sharpes[i] for i >= 1 is the Sharpe with filters 0..i-1 applied.
        Length must be len(filter_order) + 1.
    filter_order:
        Ordered list of filter names as they were added to the stack.
    threshold:
        Marginal contribution below this value is flagged (default -0.02).

    Returns
    -------
    List of NegativeMarginalResult for each filter whose MC < threshold.
    """
    results: list[NegativeMarginalResult] = []

    for i, name in enumerate(filter_order):
        mc = stack_sharpes[i + 1] - stack_sharpes[i]
        if mc < threshold:
            results.append(
                NegativeMarginalResult(
                    filter_name=name,
                    marginal_contribution=mc,
                    position_in_stack=i,
                )
            )

    return results


def detect_pairwise_destruction(
    single_sharpes: dict[str, float],
    pair_sharpes: dict[tuple[str, str], float],
    threshold: float = -0.03,
) -> list[PairwiseDestructionResult]:
    """Detect pairs of filters that destroy value when combined.

    Parameters
    ----------
    single_sharpes:
        Mapping of filter_name -> Sharpe with only that filter.
    pair_sharpes:
        Mapping of (filter_a, filter_b) -> Sharpe with both filters.
    threshold:
        Interaction effect below this value is flagged (default -0.03).

    Returns
    -------
    List of PairwiseDestructionResult for each destructive pair.
    """
    results: list[PairwiseDestructionResult] = []

    for (a, b), pair_sharpe in pair_sharpes.items():
        best_single = max(single_sharpes[a], single_sharpes[b])
        interaction = pair_sharpe - best_single
        if interaction < threshold:
            results.append(
                PairwiseDestructionResult(
                    filter_a=a,
                    filter_b=b,
                    pair_sharpe=pair_sharpe,
                    best_single_sharpe=best_single,
                    interaction_effect=interaction,
                )
            )

    return results


def detect_universe_collapse(
    fail_vectors: dict[str, np.ndarray],
    threshold: float = 0.01,
) -> list[CollapseResult]:
    """Detect filters with low unique-kill rate (universe collapse risk).

    A "unique kill" is a stock that fails this filter but passes ALL other
    filters. A low unique-kill rate means the filter is mostly redundant —
    nearly everything it eliminates is already eliminated by other filters.

    Parameters
    ----------
    fail_vectors:
        Mapping of filter_name -> binary array (1 = fail, 0 = pass).
        All arrays must have the same length.
    threshold:
        Unique-kill rate below this value is flagged (default 0.01 = 1%).

    Returns
    -------
    List of CollapseResult for each filter with unique_kill_rate < threshold.
    """
    names = list(fail_vectors.keys())
    results: list[CollapseResult] = []

    for name in names:
        fails = fail_vectors[name]
        total_kills = int(np.sum(fails))

        if total_kills == 0:
            # Filter kills nothing — unique_kill_rate is 0
            results.append(
                CollapseResult(
                    filter_name=name,
                    total_kills=0,
                    unique_kills=0,
                    unique_kill_rate=0.0,
                )
            )
            continue

        # A stock is a unique kill if it fails THIS filter and passes ALL others
        other_names = [n for n in names if n != name]
        if not other_names:
            # Only one filter — all kills are unique
            unique = total_kills
        else:
            # passes_all_others[i] = 1 if stock i passes every other filter
            passes_all_others = np.ones_like(fails)
            for other in other_names:
                passes_all_others = passes_all_others & (1 - fail_vectors[other])
            unique = int(np.sum(fails & passes_all_others))

        unique_rate = unique / total_kills if total_kills > 0 else 0.0

        if unique_rate < threshold:
            results.append(
                CollapseResult(
                    filter_name=name,
                    total_kills=total_kills,
                    unique_kills=unique,
                    unique_kill_rate=unique_rate,
                )
            )

    return results


def detect_volatility_injection(
    returns_with: dict[str, np.ndarray],
    returns_without: dict[str, np.ndarray],
) -> list[VolatilityInjectionResult]:
    """Detect filters that inject volatility without improving returns.

    For each filter, compares the portfolio return series *with* the filter
    active vs. *without* it. A filter is flagged if applying it increases
    volatility AND does not improve mean returns.

    Parameters
    ----------
    returns_with:
        Mapping of filter_name -> monthly return series with filter active.
    returns_without:
        Mapping of filter_name -> monthly return series without filter active.

    Returns
    -------
    List of VolatilityInjectionResult for each filter.
    """
    results: list[VolatilityInjectionResult] = []

    for name in returns_with:
        rw = returns_with[name]
        rwo = returns_without[name]

        vol_w = float(np.std(rw, ddof=1))
        vol_wo = float(np.std(rwo, ddof=1))
        ret_w = float(np.mean(rw))
        ret_wo = float(np.mean(rwo))

        detected = vol_w > vol_wo and ret_w <= ret_wo

        results.append(
            VolatilityInjectionResult(
                filter_name=name,
                vol_with=vol_w,
                vol_without=vol_wo,
                return_with=ret_w,
                return_without=ret_wo,
                detected=detected,
            )
        )

    return results


def compute_failure_correlation(
    fail_vectors: dict[str, np.ndarray],
) -> dict[str, dict[str, float]]:
    """Compute pairwise Pearson correlation of failure vectors.

    Parameters
    ----------
    fail_vectors:
        Mapping of filter_name -> binary array (1 = fail, 0 = pass).

    Returns
    -------
    Nested dict: corr[filter_a][filter_b] = Pearson r.
    Constant columns (std=0) produce 0.0 correlation with everything.
    """
    names = list(fail_vectors.keys())
    n = len(names)

    # Build matrix: rows = filters, columns = stocks
    matrix = np.array([fail_vectors[name].astype(np.float64) for name in names])

    # Pre-compute means and stds
    means = matrix.mean(axis=1)
    stds = matrix.std(axis=1, ddof=0)

    result: dict[str, dict[str, float]] = {}

    for i in range(n):
        result[names[i]] = {}
        for j in range(n):
            if i == j:
                result[names[i]][names[j]] = 1.0
            elif stds[i] == 0 or stds[j] == 0:
                result[names[i]][names[j]] = 0.0
            else:
                # Pearson correlation
                centered_i = matrix[i] - means[i]
                centered_j = matrix[j] - means[j]
                cov = float(np.mean(centered_i * centered_j))
                r = cov / (stds[i] * stds[j])
                result[names[i]][names[j]] = float(r)

    return result
