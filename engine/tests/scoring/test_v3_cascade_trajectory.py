"""Tests for trajectory detection in v3 gate cascades.

Verifies that turnaround companies (low ROIC but improving) get
conditional=True, which caps EXCEPTIONAL conviction to HIGH.
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import CompositeTier
from margin_engine.scoring.v3_cascade import (
    TrackAInputs,
    TrackBInputs,
    _compute_roic_series,
    run_track_a_cascade,
    run_track_b_cascade,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IC = 1000  # Invested capital: equity(800) + debt(300) - cash(100) = 1000
_TAX_RATE = 0.25


def _period_with_roic(target_roic: float, period_end: str = "2024-12-31") -> FinancialPeriod:
    """Build a FinancialPeriod with a specific ROIC.

    ROIC = NOPAT / IC = EBIT * (1 - tax_rate) / IC
    => EBIT = target_roic * IC / (1 - tax_rate)

    IC = equity(800) + debt(300) - cash(100) = 1000

    Sets tax_provision = EBIT * tax_rate so that IncomeStatement.effective_tax_rate
    returns exactly _TAX_RATE (pretax = EBIT when no interest_expense).
    """
    ebit = target_roic * _IC / (1 - _TAX_RATE)
    tax_provision = ebit * _TAX_RATE
    return FinancialPeriod(
        period_end=period_end,
        filing_date="2025-02-15",
        current_income=IncomeStatement(
            revenue=Decimal("5000"),
            cost_of_revenue=Decimal("2000"),
            gross_profit=Decimal("3000"),
            ebit=Decimal(str(round(ebit, 4))),
            tax_provision=Decimal(str(round(tax_provision, 4))),
            net_income=Decimal(str(round(ebit * (1 - _TAX_RATE), 4))),
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("1500"),
            total_equity=Decimal("800"),
            long_term_debt=Decimal("200"),
            short_term_debt=Decimal("100"),
            cash_and_equivalents=Decimal("100"),
            shares_outstanding=100,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("400"),
            capital_expenditures=Decimal("-100"),
        ),
    )


def _profile() -> AssetProfile:
    return AssetProfile(
        ticker="TRAJ",
        name="Trajectory Corp",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("10000000000"),
        shares_outstanding=100,
    )


def _build_track_a_inputs(roic_trajectory: list[float]) -> TrackAInputs:
    """Build TrackAInputs from a list of ROIC values (one per quarter)."""
    periods = [
        _period_with_roic(r, period_end=f"{2020 + i}-12-31") for i, r in enumerate(roic_trajectory)
    ]
    history = FinancialHistory(ticker="TRAJ", periods=periods)
    return TrackAInputs(
        history=history,
        period=history.periods[-1],
        profile=_profile(),
        current_price=10.0,
        current_fcf_per_share=3.0,
        wacc=0.10,
        terminal_growth=0.03,
        sustainable_growth_rate=0.08,
    )


def _build_track_b_inputs(roic_trajectory: list[float]) -> TrackBInputs:
    """Build TrackBInputs from a list of ROIC values (one per quarter)."""
    periods = [
        _period_with_roic(r, period_end=f"{2020 + i}-12-31") for i, r in enumerate(roic_trajectory)
    ]
    history = FinancialHistory(ticker="TRAJ", periods=periods)
    return TrackBInputs(
        history=history,
        period=history.periods[-1],
        profile=_profile(),
        current_price=50.0,
        dcf_iv=100.0,
        owner_earnings_iv=95.0,
        asset_floor_iv=90.0,
        peer_comparison_iv=105.0,
        sue_percentile=70.0,
        wacc=0.10,
    )


# ---------------------------------------------------------------------------
# Track A trajectory detection
# ---------------------------------------------------------------------------


class TestTrackATrajectoryDetection:
    """Track A cascade sets conditional=True for low-ROIC turnarounds."""

    def test_low_roic_improving_trajectory_sets_conditional(self):
        """ROIC [2%, 4%, 6%, 8%] -- median < 8%, 3 consecutive 200bps improvements.

        Should set conditional=True.
        """
        inputs = _build_track_a_inputs([0.02, 0.04, 0.06, 0.08])
        result = run_track_a_cascade(inputs)
        assert result.conditional is True

    def test_low_roic_flat_trajectory_not_conditional(self):
        """ROIC [5%, 5%, 5%, 5%] -- flat, no improvement -> conditional=False."""
        inputs = _build_track_a_inputs([0.05, 0.05, 0.05, 0.05])
        result = run_track_a_cascade(inputs)
        assert result.conditional is False

    def test_normal_roic_skips_trajectory(self):
        """ROIC [15%, 16%, 17%, 18%] -- median >= 8% -> no trajectory check -> conditional=False."""
        inputs = _build_track_a_inputs([0.15, 0.16, 0.17, 0.18])
        result = run_track_a_cascade(inputs)
        assert result.conditional is False

    def test_single_period_skips_trajectory(self):
        """Single period -> not enough data for trajectory -> conditional=False."""
        inputs = _build_track_a_inputs([0.05])
        result = run_track_a_cascade(inputs)
        assert result.conditional is False


# ---------------------------------------------------------------------------
# Track B trajectory detection
# ---------------------------------------------------------------------------


class TestTrackBTrajectoryDetection:
    """Track B cascade sets conditional=True for ROIC in [6%, 8%) with improvement."""

    def test_improving_in_6_to_8_range_sets_conditional(self):
        """ROIC [6%, 8%] -- median=7%, 200bps improvement for 1 period (needs 2).

        Use [0.05, 0.07, 0.09] so median=0.07, and two consecutive 200bps jumps.
        """
        inputs = _build_track_b_inputs([0.05, 0.07, 0.09])
        result = run_track_b_cascade(inputs)
        assert result.conditional is True

    def test_flat_in_6_to_8_range_not_conditional(self):
        """ROIC [7%, 7%, 7%] -- median=7%, no improvement -> conditional=False."""
        inputs = _build_track_b_inputs([0.07, 0.07, 0.07])
        result = run_track_b_cascade(inputs)
        assert result.conditional is False

    def test_roic_above_8_not_conditional(self):
        """ROIC [10%, 12%, 14%] -- median >= 8% -> no trajectory check -> conditional=False."""
        inputs = _build_track_b_inputs([0.10, 0.12, 0.14])
        result = run_track_b_cascade(inputs)
        assert result.conditional is False

    def test_roic_below_hard_floor_not_conditional(self):
        """ROIC [3%, 5%] -- median=4% < 6% hard floor -> conditional=False."""
        inputs = _build_track_b_inputs([0.03, 0.05])
        result = run_track_b_cascade(inputs)
        assert result.conditional is False


# ---------------------------------------------------------------------------
# Helper unit test
# ---------------------------------------------------------------------------


class TestComputeRoicSeries:
    """Unit tests for _compute_roic_series helper."""

    def test_returns_correct_roic_values(self):
        """Verify computed ROIC matches target within floating-point tolerance."""
        periods = [
            _period_with_roic(0.10, "2020-12-31"),
            _period_with_roic(0.15, "2021-12-31"),
        ]
        history = FinancialHistory(ticker="T", periods=periods)
        series = _compute_roic_series(history)
        assert len(series) == 2
        assert abs(series[0] - 0.10) < 0.001
        assert abs(series[1] - 0.15) < 0.001

    def test_skips_zero_ic_periods(self):
        """Periods with IC <= 0 should be excluded from the series."""
        p = FinancialPeriod(
            period_end="2024-12-31",
            filing_date="2025-02-15",
            current_income=IncomeStatement(
                revenue=Decimal("100"),
                ebit=Decimal("10"),
                net_income=Decimal("8"),
            ),
            current_balance=BalanceSheet(
                total_assets=Decimal("500"),
                total_equity=Decimal("50"),
                long_term_debt=Decimal("0"),
                cash_and_equivalents=Decimal("100"),  # IC = 50 + 0 - 100 = -50
            ),
            current_cash_flow=CashFlowStatement(
                operating_cash_flow=Decimal("20"),
                capital_expenditures=Decimal("-5"),
            ),
        )
        history = FinancialHistory(ticker="T", periods=[p])
        series = _compute_roic_series(history)
        assert series == []


# ---------------------------------------------------------------------------
# End-to-end: conditional caps EXCEPTIONAL to HIGH
# ---------------------------------------------------------------------------


class TestConditionalCapsConviction:
    """End-to-end: a turnaround with conditional=True should be capped at HIGH."""

    def test_track_a_trajectory_caps_exceptional_to_high(self):
        """Build Track A inputs that would reach EXCEPTIONAL without conditional,
        then use a trajectory scenario (low median ROIC + improving) and verify
        the conviction is capped to HIGH.

        EXCEPTIONAL requires: 4 gates passed, compounding_power > 0.15,
        moat_durability >= 3, growth_gap > 0.08.

        We craft data with strong fundamentals but low median ROIC to trigger
        conditional. Since conditional=True caps EXCEPTIONAL -> HIGH, the result
        should be at most HIGH.
        """
        # Build periods with low but rapidly improving ROIC.
        # The periods need strong enough fundamentals to pass gates and produce
        # high compounding_power/moat scores, but ROIC median must be < 8%.
        # This is inherently contradictory (low ROIC + high compounding_power is rare),
        # so we test through the threshold function directly as a complementary check.
        from margin_engine.scoring.v3_thresholds import assess_track_a_conviction

        # Scenario: an asset that would be EXCEPTIONAL but for the conditional flag.
        # All thresholds met: 4 gates, compounding_power=0.20, moat=4, gap=0.15
        result_unconditional = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.20,
            moat_durability=4,
            growth_gap=0.15,
            conditional=False,
        )
        assert result_unconditional == CompositeTier.EXCEPTIONAL

        # Same values but conditional=True -> capped to HIGH
        result_conditional = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.20,
            moat_durability=4,
            growth_gap=0.15,
            conditional=True,
        )
        assert result_conditional == CompositeTier.HIGH

    def test_track_a_cascade_conditional_propagates_to_conviction(self):
        """When cascade detects trajectory, conditional is passed to conviction function.

        Use ROIC trajectory that triggers conditional, and verify the result
        has conditional=True AND conviction is not EXCEPTIONAL.
        """
        inputs = _build_track_a_inputs([0.02, 0.04, 0.06, 0.08])
        result = run_track_a_cascade(inputs)
        assert result.conditional is True
        # Conviction must never be EXCEPTIONAL when conditional
        assert result.conviction != CompositeTier.EXCEPTIONAL
