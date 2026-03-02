"""Tests for the Institutional Accumulation (Smart Money) factor."""

import pytest
from margin_engine.models.financial import InstitutionalHolding
from margin_engine.models.scoring import FactorScore
from margin_engine.scoring.quantitative.institutional_accumulation import (
    institutional_accumulation,
)


def _make_holding(
    fund_name: str,
    quarter: str,
    shares_held: int = 100_000,
    shares_changed: int = 0,
    *,
    is_new_position: bool = False,
) -> InstitutionalHolding:
    """Helper to build an InstitutionalHolding."""
    return InstitutionalHolding(
        fund_name=fund_name,
        quarter=quarter,
        shares_held=shares_held,
        shares_changed=shares_changed,
        is_new_position=is_new_position,
    )


class TestStrongAccumulation:
    """Tests for strong accumulation signals (new positions + additions)."""

    def test_multiple_new_positions_and_additions(self):
        """Multiple new positions (+3 each) and additions (+1 each) with size weighting.

        Position sizes: [50K, 30K, 10K, 5K], median=20K
        Weights: [2.5, 1.5, 0.5, 0.25]
        Score = 3*2.5 + 3*1.5 + 1*0.5 + 1*0.25 = 12.75
        """
        holdings = [
            _make_holding("Berkshire", "2024-Q3", shares_changed=50_000, is_new_position=True),
            _make_holding("Bridgewater", "2024-Q3", shares_changed=30_000, is_new_position=True),
            _make_holding("Citadel", "2024-Q3", shares_changed=10_000),
            _make_holding("DE Shaw", "2024-Q3", shares_changed=5_000),
        ]
        result = institutional_accumulation(holdings)
        assert result.raw_value == 12.75

    def test_all_new_positions(self):
        """Three new positions = +9."""
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=100, is_new_position=True),
            _make_holding("Fund B", "2024-Q3", shares_changed=200, is_new_position=True),
            _make_holding("Fund C", "2024-Q3", shares_changed=300, is_new_position=True),
        ]
        result = institutional_accumulation(holdings)
        assert result.raw_value == 9.0


class TestNewPositionWeighting:
    """Tests verifying new positions are weighted 3x vs additions."""

    def test_new_position_worth_three_additions(self):
        """1 new position (+3) should equal 3 additions (+1 each)."""
        one_new = [
            _make_holding("Fund A", "2024-Q3", shares_changed=100, is_new_position=True),
        ]
        three_additions = [
            _make_holding("Fund A", "2024-Q3", shares_changed=100),
            _make_holding("Fund B", "2024-Q3", shares_changed=200),
            _make_holding("Fund C", "2024-Q3", shares_changed=300),
        ]
        result_new = institutional_accumulation(one_new)
        result_add = institutional_accumulation(three_additions)
        assert result_new.raw_value == result_add.raw_value == 3.0

    def test_single_new_position_vs_single_addition(self):
        """A new position scores 3 while an addition scores 1."""
        new_pos = [
            _make_holding("Fund A", "2024-Q3", shares_changed=100, is_new_position=True),
        ]
        addition = [
            _make_holding("Fund A", "2024-Q3", shares_changed=100),
        ]
        assert institutional_accumulation(new_pos).raw_value == 3.0
        assert institutional_accumulation(addition).raw_value == 1.0


class TestNetReduction:
    """Tests for net reduction scenarios (more sellers than buyers)."""

    def test_all_reductions(self):
        """Three funds all reducing with size weighting.

        Sizes: [50K, 30K, 10K], median=30K
        Weights: [5/3, 1.0, 1/3]
        Score = -1*(5/3) + -1*1.0 + -1*(1/3) = -3.0
        """
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=-50_000),
            _make_holding("Fund B", "2024-Q3", shares_changed=-30_000),
            _make_holding("Fund C", "2024-Q3", shares_changed=-10_000),
        ]
        result = institutional_accumulation(holdings)
        assert result.raw_value == pytest.approx(-3.0)

    def test_more_reducers_than_accumulators(self):
        """1 addition and 3 reductions with size weighting.

        Sizes: [10K, 20K, 15K, 5K], median=12.5K
        Weights: [0.8, 1.6, 1.2, 0.4]
        Score = 1*0.8 + -1*1.6 + -1*1.2 + -1*0.4 = -2.4
        """
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=10_000),
            _make_holding("Fund B", "2024-Q3", shares_changed=-20_000),
            _make_holding("Fund C", "2024-Q3", shares_changed=-15_000),
            _make_holding("Fund D", "2024-Q3", shares_changed=-5_000),
        ]
        result = institutional_accumulation(holdings)
        assert result.raw_value == pytest.approx(-2.4)


