"""End-to-end integration tests for the complete ablation study pipeline.

Exercises all four phases (single baselines, pairwise combinations, incremental
stacking, Shapley values) plus interference detection and recommendation
generation.  These are the final validation tests for the ablation framework.
"""

from __future__ import annotations

from datetime import date

from margin_engine.ablation.runner import ALL_FILTER_NAMES, AblationConfig
from margin_engine.ablation.study import AblationStudy, StudyReport
from margin_engine.backtesting.factor_registry import FactorRegistry

from tests.backtesting.helpers import build_pit_provider_with_tickers

# 18 months of data with 5 tickers — enough variation for meaningful metrics.
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
START = date(2019, 1, 1)
END = date(2020, 6, 1)
BOOTSTRAP_RESAMPLES = 100  # Low for speed


def _build_study() -> AblationStudy:
    """Build an AblationStudy with synthetic PIT data for 5 tickers, 18 months."""
    config = AblationConfig(start_date=START, end_date=END)
    provider = build_pit_provider_with_tickers(TICKERS, START, END)
    registry = FactorRegistry.default()
    return AblationStudy(
        config=config,
        pit_provider=provider,
        factor_registry=registry,
        bootstrap_resamples=BOOTSTRAP_RESAMPLES,
    )


# ---------------------------------------------------------------------------
# Cache the expensive study run so both test classes share it.
# ---------------------------------------------------------------------------

_cached_report: StudyReport | None = None


def _get_report() -> StudyReport:
    global _cached_report
    if _cached_report is None:
        _cached_report = _build_study().run()
    return _cached_report


# ---------------------------------------------------------------------------
# Valid recommendation actions
# ---------------------------------------------------------------------------

VALID_ACTIONS = {"retain", "remove", "merge", "convert_to_scoring_input"}


class TestAblationStudyEndToEnd:
    """Run a full AblationStudy and verify every phase produces correct output."""

    # -- Phase 1: Single-filter baselines --

    def test_phase1_seven_single_baselines(self) -> None:
        """Phase 1 produces 7 results: 1 control + 6 single-filter baselines."""
        report = _get_report()
        assert len(report.single_baselines) == 7

    def test_phase1_first_is_control(self) -> None:
        """The first single baseline is the 'control' with no filters enabled."""
        report = _get_report()
        control = report.single_baselines[0]
        assert control.combination.name == "control"
        assert control.combination.enabled_filters == set()

    def test_phase1_remaining_are_single_filters(self) -> None:
        """The remaining 6 baselines each have exactly one filter enabled."""
        report = _get_report()
        names_seen: set[str] = set()
        for result in report.single_baselines[1:]:
            assert len(result.combination.enabled_filters) == 1
            names_seen.update(result.combination.enabled_filters)
        assert names_seen == ALL_FILTER_NAMES

    # -- Phase 2: Pairwise combinations --

    def test_phase2_fifteen_pairwise_results(self) -> None:
        """Phase 2 produces C(6,2) = 15 pairwise combination results."""
        report = _get_report()
        assert len(report.pairwise_results) == 15

    def test_phase2_all_pairs_have_two_filters(self) -> None:
        """Every pairwise result has exactly 2 enabled filters."""
        report = _get_report()
        for result in report.pairwise_results:
            assert len(result.combination.enabled_filters) == 2

    # -- Phase 3: Incremental stacking --

    def test_phase3_four_stacking_orderings(self) -> None:
        """Phase 3 produces 4 orderings: default, reverse, best_first, worst_first."""
        report = _get_report()
        expected_orderings = {"default", "reverse", "best_first", "worst_first"}
        assert set(report.incremental_stacks.keys()) == expected_orderings

    def test_phase3_each_ordering_has_seven_results(self) -> None:
        """Each incremental stack has 7 results (empty + 6 cumulative additions)."""
        report = _get_report()
        for ordering_name, stack in report.incremental_stacks.items():
            assert len(stack) == 7, (
                f"Ordering '{ordering_name}' has {len(stack)} results, expected 7"
            )

    def test_phase3_stacks_are_cumulative(self) -> None:
        """Each successive stack result is a superset of the previous one."""
        report = _get_report()
        for ordering_name, stack in report.incremental_stacks.items():
            prev_filters: set[str] = set()
            for result in stack:
                current_filters = result.combination.enabled_filters
                assert prev_filters.issubset(current_filters), (
                    f"Ordering '{ordering_name}': filters not cumulative at "
                    f"{result.combination.name}"
                )
                prev_filters = current_filters

    # -- Phase 4: Shapley values --

    def test_phase4_shapley_values_not_none(self) -> None:
        """Shapley values are computed (not None)."""
        report = _get_report()
        assert report.shapley_values is not None

    def test_phase4_shapley_has_six_entries(self) -> None:
        """Shapley values dict has one entry per filter (6 total)."""
        report = _get_report()
        assert report.shapley_values is not None
        assert len(report.shapley_values.values) == 6

    def test_phase4_shapley_covers_all_filters(self) -> None:
        """Shapley values cover every filter in ALL_FILTER_NAMES."""
        report = _get_report()
        assert report.shapley_values is not None
        assert set(report.shapley_values.values.keys()) == ALL_FILTER_NAMES

    def test_phase4_shapley_efficiency_axiom(self) -> None:
        """The efficiency axiom holds: sum(phi_i) = v(full) - v(empty) within 0.01.

        This is the fundamental mathematical identity that validates the Shapley
        computation.  If it doesn't hold, something is wrong with the coalition
        value function or the formula.
        """
        report = _get_report()
        assert report.shapley_values is not None

        # Sum of all Shapley values
        phi_sum = sum(report.shapley_values.values.values())

        # v(full) - v(empty) from coalition values
        coalition_vals = report.shapley_values.coalition_values
        v_full_key = ",".join(sorted(ALL_FILTER_NAMES))
        v_full = coalition_vals[v_full_key]
        v_empty = coalition_vals["(empty)"]

        expected_diff = v_full - v_empty

        assert abs(phi_sum - expected_diff) < 0.01, (
            f"Shapley efficiency axiom violated: sum(phi)={phi_sum:.6f}, "
            f"v(full)-v(empty)={expected_diff:.6f}, "
            f"diff={abs(phi_sum - expected_diff):.6f}"
        )

    # -- Detection --

    def test_interference_report_not_none(self) -> None:
        """The interference report is populated."""
        report = _get_report()
        assert report.interference is not None

    def test_degradation_result_present(self) -> None:
        """The degradation detection result is present in the interference report."""
        report = _get_report()
        assert report.interference.degradation is not None
        # The result should have the expected fields populated
        assert isinstance(report.interference.degradation.detected, bool)
        assert report.interference.degradation.best_single in ALL_FILTER_NAMES

    # -- Recommendations --

    def test_recommendations_has_six_entries(self) -> None:
        """Recommendations dict has one entry per filter."""
        report = _get_report()
        assert len(report.recommendations) == 6

    def test_recommendations_cover_all_filters(self) -> None:
        """Every filter in ALL_FILTER_NAMES appears in recommendations."""
        report = _get_report()
        for name in ALL_FILTER_NAMES:
            assert name in report.recommendations, (
                f"Filter '{name}' missing from recommendations"
            )

    def test_recommendations_all_valid_actions(self) -> None:
        """Every recommendation is one of the valid action strings."""
        report = _get_report()
        for name, action in report.recommendations.items():
            assert action in VALID_ACTIONS, (
                f"Filter '{name}' has invalid action '{action}'"
            )

    # -- Cross-phase consistency --

    def test_full_stack_matches_last_default_stack(self) -> None:
        """full_stack is the last result of the 'default' incremental stack."""
        report = _get_report()
        assert report.full_stack is not None
        default_stack = report.incremental_stacks["default"]
        last_default = default_stack[-1]
        assert report.full_stack.metrics.sharpe_ratio == last_default.metrics.sharpe_ratio

    def test_all_results_have_metrics(self) -> None:
        """Every result across all phases has populated metrics."""
        report = _get_report()
        all_results = (
            report.single_baselines
            + report.pairwise_results
            + [r for stack in report.incremental_stacks.values() for r in stack]
        )
        for result in all_results:
            assert result.metrics is not None
            assert result.metrics.sharpe_ratio is not None
            assert result.metrics.cagr is not None


