"""Tests for the score pipeline worker functions.

Covers:
- full_score_v3: creates JobRun, calls run_scoring_v3, handles errors, chains to v4
- full_score_v4: creates JobRun, calls run_scoring_v4, handles errors, chains to stage_scores
- ingest_sweep_complete: finalizes IngestionRun, enqueues full_score_v3
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.db.models import JobRun

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
        job_mock = MagicMock()
        job_mock.id = 42
        return _make_execute_result(scalar_one=job_mock)

    session.execute = _execute

    def _add(obj):
        added_objects.append(obj)
        if isinstance(obj, JobRun):
            obj.id = 42

    session.add = _add

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=ctx)
    return factory, session, added_objects


# ---------------------------------------------------------------------------
# full_score_v3 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_score_v3_success_creates_job_run():
    """full_score_v3 should create a JobRun with job_type='score_v3'."""
    from margin_api.workers import full_score_v3

    factory, session, added = _mock_session_factory()

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.cli.run_scoring_v3", new_callable=AsyncMock),
    ):
        result = await full_score_v3({"redis": mock_redis}, pipeline_id="pipe-v3")

    assert result["status"] == "completed"
    assert result["pipeline_id"] == "pipe-v3"

    job_runs = [o for o in added if isinstance(o, JobRun)]
    assert len(job_runs) == 1
    assert job_runs[0].job_type == "score_v3"
    assert job_runs[0].status == "running"
    assert job_runs[0].triggered_by == "chained"


@pytest.mark.asyncio
async def test_full_score_v3_chains_to_v4():
    """full_score_v3 should enqueue full_score_v4 via redis after success."""
    from margin_api.workers import full_score_v3

    factory, session, added = _mock_session_factory()

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.cli.run_scoring_v3", new_callable=AsyncMock),
    ):
        result = await full_score_v3({"redis": mock_redis}, pipeline_id="pipe-chain")

    assert result["status"] == "completed"
    # Should have enqueued full_score_v4
    mock_redis.enqueue_job.assert_called_once()
    call_args = mock_redis.enqueue_job.call_args
    assert call_args[0][0] == "full_score_v4"


@pytest.mark.asyncio
async def test_full_score_v3_handles_exception_still_chains():
    """Even when v3 fails, full_score_v3 should still chain to full_score_v4."""
    from margin_api.workers import full_score_v3

    factory, session, added = _mock_session_factory()

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_api.cli.run_scoring_v3",
            new_callable=AsyncMock,
            side_effect=RuntimeError("v3 engine exploded"),
        ),
    ):
        result = await full_score_v3({"redis": mock_redis}, pipeline_id="pipe-v3-fail")

    assert result["status"] == "failed"
    assert "v3 engine exploded" in result["error"]

    # Should still chain to v4
    mock_redis.enqueue_job.assert_called_once()
    assert mock_redis.enqueue_job.call_args[0][0] == "full_score_v4"


@pytest.mark.asyncio
async def test_full_score_v3_no_redis_does_not_crash():
    """full_score_v3 with no redis in ctx should complete without chaining."""
    from margin_api.workers import full_score_v3

    factory, session, added = _mock_session_factory()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.cli.run_scoring_v3", new_callable=AsyncMock),
    ):
        result = await full_score_v3({}, pipeline_id="pipe-no-redis")

    # Should complete without error even without redis
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_full_score_v3_timeout_marks_failed():
    """TimeoutError from run_scoring_v3 should mark job as failed."""
    from margin_api.workers import full_score_v3

    factory, session, added = _mock_session_factory()

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_api.cli.run_scoring_v3",
            new_callable=AsyncMock,
            side_effect=TimeoutError(),
        ),
    ):
        result = await full_score_v3({"redis": mock_redis}, pipeline_id="pipe-timeout")

    assert result["status"] == "failed"
    assert "timed out" in result["error"]


# ---------------------------------------------------------------------------
# full_score_v4 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_score_v4_success_creates_job_run():
    """full_score_v4 should create a JobRun with job_type='score_v4'."""
    from margin_api.workers import full_score_v4

    factory, session, added = _mock_session_factory()

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    scored_at = datetime.now(UTC)

    snap = MagicMock()
    snap.tickers = ["AAPL", "MSFT"]

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.cli.run_scoring_v4", new_callable=AsyncMock, return_value=scored_at),
        patch("margin_api.workers.get_active_snapshot", return_value=snap),
        patch(
            "margin_engine.ml.reproducibility.capture_environment", return_value={"python": "3.13"}
        ),
        patch("margin_engine.ml.reproducibility.compute_data_hash", return_value="abc123"),
    ):
        result = await full_score_v4({"redis": mock_redis}, pipeline_id="pipe-v4")

    assert result["status"] == "completed"
    assert result["pipeline_id"] == "pipe-v4"

    job_runs = [o for o in added if isinstance(o, JobRun)]
    assert len(job_runs) == 1
    assert job_runs[0].job_type == "score_v4"


@pytest.mark.asyncio
async def test_full_score_v4_chains_to_stage_scores():
    """full_score_v4 should enqueue stage_scores and compute_rarity after success."""
    from margin_api.workers import full_score_v4

    factory, session, added = _mock_session_factory()

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    scored_at = datetime.now(UTC)
    snap = MagicMock()
    snap.tickers = ["AAPL"]

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.cli.run_scoring_v4", new_callable=AsyncMock, return_value=scored_at),
        patch("margin_api.workers.get_active_snapshot", return_value=snap),
        patch("margin_engine.ml.reproducibility.capture_environment", return_value={}),
        patch("margin_engine.ml.reproducibility.compute_data_hash", return_value="hash"),
    ):
        result = await full_score_v4({"redis": mock_redis}, pipeline_id="pipe-v4-chain")

    assert result["status"] == "completed"
    # Should have enqueued stage_scores and compute_rarity
    call_names = [call[0][0] for call in mock_redis.enqueue_job.call_args_list]
    assert "stage_scores" in call_names
    assert "compute_rarity" in call_names


@pytest.mark.asyncio
async def test_full_score_v4_handles_exception():
    """full_score_v4 should return status=failed when run_scoring_v4 raises."""
    from margin_api.workers import full_score_v4

    factory, session, added = _mock_session_factory()

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_api.cli.run_scoring_v4",
            new_callable=AsyncMock,
            side_effect=RuntimeError("v4 engine crashed"),
        ),
    ):
        result = await full_score_v4({"redis": mock_redis}, pipeline_id="pipe-v4-fail")

    assert result["status"] == "failed"
    assert "v4 engine crashed" in result["error"]


@pytest.mark.asyncio
async def test_full_score_v4_timeout_returns_failed():
    """TimeoutError from run_scoring_v4 should return status=failed with timeout message."""
    from margin_api.workers import full_score_v4

    factory, session, added = _mock_session_factory()

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_api.cli.run_scoring_v4",
            new_callable=AsyncMock,
            side_effect=TimeoutError(),
        ),
    ):
        result = await full_score_v4({"redis": mock_redis}, pipeline_id="pipe-v4-timeout")

    assert result["status"] == "failed"
    assert "timed out" in result["error"]


# ---------------------------------------------------------------------------
# ingest_sweep_complete tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_sweep_complete_enqueues_full_score_v3():
    """ingest_sweep_complete should enqueue full_score_v3 after finalizing the run."""
    from margin_api.workers import ingest_sweep_complete

    run_mock = MagicMock()
    run_mock.tickers_failed = 5
    run_mock.tickers_requested = 100
    run_mock.tickers_succeeded = 95
    run_mock.started_at = datetime.now(UTC)
    run_mock.tickers_partial = 2
    run_mock.status = "running"

    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"scalar_one": run_mock},  # IngestionRun fetch
            {"scalar_one": 20},  # circuit breaker threshold query
            {"all": [("AAPL",), ("MSFT",)]},  # succeeded tickers
        ]
    )

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_api.workers.get_threshold",
            new_callable=AsyncMock,
            return_value=20.0,
        ),
        patch(
            "margin_api.workers.check_ingestion_failure_rate",
            return_value=MagicMock(triggered=False, detail="ok"),
        ),
        patch(
            "margin_api.services.consistency.validate_universe_consistency",
            new_callable=AsyncMock,
        ),
    ):
        result = await ingest_sweep_complete(
            {"redis": mock_redis}, run_id="123", pipeline_id="pipe-sweep"
        )

    assert result["status"] == "completed"
    assert result["pipeline_id"] == "pipe-sweep"

    # Should have enqueued full_score_v3
    call_names = [call[0][0] for call in mock_redis.enqueue_job.call_args_list]
    assert "full_score_v3" in call_names


@pytest.mark.asyncio
async def test_ingest_sweep_complete_high_failure_rate_marks_failed():
    """When >50% tickers fail, run status should be 'failed'."""
    from margin_api.workers import ingest_sweep_complete

    run_mock = MagicMock()
    run_mock.tickers_failed = 60
    run_mock.tickers_requested = 100
    run_mock.tickers_succeeded = 40
    run_mock.started_at = datetime.now(UTC)
    run_mock.tickers_partial = 0
    run_mock.status = "running"

    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"scalar_one": run_mock},  # IngestionRun fetch
            {"scalar_one": 20},  # threshold
            {"all": []},  # no succeeded tickers
        ]
    )

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_api.workers.get_threshold",
            new_callable=AsyncMock,
            return_value=20.0,
        ),
        patch(
            "margin_api.workers.check_ingestion_failure_rate",
            return_value=MagicMock(triggered=False, detail="ok"),
        ),
    ):
        await ingest_sweep_complete({"redis": mock_redis}, run_id="456", pipeline_id="pipe-hi-fail")

    # Run mock should have been mutated to "failed"
    assert run_mock.status == "failed"
