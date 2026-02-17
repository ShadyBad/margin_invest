# V2 Data Display Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface all Conviction Engine v2 scoring data through the API and frontend with a two-view toggle (Thesis View + Data View).

**Architecture:** Extend existing data flow: add 5 nullable columns to `scores` table, add v2 fields to API schemas (ScoreResponse + PickSummary), update routes to populate them, add v2 fields to TypeScript types, then evolve stock-card and asset-detail components with opportunity badges, position sizing, timing signals, and a thesis/data toggle.

**Tech Stack:** SQLAlchemy 2.0, Alembic, FastAPI, Pydantic, Next.js 15 (React), TypeScript, Tailwind CSS

---

### Task 1: Add v2 columns to Score DB model

**Files:**
- Modify: `api/src/margin_api/db/models.py:157-188` (Score class)
- Test: `api/tests/test_models.py` (or inline verification)

**Context:** The `Score` model currently stores v1 fields. The engine's `CompositeScore.model_dump()` already includes all v2 fields in the JSONB `score_detail` column, but we need dedicated columns for `opportunity_type`, `winning_track`, `asymmetry_ratio`, `max_position_pct`, and `timing_signal` so the dashboard can query them without parsing JSONB.

**Step 1: Write a test that the Score model accepts v2 fields**

Add to `api/tests/db/test_v2_score_columns.py`:

```python
"""Tests for v2 Score model columns."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect

from margin_api.db.models import Score


class TestV2ScoreColumns:
    def test_score_model_has_v2_columns(self):
        """Score model should have v2 columns as attributes."""
        s = Score(
            asset_id=1,
            composite_percentile=99.5,
            composite_raw_score=85.0,
            conviction_level="high",
            signal="buy",
            scored_at=datetime.now(UTC),
            opportunity_type="compounder",
            winning_track="compounder",
            asymmetry_ratio=4.2,
            max_position_pct=10.0,
            timing_signal="buy_now",
        )
        assert s.opportunity_type == "compounder"
        assert s.winning_track == "compounder"
        assert s.asymmetry_ratio == 4.2
        assert s.max_position_pct == 10.0
        assert s.timing_signal == "buy_now"

    def test_v2_columns_are_nullable(self):
        """V2 columns should all default to None for backward compat."""
        s = Score(
            asset_id=1,
            composite_percentile=50.0,
            conviction_level="none",
            signal="no_action",
            scored_at=datetime.now(UTC),
        )
        assert s.opportunity_type is None
        assert s.winning_track is None
        assert s.asymmetry_ratio is None
        assert s.max_position_pct is None
        assert s.timing_signal is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/db/test_v2_score_columns.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'opportunity_type'`

**Step 3: Add v2 columns to Score model**

In `api/src/margin_api/db/models.py`, add these columns to the `Score` class after line 179 (`price_target_invalid_reason`):

```python
    opportunity_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    winning_track: Mapped[str | None] = mapped_column(String(30), nullable=True)
    asymmetry_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_position_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    timing_signal: Mapped[str | None] = mapped_column(String(30), nullable=True)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/db/test_v2_score_columns.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/db/test_v2_score_columns.py
git commit -m "feat: add v2 conviction engine columns to Score model"
```

---

### Task 2: Create Alembic migration for v2 columns

**Files:**
- Create: `api/alembic/versions/<auto>_add_v2_conviction_columns_to_scores.py`

**Context:** Follow the exact pattern of the previous migration (`4d3c03eb2d62`). The migration adds 5 nullable columns to `scores`.

**Step 1: Generate the migration**

```bash
cd api && uv run alembic revision --autogenerate -m "add v2 conviction columns to scores"
```

**Step 2: Verify the migration file was created and looks correct**

The generated migration should contain:

```python
def upgrade() -> None:
    op.add_column('scores', sa.Column('opportunity_type', sa.String(length=30), nullable=True))
    op.add_column('scores', sa.Column('winning_track', sa.String(length=30), nullable=True))
    op.add_column('scores', sa.Column('asymmetry_ratio', sa.Float(), nullable=True))
    op.add_column('scores', sa.Column('max_position_pct', sa.Float(), nullable=True))
    op.add_column('scores', sa.Column('timing_signal', sa.String(length=30), nullable=True))

def downgrade() -> None:
    op.drop_column('scores', 'timing_signal')
    op.drop_column('scores', 'max_position_pct')
    op.drop_column('scores', 'asymmetry_ratio')
    op.drop_column('scores', 'winning_track')
    op.drop_column('scores', 'opportunity_type')
```

**Step 3: Run the migration against local DB**

```bash
cd api && uv run alembic upgrade head
```

**Step 4: Commit**

```bash
git add api/alembic/versions/
git commit -m "migration: add v2 conviction columns to scores table"
```

---

### Task 3: Add v2 fields to ScoreResponse schema

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py:67-168`
- Test: `api/tests/schemas/test_v2_score_response.py`

**Context:** `ScoreResponse` needs 7 new optional fields for v2 data. The `from_engine()` classmethod needs to map them from `CompositeScore`. The `_breakdown_from_engine()` helper already works for `capital_allocation` and `catalyst` since they are `FactorBreakdown` objects.

**Step 1: Write failing tests**

Create `api/tests/schemas/test_v2_score_response.py`:

```python
"""Tests for v2 fields in ScoreResponse schema."""

