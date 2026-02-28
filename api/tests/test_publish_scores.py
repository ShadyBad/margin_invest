"""Tests for publish_scores worker job and _publish_scores_impl."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, PipelineApproval, V4Score
from margin_api.workers import _publish_scores_impl
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


async def _create_approval(
    session: AsyncSession,
    scored_at: datetime,
    status: str = "staged",
    ticker_count: int = 1,
) -> PipelineApproval:
    """Create a test PipelineApproval."""
    approval = PipelineApproval(
        gate_type="score_publish",
        status=status,
        pipeline_id="pipe-test",
        payload_ref={
            "scored_at": scored_at.isoformat(),
            "ticker_count": ticker_count,
        },
        impact_summary={
            "ticker_count": ticker_count,
            "conviction_changes": 0,
        },
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    session.add(approval)
    await session.flush()
    return approval


class TestPublishScoresImpl:
    @pytest.mark.asyncio
    async def test_flips_published_true_on_matching_v4scores(self, db_session):
        """_publish_scores_impl sets published=True on V4Scores matching scored_at."""
        now = datetime.now(UTC)
        asset1 = await _create_asset(db_session, "AAPL")
        asset2 = await _create_asset(db_session, "MSFT")
        await _create_v4_score(db_session, asset1, scored_at=now, published=False)
        await _create_v4_score(db_session, asset2, scored_at=now, published=False)
        await db_session.commit()

        approval = await _create_approval(db_session, scored_at=now, ticker_count=2)
        await db_session.commit()

        result = await _publish_scores_impl(
            db_session, approval.id, decided_by=1, decision_reason="Looks good"
        )

        assert result["status"] == "published"
        assert result["published_count"] == 2
        assert result["approval_id"] == approval.id

        # Verify scores are now published
        scores = (await db_session.execute(select(V4Score))).scalars().all()
        for score in scores:
            assert score.published is True

    @pytest.mark.asyncio
    async def test_updates_approval_status_to_approved(self, db_session):
        """_publish_scores_impl updates the PipelineApproval to approved status."""
        now = datetime.now(UTC)
        asset = await _create_asset(db_session, "AAPL")
        await _create_v4_score(db_session, asset, scored_at=now, published=False)
        await db_session.commit()

        approval = await _create_approval(db_session, scored_at=now)
        await db_session.commit()

        result = await _publish_scores_impl(
            db_session, approval.id, decided_by=42, decision_reason="Approved by operator"
        )

        assert result["status"] == "published"

        # Re-fetch approval to check updated fields
        refreshed = (
            await db_session.execute(
                select(PipelineApproval).where(PipelineApproval.id == approval.id)
            )
        ).scalar_one()

        assert refreshed.status == "approved"
        assert refreshed.decided_by == 42
        assert refreshed.decision_reason == "Approved by operator"
        assert refreshed.decided_at is not None

    @pytest.mark.asyncio
    async def test_rejects_non_staged_approval(self, db_session):
        """_publish_scores_impl returns error for already-approved or rejected approvals."""
        now = datetime.now(UTC)
        approval = await _create_approval(db_session, scored_at=now, status="approved")
        await db_session.commit()

        result = await _publish_scores_impl(db_session, approval.id)

        assert result["status"] == "error"
        assert "not in staged status" in result["message"]

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_approval(self, db_session):
        """_publish_scores_impl returns error when approval_id does not exist."""
        result = await _publish_scores_impl(db_session, 99999)

        assert result["status"] == "error"
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_does_not_flip_already_published_scores(self, db_session):
        """_publish_scores_impl only flips unpublished scores; already-published are unaffected."""
        now = datetime.now(UTC)
        asset = await _create_asset(db_session, "AAPL")
        # One published, one unpublished at same scored_at
        await _create_v4_score(db_session, asset, scored_at=now, published=True)

        asset2 = await _create_asset(db_session, "MSFT")
        await _create_v4_score(db_session, asset2, scored_at=now, published=False)
        await db_session.commit()

        approval = await _create_approval(db_session, scored_at=now, ticker_count=2)
        await db_session.commit()

        result = await _publish_scores_impl(db_session, approval.id)

        # Only the unpublished one should get flipped
        assert result["published_count"] == 1

    @pytest.mark.asyncio
    async def test_does_not_flip_scores_with_different_scored_at(self, db_session):
        """_publish_scores_impl only flips scores matching the approval's scored_at."""
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)

        asset = await _create_asset(db_session, "AAPL")
        # Score at a different time
        await _create_v4_score(db_session, asset, scored_at=yesterday, published=False)

        asset2 = await _create_asset(db_session, "MSFT")
        await _create_v4_score(db_session, asset2, scored_at=now, published=False)
        await db_session.commit()

        # Approval references "now"
        approval = await _create_approval(db_session, scored_at=now, ticker_count=1)
        await db_session.commit()

        result = await _publish_scores_impl(db_session, approval.id)

        assert result["published_count"] == 1

        # Yesterday's score should still be unpublished
        yesterday_scores = (
            (await db_session.execute(select(V4Score).where(V4Score.scored_at == yesterday)))
            .scalars()
            .all()
        )
        assert all(s.published is False for s in yesterday_scores)
