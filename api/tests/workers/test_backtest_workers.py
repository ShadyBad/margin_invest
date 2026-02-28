"""Tests for backtest worker functions."""

from __future__ import annotations

import os
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from margin_api.config import get_settings
from margin_api.db.models import (
    BacktestRun,
    JobRun,
    ShadowPortfolioSnapshot,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_execute_result(**kwargs):
    """Build a MagicMock that behaves like a SQLAlchemy Result.

    SQLAlchemy's Result methods (scalar_one, scalar_one_or_none, all, scalars)
    are synchronous, not async.
    """
    result = MagicMock()
    result.scalar_one.return_value = kwargs.get("scalar_one", 0)
    result.scalar_one_or_none.return_value = kwargs.get("scalar_one_or_none", None)
    result.all.return_value = kwargs.get("all", [])
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = kwargs.get("scalars_all", [])
    result.scalars.return_value = scalars_mock
    return result


def _mock_session_factory(execute_side_effects: list | None = None):
    """Build a mock async session factory.

    execute_side_effects: list of dicts to pass to _make_execute_result,
    one per session.execute() call.  When exhausted, returns a default
    result that acts like an updated JobRun.
    """
    effects = list(execute_side_effects or [])
    call_idx = {"n": 0}
    added_objects: list = []

    session = MagicMock()
    session.commit = AsyncMock()

    async def _execute(stmt):
        idx = call_idx["n"]
        call_idx["n"] += 1
        if idx < len(effects):
            return _make_execute_result(**effects[idx])
        # Default: return a mutable MagicMock (for job update queries)
        job_mock = MagicMock()
        job_mock.id = 42
        return _make_execute_result(scalar_one=job_mock)

    session.execute = _execute

    def _add(obj):
        added_objects.append(obj)
        if isinstance(obj, JobRun):
            obj.id = 42

    session.add = _add

    # Make session usable as async context manager
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=ctx)
    return factory, session, added_objects


# ---------------------------------------------------------------------------
# precompute_default_backtest tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_precompute_skips_when_no_pit_data():
    """Worker should skip gracefully when PIT tables are empty."""
    from margin_api.workers import precompute_default_backtest

    job_mock = MagicMock()
    job_mock.id = 42

    # Call sequence:
    # 1. JobRun creation (session.add, not execute)
    # 2. PIT count query → 0
    # 3. Job update (scalar_one → job mock object)
    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"scalar_one": 0},  # PIT count → 0
            {"scalar_one": job_mock},  # job update query → job object
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
    ):
        result = await precompute_default_backtest({})

    assert result["status"] == "skipped"
    assert result["reason"] == "no_pit_data"

    # Should have created a JobRun
    job_runs = [o for o in added if isinstance(o, JobRun)]
    assert len(job_runs) == 1
    assert job_runs[0].job_type == "precompute_default_backtest"


@pytest.mark.asyncio
async def test_precompute_runs_with_pit_data():
    """Worker should run the backtest when PIT data exists."""
    from margin_api.workers import precompute_default_backtest
    from margin_engine.backtesting.models import PerformanceMetrics
    from margin_engine.backtesting.replay_orchestrator import ReplayConfig, ReplayResult

    # Build a minimal ReplayResult
    metrics = PerformanceMetrics(
        cagr=0.12,
        excess_cagr=0.04,
        sharpe_ratio=0.95,
        sortino_ratio=1.3,
        max_drawdown=0.25,
        win_rate=0.58,
        information_ratio=0.7,
        total_return=6.0,
        benchmark_total_return=4.0,
        num_months=192,
        avg_turnover=0.15,
    )
    replay_result = ReplayResult(
        config=ReplayConfig(start_date=date(2009, 1, 1)),
        metrics=metrics,
        snapshots=[],
        audit_log=[],
        regime_segments={},
        factor_timeline=[],
        duration_seconds=1.5,
    )

    universe_snap = MagicMock()
    universe_snap.id = 1

    # Call sequence:
    # 1. PIT count query → 100 (has data)
    # 2+ job updates
    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"scalar_one": 100},  # PIT count → nonzero
        ]
    )

    mock_orchestrator = MagicMock()
    mock_orchestrator.run_async = AsyncMock(return_value=replay_result)

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.workers.get_active_snapshot", return_value=universe_snap),
        patch(
            "margin_engine.backtesting.replay_orchestrator.ReplayOrchestrator",
            return_value=mock_orchestrator,
        ),
    ):
        result = await precompute_default_backtest({})

    assert result["status"] == "completed"
    assert result["metrics"]["cagr"] == 0.12
    assert result["metrics"]["sharpe_ratio"] == 0.95

    # Should have added JobRun + BacktestRun
    backtest_runs = [o for o in added if isinstance(o, BacktestRun)]
    assert len(backtest_runs) == 1
    assert backtest_runs[0].name == "default"
    assert backtest_runs[0].status == "complete"
    assert backtest_runs[0].total_return == 6.0
    assert backtest_runs[0].sharpe_ratio == 0.95


