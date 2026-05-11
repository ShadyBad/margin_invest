"""Tests for snapshot generator."""

from __future__ import annotations

from datetime import date

import pytest
from margin_api.archiver.snapshot import generate
from sqlalchemy.ext.asyncio import AsyncSession

from .conftest import _make_asset, _make_v4score


@pytest.mark.asyncio
async def test_golden_value_snapshot(seeded_session: AsyncSession) -> None:
    result = await generate(
        session=seeded_session,
        snapshot_date=date(2026, 4, 21),
        model_hash="abc123",
    )
    assert result is not None
    assert result.snapshot_version == "1.0.0"
    assert result.universe_size == 3
    assert len(result.top_picks) == 2
    assert result.excluded_count == 1


@pytest.mark.asyncio
async def test_picks_ranked_by_composite_score(seeded_session: AsyncSession) -> None:
    result = await generate(
        session=seeded_session,
        snapshot_date=date(2026, 4, 21),
        model_hash="abc123",
    )
    assert result is not None
    assert result.top_picks[0].rank == 1
    assert result.top_picks[0].ticker == "AAPL"
    assert result.top_picks[0].composite_score == 87.3
    assert result.top_picks[1].rank == 2
    assert result.top_picks[1].ticker == "MSFT"
    assert result.top_picks[1].composite_score == 82.1


@pytest.mark.asyncio
async def test_conviction_gating(seeded_session: AsyncSession) -> None:
    result = await generate(
        session=seeded_session,
        snapshot_date=date(2026, 4, 21),
        model_hash="abc123",
    )
    assert result is not None
    convictions = {p.conviction for p in result.top_picks}
    assert "none" not in convictions


@pytest.mark.asyncio
async def test_pillar_factor_extraction(seeded_session: AsyncSession) -> None:
    result = await generate(
        session=seeded_session,
        snapshot_date=date(2026, 4, 21),
        model_hash="abc123",
    )
    assert result is not None
    aapl = result.top_picks[0]
    assert aapl.ticker == "AAPL"

    quality = aapl.pillars["quality"]
    assert quality.factors["gross_profitability"] == 92.1
    assert quality.factors["roic_wacc"] == 88.4

    value = aapl.pillars["value"]
    assert value.factors["ev_fcf"] == 71.0


@pytest.mark.asyncio
async def test_track_scores_present(seeded_session: AsyncSession) -> None:
    result = await generate(
        session=seeded_session,
        snapshot_date=date(2026, 4, 21),
        model_hash="abc123",
    )
    assert result is not None
    aapl = result.top_picks[0]
    assert aapl.track_scores["track_a"].score == 87.3
    assert aapl.track_scores["track_a"].qualifies is True


@pytest.mark.asyncio
async def test_ml_details_present(seeded_session: AsyncSession) -> None:
    result = await generate(
        session=seeded_session,
        snapshot_date=date(2026, 4, 21),
        model_hash="abc123",
    )
    assert result is not None
    aapl = result.top_picks[0]
    assert aapl.ml.alpha == 0.12
    assert aapl.ml.confidence == 0.85


@pytest.mark.asyncio
async def test_tie_breaking_by_ticker(async_session: AsyncSession) -> None:
    aaa = _make_asset(10, "AAA")
    zzz = _make_asset(11, "ZZZ")
    aaa_score = _make_v4score(10, conviction="high", composite_score=80.0)
    zzz_score = _make_v4score(11, conviction="high", composite_score=80.0)

    async_session.add_all([aaa, zzz, aaa_score, zzz_score])
    await async_session.commit()

    result = await generate(
        session=async_session,
        snapshot_date=date(2026, 4, 21),
        model_hash="abc123",
    )
    assert result is not None
    assert result.top_picks[0].ticker == "AAA"
    assert result.top_picks[1].ticker == "ZZZ"


@pytest.mark.asyncio
async def test_no_published_scores_returns_none(async_session: AsyncSession) -> None:
    result = await generate(
        session=async_session,
        snapshot_date=date(2026, 4, 21),
        model_hash="abc123",
    )
    assert result is None


@pytest.mark.asyncio
async def test_null_detail_skips_ticker(async_session: AsyncSession) -> None:
    asset = _make_asset(20, "NULL")
    score = _make_v4score(20, conviction="high", composite_score=90.0)
    score.detail = None  # null detail

    async_session.add_all([asset, score])
    await async_session.commit()

    result = await generate(
        session=async_session,
        snapshot_date=date(2026, 4, 21),
        model_hash="abc123",
    )
    # One row in universe, but null detail means 0 picks
    assert result is not None
    assert result.universe_size == 1
    assert len(result.top_picks) == 0