import pytest
from margin_api.schemas.scores import (
    FactorBreakdownResponse,
    FactorScoreResponse,
    ScoreResponse,
)


def _minimal_breakdown(name: str = "quality") -> FactorBreakdownResponse:
    return FactorBreakdownResponse(
        factor_name=name, weight=0.35, sub_scores=[], average_percentile=75.0,
    )


class TestV2ScoreResponse:
    def test_v2_fields_default_to_none(self):
        """V2 fields should be optional and default to None."""
        resp = ScoreResponse(
            ticker="TEST",
            composite_percentile=95.0,
            conviction_level="high",
            signal="buy",
            quality=_minimal_breakdown("quality"),
            value=_minimal_breakdown("value"),
            momentum=_minimal_breakdown("momentum"),
            filters_passed=[],
            data_coverage=1.0,
        )
        assert resp.opportunity_type is None
        assert resp.winning_track is None
        assert resp.asymmetry_ratio is None
        assert resp.max_position_pct is None
        assert resp.timing_signal is None
        assert resp.capital_allocation is None
        assert resp.catalyst is None

    def test_v2_fields_populated(self):
        """V2 fields can be set explicitly."""
        cap_alloc = FactorBreakdownResponse(
            factor_name="capital_allocation",
            weight=0.20,
            sub_scores=[
                FactorScoreResponse(
                    name="buyback_effectiveness",
                    raw_value=0.85,
                    percentile_rank=72.0,
                )
            ],
            average_percentile=72.0,
        )
        resp = ScoreResponse(
            ticker="COST",
            composite_percentile=99.5,
            conviction_level="high",
            signal="buy",
            quality=_minimal_breakdown("quality"),
            value=_minimal_breakdown("value"),
            momentum=_minimal_breakdown("momentum"),
            filters_passed=[],
            data_coverage=1.0,
            opportunity_type="compounder",
            winning_track="compounder",
            asymmetry_ratio=4.2,
            max_position_pct=10.0,
            timing_signal="buy_now",
            capital_allocation=cap_alloc,
            catalyst=None,
        )
        assert resp.opportunity_type == "compounder"
        assert resp.winning_track == "compounder"
        assert resp.asymmetry_ratio == 4.2
        assert resp.max_position_pct == 10.0
        assert resp.timing_signal == "buy_now"
        assert resp.capital_allocation.factor_name == "capital_allocation"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/schemas/test_v2_score_response.py -v`
Expected: FAIL — `unexpected keyword argument 'opportunity_type'`

**Step 3: Add v2 fields to ScoreResponse**

In `api/src/margin_api/schemas/scores.py`, add after line 93 (`price_target_invalid_reason`):

```python
    # v2 Conviction Engine fields
    opportunity_type: str | None = None
    winning_track: str | None = None
    asymmetry_ratio: float | None = None
    max_position_pct: float | None = None
    timing_signal: str | None = None
    capital_allocation: FactorBreakdownResponse | None = None
    catalyst: FactorBreakdownResponse | None = None
```

Update `from_engine()` to map v2 fields. Add these lines before the closing paren of the `cls(...)` call (after `price_target_invalid_reason` mapping):

```python
            opportunity_type=score.opportunity_type.value if score.opportunity_type else None,
            winning_track=score.winning_track,
            asymmetry_ratio=score.asymmetry_ratio,
            max_position_pct=score.max_position_pct,
            timing_signal=score.timing_signal,
            capital_allocation=_breakdown_from_engine(score.capital_allocation) if score.capital_allocation else None,
            catalyst=_breakdown_from_engine(score.catalyst) if score.catalyst else None,
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/schemas/test_v2_score_response.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/scores.py api/tests/schemas/test_v2_score_response.py
git commit -m "feat: add v2 conviction fields to ScoreResponse schema"
```

---

### Task 4: Add v2 fields to PickSummary schema

**Files:**
- Modify: `api/src/margin_api/schemas/dashboard.py:10-31`
- Test: `api/tests/schemas/test_v2_pick_summary.py`

**Context:** `PickSummary` needs 5 new optional fields for the stock card: `opportunity_type`, `winning_track`, `margin_of_safety`, `max_position_pct`, `timing_signal`.

**Step 1: Write failing test**

Create `api/tests/schemas/test_v2_pick_summary.py`:

```python
"""Tests for v2 fields in PickSummary schema."""

from margin_api.schemas.dashboard import PickSummary


class TestV2PickSummary:
    def test_v2_fields_default_to_none(self):
        ps = PickSummary(
            ticker="TEST", name="Test", composite_percentile=50.0,
            conviction_level="none", signal="no_action",
            quality_percentile=50.0, value_percentile=50.0,
            momentum_percentile=50.0,
        )
        assert ps.opportunity_type is None
        assert ps.winning_track is None
        assert ps.margin_of_safety is None
        assert ps.max_position_pct is None
        assert ps.timing_signal is None

    def test_v2_fields_populated(self):
        ps = PickSummary(
            ticker="COST", name="Costco", composite_percentile=99.5,
            conviction_level="high", signal="buy",
            quality_percentile=85.0, value_percentile=70.0,
            momentum_percentile=90.0,
            opportunity_type="compounder",
            winning_track="compounder",
            margin_of_safety=0.32,
            max_position_pct=10.0,
            timing_signal="buy_now",
        )
        assert ps.opportunity_type == "compounder"
        assert ps.margin_of_safety == 0.32
        assert ps.max_position_pct == 10.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/schemas/test_v2_pick_summary.py -v`
Expected: FAIL

**Step 3: Add v2 fields to PickSummary**

In `api/src/margin_api/schemas/dashboard.py`, add after line 30 (`price_updated_at`):

```python
    # v2 Conviction Engine fields
    opportunity_type: str | None = None
    winning_track: str | None = None
    margin_of_safety: float | None = None
    max_position_pct: float | None = None
    timing_signal: str | None = None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/schemas/test_v2_pick_summary.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/dashboard.py api/tests/schemas/test_v2_pick_summary.py
