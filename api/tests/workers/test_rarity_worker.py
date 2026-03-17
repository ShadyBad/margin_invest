"""Tests for compute_rarity worker function."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.db.models import JobRun

# ---------------------------------------------------------------------------
# Helpers (mirrored from test_backtest_workers.py)
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

    session.add = _add

    # Make session usable as async context manager
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=ctx)
    return factory, session, added_objects


# ---------------------------------------------------------------------------
# test_compute_rarity_no_scores
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_rarity_no_scores():
    """When no V4Score rows exist for the given scored_at, worker returns rarity_count=0."""
    from margin_api.workers import compute_rarity

    job_mock = MagicMock()
    job_mock.id = 42

    # Call sequence:
    # Session 1: JobRun creation (session.add, no execute)
    # Session 2: V4Score query → empty list
    # Session 3: job update → job mock object
    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"all": []},  # V4Score query → empty
            {"scalar_one": job_mock},  # job update query
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
    ):
        result = await compute_rarity(
            {},
            pipeline_id="pipe-1",
            scored_at_iso="2026-03-17T00:00:00+00:00",
        )

    assert result["status"] == "completed"
    assert result["rarity_count"] == 0
    assert result["pipeline_id"] == "pipe-1"

    # JobRun should have been created
    job_runs = [o for o in added if isinstance(o, JobRun)]
    assert len(job_runs) == 1
    assert job_runs[0].job_type == "compute_rarity"


# ---------------------------------------------------------------------------
# test_compute_rarity_creates_job_run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_rarity_creates_job_run():
    """Worker should create a JobRun with job_type='compute_rarity'."""
    from margin_api.workers import compute_rarity
    from margin_engine.rarity.models import RarityDimensionScores, RarityRegime, RarityResult

    # Build a minimal mock V4Score + Asset pair
    mock_asset = MagicMock()
    mock_asset.id = 10

    mock_v4 = MagicMock()
    mock_v4.asset_id = 10
    mock_v4.detail = {
        "ticker": "AAPL",
        "composite_score": 80.0,
        "signal": "strong",
        "composite_tier": "tier_1",
        "factor_breakdown": {},
        "filters": {},
    }

    # Build a minimal RarityResult that the mocked engine would return
    rarity_dims = RarityDimensionScores(
        joint_rarity_pctl=90.0,
        convergence_score=85.0,
        historical_frequency=70.0,
        quality_momentum=75.0,
        smart_money_score=60.0,
        regime_alignment=80.0,
    )
    rarity_result = RarityResult(
        ticker="AAPL",
        rarity_score=88.0,
        conviction_score=82.0,
        dimensions=rarity_dims,
        combination_signature="sig-abc",
        pillar_percentiles={"value": 80.0, "growth": 85.0},
        is_generational=False,
        passed_gates=[True, True],
        universe_size=1,
        composite_raw_score=80.0,
        composite_tier="tier_1",
    )

    job_mock = MagicMock()
    job_mock.id = 42

    # Call sequence across all sessions:
    # Session 1: JobRun creation (session.add only)
    # Session 2: V4Score query → one row
    # Session 3: add_all RarityScore rows (no execute needed)
    # Session 4: add_all RarityDistributionSnapshot rows (no execute needed)
    # Session 5: job update query → job mock
    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"all": [(mock_v4, mock_asset)]},  # V4Score query
            {"scalar_one": job_mock},  # job update
        ]
    )

    mock_regime = RarityRegime.EXPANSION

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_engine.rarity.rarity_engine.compute_rarity_for_universe",
            return_value=[rarity_result],
        ),
        patch(
            "margin_engine.rarity.regime.classify_regime",
            return_value=mock_regime,
        ),
        patch(
            "margin_api.data.macro_data_client.fetch_vix",
            new_callable=AsyncMock,
            return_value=18.0,
        ),
        patch(
            "margin_api.data.macro_data_client.fetch_yield_curve_slope",
            new_callable=AsyncMock,
            return_value=0.5,
        ),
        patch(
            "margin_api.data.macro_data_client.fetch_credit_spread",
            new_callable=AsyncMock,
            return_value=1.2,
        ),
    ):
        result = await compute_rarity(
            {},
            pipeline_id="pipe-2",
            scored_at_iso="2026-03-17T00:00:00+00:00",
        )

    assert result["status"] == "completed"
    assert result["pipeline_id"] == "pipe-2"

    job_runs = [o for o in added if isinstance(o, JobRun)]
    assert len(job_runs) == 1
    assert job_runs[0].job_type == "compute_rarity"
    assert job_runs[0].status == "running"
    assert job_runs[0].triggered_by == "chained"


# ---------------------------------------------------------------------------
# test_compute_rarity_handles_exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_rarity_handles_exception():
    """When compute_rarity_for_universe raises, worker marks job failed and returns error."""
    from margin_api.workers import compute_rarity
    from margin_engine.rarity.models import RarityRegime

    mock_asset = MagicMock()
    mock_asset.id = 10

    mock_v4 = MagicMock()
    mock_v4.asset_id = 10
    # Non-empty detail so the reconstruction attempt fires; we'll patch CompositeScore
    mock_v4.detail = {"ticker": "AAPL"}

    job_mock = MagicMock()
    job_mock.id = 42

    factory, session, added = _mock_session_factory(
        execute_side_effects=[
            {"all": [(mock_v4, mock_asset)]},  # V4Score query
            {"scalar_one": job_mock},  # job failure update
        ]
    )

    # Patch CompositeScore so reconstruction succeeds and we reach the engine call
    mock_composite = MagicMock()
    mock_composite.ticker = "AAPL"

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch("margin_engine.models.scoring.CompositeScore", return_value=mock_composite),
        patch(
            "margin_engine.rarity.rarity_engine.compute_rarity_for_universe",
            side_effect=RuntimeError("rarity engine exploded"),
        ),
        patch(
            "margin_engine.rarity.regime.classify_regime",
            return_value=RarityRegime.EXPANSION,
        ),
        patch(
            "margin_api.data.macro_data_client.fetch_vix",
            new_callable=AsyncMock,
            return_value=18.0,
        ),
        patch(
            "margin_api.data.macro_data_client.fetch_yield_curve_slope",
            new_callable=AsyncMock,
            return_value=0.5,
        ),
        patch(
            "margin_api.data.macro_data_client.fetch_credit_spread",
            new_callable=AsyncMock,
            return_value=1.2,
        ),
    ):
        result = await compute_rarity(
            {},
            pipeline_id="pipe-3",
            scored_at_iso="2026-03-17T00:00:00+00:00",
        )

    assert result["status"] == "failed"
    assert "rarity engine exploded" in result["error"]
    assert result["pipeline_id"] == "pipe-3"

    # JobRun should have been created and then marked failed
    job_runs = [o for o in added if isinstance(o, JobRun)]
    assert len(job_runs) == 1
    assert job_runs[0].job_type == "compute_rarity"
