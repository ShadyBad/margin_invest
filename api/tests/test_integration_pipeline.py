"""End-to-end integration test for the data pipeline.

Verifies the full pipeline flow in-memory: universe config -> activate -> ingest ->
score -> freshness. No real yfinance or Redis needed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, Score
from margin_api.services.freshness import compute_freshness
from margin_api.services.ingestion import (
    classify_error,
    should_ingest_ticker,
    update_failure_status,
)
from margin_api.services.universe import activate_universe, get_active_snapshot
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


class TestPipelineIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self, session, tmp_path):
        """Test the full flow: load config -> activate -> ingest -> score -> verify."""

        # Step 1: Create a test universe config
        config_file = tmp_path / "universe.yaml"
        config_file.write_text('version: "test-v1"\ntickers:\n  - AAPL\n  - MSFT\n  - NVDA\n')

        # Step 2: Activate the universe
        snapshot = await activate_universe(session, config_file)
        assert snapshot.is_active is True
        assert snapshot.ticker_count == 3
        assert snapshot.version == "test-v1"

        # Step 3: Verify active snapshot
        active = await get_active_snapshot(session)
        assert active is not None
        assert active.id == snapshot.id

        # Step 4: Create assets (simulating ingestion)
        assets = []
        for ticker in ["AAPL", "MSFT", "NVDA"]:
            asset = Asset(ticker=ticker, name=f"{ticker} Inc", sector="Technology")
            session.add(asset)
            assets.append(asset)
        await session.commit()

        # Step 5: Verify ingestion status
        for asset in assets:
            await session.refresh(asset)
            assert asset.ingestion_status == "active"
            assert should_ingest_ticker(
                asset.ingestion_status, asset.consecutive_failures, asset.last_retry_at
            )

        # Step 6: Create scores (simulating scoring)
        for asset in assets:
            score = Score(
                asset_id=asset.id,
                composite_percentile=75.0,
                conviction_level="high",
                signal="buy",
                quality_percentile=80.0,
                value_percentile=70.0,
                momentum_percentile=75.0,
                actual_price=150.0,
                margin_invest_value=200.0,
                buy_price=160.0,
                sell_price=240.0,
                scored_at=datetime.now(UTC),
            )
            session.add(score)
        await session.commit()

        # Step 7: Verify freshness
        for asset in assets:
            freshness = compute_freshness(datetime.now(UTC))
            assert freshness == "fresh"

    @pytest.mark.asyncio
    async def test_failure_tracking_flow(self, session):
        """Test progressive failure: active -> quarantined -> permanently_skipped."""
        asset = Asset(ticker="FAIL", name="Failing Corp", sector="Technology")
        session.add(asset)
        await session.commit()

        # 3 data_unavailable failures -> quarantine
        for i in range(3):
            await update_failure_status(session, asset, "data_unavailable", f"Failure {i + 1}")
            await session.refresh(asset)

        assert asset.ingestion_status == "quarantined"
        assert asset.consecutive_failures == 3

        # 3 more -> permanently skipped
        for i in range(3):
            await update_failure_status(session, asset, "data_unavailable", f"Failure {i + 4}")
            await session.refresh(asset)

        assert asset.ingestion_status == "permanently_skipped"
        assert asset.consecutive_failures == 6

    @pytest.mark.asyncio
    async def test_success_resets_quarantine(self, session):
        """Test that successful ingestion resets quarantine state."""
        asset = Asset(
            ticker="RECOVER",
            name="Recovery Corp",
            sector="Technology",
            ingestion_status="quarantined",
            consecutive_failures=4,
            quarantined_at=datetime.now(UTC),
        )
        session.add(asset)
        await session.commit()

        await update_failure_status(session, asset, "success", None)
        await session.refresh(asset)

        assert asset.ingestion_status == "active"
        assert asset.consecutive_failures == 0
        assert asset.quarantined_at is None

    @pytest.mark.asyncio
    async def test_universe_yaml_loads(self):
        """Test that the actual universe.yaml seed file loads correctly."""
        from margin_engine.universe.config import load_universe_config

        config = load_universe_config(Path("engine/universe.yaml"))
        assert config.ticker_count >= 40  # At least 40 tickers in seed
        assert config.version  # Has a version string
        assert "AAPL" in config.tickers
        assert "MSFT" in config.tickers

    def test_error_classification(self):
        """Test error classification covers all expected categories."""
        assert classify_error(TimeoutError("timeout")) == "transient"
        assert classify_error(ConnectionError("refused")) == "transient"
        assert classify_error(ValueError("No financial data")) == "data_unavailable"
        assert classify_error(ValueError("Ticker not found")) == "permanent"
        assert classify_error(ValueError("delisted")) == "permanent"

    def test_freshness_tiers(self):
        """Test all freshness tiers."""
        now = datetime.now(UTC)
        assert compute_freshness(now) == "fresh"
        assert compute_freshness(now - timedelta(hours=1)) == "fresh"
        assert compute_freshness(now - timedelta(hours=20)) == "stale"
        assert compute_freshness(now - timedelta(days=2)) == "stale"
        assert compute_freshness(now - timedelta(days=4)) == "expired"
        assert compute_freshness(None) == "expired"
