"""Correction engine — L1/L2/L3 hierarchy for self-healing data layer.

For each detection flag, attempts corrections in priority order:
  L1 (substitute)     — use secondary provider value
  L2 (carry-forward)  — use prior valid value with confidence decay
  L3 (sector median)  — use cross-sectional sector median

If no level succeeds, the flag is omitted from results (no correction possible).
"""

from __future__ import annotations

from margin_engine.healing.models import (
    CorrectionEvent,
    CorrectionMethod,
    DetectionResult,
    DetectionSeverity,
    HealingConfig,
    SectorDistribution,
)


def _try_l1(
    flag: DetectionResult,
    config: HealingConfig,
    secondary_values: dict[str, float],
) -> CorrectionEvent | None:
    """Attempt L1 correction: substitute from secondary provider.

    For IMPOSSIBLE severity, any valid secondary value is accepted.
    For other severities, the secondary value must be within
    config.substitution_tolerance of the original.
    """
    if secondary_values is None or flag.field_path not in secondary_values:
        return None

    secondary_value = secondary_values[flag.field_path]

    if flag.severity == DetectionSeverity.IMPOSSIBLE:
        # Accept any valid secondary value for IMPOSSIBLE flags
        return CorrectionEvent(
            field_path=flag.field_path,
            detection_severity=flag.severity,
            detection_detail=flag.detail,
            original_value=flag.original_value,
            corrected_value=secondary_value,
            correction_method=CorrectionMethod.L1_SUBSTITUTE,
            correction_source="secondary_provider",
            correction_confidence=0.95,
        )

    # For non-IMPOSSIBLE: check tolerance
    if flag.original_value is None:
        # Cannot compute tolerance without original value
        return None

    original = flag.original_value
    if original == 0.0:
        # Avoid division by zero — use absolute difference
        diff_ratio = abs(secondary_value)
    else:
        diff_ratio = abs(secondary_value - original) / abs(original)

    if diff_ratio <= config.substitution_tolerance:
        return CorrectionEvent(
            field_path=flag.field_path,
            detection_severity=flag.severity,
            detection_detail=flag.detail,
            original_value=flag.original_value,
            corrected_value=secondary_value,
            correction_method=CorrectionMethod.L1_SUBSTITUTE,
            correction_source="secondary_provider",
            correction_confidence=0.95,
        )

    return None


def _try_l2(
    flag: DetectionResult,
    config: HealingConfig,
    prior_valid_values: dict[str, tuple[float, int]],
) -> CorrectionEvent | None:
    """Attempt L2 correction: carry forward from prior valid value.

    Skips if the prior value is too stale (quarters_stale > carry_forward_max_quarters).
    Confidence decays linearly with staleness, floored at cross_sectional_min_confidence.
    """
    if prior_valid_values is None or flag.field_path not in prior_valid_values:
        return None

    value, quarters_stale = prior_valid_values[flag.field_path]

    if quarters_stale > config.carry_forward_max_quarters:
        return None

    confidence = max(
        config.cross_sectional_min_confidence,
        1.0 - quarters_stale * config.carry_forward_decay_rate,
    )

    return CorrectionEvent(
        field_path=flag.field_path,
        detection_severity=flag.severity,
        detection_detail=flag.detail,
        original_value=flag.original_value,
        corrected_value=value,
        correction_method=CorrectionMethod.L2_CARRY_FORWARD,
        correction_source=f"self_Q-{quarters_stale}",
        correction_confidence=confidence,
    )


def _try_l3(
    flag: DetectionResult,
    config: HealingConfig,
    sector_distributions: list[SectorDistribution],
) -> CorrectionEvent | None:
    """Attempt L3 correction: sector median imputation.

    Checks both the full field_path and the base field name (last segment)
    against config.excluded_fields. If excluded, returns None.
    """
    # Extract base field name (e.g., "revenue" from "income_statement.revenue")
    base_field = flag.field_path.rsplit(".", 1)[-1] if "." in flag.field_path else flag.field_path

    # Check exclusions: both full path and base name
    if flag.field_path in config.excluded_fields or base_field in config.excluded_fields:
        return None

    if sector_distributions is None:
        return None

    # Find matching sector distribution
    for dist in sector_distributions:
        if dist.field_path == flag.field_path:
            return CorrectionEvent(
                field_path=flag.field_path,
                detection_severity=flag.severity,
                detection_detail=flag.detail,
                original_value=flag.original_value,
                corrected_value=dist.median,
                correction_method=CorrectionMethod.L3_SECTOR_MEDIAN,
                correction_source="sector_median",
                correction_confidence=0.5,
            )

    return None


def apply_corrections(
    flags: list[DetectionResult],
    config: HealingConfig,
    secondary_values: dict[str, float] | None = None,
    prior_valid_values: dict[str, tuple[float, int]] | None = None,
    sector_distributions: list[SectorDistribution] | None = None,
) -> list[CorrectionEvent]:
    """Apply L1/L2/L3 correction hierarchy to each detection flag.

    For each flag, tries L1 → L2 → L3 in order. The first successful
    correction is used. If none succeed, the flag is omitted from results.

    Args:
        flags: Detection results to correct.
        config: Healing configuration with thresholds and tolerances.
        secondary_values: Field path → secondary provider value.
        prior_valid_values: Field path → (value, quarters_stale).
        sector_distributions: Cross-sectional distributions for L3.

    Returns:
        List of CorrectionEvent for each successfully corrected flag.
    """
    corrections: list[CorrectionEvent] = []

    for flag in flags:
        # Try L1 → L2 → L3 in order
        correction = _try_l1(flag, config, secondary_values)
        if correction is None:
            correction = _try_l2(flag, config, prior_valid_values)
        if correction is None:
            correction = _try_l3(flag, config, sector_distributions)

        if correction is not None:
            corrections.append(correction)

    return corrections
