"""Sector distribution computation for the data healing pipeline.

CRITICAL: Distributions must be computed from RAW data only, never from corrected data.

This module computes per-field statistical distributions (median and MAD) within
a given sector. These baselines are used by the outlier detection layer (Tier 2)
to identify values that deviate significantly from sector norms.
"""

from __future__ import annotations

import statistics
from collections import defaultdict

from margin_engine.healing.models import SectorDistribution


def _compute_mad(values: list[float]) -> float:
    """Compute the Median Absolute Deviation (MAD) of a list of values.

    MAD = median(|v - median(values)| for v in values)

    Args:
        values: List of numeric values.

    Returns:
        The MAD value. Returns 0.0 if fewer than 2 values are provided.
    """
    if len(values) < 2:
        return 0.0
    med = statistics.median(values)
    abs_deviations = [abs(v - med) for v in values]
    return statistics.median(abs_deviations)


def compute_sector_distributions(
    ticker_field_values: dict[str, dict[str, float]],
    sector: str,
    period: str,
) -> list[SectorDistribution]:
    """Compute per-field distribution statistics for a sector.

    Groups all values by field_path across all tickers, computes the
    median and MAD for each field, and returns sorted SectorDistribution objects.

    Args:
        ticker_field_values: Mapping of ticker -> {field_path: raw_value}.
            Values are used as-is (must be raw, uncorrected data).
        sector: The GICS sector name.
        period: The period identifier (e.g., "2026-Q1").

    Returns:
        List of SectorDistribution objects sorted by field_path.
        Returns [] if input is empty.
    """
    if not ticker_field_values:
        return []

    # Group all values by field_path across all tickers
    field_values: dict[str, list[float]] = defaultdict(list)
    for _ticker, fields in ticker_field_values.items():
        for field_path, value in fields.items():
            field_values[field_path].append(value)

    # Compute distributions for each field
    distributions: list[SectorDistribution] = []
    for field_path in sorted(field_values.keys()):
        values = field_values[field_path]
        med = statistics.median(values)
        mad = _compute_mad(values)
        distributions.append(
            SectorDistribution(
                sector=sector,
                field_path=field_path,
                median=med,
                mad=mad,
                n_observations=len(values),
                period=period,
            )
        )

    return distributions
