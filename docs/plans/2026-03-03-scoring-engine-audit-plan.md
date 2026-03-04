# Scoring Engine Audit Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the Phase 1 (Credible V1) recommendations from the scoring engine audit — sever tier-assignment ambiguity, exclude zeroed factor stubs, align API endpoints to V4-only authority, and add calibration status endpoint.

**Architecture:** Add `conviction_override` field to `CompositeScore` so V4 orchestrator becomes the single tier authority. Exclude stubbed factors from momentum averages. Remove V2 fallback from scoring API routes. Add `scoring_version` and `conviction_source` fields to response schemas. Add calibration status endpoint.

**Tech Stack:** Python (Pydantic models, FastAPI routes, SQLAlchemy), TypeScript (Next.js types), pytest, vitest

---

### Task 1: Add `conviction_override` to CompositeScore model

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py:114-159`
- Test: `engine/tests/models/test_scoring.py` (existing) and `engine/tests/test_scoring_models.py` (existing)

**Step 1: Write the failing test**

Add to `engine/tests/test_scoring_models.py`:

```python
class TestConvictionOverride:
    """Tests for conviction_override taking precedence over threshold-based tier."""

    def _make_score(self, composite_raw_score: float = 50.0, **kwargs):
        from margin_engine.models.scoring import (
            CompositeScore,
            FactorBreakdown,
            FactorScore,
        )
        dummy_breakdown = FactorBreakdown(
            factor_name="quality", weight=0.35, sub_scores=[
                FactorScore(name="test", raw_value=1.0, percentile_rank=50.0),
            ],
        )
        return CompositeScore(
            ticker="TEST",
            composite_percentile=50.0,
            composite_raw_score=composite_raw_score,
            quality=dummy_breakdown,
            value=dummy_breakdown,
            momentum=dummy_breakdown,
            filters_passed=[],
            data_coverage=1.0,
            **kwargs,
        )

    def test_override_none_uses_threshold(self):
        """When conviction_override is None, composite_tier uses threshold logic."""
        score = self._make_score(composite_raw_score=76.0)
        assert score.conviction_override is None
        assert score.composite_tier == CompositeTier.EXCEPTIONAL

    def test_override_set_takes_precedence(self):
        """When conviction_override is set, it overrides threshold-based tier."""
        score = self._make_score(
            composite_raw_score=50.0,  # Would be NONE by threshold
            conviction_override=CompositeTier.EXCEPTIONAL,
        )
        assert score.composite_tier == CompositeTier.EXCEPTIONAL

    def test_override_can_downgrade(self):
        """Override can assign a lower tier than thresholds would."""
        score = self._make_score(
            composite_raw_score=80.0,  # Would be EXCEPTIONAL by threshold
            conviction_override=CompositeTier.MEDIUM,
        )
        assert score.composite_tier == CompositeTier.MEDIUM

    def test_signal_uses_overridden_tier(self):
        """Signal property should use the overridden tier."""
        score = self._make_score(
            composite_raw_score=50.0,  # NONE by threshold
            conviction_override=CompositeTier.HIGH,
            actual_price=90.0,
            buy_price=100.0,
            sell_price=150.0,
        )
        # HIGH tier + price <= buy_price -> BUY signal
        assert score.signal == Signal.BUY
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_scoring_models.py::TestConvictionOverride -v`
Expected: FAIL — `conviction_override` field does not exist

**Step 3: Write minimal implementation**

In `engine/src/margin_engine/models/scoring.py`, add the field and modify the property:

```python
# After line 144 (timing_signal field), add:
    # V4 conviction override — when set by V4 orchestrator, takes precedence
    # over threshold-based tier assignment from composite_raw_score
    conviction_override: CompositeTier | None = None

# Replace the composite_tier property (lines 151-159) with:
    @property
    def composite_tier(self) -> CompositeTier:
        if self.conviction_override is not None:
            return self.conviction_override
        if self.composite_raw_score >= 76.0:
            return CompositeTier.EXCEPTIONAL
        if self.composite_raw_score >= 71.0:
            return CompositeTier.HIGH
        if self.composite_raw_score >= 66.0:
            return CompositeTier.MEDIUM
        return CompositeTier.NONE
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/test_scoring_models.py::TestConvictionOverride -v`
Expected: PASS (4 tests)

**Step 5: Run full scoring model tests to check for regressions**

Run: `uv run pytest engine/tests/test_scoring_models.py -v`
Expected: All existing tests still pass (conviction_override defaults to None)

**Step 6: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/tests/test_scoring_models.py
git commit -m "feat(engine): add conviction_override to CompositeScore for V4 authority"
```

---

