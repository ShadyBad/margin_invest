# Ungated Ticker Search Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let landing page visitors type a ticker and see a lightweight score summary without signing up.

**Architecture:** New public API endpoint (`GET /api/v1/public/score/{ticker}`) with a dedicated lightweight schema, plus a `HeroSearch` client component in the hero section that replaces the existing CTAs. The endpoint queries V4Score (published first, then any) with Score fallback, rate-limited at 30/min per IP, cached via `Cache-Control: public, max-age=300`.

**Tech Stack:** FastAPI + SQLAlchemy (API), Next.js 15 + React 19 (web), Vitest + @testing-library/react (web tests), pytest + pytest-asyncio (API tests)

**Design doc:** `docs/plans/2026-02-27-ungated-ticker-search-design.md`

---

### Task 1: PublicScoreResponse Schema

**Files:**
- Modify: `api/src/margin_api/schemas/scores.py` (add to end of file)
- Test: `api/tests/schemas/test_public_score_schema.py`

**Step 1: Write the failing test**

Create `api/tests/schemas/test_public_score_schema.py`:

```python
"""Tests for PublicScoreResponse schema."""

from margin_api.schemas.scores import PublicScoreFactorSummary, PublicScoreResponse


class TestPublicScoreResponse:
    def test_valid_scored_ticker(self):
        data = PublicScoreResponse(
            ticker="AAPL",
            company_name="Apple Inc",
            composite_score=78.5,
            composite_tier="high",
            signal="strong",
            factor_summary=PublicScoreFactorSummary(
                quality_percentile=72.0,
                value_percentile=81.0,
                momentum_percentile=65.0,
            ),
            eliminated=False,
            elimination_reason=None,
            scored_at="2026-02-27T12:00:00+00:00",
        )
        assert data.ticker == "AAPL"
        assert data.composite_score == 78.5
        assert data.factor_summary.quality_percentile == 72.0
        assert data.eliminated is False

    def test_eliminated_ticker(self):
        data = PublicScoreResponse(
            ticker="XYZ",
            company_name="XYZ Corp",
            composite_score=22.0,
            composite_tier="none",
            signal="failed",
            factor_summary=PublicScoreFactorSummary(
                quality_percentile=15.0,
                value_percentile=30.0,
                momentum_percentile=10.0,
            ),
            eliminated=True,
            elimination_reason="negative_earnings",
            scored_at="2026-02-27T12:00:00+00:00",
        )
        assert data.eliminated is True
        assert data.elimination_reason == "negative_earnings"

    def test_schema_does_not_leak_forensic_fields(self):
        """PublicScoreResponse must NOT have fields from ScoreResponse."""
        fields = set(PublicScoreResponse.model_fields.keys())
        forbidden = {
            "ml_alpha", "ml_confidence", "price_history", "signal_history",
            "sub_scores", "buy_price", "sell_price", "margin_invest_value",
            "opportunity_type", "track_a", "track_b", "track_c",
        }
        assert fields & forbidden == set()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/schemas/test_public_score_schema.py -v`
Expected: FAIL with `ImportError: cannot import name 'PublicScoreFactorSummary'`

**Step 3: Write minimal implementation**

Add to the end of `api/src/margin_api/schemas/scores.py`:

```python
class PublicScoreFactorSummary(BaseModel):
    """Factor percentiles exposed in the public (ungated) score response."""

    quality_percentile: float
    value_percentile: float
    momentum_percentile: float


class PublicScoreResponse(BaseModel):
    """Lightweight score summary for the public endpoint. No forensic detail."""

    ticker: str
    company_name: str
    composite_score: float
    composite_tier: str
    signal: str
    factor_summary: PublicScoreFactorSummary
    eliminated: bool
    elimination_reason: str | None = None
    scored_at: str
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/schemas/test_public_score_schema.py -v`
Expected: 3 passed

**Step 5: Commit**

```bash
git add api/src/margin_api/schemas/scores.py api/tests/schemas/test_public_score_schema.py
git commit -m "feat: add PublicScoreResponse schema for ungated ticker search"
```

