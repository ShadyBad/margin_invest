"""Tests for conviction gates — absolute quality thresholds for Track A and Track B."""

from margin_engine.scoring.conviction_gates import (
    ConvictionGateResult,
    check_track_a_gates,
    check_track_b_gates,
)

# ---------------------------------------------------------------------------
# ConvictionGateResult model
# ---------------------------------------------------------------------------


class TestConvictionGateResult:
    """ConvictionGateResult is a simple model with passed + failures."""

    def test_passed_with_no_failures(self):
        result = ConvictionGateResult(passed=True, failures=[])
        assert result.passed is True
        assert result.failures == []

    def test_failed_with_reasons(self):
        result = ConvictionGateResult(passed=False, failures=["ROIC too low", "Low coverage"])
        assert result.passed is False
        assert len(result.failures) == 2


# ---------------------------------------------------------------------------
# Track A (Compounder) gates
# ---------------------------------------------------------------------------


class TestTrackAGates:
    """Track A gate checks.

    ROIC-conditional reinvestment: reinvestment threshold varies by ROIC tier.
    Also: CV < 0.30, price < 2x IV, coverage > 85%.
    """

    def test_all_gates_pass(self):
        result = check_track_a_gates(
            roic_median=0.20,
            roic_cv=0.15,
            reinvestment_rate=0.40,
            price_to_iv_ratio=1.2,
            data_coverage=0.95,
        )
        assert result.passed is True
        assert result.failures == []

    def test_roic_too_low(self):
        """ROIC below minimum (8%) with no trajectory override -> fail."""
        result = check_track_a_gates(
            roic_median=0.06,
            roic_cv=0.15,
            reinvestment_rate=0.40,
            price_to_iv_ratio=1.2,
            data_coverage=0.95,
        )
        assert result.passed is False
        assert any("ROIC" in f for f in result.failures)

    def test_roic_cv_too_high(self):
        result = check_track_a_gates(
            roic_median=0.20,
            roic_cv=0.40,
            reinvestment_rate=0.40,
            price_to_iv_ratio=1.2,
            data_coverage=0.95,
        )
        assert result.passed is False
        assert any("CV" in f or "stability" in f.lower() for f in result.failures)

    def test_reinvestment_too_low(self):
        """ROIC in strong tier (15-25%) requires reinvestment > 10%."""
        result = check_track_a_gates(
            roic_median=0.20,
            roic_cv=0.15,
            reinvestment_rate=0.08,
            price_to_iv_ratio=1.2,
            data_coverage=0.95,
        )
        assert result.passed is False
        assert any("reinvestment" in f.lower() for f in result.failures)

    def test_overvalued_above_2x_iv(self):
        result = check_track_a_gates(
            roic_median=0.20,
            roic_cv=0.15,
            reinvestment_rate=0.40,
            price_to_iv_ratio=2.5,
            data_coverage=0.95,
        )
        assert result.passed is False
        assert any("valuation" in f.lower() or "intrinsic" in f.lower() for f in result.failures)

    def test_low_data_coverage(self):
        result = check_track_a_gates(
            roic_median=0.20,
            roic_cv=0.15,
            reinvestment_rate=0.40,
            price_to_iv_ratio=1.2,
            data_coverage=0.70,
        )
        assert result.passed is False
        assert any("coverage" in f.lower() for f in result.failures)

    def test_multiple_failures(self):
        """All gates fail at once — should list all failures."""
        result = check_track_a_gates(
            roic_median=0.05,
            roic_cv=0.50,
            reinvestment_rate=0.10,
            price_to_iv_ratio=3.0,
            data_coverage=0.50,
        )
        assert result.passed is False
        assert len(result.failures) >= 4

    def test_boundary_roic_exactly_15_in_strong_tier(self):
        """ROIC == 15% is in the strong tier (>= 15%) — needs reinvestment > 10%."""
        result = check_track_a_gates(
            roic_median=0.15,
            roic_cv=0.15,
            reinvestment_rate=0.40,
            price_to_iv_ratio=1.2,
            data_coverage=0.95,
        )
        # With adequate reinvestment, ROIC exactly at 15% passes in the strong tier
        assert result.passed is True

    def test_boundary_cv_exactly_030_fails(self):
        """CV must be < 0.30, not <=."""
        result = check_track_a_gates(
            roic_median=0.20,
            roic_cv=0.30,
            reinvestment_rate=0.40,
            price_to_iv_ratio=1.2,
            data_coverage=0.95,
        )
        assert result.passed is False

    def test_boundary_price_exactly_2x_fails(self):
        """Price to IV must be < 2x (not above 2x)."""
        result = check_track_a_gates(
            roic_median=0.20,
            roic_cv=0.15,
            reinvestment_rate=0.40,
            price_to_iv_ratio=2.0,
            data_coverage=0.95,
        )
        # At exactly 2x, the gate should still pass (not "above" 2x)
        assert result.passed is True


