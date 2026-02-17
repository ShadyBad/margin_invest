"""Tests for ensemble valuation — 4-method convergence for reliable intrinsic value."""

import pytest
from margin_engine.scoring.quantitative.ensemble_valuation import (
    EnsembleResult,
    compute_ensemble_valuation,
)


class TestEnsembleValuation:
    def test_all_methods_converge(self):
        """4 values within 30% of median -> all converge."""
        result = compute_ensemble_valuation(
            dcf_iv=100.0,
            owner_earnings_iv=110.0,
            asset_floor_iv=90.0,
            peer_comparison_iv=105.0,
        )
        assert result.converged is True
        assert result.converging_count == 4
        assert 90.0 <= result.ensemble_iv <= 110.0

    def test_three_converge_one_outlier(self):
        """3 values agree, 1 is an outlier -> still converges (3 >= 3)."""
        result = compute_ensemble_valuation(
            dcf_iv=100.0,
            owner_earnings_iv=110.0,
            asset_floor_iv=95.0,
            peer_comparison_iv=300.0,  # outlier
        )
        assert result.converged is True
        assert result.converging_count == 3

    def test_two_converge_fails(self):
        """Only 2 values agree -> fails convergence gate."""
        result = compute_ensemble_valuation(
            dcf_iv=100.0,
            owner_earnings_iv=105.0,
            asset_floor_iv=300.0,
            peer_comparison_iv=500.0,
        )
        assert result.converged is False
        assert result.converging_count == 2

    def test_ensemble_iv_is_median_of_converging(self):
        """Ensemble IV uses median of converging methods, not mean."""
        result = compute_ensemble_valuation(
            dcf_iv=100.0,
            owner_earnings_iv=120.0,
            asset_floor_iv=110.0,
            peer_comparison_iv=500.0,  # outlier, excluded
        )
        # Converging: 100, 110, 120 -> median = 110
        assert result.ensemble_iv == pytest.approx(110.0)

    def test_all_zero_returns_not_converged(self):
        result = compute_ensemble_valuation(
            dcf_iv=0.0,
            owner_earnings_iv=0.0,
            asset_floor_iv=0.0,
            peer_comparison_iv=0.0,
        )
        assert result.converged is False

    def test_negative_values_excluded(self):
        result = compute_ensemble_valuation(
            dcf_iv=-50.0,
            owner_earnings_iv=100.0,
            asset_floor_iv=110.0,
            peer_comparison_iv=105.0,
        )
        assert result.converged is True
        assert result.converging_count == 3

    def test_methods_dict_populated(self):
        result = compute_ensemble_valuation(
            dcf_iv=100.0,
            owner_earnings_iv=110.0,
            asset_floor_iv=90.0,
            peer_comparison_iv=105.0,
        )
        assert "dcf" in result.methods
        assert "owner_earnings" in result.methods
        assert "asset_floor" in result.methods
        assert "peer_comparison" in result.methods
