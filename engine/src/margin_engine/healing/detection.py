"""Anomaly detection for the self-healing data layer.

Three tiers of detection, ordered by certainty:
- Tier 1: Deterministic impossibility checks (zero false positives)
- Tier 2: Univariate MAD-based outlier detection (low false positive rate)
- Tier 3: Cross-sectional + historical consistency checks (moderate FP rate)
"""

from __future__ import annotations

import statistics
from decimal import Decimal

from margin_engine.healing.models import (
    FIELD_CLASS_MAP,
    DetectionResult,
    DetectionSeverity,
    FieldClass,
    HealingConfig,
    SectorDistribution,
)
from margin_engine.models.financial import FinancialPeriod

# ---------------------------------------------------------------------------
# Tier 1 constants
# ---------------------------------------------------------------------------

_IDENTITY_TOLERANCE = Decimal("0.01")

# ---------------------------------------------------------------------------
# Tier 3 constants
# ---------------------------------------------------------------------------

_MIN_HISTORY_POINTS = 4
"""Minimum trailing history points required for self-history analysis."""

_SECTOR_MOVEMENT_THRESHOLD = 0.10
"""Minimum relative sector median shift to classify as regime change."""

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _compute_mad(values: list[float]) -> float:
    """Compute Median Absolute Deviation (MAD) of a list of values."""
    if len(values) < 2:
        return 0.0
    med = statistics.median(values)
    return statistics.median(abs(v - med) for v in values)


def _is_monotonic(values: list[float]) -> bool:
    """Return True if all diffs are positive or all diffs are negative.

    Requires at least 3 values. Constant sequences return False.
    """
    if len(values) < 3:
        return False
    diffs = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    return all(d > 0 for d in diffs) or all(d < 0 for d in diffs)


def _get_threshold(field_path: str, config: HealingConfig) -> float:
    """Look up the MAD threshold for a field via FIELD_CLASS_MAP.

    Unknown fields default to the growth_rates threshold (most conservative).
    """
    field_class = FIELD_CLASS_MAP.get(field_path)
    if field_class is None:
        return config.tier2_mad_thresholds[FieldClass.GROWTH_RATES.value.lower()]
    return config.tier2_mad_thresholds[field_class.value.lower()]


# ---------------------------------------------------------------------------
# Tier 1: Deterministic impossibility checks
# ---------------------------------------------------------------------------


def detect_tier1(period: FinancialPeriod) -> list[DetectionResult]:
    """Run all Tier 1 (deterministic impossibility) checks on a financial period.

    Checks:
    1. Negative revenue (revenue < 0)
    2. Zero or negative shares outstanding (shares_outstanding <= 0)
    3. Accounting identity violation (L + E > A * (1 + tolerance))
    4. Stale duplicate (current == prior for all statements)
    """
    results: list[DetectionResult] = []

    # 1. Negative revenue
    if period.current_income.revenue < 0:
        results.append(
            DetectionResult(
                field_path="income_statement.revenue",
                severity=DetectionSeverity.IMPOSSIBLE,
                detail=f"Negative revenue: {period.current_income.revenue}",
                original_value=float(period.current_income.revenue),
            )
        )

    # 2. Zero or negative shares outstanding
    if period.current_income.shares_outstanding <= 0:
        results.append(
            DetectionResult(
                field_path="income_statement.shares_outstanding",
                severity=DetectionSeverity.IMPOSSIBLE,
                detail=(
                    f"Zero or negative shares outstanding: "
                    f"{period.current_income.shares_outstanding}"
                ),
                original_value=float(period.current_income.shares_outstanding),
            )
        )

    # 3. Accounting identity violation: L + E > A * (1 + tolerance)
    balance = period.current_balance
    lhs = balance.total_liabilities + balance.total_equity
    rhs = balance.total_assets * (Decimal("1") + _IDENTITY_TOLERANCE)
    if lhs > rhs:
        results.append(
            DetectionResult(
                field_path="balance_sheet.identity",
                severity=DetectionSeverity.IMPOSSIBLE,
                detail=(
                    f"Accounting identity violation: "
                    f"liabilities ({balance.total_liabilities}) + "
                    f"equity ({balance.total_equity}) = {lhs} > "
                    f"assets ({balance.total_assets}) * {Decimal('1') + _IDENTITY_TOLERANCE}"
                ),
                original_value=float(lhs),
            )
        )

    # 4. Stale duplicate: current == prior for all three statements
    if (
        period.prior_income is not None
        and period.prior_balance is not None
        and period.prior_cash_flow is not None
    ):
        current_income_dict = period.current_income.model_dump()
        prior_income_dict = period.prior_income.model_dump()
        current_balance_dict = period.current_balance.model_dump()
        prior_balance_dict = period.prior_balance.model_dump()
        current_cf_dict = period.current_cash_flow.model_dump()
        prior_cf_dict = period.prior_cash_flow.model_dump()

        if (
            current_income_dict == prior_income_dict
            and current_balance_dict == prior_balance_dict
            and current_cf_dict == prior_cf_dict
        ):
            results.append(
                DetectionResult(
                    field_path="period",
                    severity=DetectionSeverity.IMPOSSIBLE,
                    detail="Stale duplicate: current period data is identical to prior period",
                    original_value=None,
                )
            )

    return results


