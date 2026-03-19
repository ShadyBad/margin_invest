"""Additional admin route coverage tests targeting uncovered endpoints.

Covers: pit/backfill, pit/stats, pit/assemble-universe, pit/reparse,
historical/backfill, historical/stats, jobs/{id}/status, jobs/cancel-zombies,
backtest/precompute, backtest/latest, pit/data-quality, ingestion/quarantined,
ml/training-dry-run, and stage_universe_activation helper.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.base import Base
from margin_api.db.models import (
    Asset,
    BacktestRun,
    JobRun,
    PITDailyPrice,
    PITFinancialSnapshot,
    PITUniverseMembership,
    User,
    UserRole,
)
from margin_api.db.session import get_db
from margin_api.deps import get_admin_user
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_admin_user() -> User:
    user = MagicMock(spec=User)
    user.id = 1
    user.role = UserRole.ADMIN
    return user


def _make_client_with_override(app, db_override=None):
    app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
    if db_override is not None:
        app.dependency_overrides[get_db] = db_override
    return TestClient(app)


# ---------------------------------------------------------------------------
# In-memory SQLite fixtures for DB-backed endpoints
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
async def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


def _db_override(session_factory):
    async def override():
        async with session_factory() as s:
            yield s

    return override


# ---------------------------------------------------------------------------
# PIT Backfill (POST /api/v1/admin/pit/backfill)
# ---------------------------------------------------------------------------


class TestPITBackfill:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_pit_backfill_enqueues_job(self):
        mock_job = MagicMock()
        mock_job.job_id = "bootstrap-pit-abc"

        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
        mock_pool.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.create_pool", return_value=mock_pool),
        ):
            app = create_app()
            client = _make_client_with_override(app)
            resp = client.post("/api/v1/admin/pit/backfill")

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "enqueued"
        assert data["job"] == "bootstrap_pit_data"
        assert data["job_id"] == "bootstrap-pit-abc"
        mock_pool.enqueue_job.assert_called_once()
        assert mock_pool.enqueue_job.call_args[0][0] == "bootstrap_pit_data"

    def test_pit_backfill_redis_failure(self):
        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.create_pool",
                side_effect=ConnectionError("Redis down"),
            ),
        ):
            app = create_app()
            client = _make_client_with_override(app)
            resp = client.post("/api/v1/admin/pit/backfill")

        assert resp.status_code == 503

    def test_pit_backfill_requires_auth(self):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
            resp = client.post("/api/v1/admin/pit/backfill")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PIT Stats (GET /api/v1/admin/pit/stats)
# ---------------------------------------------------------------------------


class TestPITStats:
    @pytest.mark.asyncio
    async def test_pit_stats_empty_db(self, session_factory):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.get("/api/v1/admin/pit/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pit_financial_snapshots"] == 0
        assert data["pit_daily_prices"] == 0
        assert data["pit_universe_memberships"] == 0

    @pytest.mark.asyncio
    async def test_pit_stats_with_data(self, session_factory, db_session):
        from datetime import date as date_type

        # Seed one record of each type
        snapshot = PITFinancialSnapshot(
            cik="0000320193",
            ticker="AAPL",
            fiscal_year=2024,
            fiscal_quarter=4,
            form_type="10-K",
            accession_number="0001234567-24-000001",
            filing_date=date_type(2024, 11, 1),
            period_end=date_type(2024, 9, 28),
        )
        db_session.add(snapshot)

        price = PITDailyPrice(
            ticker="AAPL",
            date=date_type(2024, 11, 1),
            close=175.00,
            open=174.00,
            high=176.00,
            low=173.00,
            volume=50000000,
            adj_close=175.00,
        )
        db_session.add(price)

        membership = PITUniverseMembership(
            ticker="AAPL",
            cik="0000320193",
            quarter_date=date_type(2024, 1, 1),
            is_active=True,
            market_cap=3000000000000.0,
        )
        db_session.add(membership)
        await db_session.commit()

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.get("/api/v1/admin/pit/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pit_financial_snapshots"] == 1
        assert data["pit_daily_prices"] == 1
        assert data["pit_universe_memberships"] == 1


# ---------------------------------------------------------------------------
# PIT Assemble Universe (POST /api/v1/admin/pit/assemble-universe)
# ---------------------------------------------------------------------------


class TestPITAssembleUniverse:
    @pytest.mark.asyncio
    async def test_assemble_universe_success(self, session_factory):
        assemble_result = {"assembled": 100, "skipped": 5}
        fill_result = 42

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.services.edgar.universe_assembly.assemble_universe",
                new_callable=AsyncMock,
                return_value=assemble_result,
            ),
            patch(
                "margin_api.services.edgar.universe_assembly.fill_last_known_prices",
                new_callable=AsyncMock,
                return_value=fill_result,
            ),
        ):
            app = create_app()
            client = _make_client_with_override(app, _db_override(session_factory))
            resp = client.post("/api/v1/admin/pit/assemble-universe")

        assert resp.status_code == 200
        data = resp.json()
        assert data["assembled"] == 100
        assert data["last_known_prices_filled"] == 42


# ---------------------------------------------------------------------------
# PIT Reparse (POST /api/v1/admin/pit/reparse)
# ---------------------------------------------------------------------------


class TestPITReparse:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_pit_reparse_enqueues_job(self):
        mock_job = MagicMock()
        mock_job.job_id = "reparse-pit-xyz"

        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
        mock_pool.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.create_pool", return_value=mock_pool),
        ):
            app = create_app()
            client = _make_client_with_override(app)
            resp = client.post("/api/v1/admin/pit/reparse")

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "enqueued"
        assert data["job"] == "reparse_pit_filings"
        assert data["job_id"] == "reparse-pit-xyz"

    def test_pit_reparse_redis_failure(self):
        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.create_pool",
                side_effect=ConnectionError("Redis down"),
            ),
        ):
            app = create_app()
            client = _make_client_with_override(app)
            resp = client.post("/api/v1/admin/pit/reparse")

        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Historical Backfill (POST /api/v1/admin/historical/backfill)
# ---------------------------------------------------------------------------


class TestHistoricalBackfill:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_historical_backfill_enqueues_job(self):
        mock_job = MagicMock()
        mock_job.job_id = "hist-backfill-001"

        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
        mock_pool.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.create_pool", return_value=mock_pool),
        ):
            app = create_app()
            client = _make_client_with_override(app)
            resp = client.post("/api/v1/admin/historical/backfill")

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "enqueued"
        assert data["job"] == "backfill_historical_scores"
        assert data["job_id"] == "hist-backfill-001"

    def test_historical_backfill_redis_failure(self):
        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.create_pool",
                side_effect=ConnectionError("Redis down"),
            ),
        ):
            app = create_app()
            client = _make_client_with_override(app)
            resp = client.post("/api/v1/admin/historical/backfill")

        assert resp.status_code == 503

    def test_historical_backfill_requires_auth(self):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
            resp = client.post("/api/v1/admin/historical/backfill")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Historical Stats (GET /api/v1/admin/historical/stats)
# ---------------------------------------------------------------------------


class TestHistoricalStats:
    @pytest.mark.asyncio
    async def test_historical_stats_empty(self, session_factory):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.get("/api/v1/admin/historical/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["historical_scores"] == 0
        assert data["quarters_scored"] == 0
        assert data["min_date"] is None
        assert data["max_date"] is None

    @pytest.mark.asyncio
    async def test_historical_stats_with_data(self, session_factory, db_session):
        from datetime import date as date_type

        from margin_api.db.models import HistoricalScore

        score = HistoricalScore(
            ticker="AAPL",
            score_date=date_type(2024, 9, 30),
            composite_score=85.0,
            composite_tier="high",
        )
        db_session.add(score)
        await db_session.commit()

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.get("/api/v1/admin/historical/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["historical_scores"] == 1
        assert data["quarters_scored"] == 1
        assert data["min_date"] is not None
        assert data["max_date"] is not None


# ---------------------------------------------------------------------------
# Update Job Status (PATCH /api/v1/admin/jobs/{job_id}/status)
# ---------------------------------------------------------------------------


class TestUpdateJobStatus:
    @pytest.mark.asyncio
    async def test_update_job_status_success(self, session_factory, db_session):
        job = JobRun(
            job_type="train_ml_models",
            status="running",
            triggered_by="schedule",
            started_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        job_id = job.id

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.patch(
            f"/api/v1/admin/jobs/{job_id}/status",
            json={"status": "cancelled"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id
        assert data["old_status"] == "running"
        assert data["new_status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_update_job_status_not_found(self, session_factory):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.patch(
            "/api/v1/admin/jobs/99999/status",
            json={"status": "cancelled"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_job_status_invalid_status(self, session_factory):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.patch(
            "/api/v1/admin/jobs/1/status",
            json={"status": "invalid_status"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_job_with_error_message(self, session_factory, db_session):
        job = JobRun(
            job_type="train_ml_models",
            status="running",
            triggered_by="schedule",
            started_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        job_id = job.id

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.patch(
            f"/api/v1/admin/jobs/{job_id}/status",
            json={"status": "failed", "error_message": "Timeout error"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_status"] == "failed"


# ---------------------------------------------------------------------------
# Cancel Zombie Jobs (POST /api/v1/admin/jobs/cancel-zombies)
# ---------------------------------------------------------------------------


class TestCancelZombieJobs:
    @pytest.mark.asyncio
    async def test_cancel_zombies_no_zombies(self, session_factory):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.post(
            "/api/v1/admin/jobs/cancel-zombies",
            json={"job_type": "train_ml_models"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cancelled"] == 0
        assert data["job_ids"] == []

    @pytest.mark.asyncio
    async def test_cancel_zombies_with_old_running_job(self, session_factory, db_session):
        from datetime import timedelta

        # Job started > 1 hour ago, still "running"
        old_start = datetime.now(UTC) - timedelta(hours=2)
        job = JobRun(
            job_type="train_ml_models",
            status="running",
            triggered_by="schedule",
            started_at=old_start,
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        job_id = job.id

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.post(
            "/api/v1/admin/jobs/cancel-zombies",
            json={"job_type": "train_ml_models"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cancelled"] == 1
        assert job_id in data["job_ids"]

    @pytest.mark.asyncio
    async def test_cancel_zombies_default_job_type(self, session_factory):
        """Without a body, uses default job_type=train_ml_models."""
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        # Send request without content-type header so body parsing uses default
        resp = client.post("/api/v1/admin/jobs/cancel-zombies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cancelled"] == 0


# ---------------------------------------------------------------------------
# Backtest Precompute (POST /api/v1/admin/backtest/precompute)
# ---------------------------------------------------------------------------


class TestBacktestPrecompute:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_backtest_precompute_enqueues_job(self):
        mock_job = MagicMock()
        mock_job.job_id = "precompute-bt-001"

        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
        mock_pool.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.create_pool", return_value=mock_pool),
        ):
            app = create_app()
            client = _make_client_with_override(app)
            resp = client.post("/api/v1/admin/backtest/precompute")

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "enqueued"
        assert data["job"] == "precompute_default_backtest"
        assert data["job_id"] == "precompute-bt-001"

    def test_backtest_precompute_redis_failure(self):
        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch(
                "margin_api.routes.admin.create_pool",
                side_effect=ConnectionError("Redis down"),
            ),
        ):
            app = create_app()
            client = _make_client_with_override(app)
            resp = client.post("/api/v1/admin/backtest/precompute")

        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Backtest Latest (GET /api/v1/admin/backtest/latest)
# ---------------------------------------------------------------------------


class TestBacktestLatest:
    @pytest.mark.asyncio
    async def test_backtest_latest_not_found(self, session_factory):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.get("/api/v1/admin/backtest/latest")
        assert resp.status_code == 404

    async def _seed_snapshot(self, db_session) -> int:
        """Create a UniverseSnapshot and return its id."""
        from margin_api.db.models import UniverseSnapshot

        snap = UniverseSnapshot(
            version="v1",
            config_hash="abc123",
            ticker_count=10,
            tickers=["AAPL"],
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        db_session.add(snap)
        await db_session.flush()
        return snap.id

    @pytest.mark.asyncio
    async def test_backtest_latest_returns_run(self, session_factory, db_session):
        snap_id = await self._seed_snapshot(db_session)
        run = BacktestRun(
            name="default",
            universe_snapshot_id=snap_id,
            start_date="2020-01-01",
            end_date="2025-12-31",
            rebalance_frequency="quarterly",
            config={"strategy": "default"},
            config_hash="hash123",
            status="complete",
            total_return=0.35,
            annualized_return=0.12,
            sharpe_ratio=1.5,
            max_drawdown=-0.18,
            started_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            completed_at=datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC),
        )
        db_session.add(run)
        await db_session.commit()

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.get("/api/v1/admin/backtest/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "default"
        assert data["status"] == "complete"
        assert data["metrics"]["total_return"] == 0.35
        assert data["metrics"]["sharpe_ratio"] == 1.5
        assert data["duration_seconds"] == 3600.0

    @pytest.mark.asyncio
    async def test_backtest_latest_no_dates(self, session_factory, db_session):
        """Run without started_at/completed_at has duration_seconds=None."""
        snap_id = await self._seed_snapshot(db_session)
        run = BacktestRun(
            name="no-dates",
            universe_snapshot_id=snap_id,
            start_date="2020-01-01",
            end_date="2025-12-31",
            rebalance_frequency="quarterly",
            config={},
            config_hash="hash456",
            status="running",
        )
        db_session.add(run)
        await db_session.commit()

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.get("/api/v1/admin/backtest/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["duration_seconds"] is None


# ---------------------------------------------------------------------------
# PIT Data Quality (GET /api/v1/admin/pit/data-quality)
# ---------------------------------------------------------------------------


class TestPITDataQuality:
    @pytest.mark.asyncio
    async def test_pit_data_quality_empty(self, session_factory):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.get("/api/v1/admin/pit/data-quality")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_snapshots"] == 0
        assert data["null_income_statement"] == 0
        assert data["null_balance_sheet"] == 0
        assert data["null_cash_flow"] == 0
        assert data["null_shares_outstanding"] == 0
        assert data["year_distribution"] == {}
        assert data["sample_null_bs"] == []
        assert data["sample_with_bs"] == []

    @pytest.mark.asyncio
    async def test_pit_data_quality_with_snapshot(self, session_factory, db_session):
        from datetime import date as date_type

        # Snapshot with balance_sheet populated (no income_statement or cash_flow)
        snapshot = PITFinancialSnapshot(
            cik="0000789019",
            ticker="MSFT",
            fiscal_year=2023,
            fiscal_quarter=4,
            form_type="10-K",
            accession_number="0001234567-23-000001",
            filing_date=date_type(2023, 7, 27),
            period_end=date_type(2023, 6, 30),
            balance_sheet={"totalAssets": 411976000000},
        )
        db_session.add(snapshot)
        await db_session.commit()

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.get("/api/v1/admin/pit/data-quality")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_snapshots"] == 1
        assert data["null_balance_sheet"] == 0
        assert "2023" in data["year_distribution"]
        assert len(data["sample_with_bs"]) == 1


# ---------------------------------------------------------------------------
# Ingestion Quarantined (GET /api/v1/admin/ingestion/quarantined)
# ---------------------------------------------------------------------------


class TestIngestionQuarantined:
    @pytest.mark.asyncio
    async def test_quarantined_empty(self, session_factory):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.get("/api/v1/admin/ingestion/quarantined")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_quarantined_returns_assets(self, session_factory, db_session):
        q_asset = Asset(
            ticker="FAIL",
            name="Failed Corp",
            sector="Technology",
            market_cap=Decimal("1000000"),
            ingestion_status="quarantined",
            consecutive_failures=3,
            last_failure_reason="HTTP 429",
        )
        skip_asset = Asset(
            ticker="SKIP",
            name="Skip Corp",
            sector="Technology",
            market_cap=Decimal("500000"),
            ingestion_status="permanently_skipped",
            consecutive_failures=10,
        )
        ok_asset = Asset(
            ticker="GOOD",
            name="Good Corp",
            sector="Technology",
            market_cap=Decimal("10000000"),
            ingestion_status="active",
        )
        db_session.add_all([q_asset, skip_asset, ok_asset])
        await db_session.commit()

        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.get("/api/v1/admin/ingestion/quarantined")
        assert resp.status_code == 200
        data = resp.json()
        # Only quarantined + permanently_skipped, not active
        tickers = [a["ticker"] for a in data]
        assert "FAIL" in tickers
        assert "SKIP" in tickers
        assert "GOOD" not in tickers
        # Check fields
        fail_entry = next(a for a in data if a["ticker"] == "FAIL")
        assert fail_entry["ingestion_status"] == "quarantined"
        assert fail_entry["consecutive_failures"] == 3
        assert fail_entry["last_failure_reason"] == "HTTP 429"


# ---------------------------------------------------------------------------
# ML Training Dry Run (GET /api/v1/admin/ml/training-dry-run)
# ---------------------------------------------------------------------------


class TestMLTrainingDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_empty_db(self, session_factory):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
        client = _make_client_with_override(app, _db_override(session_factory))
        resp = client.get("/api/v1/admin/ml/training-dry-run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["v4score_rows"] == 0
        assert data["valid_composites"] == 0
        assert data["verdict"] == "NOT_READY"


# ---------------------------------------------------------------------------
# stage_universe_activation helper
# ---------------------------------------------------------------------------


class TestStageUniverseActivation:
    @pytest.mark.asyncio
    async def test_stage_universe_activation_no_existing_snapshot(
        self, session_factory, db_session
    ):
        """With no active snapshot, creates approval with empty current tickers."""
        from pathlib import Path

        from margin_api.routes.admin import stage_universe_activation

        mock_config = MagicMock()
        mock_config.tickers = ["AAPL", "MSFT", "GOOG"]

        with patch("margin_api.routes.admin.load_universe_config", return_value=mock_config):
            result = await stage_universe_activation(db_session, Path("/fake/universe.yaml"))

        assert result["status"] == "staged"
        assert result["approval_id"] is not None
        assert sorted(result["added_tickers"]) == ["AAPL", "GOOG", "MSFT"]
        assert result["removed_tickers"] == []

    @pytest.mark.asyncio
    async def test_stage_universe_activation_with_existing_snapshot(
        self, session_factory, db_session
    ):
        """Diffs proposed vs current tickers correctly."""
        from pathlib import Path

        from margin_api.db.models import UniverseSnapshot
        from margin_api.routes.admin import stage_universe_activation

        snapshot = UniverseSnapshot(
            version="v1",
            config_hash="abc123",
            ticker_count=3,
            tickers=["AAPL", "MSFT", "INTC"],
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        db_session.add(snapshot)
        await db_session.commit()

        mock_config = MagicMock()
        mock_config.tickers = ["AAPL", "MSFT", "NVDA"]  # INTC removed, NVDA added

        with patch("margin_api.routes.admin.load_universe_config", return_value=mock_config):
            result = await stage_universe_activation(db_session, Path("/fake/universe.yaml"))

        assert result["status"] == "staged"
        assert result["added_tickers"] == ["NVDA"]
        assert result["removed_tickers"] == ["INTC"]