git commit -m "feat: add v2 conviction fields to PickSummary schema"
```

---

### Task 5: Update scores route to populate v2 fields

**Files:**
- Modify: `api/src/margin_api/routes/scores.py:23-144` (`_score_response_from_row`)
- Test: `api/tests/routes/test_v2_scores_route.py`

**Context:** `_score_response_from_row()` has two code paths: (1) when `score_detail` JSONB exists, it does `ScoreResponse(**detail)` — this already works because v2 fields are in `model_dump()` output. (2) The fallback path builds from summary columns — this needs v2 column reads. We also need to compute `average_percentile` for `capital_allocation` and `catalyst` breakdowns in the JSONB path, and set `verdict` on any filter results from conviction gates.

**Step 1: Write failing test**

Create `api/tests/routes/test_v2_scores_route.py`:

```python
"""Tests for v2 fields in score route responses."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from margin_api.routes.scores import _score_response_from_row


class TestV2ScoreRoute:
    def test_fallback_path_includes_v2_fields(self):
        """When score_detail is None, v2 fields come from DB columns."""
        score = MagicMock()
        score.score_detail = None
        score.composite_percentile = 99.5
        score.composite_raw_score = 85.0
        score.conviction_level = "high"
        score.signal = "buy"
        score.quality_percentile = 80.0
        score.value_percentile = 70.0
        score.momentum_percentile = 90.0
        score.data_coverage = 1.0
        score.growth_stage = "steady_growth"
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)
        score.intrinsic_value = 500.0
        score.buy_price = 400.0
        score.sell_price = 600.0
        score.actual_price = 350.0
        score.price_target_invalid_reason = None
        # v2 columns
        score.opportunity_type = "compounder"
        score.winning_track = "compounder"
        score.asymmetry_ratio = 4.2
        score.max_position_pct = 10.0
        score.timing_signal = "buy_now"

        row = MagicMock()
        row.__getitem__ = lambda self, idx: score if idx == 0 else None
        row.Score = score
        row.ticker = "COST"
        row.asset_name = "Costco"

        resp = _score_response_from_row(row)

        assert resp.opportunity_type == "compounder"
        assert resp.winning_track == "compounder"
        assert resp.asymmetry_ratio == 4.2
        assert resp.max_position_pct == 10.0
        assert resp.timing_signal == "buy_now"

    def test_jsonb_path_includes_v2_fields(self):
        """When score_detail has v2 fields, they pass through to response."""
        score = MagicMock()
        score.score_detail = {
            "ticker": "COST",
            "composite_percentile": 99.5,
            "composite_raw_score": 85.0,
            "quality": {
                "factor_name": "quality", "weight": 0.5,
                "sub_scores": [], "average_percentile": 80.0,
            },
            "value": {
                "factor_name": "value", "weight": 0.3,
                "sub_scores": [], "average_percentile": 70.0,
            },
            "momentum": {
                "factor_name": "momentum", "weight": 0.2,
                "sub_scores": [], "average_percentile": 90.0,
            },
            "filters_passed": [],
            "data_coverage": 1.0,
            "opportunity_type": "compounder",
            "winning_track": "compounder",
            "asymmetry_ratio": 4.2,
            "max_position_pct": 10.0,
            "timing_signal": "buy_now",
            "capital_allocation": {
                "factor_name": "capital_allocation", "weight": 0.2,
                "sub_scores": [
                    {"name": "buyback", "raw_value": 0.8, "percentile_rank": 72.0, "detail": ""},
                ],
            },
        }
        score.conviction_level = "high"
        score.signal = "buy"
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)
        score.intrinsic_value = 500.0
        score.buy_price = 400.0
        score.sell_price = 600.0
        score.actual_price = 350.0
        score.price_target_invalid_reason = None
        score.composite_raw_score = 85.0
        score.composite_percentile = 99.5

        row = MagicMock()
        row.__getitem__ = lambda self, idx: score if idx == 0 else None
        row.Score = score
        row.ticker = "COST"
        row.asset_name = "Costco"

        resp = _score_response_from_row(row)

        assert resp.opportunity_type == "compounder"
        assert resp.winning_track == "compounder"
        assert resp.asymmetry_ratio == 4.2
        assert resp.capital_allocation is not None
        assert resp.capital_allocation.average_percentile == 72.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/routes/test_v2_scores_route.py -v`
Expected: FAIL — response missing v2 fields in fallback path

**Step 3: Update `_score_response_from_row` in `api/src/margin_api/routes/scores.py`**

In the JSONB path (around line 65), add `average_percentile` computation for `capital_allocation` and `catalyst` (same pattern as quality/value/momentum):

```python
        for factor_key in ("quality", "value", "momentum", "capital_allocation", "catalyst"):
            factor = detail.get(factor_key)
            if factor is not None and "average_percentile" not in factor:
                subs = factor.get("sub_scores", [])
                avg = (
                    sum(s.get("percentile_rank", 0) for s in subs) / len(subs)
                    if subs
                    else 0.0
                )
                factor["average_percentile"] = avg
```

Also add `setdefault` lines for v2 DB columns in the JSONB path (same pattern as price targets):

```python
        detail.setdefault("opportunity_type", getattr(score, "opportunity_type", None))
        detail.setdefault("winning_track", getattr(score, "winning_track", None))
        detail.setdefault("asymmetry_ratio", getattr(score, "asymmetry_ratio", None))
        detail.setdefault("max_position_pct", getattr(score, "max_position_pct", None))
        detail.setdefault("timing_signal", getattr(score, "timing_signal", None))
```

In the fallback path (around line 99), add v2 fields to the `ScoreResponse(...)` constructor:

```python
        opportunity_type=getattr(score, "opportunity_type", None),
        winning_track=getattr(score, "winning_track", None),
        asymmetry_ratio=getattr(score, "asymmetry_ratio", None),
        max_position_pct=getattr(score, "max_position_pct", None),
        timing_signal=getattr(score, "timing_signal", None),
```

Also add `margin_of_safety` to the fallback path:

```python
        margin_of_safety=(
            round((score.intrinsic_value - score.actual_price) / score.intrinsic_value, 4)
            if getattr(score, "intrinsic_value", None)
            and getattr(score, "actual_price", None)
            and score.actual_price < score.intrinsic_value
            and not invalid_reason
            else None
        ),
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/routes/test_v2_scores_route.py -v`
Expected: PASS

**Step 5: Run all API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All pass

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/scores.py api/tests/routes/test_v2_scores_route.py
git commit -m "feat: populate v2 conviction fields in score route responses"
```

---

### Task 6: Update dashboard route to pass v2 fields

**Files:**
- Modify: `api/src/margin_api/routes/dashboard.py:59-87` (PickSummary construction)
- Test: `api/tests/routes/test_v2_dashboard_route.py`

**Context:** The dashboard route constructs `PickSummary` objects from DB rows. We need to add v2 fields. The `margin_of_safety` is computed as `(intrinsic_value - actual_price) / intrinsic_value` when both are available.

**Step 1: Write failing test**

Create `api/tests/routes/test_v2_dashboard_route.py`:

```python
"""Tests for v2 fields in dashboard PickSummary construction."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest


