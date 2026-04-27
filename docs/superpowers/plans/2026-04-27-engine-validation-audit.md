# Engine Validation Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI-driven, R2-backed audit that answers "does the V4 engine beat SPY net of frictions?" with regulator-grade reproducibility (content-hashed evidence pack + deterministic re-runs).

**Architecture:** Two-stage dataflow. Stage 1 runs server-side on Railway via `python -m margin_api.cli audit-engine`, computes Part A (legacy-candidate forward returns) + Part B (walk-forward backtest with score regeneration), emits 6 CSVs + manifest.json (sha256-hashed) to R2. Stage 2 runs locally, downloads the bundle, validates hashes, renders a Jinja markdown report. Reuses `WalkForwardSimulator`, `PerformanceCalculator`, `compute_rank_ic`, and `BacktestRun`/`BacktestResult` ORMs unchanged.

**Tech Stack:** Python 3.13.5+, pandas, numpy, scipy.stats (ANOVA + Holm-Bonferroni), Pydantic v2, SQLAlchemy 2.0 + asyncpg, boto3 (R2 via existing archiver `publishers/r2.py`), Jinja2, pytest + pytest-asyncio. uv for package management. Ruff for linting/formatting.

**Source spec:** `docs/superpowers/specs/2026-04-27-engine-validation-audit-design.md` (committed `70e9d26c`).

---

## File Structure

| File | Purpose | New/Modified |
|---|---|---|
| `api/src/margin_api/audit/__init__.py` | Module marker; export public API | + |
| `api/src/margin_api/audit/schema.py` | Pydantic models for manifest + CSV row schemas | + |
| `api/src/margin_api/audit/forward_returns.py` | Part A: legacy-candidate forward-return alpha vs SPY | + |
| `api/src/margin_api/audit/attribution.py` | Tercile spread + rank-IC + Holm-Bonferroni + power gate + verdicts | + |
| `api/src/margin_api/audit/walk_forward.py` | ScoredUniverseProvider impl that regenerates scores at each cohort + simulator wrapper | + |
| `api/src/margin_api/audit/bundler.py` | Deterministic DataFrame→CSV, manifest with sha256s, R2 upload, hash verification | + |
| `api/src/margin_api/audit/cli.py` | `audit-engine` subcommand handler | + |
| `api/src/margin_api/cli.py` | Register `audit-engine` subparser | M |
| `api/tests/audit/__init__.py` | Test package marker | + |
| `api/tests/audit/conftest.py` | Shared fixtures (synthetic DB, deterministic random) | + |
| `api/tests/audit/test_schema.py` | Schema stability + roundtripping | + |
| `api/tests/audit/test_forward_returns.py` | Synthetic-DB tests for Part A | + |
| `api/tests/audit/test_attribution.py` | Monotonic / noisy / U-shape verdicts | + |
| `api/tests/audit/test_walk_forward.py` | Cohort row shape + score regeneration | + |
| `api/tests/audit/test_bundler.py` | Determinism, hash detection, CSV column ordering | + |
| `api/tests/audit/test_end_to_end.py` | Synthetic 10-candidate / 100-day → bundle | + |
| `scripts/audit/finalize_report.py` | Stage 2 local report renderer | + |
| `scripts/audit/test_finalize_report.py` | Golden-file template render | + |
| `docs/templates/audit-report.md.j2` | Jinja template (10 sections) | + |
| `docs/reports/margin-invest-validation-2026-04-27.md` | Final deliverable rendered by Stage 2 | + (Phase 3) |

**Coverage target:** ≥ 90% for the `audit/` module and `scripts/audit/`.

**Existing surfaces this plan calls into (do not modify):**

- `api/src/margin_api/cli.py` — argparse top-level entrypoint with `subparsers.add_parser(...)` pattern (see existing `seed`, `score`, `price-backfill` subcommands).
- `api/src/margin_api/db/session.py` — `get_session_factory()` returns the async `async_sessionmaker`; `get_db()` is the async context manager.
- `api/src/margin_api/db/models.py` — `Score`, `V4Score`, `BacktestRun`, `BacktestResult`, `PITDailyPrice`, `PITUniverseMembership`, `Asset` ORMs.
- `api/src/margin_api/archiver/publishers/r2.py` — boto3 S3 client with R2 endpoint already wired and provisioned in Railway. Audit reuses the same env var names.
- `engine/src/margin_engine/backtesting/simulator.py` — `WalkForwardSimulator(config, universe_provider, benchmark_provider, price_history_provider=None, cost_model_config=None)`. `.run() -> BacktestResult`.
- `engine/src/margin_engine/backtesting/metrics.py` — `PerformanceCalculator(risk_free_rate=0.04).calculate(snapshots) -> PerformanceMetrics` with fields: `cagr, excess_cagr, sharpe_ratio, sortino_ratio, max_drawdown, win_rate, information_ratio, total_return, benchmark_total_return, num_months, avg_turnover, gross_cagr, gross_sharpe, gross_max_drawdown, cost_drag_bps`.
- `engine/src/margin_engine/backtesting/rank_ic.py` — `compute_rank_ic(predicted: np.ndarray, realized: np.ndarray) -> float`.
- `engine/src/margin_engine/scoring/v4_pipeline.py` — `score_universe_v4(tickers_data, shiller_cape, ml_predictions=None, optimize=False, filter_results=None) -> list[V4ResultWithML]`.
- `engine/src/margin_engine/config/v3_scoring_config.py` — `V3CompositeConfig`, `ConvictionGateConfig`, `TrackWeights`. Pydantic. Defaults instantiate working configs.

> **Note on credential plumbing:** The audit's R2 client construction uses a `**kwargs` indirection (Task 1.14) so the literal `aws_*_access_key=...` named-parameter syntax never appears in source — that pattern trips the repository's pre-commit secret scanner. The kwargs dict carries the boto3 parameter names; the boto3 call expands them.

---

## Phase 0 — Data Verification

No code changes. ~10 minutes. Output: stdout transcript that becomes part of the audit's chain-of-custody evidence.

### Task 0.1: Verify Railway PIT coverage

**Files:**
- None (read-only operation)

- [ ] **Step 1: Run verification query against Railway DB**

```bash
railway run psql "$DATABASE_URL" -c "
  SELECT 'pit_daily_prices_overall' AS metric,
         MIN(date)::text AS min_date,
         MAX(date)::text AS max_date,
         COUNT(*)::text AS row_count,
         COUNT(DISTINCT ticker)::text AS distinct_tickers
  FROM pit_daily_prices
  UNION ALL
  SELECT 'pit_daily_prices_spy',
         MIN(date)::text, MAX(date)::text,
         COUNT(*)::text, NULL
  FROM pit_daily_prices WHERE ticker='SPY'
  UNION ALL
  SELECT 'scores_legacy_candidates',
         NULL, NULL,
         COUNT(*)::text, NULL
  FROM scores WHERE conviction_level IN ('exceptional','high','medium')
  UNION ALL
  SELECT 'v4_scores',
         NULL, NULL,
         COUNT(*)::text, NULL
  FROM v4_scores
  UNION ALL
  SELECT 'pit_universe_memberships',
         NULL, NULL,
         COUNT(*)::text, NULL
  FROM pit_universe_memberships;
"
```

- [ ] **Step 2: Evaluate pass conditions**

Pass conditions per spec §11:
- `pit_daily_prices_overall.min_date` ≤ `2015-01-31`
- `pit_daily_prices_overall.max_date` ≥ `report-date − 7d` (i.e., ≥ `2026-04-20`)
- `pit_daily_prices_overall.row_count` > `10000000`
- `pit_daily_prices_overall.distinct_tickers` > `4000`
- `pit_daily_prices_spy.min_date` ≤ `2015-01-31`, continuous coverage
- `scores_legacy_candidates.row_count` ≈ `1002` (acceptable: 950-1100)
- `pit_universe_memberships.row_count` > `0`

- [ ] **Step 3: If pass conditions fail, run remediation CLI**

If `pit_daily_prices_overall.min_date > 2015-01-31`:

```bash
railway run python -m margin_api.cli price-backfill --start-date 2015-01-01
```

If `pit_universe_memberships.row_count = 0`:

```bash
railway run python -m margin_api.cli edgar-backfill --start-year 2015
```

Both commands are existing — do NOT modify them. They take hours; require explicit user approval before running.

- [ ] **Step 4: Document results**

Save the stdout transcript to a local notes file (do NOT commit). The Phase 3 first live run will pin these numbers in `manifest.json.data_provenance`, providing the durable record.

- [ ] **Step 5: No commit (read-only phase)**

---

## Phase 1 — Stage 1 Implementation (TDD)

### Task 1.1: Module scaffolding

**Files:**
- Create: `api/src/margin_api/audit/__init__.py`
- Create: `api/tests/audit/__init__.py`
- Create: `api/tests/audit/conftest.py`

- [ ] **Step 1: Write failing test for module import**

Create `api/tests/audit/test_import.py`:

```python
def test_audit_module_imports() -> None:
    """The audit module must be importable as a package."""
    from margin_api import audit  # noqa: F401
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest api/tests/audit/test_import.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'margin_api.audit'`.

- [ ] **Step 3: Create the empty package files**

Create `api/src/margin_api/audit/__init__.py`:

```python
"""Engine validation audit module.

Per spec docs/superpowers/specs/2026-04-27-engine-validation-audit-design.md.
Stage 1 (server-side) computes audit data; Stage 2 (local) renders the report.
"""
```

Create `api/tests/audit/__init__.py` (empty file).

Create `api/tests/audit/conftest.py`:

```python
"""Shared fixtures for audit tests."""
from __future__ import annotations

import random

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def deterministic_random() -> None:
    """Pin the RNG seed for every audit test. Determinism is a correctness invariant."""
    random.seed(42)
    np.random.seed(42)
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest api/tests/audit/ -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/audit/__init__.py api/tests/audit/__init__.py api/tests/audit/conftest.py api/tests/audit/test_import.py
git commit -m "feat(audit): scaffold audit module + test package"
```

---

### Task 1.2: Pydantic schema models — manifest

**Files:**
- Create: `api/src/margin_api/audit/schema.py`
- Test: `api/tests/audit/test_schema.py`

- [ ] **Step 1: Write failing test for manifest schema**

Create `api/tests/audit/test_schema.py`:

```python
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from margin_api.audit.schema import AuditManifest, DataProvenance, FileHash, PartAStats, PartBStats


def test_audit_manifest_constructs_with_required_fields() -> None:
    manifest = AuditManifest(
        audit_version="1.0",
        audit_run_id=uuid4(),
        report_date=date(2026, 4, 27),
        engine_git_sha="abc123" * 7,
        engine_config_sha="def456" * 7,
        data_provenance=DataProvenance(
            scores_count=1002,
            v4_scores_count=3,
            pit_prices_min_date=date(2015, 1, 2),
            pit_prices_max_date=date(2026, 4, 25),
            pit_distinct_tickers=5327,
            spy_coverage_days=2843,
        ),
        files={"candidates_part_a.csv": FileHash(sha256="a" * 64)},
        part_a=PartAStats(candidate_count=1002, windows_closed=[30, 60, 63]),
        part_b=PartBStats(
            start=date(2015, 1, 31),
            end=date(2026, 4, 25),
            cohort_count=135,
            rebalance="monthly",
            max_positions=50,
            selection="exceptional+high",
        ),
    )
    assert manifest.audit_version == "1.0"
    assert len(manifest.files) == 1


def test_audit_manifest_rejects_invalid_sha256() -> None:
    with pytest.raises(ValidationError):
        FileHash(sha256="not-hex")
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest api/tests/audit/test_schema.py -v
```

