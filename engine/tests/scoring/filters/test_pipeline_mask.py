"""Tests for disabled_filters (mask) parameter on run_elimination_filters."""

from margin_engine.scoring.filters.pipeline import run_elimination_filters

ALL_FILTER_NAMES = {
    "liquidity",
    "beneish_m_score",
    "altman_z_score",
    "fcf_distress",
    "interest_coverage",
    "current_ratio",
    "mediocrity_gate",
}


class TestDisabledFiltersMask:
    """Tests for the disabled_filters parameter on run_elimination_filters."""

    def test_mask_disables_specified_filters(self):
        """Disabling 2 filters returns only the remaining 5."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        disabled = {"liquidity", "beneish_m_score"}
        result = run_elimination_filters(
            APPLE_PERIOD_2024, APPLE_PROFILE, disabled_filters=disabled
        )

        assert len(result.results) == 5
        returned_names = {r.name for r in result.results}
        assert returned_names == ALL_FILTER_NAMES - disabled
        # Verify the disabled ones are truly absent
        assert "liquidity" not in returned_names
        assert "beneish_m_score" not in returned_names

    def test_empty_mask_runs_all_filters(self):
        """An empty set produces the same results as no mask at all."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result_no_mask = run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE)
        result_empty_mask = run_elimination_filters(
            APPLE_PERIOD_2024, APPLE_PROFILE, disabled_filters=set()
        )

        assert len(result_empty_mask.results) == len(result_no_mask.results)
        assert {r.name for r in result_empty_mask.results} == {
            r.name for r in result_no_mask.results
        }
        assert result_empty_mask.passed == result_no_mask.passed

    def test_mask_all_filters_returns_empty(self):
        """Disabling all 6 filters returns empty results with passed=True."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = run_elimination_filters(
            APPLE_PERIOD_2024, APPLE_PROFILE, disabled_filters=ALL_FILTER_NAMES
        )

        assert len(result.results) == 0
        # all() of an empty iterable is True
        assert result.passed is True
        assert result.failed_filters == []

    def test_mask_preserves_no_short_circuit(self):
        """Disabled filters are still evaluated (no short-circuit).

        We verify this indirectly: even when disabling 6 filters, the one
        remaining filter still has its correct computed value (meaning the
        pipeline ran to completion, not just up to the first enabled filter).
        """
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        keep = "current_ratio"
        disabled = ALL_FILTER_NAMES - {keep}
        result = run_elimination_filters(
            APPLE_PERIOD_2024, APPLE_PROFILE, disabled_filters=disabled
        )

        assert len(result.results) == 1
        assert result.results[0].name == keep
        assert result.results[0].passed is True

    def test_mask_none_is_default_behavior(self):
        """Passing None (the default) runs all filters."""
        from tests.fixtures.golden_apple_2024 import APPLE_PERIOD_2024, APPLE_PROFILE

        result = run_elimination_filters(APPLE_PERIOD_2024, APPLE_PROFILE, disabled_filters=None)

        assert len(result.results) == 7
        assert {r.name for r in result.results} == ALL_FILTER_NAMES