def _build_pick_summary_from_score(score_mock):
    """Replicate the dashboard route's PickSummary construction logic."""
    from margin_api.schemas.dashboard import PickSummary
    from margin_api.services.freshness import compute_freshness

    return PickSummary(
        ticker="COST",
        name="Costco",
        score=score_mock.composite_raw_score,
        universe_percentile=score_mock.composite_percentile,
        composite_percentile=score_mock.composite_percentile,
        conviction_level=score_mock.conviction_level,
        signal=score_mock.signal,
        quality_percentile=score_mock.quality_percentile,
        value_percentile=score_mock.value_percentile,
        momentum_percentile=score_mock.momentum_percentile,
        actual_price=getattr(score_mock, "actual_price", None),
        buy_price=getattr(score_mock, "buy_price", None),
        sell_price=getattr(score_mock, "sell_price", None),
        opportunity_type=getattr(score_mock, "opportunity_type", None),
        winning_track=getattr(score_mock, "winning_track", None),
        max_position_pct=getattr(score_mock, "max_position_pct", None),
        timing_signal=getattr(score_mock, "timing_signal", None),
        margin_of_safety=(
            round(
                (score_mock.intrinsic_value - score_mock.actual_price)
                / score_mock.intrinsic_value,
                4,
            )
            if getattr(score_mock, "intrinsic_value", None)
            and getattr(score_mock, "actual_price", None)
            and score_mock.actual_price < score_mock.intrinsic_value
            and not getattr(score_mock, "price_target_invalid_reason", None)
            else None
        ),
    )


class TestV2DashboardPickSummary:
    def test_pick_summary_has_v2_fields(self):
        score = MagicMock()
        score.composite_percentile = 99.5
        score.composite_raw_score = 85.0
        score.conviction_level = "high"
        score.signal = "buy"
        score.quality_percentile = 80.0
        score.value_percentile = 70.0
        score.momentum_percentile = 90.0
        score.actual_price = 350.0
        score.buy_price = 400.0
        score.sell_price = 600.0
        score.intrinsic_value = 500.0
        score.price_target_invalid_reason = None
        score.opportunity_type = "compounder"
        score.winning_track = "compounder"
        score.max_position_pct = 10.0
        score.timing_signal = "buy_now"
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)

        ps = _build_pick_summary_from_score(score)
        assert ps.opportunity_type == "compounder"
        assert ps.winning_track == "compounder"
        assert ps.max_position_pct == 10.0
        assert ps.timing_signal == "buy_now"
        assert ps.margin_of_safety == 0.3  # (500-350)/500 = 0.3

    def test_pick_summary_v2_fields_none_for_v1(self):
        score = MagicMock()
        score.composite_percentile = 50.0
        score.composite_raw_score = 40.0
        score.conviction_level = "none"
        score.signal = "no_action"
        score.quality_percentile = 50.0
        score.value_percentile = 50.0
        score.momentum_percentile = 50.0
        score.actual_price = None
        score.buy_price = None
        score.sell_price = None
        score.intrinsic_value = None
        score.price_target_invalid_reason = None
        score.opportunity_type = None
        score.winning_track = None
        score.max_position_pct = None
        score.timing_signal = None
        score.scored_at = datetime(2026, 2, 17, tzinfo=UTC)

        ps = _build_pick_summary_from_score(score)
        assert ps.opportunity_type is None
        assert ps.margin_of_safety is None
