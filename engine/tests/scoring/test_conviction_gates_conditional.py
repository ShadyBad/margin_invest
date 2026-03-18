"""Tests for ROIC-conditional conviction gates and trajectory overrides.

Track A: reinvestment requirement varies by ROIC tier (capital-light path).
Track B: tightened quality floor with hard floor at 6% and trajectory-based conditional.
"""

from margin_engine.config.v3_scoring_config import ConvictionGateConfig
from margin_engine.scoring.conviction_gates import (
    check_track_a_gates,
    check_track_b_gates,
    check_trajectory_override,
)

# ---------------------------------------------------------------------------
# Track A — ROIC-conditional reinvestment
# ---------------------------------------------------------------------------


class TestTrackAROICConditional:
    """Track A reinvestment gate adjusts based on ROIC tier.

    Base params: roic_cv=0.15, price_to_iv_ratio=1.0, data_coverage=0.95.
    """

    BASE = {
        "roic_cv": 0.15,
        "price_to_iv_ratio": 1.0,
        "data_coverage": 0.95,
    }

    def test_apple_capital_light_passes(self):
        """ROIC >= 25% — no reinvestment requirement (capital-light path)."""
        result = check_track_a_gates(
            roic_median=0.40,
            reinvestment_rate=0.12,
            **self.BASE,
        )
        assert result.passed is True
        assert result.conditional is False

    def test_visa_capital_light_passes(self):
        """ROIC >= 25% — even very low reinvestment passes."""
        result = check_track_a_gates(
            roic_median=0.35,
            reinvestment_rate=0.08,
            **self.BASE,
        )
        assert result.passed is True

    def test_strong_roic_low_reinvestment(self):
        """ROIC 15-25% — reinvestment > 10% required."""
        result = check_track_a_gates(
            roic_median=0.18,
            reinvestment_rate=0.12,
            **self.BASE,
        )
        assert result.passed is True

    def test_strong_roic_insufficient_reinvestment(self):
        """ROIC 15-25% — reinvestment <= 10% fails."""
        result = check_track_a_gates(
            roic_median=0.18,
            reinvestment_rate=0.08,
            **self.BASE,
        )
        assert result.passed is False
        assert any("reinvestment" in f.lower() for f in result.failures)

    def test_adequate_roic_sufficient(self):
        """ROIC 10-15% — reinvestment > 20% required."""
        result = check_track_a_gates(
            roic_median=0.12,
            reinvestment_rate=0.22,
            **self.BASE,
        )
        assert result.passed is True

    def test_adequate_roic_insufficient(self):
        """ROIC 10-15% — reinvestment <= 20% fails."""
        result = check_track_a_gates(
            roic_median=0.12,
            reinvestment_rate=0.15,
            **self.BASE,
        )
        assert result.passed is False
        assert any("reinvestment" in f.lower() for f in result.failures)

    def test_minimum_roic_needs_full(self):
        """ROIC 8-10% — reinvestment > 30% required (original behavior)."""
        result = check_track_a_gates(
            roic_median=0.09,
            reinvestment_rate=0.25,
            **self.BASE,
        )
        assert result.passed is False
        assert any("reinvestment" in f.lower() for f in result.failures)

    def test_minimum_roic_full_passes(self):
        """ROIC 8-10% — reinvestment > 30% passes."""
        result = check_track_a_gates(
            roic_median=0.09,
            reinvestment_rate=0.35,
            **self.BASE,
        )
        assert result.passed is True


# ---------------------------------------------------------------------------
# Track A — Trajectory override
# ---------------------------------------------------------------------------


class TestTrackATrajectoryOverride:
    """Trajectory override for Track A when ROIC < 8%.

    200bps+ improvement for 3 consecutive quarters -> conditional pass.
    """

    BASE = {
        "roic_cv": 0.15,
        "reinvestment_rate": 0.05,
        "price_to_iv_ratio": 1.0,
        "data_coverage": 0.95,
    }

    def test_trajectory_conditional(self):
        """Rising ROIC with 200bps+ per quarter for 3 periods -> conditional pass."""
        result = check_track_a_gates(
            roic_median=0.06,
            roic_quarterly=[0.04, 0.06, 0.08, 0.10],
            **self.BASE,
        )
        assert result.passed is True
        assert result.conditional is True

    def test_no_data_no_trajectory(self):
        """No roic_quarterly data -> no trajectory override, fails."""
        result = check_track_a_gates(
            roic_median=0.06,
            **self.BASE,
        )
        assert result.passed is False
        assert result.conditional is False

    def test_flat_no_override(self):
        """Flat ROIC trajectory -> no override."""
        result = check_track_a_gates(
            roic_median=0.06,
            roic_quarterly=[0.06, 0.06, 0.06, 0.06],
            **self.BASE,
        )
        assert result.passed is False
        assert result.conditional is False

    def test_nan_handling(self):
        """NaN values in quarterly data -> no crash, filters them out."""
        result = check_track_a_gates(
            roic_median=0.06,
            roic_quarterly=[0.04, float("nan"), 0.06, 0.08, 0.10],
            **self.BASE,
        )
        # NaN is filtered; remaining [0.04, 0.06, 0.08, 0.10] has 3 consecutive 200bps+ deltas
        assert result.passed is True
        assert result.conditional is True