class TestMixedQuarters:
    """Tests for filtering to the most recent quarter only."""

    def test_only_most_recent_quarter_used(self):
        """Holdings from older quarters should be ignored.

        Q2 data: 2 reductions => would be -2 if counted
        Q3 data: 1 new position => +3
        Only Q3 should be used => net = +3
        """
        holdings = [
            _make_holding("Fund A", "2024-Q2", shares_changed=-50_000),
            _make_holding("Fund B", "2024-Q2", shares_changed=-30_000),
            _make_holding("Fund C", "2024-Q3", shares_changed=10_000, is_new_position=True),
        ]
        result = institutional_accumulation(holdings)
        assert result.raw_value == 3.0

    def test_three_quarters_uses_latest(self):
        """With Q1, Q2, and Q3 data, only Q3 is used.

        Q3 holdings: [10K, -5K], sizes=[10K, 5K], median=7500
        Weights: 10K/7500=4/3, 5K/7500=2/3
        Score = 1*(4/3) + -1*(2/3) = 2/3 ≈ 0.6667
        """
        holdings = [
            _make_holding("Fund A", "2024-Q1", shares_changed=100_000, is_new_position=True),
            _make_holding("Fund B", "2024-Q2", shares_changed=50_000),
            _make_holding("Fund C", "2024-Q3", shares_changed=10_000),
            _make_holding("Fund D", "2024-Q3", shares_changed=-5_000),
        ]
        result = institutional_accumulation(holdings)
        assert result.raw_value == pytest.approx(2 / 3)

    def test_quarter_sorting_lexicographic(self):
        """Quarter strings sort correctly: 2023-Q4 < 2024-Q1 < 2024-Q3."""
        holdings = [
            _make_holding("Fund A", "2023-Q4", shares_changed=-100_000),
            _make_holding("Fund B", "2024-Q1", shares_changed=-50_000),
            _make_holding("Fund C", "2024-Q3", shares_changed=20_000, is_new_position=True),
        ]
        result = institutional_accumulation(holdings)
        # Only Q3 data: 1 new position => +3
        assert result.raw_value == 3.0


class TestEmptyList:
    """Tests for empty input."""

    def test_empty_list_returns_zero(self):
        """Empty holdings list returns raw_value=0.0."""
        result = institutional_accumulation([])
        assert result.raw_value == 0.0

    def test_empty_list_detail(self):
        """Empty list should produce an informative detail message."""
        result = institutional_accumulation([])
        assert result.detail != ""


class TestAllNoChange:
    """Tests for holdings with no share changes."""

    def test_all_no_change_scores_zero(self):
        """All funds with shares_changed=0 => net score = 0."""
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=0),
            _make_holding("Fund B", "2024-Q3", shares_changed=0),
            _make_holding("Fund C", "2024-Q3", shares_changed=0),
        ]
        result = institutional_accumulation(holdings)
        assert result.raw_value == 0.0

    def test_mixed_no_change_and_activity(self):
        """No-change funds don't affect score; only active funds count.

        1 addition (+1), 2 no-change (0) => net = +1
        """
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=5_000),
            _make_holding("Fund B", "2024-Q3", shares_changed=0),
            _make_holding("Fund C", "2024-Q3", shares_changed=0),
        ]
        result = institutional_accumulation(holdings)
        assert result.raw_value == 1.0