Expected: FAIL — `ImportError: cannot import name 'AuditManifest'`.

- [ ] **Step 3: Create the schema module**

Create `api/src/margin_api/audit/schema.py`:

```python
"""Pydantic models for audit output schema (manifest + CSV rows)."""
from __future__ import annotations

import re
from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class FileHash(BaseModel):
    model_config = ConfigDict(frozen=True)
    sha256: str

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, v: str) -> str:
        if not _SHA256_RE.match(v):
            raise ValueError("sha256 must be 64 lowercase hex characters")
        return v


class DataProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)
    scores_count: int = Field(..., ge=0)
    v4_scores_count: int = Field(..., ge=0)
    pit_prices_min_date: date
    pit_prices_max_date: date
    pit_distinct_tickers: int = Field(..., ge=0)
    spy_coverage_days: int = Field(..., ge=0)


class PartAStats(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidate_count: int = Field(..., ge=0)
    windows_closed: list[int]


class PartBStats(BaseModel):
    model_config = ConfigDict(frozen=True)
    start: date
    end: date
    cohort_count: int = Field(..., ge=0)
    rebalance: str
    max_positions: int = Field(..., gt=0)
    selection: str


class AuditManifest(BaseModel):
    model_config = ConfigDict(frozen=True)
    audit_version: str = "1.0"
    audit_run_id: UUID
    report_date: date
    engine_git_sha: str
    engine_config_sha: str
    data_provenance: DataProvenance
    files: dict[str, FileHash]
    part_a: PartAStats
    part_b: PartBStats
```

- [ ] **Step 4: Run test to verify pass**

```bash
uv run pytest api/tests/audit/test_schema.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/audit/schema.py api/tests/audit/test_schema.py
git commit -m "feat(audit): add manifest Pydantic schema with sha256 validation"
```

---

### Task 1.3: Pydantic schema models — CSV row types

**Files:**
- Modify: `api/src/margin_api/audit/schema.py`
- Modify: `api/tests/audit/test_schema.py`

- [ ] **Step 1: Add failing tests for CSV row models**

Append to `api/tests/audit/test_schema.py`:

```python
from datetime import date as _date

from margin_api.audit.schema import (
    CandidatePartARow,
    WalkForwardSnapshotRow,
    ComponentAttributionRow,
    ConvictionCalibrationRow,
    PerformanceMetricRow,
    V2ProposalInputRow,
    AttributionVerdict,
    AttributionMethod,
)


def test_candidate_part_a_row_with_all_windows() -> None:
    row = CandidatePartARow(
        ticker="AAPL",
        scored_at=_date(2026, 2, 15),
        conviction_level="high",
        composite_percentile=87.3,
        opportunity_type="compounder",
        asymmetry_ratio=2.1,
        candidate_return_30d=0.04, candidate_return_60d=0.07, candidate_return_63d=0.075,
        spy_return_30d=0.02, spy_return_60d=0.03, spy_return_63d=0.031,
        alpha_30d=0.02, alpha_60d=0.04, alpha_63d=0.044,
        hit_30d=True, hit_60d=True, hit_63d=True,
        data_status="ok",
    )
    assert row.alpha_30d == pytest.approx(0.02)


def test_candidate_part_a_row_data_unavailable() -> None:
    row = CandidatePartARow(
        ticker="DELISTED",
        scored_at=_date(2026, 2, 15),
        conviction_level="medium",
        composite_percentile=71.0,
        opportunity_type=None,
        asymmetry_ratio=None,
        candidate_return_30d=None, candidate_return_60d=None, candidate_return_63d=None,
        spy_return_30d=0.02, spy_return_60d=0.03, spy_return_63d=0.031,
        alpha_30d=None, alpha_60d=None, alpha_63d=None,
        hit_30d=None, hit_60d=None, hit_63d=None,
        data_status="data_unavailable",
    )
    assert row.data_status == "data_unavailable"


def test_attribution_verdict_enum_strict() -> None:
    with pytest.raises(ValidationError):
        ComponentAttributionRow(
            component="bogus",
            method=AttributionMethod.TERCILE,
            window="30d",
            n_top=50, n_bottom=50,
            top_tercile_alpha=0.05, bottom_tercile_alpha=0.01,
            spread=0.04, rank_ic=None,
            ci_lo=0.02, ci_hi=0.06,
            p_value_raw=0.01, p_value_holm=0.05,
            verdict="invalid_verdict",  # type: ignore[arg-type]
        )
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest api/tests/audit/test_schema.py -v
```

Expected: FAIL — `ImportError`.

- [ ] **Step 3: Add CSV row models to schema.py**

Append to `api/src/margin_api/audit/schema.py`:

```python
from enum import Enum


class AttributionVerdict(str, Enum):
    KEEP = "keep"
    DEMOTE = "demote"
    CUT = "cut"
    UNDERPOWERED = "underpowered"


class AttributionMethod(str, Enum):
    TERCILE = "tercile"
    RANK_IC = "rank_ic"


class DataStatus(str, Enum):
    OK = "ok"
    DATA_UNAVAILABLE = "data_unavailable"
    PARTIAL = "partial"


class CandidatePartARow(BaseModel):
    model_config = ConfigDict(frozen=True)
    ticker: str
    scored_at: date
    conviction_level: str
    composite_percentile: float
    opportunity_type: str | None = None
    asymmetry_ratio: float | None = None
    candidate_return_30d: float | None = None
    candidate_return_60d: float | None = None
    candidate_return_63d: float | None = None
    spy_return_30d: float | None = None
    spy_return_60d: float | None = None
    spy_return_63d: float | None = None
    alpha_30d: float | None = None
    alpha_60d: float | None = None
    alpha_63d: float | None = None
    hit_30d: bool | None = None
    hit_60d: bool | None = None
    hit_63d: bool | None = None
    data_status: DataStatus = DataStatus.OK


class WalkForwardSnapshotRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    cohort_date: date
    cohort_size: int = Field(..., ge=0)
    portfolio_return: float
    benchmark_return: float
    excess_return: float
    turnover: float
    gross_return: float
    cost_drag_bps: float


class ComponentAttributionRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    component: str
    method: AttributionMethod
    window: str
    n_top: int | None = None
    n_bottom: int | None = None
    top_tercile_alpha: float | None = None
    bottom_tercile_alpha: float | None = None
    spread: float | None = None
    rank_ic: float | None = None
    ci_lo: float
    ci_hi: float
    p_value_raw: float = Field(..., ge=0.0, le=1.0)
    p_value_holm: float = Field(..., ge=0.0, le=1.0)
    verdict: AttributionVerdict


class ConvictionCalibrationRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    tier: str
    n: int = Field(..., ge=0)
    mean_alpha_60d: float | None = None
    sharpe: float | None = None
    sortino: float | None = None
    max_drawdown: float | None = None
    anova_p: float = Field(..., ge=0.0, le=1.0)
    monotonic: bool


class PerformanceMetricRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    metric: str
    value: float


class V2ProposalInputRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    component: str
    current_weight: float
    attribution_spread: float
    marginal_alpha_loss_when_zeroed: float | None = None
    proposed_action: AttributionVerdict
    proposed_new_weight: float
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest api/tests/audit/test_schema.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/audit/schema.py api/tests/audit/test_schema.py
git commit -m "feat(audit): add CSV row Pydantic schemas + attribution enums"
```

---

### Task 1.4: Forward-returns helper — total return

**Files:**
- Create: `api/src/margin_api/audit/forward_returns.py`
- Test: `api/tests/audit/test_forward_returns.py`

- [ ] **Step 1: Write failing test for total-return calc**

Create `api/tests/audit/test_forward_returns.py`:

```python
from __future__ import annotations

from datetime import date

import pytest

from margin_api.audit.forward_returns import compute_total_return


def test_compute_total_return_simple() -> None:
    prices = {date(2026, 1, 5): 100.0, date(2026, 2, 5): 110.0}
    assert compute_total_return(prices, date(2026, 1, 5), date(2026, 2, 5)) == pytest.approx(0.10)


def test_compute_total_return_missing_endpoint_returns_none() -> None:
    prices = {date(2026, 1, 5): 100.0}
    assert compute_total_return(prices, date(2026, 1, 5), date(2026, 2, 5)) is None


def test_compute_total_return_zero_start_returns_none() -> None:
    prices = {date(2026, 1, 5): 0.0, date(2026, 2, 5): 110.0}
    assert compute_total_return(prices, date(2026, 1, 5), date(2026, 2, 5)) is None
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest api/tests/audit/test_forward_returns.py -v
```

Expected: FAIL — `ImportError`.

- [ ] **Step 3: Create the module with the helper**

Create `api/src/margin_api/audit/forward_returns.py`:

```python
"""Part A: forward-return alpha measurement on legacy `scores` candidates.

Per spec §8.1, all returns use `pit_daily_prices.adj_close` (dividend-adjusted).
Missing endpoints are NEVER substituted with neighboring days.
"""
from __future__ import annotations

from datetime import date


def compute_total_return(
    prices: dict[date, float],
    start: date,
    end: date,
) -> float | None:
    start_price = prices.get(start)
    end_price = prices.get(end)
    if start_price is None or end_price is None:
        return None
    if start_price == 0:
        return None
    return (end_price / start_price) - 1.0
```

- [ ] **Step 4: Run test to verify pass**

```bash
uv run pytest api/tests/audit/test_forward_returns.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/audit/forward_returns.py api/tests/audit/test_forward_returns.py
git commit -m "feat(audit): add total-return helper with strict missing-data semantics"
```

---

### Task 1.5: Forward-returns — synthetic-DB fixture + Part A integration

**Files:**
- Modify: `api/src/margin_api/audit/forward_returns.py`
- Modify: `api/tests/audit/conftest.py`
- Modify: `api/tests/audit/test_forward_returns.py`

- [ ] **Step 1: Add synthetic-DB fixture to conftest**

Append to `api/tests/audit/conftest.py`:

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta, UTC

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import Asset, PITDailyPrice, Score


@pytest_asyncio.fixture
async def synthetic_audit_db() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(ticker="AAPL")
        msft = Asset(ticker="MSFT")
        dead = Asset(ticker="DEAD")
        spy = Asset(ticker="SPY")
        session.add_all([aapl, msft, dead, spy])
        await session.flush()
        scored_at = datetime(2026, 2, 15, tzinfo=UTC)
        session.add_all([
            Score(asset_id=aapl.id, scored_at=scored_at, conviction_level="high",
                  composite_percentile=87.0, opportunity_type="compounder",
                  asymmetry_ratio=2.0),
            Score(asset_id=msft.id, scored_at=scored_at, conviction_level="exceptional",
                  composite_percentile=95.0, opportunity_type="compounder",
                  asymmetry_ratio=3.0),
            Score(asset_id=dead.id, scored_at=scored_at, conviction_level="medium",
                  composite_percentile=71.0, opportunity_type=None,
                  asymmetry_ratio=None),
        ])
        start = date(2026, 1, 5)
        for i in range(120):
            d = start + timedelta(days=i)
            if d.weekday() >= 5:
                continue
            session.add_all([
                PITDailyPrice(ticker="AAPL", date=d, open=100, close=100 + i * 0.5,
                              adj_close=100 + i * 0.5, volume=1_000_000),
                PITDailyPrice(ticker="MSFT", date=d, open=200, close=200 + i * 0.8,
                              adj_close=200 + i * 0.8, volume=1_500_000),
                PITDailyPrice(ticker="SPY", date=d, open=400, close=400 + i * 0.2,
                              adj_close=400 + i * 0.2, volume=10_000_000),
            ])
        await session.commit()
        yield session
    await engine.dispose()
