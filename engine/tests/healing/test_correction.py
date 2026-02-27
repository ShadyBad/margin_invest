"""Tests for correction engine — L1/L2/L3 hierarchy.

Covers:
- L1: substitute from secondary provider, rejected beyond tolerance, accepted for IMPOSSIBLE
- L2: carry forward 1 quarter (confidence ~0.85), 4 quarters (confidence ~0.40), too stale → L3
- L3: sector median applied, excluded field NOT imputed
- No sources available → no correction returned
"""

from __future__ import annotations

import pytest

from margin_engine.healing.correction import apply_corrections, _try_l1, _try_l2, _try_l3
from margin_engine.healing.models import (
    CorrectionEvent,
    CorrectionMethod,
    DetectionResult,
    DetectionSeverity,
    EXCLUDED_FIELDS,
    HealingConfig,
    SectorDistribution,
)


@pytest.fixture
def config() -> HealingConfig:
    return HealingConfig()


@pytest.fixture
def outlier_flag() -> DetectionResult:
    return DetectionResult(
        field_path="income_statement.gross_margin",
        severity=DetectionSeverity.OUTLIER,
        detail="MAD deviation 7.2",
        original_value=0.90,
    )


@pytest.fixture
def impossible_flag() -> DetectionResult:
    return DetectionResult(
        field_path="income_statement.gross_margin",
        severity=DetectionSeverity.IMPOSSIBLE,
        detail="Gross margin > 1.0",
        original_value=1.50,
    )


@pytest.fixture
def sector_dist() -> list[SectorDistribution]:
    return [
        SectorDistribution(
            sector="Technology",
            field_path="income_statement.gross_margin",
            median=0.55,
            mad=0.08,
            n_observations=40,
            period="2025-Q4",
        ),
    ]


# ─── L1 Tests ───────────────────────────────────────────────────────


class TestL1Substitute:
    """L1 correction: substitute from secondary provider."""

    def test_l1_accepted_within_tolerance(
        self, outlier_flag: DetectionResult, config: HealingConfig
    ):
        """Secondary value within 20% of original → L1 accepted."""
        secondary = {"income_statement.gross_margin": 0.85}
        result = apply_corrections(
            flags=[outlier_flag],
            config=config,
            secondary_values=secondary,
            prior_valid_values={},
            sector_distributions=[],
        )
        assert len(result) == 1
        evt = result[0]
        assert evt.correction_method == CorrectionMethod.L1_SUBSTITUTE
        assert evt.corrected_value == 0.85
        assert evt.correction_confidence == 0.95
        assert evt.correction_source == "secondary_provider"
        assert evt.field_path == "income_statement.gross_margin"

    def test_l1_rejected_beyond_tolerance(
        self, outlier_flag: DetectionResult, config: HealingConfig, sector_dist: list
    ):
        """Secondary value beyond 20% of original → L1 rejected, falls to L2/L3."""
        secondary = {"income_statement.gross_margin": 0.50}  # 0.50 vs 0.90 = 44% diff
        result = apply_corrections(
            flags=[outlier_flag],
            config=config,
            secondary_values=secondary,
            prior_valid_values={},
            sector_distributions=sector_dist,
        )
        assert len(result) == 1
        # Should fall through to L3 since no prior_valid_values
        assert result[0].correction_method == CorrectionMethod.L3_SECTOR_MEDIAN

    def test_l1_accepted_for_impossible_regardless_of_tolerance(
        self, impossible_flag: DetectionResult, config: HealingConfig
    ):
        """IMPOSSIBLE severity accepts any valid secondary value, even beyond tolerance."""
        # 0.60 vs 1.50 = 60% diff, but IMPOSSIBLE accepts anything
        secondary = {"income_statement.gross_margin": 0.60}
        result = apply_corrections(
            flags=[impossible_flag],
            config=config,
            secondary_values=secondary,
            prior_valid_values={},
            sector_distributions=[],
        )
        assert len(result) == 1
        evt = result[0]
        assert evt.correction_method == CorrectionMethod.L1_SUBSTITUTE
        assert evt.corrected_value == 0.60
        assert evt.correction_confidence == 0.95

    def test_l1_helper_returns_none_when_no_secondary(
        self, outlier_flag: DetectionResult, config: HealingConfig
    ):
        """_try_l1 returns None when secondary_values has no matching field."""
        result = _try_l1(outlier_flag, config, {})
        assert result is None


