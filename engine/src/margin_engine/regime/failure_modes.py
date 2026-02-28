"""Failure mode detectors for regime-conditional filter analysis.

Implements four independent detectors from the regime study design:
  1. Threshold brittleness — values clustering near a gate threshold
  2. Signal inversion — TPR dropping below coin-flip in a regime
  3. Universe collapse — too few survivors or sector concentration
  4. Pro-cyclical amplification — survivor count correlated with forward returns

Each detector is a pure function consuming pre-computed data.
The study orchestrator (Task 9) assembles the inputs and calls these.
"""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class ThresholdBrittlenessResult(BaseModel):
    """Result of threshold brittleness detection for a single gate + regime."""

    gate_name: str
    regime_key: str
    density_ratio: float = Field(
        description="Proportion near threshold in regime vs uniform expectation"
    )
    n_near_threshold: int
    n_total: int


class SignalInversionResult(BaseModel):
    """Result of signal inversion detection for a single gate + regime."""

    gate_name: str
    regime_key: str
    tpr: float
    unconditional_tpr: float
    inverted: bool = Field(description="True if TPR < 0.50 in this regime")
    fsr: float = Field(description="False Signal Ratio: FPR(regime) / FPR(unconditional)")


class UniverseCollapseResult(BaseModel):
    """Result of universe collapse detection for a single regime."""

    regime_key: str
    total_survivors: int
    universe_collapsed: bool
    sectors_collapsed: list[str] = Field(default_factory=list)
    concentration_top3_pct: float = 0.0


class ProCyclicalityResult(BaseModel):
    """Result of pro-cyclicality detection across time periods."""

    correlation: float = Field(description="Correlation between survivor count and forward returns")
    n_observations: int
    is_pro_cyclical: bool = Field(default=False, description="True if correlation > 0.3")


class FailureModeReport(BaseModel):
    """Aggregated failure mode results across all detectors."""

    brittleness: list[ThresholdBrittlenessResult] = Field(default_factory=list)
    inversions: list[SignalInversionResult] = Field(default_factory=list)
    collapses: list[UniverseCollapseResult] = Field(default_factory=list)
    pro_cyclicality: ProCyclicalityResult | None = None


# ---------------------------------------------------------------------------
# Detector functions
# ---------------------------------------------------------------------------


def detect_threshold_brittleness(
    *,
    gate_name: str,
    regime_key: str,
    values: np.ndarray,
    threshold: float,
    margin_pct: float = 0.10,
) -> ThresholdBrittlenessResult:
    """Detect whether values cluster near a gate threshold.

    Counts values within +/-(threshold * margin_pct) of the threshold,
    then compares the actual proportion to what a uniform distribution
    across the observed range would predict.

    Parameters
    ----------
    gate_name:
        Name of the elimination gate.
    regime_key:
        Pipe-delimited regime identifier.
    values:
        Array of metric values for assets in this regime.
    threshold:
        The gate's pass/fail threshold.
    margin_pct:
        Half-width of the "near threshold" band as a fraction of *threshold*.
        Default 0.10 means +/-10% of the threshold value.

    Returns
    -------
    ThresholdBrittlenessResult
    """
    n_total = len(values)
    if n_total == 0:
        return ThresholdBrittlenessResult(
            gate_name=gate_name,
            regime_key=regime_key,
            density_ratio=0.0,
            n_near_threshold=0,
            n_total=0,
        )

    margin = abs(threshold * margin_pct)
    lower = threshold - margin
    upper = threshold + margin

    near_mask = (values >= lower) & (values <= upper)
    n_near = int(near_mask.sum())
    actual_pct = n_near / n_total

    # Expected proportion under uniform distribution across observed range
    obs_min = float(np.min(values))
    obs_max = float(np.max(values))
    obs_range = obs_max - obs_min

    if obs_range == 0.0:
        # All values identical — if they're near threshold, ratio is high;
        # otherwise, ratio is 0.
        density_ratio = float("inf") if n_near > 0 else 0.0
        return ThresholdBrittlenessResult(
            gate_name=gate_name,
            regime_key=regime_key,
            density_ratio=density_ratio,
            n_near_threshold=n_near,
            n_total=n_total,
        )

    # Width of the band that actually overlaps the observed range
    band_lower = max(lower, obs_min)
    band_upper = min(upper, obs_max)
    effective_band = max(0.0, band_upper - band_lower)
    expected_pct = effective_band / obs_range

    if expected_pct == 0.0:
        # Band doesn't overlap observed range — ratio is 0 if no values near,
        # inf if somehow there are (shouldn't happen, but be safe).
        density_ratio = float("inf") if n_near > 0 else 0.0
    else:
        density_ratio = actual_pct / expected_pct

    return ThresholdBrittlenessResult(
        gate_name=gate_name,
        regime_key=regime_key,
        density_ratio=density_ratio,
        n_near_threshold=n_near,
        n_total=n_total,
    )


