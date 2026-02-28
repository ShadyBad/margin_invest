"""Pydantic models for the self-healing data layer.

Defines detection severities, correction methods, field classifications,
and configuration for anomaly detection and correction.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class DetectionSeverity(StrEnum):
    """Severity levels for detected data anomalies."""

    IMPOSSIBLE = "IMPOSSIBLE"
    OUTLIER = "OUTLIER"
    SUSPICIOUS = "SUSPICIOUS"


class CorrectionMethod(StrEnum):
    """Methods for correcting detected anomalies, ordered by preference."""

    L1_SUBSTITUTE = "L1_SUBSTITUTE"
    L2_CARRY_FORWARD = "L2_CARRY_FORWARD"
    L3_SECTOR_MEDIAN = "L3_SECTOR_MEDIAN"


class FieldClass(StrEnum):
    """Classification of financial fields for threshold selection."""

    MARGINS = "MARGINS"
    GROWTH_RATES = "GROWTH_RATES"
    LEVERAGE_RATIOS = "LEVERAGE_RATIOS"
    PRICE_RETURNS = "PRICE_RETURNS"


FIELD_CLASS_MAP: dict[str, FieldClass] = {
    "income_statement.gross_margin": FieldClass.MARGINS,
    "income_statement.net_margin": FieldClass.MARGINS,
    "cash_flow.fcf_margin": FieldClass.MARGINS,
    "derived.revenue_growth": FieldClass.GROWTH_RATES,
    "derived.earnings_growth": FieldClass.GROWTH_RATES,
    "balance_sheet.debt_to_equity": FieldClass.LEVERAGE_RATIOS,
    "derived.interest_coverage": FieldClass.LEVERAGE_RATIOS,
    "balance_sheet.current_ratio": FieldClass.LEVERAGE_RATIOS,
}
"""Maps field paths to their FieldClass for threshold lookup."""

EXCLUDED_FIELDS: frozenset[str] = frozenset(
    {
        "revenue",
        "net_income",
        "operating_cash_flow",
        "free_cash_flow",
        "total_assets",
        "total_liabilities",
        "total_equity",
        "total_debt",
        "shares_outstanding",
        "market_cap",
        "price_history",
    }
)
"""Fields that must never be L3-imputed (cross-sectional sector median).

These are absolute-scale values where a sector median would be meaningless
or dangerous (e.g., imputing revenue from sector median).
"""


class DetectionResult(BaseModel):
    """Result of anomaly detection on a single field."""

    field_path: str
    severity: DetectionSeverity
    detail: str
    original_value: float | None
    mad_deviation: float | None = None


class CorrectionEvent(BaseModel):
    """Record of a single correction applied to a field."""

    field_path: str
    detection_severity: DetectionSeverity
    detection_detail: str
    original_value: float | None
    corrected_value: float
    correction_method: CorrectionMethod
    correction_source: str
    correction_confidence: float


class SectorDistribution(BaseModel):
    """Cross-sectional distribution statistics for a field within a sector."""

    sector: str
    field_path: str
    median: float
    mad: float
    n_observations: int
    period: str


class HealingConfig(BaseModel):
    """Configuration for the self-healing data pipeline."""

    version: str = "1.0.0"

    # Tier 2: MAD thresholds per field class for outlier detection
    tier2_mad_thresholds: dict[str, float] = {
        "margins": 6.0,
        "growth_rates": 8.0,
        "leverage_ratios": 7.0,
        "price_returns": 10.0,
    }

    # Tier 3: Self-history anomaly detection
    tier3_self_history_multiplier: float = 3.0
    tier3_sector_corroboration_required: bool = True

    # L2 carry-forward parameters
    carry_forward_max_quarters: int = 4
    carry_forward_decay_rate: float = 0.15

    # L3 cross-sectional parameters
    cross_sectional_min_confidence: float = 0.3

    # Substitution tolerance for L1
    substitution_tolerance: float = 0.20

    # Sector breadth threshold
    sector_breadth_threshold: float = 0.15

    # Regime shift detection
    consecutive_flag_regime_shift: int = 2

    # Variance compression floor
    variance_compression_floor: float = 0.85

    # Trend threshold multiplier
    trend_threshold_multiplier: float = 1.5

    # Fields excluded from L3 imputation
    excluded_fields: frozenset[str] = EXCLUDED_FIELDS