### Task 2: Exclude stubbed factors from momentum average

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py:78-111` (FactorScore and FactorBreakdown)
- Test: `engine/tests/test_scoring_models.py` (add new tests)

**Step 1: Write the failing test**

Add to `engine/tests/test_scoring_models.py`:

```python
class TestStubExclusion:
    """Tests for excluding stub=True factors from average_percentile."""

    def test_stub_excluded_from_average(self):
        from margin_engine.models.scoring import FactorBreakdown, FactorScore
        breakdown = FactorBreakdown(
            factor_name="momentum",
            weight=0.35,
            sub_scores=[
                FactorScore(name="price_momentum", raw_value=1.0, percentile_rank=80.0),
                FactorScore(name="sue", raw_value=1.0, percentile_rank=60.0),
                FactorScore(name="sentiment", raw_value=5.0, percentile_rank=0.0, stub=True),
                FactorScore(name="earnings_revision", raw_value=0.0, percentile_rank=0.0, stub=True),
            ],
        )
        # Average should be (80 + 60) / 2 = 70, not (80 + 60 + 0 + 0) / 4 = 35
        assert breakdown.average_percentile == pytest.approx(70.0)

    def test_stub_default_false(self):
        from margin_engine.models.scoring import FactorScore
        score = FactorScore(name="test", raw_value=1.0, percentile_rank=50.0)
        assert score.stub is False

    def test_all_stubs_returns_zero(self):
        from margin_engine.models.scoring import FactorBreakdown, FactorScore
        breakdown = FactorBreakdown(
            factor_name="momentum",
            weight=0.35,
            sub_scores=[
                FactorScore(name="sentiment", raw_value=5.0, percentile_rank=0.0, stub=True),
            ],
        )
        assert breakdown.average_percentile == 0.0

    def test_no_stubs_unchanged(self):
        from margin_engine.models.scoring import FactorBreakdown, FactorScore
        breakdown = FactorBreakdown(
            factor_name="momentum",
            weight=0.35,
            sub_scores=[
                FactorScore(name="a", raw_value=1.0, percentile_rank=80.0),
                FactorScore(name="b", raw_value=1.0, percentile_rank=60.0),
            ],
        )
        assert breakdown.average_percentile == pytest.approx(70.0)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_scoring_models.py::TestStubExclusion -v`
Expected: FAIL — `stub` field does not exist on FactorScore

**Step 3: Write minimal implementation**

In `engine/src/margin_engine/models/scoring.py`:

```python
# In FactorScore class (after line 85, the weight field), add:
    stub: bool = False  # True for placeholder factors (sentiment, earnings_revision) until wired

# Replace the average_percentile property (lines 102-111) with:
    @property
    def average_percentile(self) -> float:
        active = [s for s in self.sub_scores if not s.stub]
        if not active:
            return 0.0
        weights = [s.weight for s in active if s.weight is not None]
        if weights and len(weights) == len(active):
            total_weight = sum(weights)
            if total_weight > 0:
                return sum(s.percentile_rank * s.weight for s in active) / total_weight
        return sum(s.percentile_rank for s in active) / len(active)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/test_scoring_models.py::TestStubExclusion -v`
Expected: PASS (4 tests)

**Step 5: Run full test suite to check regressions**

Run: `uv run pytest engine/tests/test_scoring_models.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/tests/test_scoring_models.py
git commit -m "feat(engine): add stub flag to FactorScore, exclude from averages"
```

---

### Task 3: Mark sentiment and earnings revision as stubs in scoring pipeline

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/sentiment_score.py:67`
- Modify: `engine/src/margin_engine/scoring/quantitative/contrarian_signal.py` (find the FactorScore return)
- Test: `engine/tests/scoring/test_sentiment_score.py` (existing)
- Test: `engine/tests/scoring/test_contrarian_signal.py` (existing)

**Step 1: Write the failing test**

Add to `engine/tests/scoring/test_sentiment_score.py`:

```python
def test_sentiment_score_marked_as_stub():
    """Sentiment factor should be marked as stub until LLM pipeline is wired."""
    result = sentiment_score(0.0)
    assert result.stub is True
```

Add to `engine/tests/scoring/test_contrarian_signal.py` (or create if needed):

```python
def test_contrarian_signal_marked_as_stub():
    """Contrarian signal should be marked as stub until sentiment pipeline is wired."""
    from margin_engine.scoring.quantitative.contrarian_signal import contrarian_signal
    result = contrarian_signal(momentum_percentile=30.0, quality_percentile=80.0)
    assert result.stub is True
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/test_sentiment_score.py::test_sentiment_score_marked_as_stub engine/tests/scoring/test_contrarian_signal.py::test_contrarian_signal_marked_as_stub -v`
Expected: FAIL — stub is False by default

**Step 3: Write minimal implementation**

In `engine/src/margin_engine/scoring/quantitative/sentiment_score.py`, change the return (line 67-72):

