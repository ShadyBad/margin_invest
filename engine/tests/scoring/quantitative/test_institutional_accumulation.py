"""Tests for the Institutional Accumulation (Smart Money) factor."""

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
        """Multiple new positions (+3 each) and additions (+1 each) sum correctly.

        2 new positions = +6, 2 additions = +2 => net = +8
        """
        holdings = [
            _make_holding("Berkshire", "2024-Q3", shares_changed=50_000, is_new_position=True),
            _make_holding("Bridgewater", "2024-Q3", shares_changed=30_000, is_new_position=True),
            _make_holding("Citadel", "2024-Q3", shares_changed=10_000),
            _make_holding("DE Shaw", "2024-Q3", shares_changed=5_000),
        ]
        result = institutional_accumulation(holdings)
        assert result.raw_value == 8.0

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
        """Three funds all reducing: -1 each => net = -3."""
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=-50_000),
            _make_holding("Fund B", "2024-Q3", shares_changed=-30_000),
            _make_holding("Fund C", "2024-Q3", shares_changed=-10_000),
        ]
        result = institutional_accumulation(holdings)
        assert result.raw_value == -3.0

    def test_more_reducers_than_accumulators(self):
        """1 addition (+1) and 3 reductions (-3) => net = -2."""
        holdings = [
            _make_holding("Fund A", "2024-Q3", shares_changed=10_000),
            _make_holding("Fund B", "2024-Q3", shares_changed=-20_000),
            _make_holding("Fund C", "2024-Q3", shares_changed=-15_000),
            _make_holding("Fund D", "2024-Q3", shares_changed=-5_000),
        ]
        result = institutional_accumulation(holdings)
        assert result.raw_value == -2.0


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

        Q3 has 1 addition (+1) and 1 reduction (-1) => net = 0
        """
        holdings = [
            _make_holding("Fund A", "2024-Q1", shares_changed=100_000, is_new_position=True),
            _make_holding("Fund B", "2024-Q2", shares_changed=50_000),
            _make_holding("Fund C", "2024-Q3", shares_changed=10_000),
            _make_holding("Fund D", "2024-Q3", shares_changed=-5_000),
        ]
        result = institutional_accumulation(holdings)
        assert result.raw_value == 0.0

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
