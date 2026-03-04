"""Tests for stage_scores worker job and _stage_scores_impl."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, PipelineApproval, V4Score
from margin_api.workers import _stage_scores_impl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


async def _create_asset(session: AsyncSession, ticker: str = "AAPL") -> Asset:
    """Create a test asset."""
    asset = Asset(
        ticker=ticker,
        name=f"{ticker} Inc.",
        sector="Technology",
        market_cap=Decimal("1000000000"),
    )
    session.add(asset)
    await session.flush()
    return asset


async def _create_v4_score(
    session: AsyncSession,
    asset: Asset,
    conviction: str = "high",
    scored_at: datetime | None = None,
    published: bool = False,
) -> V4Score:
    """Create a test V4Score."""
    score = V4Score(
        asset_id=asset.id,
        opportunity_type="value",
        conviction=conviction,
        rules_conviction=conviction,
        style="value",
        timing_signal="neutral",
        max_position_pct=5.0,
        regime="normal",
        composite_score=75.0,
        ml_override="none",
        published=published,
    )
    if scored_at is not None:
        score.scored_at = scored_at
    session.add(score)
    await session.flush()
    return score


class TestStageScoresImpl:
    @pytest.mark.asyncio
    async def test_creates_pipeline_approval_with_correct_fields(self, db_session):
        """_stage_scores_impl creates a PipelineApproval with gate_type and status."""
        now = datetime.now(UTC)
        asset = await _create_asset(db_session, "AAPL")
        await _create_v4_score(db_session, asset, conviction="high", scored_at=now)
        await db_session.commit()

        pipeline_id = "pipe-test-001"
        result = await _stage_scores_impl(db_session, pipeline_id, now)

        assert result["status"] == "staged"
        assert result["ticker_count"] == 1
        assert "approval_id" in result

        # Verify PipelineApproval was created
        approvals = (await db_session.execute(select(PipelineApproval))).scalars().all()
        assert len(approvals) == 1

        approval = approvals[0]
        assert approval.gate_type == "score_publish"
        assert approval.status == "staged"
        assert approval.pipeline_id == pipeline_id
        assert approval.payload_ref["scored_at"] is not None
        assert approval.payload_ref["ticker_count"] == 1
        assert approval.impact_summary["ticker_count"] == 1
        assert approval.expires_at is not None
        # expires_at should be roughly 24 hours from now
        # SQLite returns naive datetimes, so strip tzinfo for comparison
        expires = (
            approval.expires_at.replace(tzinfo=None)
            if approval.expires_at.tzinfo
            else approval.expires_at
        )
        now_naive = now.replace(tzinfo=None)
        delta = expires - now_naive
        assert timedelta(hours=23) < delta < timedelta(hours=25)

    @pytest.mark.asyncio
    async def test_counts_conviction_changes_in_impact_summary(self, db_session):
        """_stage_scores_impl counts conviction changes when previous published scores exist."""
        now = datetime.now(UTC)
        old_time = now - timedelta(days=1)

        asset1 = await _create_asset(db_session, "AAPL")
        # Previous published score with different conviction
        await _create_v4_score(
            db_session, asset1, conviction="moderate", scored_at=old_time, published=True
        )
        # New unpublished score with changed conviction
        await _create_v4_score(db_session, asset1, conviction="high", scored_at=now)

        asset2 = await _create_asset(db_session, "MSFT")
        # Previous published score with same conviction
        await _create_v4_score(
            db_session, asset2, conviction="high", scored_at=old_time, published=True
        )
        # New unpublished score with same conviction
        await _create_v4_score(db_session, asset2, conviction="high", scored_at=now)

        await db_session.commit()

        result = await _stage_scores_impl(db_session, "pipe-test-002", now)

        assert result["status"] == "staged"
        assert result["ticker_count"] == 2

        approvals = (await db_session.execute(select(PipelineApproval))).scalars().all()
        assert len(approvals) == 1
        # Only AAPL had a conviction change
        assert approvals[0].impact_summary["conviction_changes"] == 1

    @pytest.mark.asyncio
    async def test_no_previous_published_score_conviction_changes_zero(self, db_session):
        """When no previous published score exists, conviction_changes should be 0."""
        now = datetime.now(UTC)

        asset = await _create_asset(db_session, "NVDA")
        await _create_v4_score(db_session, asset, conviction="high", scored_at=now)
        await db_session.commit()

        result = await _stage_scores_impl(db_session, "pipe-test-003", now)

        assert result["status"] == "staged"
        assert result["ticker_count"] == 1

        approvals = (await db_session.execute(select(PipelineApproval))).scalars().all()
        assert len(approvals) == 1
        assert approvals[0].impact_summary["conviction_changes"] == 0

    @pytest.mark.asyncio
    async def test_ignores_already_published_scores(self, db_session):
        """_stage_scores_impl only considers unpublished scores for the given scored_at."""
        now = datetime.now(UTC)

        asset = await _create_asset(db_session, "GOOG")
        # Already published score at this time
        await _create_v4_score(db_session, asset, conviction="high", scored_at=now, published=True)
        await db_session.commit()

        result = await _stage_scores_impl(db_session, "pipe-test-004", now)

        assert result["status"] == "staged"
        assert result["ticker_count"] == 0

    @pytest.mark.asyncio
    async def test_multiple_conviction_changes(self, db_session):
        """All conviction changes are counted correctly across multiple assets."""
        now = datetime.now(UTC)
        old_time = now - timedelta(days=1)

        # 3 assets, all with conviction changes
        for ticker, old_conv, new_conv in [
            ("AAPL", "low", "high"),
            ("MSFT", "moderate", "low"),
            ("GOOG", "high", "moderate"),
        ]:
            asset = await _create_asset(db_session, ticker)
            await _create_v4_score(
                db_session, asset, conviction=old_conv, scored_at=old_time, published=True
            )
            await _create_v4_score(db_session, asset, conviction=new_conv, scored_at=now)

        await db_session.commit()

        result = await _stage_scores_impl(db_session, "pipe-test-005", now)

        assert result["ticker_count"] == 3
        approvals = (await db_session.execute(select(PipelineApproval))).scalars().all()
        assert approvals[0].impact_summary["conviction_changes"] == 3

    @pytest.mark.asyncio
    async def test_mismatched_timestamp_finds_zero(self, db_session):
        """Scores with a different scored_at than the query timestamp are not found.

        Regression test: previously, V4Score rows were inserted with individual
        timestamps (model default) while stage_scores queried with a separate
        timestamp captured after scoring completed, causing zero matches.
        """
        score_time = datetime.now(UTC)
        query_time = score_time + timedelta(seconds=5)  # different timestamp

        asset = await _create_asset(db_session, "AAPL")
        await _create_v4_score(db_session, asset, conviction="high", scored_at=score_time)
        await db_session.commit()

        result = await _stage_scores_impl(db_session, "pipe-mismatch", query_time)
        assert result["ticker_count"] == 0

    @pytest.mark.asyncio
    async def test_shared_timestamp_finds_all(self, db_session):
        """All scores sharing the same scored_at timestamp are found by stage_scores."""
        shared_time = datetime.now(UTC)

        for ticker in ["AAPL", "MSFT", "GOOG"]:
            asset = await _create_asset(db_session, ticker)
            await _create_v4_score(db_session, asset, conviction="high", scored_at=shared_time)
        await db_session.commit()

        result = await _stage_scores_impl(db_session, "pipe-shared", shared_time)
        assert result["ticker_count"] == 3
