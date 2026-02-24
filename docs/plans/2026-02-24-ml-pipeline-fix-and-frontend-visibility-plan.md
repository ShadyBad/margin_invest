# ML Pipeline Fix & Frontend Visibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix ML training data quality, cut the API over to V4Score with graceful fallback, and add an ML Audit Panel to the asset detail page.

**Architecture:** Backend-first. Fix training quality (real JSONB unpacking, remove phantom percentiles), wire API to V4Score, expose ML fields, then build frontend components. Each layer is testable in isolation.

**Tech Stack:** Python 3.13, SQLAlchemy 2.0, FastAPI, Pydantic, Next.js 15, React 19, Tailwind v4, Vitest

**Design doc:** `docs/plans/2026-02-24-ml-pipeline-fix-and-frontend-visibility-design.md`

---

## Task 1: Remove Phantom Percentiles from Track B Cascade

**Files:**
- Modify: `engine/src/margin_engine/scoring/v3_cascade.py:182-197` (TrackBInputs)
- Modify: `engine/src/margin_engine/scoring/v3_cascade.py:282-288` (catalyst computation)
- Modify: `engine/src/margin_engine/scoring/v3_intermediates.py:187-201` (compute_catalyst_strength)
- Modify: `engine/src/margin_engine/scoring/v4_pipeline.py:44-61` (TickerV4Data)
- Modify: `engine/src/margin_engine/scoring/v4_pipeline.py:270-284` (TrackBInputs construction)
- Modify: `api/src/margin_api/cli.py:1268-1288` (run_scoring_v4 TickerV4Data construction)
- Test: `engine/tests/scoring/test_v3_cascade.py` (existing Track B tests)

**Step 1: Write failing test for catalyst_strength without insider/institutional**

In `engine/tests/scoring/test_v3_intermediates.py`, add:

```python
def test_compute_catalyst_strength_sue_only():
    """Catalyst strength uses only SUE when insider/institutional removed."""
    from margin_engine.scoring.v3_intermediates import compute_catalyst_strength
    result = compute_catalyst_strength(sue_percentile=80.0)
    assert result == 80.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/test_v3_intermediates.py::test_compute_catalyst_strength_sue_only -v`
Expected: FAIL (TypeError: missing required arguments)

**Step 3: Update compute_catalyst_strength to use only SUE**

In `engine/src/margin_engine/scoring/v3_intermediates.py:187-201`, change:

```python
def compute_catalyst_strength(
    sue_percentile: float,
) -> float:
    """Catalyst strength = SUE percentile.

    Previously blended insider, institutional, and SUE percentiles.
    Insider and institutional data sources are not yet available,
    so catalyst strength is driven solely by SUE until a 13F pipeline exists.
    """
    return sue_percentile
```

**Step 4: Remove insider_percentile and institutional_percentile from TrackBInputs**

In `engine/src/margin_engine/scoring/v3_cascade.py:182-197`, remove the two fields:

```python
class TrackBInputs(BaseModel):
    """All inputs needed to run the Track B (Mispricing) gate cascade."""

    history: FinancialHistory
    period: FinancialPeriod
    profile: AssetProfile
    current_price: float
    dcf_iv: float
    owner_earnings_iv: float
    asset_floor_iv: float
    peer_comparison_iv: float
    sue_percentile: float
    wacc: float
    regime_adjustments: RegimeAdjustments | None = None
```

Update the catalyst computation call at line 284:

```python
    catalyst = compute_catalyst_strength(
        sue_percentile=inputs.sue_percentile,
    )
```

**Step 5: Remove from TickerV4Data**

In `engine/src/margin_engine/scoring/v4_pipeline.py:44-61`, remove lines 58-59:

```python
    insider_percentile: float = 0.0
    institutional_percentile: float = 0.0
```

Update TrackBInputs construction at lines 270-284, removing the two fields:

```python
        track_b_inputs = TrackBInputs(
            history=td.history,
            period=td.latest_period,
            profile=td.profile,
            current_price=td.current_price,
            dcf_iv=td.dcf_iv,
            owner_earnings_iv=owner_earnings_iv,
            asset_floor_iv=asset_floor_iv,
            peer_comparison_iv=peer_comparison_iv,
            sue_percentile=td.sue_percentile,
            wacc=wacc,
            regime_adjustments=adj,
        )
```

**Step 6: Remove from CLI**

In `api/src/margin_api/cli.py`, remove `insider_percentile=50.0` and `institutional_percentile=50.0` from the TickerV4Data construction (around lines 1280-1281).

**Step 7: Fix all existing tests that pass insider/institutional**

Search for `insider_percentile` and `institutional_percentile` in all test files. Remove these kwargs from any TrackBInputs or TickerV4Data construction. Also remove from any compute_catalyst_strength calls.

Run: `uv run pytest engine/tests/ -v -x`

**Step 8: Run full test suite**

Run: `uv run pytest engine/tests/ -v`
Expected: All pass

**Step 9: Commit**

```
feat(engine): remove phantom insider/institutional percentiles from scoring

These fields were hardcoded at 50.0 with no data source, silently
neutering the Track B catalyst gate. Catalyst strength now uses
SUE percentile only. Fields will return when a 13F pipeline exists.
```

---

## Task 2: Fix ML Training Data Quality — Real JSONB Unpacking

**Files:**
- Modify: `api/src/margin_api/workers.py:879-899` (train_ml_models stub reconstruction)
- Test: `api/tests/workers/test_train_ml_models.py` or nearest existing test

