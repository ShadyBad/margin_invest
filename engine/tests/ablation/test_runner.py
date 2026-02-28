"""Tests for ablation runner — single-filter baselines and pairwise combinations."""

from __future__ import annotations

from datetime import date

from margin_engine.ablation.runner import (
    ALL_FILTER_NAMES,
    AblationConfig,
    AblationRunner,
)
from margin_engine.backtesting.factor_registry import FactorRegistry

from tests.backtesting.helpers import build_pit_provider_with_tickers

# Short date range — 3 months keeps tests fast while exercising the pipeline.
START = date(2020, 1, 1)
END = date(2020, 3, 1)
TICKERS = ["AAPL", "MSFT", "GOOGL"]


def _make_runner() -> AblationRunner:
    """Build an AblationRunner with synthetic PIT data."""
    config = AblationConfig(start_date=START, end_date=END)
    provider = build_pit_provider_with_tickers(TICKERS, START, END)
    registry = FactorRegistry.default()
    return AblationRunner(
        config=config,
        pit_provider=provider,
        factor_registry=registry,
    )


class TestSingleFilterBaselines:
    """Tests for run_single_filter_baselines."""

    def test_single_filter_baselines(self) -> None:
        """Returns 7 results: control (empty enabled set) + 6 single filters."""
        runner = _make_runner()
        results = runner.run_single_filter_baselines()

        assert len(results) == 7, f"Expected 7 results, got {len(results)}"

        # First result is the control with no filters enabled
        control = results[0]
        assert control.combination.name == "control"
        assert control.combination.enabled_filters == set()
        assert control.combination.disabled_filters == ALL_FILTER_NAMES

        # Remaining 6 results each have exactly 1 filter enabled
        single_names = set()
        for r in results[1:]:
            assert len(r.combination.enabled_filters) == 1, (
                f"Expected 1 enabled filter, got {r.combination.enabled_filters}"
            )
            single_names.update(r.combination.enabled_filters)

        # All 6 filter names are covered
        assert single_names == ALL_FILTER_NAMES


class TestPairwiseCombinations:
    """Tests for run_pairwise_combinations."""

    def test_pairwise_combinations(self) -> None:
        """Returns 15 results, each with exactly 2 enabled filters."""
        runner = _make_runner()
        results = runner.run_pairwise_combinations()

        assert len(results) == 15, f"Expected 15 results, got {len(results)}"

        seen_pairs: set[frozenset[str]] = set()
        for r in results:
            assert len(r.combination.enabled_filters) == 2, (
                f"Expected 2 enabled filters, got {r.combination.enabled_filters}"
            )
            pair = frozenset(r.combination.enabled_filters)
            assert pair not in seen_pairs, f"Duplicate pair: {pair}"
            seen_pairs.add(pair)

        # All pairs should come from ALL_FILTER_NAMES
        for pair in seen_pairs:
            assert pair.issubset(ALL_FILTER_NAMES)


class TestAblationResultMetrics:
    """Tests for AblationResult metric population."""

    def test_ablation_result_has_metrics(self) -> None:
        """Each result has sharpe_ratio, cagr, and survivor_counts."""
        runner = _make_runner()
        results = runner.run_single_filter_baselines()

        for r in results:
            # Metrics are populated (may be zero for short runs, but must exist)
            assert r.metrics.sharpe_ratio is not None
            assert r.metrics.cagr is not None

            # Survivor counts are populated — one entry per rebalance
            assert len(r.survivor_counts) > 0, f"Expected survivor_counts for {r.combination.name}"

            # Monthly returns match snapshot count
            assert len(r.monthly_returns) == len(r.survivor_counts)
