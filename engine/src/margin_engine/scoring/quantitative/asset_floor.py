"""Asset-Based Floor valuation — liquidation/breakup value per share.

Floor = max(Net Cash + Tangible Book * sector_liquidation_multiple, 0) / shares

Sector liquidation multiples reflect realistic recovery in distressed sale.
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import GICSSector

_SECTOR_LIQUIDATION_MULTIPLES: dict[GICSSector, float] = {
    GICSSector.TECHNOLOGY: 0.3,
    GICSSector.HEALTHCARE: 0.4,
    GICSSector.CONSUMER_STAPLES: 0.7,
    GICSSector.CONSUMER_DISCRETIONARY: 0.5,
    GICSSector.INDUSTRIALS: 0.6,
    GICSSector.ENERGY: 0.5,
    GICSSector.MATERIALS: 0.6,
    GICSSector.UTILITIES: 0.8,
    GICSSector.COMMUNICATION_SERVICES: 0.3,
    GICSSector.FINANCIALS: 0.5,
    GICSSector.REAL_ESTATE: 0.7,
}

_DEFAULT_MULTIPLE = 0.5


def asset_floor_valuation(
    net_cash: Decimal,
    tangible_book: Decimal,
    sector: GICSSector,
    shares_outstanding: int,
) -> float:
    """Compute asset-based floor valuation per share.

    Args:
        net_cash: Cash - Total Debt (can be negative for net debt).
        tangible_book: Total Equity - Intangible Assets - Goodwill.
        sector: GICS sector for liquidation multiple lookup.
        shares_outstanding: Total shares outstanding.

    Returns:
        Floor value per share (>= 0.0).
    """
    if shares_outstanding <= 0:
        return 0.0

    multiple = _SECTOR_LIQUIDATION_MULTIPLES.get(sector, _DEFAULT_MULTIPLE)
    total_floor = float(net_cash) + float(tangible_book) * multiple
    per_share = max(total_floor, 0.0) / shares_outstanding

    return per_share