---

### Task 2: Public Score Endpoint

**Files:**
- Create: `api/src/margin_api/routes/public_scores.py`
- Test: `api/tests/routes/test_public_scores.py`

**Step 1: Write the failing tests**

Create `api/tests/routes/test_public_scores.py`:

```python
"""Tests for the public score endpoint."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.base import Base
from margin_api.db.models import Asset, Score, V4Score
from margin_api.db.session import get_db


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


def _make_client(session_factory) -> TestClient:
    get_settings.cache_clear()

    async def db_override():
        async with session_factory() as s:
            yield s

    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-admin-key"}):
        app = create_app()
        app.dependency_overrides[get_db] = db_override
        client = TestClient(app)
    return client


async def _seed_asset(session: AsyncSession, ticker: str = "AAPL", name: str = "Apple Inc") -> Asset:
    asset = Asset(ticker=ticker, name=name, sector="Technology")
    session.add(asset)
    await session.flush()
    return asset


async def _seed_v4_score(
    session: AsyncSession,
    asset: Asset,
    published: bool = True,
    conviction: str = "high",
    composite_score: float = 78.5,
    detail: dict | None = None,
) -> V4Score:
    if detail is None:
        detail = {
            "quality": {"average_percentile": 72.0, "sub_scores": []},
            "value": {"average_percentile": 81.0, "sub_scores": []},
            "momentum": {"average_percentile": 65.0, "sub_scores": []},
            "filters_passed": [
                {"name": "positive_earnings", "passed": True, "value": 5.0, "threshold": 0.0},
            ],
            "signal": "strong",
        }
    v4 = V4Score(
        asset_id=asset.id,
        scored_at=datetime.now(UTC),
        opportunity_type="value_compounder",
        conviction=conviction,
        rules_conviction=conviction,
        style="value",
        timing_signal="accumulate",
        max_position_pct=5.0,
        regime="expansion",
        composite_score=composite_score,
        ml_override="none",
        detail=detail,
        published=published,
    )
    session.add(v4)
    await session.flush()
    return v4


async def _seed_base_score(
    session: AsyncSession,
    asset: Asset,
    quality_pct: float = 70.0,
    value_pct: float = 75.0,
    momentum_pct: float = 60.0,
) -> Score:
    score = Score(
        asset_id=asset.id,
        scored_at=datetime.now(UTC),
        composite_raw_score=68.0,
        composite_percentile=72.0,
        quality_percentile=quality_pct,
        value_percentile=value_pct,
        momentum_percentile=momentum_pct,
        conviction_level="medium",
        signal="stable",
        data_coverage=0.95,
        score_detail={
            "filters_passed": [
                {"name": "positive_earnings", "passed": True, "value": 5.0, "threshold": 0.0},
            ],
        },
    )
    session.add(score)
    await session.flush()
    return score


@pytest.mark.asyncio
class TestPublicScoreEndpoint:
    async def test_happy_path_published_v4(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        await _seed_v4_score(db_session, asset, published=True)
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["company_name"] == "Apple Inc"
        assert data["composite_score"] == 78.5
        assert data["composite_tier"] == "high"
        assert data["signal"] == "strong"
        assert data["factor_summary"]["quality_percentile"] == 72.0
        assert data["factor_summary"]["value_percentile"] == 81.0
        assert data["factor_summary"]["momentum_percentile"] == 65.0
        assert data["eliminated"] is False
        assert data["elimination_reason"] is None
        assert "scored_at" in data

    async def test_cache_control_header(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        await _seed_v4_score(db_session, asset)
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/AAPL")
        assert resp.headers.get("cache-control") == "public, max-age=300"

    async def test_fallback_to_unpublished_v4(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        await _seed_v4_score(db_session, asset, published=False)
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/AAPL")
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "AAPL"

    async def test_fallback_to_base_score(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        await _seed_base_score(db_session, asset)
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["factor_summary"]["quality_percentile"] == 70.0
        assert data["factor_summary"]["value_percentile"] == 75.0
        assert data["factor_summary"]["momentum_percentile"] == 60.0

    async def test_404_unknown_ticker(self, db_session, session_factory):
        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/ZZZZ")
        assert resp.status_code == 404

    async def test_eliminated_ticker(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        detail = {
            "quality": {"average_percentile": 15.0, "sub_scores": []},
            "value": {"average_percentile": 30.0, "sub_scores": []},
            "momentum": {"average_percentile": 10.0, "sub_scores": []},
            "filters_passed": [
                {"name": "positive_earnings", "passed": True, "value": 5.0, "threshold": 0.0},
                {"name": "debt_coverage", "passed": False, "value": 0.3, "threshold": 1.0},
            ],
            "signal": "failed",
        }
        await _seed_v4_score(db_session, asset, detail=detail, conviction="none")
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["eliminated"] is True
        assert data["elimination_reason"] == "debt_coverage"

    async def test_case_insensitive_ticker(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        await _seed_v4_score(db_session, asset)
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/aapl")
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "AAPL"

    async def test_response_does_not_contain_forensic_fields(self, db_session, session_factory):
        asset = await _seed_asset(db_session)
        await _seed_v4_score(db_session, asset)
        await db_session.commit()

        client = _make_client(session_factory)
        resp = client.get("/api/v1/public/score/AAPL")
        data = resp.json()
        forbidden = [
            "ml_alpha", "ml_confidence", "price_history", "signal_history",
            "buy_price", "sell_price", "margin_invest_value",
            "opportunity_type", "track_a", "track_b", "track_c",
            "sub_scores", "filters_passed",
        ]
        for field in forbidden:
            assert field not in data, f"Forensic field '{field}' leaked into public response"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/routes/test_public_scores.py -v`