```

**Step 2: Run test to verify it passes (schema already updated in Task 4)**

Run: `uv run pytest api/tests/routes/test_v2_dashboard_route.py -v`
Expected: PASS (this tests the construction pattern, not the route itself)

**Step 3: Update dashboard route `PickSummary` construction**

In `api/src/margin_api/routes/dashboard.py`, update the PickSummary construction in both the picks loop (line 60-87) and the fallback loop (line 110-138). Add these fields to each `PickSummary(...)`:

```python
            opportunity_type=getattr(row.Score, "opportunity_type", None),
            winning_track=getattr(row.Score, "winning_track", None),
            max_position_pct=getattr(row.Score, "max_position_pct", None),
            timing_signal=getattr(row.Score, "timing_signal", None),
            margin_of_safety=(
                round(
                    (row.Score.intrinsic_value - row.Score.actual_price)
                    / row.Score.intrinsic_value,
                    4,
                )
                if getattr(row.Score, "intrinsic_value", None)
                and getattr(row.Score, "actual_price", None)
                and row.Score.actual_price < row.Score.intrinsic_value
                and not getattr(row.Score, "price_target_invalid_reason", None)
                else None
            ),
```

**Step 4: Run all API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All pass

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/dashboard.py api/tests/routes/test_v2_dashboard_route.py
git commit -m "feat: pass v2 conviction fields in dashboard PickSummary"
```

---

### Task 7: Persist v2 fields in worker and CLI scoring

**Files:**
- Modify: `api/src/margin_api/worker.py:97-111` (Score row creation)
- Modify: `api/src/margin_api/cli.py:358-376` (Score row creation in batch scoring)
- Test: `api/tests/test_v2_worker_persist.py`

**Context:** Both `worker.py:score_ticker()` and `cli.py:run_scoring()` create `Score(...)` rows from `CompositeScore`. They need to persist v2 fields from the engine model to the new DB columns.

**Step 1: Write failing test**

Create `api/tests/test_v2_worker_persist.py`:

```python
"""Tests for v2 field persistence in worker scoring."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestV2WorkerPersist:
    def test_score_row_includes_v2_fields(self):
        """Score row construction should include v2 fields from composite."""
        from margin_api.db.models import Score

        # Simulate what the worker does
        composite = MagicMock()
        composite.composite_percentile = 99.5
        composite.composite_raw_score = 85.0
        composite.conviction_level.value = "high"
        composite.signal.value = "buy"
        composite.quality.average_percentile = 80.0
        composite.value.average_percentile = 70.0
        composite.momentum.average_percentile = 90.0
        composite.data_coverage = 1.0
        composite.growth_stage.value = "steady_growth"
        composite.model_dump.return_value = {"ticker": "COST"}
        composite.intrinsic_value = 500.0
        composite.buy_price = 400.0
        composite.sell_price = 600.0
        composite.actual_price = 350.0
        composite.price_target_invalid_reason = None
        composite.opportunity_type.value = "compounder"
        composite.winning_track = "compounder"
        composite.asymmetry_ratio = 4.2
        composite.max_position_pct = 10.0
        composite.timing_signal = "buy_now"

        score = Score(
            asset_id=1,
            composite_percentile=composite.composite_percentile,
            composite_raw_score=composite.composite_raw_score,
            conviction_level=composite.conviction_level.value,
            signal=composite.signal.value,
            quality_percentile=composite.quality.average_percentile,
            value_percentile=composite.value.average_percentile,
            momentum_percentile=composite.momentum.average_percentile,
            data_coverage=composite.data_coverage,
            growth_stage=composite.growth_stage.value,
            score_detail=composite.model_dump(mode="json"),
            scored_at=datetime.now(UTC),
            intrinsic_value=composite.intrinsic_value,
            buy_price=composite.buy_price,
            sell_price=composite.sell_price,
            actual_price=composite.actual_price,
            price_target_invalid_reason=composite.price_target_invalid_reason,
            opportunity_type=composite.opportunity_type.value,
            winning_track=composite.winning_track,
            asymmetry_ratio=composite.asymmetry_ratio,
            max_position_pct=composite.max_position_pct,
            timing_signal=composite.timing_signal,
        )

        assert score.opportunity_type == "compounder"
        assert score.winning_track == "compounder"
        assert score.asymmetry_ratio == 4.2
        assert score.max_position_pct == 10.0
        assert score.timing_signal == "buy_now"
```

**Step 2: Run test to verify it passes (model already updated in Task 1)**