class TestAblationPreservesDeterminism:
    """Run the same study twice with identical inputs and verify identical outputs.

    Determinism is a core design principle: same inputs must produce same outputs.
    """

    def test_same_sharpe_ratios_for_all_single_baselines(self) -> None:
        """Both runs produce identical Sharpe ratios for every single baseline."""
        study_a = _build_study()
        report_a = study_a.run()

        study_b = _build_study()
        report_b = study_b.run()

        assert len(report_a.single_baselines) == len(report_b.single_baselines)

        for result_a, result_b in zip(
            report_a.single_baselines, report_b.single_baselines
        ):
            assert result_a.combination.name == result_b.combination.name
            assert result_a.metrics.sharpe_ratio == result_b.metrics.sharpe_ratio, (
                f"Sharpe mismatch for '{result_a.combination.name}': "
                f"{result_a.metrics.sharpe_ratio} != {result_b.metrics.sharpe_ratio}"
            )

    def test_same_shapley_values(self) -> None:
        """Both runs produce identical Shapley values (within 1e-10 tolerance)."""
        study_a = _build_study()
        report_a = study_a.run()

        study_b = _build_study()
        report_b = study_b.run()

        assert report_a.shapley_values is not None
        assert report_b.shapley_values is not None

        for name in ALL_FILTER_NAMES:
            val_a = report_a.shapley_values.values[name]
            val_b = report_b.shapley_values.values[name]
            assert abs(val_a - val_b) < 1e-10, (
                f"Shapley value mismatch for '{name}': {val_a} != {val_b}"
            )

    def test_same_recommendations(self) -> None:
        """Both runs produce identical recommendation dicts."""
        study_a = _build_study()
        report_a = study_a.run()

        study_b = _build_study()
        report_b = study_b.run()

        assert report_a.recommendations == report_b.recommendations