# ---------------------------------------------------------------------------
# Tier 2: MAD-based outlier detection
# ---------------------------------------------------------------------------


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
    """
    dist_by_field: dict[str, SectorDistribution] = {
        d.field_path: d for d in sector_distributions
    }

    results: list[DetectionResult] = []

    for field_path, value in field_values.items():
        dist = dist_by_field.get(field_path)
        if dist is None or dist.mad == 0.0:
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


# ---------------------------------------------------------------------------
# Tier 3: Cross-sectional + historical consistency checks
# ---------------------------------------------------------------------------


def detect_tier3(
    field_values: dict[str, float],
    ticker_history: dict[str, list[float]],
    sector_distributions: list[SectorDistribution],
    prior_sector_distributions: list[SectorDistribution],
    config: HealingConfig,
) -> list[DetectionResult]:
    """Detect Tier 3 anomalies via cross-sectional consistency checks.

    For each field, compares the current value against the ticker's own
    trailing history. If the value is a significant outlier relative to
    the ticker's own pattern, checks whether the sector also shifted
    (regime change) before flagging.
    """
    current_by_field: dict[str, SectorDistribution] = {
        sd.field_path: sd for sd in sector_distributions
    }
    prior_by_field: dict[str, SectorDistribution] = {
        sd.field_path: sd for sd in prior_sector_distributions
    }

    results: list[DetectionResult] = []

    for field_path, value in field_values.items():
        history = ticker_history.get(field_path)
        if not history or len(history) < _MIN_HISTORY_POINTS:
            continue

        current_dist = current_by_field.get(field_path)
        prior_dist = prior_by_field.get(field_path)
        if current_dist is None or prior_dist is None:
            continue

        ticker_median = statistics.median(history)
        ticker_mad = _compute_mad(history)
        if ticker_mad == 0:
            continue

        self_deviation = abs(value - ticker_median) / ticker_mad
        if self_deviation <= config.tier3_self_history_multiplier:
            continue

        if config.tier3_sector_corroboration_required:
            if prior_dist.median == 0:
                continue
            sector_shift = abs(current_dist.median - prior_dist.median) / abs(prior_dist.median)
            if sector_shift > _SECTOR_MOVEMENT_THRESHOLD:
                continue

        results.append(
            DetectionResult(
                field_path=field_path,
                severity=DetectionSeverity.SUSPICIOUS,
                detail=(
                    f"Self-history anomaly: value {value:.4f} deviates "
                    f"{self_deviation:.1f} MADs from ticker median {ticker_median:.4f}"
                ),
                original_value=value,
                mad_deviation=self_deviation,
            )
        )

    return results
