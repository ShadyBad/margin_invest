"""Tests for the ingestion service."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset
from margin_api.services.ingestion import (
    classify_error,
    should_ingest_ticker,
    update_failure_status,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


class TestClassifyError:
    def test_timeout_is_transient(self):
        assert classify_error(TimeoutError("connection timed out")) == "transient"

    def test_connection_error_is_transient(self):
        assert classify_error(ConnectionError("refused")) == "transient"

    def test_value_error_is_data_unavailable(self):
        assert classify_error(ValueError("No financial data")) == "data_unavailable"

    def test_key_error_is_data_unavailable(self):
        assert classify_error(KeyError("missing_field")) == "data_unavailable"

    def test_ticker_not_found_is_permanent(self):
        assert classify_error(ValueError("Ticker not found")) == "permanent"

    def test_delisted_is_permanent(self):
        assert classify_error(ValueError("delisted")) == "permanent"


class TestShouldIngestTicker:
    def test_active_ticker_should_ingest(self):
        assert should_ingest_ticker("active", 0, None) is True

    def test_permanently_skipped_should_not_ingest(self):
        assert should_ingest_ticker("permanently_skipped", 6, None) is False

    def test_quarantined_within_7_days_should_not_ingest(self):
        recent = datetime.now(UTC)
        assert should_ingest_ticker("quarantined", 3, recent) is False

    def test_quarantined_after_7_days_should_ingest(self):
        from datetime import timedelta
        old = datetime.now(UTC) - timedelta(days=8)
        assert should_ingest_ticker("quarantined", 3, old) is True


class TestUpdateFailureStatus:
    @pytest.mark.asyncio
    async def test_data_unavailable_increments_failures(self, session):
        asset = Asset(ticker="XYZW", name="XYZ Corp", sector="Technology")
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "data_unavailable", "No data")
        await session.refresh(asset)
        assert asset.consecutive_failures == 1
        assert asset.ingestion_status == "active"

    @pytest.mark.asyncio
    async def test_three_failures_quarantines(self, session):
        asset = Asset(
            ticker="XYZW", name="XYZ Corp", sector="Technology",
            consecutive_failures=2,
        )
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "data_unavailable", "No data")
        await session.refresh(asset)
        assert asset.consecutive_failures == 3
        assert asset.ingestion_status == "quarantined"
        assert asset.quarantined_at is not None

    @pytest.mark.asyncio
    async def test_six_failures_permanently_skips(self, session):
        asset = Asset(
            ticker="XYZW", name="XYZ Corp", sector="Technology",
            ingestion_status="quarantined",
            consecutive_failures=5,
            quarantined_at=datetime.now(UTC),
        )
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "data_unavailable", "No data")
        await session.refresh(asset)
        assert asset.consecutive_failures == 6
        assert asset.ingestion_status == "permanently_skipped"

    @pytest.mark.asyncio
    async def test_permanent_error_skips_immediately(self, session):
        asset = Asset(ticker="DEAD", name="Dead Corp", sector="Technology")
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "permanent", "Ticker delisted")
        await session.refresh(asset)
        assert asset.ingestion_status == "permanently_skipped"

    @pytest.mark.asyncio
    async def test_transient_does_not_increment(self, session):
        asset = Asset(ticker="AAPL", name="Apple", sector="Technology")
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "transient", "Timeout")
        await session.refresh(asset)
        assert asset.consecutive_failures == 0
        assert asset.ingestion_status == "active"

    @pytest.mark.asyncio
    async def test_success_resets_failures(self, session):
        asset = Asset(
            ticker="XYZW", name="XYZ Corp", sector="Technology",
            ingestion_status="quarantined",
            consecutive_failures=4,
            quarantined_at=datetime.now(UTC),
        )
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "success", None)
        await session.refresh(asset)
        assert asset.consecutive_failures == 0
        assert asset.ingestion_status == "active"
        assert asset.quarantined_at is None
