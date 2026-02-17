"""Sector average WACC lookup — Damodaran-style sector estimates.

Provides a deterministic WACC per GICS sector, avoiding external data
dependencies (no beta calculation, no live risk-free rate fetch).
Updated annually from Damodaran's sector WACC tables.
"""

from __future__ import annotations

from margin_engine.models.financial import GICSSector

_SECTOR_WACC: dict[GICSSector, float] = {
    GICSSector.TECHNOLOGY: 0.100,
    GICSSector.HEALTHCARE: 0.095,
    GICSSector.FINANCIALS: 0.085,
    GICSSector.CONSUMER_DISCRETIONARY: 0.090,
    GICSSector.CONSUMER_STAPLES: 0.075,
    GICSSector.ENERGY: 0.105,
    GICSSector.INDUSTRIALS: 0.085,
    GICSSector.MATERIALS: 0.090,
    GICSSector.REAL_ESTATE: 0.070,
    GICSSector.UTILITIES: 0.065,
    GICSSector.COMMUNICATION_SERVICES: 0.090,
}

_DEFAULT_WACC = 0.090


def get_sector_wacc(sector: GICSSector) -> float:
    """Return the sector average WACC for the given GICS sector."""
    return _SECTOR_WACC.get(sector, _DEFAULT_WACC)