```python
    return FactorScore(
        name="sentiment",
        raw_value=normalized,
        percentile_rank=0.0,
        detail=detail,
        stub=True,
    )
```

In `engine/src/margin_engine/scoring/quantitative/contrarian_signal.py`, find the FactorScore return and add `stub=True`.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/scoring/test_sentiment_score.py engine/tests/scoring/test_contrarian_signal.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/sentiment_score.py engine/src/margin_engine/scoring/quantitative/contrarian_signal.py engine/tests/scoring/test_sentiment_score.py engine/tests/scoring/test_contrarian_signal.py
git commit -m "fix(engine): mark sentiment and contrarian factors as stubs"
```

---

### Task 4: Add `scoring_version` and `conviction_source` to API response schemas

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py:100-169` (ScoreResponse)
- Modify: `api/src/margin_api/schemas/scores.py:238-249` (PublicScoreResponse)
- Modify: `api/src/margin_api/schemas/score_history.py:10-24` (ScoreHistoryPoint)
- Test: `api/tests/test_schemas.py` or `api/tests/test_backtest_schemas.py` (add new)

**Step 1: Write the failing test**

Create `api/tests/schemas/test_score_schema_v4_fields.py`:

```python
"""Tests for V4 scoring version fields in API schemas."""
import pytest
from margin_api.schemas.scores import ScoreResponse, PublicScoreResponse
from margin_api.schemas.score_history import ScoreHistoryPoint


class TestScoringVersionFields:
    def _minimal_score_response(self, **overrides):
        defaults = {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "score": 75.0,
            "screening_score": 75.0,
            "universe_percentile": 90.0,
            "composite_percentile": 90.0,
            "composite_raw_score": 75.0,
            "composite_tier": "high",
            "signal": "strong",
            "quality": {
                "factor_name": "quality",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 80.0,
            },
            "value": {
                "factor_name": "value",
                "weight": 0.30,
                "sub_scores": [],
                "average_percentile": 70.0,
            },
            "momentum": {
                "factor_name": "momentum",
                "weight": 0.35,
                "sub_scores": [],
                "average_percentile": 75.0,
            },
            "filters_passed": [],
            "data_coverage": 1.0,
            "scoring_version": "v4",
            "conviction_source": "v4_gate_cascade",
        }
        defaults.update(overrides)
        return ScoreResponse(**defaults)

    def test_scoring_version_field_exists(self):
        resp = self._minimal_score_response()
        assert resp.scoring_version == "v4"

    def test_conviction_source_field_exists(self):
        resp = self._minimal_score_response()
        assert resp.conviction_source == "v4_gate_cascade"

    def test_screening_score_alias(self):
        resp = self._minimal_score_response(score=75.0, screening_score=75.0)
        assert resp.screening_score == 75.0

    def test_default_scoring_version(self):
        resp = self._minimal_score_response()
        assert resp.scoring_version == "v4"


class TestPublicScoreV4Fields:
    def test_opportunity_type_field(self):
        resp = PublicScoreResponse(
            ticker="AAPL",
            company_name="Apple Inc",
            composite_score=75.0,
            composite_tier="high",
            signal="strong",
            factor_summary={
                "quality_percentile": 80.0,
                "value_percentile": 70.0,
                "momentum_percentile": 75.0,
            },
            eliminated=False,
            scored_at="2026-03-03T00:00:00Z",
            opportunity_type="compounder",
        )
        assert resp.opportunity_type == "compounder"

    def test_opportunity_type_defaults_none(self):
        resp = PublicScoreResponse(
            ticker="AAPL",
            company_name="Apple Inc",
            composite_score=75.0,
            composite_tier="high",
            signal="strong",
            factor_summary={
                "quality_percentile": 80.0,
                "value_percentile": 70.0,
                "momentum_percentile": 75.0,
            },
            eliminated=False,
            scored_at="2026-03-03T00:00:00Z",
        )
        assert resp.opportunity_type is None


class TestScoreHistoryV4Fields:
    def test_scoring_version_field(self):
        point = ScoreHistoryPoint(
            scored_at="2026-03-03T00:00:00Z",
            score=75.0,
            composite_percentile=90.0,
            composite_tier="high",
            signal="strong",
            scoring_version="v4",
        )
        assert point.scoring_version == "v4"

    def test_scoring_version_defaults_none(self):
        point = ScoreHistoryPoint(
            scored_at="2026-03-03T00:00:00Z",
            score=75.0,
            composite_percentile=90.0,
            composite_tier="high",
            signal="strong",
        )
        assert point.scoring_version is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/schemas/test_score_schema_v4_fields.py -v`
Expected: FAIL — fields don't exist

**Step 3: Write minimal implementation**

In `api/src/margin_api/schemas/scores.py`, add to `ScoreResponse` class (after line 108):