# ---------------------------------------------------------------------------
# Track B — Tightened quality floor
# ---------------------------------------------------------------------------


class TestTrackBTightened:
    """Track B quality floor tightened with hard floor at 6%.

    Base params: price_to_iv_ratio=0.50, has_catalyst=True,
    net_cash_pct=0.60, tangible_book_pct=0.60, current_ratio=2.5.
    """

    BASE = {
        "price_to_iv_ratio": 0.50,
        "has_catalyst": True,
        "net_cash_pct": 0.60,
        "tangible_book_pct": 0.60,
        "current_ratio": 2.5,
    }

    def test_above_8pct(self):
        """ROIC >= 8% passes quality floor unconditionally."""
        result = check_track_b_gates(
            roic_median=0.10,
            roic_improving=False,
            **self.BASE,
        )
        assert result.passed is True
        assert result.conditional is False

    def test_trivial_improvement_fails(self):
        """ROIC 6-8% with only 50bps improvement -> fails."""
        result = check_track_b_gates(
            roic_median=0.07,
            roic_improving=True,
            roic_quarterly=[0.065, 0.070, 0.075],  # 50bps per quarter
            **self.BASE,
        )
        assert result.passed is False
        assert any("quality" in f.lower() for f in result.failures)

    def test_meaningful_improvement_conditional(self):
        """ROIC 6-8% with 200bps+ improvement for 2+ consecutive -> conditional pass."""
        result = check_track_b_gates(
            roic_median=0.07,
            roic_improving=True,
            roic_quarterly=[0.05, 0.07, 0.09],  # 200bps per quarter, 2 consecutive
            **self.BASE,
        )
        assert result.passed is True
        assert result.conditional is True

    def test_hard_floor(self):
        """ROIC < 6% -> hard FAIL regardless of trajectory."""
        result = check_track_b_gates(
            roic_median=0.05,
            roic_improving=True,
            roic_quarterly=[0.01, 0.03, 0.05, 0.07],  # strong trajectory
            **self.BASE,
        )
        assert result.passed is False
        assert any("quality" in f.lower() or "hard floor" in f.lower() for f in result.failures)


# ---------------------------------------------------------------------------
# check_trajectory_override helper
# ---------------------------------------------------------------------------


class TestCheckTrajectoryOverride:
    """Unit tests for the trajectory override helper."""

    def test_sufficient_improvement(self):
        """3 consecutive 200bps+ improvements -> True."""
        assert check_trajectory_override([0.04, 0.06, 0.08, 0.10], 0.02, 3) is True

    def test_insufficient_periods(self):
        """Only 2 consecutive 200bps+ improvements when 3 needed -> False."""
        assert check_trajectory_override([0.04, 0.06, 0.08], 0.02, 3) is False

    def test_gap_in_improvement(self):
        """Improvement dips below threshold mid-stream -> resets count."""
        # 0.04->0.06 (+200bps), 0.06->0.065 (+50bps resets), 0.065->0.085 (+200bps)
        assert check_trajectory_override([0.04, 0.06, 0.065, 0.085, 0.105], 0.02, 3) is False

    def test_nan_filtered(self):
        """NaN values are filtered out before checking deltas."""
        values = [0.04, float("nan"), 0.06, 0.08, 0.10]
        assert check_trajectory_override(values, 0.02, 3) is True

    def test_all_nan(self):
        """All NaN -> returns False (not enough data)."""
        assert check_trajectory_override([float("nan"), float("nan")], 0.02, 3) is False

    def test_empty_list(self):
        """Empty list -> returns False."""
        assert check_trajectory_override([], 0.02, 3) is False

    def test_two_periods_sufficient(self):
        """min_periods=2 with exactly 2 consecutive improvements -> True."""
        assert check_trajectory_override([0.05, 0.07, 0.09], 0.02, 2) is True

    def test_inf_filtered(self):
        """Inf values are filtered out by math.isfinite."""
        values = [0.04, float("inf"), 0.06, 0.08, 0.10]
        assert check_trajectory_override(values, 0.02, 3) is True


# ---------------------------------------------------------------------------
# Config override
# ---------------------------------------------------------------------------


class TestConvictionGateConfigOverride:
    """Passing a custom ConvictionGateConfig overrides default thresholds."""

    def test_custom_config_relaxes_reinvestment(self):
        """Custom config can lower reinvestment requirements."""
        cfg = ConvictionGateConfig(
            roic_exceptional=0.20,  # lower bar for capital-light
            reinvestment_strong=0.05,
        )
        result = check_track_a_gates(
            roic_median=0.22,
            roic_cv=0.15,
            reinvestment_rate=0.06,
            price_to_iv_ratio=1.0,
            data_coverage=0.95,
            config=cfg,
        )
        assert result.passed is True

    def test_custom_config_track_b_hard_floor(self):
        """Custom hard floor at 5% instead of 6%."""
        cfg = ConvictionGateConfig(track_b_roic_hard_floor=0.05)
        result = check_track_b_gates(
            roic_median=0.055,
            roic_improving=True,
            price_to_iv_ratio=0.50,
            has_catalyst=True,
            net_cash_pct=0.60,
            tangible_book_pct=0.60,
            current_ratio=2.5,
            roic_quarterly=[0.03, 0.05, 0.07],  # 200bps for 2 consecutive
            config=cfg,
        )
        assert result.passed is True
        assert result.conditional is True
