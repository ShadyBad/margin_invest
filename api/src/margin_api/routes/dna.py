"""DNA visual parameters endpoint.

Computes personalized visual DNA from the user's scored ticker portfolio,
mapping sector composition to colors, density, and animation tempo.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, Score
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.schemas.dna import DNAResponse

router = APIRouter(prefix="/api/v1/users/me", tags=["dna"])

SECTOR_COLORS: dict[str, str] = {
    "Information Technology": "#4a8caf",
    "Health Care": "#3a8e72",
    "Financials": "#3a6a9e",
    "Energy": "#b08428",
    "Consumer Discretionary": "#b06848",
    "Industrials": "#7a808a",
    "Materials": "#9a7050",
    "Utilities": "#4a8e4a",
    "Real Estate": "#8a7e5a",
    "Communication Services": "#8a5aa0",
    "Consumer Staples": "#8e8440",
}

DEFAULT_DNA = DNAResponse(
    base="#0f0d0b", mid="#1a5a3e", accent="#1a7a5a", density=0.5, tempo=1.0
)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a 6-digit hex color string to (r, g, b) ints."""
    n = int(hex_color.lstrip("#"), 16)
    return (n >> 16) & 255, (n >> 8) & 255, n & 255


def _rgb_to_hex(r: float, g: float, b: float) -> str:
    """Convert float RGB values (0-255) to a 6-digit hex string."""
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _blend_colors(colors: list[tuple[str, float]]) -> str:
    """Weighted blend of hex colors. Weights must sum to 1.0."""
    r, g, b = 0.0, 0.0, 0.0
    for hex_color, weight in colors:
        cr, cg, cb = _hex_to_rgb(hex_color)
        r += cr * weight
        g += cg * weight
        b += cb * weight
    return _rgb_to_hex(r, g, b)


def compute_dna(
    sector_weights: dict[str, float], ticker_count: int, avg_beta: float
) -> DNAResponse:
    """Compute visual DNA from sector weights, ticker count, and average beta.

    Parameters
    ----------
    sector_weights:
        Mapping of GICS sector name to weight (proportion of portfolio).
    ticker_count:
        Number of scored tickers in the portfolio.
    avg_beta:
        Average beta across the portfolio (defaults to 1.0 when unknown).

    Returns
    -------
    DNAResponse with blended colors, density, and tempo.
    """
    entries = [
        (sector, w)
        for sector, w in sector_weights.items()
        if sector in SECTOR_COLORS
    ]
    if not entries:
        return DEFAULT_DNA

    total = sum(w for _, w in entries)
    if total == 0:
        return DEFAULT_DNA

    weighted = [(SECTOR_COLORS[s], w / total) for s, w in entries]
    base = _blend_colors(weighted)

    # Derive mid and accent from base by blending toward fixed teal tones
    br, bg, bb = _hex_to_rgb(base)
    mid = _rgb_to_hex(
        br * 0.5 + 0x1A * 0.5,
        bg * 0.5 + 0x5A * 0.5,
        bb * 0.5 + 0x3E * 0.5,
    )
    accent = _rgb_to_hex(
        br * 0.3 + 0x1A * 0.7,
        bg * 0.3 + 0x7A * 0.7,
        bb * 0.3 + 0x5A * 0.7,
    )

    density = min(1.0, max(0.0, ticker_count / 30))
    tempo = min(1.5, max(0.5, 0.4 + avg_beta * 0.6))

    return DNAResponse(base=base, mid=mid, accent=accent, density=density, tempo=tempo)


@router.get("/dna", response_model=DNAResponse)
async def get_user_dna(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DNAResponse:
    """Compute visual DNA from user's scored ticker portfolio."""
    stmt = (
        select(Asset.sector, func.count(Asset.id))
        .join(Score, Score.asset_id == Asset.id)
        .group_by(Asset.sector)
    )
    result = await db.execute(stmt)
    sector_counts = dict(result.all())

    if not sector_counts:
        return DEFAULT_DNA

    total = sum(sector_counts.values())
    sector_weights = {s: c / total for s, c in sector_counts.items()}
    ticker_count = total

    return compute_dna(sector_weights, ticker_count, avg_beta=1.0)
