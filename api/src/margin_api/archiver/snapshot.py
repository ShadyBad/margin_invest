"""Snapshot generator — reads published V4Scores and produces a SnapshotPayload."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.archiver.hasher import compute_input_data_hash
from margin_api.archiver.models import (
    ExclusionSummary,
    HashChain,
    MLDetail,
    ModifierDetail,
    PickEntry,
    PillarDetail,
    SnapshotPayload,
    TrackScoreDetail,
)
from margin_api.db.models import Asset, V4Score

logger = logging.getLogger(__name__)

INCLUDED_CONVICTIONS = {"exceptional", "high", "medium"}
PILLAR_KEYS = ("quality", "value", "momentum", "growth", "catalyst", "capital_allocation")


def _extract_pillars(detail: dict) -> dict[str, PillarDetail]:
    """Extract pillar factor scores from the detail JSON, skipping stubs."""
    pillars: dict[str, PillarDetail] = {}
    for key in PILLAR_KEYS:
        pillar_data = detail.get(key)
        if pillar_data is None:
            continue
        sub_scores = pillar_data.get("sub_scores", [])
        factors: dict[str, float] = {}
        for ss in sub_scores:
            if ss.get("stub", False):
                continue
            factors[ss["name"]] = ss["percentile_rank"]
        if factors:
            pillars[key] = PillarDetail(factors=factors)
    return pillars


def _extract_track_scores(score: V4Score) -> dict[str, TrackScoreDetail]:
    """Extract track A/B/C scores from the V4Score model columns."""
    tracks: dict[str, TrackScoreDetail] = {}
    for label, data in [("track_a", score.track_a), ("track_b", score.track_b), ("track_c", score.track_c)]:
        if data is None:
            continue
        tracks[label] = TrackScoreDetail(
            score=data["score"],
            qualifies=data["qualifies"],
            gates_passed=data["gates_passed"],
            total_gates=data["total_gates"],
        )
    return tracks


def _extract_modifiers(detail: dict) -> ModifierDetail:
    """Extract modifier breakdown from detail JSON."""
    breakdown = detail.get("modifier_breakdown", {})
    return ModifierDetail(
        liquidity=breakdown.get("liquidity", 0.0),
        insider_signal=breakdown.get("insider_signal", 0.0),
        inflection=breakdown.get("inflection", 0.0),
        tam=breakdown.get("tam", 0.0),
        anti_consensus=breakdown.get("anti_consensus", 0.0),
    )


async def generate(
    *,
    session: AsyncSession,
    snapshot_date: date,
    model_hash: str,
) -> SnapshotPayload | None:
    """Generate a snapshot payload from published V4Scores for the given date.

    Returns None if no published scores exist for the date.
    """
    day_start = datetime(snapshot_date.year, snapshot_date.month, snapshot_date.day, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

    stmt = (
        select(V4Score, Asset)
        .join(Asset)
        .where(V4Score.published == True)  # noqa: E712
        .where(V4Score.scored_at >= day_start)
        .where(V4Score.scored_at < day_end)
    )
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        return None

    universe_size = len(rows)

    # Build input_data_hash from all rows (not just included)
    hash_rows = [
        {"ticker": asset.ticker, "composite_score": score.composite_score}
        for score, asset in rows
    ]
    input_data_hash = compute_input_data_hash(hash_rows)

    # Separate included from excluded
    included: list[tuple[V4Score, Asset]] = []
    conviction_none_count = 0

    for score, asset in rows:
        if score.detail is None:
            logger.warning("Skipping %s: null detail", asset.ticker)
            continue
        if score.conviction in INCLUDED_CONVICTIONS:
            included.append((score, asset))
        else:
            conviction_none_count += 1

    # Sort by descending composite_score, then alphabetical ticker for tie-breaking
    included.sort(key=lambda pair: (-pair[0].composite_score, pair[1].ticker))

    # Build picks
    picks: list[PickEntry] = []
    for rank, (score, asset) in enumerate(included, start=1):
        detail = score.detail
        price = detail.get("actual_price", 0.0) if detail else 0.0

        picks.append(
            PickEntry(
                rank=rank,
                ticker=asset.ticker,
                composite_score=score.composite_score,
                conviction=score.conviction,
                opportunity_type=score.opportunity_type,
                style=score.style,
                track_scores=_extract_track_scores(score),
                pillars=_extract_pillars(detail),
                modifiers=_extract_modifiers(detail),
                ml=MLDetail(
                    alpha=score.ml_alpha,
                    confidence=score.ml_confidence,
                    override=score.ml_override or "none",
                ),
                sector=asset.sector,
                market_cap_usd=int(asset.market_cap),
                price_at_close=price,
            )
        )

    excluded_count = conviction_none_count

    return SnapshotPayload(
        snapshot_version="1.0.0",
        snapshot_date=snapshot_date.isoformat(),
        generated_at_utc=datetime.now(UTC),
        market_close_time=datetime.now(UTC),
        universe_size=universe_size,
        methodology_version="4.0.0",
        model_hash=model_hash,
        input_data_hash=input_data_hash,
        top_picks=picks,
        excluded_count=excluded_count,
        exclusion_summary=ExclusionSummary(conviction_none=conviction_none_count),
        hash_chain=HashChain(),
        payload_hash="",
    )
