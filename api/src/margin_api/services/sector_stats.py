"""Sector statistics computation for V4 scoring pipeline.

Includes filter pass rates and sub-factor distributions (P10/P50/P90)
per sector. These are injected into the V4Score detail JSONB so the
frontend can render sector context sparklines.

Also provides async query helpers for the sector list and champion endpoints.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from margin_api.services.scoring import RawScoringResult


def compute_sector_filter_pass_rates(
    filter_data: list[tuple[str, list[dict]]],
) -> dict[str, dict[str, float]]:
    """Compute pass rate for each (sector, filter_name) pair.

    Args:
        filter_data: List of (sector, filters_passed_list) tuples.
            Each filters_passed_list is a list of dicts with 'name' and 'passed' keys.

    Returns:
        Nested dict: sector -> filter_name -> pass_rate (0.0-1.0)
    """
    counts: dict[tuple[str, str], list[bool]] = defaultdict(list)

    for sector, filters in filter_data:
        for f in filters:
            key = (sector, f["name"])
            counts[key].append(bool(f.get("passed", False)))

    result: dict[str, dict[str, float]] = {}
    for (sector, filter_name), passed_list in counts.items():
        if sector not in result:
            result[sector] = {}
        result[sector][filter_name] = sum(passed_list) / len(passed_list)

    return result


def compute_sector_distribution(
    raw_values: list[float],
) -> dict[str, float] | None:
    """Compute P10, P50, P90 and count for a list of raw values.

    Args:
        raw_values: Raw sub-factor values for stocks in a sector.

    Returns:
        Dict with p10, p50, p90, count. None if empty.
    """
    if not raw_values:
        return None

    sorted_vals = sorted(raw_values)
    n = len(sorted_vals)

    if n == 1:
        v = sorted_vals[0]
        return {"p10": v, "p50": v, "p90": v, "count": 1}

    def _percentile(data: list[float], pct: float) -> float:
        k = (len(data) - 1) * (pct / 100.0)
        f = int(k)
        c = f + 1
        if c >= len(data):
            return data[f]
        return data[f] + (k - f) * (data[c] - data[f])

    return {
        "p10": round(_percentile(sorted_vals, 10), 4),
        "p50": round(_percentile(sorted_vals, 50), 4),
        "p90": round(_percentile(sorted_vals, 90), 4),
        "count": n,
    }


def compute_all_sector_distributions(
    raw_results: list[RawScoringResult],
) -> dict[str, dict[str, dict]]:
    """Compute P10/P50/P90 per (sector, sub-factor) from raw scoring results.

    Args:
        raw_results: List of RawScoringResult from the scoring pipeline.

    Returns:
        Dict mapping sector -> factor_name -> {p10, p50, p90, count}
    """
    sector_values: dict[tuple[str, str], list[float]] = defaultdict(list)

    for result in raw_results:
        for list_attr in ("quality_scores", "value_scores", "momentum_scores"):
            for score in getattr(result, list_attr):
                key = (result.sector, score.name)
                sector_values[key].append(score.raw_value)

    distributions: dict[str, dict[str, dict]] = defaultdict(dict)
    for (sector, factor_name), values in sector_values.items():
        dist = compute_sector_distribution(values)
        if dist is not None:
            distributions[sector][factor_name] = dist

    return dict(distributions)


async def list_sector_summaries(session: AsyncSession) -> list[dict]:
    """Query published V4Scores grouped by sector.

    Returns one summary dict per sector with count, avg score, and the
    top-scoring ticker + its score.
    """
    from margin_api.db.models import Asset, V4Score

    # Subquery: find the max composite_score per sector among published scores
    max_score_sq = (
        select(
            Asset.sector.label("sector"),
            func.max(V4Score.composite_score).label("top_score"),
        )
        .join(Asset, V4Score.asset_id == Asset.id)
        .where(V4Score.published == True)  # noqa: E712
        .group_by(Asset.sector)
        .subquery()
    )

    # Per-sector aggregates
    agg_q = (
        select(
            Asset.sector,
            func.count(V4Score.id).label("asset_count"),
            func.avg(V4Score.composite_score).label("avg_composite_score"),
            max_score_sq.c.top_score,
        )
        .join(Asset, V4Score.asset_id == Asset.id)
        .join(max_score_sq, max_score_sq.c.sector == Asset.sector)
        .where(V4Score.published == True)  # noqa: E712
        .group_by(Asset.sector, max_score_sq.c.top_score)
        .order_by(Asset.sector)
    )
    agg_result = await session.execute(agg_q)
    agg_rows = agg_result.all()

    if not agg_rows:
        return []

    # Build a set of (sector, top_score) pairs so we can fetch matching tickers
    sector_top: dict[str, float] = {row.sector: row.top_score for row in agg_rows}

    # Fetch one ticker per sector that matches the top score
    champion_q = (
        select(Asset.sector, Asset.ticker, V4Score.composite_score)
        .join(Asset, V4Score.asset_id == Asset.id)
        .where(V4Score.published == True)  # noqa: E712
        .order_by(Asset.sector, V4Score.composite_score.desc())
    )
    champion_result = await session.execute(champion_q)
    champion_rows = champion_result.all()

    # Pick first (highest-score) ticker per sector
    top_ticker_map: dict[str, str] = {}
    for row in champion_rows:
        if row.sector not in top_ticker_map:
            top_ticker_map[row.sector] = row.ticker

    summaries = []
    for row in agg_rows:
        sector = row.sector
        summaries.append(
            {
                "sector": sector,
                "asset_count": row.asset_count,
                "avg_composite_score": float(row.avg_composite_score or 0.0),
                "top_ticker": top_ticker_map.get(sector, ""),
                "top_score": float(sector_top.get(sector, 0.0)),
            }
        )
    return summaries


async def get_sector_champion_detail(session: AsyncSession, sector: str) -> dict | None:
    """Get highest-scored published ticker in a sector.

    Returns a dict with ticker, sector, composite_score, composite_tier,
    signal, and market_cap. Returns None if the sector has no published scores.
    """
    from margin_api.db.models import Asset, V4Score

    q = (
        select(V4Score, Asset)
        .join(Asset, V4Score.asset_id == Asset.id)
        .where(
            Asset.sector == sector,
            V4Score.published == True,  # noqa: E712
        )
        .order_by(V4Score.composite_score.desc())
        .limit(1)
    )
    result = await session.execute(q)
    row = result.first()
    if row is None:
        return None

    v4, asset = row
    detail = v4.detail or {}
    composite_tier = detail.get("composite_tier") or v4.conviction or ""
    signal = detail.get("signal") or v4.timing_signal or ""
    market_cap = float(asset.market_cap) if asset.market_cap else None

    return {
        "ticker": asset.ticker,
        "sector": asset.sector,
        "composite_score": float(v4.composite_score),
        "composite_tier": composite_tier,
        "signal": signal,
        "market_cap": market_cap,
    }
