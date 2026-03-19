"""Tests for ingest pipeline workers.

Covers:
- orchestrate_ingest: no snapshot → error; with snapshot → dispatches batches
- ingest_sweep: no missing tickers → enqueues sweep_complete; missing → enqueues batch
- ingest_batch: simplified integration — processes tickers, records status
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.db.models import IngestionRun, JobRun

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_execute_result(**kwargs):
    result = MagicMock()
    result.scalar_one.return_value = kwargs.get("scalar_one", 0)
    result.scalar_one_or_none.return_value = kwargs.get("scalar_one_or_none", None)
    result.all.return_value = kwargs.get("all", [])
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = kwargs.get("scalars_all", [])
    result.scalars.return_value = scalars_mock
    return result


def _mock_session_factory(execute_side_effects: list | None = None):
    effects = list(execute_side_effects or [])
    call_idx = {"n": 0}
    added_objects: list = []

    session = MagicMock()
    session.commit = AsyncMock()
    session.add_all = MagicMock()

    async def _execute(stmt):
        idx = call_idx["n"]
        call_idx["n"] += 1
        if idx < len(effects):
            return _make_execute_result(**effects[idx])
        mock = MagicMock()
        mock.id = 42
        return _make_execute_result(scalar_one=mock)

    session.execute = _execute

    def _add(obj):
        added_objects.append(obj)
        if isinstance(obj, (IngestionRun, JobRun)):
            obj.id = 42

    session.add = _add

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=ctx)
    return factory, session, added_objects


# ---------------------------------------------------------------------------
# orchestrate_ingest tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrate_ingest_no_snapshot_returns_error():
    """When no active universe snapshot exists, returns status='error'."""
    from margin_api.workers import orchestrate_ingest

    factory, session, added = _mock_session_factory()

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.workers.get_active_snapshot", return_value=None),
        patch("margin_api.cli._load_foreign_skips", return_value=set()),
    ):
        result = await orchestrate_ingest({"redis": mock_redis})

    assert result["status"] == "error"
    assert "No active universe snapshot" in result["message"]


@pytest.mark.asyncio
async def test_orchestrate_ingest_no_redis_returns_error():
    """When no redis in ctx, returns status='error'."""
    from margin_api.workers import orchestrate_ingest

    snapshot = MagicMock()
    snapshot.id = 1
    snapshot.version = 1
    snapshot.tickers = ["AAPL", "MSFT", "GOOG"]

    factory, session, added = _mock_session_factory()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.workers.get_active_snapshot", return_value=snapshot),
        patch("margin_api.cli._load_foreign_skips", return_value=set()),
    ):
        result = await orchestrate_ingest({})  # No redis

    assert result["status"] == "error"
    assert "No redis" in result["message"]


@pytest.mark.asyncio
async def test_orchestrate_ingest_dispatches_batches():
    """With snapshot + redis, dispatches batches and returns dispatched status."""
    from margin_api.workers import orchestrate_ingest

    snapshot = MagicMock()
    snapshot.id = 1
    snapshot.version = 2
    snapshot.tickers = [f"TICK{i}" for i in range(10)]  # 10 tickers

    factory, session, added = _mock_session_factory()

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.workers.get_active_snapshot", return_value=snapshot),
        patch("margin_api.cli._load_foreign_skips", return_value=set()),
        patch("margin_api.workers.get_settings") as mock_settings,
    ):
        settings_obj = MagicMock()
        settings_obj.ingest_batch_size = 5  # 2 batches for 10 tickers
        mock_settings.return_value = settings_obj

        result = await orchestrate_ingest({"redis": mock_redis})

    assert result["status"] == "dispatched"
    assert result["total_tickers"] == 10
    assert result["total_batches"] == 2

    # Should have enqueued 2 batch jobs
    batch_calls = [
        call for call in mock_redis.enqueue_job.call_args_list if call[0][0] == "ingest_batch"
    ]
    assert len(batch_calls) == 2

    # IngestionRun should have been created
    ingest_runs = [o for o in added if isinstance(o, IngestionRun)]
    assert len(ingest_runs) == 1
    assert ingest_runs[0].run_type == "full"
    assert ingest_runs[0].tickers_requested == 10


@pytest.mark.asyncio
async def test_orchestrate_ingest_filters_foreign_tickers():
    """Known foreign tickers should be excluded from batches."""
    from margin_api.workers import orchestrate_ingest

    snapshot = MagicMock()
    snapshot.id = 1
    snapshot.version = 1
    snapshot.tickers = ["AAPL", "BARC.L", "MSFT", "VOD.L"]  # 2 foreign

    factory, session, added = _mock_session_factory()

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.workers.get_active_snapshot", return_value=snapshot),
        patch("margin_api.cli._load_foreign_skips", return_value={"BARC.L", "VOD.L"}),
        patch("margin_api.workers.get_settings") as mock_settings,
    ):
        settings_obj = MagicMock()
        settings_obj.ingest_batch_size = 10
        mock_settings.return_value = settings_obj

        result = await orchestrate_ingest({"redis": mock_redis})

    # Only 2 tickers after filtering
    assert result["total_tickers"] == 2
    assert result["status"] == "dispatched"


# ---------------------------------------------------------------------------
# ingest_sweep tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_sweep_no_redis_returns_error():
    """ingest_sweep without redis in ctx returns error."""
    from margin_api.workers import ingest_sweep

    run_mock = MagicMock()
    run_mock.snapshot_id = 1

    snap_mock = MagicMock()
    snap_mock.tickers = ["AAPL", "MSFT"]

    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"scalar_one": run_mock},  # IngestionRun
            {"scalar_one": snap_mock},  # UniverseSnapshot
            {"all": [("AAPL",)]},  # succeeded tickers
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
    ):
        result = await ingest_sweep({}, run_id="1", pipeline_id="pipe")

    assert result["status"] == "error"
    assert "No redis" in result["message"]


@pytest.mark.asyncio
async def test_ingest_sweep_no_missing_enqueues_complete():
    """When all tickers succeeded, enqueues ingest_sweep_complete."""
    from margin_api.workers import ingest_sweep

    run_mock = MagicMock()
    run_mock.snapshot_id = 1

    snap_mock = MagicMock()
    snap_mock.tickers = ["AAPL", "MSFT"]

    # Both tickers succeeded
    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"scalar_one": run_mock},  # IngestionRun
            {"scalar_one": snap_mock},  # UniverseSnapshot
            {"all": [("AAPL",), ("MSFT",)]},  # succeeded tickers = all
        ]
    )

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
    ):
        result = await ingest_sweep({"redis": mock_redis}, run_id="1", pipeline_id="pipe-complete")

    assert result["status"] == "all_complete"
    assert result["missing_count"] == 0

    # Should enqueue sweep_complete, not sweep batch
    mock_redis.enqueue_job.assert_called_once()
    assert mock_redis.enqueue_job.call_args[0][0] == "ingest_sweep_complete"


@pytest.mark.asyncio
async def test_ingest_sweep_missing_tickers_enqueues_batch():
    """When some tickers are missing, enqueues an ingest_batch with is_sweep=True."""
    from margin_api.workers import ingest_sweep

    run_mock = MagicMock()
    run_mock.snapshot_id = 1

    snap_mock = MagicMock()
    snap_mock.tickers = ["AAPL", "MSFT", "GOOG"]

    # Only AAPL succeeded — MSFT and GOOG need sweep
    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"scalar_one": run_mock},  # IngestionRun
            {"scalar_one": snap_mock},  # UniverseSnapshot
            {"all": [("AAPL",)]},  # only AAPL succeeded
        ]
    )

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
    ):
        result = await ingest_sweep({"redis": mock_redis}, run_id="2", pipeline_id="pipe-sweep")

    assert result["status"] == "sweep_dispatched"
    assert result["missing_count"] == 2

    # Should enqueue ingest_batch with is_sweep=True
    mock_redis.enqueue_job.assert_called_once()
    call = mock_redis.enqueue_job.call_args
    assert call[0][0] == "ingest_batch"
    # Positional args: ("ingest_batch", run_id, pipeline_id, missing_tickers, 0, True)
    # is_sweep=True is the 6th positional arg (index 5)
    assert call[0][5] is True