def detect_signal_inversion(
    *,
    gate_name: str,
    regime_key: str,
    tpr: float,
    unconditional_tpr: float,
) -> SignalInversionResult:
    """Detect whether a gate's signal inverts in a specific regime.

    A gate is "inverted" when its True Positive Rate drops below 0.50
    (worse than a coin flip). The False Signal Ratio (FSR) measures how
    much worse the false positive rate is compared to unconditional.

    Parameters
    ----------
    gate_name:
        Name of the elimination gate.
    regime_key:
        Pipe-delimited regime identifier.
    tpr:
        True positive rate in this regime.
    unconditional_tpr:
        True positive rate across all regimes (baseline).

    Returns
    -------
    SignalInversionResult
    """
    inverted = tpr < 0.50

    denom = 1.0 - unconditional_tpr
    if denom == 0.0:
        fsr = float("inf")
    else:
        fsr = (1.0 - tpr) / denom

    return SignalInversionResult(
        gate_name=gate_name,
        regime_key=regime_key,
        tpr=tpr,
        unconditional_tpr=unconditional_tpr,
        inverted=inverted,
        fsr=fsr,
    )


def detect_universe_collapse(
    *,
    regime_key: str,
    total_survivors: int,
    sector_survivors: dict[str, int],
    collapse_threshold: int = 500,
    sector_threshold: int = 10,
) -> UniverseCollapseResult:
    """Detect whether the post-filter universe has collapsed.

    A universe is "collapsed" when total survivors drop below a threshold.
    Individual sectors can also collapse independently.

    Parameters
    ----------
    regime_key:
        Pipe-delimited regime identifier.
    total_survivors:
        Number of assets surviving all gates.
    sector_survivors:
        Mapping of sector name to survivor count.
    collapse_threshold:
        Minimum acceptable total survivors (default 500).
    sector_threshold:
        Minimum acceptable survivors per sector (default 10).

    Returns
    -------
    UniverseCollapseResult
    """
    universe_collapsed = total_survivors < collapse_threshold

    sectors_collapsed = [
        sector for sector, count in sorted(sector_survivors.items()) if count < sector_threshold
    ]

    # Concentration: top 3 sectors as % of total
    if total_survivors == 0:
        concentration_top3_pct = 0.0
    else:
        sorted_counts = sorted(sector_survivors.values(), reverse=True)
        top3_sum = sum(sorted_counts[:3])
        concentration_top3_pct = (top3_sum / total_survivors) * 100.0

    return UniverseCollapseResult(
        regime_key=regime_key,
        total_survivors=total_survivors,
        universe_collapsed=universe_collapsed,
        sectors_collapsed=sectors_collapsed,
        concentration_top3_pct=concentration_top3_pct,
    )


def detect_pro_cyclicality(
    *,
    survivor_counts: list[int],
    forward_12m_returns: list[float],
) -> ProCyclicalityResult:
    """Detect pro-cyclical amplification in the filter pipeline.

    If survivor count is positively correlated with forward returns,
    the system amplifies momentum rather than providing stability.

    Parameters
    ----------
    survivor_counts:
        Number of survivors at each observation point.
    forward_12m_returns:
        Forward 12-month market returns at each observation point.

    Returns
    -------
    ProCyclicalityResult
    """
    n = len(survivor_counts)
    if n < 3:
        return ProCyclicalityResult(
            correlation=0.0,
            n_observations=n,
            is_pro_cyclical=False,
        )

    x = np.array(survivor_counts, dtype=np.float64)
    y = np.array(forward_12m_returns, dtype=np.float64)

    # Guard against zero standard deviation
    if np.std(x) == 0.0 or np.std(y) == 0.0:
        return ProCyclicalityResult(
            correlation=0.0,
            n_observations=n,
            is_pro_cyclical=False,
        )

    # Pearson correlation
    corr_matrix = np.corrcoef(x, y)
    correlation = float(corr_matrix[0, 1])

    # Handle NaN from numerical issues
    if math.isnan(correlation):
        correlation = 0.0

    return ProCyclicalityResult(
        correlation=correlation,
        n_observations=n,
        is_pro_cyclical=correlation > 0.3,
    )