**Step 1: Write test for real factor unpacking**

In `api/tests/workers/test_ml_training.py` (create if needed):

```python
"""Tests for ML training data quality."""

import pytest
from margin_engine.models.scoring import CompositeScore, FactorBreakdown, FactorScore, FilterResult


def test_composite_from_score_detail_has_real_percentiles():
    """CompositeScore reconstructed from JSONB should have real sub_scores, not stubs."""
    score_detail = {
        "ticker": "AAPL",
        "composite_percentile": 85.0,
        "composite_raw_score": 78.0,
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [
                {"name": "roe", "raw_value": 0.45, "percentile_rank": 90.0},
                {"name": "roic", "raw_value": 0.30, "percentile_rank": 80.0},
            ],
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [
                {"name": "ev_ebit", "raw_value": 15.0, "percentile_rank": 60.0},
            ],
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [
                {"name": "price_momentum", "raw_value": 0.12, "percentile_rank": 70.0},
            ],
        },
        "filters_passed": [{"name": "market_cap", "passed": True}],
        "data_coverage": 0.95,
    }

    from margin_api.workers import _composite_from_score_detail

    composite = _composite_from_score_detail("AAPL", score_detail)
    assert composite is not None
    assert composite.quality.sub_scores[0].percentile_rank == 90.0
    assert composite.quality.sub_scores[0].raw_value == 0.45
    assert composite.value.sub_scores[0].percentile_rank == 60.0
    assert composite.momentum.sub_scores[0].percentile_rank == 70.0


def test_composite_from_score_detail_skips_malformed():
    """Malformed JSONB should return None, not a stub."""
    from margin_api.workers import _composite_from_score_detail

    result = _composite_from_score_detail("BAD", {})
    assert result is None

    result2 = _composite_from_score_detail("BAD", {"quality": "not_a_dict"})
    assert result2 is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/workers/test_ml_training.py -v`
Expected: FAIL (ImportError: cannot import _composite_from_score_detail)

**Step 3: Implement _composite_from_score_detail helper**

In `api/src/margin_api/workers.py`, add a new function near the top of the `train_ml_models` function (or as a module-level helper):

```python
def _composite_from_score_detail(
    ticker: str, detail: dict
) -> CompositeScore | None:
    """Reconstruct a CompositeScore from score_detail JSONB.

    Returns None if the JSONB is missing required pillar breakdowns.
    """
    try:
        def _parse_breakdown(data: dict) -> FactorBreakdown:
            return FactorBreakdown(
                factor_name=data["factor_name"],
                weight=data.get("weight", 1.0),
                sub_scores=[
                    FactorScore(
                        name=s["name"],
                        raw_value=s.get("raw_value", 0.0),
                        percentile_rank=s.get("percentile_rank", 0.0),
                    )
                    for s in data.get("sub_scores", [])
                ],
            )

        quality_data = detail.get("quality")
        value_data = detail.get("value")
        momentum_data = detail.get("momentum")

        if not all(isinstance(d, dict) for d in [quality_data, value_data, momentum_data]):
            return None

        # Optional pillars
        kwargs = {}
        for key in ("growth", "capital_allocation", "catalyst"):
            pillar_data = detail.get(key)
            if isinstance(pillar_data, dict) and "sub_scores" in pillar_data:
                kwargs[key] = _parse_breakdown(pillar_data)

        return CompositeScore(
            ticker=ticker,
            composite_percentile=detail.get("composite_percentile", 0.0),
            composite_raw_score=detail.get("composite_raw_score", 0.0),
            quality=_parse_breakdown(quality_data),
            value=_parse_breakdown(value_data),
            momentum=_parse_breakdown(momentum_data),
            filters_passed=[
                FilterResult(name=f.get("name", ""), passed=f.get("passed", True))
                for f in detail.get("filters_passed", [])
            ],
            data_coverage=detail.get("data_coverage", 1.0),
            **kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return None
```

**Step 4: Replace stub reconstruction in train_ml_models**

In `train_ml_models`, replace the stub FactorBreakdown block (lines 879-895) with:

```python
        composite = _composite_from_score_detail(ticker, score.score_detail or {})
        if composite is None:
            skipped += 1
            continue
        composites.append(composite)
```

Add a `skipped = 0` counter before the loop and log it after:

```python
    logger.info("ML training: %d composites built, %d skipped (malformed JSONB)", len(composites), skipped)
```

**Step 5: Run tests**

Run: `uv run pytest api/tests/workers/test_ml_training.py -v`
Expected: PASS

**Step 6: Run full API test suite**

Run: `uv run pytest api/tests/ -v`
Expected: All pass (existing mocks may need adjustment if they relied on stub behavior)

**Step 7: Commit**

```
fix(ml): unpack real factor scores from JSONB instead of stubs

train_ml_models was building feature matrices from stub
FactorBreakdowns (all 50th percentile), making ML models train
on meaningless data. Now parses real sub_scores from score_detail
JSONB. Malformed entries are skipped instead of injecting stubs.
```

---

## Task 3: Fix composite_score and sustainable_growth_rate

**Files:**
- Modify: `engine/src/margin_engine/scoring/v4_pipeline.py:348-363` (composite_score computation)
- Modify: `api/src/margin_api/cli.py:1275` (sustainable_growth_rate)
- Test: `engine/tests/scoring/test_v4_pipeline.py`

**Step 1: Write failing test for composite_score**

In `engine/tests/scoring/test_v4_pipeline.py`, add:

