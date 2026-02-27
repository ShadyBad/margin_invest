"""Tests for the full ablation study orchestrator."""

from __future__ import annotations

from datetime import date

from margin_engine.ablation.runner import ALL_FILTER_NAMES, AblationConfig
from margin_engine.ablation.study import AblationStudy, StudyReport
from margin_engine.backtesting.factor_registry import FactorRegistry

from tests.backtesting.helpers import build_pit_provider_with_tickers

# Short date range — 3 months keeps tests fast while exercising the pipeline.
START = date(2020, 1, 1)
END = date(2020, 3, 1)
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "JNJ"]


def _make_study() -> AblationStudy:
    """Build an AblationStudy with synthetic PIT data."""
    config = AblationConfig(start_date=START, end_date=END)
    provider = build_pit_provider_with_tickers(TICKERS, START, END)
    registry = FactorRegistry.default()
    return AblationStudy(
        config=config,
        pit_provider=provider,
        factor_registry=registry,
        bootstrap_resamples=100,  # low count for speed
    )


def _run_study() -> StudyReport:
    """Run the full study and return the report (cached via module-level)."""
    study = _make_study()
    return study.run()


# Cache the report across tests to avoid re-running the expensive study.
_cached_report: StudyReport | None = None


def _get_report() -> StudyReport:
    global _cached_report
    if _cached_report is None:
        _cached_report = _run_study()
    return _cached_report


class TestFullStudyProducesReport:
    """Verify the complete study report structure and counts."""

    def test_seven_single_baselines(self) -> None:
        """Phase 1 produces 7 results: control + 6 single filters."""
        report = _get_report()
        assert len(report.single_baselines) == 7

    def test_control_is_first_baseline(self) -> None:
        """First single baseline is the control (no filters enabled)."""
        report = _get_report()
        control = report.single_baselines[0]
        assert control.combination.name == "control"
        assert control.combination.enabled_filters == set()

    def test_fifteen_pairwise_results(self) -> None:
        """Phase 2 produces 15 pairwise combination results."""
        report = _get_report()
        assert len(report.pairwise_results) == 15

    def test_four_stacking_orderings(self) -> None:
        """Phase 3 produces 4 orderings."""
        report = _get_report()
        assert set(report.incremental_stacks.keys()) == {
            "default",
            "reverse",
            "best_first",
            "worst_first",
        }

    def test_each_stack_has_seven_results(self) -> None:
        """Each incremental stack ordering has 7 results (empty + 6 filters)."""
        report = _get_report()
        for ordering_name, stack in report.incremental_stacks.items():
            assert len(stack) == 7, (
                f"Ordering '{ordering_name}' has {len(stack)} results, expected 7"
            )

    def test_shapley_values_not_none(self) -> None:
        """Phase 4 produces ShapleyResult with 6 filter entries."""
        report = _get_report()
        assert report.shapley_values is not None
        assert len(report.shapley_values.values) == 6

    def test_shapley_values_cover_all_filters(self) -> None:
        """Shapley values have an entry for every filter."""
        report = _get_report()
        assert report.shapley_values is not None
        assert set(report.shapley_values.values.keys()) == ALL_FILTER_NAMES

    def test_interference_not_none(self) -> None:
        """Interference report is populated."""
        report = _get_report()
        assert report.interference is not None
        assert report.interference.degradation is not None

    def test_recommendations_has_six_entries(self) -> None:
        """Recommendations dict has one entry per filter."""
        report = _get_report()
        assert len(report.recommendations) == 6

    def test_full_stack_populated(self) -> None:
        """Full stack result is populated (last entry of default stack)."""
        report = _get_report()
        assert report.full_stack is not None
        assert report.full_stack.metrics is not None


class TestStudyReportHasRecommendations:
    """Every filter in ALL_FILTER_NAMES appears in recommendations with a valid action."""

    VALID_ACTIONS = {"remove", "merge", "convert_to_scoring_input", "retain"}

    def test_every_filter_has_recommendation(self) -> None:
        """Every filter name appears in the recommendations dict."""
        report = _get_report()
        for name in ALL_FILTER_NAMES:
            assert name in report.recommendations, (
                f"Filter '{name}' missing from recommendations"
            )

    def test_all_actions_are_valid(self) -> None:
        """Every recommendation action is one of the valid action strings."""
        report = _get_report()
        for name, action in report.recommendations.items():
            assert action in self.VALID_ACTIONS, (
                f"Filter '{name}' has invalid action '{action}'"
            )