Expected: FAIL (route module does not exist)

**Step 3: Write minimal implementation**

Create `api/src/margin_api/routes/public_scores.py`:

```python
"""Public (ungated) score endpoint — no auth required."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, Score, V4Score
from margin_api.db.session import get_db
from margin_api.middleware.rate_limit import limiter
from margin_api.schemas.scores import PublicScoreFactorSummary, PublicScoreResponse

router = APIRouter(prefix="/api/v1/public", tags=["public"])


def _extract_factor_percentiles_v4(detail: dict) -> PublicScoreFactorSummary:
    """Extract factor percentiles from V4Score detail JSONB."""
    quality = detail.get("quality", {})
    value = detail.get("value", {})
    momentum = detail.get("momentum", {})
    return PublicScoreFactorSummary(
        quality_percentile=quality.get("average_percentile", 0.0),
        value_percentile=value.get("average_percentile", 0.0),
        momentum_percentile=momentum.get("average_percentile", 0.0),
    )


def _check_eliminated(detail: dict) -> tuple[bool, str | None]:
    """Check if any filter failed. Returns (eliminated, reason)."""
    filters = detail.get("filters_passed", [])
    for f in filters:
        if not f.get("passed", True):
            return True, f.get("name")
    return False, None


@router.get("/score/{ticker}", response_model=PublicScoreResponse)
@limiter.limit("30/minute")
async def get_public_score(
    request: Request,
    ticker: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Return a lightweight score summary for any ticker. No auth required."""
    ticker = ticker.upper()

    # 1. Try published V4Score
    v4_published_q = (
        select(V4Score, Asset.ticker, Asset.name.label("asset_name"))
        .join(Asset, V4Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker, V4Score.published == True)  # noqa: E712
        .order_by(V4Score.scored_at.desc())
        .limit(1)
    )
    result = await db.execute(v4_published_q)
    row = result.first()

    # 2. Fallback: any V4Score
    if row is None:
        v4_any_q = (
            select(V4Score, Asset.ticker, Asset.name.label("asset_name"))
            .join(Asset, V4Score.asset_id == Asset.id)
            .where(Asset.ticker == ticker)
            .order_by(V4Score.scored_at.desc())
            .limit(1)
        )
        result = await db.execute(v4_any_q)
        row = result.first()

    if row is not None:
        v4 = row[0]
        detail = v4.detail or {}
        scored_at = v4.scored_at
        if scored_at is not None and scored_at.tzinfo is None:
            scored_at = scored_at.replace(tzinfo=UTC)

        factor_summary = _extract_factor_percentiles_v4(detail)
        eliminated, elimination_reason = _check_eliminated(detail)
        signal = detail.get("signal", "neutral")

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
        )
        return JSONResponse(
            content=data.model_dump(),
            headers={"Cache-Control": "public, max-age=300"},
        )

    # 3. Fallback: base Score
    score_q = (
        select(Score, Asset.ticker, Asset.name.label("asset_name"))
        .join(Asset, Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .order_by(Score.scored_at.desc())
        .limit(1)
    )
    result = await db.execute(score_q)
    row = result.first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"No score found for {ticker}")

    score = row[0]
    scored_at = score.scored_at
    if scored_at is not None and scored_at.tzinfo is None:
        scored_at = scored_at.replace(tzinfo=UTC)

    detail = score.score_detail or {}
    eliminated, elimination_reason = _check_eliminated(detail)

    data = PublicScoreResponse(
        ticker=row.ticker,
        company_name=row.asset_name or "",
        composite_score=score.composite_percentile,
        composite_tier=score.conviction_level or "none",
        signal=score.signal or "neutral",
        factor_summary=PublicScoreFactorSummary(
            quality_percentile=score.quality_percentile or 0.0,
            value_percentile=score.value_percentile or 0.0,
            momentum_percentile=score.momentum_percentile or 0.0,
        ),
        eliminated=eliminated,
        elimination_reason=elimination_reason,
        scored_at=scored_at.isoformat() if scored_at else "",
    )
    return JSONResponse(
        content=data.model_dump(),
        headers={"Cache-Control": "public, max-age=300"},
    )
```