Run: `uv run pytest api/tests/test_v2_worker_persist.py -v`
Expected: PASS

**Step 3: Update worker.py Score construction**

In `api/src/margin_api/worker.py`, update the `Score(...)` construction at line 97-111 to add v2 fields after `price_target_invalid_reason`:

```python
                intrinsic_value=composite.intrinsic_value,
                buy_price=composite.buy_price,
                sell_price=composite.sell_price,
                actual_price=composite.actual_price,
                price_target_invalid_reason=composite.price_target_invalid_reason,
                opportunity_type=composite.opportunity_type.value if composite.opportunity_type else None,
                winning_track=composite.winning_track,
                asymmetry_ratio=composite.asymmetry_ratio,
                max_position_pct=composite.max_position_pct,
                timing_signal=composite.timing_signal,
```

Note: The worker currently doesn't persist `intrinsic_value` etc. — add those too if missing. Check lines 97-111 and ensure all price target fields are there.

**Step 4: Update cli.py Score construction**

In `api/src/margin_api/cli.py`, update the `Score(...)` construction at line 358-376 (in `run_scoring()`) to add v2 fields after `price_target_invalid_reason`:

```python
                opportunity_type=composite.opportunity_type.value if composite.opportunity_type else None,
                winning_track=composite.winning_track,
                asymmetry_ratio=composite.asymmetry_ratio,
                max_position_pct=composite.max_position_pct,
                timing_signal=composite.timing_signal,
```

**Step 5: Run all API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All pass

**Step 6: Commit**

```bash
git add api/src/margin_api/worker.py api/src/margin_api/cli.py api/tests/test_v2_worker_persist.py
git commit -m "feat: persist v2 conviction fields in worker and CLI scoring"
```

---

### Task 8: Add v2 fields to TypeScript types

**Files:**
- Modify: `web/src/lib/api/types.ts:45-73` (ScoreResponse interface)
- Modify: `web/src/lib/api/types.ts:81-101` (PickSummary interface)

**Context:** Add the same v2 fields that the API now returns. All optional/nullable for backward compat.

**Step 1: Update ScoreResponse interface**

In `web/src/lib/api/types.ts`, add after `signal_history` (line 71):

```typescript
  // v2 Conviction Engine fields
  opportunity_type: string | null
  winning_track: string | null
  asymmetry_ratio: number | null
  max_position_pct: number | null
  timing_signal: string | null
  capital_allocation: FactorBreakdownResponse | null
  catalyst: FactorBreakdownResponse | null
  price_target_invalid_reason: string | null
```

**Step 2: Update PickSummary interface**

In `web/src/lib/api/types.ts`, add after `ingestion_status` (line 100):

```typescript
  // v2 Conviction Engine fields
  opportunity_type?: string | null
  winning_track?: string | null
  margin_of_safety?: number | null
  max_position_pct?: number | null
  timing_signal?: string | null
```

**Step 3: Verify TypeScript compiles**

Run: `cd web && npx tsc --noEmit`
Expected: No type errors (all new fields are optional)

**Step 4: Commit**

```bash
git add web/src/lib/api/types.ts
git commit -m "feat: add v2 conviction fields to TypeScript interfaces"
```

---

### Task 9: Update StockCard with v2 thesis view

**Files:**
- Modify: `web/src/components/dashboard/stock-card.tsx`

**Context:** Add opportunity type badge, margin of safety, position sizing, timing signal, and track-aware percentile bars. All guarded by null checks so v1 scores render unchanged.

**Step 1: Update the StockCard component**

In `web/src/components/dashboard/stock-card.tsx`:

**a) Add opportunity type badge** — next to ConvictionBadge in the header (line 91):

```tsx
        <div className="flex items-center gap-2">
          <ConvictionBadge level={pick.conviction_level} />
          {pick.opportunity_type && pick.opportunity_type !== "neither" && (
            <span
              className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                pick.opportunity_type === "compounder"
                  ? "bg-accent/10 text-accent"
                  : pick.opportunity_type === "mispricing"
                    ? "bg-purple-500/10 text-purple-400"
                    : "bg-text-secondary/10 text-text-secondary"
              }`}
              data-testid={`opportunity-type-${pick.ticker}`}
            >
              {pick.opportunity_type === "compounder"
                ? "Compounder"
                : pick.opportunity_type === "mispricing"
                  ? "Mispricing"
                  : "Both"}
            </span>
          )}
        </div>
```

**b) Add margin of safety to price row** — after price_upside (line 139):

```tsx
          {pick.margin_of_safety != null && (
            <span className="text-text-secondary">
              MoS:{" "}
              <span className="text-bullish font-medium">
                {(pick.margin_of_safety * 100).toFixed(0)}%
              </span>
            </span>
          )}