```python
    scoring_version: str = "v4"  # Scoring engine version that produced this result
    conviction_source: str = "v4_gate_cascade"  # Source of conviction tier assignment
    screening_score: float = 0.0  # Alias for score — the additive composite used for sorting
```

In `api/src/margin_api/schemas/scores.py`, add to `PublicScoreResponse` class (after line 248):

```python
    opportunity_type: str | None = None
```

In `api/src/margin_api/schemas/score_history.py`, add to `ScoreHistoryPoint` (after line 24):

```python
    scoring_version: str | None = None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/schemas/test_score_schema_v4_fields.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/scores.py api/src/margin_api/schemas/score_history.py api/tests/schemas/test_score_schema_v4_fields.py
git commit -m "feat(api): add scoring_version, conviction_source, screening_score to schemas"
```

---

### Task 5: Update `_v4_score_response_from_row` to populate new fields

**Files:**
- Modify: `api/src/margin_api/routes/scores.py:194-301` (_v4_score_response_from_row)
- Test: `api/tests/routes/test_scores_v4_fields.py` (new)

**Step 1: Write the failing test**

Create `api/tests/routes/test_scores_v4_fields.py`:

```python
"""Tests for V4 scoring version fields in score route responses."""
import pytest
from unittest.mock import MagicMock
from datetime import datetime, UTC


def _make_v4_row(conviction="exceptional", detail=None):
    """Build a mock V4Score DB row."""
    v4 = MagicMock()
    v4.conviction = conviction
    v4.scored_at = datetime(2026, 3, 3, tzinfo=UTC)
    v4.composite_score = 85.0
    v4.opportunity_type = "compounder"
    v4.timing_signal = "buy_now"
    v4.max_position_pct = 15.0
    v4.ml_alpha = None
    v4.ml_confidence = None
    v4.ml_override = None
    v4.rules_conviction = "exceptional"
    v4.style = "blend"
    v4.regime = "normal"
    v4.track_a = {"conviction": "exceptional", "score": 0.25}
    v4.track_b = {"conviction": "none", "score": 0.0}
    v4.track_c = {"conviction": "medium", "score": 0.1}
    v4.detail = detail or {
        "composite_raw_score": 85.0,
        "composite_percentile": 95.0,
        "quality": {"factor_name": "quality", "weight": 0.35, "sub_scores": [], "average_percentile": 80.0},
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": 70.0},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": 75.0},
        "filters_passed": [],
        "data_coverage": 1.0,
    }

    row = MagicMock()
    row.__getitem__ = lambda self, idx: v4 if idx == 0 else None
    row.ticker = "AAPL"
    row.asset_name = "Apple Inc"
    row.asset_sector = "Technology"
    return row


def test_v4_response_includes_scoring_version():
    from margin_api.routes.scores import _v4_score_response_from_row
    row = _make_v4_row()
    response = _v4_score_response_from_row(row)
    assert response.scoring_version == "v4"


def test_v4_response_includes_conviction_source():
    from margin_api.routes.scores import _v4_score_response_from_row
    row = _make_v4_row()
    response = _v4_score_response_from_row(row)
    assert response.conviction_source == "v4_gate_cascade"


def test_v4_response_screening_score_matches_composite():
    from margin_api.routes.scores import _v4_score_response_from_row
    row = _make_v4_row()
    response = _v4_score_response_from_row(row)
    assert response.screening_score == response.score
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/routes/test_scores_v4_fields.py -v`
Expected: FAIL or default values (scoring_version defaults to "v4" already from schema, but conviction_source and screening_score may not be populated correctly from detail dict)

**Step 3: Write minimal implementation**

In `api/src/margin_api/routes/scores.py`, in the `_v4_score_response_from_row` function, add after the freshness fields block (around line 299):

```python
    # V4 authority fields
    detail["scoring_version"] = "v4"
    detail["conviction_source"] = "v4_gate_cascade"
    detail.setdefault("screening_score", detail.get("score", v4.composite_score))
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/routes/test_scores_v4_fields.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/scores.py api/tests/routes/test_scores_v4_fields.py
git commit -m "feat(api): populate scoring_version and conviction_source in V4 responses"
```

---

### Task 6: Remove V2 Score fallback from `GET /api/v1/scores/{ticker}`

**Files:**
- Modify: `api/src/margin_api/routes/scores.py:517-538`
- Test: `api/tests/routes/test_score_v2_fallback_removed.py` (new)

**Step 1: Write the failing test**

Create `api/tests/routes/test_score_v2_fallback_removed.py`:

```python
"""Tests that GET /scores/{ticker} returns 404 when no V4Score exists, not V2 fallback."""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_no_v4_score_returns_404(app, db_session):
    """When no V4Score exists for a ticker, return 404 instead of falling back to V2."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/scores/NONEXISTENT",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 404
        assert "No score found" in response.json()["detail"]
```

