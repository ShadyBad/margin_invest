"""Tests for calibration status endpoint."""

import asyncio
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import BacktestRun, PITFinancialSnapshot, UniverseSnapshot
from margin_api.db.session import get_db
from margin_api.schemas.calibration import CalibrationStatusResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class TestCalibrationStatusSchema:
    def test_schema_construction_empty(self):
        status = CalibrationStatusResponse(
            pit_data_available=False,
            pit_ticker_count=0,
            current_thresholds={
                "track_a": {"exceptional_power": 0.15},
                "track_b": {"exceptional_asymmetry": 5.0},
            },
        )
        assert status.pit_data_available is False
        assert status.pit_ticker_count == 0
        assert status.scoring_version == "v4"
        assert status.last_backtest_run is None

    def test_schema_construction_with_data(self):
        status = CalibrationStatusResponse(
            pit_data_available=True,
            pit_date_range_start="2009-01-01",
            pit_date_range_end="2025-12-31",
            pit_ticker_count=523,
            last_backtest_run="2026-03-03T00:00:00Z",
            validation_passed=True,
            validation_details={
                "excess_cagr": {"value": 5.2, "threshold": 3.0, "passed": True},
            },
            current_thresholds={
                "track_a": {"exceptional_power": 0.15},
                "track_b": {"exceptional_asymmetry": 5.0},
            },
        )
        assert status.pit_data_available is True
        assert status.pit_ticker_count == 523

    def test_serialization(self):
        status = CalibrationStatusResponse(
            pit_data_available=False,
            current_thresholds={"track_a": {}, "track_b": {}},
        )
        data = status.model_dump()
        assert "pit_data_available" in data
        assert "current_thresholds" in data
        assert "scoring_version" in data


@pytest.fixture
def db_client():
    """Client with in-memory SQLite DB for calibration-status endpoint tests."""

    async def _setup():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return engine, factory

    engine, factory = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_setup())

    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    tc = TestClient(app)
    yield tc, factory
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(engine.dispose())


class TestCalibrationStatusEndpoint:
    def test_returns_200(self, db_client):
        client, _ = db_client
        response = client.get("/api/v1/backtest/calibration-status")
        assert response.status_code == 200

    def test_empty_db_returns_no_pit_data(self, db_client):
        client, _ = db_client
        response = client.get("/api/v1/backtest/calibration-status")
        data = response.json()
        assert data["pit_data_available"] is False
        assert data["pit_ticker_count"] == 0
        assert data["pit_date_range_start"] is None
        assert data["pit_date_range_end"] is None
        assert data["last_backtest_run"] is None

    def test_has_current_thresholds(self, db_client):
        client, _ = db_client
        response = client.get("/api/v1/backtest/calibration-status")
        data = response.json()
        assert "current_thresholds" in data
        thresholds = data["current_thresholds"]
        assert "track_a" in thresholds
        assert "track_b" in thresholds
        assert thresholds["track_a"]["exceptional_power"] == 0.15
        assert thresholds["track_b"]["exceptional_asymmetry"] == 5.0

    def test_has_scoring_version(self, db_client):
        client, _ = db_client
        response = client.get("/api/v1/backtest/calibration-status")
        data = response.json()
        assert data["scoring_version"] == "v4"

    def test_with_pit_data(self, db_client):
        client, factory = db_client

        async def _seed():
            async with factory() as session:
                snap = PITFinancialSnapshot(
                    cik="0000320193",
                    ticker="AAPL",
                    filing_date=date(2023, 1, 15),
                    period_end=date(2022, 12, 31),
                    form_type="10-K",
                    accession_number="0000320193-23-000001",
                    fiscal_year=2022,
                    fiscal_quarter=None,
                )
                session.add(snap)
                snap2 = PITFinancialSnapshot(
                    cik="0000789019",
                    ticker="MSFT",
                    filing_date=date(2024, 7, 20),
                    period_end=date(2024, 6, 30),
                    form_type="10-Q",
                    accession_number="0000789019-24-000042",
                    fiscal_year=2024,
                    fiscal_quarter=2,
                )
                session.add(snap2)
                await session.commit()

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_seed())

        response = client.get("/api/v1/backtest/calibration-status")
        data = response.json()
        assert data["pit_data_available"] is True
        assert data["pit_ticker_count"] == 2
        assert data["pit_date_range_start"] == "2023-01-15"
        assert data["pit_date_range_end"] == "2024-07-20"

    def test_with_backtest_run(self, db_client):
        client, factory = db_client

        async def _seed():
            async with factory() as session:
                # BacktestRun requires a UniverseSnapshot FK
                universe = UniverseSnapshot(
                    version="v1",
                    config_hash="testhash",
                    ticker_count=1,
                    tickers=["AAPL"],
                    activated_at=datetime.now(UTC),
                )
                session.add(universe)
                await session.flush()

                run = BacktestRun(
                    name="test-run",
                    universe_snapshot_id=universe.id,
                    start_date="2020-01-01",
                    end_date="2025-12-31",
                    rebalance_frequency="monthly",
                    config={"test": True},
                    config_hash="abc123",
                    status="completed",
                    created_at=datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC),
                    summary_stats={
                        "validation_passed": True,
                        "validation_details": {
                            "excess_cagr": {"value": 5.2, "threshold": 3.0, "passed": True}
                        },
                    },
                )
                session.add(run)
                await session.commit()

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_seed())

        response = client.get("/api/v1/backtest/calibration-status")
        data = response.json()
        assert data["last_backtest_run"] is not None
        assert "2026-03-01" in data["last_backtest_run"]
        assert data["validation_passed"] is True
        assert data["validation_details"] is not None
        assert data["validation_details"]["excess_cagr"]["passed"] is True