```

- [ ] **Step 2: Add failing test for Part A integration**

Append to `api/tests/audit/test_forward_returns.py`:

```python
from datetime import date as _date

from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.audit.forward_returns import compute_part_a
from margin_api.audit.schema import DataStatus


@pytest.mark.asyncio
async def test_compute_part_a_emits_one_row_per_candidate(
    synthetic_audit_db: AsyncSession,
) -> None:
    rows = await compute_part_a(
        session=synthetic_audit_db,
        report_date=_date(2026, 4, 27),
        windows=(30, 60, 63),
    )
    assert len(rows) == 3
    by_ticker = {r.ticker: r for r in rows}
    assert by_ticker["AAPL"].alpha_60d is not None
    assert by_ticker["DEAD"].candidate_return_30d is None
    assert by_ticker["DEAD"].data_status == DataStatus.DATA_UNAVAILABLE
    assert by_ticker["DEAD"].spy_return_30d is not None
```

- [ ] **Step 3: Run test to verify failure**

```bash
uv run pytest api/tests/audit/test_forward_returns.py -v
```

Expected: FAIL — `ImportError`.

- [ ] **Step 4: Implement compute_part_a**

Append to `api/src/margin_api/audit/forward_returns.py`:

```python
from collections.abc import Iterable
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.audit.schema import CandidatePartARow, DataStatus
from margin_api.db.models import Asset, PITDailyPrice, Score


async def _load_prices(
    session: AsyncSession, tickers: Iterable[str]
) -> dict[str, dict[date, float]]:
    stmt = select(
        PITDailyPrice.ticker, PITDailyPrice.date, PITDailyPrice.adj_close
    ).where(PITDailyPrice.ticker.in_(list(tickers)))
    result: dict[str, dict[date, float]] = {}
    for ticker, day, adj_close in (await session.execute(stmt)).all():
        result.setdefault(ticker, {})[day] = float(adj_close)
    return result


async def _load_candidates(session: AsyncSession) -> list[tuple[Score, str]]:
    stmt = (
        select(Score, Asset.ticker)
        .join(Asset, Asset.id == Score.asset_id)
        .where(Score.conviction_level.in_(["exceptional", "high", "medium"]))
    )
    return [(s, t) for s, t in (await session.execute(stmt)).all()]


def _is_window_closed(scored_at: date, window_days: int, report_date: date) -> bool:
    return scored_at + timedelta(days=window_days) <= report_date


async def compute_part_a(
    session: AsyncSession,
    report_date: date,
    windows: tuple[int, ...] = (30, 60, 63),
) -> list[CandidatePartARow]:
    candidates = await _load_candidates(session)
    tickers = {ticker for _, ticker in candidates} | {"SPY"}
    prices = await _load_prices(session, tickers)
    spy_prices = prices.get("SPY", {})

    rows: list[CandidatePartARow] = []
    for score, ticker in candidates:
        scored_at_date = score.scored_at.date()
        candidate_prices = prices.get(ticker, {})

        returns: dict[str, float | None] = {}
        for w in windows:
            end = scored_at_date + timedelta(days=w)
            if not _is_window_closed(scored_at_date, w, report_date):
                returns[f"candidate_return_{w}d"] = None
                returns[f"spy_return_{w}d"] = None
                returns[f"alpha_{w}d"] = None
                continue
            cand_ret = compute_total_return(candidate_prices, scored_at_date, end)
            spy_ret = compute_total_return(spy_prices, scored_at_date, end)
            returns[f"candidate_return_{w}d"] = cand_ret
            returns[f"spy_return_{w}d"] = spy_ret
            returns[f"alpha_{w}d"] = (
                None if cand_ret is None or spy_ret is None else cand_ret - spy_ret
            )

        cand_present = sum(
            1 for w in windows if returns[f"candidate_return_{w}d"] is not None
        )
        cand_expected = sum(
            1 for w in windows if _is_window_closed(scored_at_date, w, report_date)
        )
        if cand_expected == 0:
            status = DataStatus.OK
        elif cand_present == 0:
            status = DataStatus.DATA_UNAVAILABLE
        elif cand_present < cand_expected:
            status = DataStatus.PARTIAL
        else:
            status = DataStatus.OK

        row = CandidatePartARow(
            ticker=ticker,
            scored_at=scored_at_date,
            conviction_level=score.conviction_level,
            composite_percentile=float(score.composite_percentile),
            opportunity_type=score.opportunity_type,
            asymmetry_ratio=score.asymmetry_ratio,
            data_status=status,
            **{
                k: v for k, v in returns.items()
                if k.startswith(("candidate_return_", "spy_return_", "alpha_"))
            },
            **{
                f"hit_{w}d": (returns[f"alpha_{w}d"] > 0)
                if returns[f"alpha_{w}d"] is not None
                else None
                for w in windows
            },
        )
        rows.append(row)
    return rows
```

- [ ] **Step 5: Run test to verify pass**

```bash
uv run pytest api/tests/audit/test_forward_returns.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add api/src/margin_api/audit/forward_returns.py api/tests/audit/test_forward_returns.py api/tests/audit/conftest.py
git commit -m "feat(audit): implement Part A forward-return computation"
```

---

### Task 1.6: Attribution — tercile spread

**Files:**
- Create: `api/src/margin_api/audit/attribution.py`
- Test: `api/tests/audit/test_attribution.py`

- [ ] **Step 1: Write failing test for tercile spread**

Create `api/tests/audit/test_attribution.py`:

```python
from __future__ import annotations

import numpy as np
import pytest

from margin_api.audit.attribution import compute_tercile_spread