**Step 2: Run test to verify current behavior**

Run: `uv run pytest api/tests/routes/test_score_v2_fallback_removed.py -v`
Expected: The test should already pass (NONEXISTENT ticker has no scores at all). The real change is removing the V2 fallback code path.

**Step 3: Write minimal implementation**

In `api/src/margin_api/routes/scores.py`, replace the V2 fallback block (lines 517-538) with a 404:

```python
    if v4_row is not None:
        # Fetch latest ML model run for metadata
        ml_model_query = select(MlModelRun).order_by(MlModelRun.created_at.desc()).limit(1)
        ml_result = await db.execute(ml_model_query)
        ml_model = ml_result.scalar_one_or_none()

        response = _v4_score_response_from_row(
            v4_row,
            ml_model=ml_model,
            live_price_data=live_price_data,
        )
        row = v4_row
    else:
        # No V4Score found — try unpublished V4
        v4_any_query = (
            select(
                V4Score,
                Asset.ticker,
                Asset.name.label("asset_name"),
                Asset.sector.label("asset_sector"),
                Asset.market_cap.label("asset_market_cap"),
            )
            .join(Asset, V4Score.asset_id == Asset.id)
            .where(Asset.ticker == ticker)
            .order_by(V4Score.scored_at.desc())
            .limit(1)
        )
        v4_any_result = await db.execute(v4_any_query)
        v4_any_row = v4_any_result.first()

        if v4_any_row is not None:
            ml_model_query = select(MlModelRun).order_by(MlModelRun.created_at.desc()).limit(1)
            ml_result = await db.execute(ml_model_query)
            ml_model = ml_result.scalar_one_or_none()

            response = _v4_score_response_from_row(
                v4_any_row,
                ml_model=ml_model,
                live_price_data=live_price_data,
            )
            response.conviction_source = "v4_gate_cascade"
            row = v4_any_row
        else:
            raise HTTPException(status_code=404, detail=f"No score found for {ticker}")
```

**Step 4: Run tests to verify**

Run: `uv run pytest api/tests/routes/ -v -k "score" --ignore=api/tests/routes/test_backtest_endpoints.py`
Expected: All pass. V2 fallback code path is removed.

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/scores.py api/tests/routes/test_score_v2_fallback_removed.py
git commit -m "feat(api): remove V2 Score fallback from GET /scores/{ticker}, V4-only"
```

---

### Task 7: Update `list_scores` to query V4Score table

**Files:**
- Modify: `api/src/margin_api/routes/scores.py:316-359` (list_scores endpoint)
- Test: `api/tests/routes/test_list_scores_v4.py` (new)

**Step 1: Write the failing test**

Create `api/tests/routes/test_list_scores_v4.py`:

```python
"""Tests for list_scores querying V4Score instead of Score table."""
import pytest