**Step 4: Register the route in app.py**

In `api/src/margin_api/app.py`, add the import alongside other router imports:

```python
from margin_api.routes.public_scores import router as public_scores_router
```

And add to the route registration block (near the transparency router):

```python
app.include_router(public_scores_router)
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest api/tests/routes/test_public_scores.py -v`
Expected: 8 passed

**Step 6: Run full API test suite to check for regressions**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`
Expected: All existing tests still pass

**Step 7: Commit**

```bash
git add api/src/margin_api/routes/public_scores.py api/src/margin_api/app.py api/tests/routes/test_public_scores.py
git commit -m "feat: add public score endpoint for ungated ticker search"
```

---

### Task 3: HeroSearch Component

**Files:**
- Create: `web/src/components/landing/hero-search.tsx`
- Test: `web/src/components/landing/__tests__/hero-search.test.tsx`

**Step 1: Write the failing tests**

Create `web/src/components/landing/__tests__/hero-search.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { HeroSearch } from "../hero-search"

// Mock apiFetch
const mockApiFetch = vi.fn()
vi.mock("@/lib/api/client", () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
  ApiError: class extends Error {
    status: number
    errorCode: string
    constructor(status: number, errorCode: string, message?: string) {
      super(message)
      this.status = status
      this.errorCode = errorCode
    }
  },
}))

const MOCK_RESULT = {
  ticker: "AAPL",
  company_name: "Apple Inc",
  composite_score: 78.5,
  composite_tier: "high",
  signal: "strong",
  factor_summary: {
    quality_percentile: 72.0,
    value_percentile: 81.0,
    momentum_percentile: 65.0,
  },
  eliminated: false,
  elimination_reason: null,
  scored_at: "2026-02-27T12:00:00+00:00",
}

const MOCK_ELIMINATED = {
  ...MOCK_RESULT,
  ticker: "XYZ",
  company_name: "XYZ Corp",
  composite_score: 22.0,
  composite_tier: "none",
  signal: "failed",
  eliminated: true,
  elimination_reason: "negative_earnings",
}