```python
def test_v4_result_composite_score_not_zero():
    """V4ResultWithML should have a non-zero composite_score from winning track."""
    # Use an existing test fixture that builds TickerV4Data
    # Score a single ticker and verify composite_score > 0
    results = score_universe_v4([make_ticker_v4_data("TEST")], shiller_cape=25.0)
    assert len(results) == 1
    # composite_score should reflect the winning track's gate score
    assert results[0].composite_score > 0.0
```

(Adapt to use existing test helpers for building TickerV4Data fixtures.)

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/scoring/test_v4_pipeline.py::test_v4_result_composite_score_not_zero -v`
Expected: FAIL (composite_score == 0.0)

**Step 3: Implement composite_score computation**

In `engine/src/margin_engine/scoring/v4_pipeline.py`, after `v4_result = orchestrate_v4(...)` (line 310), compute:

```python
        # Compute composite_score from winning track's score
        track_scores = {
            "compounder": track_a.score if track_a.qualifies else 0.0,
            "mispricing": track_b.score if track_b.qualifies else 0.0,
            "efficient_growth": track_c.score if track_c.qualifies else 0.0,
        }
        composite_score = max(track_scores.values())
```

Then set it in the V4ResultWithML construction (line 348):

```python
                composite_score=composite_score,
```

**Step 4: Fix sustainable_growth_rate in CLI**

In `api/src/margin_api/cli.py`, replace the hardcoded `sustainable_growth_rate=0.08` with a computation:

```python
        # Compute sustainable growth rate = retention_ratio * ROE
        # Fallback to 0.08 if data is missing
        net_income = float(latest.current_income.net_income or 0)
        total_equity = float(latest.current_balance.total_equity or 0)
        dividends = float(latest.current_cash_flow.dividends_paid or 0)
        if net_income > 0 and total_equity > 0:
            roe = net_income / total_equity
            retention = 1.0 - (abs(dividends) / net_income) if net_income > 0 else 1.0
            retention = max(0.0, min(1.0, retention))
            sustainable_growth = retention * roe
        else:
            sustainable_growth = 0.08
```

Then use `sustainable_growth_rate=sustainable_growth` in the TickerV4Data construction.

**Step 5: Run tests**

Run: `uv run pytest engine/tests/scoring/test_v4_pipeline.py -v`
Expected: All pass

**Step 6: Commit**

```
fix(engine): compute composite_score and sustainable_growth_rate from real data

composite_score was always 0.0 — now uses the winning track's gate
score. sustainable_growth_rate was hardcoded 0.08 — now computed as
retention_ratio * ROE with fallback.
```

---

## Task 4: Add ML Fields to API Schemas

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py:68-115` (ScoreResponse)
- Modify: `api/src/margin_api/schemas/dashboard.py:10-41` (PickSummary)
- Modify: `web/src/lib/api/types.ts:46-88` (ScoreResponse interface)
- Modify: `web/src/lib/api/types.ts:115-146` (PickSummary interface)
- Test: `api/tests/schemas/test_score_response.py` or existing schema tests

**Step 1: Write test for new ML fields on ScoreResponse**

In `api/tests/schemas/test_scores.py` (create if needed):

```python
def test_score_response_includes_ml_fields():
    """ScoreResponse should accept and serialize ML fields."""
    from margin_api.schemas.scores import ScoreResponse, FactorBreakdownResponse

    resp = ScoreResponse(
        ticker="AAPL",
        composite_percentile=85.0,
        conviction_level="high",
        signal="buy",
        quality=FactorBreakdownResponse(factor_name="quality", weight=0.35, sub_scores=[], average_percentile=80.0),
        value=FactorBreakdownResponse(factor_name="value", weight=0.30, sub_scores=[], average_percentile=70.0),
        momentum=FactorBreakdownResponse(factor_name="momentum", weight=0.35, sub_scores=[], average_percentile=75.0),
        filters_passed=[],
        data_coverage=0.95,
        # ML fields
        ml_alpha=0.034,
        ml_confidence=0.81,
        ml_override="promoted",
        rules_conviction="medium",
        style="growth",
        regime="normal",
        ml_model_qualified=True,
        ml_model_rank_ic=0.19,
        ml_model_trained_at="2026-02-22T02:00:00Z",
    )
    data = resp.model_dump()
    assert data["ml_alpha"] == 0.034
    assert data["ml_override"] == "promoted"
    assert data["rules_conviction"] == "medium"
    assert data["style"] == "growth"
    assert data["ml_model_qualified"] is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/schemas/test_scores.py::test_score_response_includes_ml_fields -v`
Expected: FAIL (unexpected keyword argument 'ml_alpha')

**Step 3: Add ML fields to ScoreResponse**

In `api/src/margin_api/schemas/scores.py`, after the asset context fields (line 112), add:

```python
    # V4 / ML fields
    ml_alpha: float | None = None
    ml_confidence: float | None = None
    ml_override: str | None = None
    rules_conviction: str | None = None
    style: str | None = None
    regime: str | None = None
    track_a: dict | None = None
    track_b: dict | None = None
    track_c: dict | None = None
    ml_model_qualified: bool | None = None
    ml_model_rank_ic: float | None = None
    ml_model_trained_at: str | None = None
```

**Step 4: Add ML fields to PickSummary**

In `api/src/margin_api/schemas/dashboard.py`, after `price_target_invalid_reason` (line 41), add:

```python
    # V4 / ML fields
    ml_override: str | None = None
    style: str | None = None
```

