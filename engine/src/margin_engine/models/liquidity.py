"""Liquidity profile model with multi-window dollar volume computation."""

from __future__ import annotations

from decimal import Decimal
from statistics import median

from pydantic import BaseModel

from margin_engine.models.financial import PriceBar


class LiquidityProfile(BaseModel):
    """Multi-window liquidity snapshot for an asset.

    Stores median daily dollar volumes across 20/60/90-day windows,
    plus venue and country metadata for downstream filtering.
    """

    median_dollar_volume_20d: Decimal | None = None
    median_dollar_volume_60d: Decimal | None = None
    median_dollar_volume_90d: Decimal | None = None
    listing_venue: str | None = None
    country_code: str | None = None
    avg_spread_bps: float | None = None


def compute_liquidity_profile(
    bars: list[PriceBar],
    listing_venue: str | None = None,
    country_code: str | None = None,
) -> LiquidityProfile:
    """Compute multi-window median dollar volumes from daily price bars.

    Uses median (not mean) to resist outlier days with abnormal volume.
    Bars are sorted by date descending so windows reflect the most recent data.

    Args:
        bars: Daily OHLCV price bars.
        listing_venue: Exchange identifier (e.g. "NYSE", "NASDAQ").
        country_code: ISO country code (e.g. "US").

    Returns:
        LiquidityProfile with computed windows. Windows requiring more bars
        than available are set to None.
    """
    # Sort bars by date descending (most recent first)
    sorted_bars = sorted(bars, key=lambda b: b.date, reverse=True)

    def _median_dollar_vol(n: int) -> Decimal | None:
        if len(sorted_bars) < n:
            return None
        window = sorted_bars[:n]
        dollar_vols = [b.close * Decimal(str(b.volume)) for b in window]
        return Decimal(str(median(dollar_vols)))

    return LiquidityProfile(
        median_dollar_volume_20d=_median_dollar_vol(20),
        median_dollar_volume_60d=_median_dollar_vol(60),
        median_dollar_volume_90d=_median_dollar_vol(90),
        listing_venue=listing_venue,
        country_code=country_code,
    )
