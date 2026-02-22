"""Tests for position sizing — maps asymmetry ratio + conviction level to max position %."""

import pytest
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.position_sizing import compute_position_size

# ---------------------------------------------------------------------------
# Asymmetry tiers
# ---------------------------------------------------------------------------


class TestAsymmetryTiers:
    """Position size max determined by asymmetry ratio tier."""

    def test_asymmetry_above_5x_max_20(self):
        """Asymmetry > 5x -> max 20%."""
        result = compute_position_size(6.0, ConvictionLevel.EXCEPTIONAL)
        assert result == pytest.approx(20.0)

    def test_asymmetry_3_to_5x_max_10(self):
        """Asymmetry 3-5x -> max 10%."""
        result = compute_position_size(4.0, ConvictionLevel.EXCEPTIONAL)
        assert result == pytest.approx(10.0)

    def test_asymmetry_1_5_to_3x_max_5(self):
        """Asymmetry 1.5-3x -> max 5%."""
        result = compute_position_size(2.0, ConvictionLevel.EXCEPTIONAL)
        assert result == pytest.approx(5.0)

    def test_asymmetry_below_1_5x_max_3(self):
        """Asymmetry < 1.5x -> max 3%."""
        result = compute_position_size(1.2, ConvictionLevel.EXCEPTIONAL)
        assert result == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# Conviction scaling
# ---------------------------------------------------------------------------


class TestConvictionScaling:
    """Conviction level scales within the max position size."""

    def test_exceptional_100_pct_of_max(self):
        """Exceptional: 100% of max."""
        result = compute_position_size(6.0, ConvictionLevel.EXCEPTIONAL)
        assert result == pytest.approx(20.0)

    def test_high_60_pct_of_max(self):
        """High: 60% of max."""
        result = compute_position_size(6.0, ConvictionLevel.HIGH)
        assert result == pytest.approx(12.0)

    def test_medium_30_pct_of_max(self):
        """Medium: 30% of max."""
        result = compute_position_size(6.0, ConvictionLevel.MEDIUM)
        assert result == pytest.approx(6.0)

    def test_none_conviction_zero(self):
        """NONE conviction -> 0% position."""
        result = compute_position_size(6.0, ConvictionLevel.NONE)
        assert result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Combined scenarios
# ---------------------------------------------------------------------------


class TestCombinedScenarios:
    """Verify correct position size for various asymmetry + conviction combos."""

    def test_moderate_asymmetry_high_conviction(self):
        """Asymmetry 4x (max=10%) + High (60%) -> 6.0%."""
        result = compute_position_size(4.0, ConvictionLevel.HIGH)
        assert result == pytest.approx(6.0)

    def test_low_asymmetry_medium(self):
        """Asymmetry 1.0x (max=3%) + Medium (30%) -> 0.9%."""
        result = compute_position_size(1.0, ConvictionLevel.MEDIUM)
        assert result == pytest.approx(0.9)

    def test_medium_asymmetry_exceptional(self):
        """Asymmetry 2.5x (max=5%) + Exceptional (100%) -> 5.0%."""
        result = compute_position_size(2.5, ConvictionLevel.EXCEPTIONAL)
        assert result == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Boundary values
# ---------------------------------------------------------------------------


class TestBoundaryValues:
    """Exact boundary values for asymmetry tiers."""

    def test_exactly_5x_is_in_3_to_5_tier(self):
        """Asymmetry == 5.0 falls in 3-5x tier (max 10%), not >5x tier."""
        result = compute_position_size(5.0, ConvictionLevel.EXCEPTIONAL)
        assert result == pytest.approx(10.0)

    def test_exactly_3x_is_in_1_5_to_3_tier(self):
        """Asymmetry == 3.0 falls in 1.5-3x tier (max 5%)."""
        result = compute_position_size(3.0, ConvictionLevel.EXCEPTIONAL)
        assert result == pytest.approx(5.0)

    def test_exactly_1_5x_is_in_below_1_5_tier(self):
        """Asymmetry == 1.5 falls in <1.5x tier (max 3%)."""
        result = compute_position_size(1.5, ConvictionLevel.EXCEPTIONAL)
        assert result == pytest.approx(3.0)

    def test_zero_asymmetry(self):
        """Asymmetry 0 -> max 3%, position = 3% * conviction scale."""
        result = compute_position_size(0.0, ConvictionLevel.EXCEPTIONAL)
        assert result == pytest.approx(3.0)

    def test_negative_asymmetry(self):
        """Negative asymmetry -> max 3%."""
        result = compute_position_size(-1.0, ConvictionLevel.EXCEPTIONAL)
        assert result == pytest.approx(3.0)
