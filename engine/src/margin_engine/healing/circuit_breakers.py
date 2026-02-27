"""Circuit breakers — breadth suspension and variance guard.

These functions act as safety valves for the healing pipeline:
- Breadth suspension: halt corrections when too many tickers in a sector are flagged
  (suggests a systematic data issue, not individual anomalies).
- Variance guard: warn when corrections compress the distribution excessively
  (corrections should fix outliers, not flatten the signal).
"""

from __future__ import annotations

import statistics

from margin_engine.healing.models import HealingConfig


def check_sector_breadth(
    flagged_tickers: set[str],
    sector_size: int,
    config: HealingConfig,
) -> bool:
    """Return True if corrections should be SUSPENDED for this sector.

    When a large fraction of a sector's tickers are flagged, the anomalies are
    likely systemic (e.g., a data-provider glitch or a genuine regime shift)
    rather than individual ticker errors.  Correcting them would destroy
    legitimate cross-sectional variation.

    Args:
        flagged_tickers: Set of ticker symbols flagged as anomalous.
        sector_size: Total number of tickers in the sector.
        config: Healing configuration with ``sector_breadth_threshold``.

    Returns:
        True if the flagged fraction meets or exceeds the threshold (suspend
        corrections); False otherwise.
    """
    if sector_size <= 0:
        return False

    flagged_ratio = len(flagged_tickers) / sector_size
    return flagged_ratio >= config.sector_breadth_threshold


def check_variance_compression(
    raw_values: list[float],
    corrected_values: list[float],
    config: HealingConfig,
) -> bool:
    """Return True if a variance-compression WARNING should fire.

    After applying corrections, the standard deviation of the corrected values
    should remain close to that of the raw values.  If the ratio drops below
    ``config.variance_compression_floor``, the corrections are removing too
    much signal — a warning is warranted.

    Args:
        raw_values: Original (uncorrected) values.
        corrected_values: Values after healing corrections.
        config: Healing configuration with ``variance_compression_floor``.

    Returns:
        True if the corrected-to-raw stdev ratio is **below** the floor
        (warning condition); False otherwise (including insufficient data).
    """
    if len(raw_values) < 3 or len(corrected_values) < 3:
        return False

    raw_std = statistics.stdev(raw_values)
    if raw_std == 0:
        return False

    corrected_std = statistics.stdev(corrected_values)
    ratio = corrected_std / raw_std
    return ratio < config.variance_compression_floor