# ─── L2 Tests ───────────────────────────────────────────────────────


class TestL2CarryForward:
    """L2 correction: carry forward from prior valid value."""

    def test_l2_one_quarter_stale(
        self, outlier_flag: DetectionResult, config: HealingConfig
    ):
        """Carry forward 1 quarter → confidence = max(0.3, 1.0 - 1*0.15) = 0.85."""
        prior = {"income_statement.gross_margin": (0.52, 1)}
        result = apply_corrections(
            flags=[outlier_flag],
            config=config,
            secondary_values={},
            prior_valid_values=prior,
            sector_distributions=[],
        )
        assert len(result) == 1
        evt = result[0]
        assert evt.correction_method == CorrectionMethod.L2_CARRY_FORWARD
        assert evt.corrected_value == 0.52
        assert evt.correction_confidence == pytest.approx(0.85)
        assert evt.correction_source == "self_Q-1"

    def test_l2_four_quarters_stale(
        self, outlier_flag: DetectionResult, config: HealingConfig
    ):
        """Carry forward 4 quarters → confidence = max(0.3, 1.0 - 4*0.15) = 0.40."""
        prior = {"income_statement.gross_margin": (0.48, 4)}
        result = apply_corrections(
            flags=[outlier_flag],
            config=config,
            secondary_values={},
            prior_valid_values=prior,
            sector_distributions=[],
        )
        assert len(result) == 1
        evt = result[0]
        assert evt.correction_method == CorrectionMethod.L2_CARRY_FORWARD
        assert evt.corrected_value == 0.48
        assert evt.correction_confidence == pytest.approx(0.40)
        assert evt.correction_source == "self_Q-4"

    def test_l2_too_stale_falls_to_l3(
        self, outlier_flag: DetectionResult, config: HealingConfig, sector_dist: list
    ):
        """Carry forward 5 quarters (> max 4) → skip L2, falls to L3."""
        prior = {"income_statement.gross_margin": (0.48, 5)}
        result = apply_corrections(
            flags=[outlier_flag],
            config=config,
            secondary_values={},
            prior_valid_values=prior,
            sector_distributions=sector_dist,
        )
        assert len(result) == 1
        evt = result[0]
        assert evt.correction_method == CorrectionMethod.L3_SECTOR_MEDIAN
        assert evt.corrected_value == 0.55  # sector median

    def test_l2_helper_returns_none_when_no_prior(
        self, outlier_flag: DetectionResult, config: HealingConfig
    ):
        """_try_l2 returns None when prior_valid_values has no matching field."""
        result = _try_l2(outlier_flag, config, {})
        assert result is None


# ─── L3 Tests ───────────────────────────────────────────────────────


class TestL3SectorMedian:
    """L3 correction: sector median imputation."""

    def test_l3_sector_median_applied(
        self,
        outlier_flag: DetectionResult,
        config: HealingConfig,
        sector_dist: list[SectorDistribution],
    ):
        """L3 applies sector median when L1 and L2 unavailable."""
        result = apply_corrections(
            flags=[outlier_flag],
            config=config,
            secondary_values={},
            prior_valid_values={},
            sector_distributions=sector_dist,
        )
        assert len(result) == 1
        evt = result[0]
        assert evt.correction_method == CorrectionMethod.L3_SECTOR_MEDIAN
        assert evt.corrected_value == 0.55
        assert evt.correction_confidence == 0.5
        assert evt.correction_source == "sector_median"

    def test_l3_excluded_field_not_imputed(self, config: HealingConfig):
        """Revenue is in EXCLUDED_FIELDS → L3 must not impute."""
        flag = DetectionResult(
            field_path="income_statement.revenue",
            severity=DetectionSeverity.OUTLIER,
            detail="MAD deviation 8.0",
            original_value=1000000.0,
        )
        dist = SectorDistribution(
            sector="Technology",
            field_path="income_statement.revenue",
            median=500000.0,
            mad=100000.0,
            n_observations=30,
            period="2025-Q4",
        )
        result = apply_corrections(
            flags=[flag],
            config=config,
            secondary_values={},
            prior_valid_values={},
            sector_distributions=[dist],
        )
        # No correction possible — excluded from L3
        assert len(result) == 0

    def test_l3_excluded_by_base_field_name(self, config: HealingConfig):
        """Field path 'balance_sheet.total_equity' — base name 'total_equity' is excluded."""
        flag = DetectionResult(
            field_path="balance_sheet.total_equity",
            severity=DetectionSeverity.OUTLIER,
            detail="Outlier detected",
            original_value=5000000.0,
        )
        dist = SectorDistribution(
            sector="Technology",
            field_path="balance_sheet.total_equity",
            median=3000000.0,
            mad=500000.0,
            n_observations=30,
            period="2025-Q4",
        )
        result = apply_corrections(
            flags=[flag],
            config=config,
            secondary_values={},
            prior_valid_values={},
            sector_distributions=[dist],
        )
        assert len(result) == 0

    def test_l3_helper_returns_none_when_no_matching_distribution(
        self, outlier_flag: DetectionResult, config: HealingConfig
    ):
        """_try_l3 returns None when sector_distributions has no match."""
        result = _try_l3(outlier_flag, config, [])
        assert result is None


