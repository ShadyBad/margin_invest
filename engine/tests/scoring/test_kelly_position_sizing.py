"""Tests for Kelly Criterion position sizing formula.

All expected values are hand-calculated from first principles:
    b = expected_gain / expected_loss
    f* = (p * b - q) / b  where q = 1 - p
    fractional = kelly_fraction * max(0, f*) * 100
    capped at max_position_pct
"""

from __future__ import annotations

from margin_engine.scoring.kelly_position_sizing import (
    KellyConstraints,
    kelly_position_size,
)


class TestKellyConstraints:
    """KellyConstraints model defaults and fields."""

    def test_defaults(self):
        kc = KellyConstraints()
        assert kc.max_single_position == 15.0
        assert kc.max_top_3_combined == 50.0
        assert kc.max_sector_concentration == 30.0
        assert kc.min_positions == 5

    def test_custom_values(self):
        kc = KellyConstraints(
            max_single_position=20.0,
            max_top_3_combined=60.0,
            max_sector_concentration=25.0,
            min_positions=8,
        )
        assert kc.max_single_position == 20.0
        assert kc.min_positions == 8


class TestKellyPositionSize:
    """Golden-value tests for kelly_position_size().

    Formula:
        b = gain / loss
        f* = (p * b - (1-p)) / b
        result = kelly_fraction * max(0, f*) * 100
        capped at max_position_pct
    """

    def test_positive_edge_standard_case(self):
        """p=0.6, gain=0.20, loss=0.10 → b=2.0, f*=0.40, result=10.0%."""
        # b = 0.20 / 0.10 = 2.0
        # f* = (0.6 * 2.0 - 0.4) / 2.0 = (1.2 - 0.4) / 2.0 = 0.8 / 2.0 = 0.4
        # fractional = 0.25 * 0.4 * 100 = 10.0
        result = kelly_position_size(
            win_probability=0.6,
            expected_gain=0.20,
            expected_loss=0.10,
            kelly_fraction=0.25,
            max_position_pct=15.0,
        )
        assert abs(result - 10.0) < 1e-9

    def test_negative_edge_returns_zero(self):
        """p=0.3, gain=0.15, loss=0.10 → f*<0 → 0.0."""
        # b = 0.15 / 0.10 = 1.5
        # f* = (0.3 * 1.5 - 0.7) / 1.5 = (0.45 - 0.7) / 1.5 = -0.25 / 1.5 < 0
        result = kelly_position_size(
            win_probability=0.3,
            expected_gain=0.15,
            expected_loss=0.10,
        )
        assert result == 0.0

    def test_low_win_high_payoff_positive(self):
        """p=0.45, gain=0.30, loss=0.10 → b=3.0, f*>0 → positive size."""
        # b = 0.30 / 0.10 = 3.0
        # f* = (0.45 * 3.0 - 0.55) / 3.0 = (1.35 - 0.55) / 3.0 = 0.80 / 3.0 ≈ 0.2667
        # fractional = 0.25 * 0.2667 * 100 ≈ 6.667
        result = kelly_position_size(
            win_probability=0.45,
            expected_gain=0.30,
            expected_loss=0.10,
            kelly_fraction=0.25,
            max_position_pct=15.0,
        )
        assert result > 0.0
        assert abs(result - (0.25 * (0.80 / 3.0) * 100)) < 1e-9

    def test_capped_at_max_position(self):
        """Very high edge is capped at max_position_pct=15.0."""
        # p=0.9, gain=0.50, loss=0.05 → extremely high Kelly fraction
        result = kelly_position_size(
            win_probability=0.9,
            expected_gain=0.50,
            expected_loss=0.05,
            kelly_fraction=0.25,
            max_position_pct=15.0,
        )
        assert result == 15.0

    def test_custom_fraction_doubles_allocation(self):
        """fraction=0.50 gives double the result of fraction=0.25."""
        result_25 = kelly_position_size(
            win_probability=0.6,
            expected_gain=0.20,
            expected_loss=0.10,
            kelly_fraction=0.25,
            max_position_pct=50.0,  # high cap so we don't hit it
        )
        result_50 = kelly_position_size(
            win_probability=0.6,
            expected_gain=0.20,
            expected_loss=0.10,
            kelly_fraction=0.50,
            max_position_pct=50.0,
        )
        assert abs(result_50 - 2.0 * result_25) < 1e-9

    def test_custom_max_position_cap_respected(self):
        """Custom max_position_pct=8.0 caps the result."""
        result = kelly_position_size(
            win_probability=0.9,
            expected_gain=0.50,
            expected_loss=0.05,
            kelly_fraction=0.25,
            max_position_pct=8.0,
        )
        assert result == 8.0

    def test_exactly_break_even_edge_returns_zero(self):
        """f*=0 exactly → 0.0% allocation."""
        # f* = 0 when p * b = q  i.e. p * (gain/loss) = (1-p)
        # Example: p=0.5, gain=0.10, loss=0.10 → b=1.0, f*=(0.5*1-0.5)/1=0.0
        result = kelly_position_size(
            win_probability=0.5,
            expected_gain=0.10,
            expected_loss=0.10,
        )
        assert result == 0.0

    def test_default_fraction_is_quarter_kelly(self):
        """Default kelly_fraction=0.25 (quarter-Kelly)."""
        result_default = kelly_position_size(
            win_probability=0.6,
            expected_gain=0.20,
            expected_loss=0.10,
        )
        result_explicit = kelly_position_size(
            win_probability=0.6,
            expected_gain=0.20,
            expected_loss=0.10,
            kelly_fraction=0.25,
            max_position_pct=15.0,
        )
        assert abs(result_default - result_explicit) < 1e-9
