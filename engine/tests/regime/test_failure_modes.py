"""Tests for regime failure mode detectors.

TDD: these tests are written before the implementation.
"""

from __future__ import annotations

import numpy as np
import pytest

from margin_engine.regime.failure_modes import (
    FailureModeReport,
    ProCyclicalityResult,
    SignalInversionResult,
    ThresholdBrittlenessResult,
    UniverseCollapseResult,
    detect_pro_cyclicality,
    detect_signal_inversion,
    detect_threshold_brittleness,
    detect_universe_collapse,
)


# ---------------------------------------------------------------------------
# Threshold Brittleness
# ---------------------------------------------------------------------------


class TestDetectThresholdBrittleness:
    """Tests for detect_threshold_brittleness."""

    def test_high_density_near_threshold(self) -> None:
        """When many values cluster near the threshold, density_ratio > 1."""
        # 80% of values are within ±10% of the threshold (0.5)
        # Threshold margin band: 0.45 to 0.55
        values = np.array([0.48, 0.49, 0.50, 0.51, 0.52, 0.53, 0.47, 0.46, 0.10, 0.90])
        result = detect_threshold_brittleness(
            gate_name="pe_filter",
            regime_key="normal|bull|normal|normal",
            values=values,
            threshold=0.50,
            margin_pct=0.10,
        )
        assert isinstance(result, ThresholdBrittlenessResult)
        assert result.gate_name == "pe_filter"
        assert result.regime_key == "normal|bull|normal|normal"
        assert result.density_ratio > 1.0, "High clustering near threshold should yield ratio > 1"
        assert result.n_near_threshold == 8  # 0.46..0.53 all within [0.45, 0.55]
        assert result.n_total == 10

    def test_well_separated_from_threshold(self) -> None:
        """When values are far from threshold, density_ratio < 1."""
        # Values are either very low or very high, none near 0.5
        values = np.array([0.01, 0.02, 0.03, 0.04, 0.05, 0.95, 0.96, 0.97, 0.98, 0.99])
        result = detect_threshold_brittleness(
            gate_name="pe_filter",
            regime_key="crisis|bear|cheap|stress",
            values=values,
            threshold=0.50,
            margin_pct=0.10,
        )
        assert result.density_ratio < 1.0, "Well-separated values should yield ratio < 1"
        assert result.n_near_threshold == 0

    def test_empty_values_returns_zero_ratio(self) -> None:
        """Empty array should not crash; ratio should be 0."""
        values = np.array([])
        result = detect_threshold_brittleness(
            gate_name="pe_filter",
            regime_key="normal|bull|normal|normal",
            values=values,
            threshold=0.50,
        )
        assert result.density_ratio == 0.0
        assert result.n_near_threshold == 0
        assert result.n_total == 0


# ---------------------------------------------------------------------------
# Signal Inversion
# ---------------------------------------------------------------------------


class TestDetectSignalInversion:
    """Tests for detect_signal_inversion."""

    def test_inverted_signal(self) -> None:
        """TPR < 0.50 should flag inversion with FSR > 1."""
        result = detect_signal_inversion(
            gate_name="momentum_filter",
            regime_key="crisis|bear|cheap|stress",
            tpr=0.30,
            unconditional_tpr=0.80,
        )
        assert isinstance(result, SignalInversionResult)
        assert result.inverted is True
        assert result.tpr == 0.30
        assert result.unconditional_tpr == 0.80
        # FSR = (1 - 0.30) / (1 - 0.80) = 0.70 / 0.20 = 3.5
        assert result.fsr == pytest.approx(3.5, rel=1e-6)

    def test_healthy_signal(self) -> None:
        """TPR > 0.50 should NOT flag inversion."""
        result = detect_signal_inversion(
            gate_name="momentum_filter",
            regime_key="normal|bull|normal|normal",
            tpr=0.85,
            unconditional_tpr=0.80,
        )
        assert result.inverted is False
        # FSR = (1 - 0.85) / (1 - 0.80) = 0.15 / 0.20 = 0.75
        assert result.fsr == pytest.approx(0.75, rel=1e-6)

    def test_perfect_unconditional_tpr_edge_case(self) -> None:
        """When unconditional_tpr == 1.0, FSR denominator is 0 → return inf."""
        result = detect_signal_inversion(
            gate_name="x",
            regime_key="x",
            tpr=0.50,
            unconditional_tpr=1.0,
        )
        assert result.fsr == float("inf")


# ---------------------------------------------------------------------------
# Universe Collapse
# ---------------------------------------------------------------------------