def test_list_scores_query_uses_v4score():
    """Verify list_scores endpoint builds query from V4Score table."""
    # This is a structural test — verify the query references V4Score
    from margin_api.routes.scores import list_scores
    import inspect
    source = inspect.getsource(list_scores)
    assert "V4Score" in source, "list_scores should query V4Score table"
    assert "Score.conviction_level" not in source, "Should not filter on V2 conviction_level"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/routes/test_list_scores_v4.py -v`
Expected: FAIL — list_scores still queries Score table

**Step 3: Write minimal implementation**

Replace the `list_scores` function body (lines 316-359) to query V4Score:

```python
@router.get("", response_model=ScoreListResponse)
@limiter.limit("20/minute")
async def list_scores(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    min_percentile: float = Query(0.0, ge=0.0, le=100.0),
    conviction: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> ScoreListResponse:
    """List all scored assets with optional filtering and pagination."""
    # Use V4Score as the source of truth
    latest_v4 = (
        select(
            V4Score.asset_id,
            func.max(V4Score.scored_at).label("max_scored_at"),
        )
        .group_by(V4Score.asset_id)
        .subquery()
    )

    base = (
        select(
            V4Score,
            Asset.ticker,
            Asset.name.label("asset_name"),
            Asset.sector.label("asset_sector"),
        )
        .join(Asset, V4Score.asset_id == Asset.id)
        .join(
            latest_v4,
            (V4Score.asset_id == latest_v4.c.asset_id)
            & (V4Score.scored_at == latest_v4.c.max_scored_at),
        )
    )

    if min_percentile > 0:
        base = base.where(V4Score.composite_score >= min_percentile)
    if conviction:
        base = base.where(V4Score.conviction == conviction.lower())

    # Count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    base = base.order_by(V4Score.composite_score.desc())
    base = base.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(base)
    rows = result.all()

    return ScoreListResponse(
        scores=[_v4_score_response_from_row(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/routes/test_list_scores_v4.py -v`
Expected: PASS

**Step 5: Run existing list_scores tests for regressions**

Run: `uv run pytest api/tests/ -v -k "list_score" --ignore=api/tests/services/test_xbrl_parser.py`
Expected: All pass

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/scores.py api/tests/routes/test_list_scores_v4.py
git commit -m "feat(api): switch list_scores to query V4Score table instead of V2 Score"
```

---

### Task 8: Add `scoring_version` to score history points

**Files:**
- Modify: `api/src/margin_api/routes/scores.py:362-422` (get_score_history)
- Test: existing history tests

**Step 1: Write the failing test**

Add to `api/tests/routes/test_scores_v4_fields.py`:

```python
def test_score_history_includes_scoring_version():
    """Score history points from V2 Score table should be marked as v2."""
    # Structural test: verify the scoring_version field is populated
    from margin_api.schemas.score_history import ScoreHistoryPoint
    point = ScoreHistoryPoint(
        scored_at="2026-03-03T00:00:00Z",
        score=75.0,
        composite_percentile=90.0,
        composite_tier="high",
        signal="strong",
        scoring_version="v2",
    )
    assert point.scoring_version == "v2"
```

**Step 2: Run test to verify it passes** (schema field already added in Task 4)

Run: `uv run pytest api/tests/routes/test_scores_v4_fields.py::test_score_history_includes_scoring_version -v`
Expected: PASS (field exists from Task 4)

**Step 3: Write minimal implementation**

In `api/src/margin_api/routes/scores.py`, in the `get_score_history` function, add `scoring_version="v2"` to the `ScoreHistoryPoint` constructor (around line 402):

```python
        points.append(
            ScoreHistoryPoint(
                scored_at=scored_at,
                score=row.composite_raw_score,
                composite_percentile=row.composite_percentile,
                composite_raw_score=row.composite_raw_score,
                quality_percentile=row.quality_percentile,
                value_percentile=row.value_percentile,
                momentum_percentile=row.momentum_percentile,
                composite_tier=row.conviction_level,
                signal=row.signal,
                margin_invest_value=(
                    float(row.margin_invest_value) if row.margin_invest_value is not None else None
                ),
                buy_price=float(row.buy_price) if row.buy_price is not None else None,
                sell_price=float(row.sell_price) if row.sell_price is not None else None,
                actual_price=float(row.actual_price) if row.actual_price is not None else None,
                delta=delta,
                scoring_version="v2",
            )
        )
```

**Step 4: Commit**

```bash
git add api/src/margin_api/routes/scores.py
git commit -m "feat(api): add scoring_version='v2' to score history points"
```

---

### Task 9: Update public score endpoint to add `opportunity_type`

**Files:**
- Modify: `api/src/margin_api/routes/public_scores.py:85-99`
- Test: `api/tests/routes/test_public_scores_v4.py` (new)

**Step 1: Write the failing test**

Create `api/tests/routes/test_public_scores_v4.py`:

```python
"""Tests for public score endpoint V4 field additions."""
import pytest


def test_public_score_response_includes_opportunity_type():
    """PublicScoreResponse should include opportunity_type from V4Score."""
    from margin_api.schemas.scores import PublicScoreResponse
    resp = PublicScoreResponse(
        ticker="AAPL",
        company_name="Apple Inc",
        composite_score=85.0,
        composite_tier="exceptional",
        signal="strong",
        factor_summary={
            "quality_percentile": 80.0,
            "value_percentile": 90.0,
            "momentum_percentile": 75.0,
        },
        eliminated=False,
        scored_at="2026-03-03T00:00:00Z",
        opportunity_type="compounder",
    )
    data = resp.model_dump()
    assert data["opportunity_type"] == "compounder"
```

**Step 2: Run test to verify**

Run: `uv run pytest api/tests/routes/test_public_scores_v4.py -v`
Expected: PASS (field added in Task 4)

**Step 3: Write minimal implementation**

In `api/src/margin_api/routes/public_scores.py`, update the V4 response construction (around line 85-95) to include `opportunity_type`:

```python
        data = PublicScoreResponse(
            ticker=row.ticker,
            company_name=row.asset_name or "",
            composite_score=v4.composite_score,
            composite_tier=v4.conviction,
            signal=signal,
            factor_summary=factor_summary,
            eliminated=eliminated,
            elimination_reason=elimination_reason,
            scored_at=scored_at.isoformat() if scored_at else "",
            opportunity_type=v4.opportunity_type,
        )
```

**Step 4: Commit**

```bash
git add api/src/margin_api/routes/public_scores.py api/tests/routes/test_public_scores_v4.py
git commit -m "feat(api): include opportunity_type in public score endpoint"
```

---

### Task 10: Add deprecation header to V3 score routes

**Files:**
- Modify: `api/src/margin_api/routes/v3_scores.py`
- Test: `api/tests/routes/test_v3_deprecation.py` (new)

**Step 1: Write the failing test**

Create `api/tests/routes/test_v3_deprecation.py`:

```python
"""Tests for V3 routes deprecation header."""
import pytest


def test_v3_routes_have_deprecation_markers():
    """V3 score routes should include deprecation notice in docstrings."""
    from margin_api.routes.v3_scores import list_v3_scores, get_v3_score
    assert "deprecated" in list_v3_scores.__doc__.lower()
    assert "deprecated" in get_v3_score.__doc__.lower()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/routes/test_v3_deprecation.py -v`
Expected: FAIL — docstrings don't mention deprecation

**Step 3: Write minimal implementation**

In `api/src/margin_api/routes/v3_scores.py`, update the endpoint functions:

For `list_v3_scores` (line 54), change docstring to:
```python
    """List latest v3 scores. DEPRECATED: Use GET /api/v1/scores instead."""
```

For `get_v3_score` (line 104), change docstring to:
```python
    """Get the latest v3 score for a specific ticker. DEPRECATED: Use GET /api/v1/scores/{ticker} instead."""
```

Add a `Deprecation` response header by wrapping the response. At the top of the file, add `from fastapi.responses import JSONResponse`, then modify both endpoints to return responses with headers:

```python
@router.get("", response_model=V3ScoreListResponse)
async def list_v3_scores(
    conviction: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """List latest v3 scores. DEPRECATED: Use GET /api/v1/scores instead."""
    # ... existing logic ...
    result_data = V3ScoreListResponse(scores=scores, total=len(scores))
    return JSONResponse(
        content=result_data.model_dump(),
        headers={
            "Deprecation": "true",
            "Sunset": "2026-06-01",
            "Link": '</api/v1/scores>; rel="successor-version"',
        },
    )
```

Apply the same pattern to `get_v3_score`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/routes/test_v3_deprecation.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/v3_scores.py api/tests/routes/test_v3_deprecation.py
git commit -m "feat(api): add deprecation headers to V3 score routes"
```

---

### Task 11: Add calibration status endpoint

**Files:**
- Create: `api/src/margin_api/schemas/calibration.py`
- Modify: `api/src/margin_api/routes/backtest.py` (add new endpoint)
- Test: `api/tests/routes/test_calibration_status.py` (new)

**Step 1: Write the failing test**

Create `api/tests/routes/test_calibration_status.py`:

```python
"""Tests for calibration status endpoint."""
import pytest
from margin_api.schemas.calibration import CalibrationStatusResponse


class TestCalibrationStatusSchema:
    def test_schema_construction(self):
        status = CalibrationStatusResponse(
            pit_data_available=False,
            pit_date_range_start=None,
            pit_date_range_end=None,
            pit_ticker_count=0,
            last_backtest_run=None,
            validation_passed=None,
            validation_details=None,
            current_thresholds={
                "track_a": {
                    "exceptional_power": 0.15,
                    "exceptional_moat": 3,
                    "exceptional_gap": 0.08,
                },
                "track_b": {
                    "exceptional_asymmetry": 5.0,
                    "exceptional_catalyst": 55.0,
                },
            },
            scoring_version="v4",
        )
        assert status.pit_data_available is False
        assert status.pit_ticker_count == 0
        assert status.scoring_version == "v4"

    def test_schema_with_data(self):
        status = CalibrationStatusResponse(
            pit_data_available=True,
            pit_date_range_start="2009-01-01",
            pit_date_range_end="2025-12-31",
            pit_ticker_count=523,
            last_backtest_run="2026-03-03T00:00:00Z",
            validation_passed=True,
            validation_details={
                "excess_cagr": {"value": 5.2, "threshold": 3.0, "passed": True},
                "sharpe_ratio": {"value": 0.85, "threshold": 0.7, "passed": True},
            },
            current_thresholds={
                "track_a": {"exceptional_power": 0.15},
                "track_b": {"exceptional_asymmetry": 5.0},
            },
            scoring_version="v4",
        )
        assert status.pit_data_available is True
        assert status.pit_ticker_count == 523
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/routes/test_calibration_status.py -v`
Expected: FAIL — module does not exist

**Step 3: Write minimal implementation**

Create `api/src/margin_api/schemas/calibration.py`:

```python
"""Calibration status response schema."""
from __future__ import annotations

from pydantic import BaseModel


class CalibrationStatusResponse(BaseModel):
    """Current calibration status of the scoring engine."""

    pit_data_available: bool
    pit_date_range_start: str | None = None
    pit_date_range_end: str | None = None
    pit_ticker_count: int = 0
    last_backtest_run: str | None = None
    validation_passed: bool | None = None
    validation_details: dict | None = None
    current_thresholds: dict
    scoring_version: str = "v4"
```

In `api/src/margin_api/routes/backtest.py`, add the endpoint:

```python
from margin_api.schemas.calibration import CalibrationStatusResponse

@router.get("/calibration-status", response_model=CalibrationStatusResponse)
async def get_calibration_status(
    db: AsyncSession = Depends(get_db),
) -> CalibrationStatusResponse:
    """Return current calibration status: PIT data coverage, last backtest, validation results."""
    from sqlalchemy import func, select
    from margin_api.db.models import PITFinancialSnapshot, PITDailyPrice, BacktestRun

    # Check PIT data availability
    pit_count_q = select(func.count(func.distinct(PITFinancialSnapshot.ticker)))
    pit_count = (await db.execute(pit_count_q)).scalar() or 0

    pit_range_q = select(
        func.min(PITFinancialSnapshot.as_of_date),
        func.max(PITFinancialSnapshot.as_of_date),
    )
    pit_range = (await db.execute(pit_range_q)).first()
    pit_start = pit_range[0].isoformat() if pit_range and pit_range[0] else None
    pit_end = pit_range[1].isoformat() if pit_range and pit_range[1] else None

    # Latest backtest run
    bt_q = select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(1)
    bt_result = await db.execute(bt_q)
    bt_run = bt_result.scalar_one_or_none()

    # Current thresholds
    from margin_engine.config.threshold_config import ThresholdConfig
    config = ThresholdConfig()

    return CalibrationStatusResponse(
        pit_data_available=pit_count > 0,
        pit_date_range_start=pit_start,
        pit_date_range_end=pit_end,
        pit_ticker_count=pit_count,
        last_backtest_run=bt_run.created_at.isoformat() if bt_run else None,
        validation_passed=None,  # Populated after first real backtest
        validation_details=None,
        current_thresholds={
            "track_a": config.track_a.model_dump(),
            "track_b": config.track_b.model_dump(),
            "hysteresis_buffer": config.hysteresis_buffer,
        },
        scoring_version="v4",
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/routes/test_calibration_status.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/calibration.py api/src/margin_api/routes/backtest.py api/tests/routes/test_calibration_status.py
git commit -m "feat(api): add GET /backtest/calibration-status endpoint"
```

---

### Task 12: Update frontend TypeScript types

**Files:**
- Modify: `web/src/lib/api/types.ts:47-117` (ScoreResponse interface)
- Test: `cd web && npx vitest run` (ensure no type errors)

**Step 1: Add new fields to ScoreResponse interface**

In `web/src/lib/api/types.ts`, add to the `ScoreResponse` interface after line 54 (`composite_tier: string`):

```typescript
  scoring_version: string       // "v4" — which scoring engine produced this
  conviction_source: string     // "v4_gate_cascade" or "v1_percentile_threshold"
  screening_score: number       // Additive composite used for sorting (alias for score)
```

**Step 2: Add CalibrationStatus type**

After the `ScoreListResponse` interface (line 124), add:

```typescript
export interface CalibrationStatus {
  pit_data_available: boolean
  pit_date_range_start: string | null
  pit_date_range_end: string | null
  pit_ticker_count: number
  last_backtest_run: string | null
  validation_passed: boolean | null
  validation_details: Record<string, { value: number; threshold: number; passed: boolean }> | null
  current_thresholds: Record<string, unknown>
  scoring_version: string
}
```

**Step 3: Add scoring_version to ScoreHistoryPoint**

Find or create the ScoreHistoryPoint type and add:

```typescript
export interface ScoreHistoryPoint {
  // ... existing fields ...
  scoring_version?: string | null
}
```

**Step 4: Run frontend tests**

Run: `cd web && npx vitest run`
Expected: All pass (new optional fields don't break existing consumers)

**Step 5: Commit**

```bash
git add web/src/lib/api/types.ts
git commit -m "feat(web): add scoring_version, conviction_source, CalibrationStatus types"
```

---

### Task 13: Final integration test pass

**Files:**
- No new files — run existing test suites

**Step 1: Run engine tests**

Run: `uv run pytest engine/tests/ -v --tb=short`
Expected: All pass (~2621 tests)

**Step 2: Run API tests**

Run: `uv run pytest api/tests/ -v --tb=short --ignore=api/tests/services/test_xbrl_parser.py`
Expected: All pass (~1587 tests)

**Step 3: Run web tests**

Run: `cd web && npx vitest run`
Expected: All pass (~1285 tests)

**Step 4: Final commit with all clean**

If any test failures were found and fixed during this task, commit the fixes:

```bash
git add -A
git commit -m "fix: resolve integration test issues from scoring engine audit Phase 1"
```
