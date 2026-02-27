"""Anomaly detection functions for the self-healing data layer.

Tier 2: MAD-based outlier detection using sector cross-sectional distributions.
"""

from __future__ import annotations

from margin_engine.healing.models import (
    DetectionResult,
    DetectionSeverity,
    FieldClass,
    FIELD_CLASS_MAP,
    HealingConfig,
    SectorDistribution,
)


def _is_monotonic(values: list[float]) -> bool:
    """Return True if all diffs are positive or all diffs are negative.

    Requires at least 3 values. Constant sequences (all diffs zero) return False.
    """
    if len(values) < 3:
        return False
    diffs = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    all_positive = all(d > 0 for d in diffs)
    all_negative = all(d < 0 for d in diffs)
    return all_positive or all_negative


def _get_threshold(field_path: str, config: HealingConfig) -> float:
    """Look up the MAD threshold for a field via FIELD_CLASS_MAP.

    Unknown fields default to the growth_rates threshold (most conservative).
    """
    field_class = FIELD_CLASS_MAP.get(field_path)
    if field_class is None:
        return config.tier2_mad_thresholds[FieldClass.GROWTH_RATES.value.lower()]
    return config.tier2_mad_thresholds[field_class.value.lower()]


def detect_tier2(
    field_values: dict[str, float],
    sector_distributions: list[SectorDistribution],
    config: HealingConfig,
    trailing_values: dict[str, list[float]] | None = None,
) -> list[DetectionResult]:
    """Detect outliers using MAD-based deviation from sector distributions.

    For each field in field_values:
    1. Look up its SectorDistribution from the list.
    2. Skip if no distribution found or MAD is 0.0.
    3. Compute deviation = abs(value - median) / mad.
    4. Look up threshold from config via FIELD_CLASS_MAP.
    5. If trailing_values provided with 3+ monotonic values, widen threshold.
    6. If deviation > threshold, flag as OUTLIER.

    Args:
        field_values: Mapping of field_path to its current value.
        sector_distributions: Cross-sectional distributions for the sector.
        config: Healing configuration with thresholds.
        trailing_values: Optional historical values for trend detection.

    Returns:
        List of DetectionResult for fields that exceed their threshold.
    """
    # Index distributions by field_path for O(1) lookup
    dist_by_field: dict[str, SectorDistribution] = {
        d.field_path: d for d in sector_distributions
    }

    results: list[DetectionResult] = []

    for field_path, value in field_values.items():
        dist = dist_by_field.get(field_path)
        if dist is None:
            continue
        if dist.mad == 0.0:
            continue

        deviation = abs(value - dist.median) / dist.mad
        threshold = _get_threshold(field_path, config)

        # Widen threshold if trailing values show a monotonic trend
        if trailing_values is not None:
            trail = trailing_values.get(field_path)
            if trail is not None and _is_monotonic(trail):
                threshold *= config.trend_threshold_multiplier

        if deviation > threshold:
            results.append(
                DetectionResult(
                    field_path=field_path,
                    severity=DetectionSeverity.OUTLIER,
                    detail=(
                        f"MAD deviation {deviation:.2f} exceeds threshold {threshold:.2f} "
                        f"(median={dist.median}, mad={dist.mad})"
                    ),
                    original_value=value,
                    mad_deviation=deviation,
                )
            )

    return results
