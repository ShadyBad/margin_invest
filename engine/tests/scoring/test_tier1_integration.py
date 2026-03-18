"""Tier 1 engine scoring overhaul — integration regression tests.

Verifies the three core changes work correctly end-to-end:
1. Geometric mean composite — zero in any factor no longer kills the score
2. ROIC-conditional conviction gates — capital-light path, trajectory overrides
3. Mediocrity gate trajectory override — conditional passes for turnarounds

These tests exercise the public APIs with realistic profiles (Apple, Visa,
turnarounds) and confirm the changes are independent of one another.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from margin_engine.config.v3_scoring_config import (
    V3CompositeConfig,
)
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import GrowthStage
from margin_engine.scoring.conviction_gates import (
    check_track_a_gates,
    check_track_b_gates,
)
from margin_engine.scoring.filters.mediocrity_gate import mediocrity_gate
from margin_engine.scoring.v3_composite import (
    compute_track_a_score,
    compute_track_b_score,
    compute_track_c_score,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_period(
    year: int,
    ebit: Decimal = Decimal("200"),
    revenue: Decimal = Decimal("1000"),
    cfo: Decimal = Decimal("250"),
    gross_margin_pct: float = 0.40,
) -> FinancialPeriod:
    """Create a FinancialPeriod. Defaults produce a quality business (passes all gates)."""
    cogs = revenue * Decimal(str(1 - gross_margin_pct))
    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=IncomeStatement(
            revenue=revenue,
            cost_of_revenue=cogs,
            gross_profit=revenue - cogs,
            ebit=ebit,
            net_income=ebit * Decimal("0.79"),
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=Decimal("500"),
            long_term_debt=Decimal("200"),
            cash_and_equivalents=Decimal("100"),
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=cfo,
            capital_expenditures=Decimal("-50"),
        ),
    )


def _make_failing_history() -> FinancialHistory:
    """FinancialHistory that fails the static mediocrity gate on ROIC.

    Low EBIT (20) on equity=500, debt=200, cash=100 gives ROIC ~2.6% << 8%.
    """
    return FinancialHistory(
        ticker="FAIL",
        periods=[_make_period(y, ebit=Decimal("20")) for y in range(2019, 2024)],
    )


# ===========================================================================
# 1. Geometric Mean End-to-End
# ===========================================================================


class TestGeometricMeanEndToEnd:
    """Verify the weighted geometric mean composite produces non-zero scores
    even when one factor is zero, and that balanced profiles outscore unbalanced."""

    def test_amazon_profile_nonzero(self):
        """Amazon-like profile (0.30, 0.90, 0.0, 0.95) -> score > 0.10.

        Under the old multiplicative formula this was 0.0; the geometric mean
        with factor_floor=0.05 rescues the zero.
        """
        score = compute_track_a_score(0.30, 0.90, 0.0, 0.95)
        assert score > 0.10

    def test_all_zeros_above_floor(self):
        """All factors zero -> score >= composite_floor (0.01)."""
        score = compute_track_a_score(0.0, 0.0, 0.0, 0.0)
        assert score >= 0.01

    def test_balanced_beats_unbalanced(self):
        """Balanced (0.5 x4) outscores unbalanced (0.3, 0.9, 0.0, 0.95), both > 0."""
        balanced = compute_track_a_score(0.5, 0.5, 0.5, 0.5)
        unbalanced = compute_track_a_score(0.3, 0.9, 0.0, 0.95)
        assert balanced > unbalanced > 0

    def test_track_b_zero_factor_rescued(self):
        """Track B: zero in one factor does not kill the score."""
        score = compute_track_b_score(5.0, 0.0, 1.0, 0.75)
        assert score > 0

    def test_track_c_zero_factor_rescued(self):
        """Track C: zero in one factor does not kill the score."""
        score = compute_track_c_score(0.80, 0.0, 0.70, 0.90)
        assert score > 0

    def test_factor_floor_config_respected(self):
        """Custom factor_floor changes the rescue value for zero factors."""
        low_floor = V3CompositeConfig(factor_floor=0.01)
        high_floor = V3CompositeConfig(factor_floor=0.20)
        score_low = compute_track_a_score(0.0, 0.80, 0.80, 0.80, config=low_floor)
        score_high = compute_track_a_score(0.0, 0.80, 0.80, 0.80, config=high_floor)
        # Higher floor for the zero factor -> higher rescue score
        assert score_high > score_low


# ===========================================================================
# 2. Conviction Gates End-to-End
# ===========================================================================


class TestConvictionGatesEndToEnd:
    """Verify ROIC-conditional reinvestment and trajectory overrides."""

    def test_apple_passes_gates(self):
        """Apple profile: ROIC 40%, low CV, low reinvestment -> unconditional pass.

        ROIC >= 25% = capital-light path, no reinvestment required.
        """
        result = check_track_a_gates(
            roic_median=0.40,
            roic_cv=0.15,
            reinvestment_rate=0.12,
            price_to_iv_ratio=1.0,
            data_coverage=0.95,
        )
        assert result.passed is True
        assert result.conditional is False
        assert result.failures == []

    def test_visa_passes_gates(self):
        """Visa profile: ROIC 35%, very low reinvestment -> pass (capital-light)."""
        result = check_track_a_gates(
            roic_median=0.35,
            roic_cv=0.15,
            reinvestment_rate=0.08,
            price_to_iv_ratio=1.0,
            data_coverage=0.95,
        )
        assert result.passed is True

    def test_turnaround_conditional(self):
        """ROIC 6% with 200bps+/Q for 3 consecutive quarters -> conditional pass."""
        result = check_track_a_gates(
            roic_median=0.06,
            roic_cv=0.15,
            reinvestment_rate=0.05,
            price_to_iv_ratio=1.0,
            data_coverage=0.95,
            roic_quarterly=[0.04, 0.06, 0.08, 0.10],
        )
        assert result.passed is True
        assert result.conditional is True

    def test_track_b_hard_floor(self):
        """ROIC 5% on Track B -> hard FAIL regardless of trajectory."""
        result = check_track_b_gates(
            roic_median=0.05,
            roic_improving=True,
            price_to_iv_ratio=0.50,
            has_catalyst=True,
            net_cash_pct=0.60,
            tangible_book_pct=0.60,
            current_ratio=2.5,
            roic_quarterly=[0.01, 0.03, 0.05, 0.07],
        )
        assert result.passed is False
        assert any("hard floor" in f.lower() for f in result.failures)

    def test_track_b_improving_zone_conditional(self):
        """ROIC 7% (in 6-8% zone) with meaningful trajectory -> conditional pass."""
        result = check_track_b_gates(
            roic_median=0.07,
            roic_improving=True,
            price_to_iv_ratio=0.50,
            has_catalyst=True,
            net_cash_pct=0.60,
            tangible_book_pct=0.60,
            current_ratio=2.5,
            roic_quarterly=[0.05, 0.07, 0.09],
        )
        assert result.passed is True
        assert result.conditional is True

    def test_strong_roic_adequate_reinvestment(self):
        """ROIC 18% (strong tier) with reinvestment 12% (>10%) -> pass."""
        result = check_track_a_gates(
            roic_median=0.18,
            roic_cv=0.15,
            reinvestment_rate=0.12,
            price_to_iv_ratio=1.0,
            data_coverage=0.95,
        )
        assert result.passed is True
        assert result.conditional is False


# ===========================================================================
# 3. Mediocrity Gate Trajectory End-to-End
# ===========================================================================


class TestMediocracyTrajectoryEndToEnd:
    """Verify the mediocrity gate trajectory override produces conditional passes."""

    def test_static_fail_with_trajectory_conditional(self):
        """Failing history + ROIC improving 200bps+/Q for 3Q -> conditional=True."""
        history = _make_failing_history()
        roic_q = [0.04, 0.06, 0.08, 0.10]  # 3 consecutive 200bps+ improvements
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=roic_q,
        )
        assert result.passed is False
        assert result.conditional is True
        assert result.computed_metrics is not None
        assert result.computed_metrics["conditional_score_multiplier"] == 0.90
        assert "roic_trajectory" in result.computed_metrics.get("trajectory_reasons", "")

    def test_backward_compatible_no_quarterly(self):
        """No quarterly params -> conditional=False (pure static gate)."""
        history = _make_failing_history()
        result = mediocrity_gate(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is False
        assert result.conditional is False

    def test_gm_approaching_conditional(self):
        """GM within 3% of threshold and expanding 300bps+/year -> conditional."""
        history = _make_failing_history()
        gm_q = [0.17, 0.1775, 0.185, 0.20]  # 4 quarters, ~300bps/year
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            gm_quarterly=gm_q,
        )
        assert result.passed is False
        assert result.conditional is True
        assert "gm_approaching" in result.computed_metrics.get("trajectory_reasons", "")

    def test_fcf_inflection_conditional(self):
        """FCF turned positive in recent 2 quarters after negative priors -> conditional."""
        history = _make_failing_history()
        fcf_q = [-100.0, -80.0, -50.0, -20.0, 30.0, 50.0]
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            fcf_quarterly=fcf_q,
        )
        assert result.passed is False
        assert result.conditional is True
        assert "fcf_inflection" in result.computed_metrics.get("trajectory_reasons", "")

    def test_turnaround_stage_conditional(self):
        """TURNAROUND stage + any positive ROIC trajectory -> conditional."""
        history = _make_failing_history()
        roic_q = [0.02, 0.03]  # Any positive trajectory
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=roic_q,
            growth_stage=GrowthStage.TURNAROUND,
        )
        assert result.passed is False
        assert result.conditional is True
        assert "growth_stage_override" in result.computed_metrics.get("trajectory_reasons", "")


# ===========================================================================
# 4. Combined Changes — Independence
# ===========================================================================


class TestCombinedChanges:
    """Verify each change works independently of the others."""

    def test_geometric_mean_independent_of_gates(self):
        """Geometric mean scoring works with default config, no gate interaction."""
        # Score computation is purely mathematical, no gate logic involved
        score = compute_track_a_score(0.60, 0.70, 0.50, 0.80)
        assert 0.0 < score < 1.0

        # Same call with explicit default config produces identical result
        score2 = compute_track_a_score(0.60, 0.70, 0.50, 0.80, config=V3CompositeConfig())
        assert score == pytest.approx(score2)

    def test_gates_independent_of_scoring(self):
        """Conviction gates evaluate thresholds without calling any score function."""
        result = check_track_a_gates(
            roic_median=0.40,
            roic_cv=0.15,
            reinvestment_rate=0.12,
            price_to_iv_ratio=1.0,
            data_coverage=0.95,
        )
        # Gates return a result object, never a composite score
        assert result.passed is True
        assert not hasattr(result, "score")

    def test_mediocrity_independent_of_scoring(self):
        """Mediocrity gate evaluates FinancialHistory, not composite scores."""
        history = FinancialHistory(
            ticker="GOOD",
            periods=[_make_period(y) for y in range(2019, 2024)],
        )
        result = mediocrity_gate(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True
        # FilterResult, not a score
        assert hasattr(result, "conditional")
        assert not hasattr(result, "score")

    def test_gates_independent_of_mediocrity(self):
        """Conviction gates use ROIC metrics directly, not mediocrity gate output."""
        # Conviction gates use raw ROIC values, not mediocrity gate results
        gate_result = check_track_a_gates(
            roic_median=0.06,
            roic_cv=0.15,
            reinvestment_rate=0.05,
            price_to_iv_ratio=1.0,
            data_coverage=0.95,
            roic_quarterly=[0.04, 0.06, 0.08, 0.10],
        )
        assert gate_result.passed is True
        assert gate_result.conditional is True

        # Mediocrity gate uses FinancialHistory, not gate inputs
        history = _make_failing_history()
        med_result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=[0.04, 0.06, 0.08, 0.10],
        )
        assert med_result.conditional is True

        # The two produce results from entirely separate inputs
        assert type(gate_result).__name__ == "ConvictionGateResult"
        assert type(med_result).__name__ == "FilterResult"

    def test_all_three_composable_in_sequence(self):
        """Realistic pipeline: score -> gate check -> mediocrity check (all succeed)."""
        # Step 1: Compute a composite score
        score = compute_track_a_score(0.70, 0.80, 0.60, 0.75)
        assert score > 0.50

        # Step 2: Check conviction gates
        gate = check_track_a_gates(
            roic_median=0.30,
            roic_cv=0.15,
            reinvestment_rate=0.12,
            price_to_iv_ratio=1.0,
            data_coverage=0.95,
        )
        assert gate.passed is True

        # Step 3: Check mediocrity gate
        history = FinancialHistory(
            ticker="QUALITY",
            periods=[_make_period(y) for y in range(2019, 2024)],
        )
        med = mediocrity_gate(history, sector=GICSSector.TECHNOLOGY)
        assert med.passed is True

        # All three produce independent, composable results
        assert score > 0
        assert gate.passed
        assert med.passed
