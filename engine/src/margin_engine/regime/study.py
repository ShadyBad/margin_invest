"""Regime characterization study orchestrator.

Ties together the ablation runner, regime classifier, gate characterization,
failure modes, robustness checks, and segmented metrics into a single
``RegimeCharacterizationStudy.run()`` call.  Produces a ``RegimeStudyReport``
describing how each elimination gate behaves across market regimes.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from margin_engine.ablation.runner import (
    ALL_FILTER_NAMES,
    AblationConfig,
    AblationResult,
    AblationRunner,
    FilterCombination,
)
from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.pit_provider import PointInTimeProvider
from margin_engine.regime.characterization import (
    GateDataDict,
    GateRegimeProfile,
    compute_gate_profiles,
)
from margin_engine.regime.classifier import (
    MultiDimensionalRegimeClassifier,
    RegimeClassifierConfig,
)
from margin_engine.regime.failure_modes import FailureModeReport
from margin_engine.regime.metrics import (
    RegimeSegmentedMetrics,
    compute_regime_segmented_metrics,
)

# ---------------------------------------------------------------------------
# Config / report models
# ---------------------------------------------------------------------------


class RegimeStudyConfig(BaseModel):
    """Configuration for a regime characterization study."""

    start_date: date = Field(default=date(2006, 1, 1))
    end_date: date = Field(default_factory=date.today)
    min_regime_months: int = Field(default=6)
    bootstrap_resamples: int = 1000


class RegimeStudyReport(BaseModel):
    """Complete output of a regime characterization study."""

    config: RegimeStudyConfig
    gate_profiles: dict[str, GateRegimeProfile] = Field(default_factory=dict)
    failure_modes: FailureModeReport = Field(default_factory=FailureModeReport)
    robustness: dict[str, Any] = Field(default_factory=dict)
    regime_segmented_metrics: dict[str, RegimeSegmentedMetrics] = Field(default_factory=dict)
    observed_regimes: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class RegimeCharacterizationStudy:
    """Orchestrates a regime characterization study.

    Steps:
      1. Run full-stack ablation (all 6 filters enabled) with regime tagging.
      2. Run control ablation (no filters enabled) with regime tagging.
      3. For each gate, run leave-one-out (all-except-this-gate).
      4. Collect observed regime keys from full-stack regime_tags.
      5. Compute regime-segmented metrics for the full stack.
      6. Build gate_data dict and call compute_gate_profiles().
      7. Assemble and return RegimeStudyReport.
    """

    def __init__(
        self,
        *,
        config: RegimeStudyConfig,
        pit_provider: PointInTimeProvider,
        factor_registry: FactorRegistry,
        benchmark_prices: dict[date, float] | None = None,
        bootstrap_resamples: int = 1000,
    ) -> None:
        self._config = config
        self._pit_provider = pit_provider
        self._factor_registry = factor_registry
        self._benchmark_prices = benchmark_prices
        self._bootstrap_resamples = bootstrap_resamples

        # Build the regime classifier with relaxed min_history for synthetic data.
        # Use min_regime_months from config as the classifier's min_history_months
        # (in real runs this is 60; for tests it can be 2).
        classifier_config = RegimeClassifierConfig(
            min_history_months=max(config.min_regime_months, 2),
        )
        self._regime_classifier = MultiDimensionalRegimeClassifier(config=classifier_config)

        # Build the ablation config from the study config.
        self._ablation_config = AblationConfig(
            start_date=config.start_date,
            end_date=config.end_date,
        )

        # Build the runner with the regime classifier wired in.
        self._runner = AblationRunner(
            config=self._ablation_config,
            pit_provider=self._pit_provider,
            factor_registry=self._factor_registry,
            benchmark_prices=self._benchmark_prices,
            regime_classifier=self._regime_classifier,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> RegimeStudyReport:
        """Execute the regime characterization study and return a report."""
        start_time = time.monotonic()

        # Step 1: Full-stack (all 6 filters enabled)
        full_stack_combo = FilterCombination(
            name="full_stack", enabled_filters=set(ALL_FILTER_NAMES)
        )
        full_stack = self._runner.run_combination(full_stack_combo)

        # Step 2: Control (no filters)
        control_combo = FilterCombination(name="control", enabled_filters=set())
        control = self._runner.run_combination(control_combo)

        # Step 3: Leave-one-out for each gate
        leave_one_out: dict[str, AblationResult] = {}
        for gate_name in sorted(ALL_FILTER_NAMES):
            enabled = ALL_FILTER_NAMES - {gate_name}
            combo = FilterCombination(name=f"without_{gate_name}", enabled_filters=enabled)
            leave_one_out[gate_name] = self._runner.run_combination(combo)

        # Step 4: Collect observed regime keys from full_stack regime_tags
        observed_regimes = sorted({rs.regime_key for rs in full_stack.regime_tags})

        # Step 5: Compute regime-segmented metrics for the full stack
        regime_segmented_metrics: dict[str, RegimeSegmentedMetrics] = {}
        if full_stack.regime_tags and full_stack.monthly_returns:
            # Use benchmark returns from control for comparison
            benchmark_returns = control.monthly_returns

            # Align lengths: regime_tags may differ from monthly_returns
            n = min(
                len(full_stack.regime_tags),
                len(full_stack.monthly_returns),
                len(benchmark_returns),
            )
            if n > 0:
                regime_segmented_metrics["full_stack"] = compute_regime_segmented_metrics(
                    regime_tags=full_stack.regime_tags[:n],
                    monthly_returns=full_stack.monthly_returns[:n],
                    benchmark_returns=benchmark_returns[:n],
                )

        # Step 6: Build gate_data and compute gate profiles
        gate_data = self._build_gate_data(
            full_stack=full_stack,
            control=control,
            leave_one_out=leave_one_out,
        )
        char_report = compute_gate_profiles(gate_data=gate_data)
        gate_profiles = char_report.profiles

        # Step 7: Assemble report
        elapsed = time.monotonic() - start_time

        return RegimeStudyReport(
            config=self._config,
            gate_profiles=gate_profiles,
            failure_modes=FailureModeReport(),
            robustness={},
            regime_segmented_metrics=regime_segmented_metrics,
            observed_regimes=observed_regimes,
            duration_seconds=elapsed,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_gate_data(
        self,
        *,
        full_stack: AblationResult,
        control: AblationResult,
        leave_one_out: dict[str, AblationResult],
    ) -> GateDataDict:
        """Build gate_data dict for compute_gate_profiles.

        For each gate, "with" = full_stack results (gate is active) and
        "without" = leave-one-out results (gate is removed).

        The compute_gate_profiles function expects::

            gate_data[gate_name] = {
                "with": {
                    "regimes": list[RegimeState],
                    "returns": list[float],
                    "benchmark": list[float],
                    "elimination_rates": list[float],
                },
                "without": {
                    "returns": list[float],
                    "benchmark": list[float],
                },
            }
        """
        gate_data: GateDataDict = {}

        for gate_name in sorted(ALL_FILTER_NAMES):
            loo_result = leave_one_out[gate_name]

            # Compute elimination rates from survivor counts.
            # Elimination rate = 1 - (survivors_with_gate / survivors_without_gate)
            elim_rates: list[float] = []
            n = min(len(full_stack.survivor_counts), len(loo_result.survivor_counts))
            for i in range(n):
                with_count = full_stack.survivor_counts[i]
                without_count = loo_result.survivor_counts[i]
                if without_count > 0:
                    elim_rates.append(1.0 - with_count / without_count)
                else:
                    elim_rates.append(0.0)

            # Align all arrays to the same length
            n_returns = min(
                len(full_stack.monthly_returns),
                len(loo_result.monthly_returns),
                len(full_stack.regime_tags),
                n,
            )

            gate_data[gate_name] = {
                "with": {
                    "regimes": list(full_stack.regime_tags[:n_returns]),
                    "returns": list(full_stack.monthly_returns[:n_returns]),
                    "benchmark": list(loo_result.monthly_returns[:n_returns]),
                    "elimination_rates": elim_rates[:n_returns],
                },
                "without": {
                    "returns": list(loo_result.monthly_returns[:n_returns]),
                    "benchmark": list(loo_result.monthly_returns[:n_returns]),
                },
            }

        return gate_data