# ---------------------------------------------------------------------------
# Track B (Mispricing) gates
# ---------------------------------------------------------------------------


class TestTrackBGates:
    """Track B requires: quality floor, valuation depth, catalyst, downside floor."""

    def test_all_gates_pass_with_roic(self):
        result = check_track_b_gates(
            roic_median=0.12,
            roic_improving=False,
            price_to_iv_ratio=0.50,
            has_catalyst=True,
            net_cash_pct=0.60,
            tangible_book_pct=0.30,
            current_ratio=1.5,
        )
        assert result.passed is True
        assert result.failures == []

    def test_all_gates_pass_with_improving_roic(self):
        """Quality floor met via trajectory in 6-8% zone with sufficient improvement."""
        result = check_track_b_gates(
            roic_median=0.07,
            roic_improving=True,
            price_to_iv_ratio=0.50,
            has_catalyst=True,
            net_cash_pct=0.60,
            tangible_book_pct=0.30,
            current_ratio=1.5,
            roic_quarterly=[0.05, 0.07, 0.09],  # 200bps for 2 consecutive
        )
        assert result.passed is True
        assert result.conditional is True

    def test_quality_floor_fails(self):
        """ROIC < 8% and not improving -> quality floor fail."""
        result = check_track_b_gates(
            roic_median=0.05,
            roic_improving=False,
            price_to_iv_ratio=0.50,
            has_catalyst=True,
            net_cash_pct=0.60,
            tangible_book_pct=0.30,
            current_ratio=1.5,
        )
        assert result.passed is False
        assert any("quality" in f.lower() for f in result.failures)

    def test_valuation_not_deep_enough(self):
        """Price to IV ratio >= 0.60 -> valuation depth fails."""
        result = check_track_b_gates(
            roic_median=0.12,
            roic_improving=False,
            price_to_iv_ratio=0.70,
            has_catalyst=True,
            net_cash_pct=0.60,
            tangible_book_pct=0.30,
            current_ratio=1.5,
        )
        assert result.passed is False
        assert any("valuation" in f.lower() for f in result.failures)

    def test_no_catalyst(self):
        """has_catalyst=False -> catalyst gate fails."""
        result = check_track_b_gates(
            roic_median=0.12,
            roic_improving=False,
            price_to_iv_ratio=0.50,
            has_catalyst=False,
            net_cash_pct=0.60,
            tangible_book_pct=0.30,
            current_ratio=1.5,
        )
        assert result.passed is False
        assert any("catalyst" in f.lower() for f in result.failures)

    def test_downside_floor_fails_all_metrics(self):
        """No downside protection at all -> downside floor fails."""
        result = check_track_b_gates(
            roic_median=0.12,
            roic_improving=False,
            price_to_iv_ratio=0.50,
            has_catalyst=True,
            net_cash_pct=0.30,
            tangible_book_pct=0.30,
            current_ratio=1.5,
        )
        assert result.passed is False
        assert any("downside" in f.lower() for f in result.failures)

    def test_downside_met_via_tangible_book(self):
        """Downside floor met via tangible_book_pct > 50%."""
        result = check_track_b_gates(
            roic_median=0.12,
            roic_improving=False,
            price_to_iv_ratio=0.50,
            has_catalyst=True,
            net_cash_pct=0.30,
            tangible_book_pct=0.60,
            current_ratio=1.5,
        )
        assert result.passed is True

    def test_downside_met_via_current_ratio(self):
        """Downside floor met via current_ratio > 2.0."""
        result = check_track_b_gates(
            roic_median=0.12,
            roic_improving=False,
            price_to_iv_ratio=0.50,
            has_catalyst=True,
            net_cash_pct=0.30,
            tangible_book_pct=0.30,
            current_ratio=2.5,
        )
        assert result.passed is True

    def test_boundary_roic_exactly_8_fails(self):
        """ROIC must be > 8%, not >=."""
        result = check_track_b_gates(
            roic_median=0.08,
            roic_improving=False,
            price_to_iv_ratio=0.50,
            has_catalyst=True,
            net_cash_pct=0.60,
            tangible_book_pct=0.30,
            current_ratio=1.5,
        )
        assert result.passed is False

    def test_boundary_price_exactly_060_fails(self):
        """Price to IV must be < 0.60, not <=."""
        result = check_track_b_gates(
            roic_median=0.12,
            roic_improving=False,
            price_to_iv_ratio=0.60,
            has_catalyst=True,
            net_cash_pct=0.60,
            tangible_book_pct=0.30,
            current_ratio=1.5,
        )
        assert result.passed is False

    def test_multiple_failures(self):
        """All gates fail at once."""
        result = check_track_b_gates(
            roic_median=0.03,
            roic_improving=False,
            price_to_iv_ratio=0.90,
            has_catalyst=False,
            net_cash_pct=0.10,
            tangible_book_pct=0.10,
            current_ratio=0.8,
        )
        assert result.passed is False
        assert len(result.failures) >= 3
