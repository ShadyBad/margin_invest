"""Ablation runner — executes backtest variants with different filter combinations.

Wraps ReplayOrchestrator to systematically test single-filter baselines,
pairwise combinations, and incremental filter stacks.  Each run disables
all filters except those in the requested combination, producing comparable
PerformanceMetrics and survivor-count timelines.
"""

from __future__ import annotations

import itertools
from datetime import date

from pydantic import BaseModel, Field

from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.models import PerformanceMetrics
from margin_engine.backtesting.pit_provider import PointInTimeProvider
from margin_engine.backtesting.replay_orchestrator import ReplayConfig, ReplayOrchestrator
from margin_engine.regime.classifier import MultiDimensionalRegimeClassifier
from margin_engine.regime.models import RegimeState

ALL_FILTER_NAMES: set[str] = {
    "liquidity",
    "beneish_m_score",
    "altman_z_score",
    "fcf_distress",
    "interest_coverage",
    "current_ratio",
}

# Default order for incremental stacking: liquidity first (broadest screen),
# then increasingly specific financial-health filters.
DEFAULT_STACK_ORDER: list[str] = [
    "liquidity",
    "beneish_m_score",
    "altman_z_score",
    "fcf_distress",
    "interest_coverage",
    "current_ratio",
]


class FilterCombination(BaseModel):
    """A named set of enabled elimination filters."""

    name: str
    enabled_filters: set[str]

    @property
    def disabled_filters(self) -> set[str]:
        """Filters NOT in this combination (to be disabled during replay)."""
        return ALL_FILTER_NAMES - self.enabled_filters


class AblationConfig(BaseModel):
    """Configuration controlling every replay variant in an ablation study."""

    start_date: date = Field(default=date(2006, 1, 1))
    end_date: date = Field(default_factory=date.today)
    rebalance_frequency: str = "monthly"
    conviction_threshold: float = 0.10
    weighting: str = "equal"
    transaction_cost_bps: float = 20.0


class AblationResult(BaseModel):
    """Output of a single ablation variant run."""

    combination: FilterCombination
    metrics: PerformanceMetrics
    survivor_counts: list[int] = Field(default_factory=list)
    monthly_returns: list[float] = Field(default_factory=list)
    regime_tags: list[RegimeState] = Field(default_factory=list)


class AblationRunner:
    """Executes backtest variants with different filter combinations.

    Each public method produces a list of AblationResult by running the
    ReplayOrchestrator with different ``disabled_filters`` sets.  The runner
    is stateless across calls — every run builds a fresh orchestrator.
    """

    def __init__(
        self,
        config: AblationConfig,
        pit_provider: PointInTimeProvider,
        factor_registry: FactorRegistry,
        benchmark_prices: dict[date, float] | None = None,
        regime_classifier: MultiDimensionalRegimeClassifier | None = None,
    ) -> None:
        self._config = config
        self._provider = pit_provider
        self._registry = factor_registry
        self._benchmark_prices = benchmark_prices
        self._regime_classifier = regime_classifier

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_single_filter_baselines(self) -> list[AblationResult]:
        """Run control (no filters) plus each filter in isolation.

        Returns 7 results:
          - Run 0: control — ALL filters disabled (empty enabled set)
          - Runs 1-6: each of the 6 filters enabled alone
        """
        results: list[AblationResult] = []

        # Control: no filters enabled at all
        control = FilterCombination(name="control", enabled_filters=set())
        results.append(self.run_combination(control))

        # Each filter in isolation
        for name in sorted(ALL_FILTER_NAMES):
            combo = FilterCombination(name=name, enabled_filters={name})
            results.append(self.run_combination(combo))

        return results

    def run_pairwise_combinations(self) -> list[AblationResult]:
        """Run all C(6, 2) = 15 pairwise filter combinations.

        Returns 15 results, one for each unique pair.
        """
        results: list[AblationResult] = []
        for pair in itertools.combinations(sorted(ALL_FILTER_NAMES), 2):
            combo_name = "+".join(pair)
            combo = FilterCombination(name=combo_name, enabled_filters=set(pair))
            results.append(self.run_combination(combo))
        return results

    def run_incremental_stack(
        self, order: list[str] | None = None
    ) -> list[AblationResult]:
        """Run cumulative filter additions in the given order.

        Returns N+1 results (7 for the default 6 filters):
          - Run 0: empty set (no filters)
          - Run 1: first filter only
          - Run 2: first + second
          - ...
          - Run N: all filters enabled

        Args:
            order: Filter addition order. Defaults to DEFAULT_STACK_ORDER.
        """
        if order is None:
            order = list(DEFAULT_STACK_ORDER)

        results: list[AblationResult] = []
        cumulative: set[str] = set()

        # Run 0: empty set
        combo = FilterCombination(name="empty", enabled_filters=set())
        results.append(self.run_combination(combo))

        # Cumulative additions
        for name in order:
            cumulative = cumulative | {name}
            combo_name = "+".join(sorted(cumulative))
            combo = FilterCombination(name=combo_name, enabled_filters=set(cumulative))
            results.append(self.run_combination(combo))

        return results

    def run_combination(self, combination: FilterCombination) -> AblationResult:
        """Run a single backtest with the given filter combination.

        Builds a ReplayOrchestrator with ``disabled_filters`` set to
        everything NOT in ``combination.enabled_filters``, runs it, and
        extracts metrics, survivor counts, and monthly returns.
        """
        replay_config = ReplayConfig(
            start_date=self._config.start_date,
            end_date=self._config.end_date,
            rebalance_frequency=self._config.rebalance_frequency,
            conviction_threshold=self._config.conviction_threshold,
            weighting=self._config.weighting,
            transaction_cost_bps=self._config.transaction_cost_bps,
        )

        orchestrator = ReplayOrchestrator(
            config=replay_config,
            pit_provider=self._provider,
            factor_registry=self._registry,
            benchmark_prices=self._benchmark_prices,
            disabled_filters=combination.disabled_filters,
            regime_classifier=self._regime_classifier,
        )

        result = orchestrator.run()

        # Extract survivor counts from audit log
        survivor_counts = [record.survivor_count for record in result.audit_log]

        # Extract monthly portfolio returns from snapshots
        monthly_returns = [snap.portfolio_return for snap in result.snapshots]

        # Extract regime tags from audit records
        regime_tags = [
            rec.regime_state for rec in result.audit_log if rec.regime_state is not None
        ]

        return AblationResult(
            combination=combination,
            metrics=result.metrics,
            survivor_counts=survivor_counts,
            monthly_returns=monthly_returns,
            regime_tags=regime_tags,
        )