**Step 5: Add ML fields to TypeScript ScoreResponse**

In `web/src/lib/api/types.ts`, after the asset context fields (line 87), add:

```typescript
  // V4 / ML fields
  ml_alpha?: number | null
  ml_confidence?: number | null
  ml_override?: string | null
  rules_conviction?: string | null
  style?: string | null
  regime?: string | null
  track_a?: Record<string, unknown> | null
  track_b?: Record<string, unknown> | null
  track_c?: Record<string, unknown> | null
  ml_model_qualified?: boolean | null
  ml_model_rank_ic?: number | null
  ml_model_trained_at?: string | null
```

**Step 6: Add ML fields to TypeScript PickSummary**

In `web/src/lib/api/types.ts`, after `price_target_invalid_reason` (line 145), add:

```typescript
  // V4 / ML fields
  ml_override?: string | null
  style?: string | null
```

**Step 7: Run tests**

Run: `uv run pytest api/tests/schemas/ -v`
Expected: All pass

**Step 8: Commit**

```
feat(api): add ML fields to ScoreResponse and PickSummary schemas

Adds ml_alpha, ml_confidence, ml_override, rules_conviction, style,
regime, track details, and model metadata to ScoreResponse. Adds
ml_override and style to PickSummary. All nullable for backwards
compatibility. TypeScript types mirrored.
```

---

## Task 5: Wire API Score Endpoint to V4Score with Fallback

**Files:**
- Modify: `api/src/margin_api/routes/scores.py:1-22` (imports)
- Modify: `api/src/margin_api/routes/scores.py:25-190` (_score_response_from_row)
- Modify: `api/src/margin_api/routes/scores.py:354-432` (get_score endpoint)
- Test: `api/tests/routes/test_scores.py`

**Step 1: Write test for V4 score serving**

In `api/tests/routes/test_scores_v4.py` (create):

```python
"""Tests for V4Score serving via the score endpoint."""

import pytest
from datetime import datetime, UTC
from httpx import AsyncClient


@pytest.mark.anyio
async def test_get_score_returns_v4_data_when_available(client: AsyncClient, seed_v4_score):
    """GET /api/v1/scores/AAPL returns V4Score data with ML fields."""
    resp = await client.get("/api/v1/scores/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ml_override"] is not None
    assert data["style"] is not None
    assert data["rules_conviction"] is not None


@pytest.mark.anyio
async def test_get_score_falls_back_to_v2_when_no_v4(client: AsyncClient, seed_v2_score_only):
    """GET /api/v1/scores/MSFT falls back to Score table when no V4Score exists."""
    resp = await client.get("/api/v1/scores/MSFT")
    assert resp.status_code == 200
    data = resp.json()
    # ML fields should be null in fallback
    assert data["ml_override"] is None
    assert data["style"] is None


@pytest.mark.anyio
async def test_get_score_includes_ml_model_metadata(client: AsyncClient, seed_v4_score, seed_ml_model_run):
    """GET /api/v1/scores/AAPL includes ML model training metadata."""
    resp = await client.get("/api/v1/scores/AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ml_model_qualified"] is not None
    assert data["ml_model_rank_ic"] is not None
```

