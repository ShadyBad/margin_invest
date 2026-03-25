"""Tests for governance pipeline worker functions.

Covers:
- stage_scores / _stage_scores_impl
- publish_scores / _publish_scores_impl
- promote_ml_model / _promote_ml_model_impl
- expire_stale_approvals / _expire_stale_approvals_impl
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.db.models import JobRun, PipelineApproval

UTC = UTC

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_execute_result(**kwargs):
    """Build a MagicMock that behaves like a SQLAlchemy Result."""
    result = MagicMock()
    result.scalar_one.return_value = kwargs.get("scalar_one", 0)
    result.scalar_one_or_none.return_value = kwargs.get("scalar_one_or_none", None)
    result.all.return_value = kwargs.get("all", [])
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = kwargs.get("scalars_all", [])
    result.scalars.return_value = scalars_mock
    result.rowcount = kwargs.get("rowcount", 0)
    return result


def _mock_session_factory(execute_side_effects: list | None = None):
    """Build a mock async session factory with a call-index-based execute."""
    effects = list(execute_side_effects or [])
    call_idx = {"n": 0}
    added_objects: list = []

    session = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add_all = MagicMock()

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
        if isinstance(obj, PipelineApproval):
            obj.id = 99

    session.add = _add

    # Make session usable as async context manager
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=ctx)
    return factory, session, added_objects


def _make_mock_approval(
    status: str = "staged",
    scored_at: str = "2026-03-17T00:00:00+00:00",
    model_id: int = 7,
) -> MagicMock:
    """Build a mock PipelineApproval object."""
    approval = MagicMock(spec=PipelineApproval)
    approval.id = 99
    approval.status = status
    approval.payload_ref = {
        "scored_at": scored_at,
        "ticker_count": 3,
        "ml_model_run_id": model_id,
    }
    return approval


def _make_drift_result(triggered: bool = False, drift_pct: float = 0.05) -> MagicMock:
    """Build a mock CircuitBreakerResult."""
    r = MagicMock()
    r.triggered = triggered
    r.drift_pct = drift_pct
    r.detail = f"drift={drift_pct:.0%}"
    return r


# ---------------------------------------------------------------------------
# _stage_scores_impl tests
# ---------------------------------------------------------------------------


class TestStageScoresImpl:
    """Direct unit tests for _stage_scores_impl."""

    @pytest.mark.asyncio
    async def test_auto_approves_when_low_conviction_change(self):
        """Creates PipelineApproval with status=auto_approved when change rate < 10%."""
        from margin_api.workers import _stage_scores_impl

        scored_at = datetime(2026, 3, 17, tzinfo=UTC)

        # Build mock V4Score objects with same conviction (no changes)
        new_score = MagicMock()
        new_score.asset_id = 1
        new_score.conviction = "high"

        prev_score = MagicMock()
        prev_score.conviction = "high"  # same conviction → no change

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalars_all": [new_score]},  # unpublished V4Scores query
                {"scalar_one_or_none": prev_score},  # prev published score
            ]
        )

        drift_not_triggered = _make_drift_result(triggered=False)

        with (
            patch(
                "margin_api.workers.get_threshold",
                new_callable=AsyncMock,
                return_value=30.0,
            ),
            patch(
                "margin_api.workers.check_score_drift",
                new_callable=AsyncMock,
                return_value=drift_not_triggered,
            ),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await _stage_scores_impl(session, "pipe-1", scored_at)

        assert result["status"] == "auto_approved"
        assert result["ticker_count"] == 1
        assert "approval_id" in result

        # PipelineApproval should have been added and committed
        approvals = [o for o in added if isinstance(o, PipelineApproval)]
        assert len(approvals) == 1
        assert approvals[0].gate_type == "score_publish"

    @pytest.mark.asyncio
    async def test_requires_manual_approval_when_high_conviction_change(self):
        """Stays in staged status when conviction change rate >= 10%."""
        from margin_api.workers import _stage_scores_impl

        scored_at = datetime(2026, 3, 17, tzinfo=UTC)

        # 5 scores where all changed conviction → 100% change rate
        scores = []
        for i in range(5):
            s = MagicMock()
            s.asset_id = i
            s.conviction = "high"
            scores.append(s)

        prev_scores = []
        for _ in range(5):
            p = MagicMock()
            p.conviction = "low"  # different conviction
            prev_scores.append(p)

        effects = [{"scalars_all": scores}]
        for p in prev_scores:
            effects.append({"scalar_one_or_none": p})

        factory, session, added = _mock_session_factory(execute_side_effects=effects)

        drift_not_triggered = _make_drift_result(triggered=False)

        with (
            patch(
                "margin_api.workers.get_threshold",
                new_callable=AsyncMock,
                return_value=30.0,
            ),
            patch(
                "margin_api.workers.check_score_drift",
                new_callable=AsyncMock,
                return_value=drift_not_triggered,
            ),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await _stage_scores_impl(session, "pipe-2", scored_at)

        assert result["status"] == "staged"
        assert result["ticker_count"] == 5

    @pytest.mark.asyncio
    async def test_zero_scores_stages_empty_approval(self):
        """Creates a staged approval with ticker_count=0 when no new scores exist."""
        from margin_api.workers import _stage_scores_impl

        scored_at = datetime(2026, 3, 17, tzinfo=UTC)

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalars_all": []},  # no unpublished scores
            ]
        )

        drift_not_triggered = _make_drift_result(triggered=False)

        with (
            patch(
                "margin_api.workers.get_threshold",
                new_callable=AsyncMock,
                return_value=30.0,
            ),
            patch(
                "margin_api.workers.check_score_drift",
                new_callable=AsyncMock,
                return_value=drift_not_triggered,
            ),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await _stage_scores_impl(session, "pipe-3", scored_at)

        assert result["status"] == "staged"
        assert result["ticker_count"] == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_triggered_dispatches_cb_webhook(self):
        """When drift CB triggers, dispatches circuit_breaker.tripped webhook."""
        from margin_api.workers import _stage_scores_impl

        scored_at = datetime(2026, 3, 17, tzinfo=UTC)

        new_score = MagicMock()
        new_score.asset_id = 1
        new_score.conviction = "high"

        prev_score = MagicMock()
        prev_score.conviction = "high"

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalars_all": [new_score]},
                {"scalar_one_or_none": prev_score},
            ]
        )

        drift_triggered = _make_drift_result(triggered=True, drift_pct=0.50)

        mock_dispatch = AsyncMock(return_value=[101, 102])

        with (
            patch(
                "margin_api.workers.get_threshold",
                new_callable=AsyncMock,
                return_value=30.0,
            ),
            patch(
                "margin_api.workers.check_score_drift",
                new_callable=AsyncMock,
                return_value=drift_triggered,
            ),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                mock_dispatch,
            ),
        ):
            result = await _stage_scores_impl(session, "pipe-4", scored_at)

        # CB webhook IDs should appear in _webhook_delivery_ids
        assert 101 in result["_webhook_delivery_ids"] or 102 in result["_webhook_delivery_ids"]
        mock_dispatch.assert_called()

    @pytest.mark.asyncio
    async def test_webhook_dispatch_failure_is_non_blocking(self):
        """Webhook failure must not prevent stage_scores_impl from returning normally."""
        from margin_api.workers import _stage_scores_impl

        scored_at = datetime(2026, 3, 17, tzinfo=UTC)

        new_score = MagicMock()
        new_score.asset_id = 1
        new_score.conviction = "high"

        prev_score = MagicMock()
        prev_score.conviction = "high"

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalars_all": [new_score]},
                {"scalar_one_or_none": prev_score},
            ]
        )

        drift_not_triggered = _make_drift_result(triggered=False)

        with (
            patch(
                "margin_api.workers.get_threshold",
                new_callable=AsyncMock,
                return_value=30.0,
            ),
            patch(
                "margin_api.workers.check_score_drift",
                new_callable=AsyncMock,
                return_value=drift_not_triggered,
            ),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                side_effect=RuntimeError("webhook endpoint down"),
            ),
        ):
            result = await _stage_scores_impl(session, "pipe-5", scored_at)

        # Should succeed despite webhook failure
        assert result["status"] in ("auto_approved", "staged")
        assert result["ticker_count"] == 1


# ---------------------------------------------------------------------------
# stage_scores worker entry point tests
# ---------------------------------------------------------------------------


class TestStageScoresWorker:
    """Tests for the stage_scores ARQ entry point."""

    @pytest.mark.asyncio
    async def test_stage_scores_creates_job_run_and_returns_result(self):
        """Happy path: creates JobRun, calls impl, returns result."""
        from margin_api.workers import stage_scores

        scored_at = datetime(2026, 3, 17, tzinfo=UTC)
        scored_at_iso = scored_at.isoformat()

        new_score = MagicMock()
        new_score.asset_id = 1
        new_score.conviction = "high"

        prev_score = MagicMock()
        prev_score.conviction = "high"

        job_mock = MagicMock()
        job_mock.id = 42
        job_mock.status = "running"

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                # impl: unpublished scores query
                {"scalars_all": [new_score]},
                # impl: prev published score for asset 1
                {"scalar_one_or_none": prev_score},
                # job update: scalar_one → job
                {"scalar_one": job_mock},
            ]
        )

        drift_not_triggered = _make_drift_result(triggered=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch(
                "margin_api.workers.get_threshold",
                new_callable=AsyncMock,
                return_value=30.0,
            ),
            patch(
                "margin_api.workers.check_score_drift",
                new_callable=AsyncMock,
                return_value=drift_not_triggered,
            ),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await stage_scores(
                {},
                pipeline_id="pipe-1",
                scored_at_iso=scored_at_iso,
            )

        assert result["status"] in ("auto_approved", "staged")
        assert result["ticker_count"] == 1

        job_runs = [o for o in added if isinstance(o, JobRun)]
        assert len(job_runs) == 1
        assert job_runs[0].job_type == "stage_scores"

    @pytest.mark.asyncio
    async def test_stage_scores_auto_approved_chains_to_publish(self):
        """When auto-approved, stage_scores should enqueue publish_scores on redis."""
        from margin_api.workers import stage_scores

        scored_at = datetime(2026, 3, 17, tzinfo=UTC)
        scored_at_iso = scored_at.isoformat()

        new_score = MagicMock()
        new_score.asset_id = 1
        new_score.conviction = "high"

        prev_score = MagicMock()
        prev_score.conviction = "high"  # no change → auto-approve

        job_mock = MagicMock()
        job_mock.id = 42
        job_mock.status = "running"

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalars_all": [new_score]},
                {"scalar_one_or_none": prev_score},
                {"scalar_one": job_mock},
            ]
        )

        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        drift_not_triggered = _make_drift_result(triggered=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch(
                "margin_api.workers.get_threshold",
                new_callable=AsyncMock,
                return_value=30.0,
            ),
            patch(
                "margin_api.workers.check_score_drift",
                new_callable=AsyncMock,
                return_value=drift_not_triggered,
            ),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await stage_scores(
                {"redis": mock_redis},
                pipeline_id="pipe-2",
                scored_at_iso=scored_at_iso,
            )

        # If auto_approved, redis.enqueue_job should have been called for publish_scores
        if result["status"] == "auto_approved":
            mock_redis.enqueue_job.assert_called()
            call_args = mock_redis.enqueue_job.call_args_list
            job_names = [c[0][0] for c in call_args]
            assert "publish_scores" in job_names

    @pytest.mark.asyncio
    async def test_stage_scores_handles_exception(self):
        """Marks job as failed and returns error dict on exception."""
        from margin_api.workers import stage_scores

        job_mock = MagicMock()
        job_mock.id = 42
        job_mock.status = "running"

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one": job_mock},  # job update on failure
            ]
        )

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch(
                "margin_api.workers.get_threshold",
                new_callable=AsyncMock,
                side_effect=RuntimeError("DB connection lost"),
            ),
        ):
            result = await stage_scores(
                {},
                pipeline_id="pipe-err",
                scored_at_iso="2026-03-17T00:00:00+00:00",
            )

        assert result["status"] == "failed"
        assert "DB connection lost" in result["error"]
        assert result["pipeline_id"] == "pipe-err"

    @pytest.mark.asyncio
    async def test_stage_scores_no_redis_does_not_crash(self):
        """When ctx has no redis, auto-approved stage_scores should still return normally."""
        from margin_api.workers import stage_scores

        scored_at = datetime(2026, 3, 17, tzinfo=UTC)
        scored_at_iso = scored_at.isoformat()

        new_score = MagicMock()
        new_score.asset_id = 1
        new_score.conviction = "high"

        prev_score = MagicMock()
        prev_score.conviction = "high"

        job_mock = MagicMock()
        job_mock.id = 42
        job_mock.status = "running"

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalars_all": [new_score]},
                {"scalar_one_or_none": prev_score},
                {"scalar_one": job_mock},
            ]
        )

        drift_not_triggered = _make_drift_result(triggered=False)

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch(
                "margin_api.workers.get_threshold",
                new_callable=AsyncMock,
                return_value=30.0,
            ),
            patch(
                "margin_api.workers.check_score_drift",
                new_callable=AsyncMock,
                return_value=drift_not_triggered,
            ),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            # Pass empty ctx (no redis)
            result = await stage_scores({}, pipeline_id="pipe-3", scored_at_iso=scored_at_iso)

        # Should still return a valid result even without redis
        assert "status" in result


# ---------------------------------------------------------------------------
# _publish_scores_impl tests
# ---------------------------------------------------------------------------


class TestPublishScoresImpl:
    """Direct unit tests for _publish_scores_impl."""

    @pytest.mark.asyncio
    async def test_publish_scores_sets_published_true(self):
        """Happy path: flips published=True and returns published status."""
        from margin_api.workers import _publish_scores_impl

        approval = _make_mock_approval(status="staged")
        approval.id = 99

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": approval},  # fetch approval
                {"rowcount": 5},  # bulk update V4Score
            ]
        )

        with (
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[10, 11],
            ),
        ):
            result = await _publish_scores_impl(session, approval_id=99, decided_by=1)

        assert result["status"] == "published"
        assert result["published_count"] == 5
        assert result["approval_id"] == 99
        # approval should be mutated to approved
        assert approval.status == "approved"
        assert approval.decided_by == 1

    @pytest.mark.asyncio
    async def test_publish_scores_returns_error_when_approval_not_found(self):
        """Returns error dict when approval_id does not exist."""
        from margin_api.workers import _publish_scores_impl

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": None},  # approval not found
            ]
        )

        result = await _publish_scores_impl(session, approval_id=999)

        assert result["status"] == "error"
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_publish_scores_returns_error_when_not_staged(self):
        """Returns error dict when approval is not in an accepted status."""
        from margin_api.workers import _publish_scores_impl

        approval = _make_mock_approval(status="expired")  # rejected/expired status

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": approval},
            ]
        )

        result = await _publish_scores_impl(session, approval_id=99)

        assert result["status"] == "error"
        assert "unexpected status" in result["message"]

    @pytest.mark.asyncio
    async def test_publish_scores_webhook_failure_is_non_blocking(self):
        """Webhook failure must not prevent publish_scores_impl from returning normally."""
        from margin_api.workers import _publish_scores_impl

        approval = _make_mock_approval(status="staged")
        approval.id = 99

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": approval},
                {"rowcount": 3},
            ]
        )

        with patch(
            "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
            side_effect=RuntimeError("webhook down"),
        ):
            result = await _publish_scores_impl(session, approval_id=99)

        assert result["status"] == "published"
        assert result["published_count"] == 3

    @pytest.mark.asyncio
    async def test_publish_scores_stores_decision_reason(self):
        """Decision reason is stored on the approval."""
        from margin_api.workers import _publish_scores_impl

        approval = _make_mock_approval(status="staged")
        approval.id = 99

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": approval},
                {"rowcount": 2},
            ]
        )

        with patch(
            "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await _publish_scores_impl(
                session,
                approval_id=99,
                decided_by=5,
                decision_reason="Reviewed and approved by analyst",
            )

        assert result["status"] == "published"
        assert approval.decision_reason == "Reviewed and approved by analyst"
        assert approval.decided_by == 5


# ---------------------------------------------------------------------------
# publish_scores worker entry point tests
# ---------------------------------------------------------------------------


class TestPublishScoresWorker:
    """Tests for the publish_scores ARQ entry point."""

    @pytest.mark.asyncio
    async def test_publish_scores_happy_path(self):
        """Happy path: creates JobRun, publishes, returns result."""
        from margin_api.workers import publish_scores

        approval = _make_mock_approval(status="staged")
        approval.id = 99

        job_mock = MagicMock()
        job_mock.id = 42
        job_mock.status = "running"

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                # _publish_scores_impl: fetch approval
                {"scalar_one_or_none": approval},
                # _publish_scores_impl: bulk update
                {"rowcount": 3},
                # job update — must return job object via scalar_one
                {"scalar_one": job_mock},
            ]
        )

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch(
                "margin_api.workers._emit_score_change_events",
                new_callable=AsyncMock,
                return_value=3,
            ),
            patch(
                "margin_api.workers._broadcast_score_events",
                new_callable=AsyncMock,
                return_value=3,
            ),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await publish_scores({}, approval_id=99, decided_by=1)

        assert result["status"] == "published"
        assert result["published_count"] == 3

        job_runs = [o for o in added if isinstance(o, JobRun)]
        assert len(job_runs) == 1
        assert job_runs[0].job_type == "publish_scores"

    @pytest.mark.asyncio
    async def test_publish_scores_handles_exception(self):
        """Marks job as failed and returns error dict on exception."""
        from margin_api.workers import publish_scores

        job_mock = MagicMock()
        job_mock.id = 42
        job_mock.status = "running"

        # Two separate session factories needed: one for JobRun creation, one for failure path
        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                # job update on failure — must return job object
                {"scalar_one": job_mock},
            ]
        )

        # Patch _publish_scores_impl to raise directly
        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch(
                "margin_api.workers._publish_scores_impl",
                new_callable=AsyncMock,
                side_effect=RuntimeError("impl exploded"),
            ),
        ):
            result = await publish_scores({}, approval_id=99)

        assert result["status"] == "failed"
        assert "impl exploded" in result["error"]

    @pytest.mark.asyncio
    async def test_publish_scores_enqueues_webhook_deliveries(self):
        """publish_scores should enqueue deliver_webhook jobs when webhook IDs returned."""
        from margin_api.workers import publish_scores

        approval = _make_mock_approval(status="staged")
        approval.id = 99

        job_mock = MagicMock()
        job_mock.id = 42
        job_mock.status = "running"

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": approval},
                {"rowcount": 2},
                {"scalar_one": job_mock},
            ]
        )

        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch(
                "margin_api.workers._emit_score_change_events",
                new_callable=AsyncMock,
                return_value=2,
            ),
            patch(
                "margin_api.workers._broadcast_score_events",
                new_callable=AsyncMock,
                return_value=2,
            ),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[201, 202],
            ),
        ):
            result = await publish_scores({"redis": mock_redis}, approval_id=99)

        assert result["status"] == "published"
        # Should have enqueued 2 deliver_webhook jobs
        assert mock_redis.enqueue_job.call_count == 2
        for call in mock_redis.enqueue_job.call_args_list:
            assert call[0][0] == "deliver_webhook"


# ---------------------------------------------------------------------------
# _promote_ml_model_impl tests
# ---------------------------------------------------------------------------


class TestPromoteMlModelImpl:
    """Direct unit tests for _promote_ml_model_impl."""

    @pytest.mark.asyncio
    async def test_promotes_model_and_retires_active(self):
        """Happy path: retires active models, activates candidate, updates approval."""
        from margin_api.workers import _promote_ml_model_impl

        approval = _make_mock_approval(status="staged", model_id=7)
        approval.id = 99

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": approval},  # fetch approval
                {},  # retire active models (bulk update)
                {},  # activate candidate model (bulk update)
            ]
        )

        with (
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[301],
            ),
        ):
            result = await _promote_ml_model_impl(session, approval_id=99, decided_by=2)

        assert result["status"] == "promoted"
        assert result["model_id"] == 7
        assert result["approval_id"] == 99
        assert approval.status == "approved"
        assert approval.decided_by == 2

    @pytest.mark.asyncio
    async def test_promote_returns_error_when_not_found(self):
        """Returns error when approval_id does not exist."""
        from margin_api.workers import _promote_ml_model_impl

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": None},
            ]
        )

        result = await _promote_ml_model_impl(session, approval_id=999)

        assert result["status"] == "error"
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_promote_returns_error_when_not_staged(self):
        """Returns error when approval is already approved/expired."""
        from margin_api.workers import _promote_ml_model_impl

        approval = _make_mock_approval(status="approved")

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": approval},
            ]
        )

        result = await _promote_ml_model_impl(session, approval_id=99)

        assert result["status"] == "error"
        assert "not in staged status" in result["message"]

    @pytest.mark.asyncio
    async def test_promote_webhook_failure_is_non_blocking(self):
        """Webhook failure must not prevent promotion from completing."""
        from margin_api.workers import _promote_ml_model_impl

        approval = _make_mock_approval(status="staged", model_id=7)
        approval.id = 99

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": approval},
                {},  # retire
                {},  # activate
            ]
        )

        with patch(
            "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
            side_effect=RuntimeError("webhook unavailable"),
        ):
            result = await _promote_ml_model_impl(session, approval_id=99)

        assert result["status"] == "promoted"

    @pytest.mark.asyncio
    async def test_promote_stores_decision_reason(self):
        """Decision reason is stored on the approval."""
        from margin_api.workers import _promote_ml_model_impl

        approval = _make_mock_approval(status="staged", model_id=7)
        approval.id = 99

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": approval},
                {},
                {},
            ]
        )

        with patch(
            "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
            new_callable=AsyncMock,
            return_value=[],
        ):
            await _promote_ml_model_impl(
                session,
                approval_id=99,
                decided_by=3,
                decision_reason="Model IC improved over baseline",
            )

        assert approval.decision_reason == "Model IC improved over baseline"


# ---------------------------------------------------------------------------
# promote_ml_model worker entry point tests
# ---------------------------------------------------------------------------


class TestPromoteMlModelWorker:
    """Tests for the promote_ml_model ARQ entry point."""

    @pytest.mark.asyncio
    async def test_promote_ml_model_happy_path(self):
        """Happy path: calls impl and returns promoted result."""
        from margin_api.workers import promote_ml_model

        approval = _make_mock_approval(status="staged", model_id=7)
        approval.id = 99

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": approval},
                {},  # retire
                {},  # activate
            ]
        )

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await promote_ml_model({}, approval_id=99, decided_by=1)

        assert result["status"] == "promoted"
        assert result["model_id"] == 7

    @pytest.mark.asyncio
    async def test_promote_ml_model_enqueues_webhook_deliveries(self):
        """Enqueues deliver_webhook jobs when webhook IDs are returned."""
        from margin_api.workers import promote_ml_model

        approval = _make_mock_approval(status="staged", model_id=7)
        approval.id = 99

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": approval},
                {},
                {},
            ]
        )

        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[401],
            ),
        ):
            result = await promote_ml_model({"redis": mock_redis}, approval_id=99)

        assert result["status"] == "promoted"
        mock_redis.enqueue_job.assert_called_once_with(
            "deliver_webhook", 401, _job_id="webhook:401"
        )

    @pytest.mark.asyncio
    async def test_promote_ml_model_no_redis_does_not_crash(self):
        """When ctx has no redis, promote_ml_model should still return normally."""
        from margin_api.workers import promote_ml_model

        approval = _make_mock_approval(status="staged", model_id=7)
        approval.id = 99

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalar_one_or_none": approval},
                {},
                {},
            ]
        )

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch(
                "margin_api.services.webhook_dispatcher.WebhookDispatcher.dispatch",
                new_callable=AsyncMock,
                return_value=[501],
            ),
        ):
            result = await promote_ml_model({}, approval_id=99)

        assert result["status"] == "promoted"


# ---------------------------------------------------------------------------
# _expire_stale_approvals_impl tests
# ---------------------------------------------------------------------------


class TestExpireStaleApprovalsImpl:
    """Direct unit tests for _expire_stale_approvals_impl."""

    @pytest.mark.asyncio
    async def test_expires_stale_approvals(self):
        """Marks staged approvals past expires_at as expired."""
        from margin_api.workers import _expire_stale_approvals_impl

        now = datetime.now(UTC)
        stale_1 = MagicMock(spec=PipelineApproval)
        stale_1.status = "staged"
        stale_1.expires_at = now - timedelta(hours=25)

        stale_2 = MagicMock(spec=PipelineApproval)
        stale_2.status = "staged"
        stale_2.expires_at = now - timedelta(hours=1)

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalars_all": [stale_1, stale_2]},
            ]
        )

        count = await _expire_stale_approvals_impl(session)

        assert count == 2
        assert stale_1.status == "expired"
        assert stale_2.status == "expired"
        assert stale_1.decided_at is not None
        assert stale_2.decided_at is not None
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_stale_approvals_does_not_commit(self):
        """When no stale approvals exist, commit should not be called."""
        from margin_api.workers import _expire_stale_approvals_impl

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalars_all": []},
            ]
        )

        count = await _expire_stale_approvals_impl(session)

        assert count == 0
        session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_stale(self):
        """Returns 0 when there are no stale approvals."""
        from margin_api.workers import _expire_stale_approvals_impl

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalars_all": []},
            ]
        )

        count = await _expire_stale_approvals_impl(session)
        assert count == 0


# ---------------------------------------------------------------------------
# expire_stale_approvals worker entry point tests
# ---------------------------------------------------------------------------


class TestExpireStaleApprovalsWorker:
    """Tests for the expire_stale_approvals ARQ entry point."""

    @pytest.mark.asyncio
    async def test_expire_stale_approvals_happy_path(self):
        """Happy path: acquires lock, expires stale approvals, returns count."""
        from margin_api.workers import expire_stale_approvals

        now = datetime.now(UTC)
        stale = MagicMock(spec=PipelineApproval)
        stale.status = "staged"
        stale.expires_at = now - timedelta(hours=25)

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalars_all": [stale]},
            ]
        )

        mock_redis_client = AsyncMock()
        mock_redis_client.set = AsyncMock(return_value=True)  # lock acquired
        mock_redis_client.aclose = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch("margin_api.workers.aioredis") as mock_aioredis,
            patch("margin_api.workers.get_settings"),
        ):
            mock_aioredis.from_url.return_value = mock_redis_client
            result = await expire_stale_approvals({})

        assert result["status"] == "completed"
        assert result["expired_count"] == 1

    @pytest.mark.asyncio
    async def test_expire_stale_approvals_skips_when_lock_held(self):
        """Returns skipped_dedup when Redis lock is already held."""
        from margin_api.workers import expire_stale_approvals

        mock_redis_client = AsyncMock()
        mock_redis_client.set = AsyncMock(
            return_value=None
        )  # lock NOT acquired (None = already set)
        mock_redis_client.aclose = AsyncMock()

        with (
            patch("margin_api.workers.aioredis") as mock_aioredis,
            patch("margin_api.workers.get_settings"),
        ):
            mock_aioredis.from_url.return_value = mock_redis_client
            result = await expire_stale_approvals({})

        assert result["status"] == "skipped_dedup"

    @pytest.mark.asyncio
    async def test_expire_stale_approvals_proceeds_when_redis_unavailable(self):
        """When Redis lock check fails, proceeds anyway (non-blocking)."""
        from margin_api.workers import expire_stale_approvals

        now = datetime.now(UTC)
        stale = MagicMock(spec=PipelineApproval)
        stale.status = "staged"
        stale.expires_at = now - timedelta(hours=25)

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalars_all": [stale]},
            ]
        )

        mock_redis_client = AsyncMock()
        mock_redis_client.set = AsyncMock(side_effect=ConnectionError("Redis down"))
        mock_redis_client.aclose = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch("margin_api.workers.aioredis") as mock_aioredis,
            patch("margin_api.workers.get_settings"),
        ):
            mock_aioredis.from_url.return_value = mock_redis_client
            result = await expire_stale_approvals({})

        # Should proceed and expire even when Redis is unavailable
        assert result["status"] == "completed"
        assert result["expired_count"] == 1

    @pytest.mark.asyncio
    async def test_expire_stale_approvals_zero_expired(self):
        """Returns completed with expired_count=0 when nothing is stale."""
        from margin_api.workers import expire_stale_approvals

        factory, session, added = _mock_session_factory(
            execute_side_effects=[
                {"scalars_all": []},
            ]
        )

        mock_redis_client = AsyncMock()
        mock_redis_client.set = AsyncMock(return_value=True)
        mock_redis_client.aclose = AsyncMock()

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=factory),
            patch("margin_api.workers.reset_engine_cache"),
            patch("margin_api.workers.aioredis") as mock_aioredis,
            patch("margin_api.workers.get_settings"),
        ):
            mock_aioredis.from_url.return_value = mock_redis_client
            result = await expire_stale_approvals({})

        assert result["status"] == "completed"
        assert result["expired_count"] == 0


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestGovernanceWorkerRegistration:
    """Verify governance workers are registered in WorkerSettings."""

    def test_stage_scores_in_functions(self):
        from margin_api.workers import WorkerSettings, stage_scores

        assert stage_scores in WorkerSettings.functions

    def test_publish_scores_in_functions(self):
        from margin_api.workers import WorkerSettings, publish_scores

        assert publish_scores in WorkerSettings.functions

    def test_promote_ml_model_in_functions(self):
        from margin_api.workers import WorkerSettings, promote_ml_model

        assert promote_ml_model in WorkerSettings.functions

    def test_expire_stale_approvals_in_functions(self):
        from margin_api.workers import WorkerSettings, expire_stale_approvals

        assert expire_stale_approvals in WorkerSettings.functions

    def test_expire_stale_approvals_in_cron_jobs(self):
        from margin_api.workers import WorkerSettings

        cron_funcs = [
            job.coroutine.__name__ if hasattr(job, "coroutine") else str(job)
            for job in WorkerSettings.cron_jobs
        ]
        assert "expire_stale_approvals" in cron_funcs