# ─── No Sources Available ───────────────────────────────────────────


class TestNoCorrection:
    """No correction possible → omit from results."""

    def test_no_sources_returns_empty(
        self, outlier_flag: DetectionResult, config: HealingConfig
    ):
        """When no secondary, no prior, no sector distribution, result is empty."""
        result = apply_corrections(
            flags=[outlier_flag],
            config=config,
            secondary_values={},
            prior_valid_values={},
            sector_distributions=[],
        )
        assert len(result) == 0

    def test_multiple_flags_partial_correction(self, config: HealingConfig):
        """Multiple flags: one correctable, one not → only correctable returned."""
        flag_correctable = DetectionResult(
            field_path="income_statement.gross_margin",
            severity=DetectionSeverity.OUTLIER,
            detail="MAD deviation 7.0",
            original_value=0.90,
        )
        flag_uncorrectable = DetectionResult(
            field_path="derived.some_obscure_metric",
            severity=DetectionSeverity.SUSPICIOUS,
            detail="Suspicious value",
            original_value=999.0,
        )
        secondary = {"income_statement.gross_margin": 0.85}
        result = apply_corrections(
            flags=[flag_correctable, flag_uncorrectable],
            config=config,
            secondary_values=secondary,
            prior_valid_values={},
            sector_distributions=[],
        )
        assert len(result) == 1
        assert result[0].field_path == "income_statement.gross_margin"


# ─── L1 tolerance edge cases ────────────────────────────────────────


class TestL1ToleranceEdgeCases:
    """Edge cases for L1 substitution tolerance."""

    def test_l1_exactly_at_tolerance_boundary(self, config: HealingConfig):
        """Secondary value exactly at 20% diff → should be accepted."""
        flag = DetectionResult(
            field_path="income_statement.gross_margin",
            severity=DetectionSeverity.OUTLIER,
            detail="Outlier",
            original_value=1.0,
        )
        # 1.0 * 0.20 = 0.20, so 0.80 is exactly at boundary
        secondary = {"income_statement.gross_margin": 0.80}
        result = apply_corrections(
            flags=[flag],
            config=config,
            secondary_values=secondary,
            prior_valid_values={},
            sector_distributions=[],
        )
        assert len(result) == 1
        assert result[0].correction_method == CorrectionMethod.L1_SUBSTITUTE

    def test_l1_original_value_none_impossible(self, config: HealingConfig):
        """When original_value is None and severity is IMPOSSIBLE, accept any secondary."""
        flag = DetectionResult(
            field_path="income_statement.gross_margin",
            severity=DetectionSeverity.IMPOSSIBLE,
            detail="Missing value",
            original_value=None,
        )
        secondary = {"income_statement.gross_margin": 0.55}
        result = apply_corrections(
            flags=[flag],
            config=config,
            secondary_values=secondary,
            prior_valid_values={},
            sector_distributions=[],
        )
        assert len(result) == 1
        assert result[0].correction_method == CorrectionMethod.L1_SUBSTITUTE
        assert result[0].corrected_value == 0.55

    def test_l1_original_value_none_non_impossible_rejected(self, config: HealingConfig):
        """When original_value is None and severity is not IMPOSSIBLE, cannot compute tolerance."""
        flag = DetectionResult(
            field_path="income_statement.gross_margin",
            severity=DetectionSeverity.OUTLIER,
            detail="Missing",
            original_value=None,
        )
        secondary = {"income_statement.gross_margin": 0.55}
        # Can't compute % difference without original → L1 fails, no L2/L3 → empty
        result = apply_corrections(
            flags=[flag],
            config=config,
            secondary_values=secondary,
            prior_valid_values={},
            sector_distributions=[],
        )
        # Falls through to L2/L3, but none available → empty
        assert len(result) == 0