describe("HeroSearch", () => {
  beforeEach(() => {
    mockApiFetch.mockReset()
  })

  it("renders search input and button", () => {
    render(<HeroSearch />)
    expect(screen.getByPlaceholderText(/search any ticker/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /search/i })).toBeInTheDocument()
  })

  it("shows loading state on submit", async () => {
    mockApiFetch.mockImplementation(() => new Promise(() => {})) // never resolves
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "AAPL" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByTestId("hero-search-loading")).toBeInTheDocument()
    })
  })

  it("shows result card with score data on success", async () => {
    mockApiFetch.mockResolvedValueOnce(MOCK_RESULT)
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "AAPL" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument()
      expect(screen.getByText("Apple Inc")).toBeInTheDocument()
      expect(screen.getByText("79")).toBeInTheDocument() // Math.round(78.5)
    })
  })

  it("shows factor percentile bars", async () => {
    mockApiFetch.mockResolvedValueOnce(MOCK_RESULT)
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "AAPL" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByText("Quality")).toBeInTheDocument()
      expect(screen.getByText("Value")).toBeInTheDocument()
      expect(screen.getByText("Momentum")).toBeInTheDocument()
    })
  })

  it("shows eliminated badge for eliminated tickers", async () => {
    mockApiFetch.mockResolvedValueOnce(MOCK_ELIMINATED)
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "XYZ" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByText(/eliminated/i)).toBeInTheDocument()
      expect(screen.getByText(/negative_earnings/i)).toBeInTheDocument()
    })
  })

  it("shows error for 404 response", async () => {
    const { ApiError } = await import("@/lib/api/client")
    mockApiFetch.mockRejectedValueOnce(new ApiError(404, "NOT_FOUND", "No score found for ZZZZ"))
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "ZZZZ" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByText(/not found/i)).toBeInTheDocument()
    })
  })

  it("shows generic error for network failure", async () => {
    mockApiFetch.mockRejectedValueOnce(new Error("Network error"))
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "AAPL" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    })
  })

  it("CTA links to /onboarding", async () => {
    mockApiFetch.mockResolvedValueOnce(MOCK_RESULT)
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "AAPL" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      const link = screen.getByRole("link", { name: /full forensic report/i })
      expect(link).toHaveAttribute("href", "/onboarding")
    })
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/landing/__tests__/hero-search.test.tsx`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

Create `web/src/components/landing/hero-search.tsx`:

```tsx
"use client"

import { useState, type FormEvent } from "react"
import Link from "next/link"
import { apiFetch, ApiError } from "@/lib/api/client"

interface FactorSummary {
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
}

interface PublicScoreResult {
  ticker: string
  company_name: string
  composite_score: number
  composite_tier: string
  signal: string
  factor_summary: FactorSummary
  eliminated: boolean
  elimination_reason: string | null
  scored_at: string
}

type SearchState = "idle" | "loading" | "result" | "error"

const TIER_COLORS: Record<string, string> = {
  exceptional: "text-[var(--color-bullish)]",
  high: "text-[var(--color-bullish)]",
  medium: "text-[var(--color-warning)]",
  none: "text-text-tertiary",
}

const SIGNAL_LABELS: Record<string, string> = {
  strong: "Strong",
  stable: "Stable",
  emerging: "Emerging",
  weak: "Weak",
  failed: "Failed",
  neutral: "Neutral",
}