# ---------------------------------------------------------------------------
# snapshot_shadow_portfolio tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_snapshot_shadow_empty_scores():
    """Worker should handle no published scores gracefully."""
    from margin_api.workers import snapshot_shadow_portfolio

    # Call sequence:
    # 1. V4Score query → empty
    # 2. Existing snapshot check → None
    # 3+ job updates
    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"all": []},  # V4Score query → empty
            {"scalar_one_or_none": None},  # existing snapshot check → None
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
    ):
        result = await snapshot_shadow_portfolio({})

    assert result["status"] == "completed"
    assert result["positions"] == 0

    # Should have added a ShadowPortfolioSnapshot with 0 positions
    snapshots = [o for o in added if isinstance(o, ShadowPortfolioSnapshot)]
    assert len(snapshots) == 1
    assert snapshots[0].num_positions == 0
    assert snapshots[0].portfolio_value == 1_000_000.0


@pytest.mark.asyncio
async def test_snapshot_shadow_with_published_scores():
    """Worker should record positions from published V4Scores."""
    from margin_api.workers import snapshot_shadow_portfolio

    # Build mock V4Score rows
    v4_1 = MagicMock()
    v4_1.composite_score = 85.0
    v4_1.conviction = "high"
    v4_2 = MagicMock()
    v4_2.composite_score = 72.0
    v4_2.conviction = "moderate"

    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"all": [(v4_1, "AAPL"), (v4_2, "MSFT")]},  # V4Score query
            {"scalar_one_or_none": None},  # existing snapshot check → None
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
    ):
        result = await snapshot_shadow_portfolio({})

    assert result["status"] == "completed"
    assert result["positions"] == 2

    snapshots = [o for o in added if isinstance(o, ShadowPortfolioSnapshot)]
    assert len(snapshots) == 1
    snap = snapshots[0]
    assert snap.num_positions == 2
    assert len(snap.positions_json) == 2
    assert snap.positions_json[0]["ticker"] == "AAPL"
    assert snap.positions_json[0]["score"] == 85.0
    assert snap.positions_json[0]["conviction"] == "high"
    assert snap.positions_json[0]["weight"] == 0.5
    assert snap.positions_json[1]["ticker"] == "MSFT"


@pytest.mark.asyncio
async def test_snapshot_shadow_idempotent_skip():
    """Worker should skip if snapshot for today already exists."""
    from margin_api.workers import snapshot_shadow_portfolio

    existing_snap = MagicMock()

    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"all": []},  # V4Score query → empty
            {"scalar_one_or_none": existing_snap},  # existing snapshot → already exists
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
    ):
        result = await snapshot_shadow_portfolio({})

    assert result["status"] == "completed"
    assert result["positions"] == 0

    # Should NOT have added any ShadowPortfolioSnapshot (skipped)
    snapshots = [o for o in added if isinstance(o, ShadowPortfolioSnapshot)]
    assert len(snapshots) == 0


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestWorkerRegistration:
    """Verify both workers are registered in WorkerSettings."""

    def test_precompute_default_backtest_in_functions(self):
        from margin_api.workers import WorkerSettings, precompute_default_backtest

        assert precompute_default_backtest in WorkerSettings.functions

    def test_snapshot_shadow_portfolio_in_functions(self):
        from margin_api.workers import WorkerSettings, snapshot_shadow_portfolio

        assert snapshot_shadow_portfolio in WorkerSettings.functions

    def test_bootstrap_pit_data_in_functions(self):
        from margin_api.workers import WorkerSettings

        func_names = [
            f.name if hasattr(f, "name") else f.__name__ for f in WorkerSettings.functions
        ]
        assert "bootstrap_pit_data" in func_names

    def test_precompute_in_cron_jobs(self):
        from margin_api.workers import WorkerSettings

        cron_funcs = [
            job.coroutine.__name__ if hasattr(job, "coroutine") else str(job)
            for job in WorkerSettings.cron_jobs
        ]
        assert "precompute_default_backtest" in cron_funcs

    def test_snapshot_in_cron_jobs(self):
        from margin_api.workers import WorkerSettings

        cron_funcs = [
            job.coroutine.__name__ if hasattr(job, "coroutine") else str(job)
            for job in WorkerSettings.cron_jobs
        ]
        assert "snapshot_shadow_portfolio" in cron_funcs


