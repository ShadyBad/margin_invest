"""Extended tests for compute_rarity worker function.

Covers:
- Multiple tickers with percentile ranking
- Regime classification effects on result
- Dimension score population
- Missing/corrupt factors handled gracefully
- All-failed reconstruction path
- Distribution snapshots written correctly
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.db.models import JobRun, RarityDistributionSnapshot, RarityScore

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
    added_all_objects: list = []

    session = MagicMock()
    session.commit = AsyncMock()

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

    def _add_all(objs):
        added_all_objects.extend(objs)

    session.add = _add
    session.add_all = _add_all

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=ctx)
    return factory, session, added_objects, added_all_objects


def _build_rarity_result(ticker: str, rarity_score: float = 80.0):
    """Build a minimal RarityResult for testing."""
    from margin_engine.rarity.models import RarityDimensionScores, RarityResult

    dims = RarityDimensionScores(
        joint_rarity_pctl=rarity_score,
        convergence_score=rarity_score - 5,
        historical_frequency=70.0,
        quality_momentum=75.0,
        smart_money_score=60.0,
        regime_alignment=80.0,
    )
    return RarityResult(
        ticker=ticker,
        rarity_score=rarity_score,
        conviction_score=rarity_score - 2,
        dimensions=dims,
        combination_signature=f"sig-{ticker}",
        pillar_percentiles={"value": 80.0, "growth": 85.0, "quality": 70.0},
        is_generational=False,
        passed_gates=[True, True],
        universe_size=3,
        composite_raw_score=rarity_score,
        composite_tier="tier_1",
    )


def _build_v4_asset_pair(ticker: str, asset_id: int):
    """Build a minimal (V4Score, Asset) mock pair with a valid CompositeScore detail dict."""
    mock_asset = MagicMock()
    mock_asset.id = asset_id

    mock_v4 = MagicMock()
    mock_v4.asset_id = asset_id
    # Must include all required CompositeScore fields so reconstruction succeeds:
    # ticker, composite_percentile, quality, value, momentum, filters_passed, data_coverage
    mock_v4.detail = {
        "ticker": ticker,
        "composite_percentile": 80.0,
        "composite_raw_score": 80.0,
        "quality": {"factor_name": "quality", "weight": 0.3, "sub_scores": []},
        "value": {"factor_name": "value", "weight": 0.3, "sub_scores": []},
        "momentum": {"factor_name": "momentum", "weight": 0.2, "sub_scores": []},
        "filters_passed": [],
        "data_coverage": 1.0,
    }
    return mock_v4, mock_asset


# ---------------------------------------------------------------------------
# Test: multiple tickers produce correct rarity_count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_rarity_multiple_tickers():
    """With multiple tickers, rarity_count matches number of RarityResult rows."""
    from margin_api.workers import compute_rarity
    from margin_engine.rarity.models import RarityRegime

    pairs = [
        _build_v4_asset_pair("AAPL", 1),
        _build_v4_asset_pair("MSFT", 2),
        _build_v4_asset_pair("GOOG", 3),
    ]
    results = [
        _build_rarity_result("AAPL", 90.0),
        _build_rarity_result("MSFT", 75.0),
        _build_rarity_result("GOOG", 60.0),
    ]

    job_mock = MagicMock()
    job_mock.id = 42

    factory, session, added, added_all = _mock_session_factory(
        execute_side_effects=[
            {"all": pairs},  # V4Score query
            {"scalar_one": job_mock},  # job update
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_engine.rarity.rarity_engine.compute_rarity_for_universe", return_value=results
        ),
        patch("margin_engine.rarity.regime.classify_regime", return_value=RarityRegime.EXPANSION),
        patch(
            "margin_api.data.macro_data_client.fetch_vix", new_callable=AsyncMock, return_value=18.0
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
            pipeline_id="pipe-multi",
            scored_at_iso="2026-03-17T00:00:00+00:00",
        )

    assert result["status"] == "completed"
    assert result["rarity_count"] == 3
    assert result["pipeline_id"] == "pipe-multi"

    # Should have written RarityScore rows via add_all
    rarity_score_rows = [o for o in added_all if isinstance(o, RarityScore)]
    assert len(rarity_score_rows) == 3
    tickers_written = {r.asset_id for r in rarity_score_rows}
    assert tickers_written == {1, 2, 3}


# ---------------------------------------------------------------------------
# Test: regime appears in result dict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_rarity_regime_in_result():
    """The regime value should be returned in the result dict."""
    from margin_api.workers import compute_rarity
    from margin_engine.rarity.models import RarityRegime

    pair = _build_v4_asset_pair("TSLA", 10)
    rarity_result = _build_rarity_result("TSLA", 55.0)

    factory, session, added, added_all = _mock_session_factory(
        execute_side_effects=[
            {"all": [pair]},
            {"scalar_one": MagicMock(id=42)},
        ]
    )

    # Use CONTRACTION regime to verify it flows through
    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_engine.rarity.rarity_engine.compute_rarity_for_universe",
            return_value=[rarity_result],
        ),
        patch("margin_engine.rarity.regime.classify_regime", return_value=RarityRegime.CONTRACTION),
        patch(
            "margin_api.data.macro_data_client.fetch_vix", new_callable=AsyncMock, return_value=35.0
        ),
        patch(
            "margin_api.data.macro_data_client.fetch_yield_curve_slope",
            new_callable=AsyncMock,
            return_value=-0.5,
        ),
        patch(
            "margin_api.data.macro_data_client.fetch_credit_spread",
            new_callable=AsyncMock,
            return_value=3.5,
        ),
    ):
        result = await compute_rarity({}, pipeline_id="pipe-regime")

    assert result["status"] == "completed"
    assert "contraction" in result["regime"].lower()

    # RarityScore row should have the regime set
    rarity_rows = [o for o in added_all if isinstance(o, RarityScore)]
    assert len(rarity_rows) == 1
    assert "contraction" in rarity_rows[0].regime.lower()


# ---------------------------------------------------------------------------
# Test: dimension scores populated on RarityScore rows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_rarity_dimension_scores_populated():
    """RarityScore rows should have all dimension fields populated."""
    from margin_api.workers import compute_rarity
    from margin_engine.rarity.models import RarityRegime

    pair = _build_v4_asset_pair("NVDA", 5)
    rarity_result = _build_rarity_result("NVDA", 95.0)

    factory, session, added, added_all = _mock_session_factory(
        execute_side_effects=[
            {"all": [pair]},
            {"scalar_one": MagicMock(id=42)},
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_engine.rarity.rarity_engine.compute_rarity_for_universe",
            return_value=[rarity_result],
        ),
        patch("margin_engine.rarity.regime.classify_regime", return_value=RarityRegime.EXPANSION),
        patch(
            "margin_api.data.macro_data_client.fetch_vix", new_callable=AsyncMock, return_value=18.0
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
        result = await compute_rarity({}, pipeline_id="pipe-dims")

    assert result["status"] == "completed"
    rarity_rows = [o for o in added_all if isinstance(o, RarityScore)]
    assert len(rarity_rows) == 1
    row = rarity_rows[0]
    # All dimension fields should be floats
    assert row.rarity_score == 95.0
    assert row.joint_rarity_pctl == 95.0
    assert row.convergence_score == 90.0
    assert row.historical_frequency == 70.0
    assert row.quality_momentum == 75.0
    assert row.smart_money_score == 60.0
    assert row.regime_alignment == 80.0
    assert row.combination_signature == "sig-NVDA"
    assert row.is_generational is False
    assert row.universe_size == 3
    # Detail dict should contain pillar_percentiles and gates
    assert "pillar_percentiles" in row.detail
    assert "passed_gates" in row.detail


# ---------------------------------------------------------------------------
# Test: missing factors (corrupt JSONB) handled gracefully
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_rarity_corrupt_detail_skipped():
    """Tickers with corrupt detail JSONB should be skipped without crashing."""
    from margin_api.workers import compute_rarity
    from margin_engine.rarity.models import RarityRegime

    # One good pair, one with empty detail
    good_pair = _build_v4_asset_pair("AAPL", 1)
    bad_v4 = MagicMock()
    bad_v4.asset_id = 99
    bad_v4.detail = {}  # Empty — CompositeScore(**{}) will raise or produce bad object
    bad_asset = MagicMock()
    bad_asset.id = 99

    rarity_result = _build_rarity_result("AAPL", 88.0)

    factory, session, added, added_all = _mock_session_factory(
        execute_side_effects=[
            {"all": [good_pair, (bad_v4, bad_asset)]},
            {"scalar_one": MagicMock(id=42)},
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_engine.rarity.rarity_engine.compute_rarity_for_universe",
            return_value=[rarity_result],
        ),
        patch("margin_engine.rarity.regime.classify_regime", return_value=RarityRegime.EXPANSION),
        patch(
            "margin_api.data.macro_data_client.fetch_vix", new_callable=AsyncMock, return_value=18.0
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
        result = await compute_rarity({}, pipeline_id="pipe-corrupt")

    # Should complete successfully — bad ticker was skipped
    assert result["status"] == "completed"
    assert result["rarity_count"] == 1


# ---------------------------------------------------------------------------
# Test: all reconstructions fail → returns rarity_count=0 but completes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_rarity_all_detail_null():
    """When all V4Score rows have null detail, returns completed with rarity_count=0."""
    from margin_api.workers import compute_rarity

    null_v4 = MagicMock()
    null_v4.asset_id = 1
    null_v4.detail = None  # Null detail triggers early exit
    null_asset = MagicMock()
    null_asset.id = 1

    factory, session, added, added_all = _mock_session_factory(
        execute_side_effects=[
            {"all": [(null_v4, null_asset)]},
            {"scalar_one": MagicMock(id=42)},
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
    ):
        result = await compute_rarity({}, pipeline_id="pipe-null")

    assert result["status"] == "completed"
    assert result["rarity_count"] == 0


# ---------------------------------------------------------------------------
# Test: distribution snapshots written for multiple pillar buckets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_rarity_distribution_snapshots_written():
    """RarityDistributionSnapshot rows should be written for each pillar."""
    from margin_api.workers import compute_rarity
    from margin_engine.rarity.models import RarityRegime

    # Two tickers with pillar_percentiles
    pairs = [_build_v4_asset_pair("AAPL", 1), _build_v4_asset_pair("MSFT", 2)]
    results = [_build_rarity_result("AAPL", 90.0), _build_rarity_result("MSFT", 75.0)]
    # Each result has pillar_percentiles: {"value": 80.0, "growth": 85.0, "quality": 70.0}

    factory, session, added, added_all = _mock_session_factory(
        execute_side_effects=[
            {"all": pairs},
            {"scalar_one": MagicMock(id=42)},
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_engine.rarity.rarity_engine.compute_rarity_for_universe", return_value=results
        ),
        patch("margin_engine.rarity.regime.classify_regime", return_value=RarityRegime.EXPANSION),
        patch(
            "margin_api.data.macro_data_client.fetch_vix", new_callable=AsyncMock, return_value=18.0
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
        result = await compute_rarity({}, pipeline_id="pipe-distrib")

    assert result["status"] == "completed"

    # Should have written distribution snapshots for each pillar name
    snap_rows = [o for o in added_all if isinstance(o, RarityDistributionSnapshot)]
    assert len(snap_rows) == 3  # value, growth, quality
    factor_names = {s.factor_name for s in snap_rows}
    assert "value" in factor_names
    assert "growth" in factor_names
    assert "quality" in factor_names

    # Each snapshot should have n_obs=2 (two tickers) and percentile keys
    for snap in snap_rows:
        assert snap.n_obs == 2
        assert snap.scope == "universe"
        assert "p50" in snap.percentiles
        assert snap.mean is not None


# ---------------------------------------------------------------------------
# Test: is_generational ticker flagged correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_rarity_generational_flag():
    """A generational ticker should have is_generational=True on its RarityScore row."""
    from margin_api.workers import compute_rarity
    from margin_engine.rarity.models import RarityDimensionScores, RarityRegime, RarityResult

    pair = _build_v4_asset_pair("BRK", 7)

    dims = RarityDimensionScores(
        joint_rarity_pctl=99.0,
        convergence_score=99.0,
        historical_frequency=99.0,
        quality_momentum=99.0,
        smart_money_score=99.0,
        regime_alignment=99.0,
    )
    generational_result = RarityResult(
        ticker="BRK",
        rarity_score=99.0,
        conviction_score=99.0,
        dimensions=dims,
        combination_signature="sig-gen",
        pillar_percentiles={"value": 99.0},
        is_generational=True,
        passed_gates=[True, True, True],
        universe_size=50,
        composite_raw_score=99.0,
        composite_tier="tier_1",
    )

    factory, session, added, added_all = _mock_session_factory(
        execute_side_effects=[
            {"all": [pair]},
            {"scalar_one": MagicMock(id=42)},
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_engine.rarity.rarity_engine.compute_rarity_for_universe",
            return_value=[generational_result],
        ),
        patch("margin_engine.rarity.regime.classify_regime", return_value=RarityRegime.EXPANSION),
        patch(
            "margin_api.data.macro_data_client.fetch_vix", new_callable=AsyncMock, return_value=16.0
        ),
        patch(
            "margin_api.data.macro_data_client.fetch_yield_curve_slope",
            new_callable=AsyncMock,
            return_value=0.8,
        ),
        patch(
            "margin_api.data.macro_data_client.fetch_credit_spread",
            new_callable=AsyncMock,
            return_value=0.9,
        ),
    ):
        result = await compute_rarity({}, pipeline_id="pipe-gen")

    assert result["status"] == "completed"
    rarity_rows = [o for o in added_all if isinstance(o, RarityScore)]
    assert len(rarity_rows) == 1
    assert rarity_rows[0].is_generational is True
    assert rarity_rows[0].rarity_score == 99.0


# ---------------------------------------------------------------------------
# Test: macro fetch failure falls back gracefully
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_rarity_macro_fetch_failure():
    """If macro data fetch raises, the worker still completes via classify_regime fallback."""
    from margin_api.workers import compute_rarity
    from margin_engine.rarity.models import RarityRegime

    pair = _build_v4_asset_pair("AAPL", 1)
    rarity_result = _build_rarity_result("AAPL", 80.0)

    factory, session, added, added_all = _mock_session_factory(
        execute_side_effects=[
            {"all": [pair]},
            {"scalar_one": MagicMock(id=42)},
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_engine.rarity.rarity_engine.compute_rarity_for_universe",
            return_value=[rarity_result],
        ),
        patch("margin_engine.rarity.regime.classify_regime", return_value=RarityRegime.LATE_CYCLE),
        # Macro fetches return defaults (no exception — VIX etc have built-in fallback)
        patch(
            "margin_api.data.macro_data_client.fetch_vix", new_callable=AsyncMock, return_value=20.0
        ),
        patch(
            "margin_api.data.macro_data_client.fetch_yield_curve_slope",
            new_callable=AsyncMock,
            return_value=0.0,
        ),
        patch(
            "margin_api.data.macro_data_client.fetch_credit_spread",
            new_callable=AsyncMock,
            return_value=2.0,
        ),
    ):
        result = await compute_rarity({}, pipeline_id="pipe-macro-fallback")

    assert result["status"] == "completed"
    assert result["rarity_count"] == 1


# ---------------------------------------------------------------------------
# Test: ticker with no matching asset_id in map is skipped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_rarity_unknown_ticker_skipped():
    """If rarity engine returns a ticker not in asset_id_by_ticker, it's skipped."""
    from margin_api.workers import compute_rarity
    from margin_engine.rarity.models import RarityRegime

    pair = _build_v4_asset_pair("AAPL", 1)
    # Engine returns result for AAPL + an unknown ticker "FAKE"
    good_result = _build_rarity_result("AAPL", 80.0)
    unknown_result = _build_rarity_result("FAKE", 90.0)

    factory, session, added, added_all = _mock_session_factory(
        execute_side_effects=[
            {"all": [pair]},
            {"scalar_one": MagicMock(id=42)},
        ]
    )

    with (
        patch("margin_api.workers.get_engine"),
        patch("margin_api.workers.get_session_factory", return_value=factory),
        patch("margin_api.workers.reset_engine_cache"),
        patch(
            "margin_engine.rarity.rarity_engine.compute_rarity_for_universe",
            return_value=[good_result, unknown_result],
        ),
        patch("margin_engine.rarity.regime.classify_regime", return_value=RarityRegime.EXPANSION),
        patch(
            "margin_api.data.macro_data_client.fetch_vix", new_callable=AsyncMock, return_value=18.0
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
        result = await compute_rarity({}, pipeline_id="pipe-unknown")

    assert result["status"] == "completed"
    # Only AAPL written — FAKE is unknown
    assert result["rarity_count"] == 1
    rarity_rows = [o for o in added_all if isinstance(o, RarityScore)]
    assert len(rarity_rows) == 1
    assert rarity_rows[0].asset_id == 1
