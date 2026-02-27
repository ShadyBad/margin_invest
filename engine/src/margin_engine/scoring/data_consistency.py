"""Cross-period data consistency validation.

Compares the most recent period's critical financial fields against trailing
history to detect silent provider errors (e.g., wrong shares_outstanding
after stock splits, revenue off by orders of magnitude).

Uses z-scores with a 3-sigma threshold. Fields with zero standard deviation
use a fallback: flag if current deviates >100% from mean.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import ConsistencyFlag

_MIN_PERIODS = 3
_Z_THRESHOLD = 3.0
_FALLBACK_DEVIATION_PCT = 1.0  # 100% deviation when std is zero


def _extract_field(period: FinancialPeriod, field_name: str) -> float | None:
    """Extract a critical field value from a FinancialPeriod."""
    extractors: dict[str, Callable[[FinancialPeriod], float]] = {
        "revenue": lambda p: float(p.current_income.revenue),
        "total_assets": lambda p: float(p.current_balance.total_assets),
        "shares_outstanding": lambda p: float(p.current_income.shares_outstanding),
        "operating_income": lambda p: float(p.current_income.ebit),
        "free_cash_flow": lambda p: float(p.current_cash_flow.free_cash_flow),
    }
    extractor = extractors.get(field_name)
    if extractor is None:
        return None
    try:
        return extractor(period)
    except (AttributeError, TypeError, ZeroDivisionError):
        return None


CRITICAL_FIELDS = [
    "revenue",
    "total_assets",
    "shares_outstanding",
    "operating_income",
    "free_cash_flow",
]


def validate_data_consistency(
    history: FinancialHistory,
) -> list[ConsistencyFlag]:
    """Validate the most recent period against trailing history.

    Args:
        history: Multi-period financial data (sorted oldest-first by validator).

    Returns:
        List of ConsistencyFlag for each critical field. Each flag includes
        the z-score; callers use flag.is_anomaly to check if it exceeds 3-sigma.
        Returns empty list if fewer than 3 periods available.
    """
    if len(history.periods) < _MIN_PERIODS:
        return []

    current = history.periods[-1]
    prior_periods = history.periods[:-1]
    flags: list[ConsistencyFlag] = []

    for field_name in CRITICAL_FIELDS:
        current_value = _extract_field(current, field_name)
        if current_value is None:
            continue

        prior_values = []
        for p in prior_periods:
            v = _extract_field(p, field_name)
            if v is not None:
                prior_values.append(v)

        if len(prior_values) < 2:
            continue

        mean = sum(prior_values) / len(prior_values)
        variance = sum((v - mean) ** 2 for v in prior_values) / len(prior_values)
        std = math.sqrt(variance)

        if std == 0.0:
            # All prior values identical — use percentage deviation fallback
            if mean == 0.0:
                z_score = 0.0
            else:
                deviation_pct = abs(current_value - mean) / abs(mean)
                # Map >100% deviation to z=4 (above threshold), proportionally
                z_score = (deviation_pct / _FALLBACK_DEVIATION_PCT) * (_Z_THRESHOLD + 1.0)
        else:
            z_score = (current_value - mean) / std

        flags.append(
            ConsistencyFlag(
                field_name=field_name,
                current_value=current_value,
                historical_mean=round(mean, 2),
                historical_std=round(std, 2),
                z_score=round(z_score, 2),
                periods_used=len(prior_values),
            )
        )

    return flags
