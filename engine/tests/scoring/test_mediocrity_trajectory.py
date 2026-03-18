"""Tests for mediocrity gate trajectory override (conditional pass for turnarounds)."""

from decimal import Decimal

from margin_engine.config.v3_scoring_config import MediocracyTrajectoryConfig
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import GrowthStage
from margin_engine.scoring.filters.mediocrity_gate import mediocrity_gate


def _make_period(
    year: int,
    ebit: Decimal = Decimal("200"),
    revenue: Decimal = Decimal("1000"),
    cfo: Decimal = Decimal("250"),
    gross_margin_pct: float = 0.40,
) -> FinancialPeriod:
    """Create a FinancialPeriod with given parameters. Defaults produce a quality business."""
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
    """Create a FinancialHistory that fails the static mediocrity gate on ROIC.

    Low EBIT (20) on equity=500, debt=200, cash=100 gives ROIC ~2.6% << 8%.
    """
    return FinancialHistory(
        ticker="FAIL",
        periods=[_make_period(y, ebit=Decimal("20")) for y in range(2019, 2024)],
    )


class TestPassingCompanyNoConditional:
    def test_passing_company_no_conditional(self):
        """Company meeting all static thresholds -> passed=True, conditional=False."""
        history = FinancialHistory(
            ticker="GOOD",
            periods=[_make_period(y) for y in range(2019, 2024)],
        )
        result = mediocrity_gate(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True
        assert result.conditional is False


class TestROICTrajectoryConditional:
    def test_roic_trajectory_conditional(self):
        """Static fail + ROIC improving 200bps+/quarter for 3 consecutive -> conditional=True."""
        history = _make_failing_history()
        # 4 quarters: each jumps by 200bps (0.02) → 3 consecutive improvements >=200bps
        roic_q = [0.04, 0.06, 0.08, 0.10]
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=roic_q,
        )
        assert result.passed is False
        assert result.conditional is True
        assert result.computed_metrics is not None
        assert result.computed_metrics["conditional_score_multiplier"] == 0.90


class TestFCFInflectionConditional:
    def test_fcf_inflection_conditional(self):
        """FCF positive in most recent 2 quarters after negative priors -> conditional=True."""
        history = _make_failing_history()
        fcf_q = [-100.0, -80.0, -50.0, -20.0, 30.0, 50.0]
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            fcf_quarterly=fcf_q,
        )
        assert result.passed is False
        assert result.conditional is True
        assert result.computed_metrics is not None
        assert result.computed_metrics["conditional_score_multiplier"] == 0.90


class TestTurnaroundPositiveTrajectory:
    def test_turnaround_positive_trajectory(self):
        """TURNAROUND stage + any positive ROIC trajectory -> conditional=True."""
        history = _make_failing_history()
        roic_q = [0.02, 0.03]  # Any positive trajectory (most recent > earliest)
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=roic_q,
            growth_stage=GrowthStage.TURNAROUND,
        )
        assert result.passed is False
        assert result.conditional is True

    def test_high_growth_positive_trajectory(self):
        """HIGH_GROWTH stage + positive ROIC trajectory -> conditional=True."""
        history = _make_failing_history()
        roic_q = [0.02, 0.03]
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=roic_q,
            growth_stage=GrowthStage.HIGH_GROWTH,
        )
        assert result.passed is False
        assert result.conditional is True

    def test_turnaround_flat_trajectory_no_conditional(self):
        """TURNAROUND stage but flat/declining ROIC -> no conditional."""
        history = _make_failing_history()
        roic_q = [0.03, 0.03]  # Flat, not positive
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=roic_q,
            growth_stage=GrowthStage.TURNAROUND,
        )
        assert result.conditional is False

    def test_mature_stage_no_override(self):
        """MATURE stage does NOT get growth stage override."""
        history = _make_failing_history()
        roic_q = [0.02, 0.05]  # Positive trajectory but wrong stage
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=roic_q,
            growth_stage=GrowthStage.MATURE,
        )
        # Could still get conditional from ROIC trajectory if delta is big enough,
        # but not from the growth_stage override path specifically.
        # This test checks that MATURE alone doesn't trigger growth_stage override.
        # With delta of 0.03 over 2 quarters, that's only 1 consecutive improvement,
        # not enough for the ROIC trajectory rule (needs 3).
        assert result.conditional is False


class TestAllTrajectoryFail:
    def test_all_trajectory_fail(self):
        """Flat ROIC, below-threshold GM, always-negative FCF -> no conditional."""
        history = _make_failing_history()
        roic_q = [0.03, 0.03, 0.03, 0.03]  # Flat, no improvement
        gm_q = [0.10, 0.10, 0.10, 0.10]  # Far below threshold, not expanding
        fcf_q = [-100.0, -90.0, -80.0, -70.0, -60.0, -50.0]  # All negative
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=roic_q,
            gm_quarterly=gm_q,
            fcf_quarterly=fcf_q,
        )
        assert result.passed is False
        assert result.conditional is False