# ---------------------------------------------------------------------------
# bootstrap_pit_data tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_is_idempotent_with_existing_data():
    """Worker should run even when data exists (only fetches missing data)."""
    from margin_api.workers import bootstrap_pit_data

    job_mock = MagicMock()
    job_mock.id = 42

    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"scalar_one": 5000},  # existing filing count
            {"all": [("AAPL",), ("MSFT",)]},  # distinct tickers query
        ]
    )

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    # EDGAR returns 0 new inserts (all already exist)
    edgar_result = {"total": 100, "inserted": 0, "skipped": 100, "failed": 0}
    price_result = {"AAPL": 0, "MSFT": 0}
    universe_result = {"quarters_processed": 68, "tickers_tracked": 2, "delistings_detected": 0}

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_api.workers.run_edgar_backfill",
            new_callable=AsyncMock,
            return_value=edgar_result,
        ),
        patch(
            "margin_api.workers.backfill_prices_for_tickers",
            new_callable=AsyncMock,
            return_value=price_result,
        ),
        patch(
            "margin_api.workers.assemble_universe",
            new_callable=AsyncMock,
            return_value=universe_result,
        ),
        patch(
            "margin_api.workers.fill_last_known_prices",
            new_callable=AsyncMock,
            return_value=0,
        ),
    ):
        result = await bootstrap_pit_data({"redis": mock_redis})

    # Should complete (not skip), even though data exists
    assert result["status"] == "completed"
    assert result["edgar"]["inserted"] == 0
    assert result["edgar"]["skipped"] == 100


@pytest.mark.asyncio
async def test_bootstrap_runs_full_pipeline():
    """Worker should chain EDGAR → prices → universe when tables empty."""
    from margin_api.workers import bootstrap_pit_data

    job_mock = MagicMock()
    job_mock.id = 42

    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"scalar_one": 0},  # PIT count → empty
            {"all": [("AAPL",), ("MSFT",)]},  # distinct tickers query
        ]
    )

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    edgar_result = {"total": 100, "inserted": 95, "skipped": 3, "failed": 2}
    price_result = {"AAPL": 4000, "MSFT": 4000}
    universe_result = {"quarters_processed": 68, "tickers_tracked": 2, "delistings_detected": 0}

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_api.workers.run_edgar_backfill",
            new_callable=AsyncMock,
            return_value=edgar_result,
        ),
        patch(
            "margin_api.workers.backfill_prices_for_tickers",
            new_callable=AsyncMock,
            return_value=price_result,
        ),
        patch(
            "margin_api.workers.assemble_universe",
            new_callable=AsyncMock,
            return_value=universe_result,
        ),
        patch(
            "margin_api.workers.fill_last_known_prices",
            new_callable=AsyncMock,
            return_value=0,
        ),
    ):
        result = await bootstrap_pit_data({"redis": mock_redis})

    assert result["status"] == "completed"
    assert result["edgar"] == edgar_result
    assert result["prices_tickers"] == 2
    assert result["universe"] == universe_result

    # Should have created a JobRun
    job_runs = [o for o in added if isinstance(o, JobRun)]
    assert len(job_runs) == 1
    assert job_runs[0].job_type == "bootstrap_pit_data"


@pytest.mark.asyncio
async def test_bootstrap_handles_errors():
    """Worker should mark job as failed on exception."""
    from margin_api.workers import bootstrap_pit_data

    job_mock = MagicMock()
    job_mock.id = 42

    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"scalar_one": 0},  # PIT count → empty
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_api.workers.run_edgar_backfill",
            new_callable=AsyncMock,
            side_effect=RuntimeError("SEC EDGAR down"),
        ),
    ):
        result = await bootstrap_pit_data({})

    assert result["status"] == "error"
    assert "SEC EDGAR down" in result["message"]


# ---------------------------------------------------------------------------
# Admin PIT backfill endpoint tests
# ---------------------------------------------------------------------------


class TestPitBackfillEndpoint:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def test_pit_backfill_requires_admin_key(self):
        from margin_api.app import create_app

        get_settings.cache_clear()
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
            app = create_app()
            client = TestClient(app)
            response = client.post("/api/v1/admin/pit/backfill")
            assert response.status_code == 422

    def test_pit_backfill_enqueues_job(self):
        from margin_api.app import create_app

        get_settings.cache_clear()
        mock_job = MagicMock()
        mock_job.job_id = "bootstrap-123"

        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
        mock_pool.aclose = AsyncMock()

        with (
            patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}),
            patch("margin_api.routes.admin.create_pool", return_value=mock_pool),
        ):
            app = create_app()
            client = TestClient(app)
            response = client.post(
                "/api/v1/admin/pit/backfill",
                headers={"X-Admin-Key": "test-key"},
            )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "enqueued"
        assert data["job"] == "bootstrap_pit_data"
        assert data["job_id"] == "bootstrap-123"

        mock_pool.enqueue_job.assert_called_once()
        call_args = mock_pool.enqueue_job.call_args
        assert call_args[0][0] == "bootstrap_pit_data"