class TestPositionSizeWeighting:
    """Tests for position-size weighting behavior."""

    def test_single_holding_weight_is_one(self):
        """A single holding always gets size_weight=1.0 (median = itself)."""
        small = [
            _make_holding("Small Fund", "2024-Q3", shares_changed=1_000, is_new_position=True),
        ]
        large = [
            _make_holding("Large Fund", "2024-Q3", shares_changed=1_000_000, is_new_position=True),
        ]
        # Both single holdings => weight = 1.0 => score = 3.0 each
        assert institutional_accumulation(small).raw_value == 3.0
        assert institutional_accumulation(large).raw_value == 3.0

    def test_large_position_amplifies_within_group(self):
        """Within a group, larger positions get higher weight."""
        holdings = [
            _make_holding("Small Fund", "2024-Q3", shares_changed=1_000, is_new_position=True),
            _make_holding("Large Fund", "2024-Q3", shares_changed=1_000_000, is_new_position=True),
        ]
        result = institutional_accumulation(holdings)
        # median = (1_000 + 1_000_000) / 2 = 500_500
        # small weight = 1_000 / 500_500 ≈ 0.002, large weight = 1_000_000 / 500_500 ≈ 1.998
        # score = 3 * 0.002 + 3 * 1.998 ≈ 6.0
        # The large position dominates — score is above a single fund's 3.0
        assert result.raw_value > 3.0

    def test_size_weight_capped_at_five(self):
        """Size weight is capped at 5x to prevent outlier dominance.

        Holdings: [10, 10_000_000]. Median = 5_000_005.
        Small weight = 10 / 5_000_005 ≈ 0.000002 (uncapped)
        Large weight = 10_000_000 / 5_000_005 ≈ 2.0 (uncapped, under 5)
        But if median were much smaller, e.g. [1, 1_000_000]:
        median = 500_000.5, large weight = ~2.0, still under cap.
        To trigger cap: [1, 1, 1, 1, 1_000_000] median=1, large=1M/1=1M → capped at 5.
        """
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=1),
            _make_holding("Fund B", "2024-Q3", shares_changed=1),
            _make_holding("Fund C", "2024-Q3", shares_changed=1),
            _make_holding("Fund D", "2024-Q3", shares_changed=1),
            _make_holding("Fund E", "2024-Q3", shares_changed=1_000_000, is_new_position=True),
        ]
        result = institutional_accumulation(holdings)
        # median = 1 (5 values: [1,1,1,1,1000000], median=1)
        # Weights: 4 additions at min(1/1, 5)=1.0 each, 1 new at min(1000000/1, 5)=5.0
        # Score = 4*(1*1.0) + 1*(3*5.0) = 4 + 15 = 19.0
        assert result.raw_value == 19.0

    def test_equal_sizes_produce_unweighted_result(self):
        """When all holdings have the same size, weights are all 1.0 (same as unweighted)."""
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=10_000, is_new_position=True),
            _make_holding("Fund B", "2024-Q3", shares_changed=10_000, is_new_position=True),
            _make_holding("Fund C", "2024-Q3", shares_changed=10_000),
        ]
        result = institutional_accumulation(holdings)
        # All same size => median = 10_000, all weights = 1.0
        # Score = 3*1 + 3*1 + 1*1 = 7.0 (same as old unweighted)
        assert result.raw_value == 7.0

    def test_detail_contains_size_weighted(self):
        """Detail string should indicate size-weighted scoring."""
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=10_000, is_new_position=True),
        ]
        result = institutional_accumulation(holdings)
        assert "size_weighted" in result.detail.lower() or "size-weighted" in result.detail.lower()


class TestFactorScoreFields:
    """Tests for FactorScore metadata fields."""

    def test_name_is_institutional_accumulation(self):
        """Factor name should be 'institutional_accumulation'."""
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=10_000),
        ]
        result = institutional_accumulation(holdings)
        assert result.name == "institutional_accumulation"

    def test_returns_factor_score_type(self):
        """Should return a FactorScore instance."""
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=10_000),
        ]
        result = institutional_accumulation(holdings)
        assert isinstance(result, FactorScore)

    def test_percentile_rank_is_placeholder(self):
        """Percentile rank should be 0.0 (placeholder for Phase 6)."""
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=10_000),
        ]
        result = institutional_accumulation(holdings)
        assert result.percentile_rank == 0.0

    def test_detail_contains_fund_counts(self):
        """Detail string should contain accumulating/reducing fund counts."""
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=50_000, is_new_position=True),
            _make_holding("Fund B", "2024-Q3", shares_changed=10_000),
            _make_holding("Fund C", "2024-Q3", shares_changed=-20_000),
        ]
        result = institutional_accumulation(holdings)
        # Should mention accumulating and reducing counts
        assert "accumulating" in result.detail.lower() or "new" in result.detail.lower()
        assert "reducing" in result.detail.lower() or "reduc" in result.detail.lower()

    def test_empty_list_factor_score_fields(self):
        """Empty list should still have correct name and percentile_rank."""
        result = institutional_accumulation([])
        assert result.name == "institutional_accumulation"
        assert result.percentile_rank == 0.0