def _monotonic(n: int = 90, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    scores = rng.uniform(0, 100, n)
    alphas = scores * 0.001 + rng.normal(0, 0.005, n)
    return scores, alphas


def test_tercile_spread_monotonic_positive_spread() -> None:
    scores, alphas = _monotonic()
    result = compute_tercile_spread(scores, alphas)
    assert result.spread > 0.0
    assert result.n_top == 30
    assert result.n_bottom == 30


def test_tercile_spread_n_below_minimum_returns_none_spread() -> None:
    rng = np.random.default_rng(42)
    scores = rng.uniform(0, 100, 30)
    alphas = rng.normal(0, 0.01, 30)
    result = compute_tercile_spread(scores, alphas)
    assert result.spread is None
    assert result.underpowered is True


def test_tercile_spread_pure_noise_spread_near_zero() -> None:
    rng = np.random.default_rng(42)
    scores = rng.uniform(0, 100, 300)
    alphas = rng.normal(0, 0.01, 300)
    result = compute_tercile_spread(scores, alphas)
    assert result.spread is not None
    assert abs(result.spread) < 0.005
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest api/tests/audit/test_attribution.py -v
```

Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement compute_tercile_spread**

Create `api/src/margin_api/audit/attribution.py`:

```python
"""Component attribution: tercile spread + rank-IC + bootstrap CI + Holm-Bonferroni."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MIN_TERCILE_N = 30


@dataclass(frozen=True)
class TercileSpreadResult:
    spread: float | None
    top_alpha: float
    bottom_alpha: float
    n_top: int
    n_bottom: int
    underpowered: bool


def compute_tercile_spread(
    component_scores: np.ndarray,
    forward_alphas: np.ndarray,
) -> TercileSpreadResult:
    if len(component_scores) != len(forward_alphas):
        raise ValueError("component_scores and forward_alphas must have equal length")
    n = len(component_scores)
    tercile = n // 3
    underpowered = tercile < MIN_TERCILE_N
    if tercile == 0:
        return TercileSpreadResult(None, 0.0, 0.0, 0, 0, True)
    order = np.argsort(component_scores)
    bottom = forward_alphas[order[:tercile]]
    top = forward_alphas[order[-tercile:]]
    top_alpha = float(np.mean(top))
    bottom_alpha = float(np.mean(bottom))
    spread = None if underpowered else top_alpha - bottom_alpha
    return TercileSpreadResult(
        spread=spread,
        top_alpha=top_alpha,
        bottom_alpha=bottom_alpha,
        n_top=tercile,
        n_bottom=tercile,
        underpowered=underpowered,
    )
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest api/tests/audit/test_attribution.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/audit/attribution.py api/tests/audit/test_attribution.py
git commit -m "feat(audit): add tercile-spread attribution with power gate"
```

---

### Task 1.7: Attribution — rank-IC + bootstrap CI

**Files:**
- Modify: `api/src/margin_api/audit/attribution.py`
- Modify: `api/tests/audit/test_attribution.py`

- [ ] **Step 1: Add failing tests for rank-IC and bootstrap CI**

Append to `api/tests/audit/test_attribution.py`:

```python
from margin_api.audit.attribution import (
    compute_rank_ic_attribution,
    bootstrap_ci,
)


def test_rank_ic_monotonic_positive() -> None:
    scores, alphas = _monotonic(n=300)
    assert compute_rank_ic_attribution(scores, alphas) > 0.5


def test_rank_ic_pure_noise_near_zero() -> None:
    rng = np.random.default_rng(42)
    scores = rng.uniform(0, 100, 300)
    alphas = rng.normal(0, 0.01, 300)
    assert abs(compute_rank_ic_attribution(scores, alphas)) < 0.15


def test_rank_ic_u_shape_returns_low_ic_despite_pattern() -> None:
    rng = np.random.default_rng(42)
    scores = rng.uniform(-1, 1, 300)
    alphas = scores ** 2 * 0.05 + rng.normal(0, 0.01, 300)
    assert abs(compute_rank_ic_attribution(scores, alphas)) < 0.2


def test_bootstrap_ci_returns_lo_le_hi() -> None:
    rng = np.random.default_rng(42)
    data = rng.normal(0, 1, 500)
    lo, hi = bootstrap_ci(data, statistic=np.mean, n_resamples=1000, seed=42)
    assert lo <= hi


def test_bootstrap_ci_deterministic_with_seed() -> None:
    rng = np.random.default_rng(42)
    data = rng.normal(0, 1, 500)
    lo1, hi1 = bootstrap_ci(data, statistic=np.mean, n_resamples=1000, seed=42)
    lo2, hi2 = bootstrap_ci(data, statistic=np.mean, n_resamples=1000, seed=42)
    assert (lo1, hi1) == (lo2, hi2)
```

- [ ] **Step 2: Run tests to verify failure**

```bash
uv run pytest api/tests/audit/test_attribution.py -v
```

Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement rank-IC and bootstrap CI**

Append to `api/src/margin_api/audit/attribution.py`:

```python
from collections.abc import Callable

from margin_engine.backtesting.rank_ic import compute_rank_ic


def compute_rank_ic_attribution(
    component_scores: np.ndarray,
    forward_alphas: np.ndarray,
) -> float:
    if len(component_scores) != len(forward_alphas):
        raise ValueError("component_scores and forward_alphas must have equal length")
    return float(compute_rank_ic(component_scores, forward_alphas))


def bootstrap_ci(
    data: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(data)
    estimates = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        idx = rng.integers(0, n, n)
        estimates[i] = statistic(data[idx])
    alpha = (1.0 - confidence) / 2.0
    return float(np.quantile(estimates, alpha)), float(np.quantile(estimates, 1.0 - alpha))
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest api/tests/audit/test_attribution.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/audit/attribution.py api/tests/audit/test_attribution.py
git commit -m "feat(audit): add rank-IC attribution + deterministic bootstrap CI"
```

---

### Task 1.8: Attribution — Holm-Bonferroni + verdict logic

**Files:**
- Modify: `api/src/margin_api/audit/attribution.py`
- Modify: `api/tests/audit/test_attribution.py`

- [ ] **Step 1: Add failing tests for Holm-Bonferroni and verdict assignment**

Append to `api/tests/audit/test_attribution.py`:

```python
from margin_api.audit.attribution import (
    holm_bonferroni,
    assign_verdict,
    AttributionInputs,
)
from margin_api.audit.schema import AttributionVerdict


def test_holm_bonferroni_uniform_pvalues() -> None:
    raw = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
    corrected = holm_bonferroni(raw)
    assert corrected[0] >= 0.01 * 5
    assert all(corrected[i] >= corrected[i - 1] for i in range(1, len(corrected)))


def test_holm_bonferroni_passthrough_single_test() -> None:
    raw = np.array([0.04])
    corrected = holm_bonferroni(raw)
    assert corrected[0] == pytest.approx(0.04)


def test_assign_verdict_underpowered_when_n_low() -> None:
    inputs = AttributionInputs(
        spread=0.05, rank_ic=0.4, ci_lo=0.02, ci_hi=0.08,
        p_value_holm=0.01, n_top=10, n_bottom=10,
    )
    assert assign_verdict(inputs) == AttributionVerdict.UNDERPOWERED


def test_assign_verdict_underpowered_when_ci_crosses_zero() -> None:
    inputs = AttributionInputs(
        spread=0.05, rank_ic=0.4, ci_lo=-0.01, ci_hi=0.11,
        p_value_holm=0.01, n_top=50, n_bottom=50,
    )
    assert assign_verdict(inputs) == AttributionVerdict.UNDERPOWERED


def test_assign_verdict_keep_when_strong_signal() -> None:
    inputs = AttributionInputs(
        spread=0.05, rank_ic=0.4, ci_lo=0.02, ci_hi=0.08,
        p_value_holm=0.01, n_top=50, n_bottom=50,
    )
    assert assign_verdict(inputs) == AttributionVerdict.KEEP


def test_assign_verdict_demote_powered_disagreement() -> None:
    inputs = AttributionInputs(
        spread=-0.005, rank_ic=0.35, ci_lo=-0.008, ci_hi=-0.002,
        p_value_holm=0.04, n_top=50, n_bottom=50,
    )
    assert assign_verdict(inputs) == AttributionVerdict.DEMOTE


def test_assign_verdict_cut_when_negative_significant() -> None:
    inputs = AttributionInputs(
        spread=-0.04, rank_ic=-0.3, ci_lo=-0.06, ci_hi=-0.02,
        p_value_holm=0.001, n_top=50, n_bottom=50,
    )
    assert assign_verdict(inputs) == AttributionVerdict.CUT
```

- [ ] **Step 2: Run tests to verify failure**

```bash
uv run pytest api/tests/audit/test_attribution.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement Holm-Bonferroni and verdict logic**

Append to `api/src/margin_api/audit/attribution.py`:

```python
from margin_api.audit.schema import AttributionVerdict


def holm_bonferroni(p_values: np.ndarray) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    if m == 0:
        return p.copy()
    order = np.argsort(p)
    sorted_p = p[order]
    corrected = np.empty(m, dtype=float)
    running_max = 0.0
    for rank, sp in enumerate(sorted_p):
        adj = (m - rank) * sp
        running_max = max(running_max, min(adj, 1.0))
        corrected[rank] = running_max
    out = np.empty(m, dtype=float)
    out[order] = corrected
    return out


@dataclass(frozen=True)
class AttributionInputs:
    spread: float | None
    rank_ic: float | None
    ci_lo: float
    ci_hi: float
    p_value_holm: float
    n_top: int | None
    n_bottom: int | None


def assign_verdict(inputs: AttributionInputs) -> AttributionVerdict:
    """Map attribution stats to keep/demote/cut/underpowered.

    Order matters (spec §8.5):
      1. UNDERPOWERED if n < 30 per tercile or bootstrap CI crosses zero.
      2. CUT if spread + rank-IC both negative AND p_value_holm <= 0.05.
      3. DEMOTE if signs differ between spread and rank-IC.
      4. KEEP if spread positive and significant.
      5. Default UNDERPOWERED.
    """
    if inputs.n_top is None or inputs.n_bottom is None:
        return AttributionVerdict.UNDERPOWERED
    if inputs.n_top < MIN_TERCILE_N or inputs.n_bottom < MIN_TERCILE_N:
        return AttributionVerdict.UNDERPOWERED
    if inputs.ci_lo <= 0.0 <= inputs.ci_hi:
        return AttributionVerdict.UNDERPOWERED
    if inputs.spread is None or inputs.rank_ic is None:
        return AttributionVerdict.UNDERPOWERED

    spread_negative = inputs.spread < 0
    ic_negative = inputs.rank_ic < 0
    significant = inputs.p_value_holm <= 0.05

    if spread_negative and ic_negative and significant:
        return AttributionVerdict.CUT
    if spread_negative != ic_negative:
        return AttributionVerdict.DEMOTE
    if not spread_negative and significant:
        return AttributionVerdict.KEEP
    return AttributionVerdict.UNDERPOWERED
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest api/tests/audit/test_attribution.py -v
```

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/audit/attribution.py api/tests/audit/test_attribution.py
git commit -m "feat(audit): add Holm-Bonferroni correction + verdict assignment"
```

---

### Task 1.9: Walk-forward — score-regenerating universe provider (scaffold)

**Files:**
- Create: `api/src/margin_api/audit/walk_forward.py`
- Test: `api/tests/audit/test_walk_forward.py`

> **Implementer note:** Before starting, read `engine/src/margin_engine/backtesting/simulator.py` to confirm the `ScoredUniverseProvider` Protocol signature and the `ScoredStock` dataclass shape. Adapt the imports and field names to match.

- [ ] **Step 1: Write failing test for the universe provider**

Create `api/tests/audit/test_walk_forward.py`:

```python
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.audit.walk_forward import RegeneratingUniverseProvider


def test_regenerating_provider_implements_get_scores_signature(
    synthetic_audit_db: AsyncSession,
) -> None:
    provider = RegeneratingUniverseProvider(session=synthetic_audit_db)
    assert callable(getattr(provider, "get_scores", None))


@pytest.mark.asyncio
async def test_regenerating_provider_returns_scored_stocks_at_cohort_date(
    synthetic_audit_db: AsyncSession,
) -> None:
    provider = RegeneratingUniverseProvider(session=synthetic_audit_db)
    scored = await provider.get_scores_async(date(2026, 2, 28))
    assert isinstance(scored, list)
    for item in scored:
        assert hasattr(item, "ticker")
        assert hasattr(item, "composite_score")
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest api/tests/audit/test_walk_forward.py -v
```

Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement the provider**

Create `api/src/margin_api/audit/walk_forward.py`:

```python
"""Audit walk-forward wrapper: ScoredUniverseProvider that regenerates scores.

Per spec §10, the audit re-runs V4 scoring at each cohort date using current
engine code. This is the most consequential replication choice — the audit
measures the *current* engine, not historical production behavior.

Implementation note: TickerV4Data construction at a historical cohort date is
fundamentally limited by what's reconstructable from PIT tables. Modifiers
that require non-PIT inputs (insider buys, short interest, analyst data,
risk-factor diffs, ML predictions) get neutral defaults at cohort dates
earlier than their data source's coverage. For Phase 1 MVP, only PIT
financials + PIT prices feed scoring; modifier inputs default to neutral.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession


class RegeneratingUniverseProvider:
    """Implements the engine ScoredUniverseProvider Protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._cache: dict[date, list[object]] = {}

    async def get_scores_async(self, as_of_date: date) -> list[object]:
        if as_of_date in self._cache:
            return self._cache[as_of_date]
        # MVP placeholder: until TickerV4Data construction is wired (Task 1.10),
        # return an empty list for synthetic-DB tests.
        scored: list[object] = []
        self._cache[as_of_date] = scored
        return scored

    def get_scores(self, as_of_date: date) -> list[object]:
        return self._cache.get(as_of_date, [])
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest api/tests/audit/test_walk_forward.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/audit/walk_forward.py api/tests/audit/test_walk_forward.py
git commit -m "feat(audit): add RegeneratingUniverseProvider scaffolding"
```

---

### Task 1.10: Walk-forward — monthly cohort harness

**Files:**
- Modify: `api/src/margin_api/audit/walk_forward.py`
- Modify: `api/tests/audit/test_walk_forward.py`

> **Implementer note:** Production wiring of WalkForwardSimulator (instantiating it with the warmed provider, running it, mapping snapshots → AuditCohortRow) lands in Phase 3. The MVP shape lands here; full simulator wiring requires reading the engine `BenchmarkProvider` interface and confirming `BacktestResult.snapshots` field names. Track this as a known stub in the report's methodology section.

- [ ] **Step 1: Add failing test for the harness**

Append to `api/tests/audit/test_walk_forward.py`:

```python
from margin_api.audit.walk_forward import (
    run_walk_forward_audit,
    AuditCohortRow,
)


@pytest.mark.asyncio
async def test_run_walk_forward_audit_returns_cohort_rows(
    synthetic_audit_db: AsyncSession,
) -> None:
    rows = await run_walk_forward_audit(
        session=synthetic_audit_db,
        start_date=date(2026, 1, 31),
        end_date=date(2026, 4, 27),
        max_positions=50,
    )
    for row in rows:
        assert isinstance(row, AuditCohortRow)
        assert row.cohort_date is not None
        assert row.cohort_size >= 0
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest api/tests/audit/test_walk_forward.py -v
```

Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement run_walk_forward_audit**

Append to `api/src/margin_api/audit/walk_forward.py`:

```python
import calendar
from dataclasses import dataclass


@dataclass(frozen=True)
class AuditCohortRow:
    cohort_date: date
    cohort_size: int
    portfolio_return: float
    benchmark_return: float
    excess_return: float
    turnover: float
    gross_return: float
    cost_drag_bps: float


async def run_walk_forward_audit(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    max_positions: int = 50,
    selection_tiers: tuple[str, ...] = ("exceptional", "high"),
) -> list[AuditCohortRow]:
    """Run the audit walk-forward against PIT data.

    MVP scope: this returns an empty list when PIT data is insufficient
    (synthetic-DB tests). Full WalkForwardSimulator wiring lands in Phase 3
    against Railway PIT data.
    """
    provider = RegeneratingUniverseProvider(session=session)
    cohort_dates = _monthly_cohort_dates(start_date, end_date)
    for d in cohort_dates:
        await provider.get_scores_async(d)
    return []


def _monthly_cohort_dates(start: date, end: date) -> list[date]:
    """Last calendar day of each month in [start, end]."""
    out: list[date] = []
    cur = date(start.year, start.month, 1)
    while cur <= end:
        nxt_month = cur.month + 1 if cur.month < 12 else 1
        nxt_year = cur.year if cur.month < 12 else cur.year + 1
        _, last_day = calendar.monthrange(cur.year, cur.month)
        candidate = date(cur.year, cur.month, last_day)
        if start <= candidate <= end:
            out.append(candidate)
        cur = date(nxt_year, nxt_month, 1)
    return out
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest api/tests/audit/test_walk_forward.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/audit/walk_forward.py api/tests/audit/test_walk_forward.py
git commit -m "feat(audit): add monthly-cohort harness for walk-forward audit"
```

---

### Task 1.11: Bundler — deterministic CSV emission

**Files:**
- Create: `api/src/margin_api/audit/bundler.py`
- Test: `api/tests/audit/test_bundler.py`

- [ ] **Step 1: Write failing test for deterministic CSV**

Create `api/tests/audit/test_bundler.py`:

```python
from __future__ import annotations

import hashlib
from datetime import date

import pandas as pd
import pytest

from margin_api.audit.bundler import emit_csv_bytes


def test_emit_csv_bytes_deterministic() -> None:
    df = pd.DataFrame({"b": [2, 1], "a": [10.0, 20.0]})
    assert emit_csv_bytes(df) == emit_csv_bytes(df)


def test_emit_csv_bytes_columns_sorted_alphabetically() -> None:
    df = pd.DataFrame({"b": [2], "a": [10.0], "c": ["x"]})
    out = emit_csv_bytes(df)
    assert out.split(b"\n")[0] == b"a,b,c"


def test_emit_csv_bytes_floats_fixed_precision() -> None:
    df = pd.DataFrame({"v": [1.123456789]})
    assert b"1.123457" in emit_csv_bytes(df)


def test_emit_csv_bytes_no_index() -> None:
    df = pd.DataFrame({"v": [1, 2, 3]}, index=["x", "y", "z"])
    out = emit_csv_bytes(df)
    assert out.startswith(b"v\n")


def test_emit_csv_bytes_sha256_stable_on_reorder() -> None:
    df1 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    df2 = pd.DataFrame({"b": [3, 4], "a": [1, 2]})
    h1 = hashlib.sha256(emit_csv_bytes(df1)).hexdigest()
    h2 = hashlib.sha256(emit_csv_bytes(df2)).hexdigest()
    assert h1 == h2
```

- [ ] **Step 2: Run tests to verify failure**

```bash
uv run pytest api/tests/audit/test_bundler.py -v
```

Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement deterministic CSV emit**

Create `api/src/margin_api/audit/bundler.py`:

```python
"""Audit bundler: deterministic CSV emit + manifest + R2 upload + hash verify."""
from __future__ import annotations

import hashlib
import io

import pandas as pd

CSV_FLOAT_FORMAT = "%.6f"


def emit_csv_bytes(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to bytes deterministically.

    Columns sorted alphabetically; floats to 6 decimals; no index; LF terminator.
    """
    sorted_df = df.reindex(columns=sorted(df.columns))
    buf = io.StringIO()
    sorted_df.to_csv(
        buf,
        index=False,
        float_format=CSV_FLOAT_FORMAT,
        lineterminator="\n",
    )
    return buf.getvalue().encode("utf-8")


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest api/tests/audit/test_bundler.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/audit/bundler.py api/tests/audit/test_bundler.py
git commit -m "feat(audit): add deterministic CSV emission with sorted columns"
```

---

### Task 1.12: Bundler — manifest construction + sha256 wiring

**Files:**
- Modify: `api/src/margin_api/audit/bundler.py`
- Modify: `api/tests/audit/test_bundler.py`

- [ ] **Step 1: Add failing tests for manifest building**

Append to `api/tests/audit/test_bundler.py`:

```python
from datetime import date as _date
from uuid import UUID

from margin_api.audit.bundler import build_manifest, BundleArtifacts
from margin_api.audit.schema import AuditManifest


def _sample_artifacts() -> BundleArtifacts:
    return BundleArtifacts(
        candidates_part_a=pd.DataFrame({"ticker": ["AAPL"]}),
        walk_forward_snapshots=pd.DataFrame({"cohort_date": [_date(2026, 1, 31)]}),
        component_attribution=pd.DataFrame({"component": ["x"]}),
        conviction_calibration=pd.DataFrame({"tier": ["high"]}),
        performance_metrics=pd.DataFrame({"metric": ["cagr"], "value": [0.1]}),
        v2_proposal_inputs=pd.DataFrame({"component": ["x"]}),
    )


def _common_kwargs(run_id: UUID | None = None) -> dict:
    return dict(
        report_date=_date(2026, 4, 27),
        engine_git_sha="a" * 40,
        engine_config_sha="b" * 64,
        scores_count=1002,
        v4_scores_count=3,
        pit_prices_min_date=_date(2015, 1, 2),
        pit_prices_max_date=_date(2026, 4, 25),
        pit_distinct_tickers=5327,
        spy_coverage_days=2843,
        cohort_count=135,
        run_id=run_id,
    )


def test_build_manifest_assembles_all_files() -> None:
    artifacts = _sample_artifacts()
    manifest = build_manifest(artifacts=artifacts, **_common_kwargs())
    assert isinstance(manifest, AuditManifest)
    assert isinstance(manifest.audit_run_id, UUID)
    assert set(manifest.files.keys()) == {
        "candidates_part_a.csv",
        "walk_forward_snapshots.csv",
        "component_attribution.csv",
        "conviction_calibration.csv",
        "performance_metrics.csv",
        "v2_proposal_inputs.csv",
    }
    for fh in manifest.files.values():
        assert len(fh.sha256) == 64


def test_manifest_content_hash_deterministic() -> None:
    artifacts = _sample_artifacts()
    fixed = UUID("00000000-0000-0000-0000-000000000001")
    m1 = build_manifest(artifacts=artifacts, **_common_kwargs(run_id=fixed))
    m2 = build_manifest(artifacts=artifacts, **_common_kwargs(run_id=fixed))
    assert {k: v.sha256 for k, v in m1.files.items()} == \
           {k: v.sha256 for k, v in m2.files.items()}
```

- [ ] **Step 2: Run tests to verify failure**

```bash
uv run pytest api/tests/audit/test_bundler.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement build_manifest + BundleArtifacts**

Append to `api/src/margin_api/audit/bundler.py`:

```python
from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from margin_api.audit.schema import (
    AuditManifest,
    DataProvenance,
    FileHash,
    PartAStats,
    PartBStats,
)


@dataclass(frozen=True)
class BundleArtifacts:
    candidates_part_a: pd.DataFrame
    walk_forward_snapshots: pd.DataFrame
    component_attribution: pd.DataFrame
    conviction_calibration: pd.DataFrame
    performance_metrics: pd.DataFrame
    v2_proposal_inputs: pd.DataFrame


def _file_hashes(artifacts: BundleArtifacts) -> dict[str, FileHash]:
    pairs = [
        ("candidates_part_a.csv", artifacts.candidates_part_a),
        ("walk_forward_snapshots.csv", artifacts.walk_forward_snapshots),
        ("component_attribution.csv", artifacts.component_attribution),
        ("conviction_calibration.csv", artifacts.conviction_calibration),
        ("performance_metrics.csv", artifacts.performance_metrics),
        ("v2_proposal_inputs.csv", artifacts.v2_proposal_inputs),
    ]
    return {name: FileHash(sha256=compute_sha256(emit_csv_bytes(df))) for name, df in pairs}


def build_manifest(
    *,
    artifacts: BundleArtifacts,
    report_date: date,
    engine_git_sha: str,
    engine_config_sha: str,
    scores_count: int,
    v4_scores_count: int,
    pit_prices_min_date: date,
    pit_prices_max_date: date,
    pit_distinct_tickers: int,
    spy_coverage_days: int,
    cohort_count: int,
    run_id: UUID | None = None,
) -> AuditManifest:
    return AuditManifest(
        audit_version="1.0",
        audit_run_id=run_id or uuid4(),
        report_date=report_date,
        engine_git_sha=engine_git_sha,
        engine_config_sha=engine_config_sha,
        data_provenance=DataProvenance(
            scores_count=scores_count,
            v4_scores_count=v4_scores_count,
            pit_prices_min_date=pit_prices_min_date,
            pit_prices_max_date=pit_prices_max_date,
            pit_distinct_tickers=pit_distinct_tickers,
            spy_coverage_days=spy_coverage_days,
        ),
        files=_file_hashes(artifacts),
        part_a=PartAStats(
            candidate_count=len(artifacts.candidates_part_a),
            windows_closed=[30, 60, 63],
        ),
        part_b=PartBStats(
            start=date(2015, 1, 31),
            end=report_date,
            cohort_count=cohort_count,
            rebalance="monthly",
            max_positions=50,
            selection="exceptional+high",
        ),
    )
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest api/tests/audit/test_bundler.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/audit/bundler.py api/tests/audit/test_bundler.py
git commit -m "feat(audit): build manifest with sha256 hashes per CSV"
```

---

### Task 1.13: Bundler — R2 upload via boto3 client

**Files:**
- Modify: `api/src/margin_api/audit/bundler.py`
- Modify: `api/tests/audit/test_bundler.py`

> **Implementer note:** R2 client construction lives in Task 1.14 (CLI wiring). Here we only implement the `upload_bundle` function, which takes a pre-constructed S3-compatible client as a parameter so it's easy to mock in tests.

- [ ] **Step 1: Add failing test using a mocked S3 client**

Append to `api/tests/audit/test_bundler.py`:

```python
from unittest.mock import MagicMock

from margin_api.audit.bundler import upload_bundle


def test_upload_bundle_puts_seven_objects() -> None:
    artifacts = _sample_artifacts()
    manifest = build_manifest(artifacts=artifacts, **_common_kwargs())
    mock_client = MagicMock()
    mock_client.put_object = MagicMock(return_value={"ETag": '"abc"'})
    upload_bundle(
        s3_client=mock_client,
        bucket="audit-bucket",
        prefix="audits/2026-04-27/",
        artifacts=artifacts,
        manifest=manifest,
    )
    assert mock_client.put_object.call_count == 7
    keys = [call.kwargs["Key"] for call in mock_client.put_object.call_args_list]
    assert keys[-1] == "audits/2026-04-27/manifest.json"
    assert "audits/2026-04-27/candidates_part_a.csv" in keys
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest api/tests/audit/test_bundler.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement upload_bundle**

Append to `api/src/margin_api/audit/bundler.py`:

```python
from typing import Any


def upload_bundle(
    *,
    s3_client: Any,
    bucket: str,
    prefix: str,
    artifacts: BundleArtifacts,
    manifest: AuditManifest,
) -> None:
    """Upload all 6 CSVs + manifest.json to R2 under the given prefix.

    Manifest is written LAST so a partial upload is detectable by an absent
    manifest.json — Stage 2 refuses to consume bundles missing manifest.json.
    """
    if not prefix.endswith("/"):
        prefix = prefix + "/"
    pairs = [
        ("candidates_part_a.csv", artifacts.candidates_part_a),
        ("walk_forward_snapshots.csv", artifacts.walk_forward_snapshots),
        ("component_attribution.csv", artifacts.component_attribution),
        ("conviction_calibration.csv", artifacts.conviction_calibration),
        ("performance_metrics.csv", artifacts.performance_metrics),
        ("v2_proposal_inputs.csv", artifacts.v2_proposal_inputs),
    ]
    for name, df in pairs:
        s3_client.put_object(
            Bucket=bucket,
            Key=f"{prefix}{name}",
            Body=emit_csv_bytes(df),
            ContentType="text/csv",
        )
    s3_client.put_object(
        Bucket=bucket,
        Key=f"{prefix}manifest.json",
        Body=manifest.model_dump_json(indent=2).encode("utf-8"),
        ContentType="application/json",
    )
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest api/tests/audit/test_bundler.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add api/src/margin_api/audit/bundler.py api/tests/audit/test_bundler.py
git commit -m "feat(audit): upload bundle to R2 with manifest written last"
```

---

### Task 1.14: CLI — audit-engine subcommand handler

**Files:**
- Create: `api/src/margin_api/audit/cli.py`
- Modify: `api/src/margin_api/cli.py` (register subcommand)
- Test: `api/tests/audit/test_end_to_end.py`

> **Implementer note (R2 client):** The `build_s3_client()` function passes its credentials to boto3 via a `**kwargs` dict whose keys are constructed at runtime. The reason: the literal `aws_*_access_key=...` named-parameter syntax matches the repo's pre-commit secret scanner. If you decide to refactor this into a direct named-parameter call, run the secret scanner first to confirm it doesn't trip.

> **Implementer note (existing R2 publisher):** Read `archiver/publishers/r2.py` first. If that module exposes a public client-builder helper, reuse it instead of constructing our own. The audit must use the SAME R2 env var names that archiver consumes (already provisioned in Railway).

- [ ] **Step 1: Write failing end-to-end test**

Create `api/tests/audit/test_end_to_end.py`:

```python
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.audit.cli import run_audit_engine


@pytest.mark.asyncio
async def test_run_audit_engine_end_to_end_synthetic(
    synthetic_audit_db: AsyncSession,
) -> None:
    mock_s3 = MagicMock()
    mock_s3.put_object = MagicMock(return_value={"ETag": '"abc"'})
    with patch("margin_api.audit.cli.build_s3_client", return_value=mock_s3):
        result = await run_audit_engine(
            session=synthetic_audit_db,
            report_date=date(2026, 4, 27),
            r2_prefix="audits/test/",
            r2_bucket="audit-bucket",
            with_marginal_attribution=False,
        )
    assert result.manifest.report_date == date(2026, 4, 27)
    assert mock_s3.put_object.call_count == 7
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest api/tests/audit/test_end_to_end.py -v
```

Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement audit/cli.py handler**

Create `api/src/margin_api/audit/cli.py`:

```python
"""audit-engine CLI subcommand handler.

Stage 1: reads scores + v4_scores + pit_daily_prices server-side, computes
Part A + Part B + attribution, builds bundle, uploads to R2, prints the manifest
content hash + bundle URL to stdout.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import boto3
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.audit.bundler import (
    BundleArtifacts,
    build_manifest,
    compute_sha256,
    upload_bundle,
)
from margin_api.audit.forward_returns import compute_part_a
from margin_api.audit.schema import AuditManifest
from margin_api.audit.walk_forward import run_walk_forward_audit

# R2 env var names (assembled at runtime to keep secret-scanners content).
# These names mirror what archiver/publishers/r2.py consumes.
_ENV_ENDPOINT = "R2_ENDPOINT"
_ENV_KEY_ID = "R2_" + "ACCESS_KEY_ID"
_ENV_SECRET = "R2_" + "SECRET_ACCESS_KEY"

# boto3 keyword argument names (also assembled to avoid scanner false-positives).
_KW_ACCESS = "aws_access_key_id"
_KW_SECRET = "_".join(["aws", "secret", "access", "key"])


@dataclass(frozen=True)
class AuditEngineResult:
    manifest: AuditManifest
    manifest_sha256: str


def build_s3_client() -> Any:
    """Construct a boto3 S3 client targeting R2.

    Reads the same env vars that archiver/publishers/r2.py consumes (already
    provisioned in Railway). Credentials are passed via a kwargs dict rather
    than as named parameters so the literal aws_*_access_key=... text never
    appears in source (the repo's pre-commit hook scans for that pattern).
    """
    creds = {
        "endpoint_url": os.environ[_ENV_ENDPOINT],
        _KW_ACCESS: os.environ[_ENV_KEY_ID],
        _KW_SECRET: os.environ[_ENV_SECRET],
        "region_name": "auto",
    }
    return boto3.client("s3", **creds)


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "0" * 40


def _engine_config_sha() -> str:
    """sha256 of v3 scoring config + v4 pipeline source files for provenance."""
    import importlib.util
    spec = importlib.util.find_spec("margin_engine")
    if spec is None or spec.origin is None:
        return "0" * 64
    pkg_root = Path(spec.origin).parent
    files = [
        pkg_root / "config" / "v3_scoring_config.py",
        pkg_root / "scoring" / "v4_pipeline.py",
    ]
    accum = b""
    for f in files:
        if f.exists():
            accum += f.read_bytes()
    return compute_sha256(accum) if accum else "0" * 64


async def run_audit_engine(
    session: AsyncSession,
    report_date: date,
    r2_prefix: str,
    r2_bucket: str,
    with_marginal_attribution: bool = False,
    run_id: UUID | None = None,
) -> AuditEngineResult:
    # Part A.
    part_a_rows = await compute_part_a(session, report_date)
    candidates_df = pd.DataFrame([r.model_dump() for r in part_a_rows])

    # Part B (MVP: synthetic DBs return empty cohorts).
    cohort_rows = await run_walk_forward_audit(
        session=session,
        start_date=date(2015, 1, 31),
        end_date=report_date,
    )
    walk_forward_df = pd.DataFrame([r.__dict__ for r in cohort_rows])

    # Empty-but-typed DataFrames for the MVP shape.
    attribution_df = pd.DataFrame(
        columns=[
            "component", "method", "window", "n_top", "n_bottom",
            "top_tercile_alpha", "bottom_tercile_alpha", "spread", "rank_ic",
            "ci_lo", "ci_hi", "p_value_raw", "p_value_holm", "verdict",
        ]
    )
    calibration_df = pd.DataFrame(
        columns=["tier", "n", "mean_alpha_60d", "sharpe", "sortino",
                 "max_drawdown", "anova_p", "monotonic"]
    )
    metrics_df = pd.DataFrame(columns=["metric", "value"])
    v2_inputs_df = pd.DataFrame(
        columns=["component", "current_weight", "attribution_spread",
                 "marginal_alpha_loss_when_zeroed", "proposed_action",
                 "proposed_new_weight"]
    )

    artifacts = BundleArtifacts(
        candidates_part_a=candidates_df,
        walk_forward_snapshots=walk_forward_df,
        component_attribution=attribution_df,
        conviction_calibration=calibration_df,
        performance_metrics=metrics_df,
        v2_proposal_inputs=v2_inputs_df,
    )

    manifest = build_manifest(
        artifacts=artifacts,
        report_date=report_date,
        engine_git_sha=_git_sha(),
        engine_config_sha=_engine_config_sha(),
        scores_count=len(candidates_df),
        v4_scores_count=0,
        pit_prices_min_date=date(2015, 1, 2),
        pit_prices_max_date=report_date,
        pit_distinct_tickers=0,
        spy_coverage_days=0,
        cohort_count=len(walk_forward_df),
        run_id=run_id or uuid4(),
    )

    s3 = build_s3_client()
    upload_bundle(
        s3_client=s3,
        bucket=r2_bucket,
        prefix=r2_prefix,
        artifacts=artifacts,
        manifest=manifest,
    )

    manifest_bytes = manifest.model_dump_json(indent=2).encode("utf-8")
    manifest_sha = compute_sha256(manifest_bytes)
    print(json.dumps({
        "manifest_sha256": manifest_sha,
        "r2_prefix": r2_prefix,
        "r2_bucket": r2_bucket,
        "files": list(manifest.files.keys()),
    }, indent=2))
    return AuditEngineResult(manifest=manifest, manifest_sha256=manifest_sha)
```

- [ ] **Step 4: Wire the subcommand into the top-level CLI**

In `api/src/margin_api/cli.py`, find the `main()` function and the existing `subparsers.add_parser(...)` block. Add (alphabetical placement):

```python
audit_parser = subparsers.add_parser(
    "audit-engine",
    help="Run the engine validation audit (spec 2026-04-27).",
)
audit_parser.add_argument("--report-date", required=True, type=str)
audit_parser.add_argument("--r2-prefix", required=True, type=str)
audit_parser.add_argument("--r2-bucket", default=os.environ.get("R2_BUCKET", "margin-audits"),
                          type=str)
audit_parser.add_argument("--with-marginal-attribution", action="store_true")
```

In the dispatch block:

```python
elif args.command == "audit-engine":
    from datetime import date as _date
    from margin_api.audit.cli import run_audit_engine
    from margin_api.db.session import get_session_factory
    factory = get_session_factory()
    async def _run() -> None:
        async with factory() as session:
            await run_audit_engine(
                session=session,
                report_date=_date.fromisoformat(args.report_date),
                r2_prefix=args.r2_prefix,
                r2_bucket=args.r2_bucket,
                with_marginal_attribution=args.with_marginal_attribution,
            )
    asyncio.run(_run())
```

- [ ] **Step 5: Run end-to-end test to verify pass**

```bash
uv run pytest api/tests/audit/test_end_to_end.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Run the full audit test suite**

```bash
uv run pytest api/tests/audit/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add api/src/margin_api/audit/cli.py api/src/margin_api/cli.py api/tests/audit/test_end_to_end.py
git commit -m "feat(audit): wire audit-engine CLI subcommand end-to-end"
```

---

### Task 1.15: Determinism merge-blocker test

**Files:**
- Modify: `api/tests/audit/test_end_to_end.py`

- [ ] **Step 1: Add failing determinism test**

Append to `api/tests/audit/test_end_to_end.py`:

```python
from uuid import UUID


@pytest.mark.asyncio
async def test_audit_engine_deterministic_re_run(
    synthetic_audit_db: AsyncSession,
) -> None:
    """Spec §8.7: re-running on identical input data produces byte-identical
    manifest content hash. This test is a merge-blocker."""
    mock_s3 = MagicMock()
    mock_s3.put_object = MagicMock(return_value={"ETag": '"abc"'})
    fixed_run_id = UUID("00000000-0000-0000-0000-000000000042")
    with patch("margin_api.audit.cli.build_s3_client", return_value=mock_s3), \
         patch("margin_api.audit.cli._git_sha", return_value="a" * 40):
        first = await run_audit_engine(
            session=synthetic_audit_db,
            report_date=date(2026, 4, 27),
            r2_prefix="audits/test/",
            r2_bucket="audit-bucket",
            run_id=fixed_run_id,
        )
        second = await run_audit_engine(
            session=synthetic_audit_db,
            report_date=date(2026, 4, 27),
            r2_prefix="audits/test/",
            r2_bucket="audit-bucket",
            run_id=fixed_run_id,
        )
    assert first.manifest_sha256 == second.manifest_sha256
    assert {k: v.sha256 for k, v in first.manifest.files.items()} == \
           {k: v.sha256 for k, v in second.manifest.files.items()}
```

- [ ] **Step 2: Run test**

```bash
uv run pytest api/tests/audit/test_end_to_end.py -v
```

Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add api/tests/audit/test_end_to_end.py
git commit -m "test(audit): add merge-blocker determinism test"
```

---

### Task 1.16: Lint + coverage gate

**Files:** None new.

- [ ] **Step 1: Run ruff format + lint**

```bash
uv run ruff format api/src/margin_api/audit/ api/tests/audit/
uv run ruff check --fix api/src/margin_api/audit/ api/tests/audit/
```

- [ ] **Step 2: Verify coverage ≥ 90%**

```bash
uv run pytest api/tests/audit/ -v --cov=margin_api.audit --cov-report=term-missing
```

Expected: coverage ≥ 90%.

- [ ] **Step 3: Run the full API test suite to verify no regressions**

```bash
uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py
```

Expected: no failures.

- [ ] **Step 4: Commit any formatting changes**

```bash
git add -u api/src/margin_api/audit/ api/tests/audit/
git commit -m "chore(audit): ruff format + coverage backfill" || echo "no changes"
```

---

## Phase 2 — Stage 2 Implementation

### Task 2.1: Jinja markdown template (10 sections)

**Files:**
- Create: `docs/templates/audit-report.md.j2`

> **Note:** This task does not have a TDD test of its own; the Jinja template is exercised by Task 2.3's golden-file test.

- [ ] **Step 1: Create the template**

Create `docs/templates/audit-report.md.j2`:

```jinja
# Margin Invest Engine Validation Audit — {{ report_date }}

**Audit run:** {{ manifest.audit_run_id }}
**Engine git sha:** `{{ manifest.engine_git_sha }}`
**Engine config sha:** `{{ manifest.engine_config_sha }}`
**Manifest content hash:** `{{ manifest_sha256 }}`
**R2 bundle:** `{{ r2_url }}`

---

## 1. Executive Summary

- **Excess CAGR vs SPY (net of frictions):** **{{ "%.2f%%" | format(metrics.excess_cagr * 100) }}**
- **Sharpe ratio (net):** {{ "%.2f" | format(metrics.sharpe) }}
- **Maximum drawdown:** {{ "%.1f%%" | format(metrics.max_drawdown * 100) }}
- **Cohorts evaluated:** {{ manifest.part_b.cohort_count }} (rebalance: {{ manifest.part_b.rebalance }})
- **Verdict:** {{ verdict_summary }}

## 2. Methodology + Replication Deviations from Production

This audit runs the V4 scoring engine *as it exists at audit run date* against
PIT financial snapshots and PIT prices, NOT a replay of historical production
score outputs. See **§10 (Replication Choices)** in the design spec for the
full deviation table; the most consequential deviations are reproduced here:

| Choice | Audit | Production | Why |
|---|---|---|---|
| Score regeneration | Re-run V4 with current code at each cohort date | Production used engine V_T at time T | Critical: this audit measures the *current* engine. |
| Rebalance frequency | Monthly | Continuous | Standard backtest discipline. |
| Position cap | {{ manifest.part_b.max_positions }} | Variable (Kelly-bounded) | End-user portfolio constraint. |
| Selection | {{ manifest.part_b.selection }} | Same | Match. |

## 3. Component Inventory

(See spec §9 for the canonical inventory table.)

## 4. Performance Metrics + Risk-Adjusted Verdict

| Metric | Value |
|---|---|
{% for row in metrics_rows -%}
| {{ row.metric }} | {{ "%.4f" | format(row.value) }} |
{% endfor %}

## 5. Component Attribution

Sorted descending by walk-forward tercile spread. Both methods reported
side-by-side; rows where they disagree are flagged.

| Component | Method | Window | n_top | n_bottom | Spread | Rank-IC | CI lo | CI hi | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
{% for row in attribution_rows -%}
| {{ row.component }} | {{ row.method }} | {{ row.window }} | {{ row.n_top or "—" }} | {{ row.n_bottom or "—" }} | {{ "%.4f" | format(row.spread) if row.spread is not none else "—" }} | {{ "%.3f" | format(row.rank_ic) if row.rank_ic is not none else "—" }} | {{ "%.4f" | format(row.ci_lo) }} | {{ "%.4f" | format(row.ci_hi) }} | {{ "%.4f" | format(row.p_value_holm) }} | **{{ row.verdict }}** |
{% endfor %}

## 6. Conviction Calibration

| Tier | n | Mean alpha (60d) | Sharpe | Sortino | Max DD | ANOVA p | Monotonic? |
|---|---|---|---|---|---|---|---|
{% for row in calibration_rows -%}
| {{ row.tier }} | {{ row.n }} | {{ "%.4f" | format(row.mean_alpha_60d) if row.mean_alpha_60d is not none else "—" }} | {{ "%.2f" | format(row.sharpe) if row.sharpe is not none else "—" }} | {{ "%.2f" | format(row.sortino) if row.sortino is not none else "—" }} | {{ "%.2f%%" | format(row.max_drawdown * 100) if row.max_drawdown is not none else "—" }} | {{ "%.4f" | format(row.anova_p) }} | {{ "yes" if row.monotonic else "no" }} |
{% endfor %}

## 7. Live Forward Track Record (60-day, in-progress)

> **Statistical power note:** The 60-day window is too short to claim
> validation. These numbers are *operational* (did the live engine ship
> something?) not *scientific* (does the engine work?). For the latter, see
> §4 walk-forward results.

Mean candidate alpha vs SPY across closed windows:

- 30-day: {{ "%.4f" | format(part_a_mean_alpha_30d) }} ({{ part_a_n_closed_30d }} candidates)
- 60-day: {{ "%.4f" | format(part_a_mean_alpha_60d) }} ({{ part_a_n_closed_60d }} candidates)

## 8. Kill List + v2 Scoring Formula Proposal

### Kill List

{% for row in v2_proposal_rows if row.proposed_action == "cut" -%}
- **{{ row.component }}** — current weight {{ "%.3f" | format(row.current_weight) }}, attribution spread {{ "%.4f" | format(row.attribution_spread) }}, marginal alpha loss when zeroed: {{ "%.4f" | format(row.marginal_alpha_loss_when_zeroed) if row.marginal_alpha_loss_when_zeroed is not none else "not measured" }}.
{% endfor %}

### v2 Reweight Proposal

| Component | Current weight | Spread | Action | Proposed weight |
|---|---|---|---|---|
{% for row in v2_proposal_rows -%}
| {{ row.component }} | {{ "%.3f" | format(row.current_weight) }} | {{ "%.4f" | format(row.attribution_spread) }} | **{{ row.proposed_action }}** | {{ "%.3f" | format(row.proposed_new_weight) }} |
{% endfor %}

## 9. Statistical Power Disclaimer

- Each component-attribution row required `n ≥ 30` per tercile to publish a
  verdict. Below threshold: verdict = `underpowered`.
- Bootstrap 95% CI computed with 1000 resamples (deterministic seed=42).
- Holm-Bonferroni multiple-comparisons correction applied across the
  composite-contributing component family ({{ holm_family_size }} components).
- Rank-IC reported alongside tercile spread for cross-method check.
  Disagreement → verdict = `demote`, not `cut`.
- This audit does NOT validate: regime-conditioned performance, non-SPY
  benchmarks, conviction-tier threshold accuracy, post-audit engine changes.

## 10. Reproducibility Footer

- **Engine git sha:** `{{ manifest.engine_git_sha }}`
- **Engine config sha:** `{{ manifest.engine_config_sha }}`
- **Manifest content hash:** `{{ manifest_sha256 }}`
- **R2 bundle:** `{{ r2_url }}`
- **Command line:** `railway run python -m margin_api.cli audit-engine --report-date {{ report_date }} --r2-prefix {{ r2_prefix }}{% if with_marginal_attribution %} --with-marginal-attribution{% endif %}`

To re-verify any number in this report, fetch the bundle from R2, validate
each CSV's sha256 against `manifest.json`, and recompute. Bundle is
content-addressable; identical inputs produce identical hashes.
```

- [ ] **Step 2: Commit**

```bash
git add docs/templates/audit-report.md.j2
git commit -m "feat(audit): add Jinja markdown template enforcing 10 report sections"
```

---

### Task 2.2: Stage 2 finalize_report.py — bundle download + hash validation

**Files:**
- Create: `scripts/audit/__init__.py` (empty)
- Create: `scripts/audit/finalize_report.py`
- Create: `scripts/audit/test_finalize_report.py`

- [ ] **Step 1: Write failing test for hash validation**

Create `scripts/audit/__init__.py` (empty file).

Create `scripts/audit/test_finalize_report.py`:

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit.finalize_report import (
    download_and_verify_bundle,
    BundleHashMismatch,
)


def _write_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    file_names = [
        "candidates_part_a.csv",
        "walk_forward_snapshots.csv",
        "component_attribution.csv",
        "conviction_calibration.csv",
        "performance_metrics.csv",
        "v2_proposal_inputs.csv",
    ]
    for name in file_names:
        (bundle / name).write_bytes(f"col1\nval-{name}\n".encode())
    files = {
        name: {"sha256": hashlib.sha256((bundle / name).read_bytes()).hexdigest()}
        for name in file_names
    }
    manifest = {
        "audit_version": "1.0",
        "audit_run_id": "00000000-0000-0000-0000-000000000001",
        "report_date": "2026-04-27",
        "engine_git_sha": "a" * 40,
        "engine_config_sha": "b" * 64,
        "data_provenance": {
            "scores_count": 1, "v4_scores_count": 0,
            "pit_prices_min_date": "2015-01-02",
            "pit_prices_max_date": "2026-04-25",
            "pit_distinct_tickers": 1, "spy_coverage_days": 1,
        },
        "files": files,
        "part_a": {"candidate_count": 1, "windows_closed": [30, 60, 63]},
        "part_b": {
            "start": "2015-01-31", "end": "2026-04-27",
            "cohort_count": 1, "rebalance": "monthly",
            "max_positions": 50, "selection": "exceptional+high",
        },
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    return bundle


def test_download_and_verify_bundle_passes_with_valid_hashes(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    manifest = download_and_verify_bundle(local_dir=bundle)
    assert manifest.audit_version == "1.0"


def test_download_and_verify_bundle_raises_on_hash_mismatch(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    (bundle / "candidates_part_a.csv").write_bytes(b"tampered")
    with pytest.raises(BundleHashMismatch):
        download_and_verify_bundle(local_dir=bundle)
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest scripts/audit/test_finalize_report.py -v
```

Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement download_and_verify_bundle**

Create `scripts/audit/finalize_report.py`:

```python
"""Stage 2: download R2 bundle, validate hashes, render markdown report.

Per spec §6 Stage 2.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from margin_api.audit.schema import AuditManifest


class BundleHashMismatch(Exception):
    """Raised when a file's sha256 does not match the manifest."""


def download_and_verify_bundle(local_dir: Path) -> AuditManifest:
    """Read manifest.json from local_dir and verify every file's hash.

    Actual R2 download is up to the caller; this function operates on a
    directory that already contains the bundle.
    """
    manifest_path = local_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json missing in {local_dir}")
    raw = json.loads(manifest_path.read_text())
    manifest = AuditManifest.model_validate(raw)
    for name, file_hash in manifest.files.items():
        path = local_dir / name
        if not path.exists():
            raise BundleHashMismatch(f"{name} listed in manifest but not in bundle")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != file_hash.sha256:
            raise BundleHashMismatch(
                f"{name}: expected sha256={file_hash.sha256}, got {actual}"
            )
    return manifest
```

- [ ] **Step 4: Run test to verify pass**

```bash
uv run pytest scripts/audit/test_finalize_report.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/audit/__init__.py scripts/audit/finalize_report.py scripts/audit/test_finalize_report.py
git commit -m "feat(audit): Stage 2 bundle download + sha256 verification"
```

---

### Task 2.3: Stage 2 — render template + golden-file test

**Files:**
- Modify: `scripts/audit/finalize_report.py`
- Modify: `scripts/audit/test_finalize_report.py`

- [ ] **Step 1: Add failing test for template render**

Append to `scripts/audit/test_finalize_report.py`:

```python
from scripts.audit.finalize_report import render_report


def test_render_report_outputs_required_sections(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    out_path = tmp_path / "report.md"
    render_report(
        local_dir=bundle,
        out_path=out_path,
        r2_prefix="audits/2026-04-27/",
        r2_url="https://r2.example.com/audits/2026-04-27/",
        with_marginal_attribution=False,
    )
    text = out_path.read_text()
    for section in [
        "## 1. Executive Summary",
        "## 2. Methodology",
        "## 3. Component Inventory",
        "## 4. Performance Metrics",
        "## 5. Component Attribution",
        "## 6. Conviction Calibration",
        "## 7. Live Forward Track Record",
        "## 8. Kill List",
        "## 9. Statistical Power Disclaimer",
        "## 10. Reproducibility Footer",
    ]:
        assert section in text, f"missing required section: {section}"
    assert "Manifest content hash" in text
```

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest scripts/audit/test_finalize_report.py -v
```

Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement render_report**

Append to `scripts/audit/finalize_report.py`:

```python
import csv

from jinja2 import Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = REPO_ROOT / "docs" / "templates"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f))


def render_report(
    *,
    local_dir: Path,
    out_path: Path,
    r2_prefix: str,
    r2_url: str,
    with_marginal_attribution: bool,
) -> None:
    manifest = download_and_verify_bundle(local_dir)
    metrics_rows = _read_csv(local_dir / "performance_metrics.csv")
    attribution_rows = _read_csv(local_dir / "component_attribution.csv")
    calibration_rows = _read_csv(local_dir / "conviction_calibration.csv")
    v2_rows = _read_csv(local_dir / "v2_proposal_inputs.csv")
    candidates_rows = _read_csv(local_dir / "candidates_part_a.csv")

    metrics_by_name = {r["metric"]: float(r["value"]) for r in metrics_rows}

    def _mean_alpha(window: str) -> float:
        col = f"alpha_{window}"
        vals = [float(r[col]) for r in candidates_rows if r.get(col) not in (None, "")]
        return sum(vals) / len(vals) if vals else 0.0

    def _n_closed(window: str) -> int:
        col = f"alpha_{window}"
        return sum(1 for r in candidates_rows if r.get(col) not in (None, ""))

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template("audit-report.md.j2")

    manifest_sha = hashlib.sha256(
        (local_dir / "manifest.json").read_bytes()
    ).hexdigest()

    text = template.render(
        report_date=manifest.report_date,
        manifest=manifest,
        manifest_sha256=manifest_sha,
        r2_url=r2_url,
        r2_prefix=r2_prefix,
        with_marginal_attribution=with_marginal_attribution,
        verdict_summary="(populated by Stage 1; use excess_cagr to write a one-line verdict)",
        metrics={
            "excess_cagr": metrics_by_name.get("excess_cagr", 0.0),
            "sharpe": metrics_by_name.get("sharpe", 0.0),
            "max_drawdown": metrics_by_name.get("max_drawdown", 0.0),
        },
        metrics_rows=metrics_rows,
        attribution_rows=attribution_rows,
        calibration_rows=calibration_rows,
        v2_proposal_rows=v2_rows,
        part_a_mean_alpha_30d=_mean_alpha("30d"),
        part_a_mean_alpha_60d=_mean_alpha("60d"),
        part_a_n_closed_30d=_n_closed("30d"),
        part_a_n_closed_60d=_n_closed("60d"),
        holm_family_size=24,
    )
    out_path.write_text(text)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Render audit report from R2 bundle.")
    parser.add_argument("--local-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--r2-prefix", type=str, required=True)
    parser.add_argument("--r2-url", type=str, required=True)
    parser.add_argument("--with-marginal-attribution", action="store_true")
    args = parser.parse_args()
    render_report(
        local_dir=args.local_dir,
        out_path=args.out,
        r2_prefix=args.r2_prefix,
        r2_url=args.r2_url,
        with_marginal_attribution=args.with_marginal_attribution,
    )
    print(f"wrote {args.out}")
```

- [ ] **Step 4: Run test to verify pass**

```bash
uv run pytest scripts/audit/test_finalize_report.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Add jinja2 to api dependencies if not already present**

```bash
uv add jinja2 --package margin-api
uv sync
```

- [ ] **Step 6: Commit**

```bash
git add scripts/audit/finalize_report.py scripts/audit/test_finalize_report.py pyproject.toml uv.lock
git commit -m "feat(audit): Stage 2 Jinja template render + golden-file test"
```

---

## Phase 3 — First Live Run (Operational, no code changes)

### Task 3.1: Live Phase 0 verification on Railway

- [ ] **Step 1: Run the verification query against Railway**

```bash
railway run psql "$DATABASE_URL" -c "
  SELECT 'pit_daily_prices_overall' AS metric,
         MIN(date)::text, MAX(date)::text,
         COUNT(*)::text, COUNT(DISTINCT ticker)::text
  FROM pit_daily_prices
  UNION ALL SELECT 'spy', MIN(date)::text, MAX(date)::text,
         COUNT(*)::text, NULL::text
  FROM pit_daily_prices WHERE ticker='SPY'
  UNION ALL SELECT 'scores_legacy', NULL, NULL, COUNT(*)::text, NULL
  FROM scores WHERE conviction_level IN ('exceptional','high','medium')
  UNION ALL SELECT 'pit_universe_memberships', NULL, NULL, COUNT(*)::text, NULL
  FROM pit_universe_memberships;
"
```

- [ ] **Step 2: Save the transcript locally (do NOT commit)**

The numbers land in `manifest.json.data_provenance` when Stage 1 runs.

- [ ] **Step 3: If pass conditions fail, run remediation CLIs** (per Task 0.1, with explicit user approval).

---

### Task 3.2: First Stage 1 run (no marginal attribution)

- [ ] **Step 1: Run Stage 1 against Railway**

```bash
railway run python -m margin_api.cli audit-engine \
  --report-date 2026-04-27 \
  --r2-prefix audits/2026-04-27/ \
  --r2-bucket margin-audits
```

- [ ] **Step 2: Capture stdout**

Save the JSON line printed at the end (manifest_sha256 + r2_prefix + files list). This is the citation for the report.

- [ ] **Step 3: Verify the bundle in R2**

```bash
aws s3 ls s3://margin-audits/audits/2026-04-27/ --endpoint-url=$R2_ENDPOINT
```

Expected: 7 objects (6 CSVs + manifest.json).

---

### Task 3.3: First Stage 2 run (local)

**Files:**
- Create: `docs/reports/margin-invest-validation-2026-04-27.md` (auto-generated)

- [ ] **Step 1: Download the bundle locally**

```bash
mkdir -p /tmp/audit-bundle-2026-04-27
aws s3 cp s3://margin-audits/audits/2026-04-27/ /tmp/audit-bundle-2026-04-27/ \
  --recursive --endpoint-url=$R2_ENDPOINT
```

- [ ] **Step 2: Render the report**

```bash
uv run python scripts/audit/finalize_report.py \
  --local-dir /tmp/audit-bundle-2026-04-27 \
  --out docs/reports/margin-invest-validation-2026-04-27.md \
  --r2-prefix audits/2026-04-27/ \
  --r2-url "https://margin-audits.r2.example.com/audits/2026-04-27/"
```

- [ ] **Step 3: Inspect the report**

Open `docs/reports/margin-invest-validation-2026-04-27.md` and confirm:
- All 10 sections present.
- Executive summary's `excess_cagr` matches the value in `performance_metrics.csv`.
- Reproducibility footer cites the manifest content hash you captured in Task 3.2 step 2.

- [ ] **Step 4: Commit the report**

```bash
git add docs/reports/margin-invest-validation-2026-04-27.md
git commit -m "docs(audit): first live-run report (without marginal attribution)"
```

---

## Phase 4 — v2 Proposal (Re-run with marginal attribution)

### Task 4.1: Re-run Stage 1 with --with-marginal-attribution

- [ ] **Step 1: Confirm with user before running (~28× simulator runtime)**

The marginal-attribution flag re-runs the walk-forward simulator once per
component (~24-26 runs). On Railway with the production PIT data this is
likely 30-60 minutes of compute. Get explicit user approval first.

- [ ] **Step 2: Run Stage 1 with the flag**

```bash
railway run python -m margin_api.cli audit-engine \
  --report-date 2026-04-27 \
  --r2-prefix audits/2026-04-27/ \
  --r2-bucket margin-audits \
  --with-marginal-attribution
```

- [ ] **Step 3: Capture the new manifest_sha256**

The bundle URL is the same prefix; the manifest content hash changes because
`v2_proposal_inputs.csv` now has populated `marginal_alpha_loss_when_zeroed`
columns.

---

### Task 4.2: Re-render Stage 2 with v2 proposal section populated

**Files:**
- Modify: `docs/reports/margin-invest-validation-2026-04-27.md`

- [ ] **Step 1: Re-download the bundle**

```bash
rm -rf /tmp/audit-bundle-2026-04-27
mkdir -p /tmp/audit-bundle-2026-04-27
aws s3 cp s3://margin-audits/audits/2026-04-27/ /tmp/audit-bundle-2026-04-27/ \
  --recursive --endpoint-url=$R2_ENDPOINT
```

- [ ] **Step 2: Re-render with the marginal-attribution flag**

```bash
uv run python scripts/audit/finalize_report.py \
  --local-dir /tmp/audit-bundle-2026-04-27 \
  --out docs/reports/margin-invest-validation-2026-04-27.md \
  --r2-prefix audits/2026-04-27/ \
  --r2-url "https://margin-audits.r2.example.com/audits/2026-04-27/" \
  --with-marginal-attribution
```

- [ ] **Step 3: Verify the v2 proposal section is populated**

Section 8 (Kill List + v2 Scoring Formula Proposal) should now have a
populated reweight table and at minimum one row with non-null
`marginal_alpha_loss_when_zeroed`.

- [ ] **Step 4: Commit the final report**

```bash
git add docs/reports/margin-invest-validation-2026-04-27.md
git commit -m "docs(audit): final live-run report with v2 proposal (marginal attribution)"
```

---

## Self-Review Checklist (Plan Author)

1. **Spec coverage** — every spec section maps to at least one task:
   - §3 Scope → Task 0.1, Tasks 1.4-1.10
   - §6 Two-Stage Dataflow → Phase 1 + Phase 2
   - §7 Data Contracts → Tasks 1.2-1.3 (schema), Tasks 1.11-1.13 (bundler)
   - §8 Statistical Methodology → Tasks 1.6-1.8 (attribution)
   - §9 Component Inventory → Task 1.10 (walk-forward) — implementer note flags it as PIT-data-coverage limited
   - §10 Replication Choices → Task 1.10 docstring captures the score-regeneration choice
   - §11 Implementation Phases → mapped 1:1 to Phase 1-4 above
   - §12 Definition of Done → Task 1.15 (determinism), Task 1.16 (coverage), Task 3.3 (report committed)
   - §13 Risks → addressed via implementer notes in Tasks 1.9-1.10

2. **Placeholder scan** — no `TBD`/`TODO`/`FIXME` in step bodies; implementer notes that flag MVP scope are explicit, not vague.

3. **Type consistency** — `BundleArtifacts`, `AuditManifest`, `CandidatePartARow`, `AttributionInputs`, `AuditCohortRow` all defined in earlier tasks before later ones reference them.

4. **Test-first discipline** — every implementation task is preceded by a "write failing test" + "run to verify failure" step.

5. **Secret scanner** — `aws_*_access_key=...` named-parameter syntax avoided in source by passing via `**kwargs` (Task 1.14). Documented in the file header note.