(The fixtures `seed_v4_score`, `seed_v2_score_only`, `seed_ml_model_run` will need to be created in conftest.py — they insert rows into the V4Score, Score, and MlModelRun tables respectively.)

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/routes/test_scores_v4.py -v`
Expected: FAIL (ml_override is None even with V4Score data)

**Step 3: Update get_score endpoint to query V4Score first**

In `api/src/margin_api/routes/scores.py`, add V4Score and MlModelRun imports:

```python
from margin_api.db.models import Asset, Score, V4Score, MlModelRun
```

In the `get_score` endpoint, before the existing Score query, try V4Score first:

```python
    # Try V4Score first
    v4_query = (
        select(V4Score, Asset.ticker, Asset.name.label("asset_name"), Asset.sector.label("asset_sector"))
        .join(Asset, V4Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .order_by(V4Score.scored_at.desc())
        .limit(1)
    )
    v4_result = await db.execute(v4_query)
    v4_row = v4_result.first()

    # Fetch latest ML model metadata (regardless of V4/V2 path)
    ml_model_query = (
        select(MlModelRun)
        .order_by(MlModelRun.created_at.desc())
        .limit(1)
    )
    ml_result = await db.execute(ml_model_query)
    ml_model = ml_result.scalar_one_or_none()

    if v4_row is not None:
        response = _v4_score_response_from_row(v4_row, ml_model, live_price_data)
    else:
        # Fallback to V2/V3 Score table
        # ... existing query logic ...
        response = _score_response_from_row(row, live_price_data)
```

**Step 4: Implement _v4_score_response_from_row**

Add a new function that builds ScoreResponse from a V4Score row:

```python
def _v4_score_response_from_row(
    row,
    ml_model: MlModelRun | None = None,
    live_price_data: dict | None = None,
) -> ScoreResponse:
    """Build a ScoreResponse from a V4Score DB row."""
    v4 = row[0] if hasattr(row[0], "conviction") else row.V4Score
    ticker = row.ticker if hasattr(row, "ticker") else row[1]
    asset_name = row.asset_name if hasattr(row, "asset_name") else ""

    scored_at = v4.scored_at
    if scored_at is not None and scored_at.tzinfo is None:
        scored_at = scored_at.replace(tzinfo=UTC)
    freshness = compute_freshness(scored_at)

    detail = v4.detail or {}

    # Build factor breakdowns from V4 detail JSONB (same pattern as v2)
    def _build_factor(key: str, default_weight: float) -> FactorBreakdownResponse:
        factor = detail.get(key, {})
        if isinstance(factor, dict):
            subs = factor.get("sub_scores", [])
            avg = sum(s.get("percentile_rank", 0) for s in subs) / len(subs) if subs else 0.0
            return FactorBreakdownResponse(
                factor_name=key,
                weight=factor.get("weight", default_weight),
                sub_scores=[
                    FactorScoreResponse(
                        name=s.get("name", ""),
                        raw_value=s.get("raw_value", 0.0),
                        percentile_rank=s.get("percentile_rank", 0.0),
                        detail=s.get("detail", ""),
                    )
                    for s in subs
                ],
                average_percentile=avg,
            )
        return FactorBreakdownResponse(
            factor_name=key, weight=default_weight, sub_scores=[], average_percentile=0.0
        )

    actual_price = detail.get("actual_price")
    if live_price_data:
        actual_price = live_price_data["price"]
        price_source = "live"
        price_updated_at = live_price_data.get("updated_at")
    else:
        price_source = "daily_close"
        price_updated_at = scored_at.isoformat() if scored_at else None

    miv = detail.get("margin_invest_value")
    invalid_reason = detail.get("price_target_invalid_reason")

    return ScoreResponse(
        ticker=ticker,
        name=asset_name,
        score=v4.composite_score,
        universe_percentile=detail.get("composite_percentile", 0.0),
        composite_percentile=detail.get("composite_percentile", 0.0),
        composite_raw_score=v4.composite_score,
        conviction_level=v4.conviction,
        signal=detail.get("signal", "no_action"),
        quality=_build_factor("quality", 0.35),
        value=_build_factor("value", 0.30),
        momentum=_build_factor("momentum", 0.35),
        filters_passed=[
            FilterResultResponse(
                name=f.get("name", ""),
                passed=f.get("passed", True),
                value=f.get("value"),
                threshold=f.get("threshold"),
                detail=f.get("detail", ""),
                verdict=f.get("verdict", "pass" if f.get("passed") else "fail"),
                missing_fields=f.get("missing_fields"),
            )
            for f in detail.get("filters_passed", [])
        ],
        data_coverage=detail.get("data_coverage", 1.0),
        growth_stage=detail.get("growth_stage"),
        scored_at=scored_at.isoformat() if scored_at else None,
        margin_invest_value=miv,
        buy_price=detail.get("buy_price"),
        sell_price=detail.get("sell_price"),
        actual_price=actual_price,
        price_upside=(
            round((miv - actual_price) / actual_price, 4)
            if miv and actual_price and not invalid_reason
            else None
        ),
        margin_of_safety=(
            round((miv - actual_price) / miv, 4)
            if miv and actual_price and actual_price < miv and not invalid_reason
            else None
        ),
        price_target_invalid_reason=invalid_reason,
        opportunity_type=v4.opportunity_type,
        winning_track=detail.get("winning_track"),
        asymmetry_ratio=detail.get("asymmetry_ratio"),
        max_position_pct=v4.max_position_pct,
        timing_signal=v4.timing_signal,
        capital_allocation=_build_factor("capital_allocation", 1.0) if detail.get("capital_allocation") else None,
        catalyst=_build_factor("catalyst", 1.0) if detail.get("catalyst") else None,
        data_freshness=freshness,
        price_source=price_source,
        price_updated_at=price_updated_at,
        # V4 / ML fields
        ml_alpha=v4.ml_alpha,
        ml_confidence=v4.ml_confidence,
        ml_override=v4.ml_override,
        rules_conviction=v4.rules_conviction,
        style=v4.style,
        regime=getattr(v4, "regime", None),
        track_a=v4.track_a,
        track_b=v4.track_b,
        track_c=v4.track_c,
        ml_model_qualified=ml_model.model_qualifies if ml_model else None,
        ml_model_rank_ic=ml_model.overall_rank_ic if ml_model else None,
        ml_model_trained_at=ml_model.created_at.isoformat() if ml_model else None,
    )
```

**Step 5: Run tests**

Run: `uv run pytest api/tests/routes/test_scores_v4.py -v`
Expected: All pass

Run: `uv run pytest api/tests/ -v`
Expected: All pass (existing tests still work with fallback path)

**Step 6: Commit**

```
feat(api): wire score endpoint to V4Score with per-ticker fallback

GET /scores/{ticker} now queries V4Score first. If found, builds
response with ML fields (alpha, confidence, override, model metadata).
Falls back to Score table (v2) if no V4Score exists for the ticker.
```

---

## Task 6: Wire Dashboard PickSummary to V4Score

**Files:**
- Modify: `api/src/margin_api/routes/dashboard.py:1-21` (imports)
- Modify: `api/src/margin_api/routes/dashboard.py:25-90` (_pick_summary_from_row)
- Modify: `api/src/margin_api/routes/dashboard.py:105-151` (_fetch_picks_and_watchlist)
- Test: `api/tests/routes/test_dashboard.py`

**Step 1: Write test for ML fields on dashboard picks**

In `api/tests/routes/test_dashboard_v4.py`:

```python
@pytest.mark.anyio
async def test_dashboard_picks_include_ml_override(client: AsyncClient, seed_v4_scores):
    """Dashboard picks should include ml_override and style from V4Score."""
    resp = await client.get("/api/v1/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    if data["picks"]:
        pick = data["picks"][0]
        assert "ml_override" in pick
        assert "style" in pick
```

**Step 2: Update dashboard to prefer V4Score**

Update the dashboard query to join V4Score when available, similar to the score endpoint pattern. Add `ml_override` and `style` to the `_pick_summary_from_row` construction.

**Step 3: Run tests**

Run: `uv run pytest api/tests/routes/test_dashboard_v4.py -v && uv run pytest api/tests/ -v`

**Step 4: Commit**

```
feat(api): add ml_override and style to dashboard PickSummary

Dashboard picks now include V4 ML override status and investment
style classification when V4Score data is available.
```

---

## Task 7: Build ML Audit Panel Component

**Files:**
- Create: `web/src/components/asset-detail/ml-audit-panel.tsx`
- Create: `web/src/components/asset-detail/__tests__/ml-audit-panel.test.tsx`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx:7,99-110` (add MLAuditPanel)

**Step 1: Write tests for all three panel states**

In `web/src/components/asset-detail/__tests__/ml-audit-panel.test.tsx`:

```typescript
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MLAuditPanel } from "../ml-audit-panel"

describe("MLAuditPanel", () => {
  it("shows no-model state when ml_model_qualified is false", () => {
    render(
      <MLAuditPanel
        mlModelQualified={false}
        mlModelRankIc={0.11}
        mlModelTrainedAt="2026-02-22T02:00:00Z"
        mlAlpha={null}
        mlConfidence={null}
        mlOverride={null}
        rulesConviction={null}
        conviction={null}
      />
    )
    expect(screen.getByText(/no qualified model/i)).toBeInTheDocument()
    expect(screen.getByText(/0\.11/)).toBeInTheDocument()
    expect(screen.getByText(/rules-only/i)).toBeInTheDocument()
  })

  it("shows qualified-no-override state", () => {
    render(
      <MLAuditPanel
        mlModelQualified={true}
        mlModelRankIc={0.19}
        mlModelTrainedAt="2026-02-22T02:00:00Z"
        mlAlpha={0.034}
        mlConfidence={0.62}
        mlOverride="none"
        rulesConviction="high"
        conviction="high"
      />
    )
    expect(screen.getByText(/qualified/i)).toBeInTheDocument()
    expect(screen.getByText(/0\.19/)).toBeInTheDocument()
    expect(screen.getByText(/62%/)).toBeInTheDocument()
    expect(screen.queryByText(/promoted|demoted/i)).not.toBeInTheDocument()
  })

  it("shows promoted override state", () => {
    render(
      <MLAuditPanel
        mlModelQualified={true}
        mlModelRankIc={0.19}
        mlModelTrainedAt="2026-02-22T02:00:00Z"
        mlAlpha={0.072}
        mlConfidence={0.81}
        mlOverride="promoted"
        rulesConviction="medium"
        conviction="high"
      />
    )
    expect(screen.getByText(/promoted/i)).toBeInTheDocument()
    expect(screen.getByText(/medium/i)).toBeInTheDocument()
    expect(screen.getByText(/81%/)).toBeInTheDocument()
  })

  it("shows demoted override state", () => {
    render(
      <MLAuditPanel
        mlModelQualified={true}
        mlModelRankIc={0.19}
        mlModelTrainedAt="2026-02-22T02:00:00Z"
        mlAlpha={-0.05}
        mlConfidence={0.78}
        mlOverride="demoted"
        rulesConviction="high"
        conviction="medium"
      />
    )
    expect(screen.getByText(/demoted/i)).toBeInTheDocument()
  })

  it("renders nothing when no ML data at all", () => {
    const { container } = render(
      <MLAuditPanel
        mlModelQualified={null}
        mlModelRankIc={null}
        mlModelTrainedAt={null}
        mlAlpha={null}
        mlConfidence={null}
        mlOverride={null}
        rulesConviction={null}
        conviction={null}
      />
    )
    expect(container.innerHTML).toBe("")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/ml-audit-panel.test.tsx`
Expected: FAIL (module not found)

**Step 3: Implement MLAuditPanel component**

Create `web/src/components/asset-detail/ml-audit-panel.tsx`:

```typescript
interface MLAuditPanelProps {
  mlModelQualified: boolean | null
  mlModelRankIc: number | null
  mlModelTrainedAt: string | null
  mlAlpha: number | null
  mlConfidence: number | null
  mlOverride: string | null
  rulesConviction: string | null
  conviction: string | null
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

function OverrideRulesChecklist({
  rankIc,
  confidence,
  mlOverride,
}: {
  rankIc: number
  confidence: number
  mlOverride: string
}) {
  const isPromotion = mlOverride === "promoted"
  const pctThreshold = isPromotion ? 85 : 15
  const pctLabel = isPromotion ? "\u2265 85" : "\u2264 15"

  return (
    <div className="mt-3 space-y-1 text-xs">
      <div className="text-text-secondary font-medium">Override Rules:</div>
      <div className="text-bullish">
        \u2713 Model qualified (IC {rankIc.toFixed(2)} &gt; 0.15)
      </div>
      <div className="text-bullish">
        \u2713 Confidence \u2265 0.75 ({(confidence * 100).toFixed(0)}%)
      </div>
      <div className="text-bullish">
        \u2713 ML percentile {pctLabel}
      </div>
    </div>
  )
}

export function MLAuditPanel({
  mlModelQualified,
  mlModelRankIc,
  mlModelTrainedAt,
  mlAlpha,
  mlConfidence,
  mlOverride,
  rulesConviction,
  conviction,
}: MLAuditPanelProps) {
  // No ML data at all (v2 fallback)
  if (mlModelQualified === null && mlModelRankIc === null) {
    return null
  }

  const hasOverride = mlOverride === "promoted" || mlOverride === "demoted"

  return (
    <section data-testid="ml-audit-panel" className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Machine Learning Audit</h2>
        {hasOverride && (
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded ${
              mlOverride === "promoted"
                ? "bg-bullish/10 text-bullish"
                : "bg-bearish/10 text-bearish"
            }`}
          >
            {mlOverride === "promoted" ? "\u25B2 PROMOTED" : "\u25BC DEMOTED"}
          </span>
        )}
      </div>

      {/* State 1: No qualified model */}
      {mlModelQualified === false && (
        <div className="terminal-card p-4 space-y-2">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full bg-text-tertiary" />
            <span className="text-sm font-medium text-text-secondary">No qualified model</span>
          </div>
          <p className="text-sm text-text-tertiary">
            ML models are training. Current rank IC ({mlModelRankIc?.toFixed(2) ?? "N/A"}) is below
            the 0.15 qualification threshold. Scoring is rules-only.
          </p>
          {mlModelTrainedAt && (
            <p className="text-xs text-text-tertiary">
              Last training: {formatDate(mlModelTrainedAt)}
            </p>
          )}
        </div>
      )}

      {/* State 2 & 3: Qualified model */}
      {mlModelQualified === true && (
        <>
          {/* Model status row */}
          <div className="terminal-card p-4">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="inline-block h-2 w-2 rounded-full bg-bullish" />
                <span className="font-medium text-text-primary">Qualified</span>
              </div>
              <div className="flex items-center gap-4 text-text-tertiary">
                <span>
                  Rank IC:{" "}
                  <span className="text-text-primary font-mono">
                    {mlModelRankIc?.toFixed(2) ?? "N/A"}
                  </span>
                </span>
                {mlModelTrainedAt && <span>Trained: {formatDate(mlModelTrainedAt)}</span>}
              </div>
            </div>
          </div>

          {/* Three metric cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="terminal-card p-4 space-y-1">
              <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
                ML Alpha
              </span>
              <span className="text-2xl font-display text-text-primary block">
                {mlAlpha != null ? mlAlpha.toFixed(3) : "N/A"}
              </span>
            </div>

            <div className="terminal-card p-4 space-y-1">
              <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
                Confidence
              </span>
              <span className="text-2xl font-display text-text-primary block">
                {mlConfidence != null ? `${(mlConfidence * 100).toFixed(0)}%` : "N/A"}
              </span>
            </div>

            <div className="terminal-card p-4 space-y-1">
              <span className="text-[11px] uppercase tracking-wider text-text-tertiary">
                Override
              </span>
              <span
                className={`text-2xl font-display block ${
                  mlOverride === "promoted"
                    ? "text-bullish"
                    : mlOverride === "demoted"
                      ? "text-bearish"
                      : "text-text-secondary"
                }`}
              >
                {mlOverride === "promoted"
                  ? "Promoted"
                  : mlOverride === "demoted"
                    ? "Demoted"
                    : "None"}
              </span>
              {hasOverride && rulesConviction && conviction && (
                <span className="text-xs text-text-tertiary">
                  {rulesConviction.toUpperCase()} \u2192 {conviction.toUpperCase()}
                </span>
              )}
            </div>
          </div>

          {/* Verdict text */}
          <div className="terminal-card p-4">
            <p className="text-sm text-text-secondary">
              {hasOverride ? (
                <>
                  ML signal is {mlOverride === "promoted" ? "strong" : "weak"} with{" "}
                  {mlConfidence != null ? `${(mlConfidence * 100).toFixed(0)}%` : "unknown"}{" "}
                  confidence. Conviction{" "}
                  {mlOverride === "promoted" ? "promoted" : "demoted"} from{" "}
                  {rulesConviction?.toUpperCase()} to {conviction?.toUpperCase()}.
                </>
              ) : (
                <>
                  ML signal did not meet override thresholds. Rules-based conviction preserved.
                </>
              )}
            </p>
            {hasOverride && mlModelRankIc != null && mlConfidence != null && (
              <OverrideRulesChecklist
                rankIc={mlModelRankIc}
                confidence={mlConfidence}
                mlOverride={mlOverride!}
              />
            )}
          </div>
        </>
      )}
    </section>
  )
}
```

**Step 4: Run tests**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/ml-audit-panel.test.tsx`
Expected: All pass

