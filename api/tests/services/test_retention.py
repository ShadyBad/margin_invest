"""Tests for DB retention policies."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import (
    FilingText,
    JobRun,
    RiskFactorAnalysis,
    User,
    WebhookDelivery,
    WebhookSubscription,
)
from margin_api.services.retention import (
    blank_diffed_risk_factor_text,
    purge_job_runs,
    purge_webhook_deliveries,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Async DB fixtures (SQLite in-memory for speed)
# ---------------------------------------------------------------------------


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
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purge_job_runs_deletes_rows_older_than_cutoff(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    old_run = JobRun(
        job_type="full_score",
        status="completed",
        triggered_by="schedule",
        started_at=now - timedelta(days=45),
        completed_at=now - timedelta(days=45),
    )
    fresh_run = JobRun(
        job_type="full_score",
        status="completed",
        triggered_by="schedule",
        started_at=now - timedelta(days=5),
        completed_at=now - timedelta(days=5),
    )
    session.add(old_run)
    session.add(fresh_run)
    await session.flush()

    deleted = await purge_job_runs(session, days=30)

    assert deleted == 1
    remaining = (await session.execute(select(JobRun))).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].id == fresh_run.id


@pytest.mark.asyncio
async def test_purge_job_runs_with_no_old_rows_returns_zero(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    fresh_run = JobRun(
        job_type="full_score",
        status="completed",
        triggered_by="chained",
        started_at=now - timedelta(days=1),
        completed_at=now - timedelta(days=1),
    )
    session.add(fresh_run)
    await session.flush()

    deleted = await purge_job_runs(session, days=30)

    assert deleted == 0
    remaining = (await session.execute(select(JobRun))).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].id == fresh_run.id


@pytest.mark.asyncio
async def test_purge_webhook_deliveries_keeps_failed_deletes_old_success(
    session: AsyncSession,
) -> None:
    now = datetime.now(UTC)

    # Parent: a user (created_by FK) and a subscription
    user = User(email="webhook-owner@example.com")
    session.add(user)
    await session.flush()

    subscription = WebhookSubscription(
        event_type="score.published",
        url="https://example.com/hooks/scores",
        hmac_key_encrypted="encrypted-key",
        created_by=user.id,
    )
    session.add(subscription)
    await session.flush()

    old_delivered = WebhookDelivery(
        subscription_id=subscription.id,
        event_type="score.published",
        payload={"ticker": "AAPL"},
        status="delivered",
        attempts=1,
        delivered_at=now - timedelta(days=45),
    )
    old_dead_letter = WebhookDelivery(
        subscription_id=subscription.id,
        event_type="score.published",
        payload={"ticker": "MSFT"},
        status="dead_letter",
        attempts=5,
        delivered_at=now - timedelta(days=45),
    )
    fresh_delivered = WebhookDelivery(
        subscription_id=subscription.id,
        event_type="score.published",
        payload={"ticker": "GOOG"},
        status="delivered",
        attempts=1,
        delivered_at=now - timedelta(days=5),
    )
    mid_flight = WebhookDelivery(
        subscription_id=subscription.id,
        event_type="score.published",
        payload={},
        status="pending",
        attempts=1,
        delivered_at=None,
    )
    session.add_all([old_delivered, old_dead_letter, fresh_delivered, mid_flight])
    await session.flush()

    deleted = await purge_webhook_deliveries(session, days=30)

    assert deleted == 1  # only the old "delivered" row
    remaining = (await session.execute(select(WebhookDelivery))).scalars().all()
    assert len(remaining) == 3
    assert sorted(d.status for d in remaining) == ["dead_letter", "delivered", "pending"]


@pytest.mark.asyncio
async def test_blank_diffed_risk_factor_text_only_blanks_diffed_filings(
    session: AsyncSession,
) -> None:
    diffed_filing = FilingText(
        ticker="AAPL",
        cik="0000320193",
        filing_type="10-K",
        filing_date=date(2025, 11, 1),
        period_end=date(2025, 9, 30),
        risk_factors_text="A very long risk factors blob ...",
        raw_html_hash="hash_a",
    )
    session.add(diffed_filing)
    await session.flush()

    not_diffed_filing = FilingText(
        ticker="MSFT",
        cik="0000789019",
        filing_type="10-K",
        filing_date=date(2025, 7, 1),
        period_end=date(2025, 6, 30),
        risk_factors_text="A very long risk factors blob ...",
        raw_html_hash="hash_b",
    )
    session.add(not_diffed_filing)
    await session.flush()

    prior_filing = FilingText(
        ticker="AAPL",
        cik="0000320193",
        filing_type="10-K",
        filing_date=date(2024, 11, 1),
        period_end=date(2024, 9, 30),
        risk_factors_text="prior blob",
        raw_html_hash="hash_prior",
    )
    session.add(prior_filing)
    await session.flush()

    analysis = RiskFactorAnalysis(
        ticker="AAPL",
        filing_text_id=diffed_filing.id,
        prior_filing_text_id=prior_filing.id,
        prompt_version="v1",
    )
    session.add(analysis)
    await session.flush()

    blanked = await blank_diffed_risk_factor_text(session)

    assert blanked == 1

    aapl = await session.get(FilingText, diffed_filing.id)
    assert aapl is not None
    assert aapl.risk_factors_text is None
    assert aapl.raw_html_hash == "hash_a"

    msft = await session.get(FilingText, not_diffed_filing.id)
    assert msft is not None
    assert msft.risk_factors_text is not None