class TestBackwardCompatible:
    def test_backward_compatible(self):
        """No quarterly data -> conditional=False (static gate only)."""
        history = _make_failing_history()
        result = mediocrity_gate(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is False
        assert result.conditional is False

    def test_backward_compatible_passing(self):
        """Passing company with no quarterly data -> works normally."""
        history = FinancialHistory(
            ticker="GOOD",
            periods=[_make_period(y) for y in range(2019, 2024)],
        )
        result = mediocrity_gate(history, sector=GICSSector.TECHNOLOGY)
        assert result.passed is True
        assert result.conditional is False


class TestGMApproachingConditional:
    def test_gm_approaching_conditional(self):
        """GM within 3% of sector threshold AND expanding 300bps+/year -> conditional=True.

        For TECHNOLOGY sector, threshold=20%. GM at 18% is within 3%.
        With 4 quarters showing expansion from 17% to 20%, annualized expansion
        = (0.20 - 0.17) = 3% = 300bps over 1 year -> meets threshold.
        """
        history = _make_failing_history()
        gm_q = [0.17, 0.1775, 0.185, 0.20]  # 4 quarters, expanding ~300bps/year
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            gm_quarterly=gm_q,
        )
        assert result.passed is False
        assert result.conditional is True
        assert result.computed_metrics is not None
        assert result.computed_metrics["conditional_score_multiplier"] == 0.90

    def test_gm_not_approaching_no_conditional(self):
        """GM far below threshold -> no conditional even if expanding."""
        history = _make_failing_history()
        gm_q = [0.05, 0.06, 0.07, 0.08]  # Expanding but too far from 20%
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            gm_quarterly=gm_q,
        )
        assert result.conditional is False

    def test_gm_near_but_not_expanding_no_conditional(self):
        """GM near threshold but flat -> no conditional."""
        history = _make_failing_history()
        gm_q = [0.18, 0.18, 0.18, 0.18]  # Near threshold but flat
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            gm_quarterly=gm_q,
        )
        assert result.conditional is False


class TestNaNHandling:
    def test_nan_in_roic_quarterly_filtered(self):
        """NaN values in roic_quarterly are filtered out before processing."""
        history = _make_failing_history()
        roic_q = [0.04, float("nan"), 0.06, 0.08, 0.10]
        # After filtering NaN: [0.04, 0.06, 0.08, 0.10] -> 3 consecutive 200bps+ -> conditional
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=roic_q,
        )
        assert result.passed is False
        assert result.conditional is True

    def test_nan_in_fcf_quarterly_filtered(self):
        """NaN values in fcf_quarterly are filtered out."""
        history = _make_failing_history()
        fcf_q = [-100.0, float("nan"), -50.0, float("nan"), 30.0, 50.0]
        # After filtering: [-100.0, -50.0, 30.0, 50.0]
        # Last 2 positive, priors negative -> conditional
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            fcf_quarterly=fcf_q,
        )
        assert result.passed is False
        assert result.conditional is True

    def test_all_nan_no_crash(self):
        """All-NaN quarterly series should not crash, just no conditional."""
        history = _make_failing_history()
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=[float("nan"), float("nan")],
            gm_quarterly=[float("nan")],
            fcf_quarterly=[float("nan"), float("nan")],
        )
        assert result.passed is False
        assert result.conditional is False

    def test_inf_values_filtered(self):
        """Inf values are also filtered out by math.isfinite()."""
        history = _make_failing_history()
        roic_q = [0.04, float("inf"), 0.06, 0.08, 0.10]
        # After filtering: [0.04, 0.06, 0.08, 0.10] -> conditional
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=roic_q,
        )
        assert result.conditional is True


class TestCustomConfig:
    def test_custom_config_multiplier(self):
        """Custom config with different multiplier is reflected in computed_metrics."""
        history = _make_failing_history()
        config = MediocracyTrajectoryConfig(conditional_score_multiplier=0.85)
        roic_q = [0.04, 0.06, 0.08, 0.10]
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=roic_q,
            config=config,
        )
        assert result.conditional is True
        assert result.computed_metrics is not None
        assert result.computed_metrics["conditional_score_multiplier"] == 0.85

    def test_custom_config_stricter_roic_delta(self):
        """Stricter ROIC delta per quarter -> marginal improvement no longer qualifies."""
        history = _make_failing_history()
        config = MediocracyTrajectoryConfig(roic_min_delta_per_quarter=0.05)
        # Each step is only 200bps (0.02), less than 500bps (0.05) -> no conditional
        roic_q = [0.04, 0.06, 0.08, 0.10]
        result = mediocrity_gate(
            history,
            sector=GICSSector.TECHNOLOGY,
            roic_quarterly=roic_q,
            config=config,
        )
        assert result.conditional is False