**Step 5: Wire into AssetDetailView**

In `web/src/components/asset-detail/asset-detail-view.tsx`:

Add import:
```typescript
import { MLAuditPanel } from "./ml-audit-panel"
```

After the ConvictionEngine section (line 110), add:

```typescript
      {allFiltersPassed && (
        <MLAuditPanel
          mlModelQualified={scoreData.ml_model_qualified ?? null}
          mlModelRankIc={scoreData.ml_model_rank_ic ?? null}
          mlModelTrainedAt={scoreData.ml_model_trained_at ?? null}
          mlAlpha={scoreData.ml_alpha ?? null}
          mlConfidence={scoreData.ml_confidence ?? null}
          mlOverride={scoreData.ml_override ?? null}
          rulesConviction={scoreData.rules_conviction ?? null}
          conviction={scoreData.conviction_level ?? null}
        />
      )}
```

**Step 6: Run web tests**

Run: `cd web && npx vitest run`
Expected: All pass

**Step 7: Commit**

```
feat(web): add ML Audit Panel to asset detail page

Shows model qualification status, ML alpha, confidence, and override
details. Three states: no qualified model (honest empty state),
qualified with no override, qualified with promotion/demotion.
Includes override rules checklist when ML adjusts conviction.
```

---

## Task 8: Add ML Override Badge to Conviction Engine