```

**c) Add position sizing and timing signal** — new row after price row, before percentile bars (line 147):

```tsx
      {(pick.max_position_pct != null || pick.timing_signal) && (
        <div className="flex items-center justify-between mb-4 text-sm">
          {pick.max_position_pct != null && (
            <span className="text-text-secondary">
              Max position:{" "}
              <span className="text-text-primary font-medium">
                {pick.max_position_pct.toFixed(0)}%
              </span>
            </span>
          )}
          {pick.timing_signal && (
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                pick.timing_signal === "buy_now"
                  ? "bg-bullish/10 text-bullish"
                  : pick.timing_signal === "add_on_pullback"
                    ? "bg-accent/10 text-accent"
                    : "bg-text-secondary/10 text-text-secondary"
              }`}
              data-testid={`timing-signal-${pick.ticker}`}
            >
              {pick.timing_signal === "buy_now"
                ? "Buy now"
                : pick.timing_signal === "add_on_pullback"
                  ? "Add on pullback"
                  : "Wait for catalyst"}
            </span>
          )}
        </div>
      )}
```

**d) Make percentile bars track-aware** — replace the hardcoded Q/V/M bars (lines 148-152):

```tsx
      <div className="space-y-2">
        {pick.winning_track === "compounder" ? (
          <>
            <PercentileBar value={pick.quality_percentile} label="Quality" />
            <PercentileBar value={pick.value_percentile} label="Value" />
            <PercentileBar value={pick.momentum_percentile} label="Momentum" />
          </>
        ) : pick.winning_track === "mispricing" ? (
          <>
            <PercentileBar value={pick.value_percentile} label="Value" />
            <PercentileBar value={pick.quality_percentile} label="Quality Floor" />
            <PercentileBar value={pick.momentum_percentile} label="Catalyst" />
          </>
        ) : (
          <>
            <PercentileBar value={pick.quality_percentile} label="Quality" />
            <PercentileBar value={pick.value_percentile} label="Value" />
            <PercentileBar value={pick.momentum_percentile} label="Momentum" />
          </>
        )}
      </div>
```

**Step 2: Verify it compiles**

Run: `cd web && npx tsc --noEmit`
Expected: No type errors

**Step 3: Commit**

```bash
git add web/src/components/dashboard/stock-card.tsx
git commit -m "feat: add v2 thesis view to stock card — opportunity badge, MoS, position sizing, timing"
```

---

### Task 10: Update AssetDetail with v2 data + toggle

**Files:**
- Modify: `web/src/components/dashboard/asset-detail.tsx`
- Modify: `web/src/components/dashboard/factor-breakdown.tsx`

**Context:** Add a "Show Data" / "Show Thesis" toggle, winning track label, asymmetry ratio display, and conditional factor breakdown. The thesis view shows winning track pillars; the data view shows all sub-factors.

**Step 1: Update AssetDetail**

In `web/src/components/dashboard/asset-detail.tsx`:

a) Add `useState` import and toggle state:

```tsx
"use client"

import { useState } from "react"
```

Add at top of component function:

```tsx
  const [showData, setShowData] = useState(false)
  const hasV2 = score.opportunity_type != null
```

b) Add toggle button and track label in header (after ActionPill):

```tsx
        {hasV2 && (
          <>
            {score.winning_track && (
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                score.winning_track === "compounder"
                  ? "bg-accent/10 text-accent"
                  : "bg-purple-500/10 text-purple-400"
              }`}>
                {score.winning_track === "compounder" ? "Compounder" : "Mispricing"} Track
              </span>
            )}
            <button
              onClick={(e) => { e.stopPropagation(); setShowData(!showData) }}
              className="text-xs text-accent hover:text-accent/80 underline ml-2"
              data-testid="thesis-data-toggle"
            >
              {showData ? "Show Thesis" : "Show Data"}
            </button>
          </>
        )}
```

c) Add asymmetry ratio display below header:

```tsx
      {hasV2 && score.asymmetry_ratio != null && (
        <div className="flex items-center gap-4 mb-4 text-sm">
          <span className="text-text-secondary">
            Asymmetry:{" "}
            <span className="text-text-primary font-bold">
              {score.asymmetry_ratio.toFixed(1)}x
            </span>
          </span>
          {score.max_position_pct != null && (
            <span className="text-text-secondary">
              Max position:{" "}
              <span className="text-text-primary font-medium">
                {score.max_position_pct.toFixed(0)}%
              </span>
            </span>
          )}
          {score.timing_signal && (
            <span className={`text-xs px-2 py-0.5 rounded ${
              score.timing_signal === "buy_now"
                ? "bg-bullish/10 text-bullish"
                : score.timing_signal === "add_on_pullback"
                  ? "bg-accent/10 text-accent"
                  : "bg-text-secondary/10 text-text-secondary"
            }`}>
              {score.timing_signal === "buy_now"
                ? "Buy now"
                : score.timing_signal === "add_on_pullback"
                  ? "Add on pullback"
                  : "Wait for catalyst"}
            </span>
          )}
        </div>
      )}
```

d) Update factor breakdown to pass v2 data:

```tsx
        <FactorBreakdown
          quality={score.quality}
          value={score.value}
          momentum={score.momentum}
          capitalAllocation={score.capital_allocation}
          catalyst={score.catalyst}
          winningTrack={score.winning_track}
          showAllFactors={showData}
        />
