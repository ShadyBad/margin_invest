"""Tests for regime robustness validation functions."""

from __future__ import annotations

import pytest

from margin_engine.regime.robustness import (
    BoundarySensitivityResult,
    CrisisLeaveOneOutResult,
    RegimeCompletenessResult,
    check_boundary_sensitivity,
    crisis_leave_one_out,
    check_regime_completeness,
    _MAX_ACCEPTABLE_RANK_CHANGE,
    _PDR_CHANGE_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Boundary sensitivity tests
# ---------------------------------------------------------------------------


class TestCheckBoundarySensitivity:
    """Tests for check_boundary_sensitivity."""

    def test_stable_rankings_no_change(self) -> None:
        """When all perturbations produce identical rankings, result is stable."""
        baseline = {"momentum": 1, "value": 2, "quality": 3}
        # Two perturbations that are identical to baseline
        perturbed = [
            {"momentum": 1, "value": 2, "quality": 3},
            {"momentum": 1, "value": 2, "quality": 3},
        ]
        result = check_boundary_sensitivity(
            baseline_rankings=baseline,
            perturbed_rankings=perturbed,
        )
        assert isinstance(result, BoundarySensitivityResult)
        assert result.is_stable is True
        assert result.max_rank_change == 0
        assert result.gates_with_rank_change == []

    def test_stable_rankings_change_within_threshold(self) -> None:
        """Rank change of exactly 1 is still considered stable."""
        baseline = {"momentum": 1, "value": 2, "quality": 3}
        perturbed = [
            {"momentum": 2, "value": 1, "quality": 3},  # momentum +1, value -1
        ]
        result = check_boundary_sensitivity(
            baseline_rankings=baseline,
            perturbed_rankings=perturbed,
        )
        assert result.is_stable is True
        assert result.max_rank_change == 1
        assert result.gates_with_rank_change == []

    def test_unstable_rankings_large_change(self) -> None:
        """Rank change >= 2 triggers instability."""
        baseline = {"momentum": 1, "value": 2, "quality": 3}
        perturbed = [
            {"momentum": 3, "value": 2, "quality": 1},  # momentum +2, quality -2
        ]
        result = check_boundary_sensitivity(
            baseline_rankings=baseline,
            perturbed_rankings=perturbed,
        )
        assert result.is_stable is False
        assert result.max_rank_change >= 2
        # Both momentum and quality changed by 2
        assert "momentum" in result.gates_with_rank_change
        assert "quality" in result.gates_with_rank_change

    def test_empty_perturbations_stable(self) -> None:
        """No perturbations means stable by default."""
        baseline = {"momentum": 1, "value": 2}
        result = check_boundary_sensitivity(
            baseline_rankings=baseline,
            perturbed_rankings=[],
        )
        assert result.is_stable is True
        assert result.max_rank_change == 0


# ---------------------------------------------------------------------------
# Crisis leave-one-out tests
# ---------------------------------------------------------------------------


class TestCrisisLeaveOneOut:
    """Tests for crisis_leave_one_out."""

    def test_all_crises_stable(self) -> None:
        """When no crisis removal causes large PDR change, result is robust."""
        full_pdr = {"momentum": 0.50, "value": 0.30}
        leave_out = {
            "gfc_2008": {"momentum": 0.48, "value": 0.29},
            "covid_2020": {"momentum": 0.52, "value": 0.31},
        }
        result = crisis_leave_one_out(
            full_pdr_rankings=full_pdr,
            leave_out_pdr_rankings=leave_out,
        )
        assert isinstance(result, CrisisLeaveOneOutResult)
        assert result.is_robust is True
        assert result.sensitive_to_crisis == []
        # Should still have pdr_change_by_crisis entries
        assert "gfc_2008" in result.pdr_change_by_crisis
        assert "covid_2020" in result.pdr_change_by_crisis

    def test_one_crisis_dominates_gate(self) -> None:
        """When removing a crisis causes >50% relative PDR change, it's sensitive."""
        full_pdr = {"momentum": 1.00, "value": 0.30}
        leave_out = {
            # Removing GFC causes momentum PDR to drop to 0.40 (60% change)
            "gfc_2008": {"momentum": 0.40, "value": 0.29},
            "covid_2020": {"momentum": 0.95, "value": 0.28},
        }
        result = crisis_leave_one_out(
            full_pdr_rankings=full_pdr,
            leave_out_pdr_rankings=leave_out,
        )
        assert result.is_robust is False
        assert "gfc_2008" in result.sensitive_to_crisis
        assert "covid_2020" not in result.sensitive_to_crisis

    def test_zero_full_pdr_no_division_error(self) -> None:
        """Gate with zero full PDR should not cause division by zero."""
        full_pdr = {"momentum": 0.0, "value": 0.30}
        leave_out = {
            "gfc_2008": {"momentum": 0.10, "value": 0.29},
        }
        result = crisis_leave_one_out(
            full_pdr_rankings=full_pdr,
            leave_out_pdr_rankings=leave_out,
        )
        # Should not raise; zero-PDR gates are treated as infinite relative change
        # or handled gracefully
        assert isinstance(result, CrisisLeaveOneOutResult)


# ---------------------------------------------------------------------------
# Regime completeness tests
# ---------------------------------------------------------------------------


class TestCheckRegimeCompleteness:
    """Tests for check_regime_completeness."""

    def test_low_residual_is_complete(self) -> None:
        """Within-regime variance 0.02 / total 0.10 = 0.2 => complete."""
        result = check_regime_completeness(
            total_variance=0.10,
            within_regime_variance=0.02,
        )
        assert isinstance(result, RegimeCompletenessResult)
        assert result.is_complete is True
        assert result.residual_ratio == pytest.approx(0.2)

    def test_high_residual_is_incomplete(self) -> None:
        """Within-regime variance 0.08 / total 0.10 = 0.8 => incomplete."""
        result = check_regime_completeness(
            total_variance=0.10,
            within_regime_variance=0.08,
        )
        assert result.is_complete is False
        assert result.residual_ratio == pytest.approx(0.8)

    def test_zero_total_variance_is_complete(self) -> None:
        """Zero total variance => residual_ratio = 0.0 => complete."""
        result = check_regime_completeness(
            total_variance=0.0,
            within_regime_variance=0.0,
        )
        assert result.is_complete is True
        assert result.residual_ratio == 0.0

    def test_exactly_at_boundary(self) -> None:
        """Residual ratio exactly 0.5 should be incomplete (threshold is strict <)."""
        result = check_regime_completeness(
            total_variance=1.0,
            within_regime_variance=0.5,
        )
        assert result.is_complete is False
        assert result.residual_ratio == pytest.approx(0.5)