**Files:**
- Modify: `web/src/components/asset-detail/conviction-engine.tsx:10-19,72-84`
- Test: `web/src/components/asset-detail/__tests__/conviction-engine.test.tsx`

**Step 1: Write test for override badge**

```typescript
it("shows ML-promoted badge when mlOverride is promoted", () => {
  render(
    <ConvictionEngine
      opportunityType="compounder"
      winningTrack="compounder"
      asymmetryRatio={2.5}
      maxPositionPct={5.0}
      timingSignal="buy_now"
      capitalAllocation={null}
      catalyst={null}
      mlOverride="promoted"
    />
  )
  expect(screen.getByText(/ml-promoted/i)).toBeInTheDocument()
})

it("does not show ML badge when mlOverride is none", () => {
  render(
    <ConvictionEngine
      opportunityType="compounder"
      winningTrack="compounder"
      asymmetryRatio={2.5}
      maxPositionPct={5.0}
      timingSignal="buy_now"
      capitalAllocation={null}
      catalyst={null}
      mlOverride="none"
    />
  )
  expect(screen.queryByText(/ml-promoted|ml-demoted/i)).not.toBeInTheDocument()
})
```

**Step 2: Add mlOverride prop**

In `conviction-engine.tsx`, add to ConvictionEngineProps:

```typescript
  mlOverride?: string | null
```

Add to the destructured props. After the opportunity type banner heading, add:

```typescript
      {mlOverride === "promoted" && (
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-bullish/10 text-bullish">
          ML-promoted
        </span>
      )}
      {mlOverride === "demoted" && (
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-bearish/10 text-bearish">
          ML-demoted
        </span>
      )}
```

**Step 3: Wire in AssetDetailView**

Add `mlOverride={scoreData.ml_override ?? null}` to the ConvictionEngine props.

**Step 4: Run tests and commit**

```
feat(web): add ML override badge to conviction engine section
```

---

## Task 9: Add Style Tag to Hero Header

**Files:**
- Modify: `web/src/components/asset-detail/hero-header.tsx:3-21,116-122`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx` (pass style prop)
- Test: `web/src/components/asset-detail/__tests__/hero-header.test.tsx`

**Step 1: Write test**

```typescript
it("shows style tag in metadata ribbon", () => {
  render(<HeroHeader {...defaultProps} style="growth" />)
  expect(screen.getByText("Growth")).toBeInTheDocument()
})
```

**Step 2: Add style prop**

In `hero-header.tsx`, add to HeroHeaderProps:

```typescript
  style?: string | null
```

In the metadata ribbon section (between sector and growthStage), add the style tag:

```typescript
            {style && <span>{style.charAt(0).toUpperCase() + style.slice(1)}</span>}
            {style && (sector || growthStage) && <span>·</span>}
```

**Step 3: Wire in AssetDetailView**

Add `style={scoreData.style}` to the HeroHeader props.

**Step 4: Run tests and commit**

```
feat(web): add investment style tag to hero metadata ribbon
```

---

## Task 10: Add ML Override Indicator to Dashboard Stock Cards

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx:58-61,137-170`
- Test: `web/src/components/dashboard/__tests__/stock-card.test.tsx`

**Step 1: Write test**

```typescript
it("shows ML promoted indicator when ml_override is promoted", () => {
  render(<StockCard pick={{ ...defaultPick, ml_override: "promoted" }} />)
  expect(screen.getByTestId(`ml-override-${defaultPick.ticker}`)).toBeInTheDocument()
})

it("does not show ML indicator when ml_override is none", () => {
  render(<StockCard pick={{ ...defaultPick, ml_override: "none" }} />)
  expect(screen.queryByTestId(`ml-override-${defaultPick.ticker}`)).not.toBeInTheDocument()
})
```

**Step 2: Add ML indicator**

In the stock card header section (near the ConvictionBadge), add:

```typescript
          {pick.ml_override === "promoted" && (
            <span
              className="text-xs text-bullish font-semibold"
              data-testid={`ml-override-${pick.ticker}`}
              title="ML-promoted"
            >
              ▲
            </span>
          )}
          {pick.ml_override === "demoted" && (
            <span
              className="text-xs text-bearish font-semibold"
              data-testid={`ml-override-${pick.ticker}`}
              title="ML-demoted"
            >
              ▼
            </span>
          )}
```

**Step 3: Run tests and commit**

```
feat(web): add ML override indicator to dashboard stock cards
```

---

## Task Dependencies

Tasks 1-3 are independent (all engine/API backend). Can be parallelized.

Task 4 (schemas) is independent of 1-3.

Task 5 depends on Task 4 (needs ML fields on ScoreResponse).

Task 6 depends on Task 4 (needs ML fields on PickSummary).

Task 7 depends on Task 4 (needs TypeScript types).

Tasks 8-10 depend on Task 7 (share the asset detail view wiring).

```
Parallel group 1: Tasks 1, 2, 3, 4
Parallel group 2: Tasks 5, 6, 7 (after 4)
Sequential: Tasks 8, 9, 10 (after 7)
```