```

**Step 2: Update FactorBreakdown component**

In `web/src/components/dashboard/factor-breakdown.tsx`, update the props interface:

```tsx
interface FactorBreakdownProps {
  quality: FactorBreakdownResponse
  value: FactorBreakdownResponse
  momentum: FactorBreakdownResponse
  capitalAllocation?: FactorBreakdownResponse | null
  catalyst?: FactorBreakdownResponse | null
  winningTrack?: string | null
  showAllFactors?: boolean
  className?: string
}
```

Update the component body to conditionally show track-relevant factors:

```tsx
export function FactorBreakdown({
  quality, value, momentum,
  capitalAllocation, catalyst,
  winningTrack, showAllFactors = false,
  className = "",
}: FactorBreakdownProps) {
  let factors: FactorBreakdownResponse[]

  if (showAllFactors || !winningTrack) {
    // Data view or v1: show all
    factors = [quality, value, momentum]
    if (capitalAllocation) factors.push(capitalAllocation)
    if (catalyst) factors.push(catalyst)
  } else if (winningTrack === "compounder") {
    factors = [quality, value]
    if (capitalAllocation) factors.push(capitalAllocation)
  } else {
    // mispricing
    factors = [value, quality]
    if (catalyst) factors.push(catalyst)
  }

  return (
    <div className={`space-y-4 ${className}`} data-testid="factor-breakdown">
      <h3 className="text-base font-semibold text-text-primary">
        Factor Breakdown
        {winningTrack && !showAllFactors && (
          <span className="text-xs font-normal text-text-secondary ml-2">
            ({winningTrack === "compounder" ? "Compounder" : "Mispricing"} Track)
          </span>
        )}
      </h3>
      <div className="space-y-5">
        {factors.map((factor) => (
          <FactorSection key={factor.factor_name} factor={factor} />
        ))}
      </div>
    </div>
  )
}
```

**Step 3: Verify it compiles**

Run: `cd web && npx tsc --noEmit`
Expected: No type errors

**Step 4: Commit**

```bash
git add web/src/components/dashboard/asset-detail.tsx web/src/components/dashboard/factor-breakdown.tsx
git commit -m "feat: add thesis/data toggle and v2 track-aware layout to asset detail"
```

---

### Task 11: Add margin of safety to ValuationBreakdown

**Files:**
- Modify: `web/src/components/dashboard/valuation-breakdown.tsx`

**Context:** Add margin of safety display below the consensus intrinsic value, and show `price_target_invalid_reason` as a warning.

**Step 1: Update ValuationBreakdown props and component**

In `web/src/components/dashboard/valuation-breakdown.tsx`, update the interface:

```tsx
interface ValuationBreakdownProps {
  methods: Record<string, number> | null | undefined
  intrinsicValue: number | null | undefined
  actualPrice?: number | null
  marginOfSafety?: number | null
  invalidReason?: string | null
  className?: string
}
```

Update the component signature to accept new props:

```tsx
export function ValuationBreakdown({
  methods,
  intrinsicValue,
  actualPrice,
  marginOfSafety,
  invalidReason,
  className = "",
}: ValuationBreakdownProps) {
```

Add invalid reason warning at top of the component body (after the empty check):

```tsx
  if (invalidReason) {
    return (
      <div className={className} data-testid="valuation-invalid">
        <h4 className="text-sm font-semibold text-text-primary mb-3">Valuation</h4>
        <p className="text-sm text-warning">{invalidReason}</p>
      </div>
    )
  }
```

Add margin of safety display after the consensus line (inside the existing `intrinsicValue != null` block):

```tsx
      {intrinsicValue != null && (
        <div className="mt-3 pt-3 border-t border-border-primary">
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Consensus</span>
            <span className="text-text-primary font-semibold">${intrinsicValue.toFixed(2)}</span>
          </div>
          {actualPrice != null && (
            <div className="flex justify-between text-sm mt-1">
              <span className="text-text-secondary">Current Price</span>
              <span className="text-text-primary">${actualPrice.toFixed(2)}</span>
            </div>
          )}
          {marginOfSafety != null && (
            <div className="flex justify-between text-sm mt-1">
              <span className="text-text-secondary">Margin of Safety</span>
              <span className={marginOfSafety > 0 ? "text-bullish font-semibold" : "text-bearish"}>
                {(marginOfSafety * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>
      )}
```

**Step 2: Update AssetDetail to pass new props**

In `web/src/components/dashboard/asset-detail.tsx`, update the ValuationBreakdown call:

```tsx
          <ValuationBreakdown
            methods={score.valuation_methods}
            intrinsicValue={score.intrinsic_value}
            actualPrice={score.actual_price}
            marginOfSafety={score.margin_of_safety}
            invalidReason={score.price_target_invalid_reason}
          />
```

**Step 3: Verify it compiles**

Run: `cd web && npx tsc --noEmit`
Expected: No type errors

**Step 4: Commit**

```bash
git add web/src/components/dashboard/valuation-breakdown.tsx web/src/components/dashboard/asset-detail.tsx
git commit -m "feat: add margin of safety and invalid reason to valuation breakdown"
```

---

### Task 12: Run full test suite and verify backward compatibility

**Step 1: Run all engine tests**

Run: `uv run pytest engine/tests/ -v`
Expected: All 1049 tests pass (no engine changes in this plan)

**Step 2: Run all API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All tests pass including new v2 tests

**Step 3: Verify TypeScript compilation**

Run: `cd web && npx tsc --noEmit`
Expected: No errors

**Step 4: Verify the dev server starts**

Run: `cd web && npx next build`
Expected: Build succeeds

**Step 5: Commit any fixes if needed, then final commit**

```bash
git add -A
git commit -m "test: verify v2 data display backward compatibility"
```