export function HeroSearch() {
  const [query, setQuery] = useState("")
  const [state, setState] = useState<SearchState>("idle")
  const [result, setResult] = useState<PublicScoreResult | null>(null)
  const [error, setError] = useState("")

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const ticker = query.trim().toUpperCase()
    if (!ticker) return

    setState("loading")
    setError("")
    setResult(null)

    try {
      const data = await apiFetch<PublicScoreResult>(
        `/api/v1/public/score/${ticker}`
      )
      setResult(data)
      setState("result")
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("Ticker not found. Check the symbol and try again.")
      } else {
        setError("Something went wrong. Please try again.")
      }
      setState("error")
    }
  }

  const factors = result
    ? [
        { label: "Quality", value: result.factor_summary.quality_percentile },
        { label: "Value", value: result.factor_summary.value_percentile },
        { label: "Momentum", value: result.factor_summary.momentum_percentile },
      ]
    : []

  return (
    <div data-hero-ctas>
      <form onSubmit={handleSubmit} className="flex gap-2 max-w-md">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onBlur={() => setQuery((q) => q.toUpperCase())}
          placeholder="Search any ticker..."
          className="flex-1 px-4 py-3 bg-bg-subtle border border-border-subtle rounded text-text-primary font-mono text-sm placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-colors"
          disabled={state === "loading"}
        />
        <button
          type="submit"
          disabled={state === "loading" || !query.trim()}
          aria-label="Search"
          className="px-5 py-3 bg-accent text-bg-primary font-medium text-sm rounded hover:bg-accent/90 transition-colors disabled:opacity-50"
        >
          {state === "loading" ? (
            <span data-testid="hero-search-loading" className="inline-block w-4 h-4 border-2 border-bg-primary border-t-transparent rounded-full animate-spin" />
          ) : (
            "Search"
          )}
        </button>
      </form>

      {/* Result card */}
      {state === "result" && result && (
        <div className="terminal-card p-5 mt-4 max-w-md animate-in fade-in duration-200">
          {/* Header: ticker + name */}
          <div className="flex items-center justify-between mb-3">
            <div>
              <span className="font-mono text-lg font-bold text-text-primary">
                {result.ticker}
              </span>
              <span className="text-sm text-text-secondary ml-2">
                {result.company_name}
              </span>
            </div>
            {result.eliminated && (
              <span className="text-xs font-mono uppercase tracking-wider text-[var(--color-bearish)] bg-[var(--color-bearish)]/10 px-2 py-0.5 rounded">
                Eliminated
              </span>
            )}
          </div>

          {/* Elimination reason */}
          {result.eliminated && result.elimination_reason && (
            <p className="text-xs text-[var(--color-bearish)] mb-3 font-mono">
              Failed: {result.elimination_reason}
            </p>
          )}

          {/* Score + tier + signal */}
          <div className="flex items-end gap-3 mb-4">
            <span className={`font-mono text-4xl font-bold ${TIER_COLORS[result.composite_tier] || "text-text-primary"}`}>
              {Math.round(result.composite_score)}
            </span>
            <div className="pb-1">
              <span className="text-xs uppercase tracking-wider text-text-tertiary">
                {result.composite_tier}
              </span>
              <span className="text-xs text-text-tertiary mx-1.5">·</span>
              <span className="text-xs text-text-secondary">
                {SIGNAL_LABELS[result.signal] || result.signal}
              </span>
            </div>
          </div>

          {/* Factor bars */}
          <div className="space-y-2 mb-4">
            {factors.map((factor) => (
              <div key={factor.label} className="flex items-center gap-2">
                <span className="text-xs text-text-secondary w-20 shrink-0">
                  {factor.label}
                </span>
                <div className="flex-1 h-1.5 bg-bg-subtle rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-500"
                    style={{ width: `${factor.value}%` }}
                  />
                </div>
                <span className="font-mono text-xs text-text-secondary w-8 text-right">
                  {Math.round(factor.value)}
                </span>
              </div>
            ))}
          </div>

          {/* CTA */}
          <Link
            href="/onboarding"
            className="text-sm text-accent hover:text-accent/80 transition-colors"
          >
            See the full forensic report &rarr;
          </Link>
        </div>
      )}

      {/* Error state */}
      {state === "error" && (
        <p className="text-sm text-[var(--color-bearish)] mt-3 max-w-md">
          {error}
        </p>
      )}
    </div>
  )
}
```

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/hero-search.test.tsx`
Expected: 8 passed

**Step 5: Commit**

```bash
git add web/src/components/landing/hero-search.tsx web/src/components/landing/__tests__/hero-search.test.tsx
git commit -m "feat: add HeroSearch component for ungated ticker search"
```