class TestDetectUniverseCollapse:
    """Tests for detect_universe_collapse."""

    def test_collapsed_universe(self) -> None:
        """< 500 total survivors + sectors below threshold → collapsed."""
        sector_survivors = {
            "Technology": 100,
            "Healthcare": 8,  # below 10
            "Financials": 5,  # below 10
            "Energy": 3,  # below 10
        }
        result = detect_universe_collapse(
            regime_key="crisis|bear|expensive|stress",
            total_survivors=116,
            sector_survivors=sector_survivors,
            collapse_threshold=500,
            sector_threshold=10,
        )
        assert isinstance(result, UniverseCollapseResult)
        assert result.universe_collapsed is True
        assert set(result.sectors_collapsed) == {"Healthcare", "Financials", "Energy"}
        # top 3 = 100 + 8 + 5 = 113 out of 116
        assert result.concentration_top3_pct == pytest.approx(113 / 116 * 100, rel=1e-2)

    def test_healthy_universe(self) -> None:
        """Above threshold + healthy sectors → not collapsed."""
        sector_survivors = {
            "Technology": 200,
            "Healthcare": 150,
            "Financials": 180,
            "Energy": 120,
            "Consumer": 100,
        }
        result = detect_universe_collapse(
            regime_key="normal|bull|normal|normal",
            total_survivors=750,
            sector_survivors=sector_survivors,
        )
        assert result.universe_collapsed is False
        assert result.sectors_collapsed == []
        # top 3 = 200 + 180 + 150 = 530 out of 750
        assert result.concentration_top3_pct == pytest.approx(530 / 750 * 100, rel=1e-2)

    def test_zero_survivors(self) -> None:
        """Zero survivors should be collapsed, concentration_top3_pct = 0."""
        result = detect_universe_collapse(
            regime_key="crisis|drawdown|euphoria|stress",
            total_survivors=0,
            sector_survivors={},
        )
        assert result.universe_collapsed is True
        assert result.concentration_top3_pct == 0.0


# ---------------------------------------------------------------------------
# Pro-Cyclicality
# ---------------------------------------------------------------------------


class TestDetectProCyclicality:
    """Tests for detect_pro_cyclicality."""

    def test_positive_correlation_detected(self) -> None:
        """Strong positive correlation between survivors and returns → pro-cyclical."""
        # More survivors correlates with higher forward returns
        survivor_counts = [100, 200, 300, 400, 500, 600, 700, 800]
        forward_returns = [0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.14, 0.16]
        result = detect_pro_cyclicality(
            survivor_counts=survivor_counts,
            forward_12m_returns=forward_returns,
        )
        assert isinstance(result, ProCyclicalityResult)
        assert result.correlation > 0.3
        assert result.is_pro_cyclical is True
        assert result.n_observations == 8

    def test_too_few_observations(self) -> None:
        """Fewer than 3 observations → correlation 0.0."""
        result = detect_pro_cyclicality(
            survivor_counts=[100, 200],
            forward_12m_returns=[0.05, 0.10],
        )
        assert result.correlation == 0.0
        assert result.is_pro_cyclical is False
        assert result.n_observations == 2

    def test_negative_correlation_not_pro_cyclical(self) -> None:
        """Negative correlation → is_pro_cyclical = False."""
        survivor_counts = [100, 200, 300, 400, 500]
        forward_returns = [0.20, 0.15, 0.10, 0.05, 0.00]
        result = detect_pro_cyclicality(
            survivor_counts=survivor_counts,
            forward_12m_returns=forward_returns,
        )
        assert result.correlation < 0.0
        assert result.is_pro_cyclical is False

    def test_constant_values_zero_std(self) -> None:
        """If all survivor counts are identical (zero std), correlation = 0.0."""
        survivor_counts = [500, 500, 500, 500]
        forward_returns = [0.05, 0.10, 0.15, 0.20]
        result = detect_pro_cyclicality(
            survivor_counts=survivor_counts,
            forward_12m_returns=forward_returns,
        )
        assert result.correlation == 0.0
        assert result.is_pro_cyclical is False


# ---------------------------------------------------------------------------
# FailureModeReport model
# ---------------------------------------------------------------------------


class TestFailureModeReport:
    """Tests for the composite report model."""

    def test_empty_report(self) -> None:
        """Default report has empty lists and None pro_cyclicality."""
        report = FailureModeReport()
        assert report.brittleness == []
        assert report.inversions == []
        assert report.collapses == []
        assert report.pro_cyclicality is None

    def test_populated_report(self) -> None:
        """Report can hold results from all detectors."""
        report = FailureModeReport(
            brittleness=[
                ThresholdBrittlenessResult(
                    gate_name="pe",
                    regime_key="x",
                    density_ratio=2.0,
                    n_near_threshold=50,
                    n_total=100,
                )
            ],
            inversions=[
                SignalInversionResult(
                    gate_name="mom",
                    regime_key="x",
                    tpr=0.3,
                    unconditional_tpr=0.8,
                    inverted=True,
                    fsr=3.5,
                )
            ],
            collapses=[
                UniverseCollapseResult(
                    regime_key="x",
                    total_survivors=100,
                    universe_collapsed=True,
                    sectors_collapsed=["Energy"],
                    concentration_top3_pct=90.0,
                )
            ],
            pro_cyclicality=ProCyclicalityResult(
                correlation=0.5,
                n_observations=10,
                is_pro_cyclical=True,
            ),
        )
        assert len(report.brittleness) == 1
        assert len(report.inversions) == 1
        assert len(report.collapses) == 1
        assert report.pro_cyclicality is not None
        assert report.pro_cyclicality.is_pro_cyclical is True
