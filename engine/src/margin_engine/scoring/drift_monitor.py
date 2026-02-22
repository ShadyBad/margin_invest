"""Style Drift Monitor — detects sector/style concentration.

Checks portfolio weights against configurable thresholds and
produces alerts when concentration exceeds limits.
"""

from __future__ import annotations

from pydantic import BaseModel

_DEFAULT_MAX_SECTOR_PCT = 0.40
_DEFAULT_MAX_STYLE_PCT = 0.50


class DriftAlert(BaseModel):
    """A single concentration alert."""

    alert_type: str  # "sector_concentration" | "style_concentration"
    dimension: str  # e.g., "Technology" or "growth"
    weight: float
    threshold: float
    message: str


def check_concentration(
    sector_weights: dict[str, float],
    style_weights: dict[str, float],
    max_sector_pct: float = _DEFAULT_MAX_SECTOR_PCT,
    max_style_pct: float = _DEFAULT_MAX_STYLE_PCT,
) -> list[DriftAlert]:
    """Check for sector and style concentration breaches."""
    alerts: list[DriftAlert] = []

    for sector, weight in sector_weights.items():
        if weight > max_sector_pct:
            alerts.append(
                DriftAlert(
                    alert_type="sector_concentration",
                    dimension=sector,
                    weight=weight,
                    threshold=max_sector_pct,
                    message=f"{sector} at {weight:.1%} exceeds {max_sector_pct:.0%} limit",
                )
            )

    for style, weight in style_weights.items():
        if weight > max_style_pct:
            alerts.append(
                DriftAlert(
                    alert_type="style_concentration",
                    dimension=style,
                    weight=weight,
                    threshold=max_style_pct,
                    message=f"{style} at {weight:.1%} exceeds {max_style_pct:.0%} limit",
                )
            )

    return alerts
