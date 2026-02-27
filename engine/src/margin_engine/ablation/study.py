"""Full ablation study orchestrator.

Ties together the runner, detection, bootstrap, and Shapley modules into a
single ``AblationStudy.run()`` call that executes all four phases and produces
a ``StudyReport`` with actionable recommendations per filter.
"""

from __future__ import annotations

import itertools
from statistics import median

from pydantic import BaseModel, Field

from margin_engine.ablation.bootstrap import bootstrap_sharpe_difference  # noqa: F401
from margin_engine.ablation.detection import (
    InterferenceReport,
    detect_degradation,
    detect_negative_marginal,
    detect_pairwise_destruction,
)
from margin_engine.ablation.runner import (
    ALL_FILTER_NAMES,
    DEFAULT_STACK_ORDER,
    AblationConfig,
    AblationResult,
    AblationRunner,
    FilterCombination,
)
from margin_engine.ablation.shapley import ShapleyResult, compute_shapley_values
from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.pit_provider import PointInTimeProvider

# ---------------------------------------------------------------------------
# Report model
# ---------------------------------------------------------------------------


class StudyReport(BaseModel):
    """Complete ablation study output."""

    single_baselines: list[AblationResult]  # 7 results (control + 6 singles)
    pairwise_results: list[AblationResult]  # 15 pairwise results
    incremental_stacks: dict[str, list[AblationResult]]  # 4 orderings
    full_stack: AblationResult | None = None
    interference: InterferenceReport
    shapley_values: ShapleyResult | None = None
    failure_correlations: dict[str, dict[str, float]] = Field(default_factory=dict)
    recommendations: dict[str, str] = Field(default_factory=dict)  # filter_name -> action


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class AblationStudy:
    """Orchestrates a complete ablation study across four phases.

    Phase 1: Single-filter baselines (7 results).
    Phase 2: Pairwise combinations (15 results).
    Phase 3: Incremental stacks (4 orderings x 7 results each).
    Phase 4: Shapley values with coalition caching.

    Then applies interference detection and generates per-filter recommendations.
    """

    def __init__(
        self,
        config: AblationConfig,
        pit_provider: PointInTimeProvider,
        factor_registry: FactorRegistry,
        benchmark_prices: dict | None = None,
        bootstrap_resamples: int = 1000,
    ) -> None:
        self._config = config
        self._runner = AblationRunner(
            config=config,
            pit_provider=pit_provider,
            factor_registry=factor_registry,
            benchmark_prices=benchmark_prices,
        )
        self._bootstrap_resamples = bootstrap_resamples

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> StudyReport:
        """Execute all four phases and return a complete StudyReport."""

        # Phase 1: Single-filter baselines
        single_baselines = self._runner.run_single_filter_baselines()

        # Extract single-filter Sharpe ratios (skip control at index 0)
        single_sharpes: dict[str, float] = {}
        for r in single_baselines[1:]:
            filter_name = next(iter(r.combination.enabled_filters))
            single_sharpes[filter_name] = r.metrics.sharpe_ratio

        # Phase 2: Pairwise combinations
        pairwise_results = self._runner.run_pairwise_combinations()

        # Phase 3: Incremental stacks (4 orderings)
        best_first_order = sorted(
            single_sharpes.keys(),
            key=lambda f: single_sharpes[f],
            reverse=True,
        )
        worst_first_order = list(reversed(best_first_order))

        orderings: dict[str, list[str]] = {
            "default": list(DEFAULT_STACK_ORDER),
            "reverse": list(reversed(DEFAULT_STACK_ORDER)),
            "best_first": best_first_order,
            "worst_first": worst_first_order,
        }

        incremental_stacks: dict[str, list[AblationResult]] = {}
        for ordering_name, order in orderings.items():
            incremental_stacks[ordering_name] = self._runner.run_incremental_stack(order)

        # Full stack = last result of the default incremental stack
        full_stack = incremental_stacks["default"][-1]

        # Phase 4: Shapley values with coalition caching
        coalition_cache = self._build_coalition_cache(
            single_baselines, pairwise_results
        )

        def cached_value_fn(coalition: frozenset[str]) -> float:
            key = coalition
            if key in coalition_cache:
                return coalition_cache[key]
            # Run on demand for coalitions not already cached
            combo_name = "+".join(sorted(coalition)) if coalition else "empty"
            combo = FilterCombination(name=combo_name, enabled_filters=set(coalition))
            result = self._runner.run_combination(combo)
            value = result.metrics.sharpe_ratio
            coalition_cache[key] = value
            return value

        shapley_values = compute_shapley_values(
            filters=sorted(ALL_FILTER_NAMES),
            value_fn=cached_value_fn,
        )

        # Detection
        full_stack_sharpe = full_stack.metrics.sharpe_ratio

        degradation = detect_degradation(full_stack_sharpe, single_sharpes)

        # Default stack Sharpe values for negative marginal detection
        default_stack = incremental_stacks["default"]
        default_stack_sharpes = [r.metrics.sharpe_ratio for r in default_stack]
        negative_marginals = detect_negative_marginal(
            default_stack_sharpes, orderings["default"]
        )

        # Pairwise destruction detection
        pair_sharpes: dict[tuple[str, str], float] = {}
        for r in pairwise_results:
            filters_sorted = tuple(sorted(r.combination.enabled_filters))
            pair_sharpes[filters_sorted] = r.metrics.sharpe_ratio  # type: ignore[assignment]

        destructive_pairs = detect_pairwise_destruction(single_sharpes, pair_sharpes)

        interference = InterferenceReport(
            degradation=degradation,
            negative_marginals=negative_marginals,
            destructive_pairs=destructive_pairs,
        )

        # Recommendations
        recommendations = self._compute_recommendations(
            single_sharpes=single_sharpes,
            negative_marginals=negative_marginals,
            destructive_pairs=destructive_pairs,
            shapley_values=shapley_values,
        )

        return StudyReport(
            single_baselines=single_baselines,
            pairwise_results=pairwise_results,
            incremental_stacks=incremental_stacks,
            full_stack=full_stack,
            interference=interference,
            shapley_values=shapley_values,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_coalition_cache(
        self,
        single_baselines: list[AblationResult],
        pairwise_results: list[AblationResult],
    ) -> dict[frozenset[str], float]:
        """Build a cache of coalition -> Sharpe from Phase 1 and Phase 2 results."""
        cache: dict[frozenset[str], float] = {}

        # Control (empty coalition)
        cache[frozenset()] = single_baselines[0].metrics.sharpe_ratio

        # Singles
        for r in single_baselines[1:]:
            key = frozenset(r.combination.enabled_filters)
            cache[key] = r.metrics.sharpe_ratio

        # Pairs
        for r in pairwise_results:
            key = frozenset(r.combination.enabled_filters)
            cache[key] = r.metrics.sharpe_ratio

        return cache

    def _compute_recommendations(
        self,
        single_sharpes: dict[str, float],
        negative_marginals: list,
        destructive_pairs: list,
        shapley_values: ShapleyResult,
    ) -> dict[str, str]:
        """Apply the decision framework to produce per-filter recommendations.

        Rules:
          - negative_marginal + low_shapley -> "remove"
          - destructive + positive_sv -> "merge"
          - negative_marginal + positive_sv -> "convert_to_scoring_input"
          - else -> "retain"
        """
        neg_marginal_names = {nm.filter_name for nm in negative_marginals}

        destructive_names: set[str] = set()
        for dp in destructive_pairs:
            destructive_names.add(dp.filter_a)
            destructive_names.add(dp.filter_b)

        sv = shapley_values.values
        median_sv = median(sv.values()) if sv else 0.0

        recommendations: dict[str, str] = {}
        for name in sorted(ALL_FILTER_NAMES):
            filter_sv = sv.get(name, 0.0)
            is_neg_marginal = name in neg_marginal_names
            is_destructive = name in destructive_names
            is_low_shapley = filter_sv < median_sv

            if is_neg_marginal and is_low_shapley:
                recommendations[name] = "remove"
            elif is_destructive and filter_sv > 0:
                recommendations[name] = "merge"
            elif is_neg_marginal and filter_sv > 0:
                recommendations[name] = "convert_to_scoring_input"
            else:
                recommendations[name] = "retain"

        return recommendations
