"""Tests for the rescore_ticker per-ticker scoring worker.

Covers:
- rescore_ticker calls run_scoring_v4 with correct ticker
- rescore_ticker updates DrawdownRescreen record on success
- rescore_ticker handles pipeline failure gracefully
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.db.models import DrawdownRescreen, JobRun, V4Score

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_execute_result(**kwargs):
    """Build a MagicMock that behaves like a SQLAlchemy Result."""
    result = MagicMock()
    result.scalar_one.return_value = kwargs.get("scalar_one", MagicMock(id=42))
    result.scalar_one_or_none.return_value = kwargs.get("scalar_one_or_none", None)
    result.all.return_value = kwargs.get("all", [])
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = kwargs.get("scalars_all", [])
    result.scalars.return_value = scalars_mock
    return result


def _mock_session_factory(execute_side_effects: list | None = None):
    """Build a mock async session factory with a call-index-based execute."""
    effects = list(execute_side_effects or [])
    call_idx = {"n": 0}
    added_objects: list = []

    session = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()

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


def _make_drawdown_rescreen(ticker: str = "DROP") -> DrawdownRescreen:
    """Create a mock DrawdownRescreen with no outcome (unprocessed)."""
    rescreen = MagicMock(spec=DrawdownRescreen)
    rescreen.id = 1
    rescreen.ticker = ticker
    rescreen.drawdown_pct = 25.0
    rescreen.high_price = 100.0
    rescreen.current_price = 75.0
    rescreen.outcome = None
    rescreen.new_conviction = None
    rescreen.prior_conviction = "stable"
    return rescreen


def _make_v4_score(conviction: str = "strong") -> V4Score:
    """Create a mock V4Score."""
    score = MagicMock(spec=V4Score)
    score.conviction = conviction
    return score


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rescore_ticker_calls_scoring_pipeline():
    """rescore_ticker should call run_scoring_v4 with the target ticker."""
    from margin_api.workers import rescore_ticker

    rescreen = _make_drawdown_rescreen("DROP")
    v4_score = _make_v4_score("strong")

    # Execute effects:
    # 1. First session block: JobRun creation (uses session.add, not execute)
    # 2. Second session block (success path):
    #    - select JobRun -> job mock
    #    - select DrawdownRescreen -> rescreen
    #    - select V4Score (joined with Asset) -> v4_score
    factory, session, added = _mock_session_factory(
        [
            {"scalar_one": MagicMock(id=42)},  # JobRun select
            {"scalar_one_or_none": rescreen},  # DrawdownRescreen select
            {"scalar_one_or_none": v4_score},  # V4Score select
        ]
    )

    mock_scoring = AsyncMock(return_value=datetime.now(UTC))

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.cli.run_scoring_v4", new=mock_scoring),
    ):
        await rescore_ticker({}, "DROP", "drawdown")

    # The key assertion: run_scoring_v4 was called with the ticker
    mock_scoring.assert_awaited_once_with(tickers=["DROP"])


@pytest.mark.asyncio
async def test_rescore_ticker_updates_drawdown_record():
    """rescore_ticker should return status='rescored' on success."""
    from margin_api.workers import rescore_ticker

    rescreen = _make_drawdown_rescreen("DROP")
    v4_score = _make_v4_score("strong")

    factory, session, added = _mock_session_factory(
        [
            {"scalar_one": MagicMock(id=42)},  # JobRun select
            {"scalar_one_or_none": rescreen},  # DrawdownRescreen select
            {"scalar_one_or_none": v4_score},  # V4Score select
        ]
    )

    mock_scoring = AsyncMock(return_value=datetime.now(UTC))

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.cli.run_scoring_v4", new=mock_scoring),
    ):
        result = await rescore_ticker({}, "DROP", "drawdown")

    assert result["status"] == "rescored"
    assert result["ticker"] == "DROP"
    # Verify the rescreen record was updated
    assert rescreen.outcome == "rescored"
    assert rescreen.new_conviction == "strong"


@pytest.mark.asyncio
async def test_rescore_ticker_handles_failure():
    """rescore_ticker should return status='error' when scoring raises."""
    from margin_api.workers import rescore_ticker

    rescreen = _make_drawdown_rescreen("DROP")

    factory, session, added = _mock_session_factory(
        [
            {"scalar_one": MagicMock(id=42)},  # JobRun select (error path)
            {"scalar_one_or_none": rescreen},  # DrawdownRescreen select (error path)
        ]
    )

    mock_scoring = AsyncMock(side_effect=RuntimeError("scoring engine exploded"))

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_api.cli.run_scoring_v4", new=mock_scoring),
    ):
        result = await rescore_ticker({}, "DROP", "drawdown")

    assert result["status"] == "error"
    assert result["ticker"] == "DROP"
    assert "scoring engine exploded" in result["error"]
    # Verify the rescreen record was marked failed
    assert rescreen.outcome == "failed"