---

### Task 4: Wire HeroSearch into Hero Section

**Files:**
- Modify: `web/src/components/landing/hero-section.tsx`
- Modify: `web/src/components/landing/__tests__/hero-section.test.tsx`

**Step 1: Update the hero section test**

In `web/src/components/landing/__tests__/hero-section.test.tsx`, the CTA tests need to change. The "Open the Dashboard" and "See the Methodology" links are being replaced by the search component.

Replace the test file content — keep the GSAP mocks and working tests, update the CTA tests:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("gsap", () => ({
  default: {
    registerPlugin: vi.fn(),
    to: vi.fn(),
    fromTo: vi.fn(),
    set: vi.fn(),
    timeline: vi.fn(() => ({
      to: vi.fn().mockReturnThis(),
      fromTo: vi.fn().mockReturnThis(),
      play: vi.fn(),
      pause: vi.fn(),
      kill: vi.fn(),
    })),
  },
}))
vi.mock("gsap/ScrollTrigger", () => ({
  default: { create: vi.fn(), getAll: () => [], refresh: vi.fn() },
}))
// Mock apiFetch for HeroSearch
vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
  ApiError: class extends Error {
    status: number
    errorCode: string
    constructor(status: number, errorCode: string, message?: string) {
      super(message)
      this.status = status
      this.errorCode = errorCode
    }
  },
}))

import { HeroSection } from "../hero-section"

describe("HeroSection", () => {
  it("renders Discipline. and Engineered.", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("Discipline.")).toBeInTheDocument()
    expect(screen.getByText("Engineered.")).toBeInTheDocument()
  })

  it("renders subheadline about deterministic capital allocation", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText(/deterministic capital allocation/)).toBeInTheDocument()
  })

  it("renders search input instead of old CTAs", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByPlaceholderText(/search any ticker/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /search/i })).toBeInTheDocument()
  })

  it("shows AAPL from fallback when data is null", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
  })

  it("renders search-any-ticker call to action in subtext", () => {
    render(<HeroSection data={null} />)
    expect(screen.getByText(/search any ticker/i)).toBeInTheDocument()
    expect(screen.getByText(/quantitative evidence/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run the updated test to see it fail**

Run: `cd web && npx vitest run src/components/landing/__tests__/hero-section.test.tsx`
Expected: FAIL on "renders search input instead of old CTAs" (search input not yet in hero-section.tsx)

**Step 3: Update hero-section.tsx**

In `web/src/components/landing/hero-section.tsx`:

1. Add import for `HeroSearch`:
```tsx
import { HeroSearch } from "./hero-search"
```

2. Replace the CTA `<div>` (the `<div data-hero-ctas>` block containing the two `<Link>` elements) with:
```tsx
<HeroSearch />
```

The `data-hero-ctas` attribute is already on the root div of `HeroSearch`, so the GSAP animation still picks it up.

**Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/hero-section.test.tsx`
Expected: 5 passed

**Step 5: Run full web test suite**

Run: `cd web && npx vitest run`
Expected: All tests pass (no regressions)

**Step 6: Commit**

```bash
git add web/src/components/landing/hero-section.tsx web/src/components/landing/__tests__/hero-section.test.tsx
git commit -m "feat: wire HeroSearch into hero section, replacing CTA buttons"
```

---

### Task 5: Final Integration Test & Cleanup

**Step 1: Run full API test suite**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`
Expected: All tests pass

**Step 2: Run full web test suite**

Run: `cd web && npx vitest run`
Expected: All tests pass

**Step 3: Visual sanity check (optional)**

Start the dev server and verify:
- Landing page loads
- Search input appears where CTAs used to be
- Rotating candidate card still works on the right
- Typing a ticker and pressing Enter shows a result (or 404 if not in DB)

**Step 4: Final commit if any cleanup needed**

```bash
git add -A && git commit -m "chore: cleanup after ungated ticker search integration"
```