# ─── L2 confidence formula ──────────────────────────────────────────


class TestL2ConfidenceFormula:
    """Verify L2 confidence = max(cross_sectional_min_confidence, 1.0 - q * decay)."""

    def test_l2_confidence_floor_applied(self, config: HealingConfig):
        """When decay would go below min_confidence, floor is applied."""
        # With default decay 0.15 and min_confidence 0.3:
        # 1.0 - 4 * 0.15 = 0.40 > 0.30 → use 0.40
        # But with 5+ quarters, it's rejected entirely (stale).
        # Let's test a custom config with higher decay
        custom = HealingConfig(carry_forward_decay_rate=0.30, carry_forward_max_quarters=5)
        flag = DetectionResult(
            field_path="income_statement.gross_margin",
            severity=DetectionSeverity.OUTLIER,
            detail="Outlier",
            original_value=0.90,
        )
        prior = {"income_statement.gross_margin": (0.50, 3)}
        # 1.0 - 3 * 0.30 = 0.10 < 0.30 → floor to 0.30
        result = apply_corrections(
            flags=[flag],
            config=custom,
            secondary_values={},
            prior_valid_values=prior,
            sector_distributions=[],
        )
        assert len(result) == 1
        assert result[0].correction_confidence == pytest.approx(0.3)


# ─── Full hierarchy fallthrough ─────────────────────────────────────


class TestHierarchyFallthrough:
    """Test the full L1 → L2 → L3 fallthrough behavior."""

    def test_l1_preferred_over_l2_and_l3(
        self, config: HealingConfig, sector_dist: list[SectorDistribution]
    ):
        """When all levels available, L1 wins."""
        flag = DetectionResult(
            field_path="income_statement.gross_margin",
            severity=DetectionSeverity.OUTLIER,
            detail="Outlier",
            original_value=0.90,
        )
        result = apply_corrections(
            flags=[flag],
            config=config,
            secondary_values={"income_statement.gross_margin": 0.85},
            prior_valid_values={"income_statement.gross_margin": (0.52, 1)},
            sector_distributions=sector_dist,
        )
        assert len(result) == 1
        assert result[0].correction_method == CorrectionMethod.L1_SUBSTITUTE

    def test_l2_used_when_l1_fails(
        self, config: HealingConfig, sector_dist: list[SectorDistribution]
    ):
        """L1 beyond tolerance → L2 carry-forward used."""
        flag = DetectionResult(
            field_path="income_statement.gross_margin",
            severity=DetectionSeverity.OUTLIER,
            detail="Outlier",
            original_value=0.90,
        )
        result = apply_corrections(
            flags=[flag],
            config=config,
            secondary_values={"income_statement.gross_margin": 0.50},  # 44% off → rejected
            prior_valid_values={"income_statement.gross_margin": (0.52, 2)},
            sector_distributions=sector_dist,
        )
        assert len(result) == 1
        assert result[0].correction_method == CorrectionMethod.L2_CARRY_FORWARD

    def test_l3_used_when_l1_and_l2_fail(
        self, config: HealingConfig, sector_dist: list[SectorDistribution]
    ):
        """L1 beyond tolerance, L2 too stale → L3 sector median."""
        flag = DetectionResult(
            field_path="income_statement.gross_margin",
            severity=DetectionSeverity.OUTLIER,
            detail="Outlier",
            original_value=0.90,
        )
        result = apply_corrections(
            flags=[flag],
            config=config,
            secondary_values={"income_statement.gross_margin": 0.50},  # rejected
            prior_valid_values={"income_statement.gross_margin": (0.52, 5)},  # too stale
            sector_distributions=sector_dist,
        )
        assert len(result) == 1
        assert result[0].correction_method == CorrectionMethod.L3_SECTOR_MEDIAN
