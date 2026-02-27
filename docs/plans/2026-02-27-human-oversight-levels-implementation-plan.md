# Human Oversight Levels Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add three-level human oversight (in-the-loop, on-the-loop, out-of-the-loop) with backend approval gates and operator/user UIs.

**Architecture:** State machine pipeline — gated outputs move through `staged → approved → published`. New `pipeline_approvals`, `governance_events`, and `user_proposals` tables. V4Score gains `published` column; MlModelRun gains `deployment_status`. Redis stream for lightweight event logging with periodic DB rollup. Operator UI at `/admin/approvals`, user proposals integrated into existing surfaces.

**Tech Stack:** SQLAlchemy 2.0 (async), FastAPI, ARQ workers, Redis streams, Next.js 15, React 19, Tailwind v4, Vitest

**Design doc:** `docs/plans/2026-02-27-human-oversight-levels-design.md`

---

## Task Dependency Graph

```
T1 (models) ──┬──> T3 (stage_scores worker)
              ├──> T4 (publish_scores worker)
              ├──> T5 (ML deployment gate)
              ├──> T6 (universe activation gate)
              ├──> T7 (circuit breakers)
              ├──> T8 (governance event stream)
              └──> T9 (expiry daemon)

T2 (migration) ──> T3, T4, T5, T6

T3, T4 ──> T10 (score serving filter)

T8 ──> T11 (event rollup worker)

T3-T9 ──> T12 (admin approval API)
T12 ──> T13 (governance dashboard API)
T12 ──> T14 (transparency endpoint)

T12, T13, T14 ──> T15 (operator approval UI)
T15 ──> T16 (pipeline monitor UI)
T15 ──> T17 (event log UI)

T10 ──> T18 (user proposals model + API)
T18 ──> T19 (user proposal UI)
```

**Parallel groups:**
- **Group A** (T1–T2): Data model + migration
- **Group B** (T3–T9): Backend enforcement — all depend on T1+T2, independent of each other
- **Group C** (T10): Score serving filter — depends on T3+T4
- **Group D** (T11–T14): API layer — depends on Group B
- **Group E** (T15–T17): Operator UI — depends on Group D
- **Group F** (T18–T19): User proposals — depends on T10

---

### Task 1: Add Governance Data Models

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Test: `api/tests/test_governance_models.py`

**Step 1: Write the failing test**

```python
"""Tests for governance data models."""

import pytest
from datetime import UTC, datetime

from margin_api.db.models import (
    GovernanceConfig,
    GovernanceEvent,
    PipelineApproval,
    UserProposal,
    V4Score,
    MlModelRun,
)


def test_pipeline_approval_fields():
    """PipelineApproval has all required columns."""
    approval = PipelineApproval(
        gate_type="score_publish",
        status="staged",
        pipeline_id="abc123",
        payload_ref={"scored_at": "2026-02-27T00:00:00Z", "ticker_count": 47},
        impact_summary={"conviction_changes": 3},
        submitted_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )
    assert approval.gate_type == "score_publish"
    assert approval.status == "staged"
    assert approval.payload_ref["ticker_count"] == 47
    assert approval.decided_by is None
    assert approval.decision_reason is None


def test_governance_event_fields():
    """GovernanceEvent has all required columns."""
    event = GovernanceEvent(
        event_type="ingestion.ticker.success",
        source="ingest_batch",
        detail={"ticker": "AAPL", "duration_ms": 1234},
    )
    assert event.event_type == "ingestion.ticker.success"
    assert event.detail["ticker"] == "AAPL"


def test_governance_config_fields():
    """GovernanceConfig stores key-value pairs."""
    config = GovernanceConfig(
        config_key="circuit_breaker.score_drift_pct",
        config_value={"threshold": 0.30, "description": "Max % universe conviction change"},
    )
    assert config.config_key == "circuit_breaker.score_drift_pct"
    assert config.config_value["threshold"] == 0.30


def test_user_proposal_fields():
    """UserProposal has all required columns."""
    proposal = UserProposal(
        user_id=1,
        proposal_type="watchlist_add",
        status="pending",
        payload={"ticker": "AAPL", "rationale": "Score improved to 85th percentile"},
    )
    assert proposal.proposal_type == "watchlist_add"
    assert proposal.status == "pending"


def test_v4score_published_default():
    """V4Score.published defaults to False."""
    score = V4Score(
        asset_id=1,
        opportunity_type="value",
        conviction="high",
        rules_conviction="high",
        style="value",
        timing_signal="neutral",
        regime="expansion",
        composite_score=75.0,
    )
    assert score.published is False


def test_ml_model_run_deployment_status_default():
    """MlModelRun.deployment_status defaults to 'candidate'."""
    run = MlModelRun(
        model_type="lightgbm_cluster",
    )
    assert run.deployment_status == "candidate"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_governance_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'PipelineApproval'`

**Step 3: Write the models**

Add to `api/src/margin_api/db/models.py` (after the AuditLog class, near line 880):

```python
class PipelineApproval(Base):
    """Tracks approval gates for high-stakes pipeline outputs."""

    __tablename__ = "pipeline_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    gate_type: Mapped[str] = mapped_column(String(30))  # score_publish | ml_model_deploy | universe_activate | filter_config_change
    status: Mapped[str] = mapped_column(String(20), default="staged")  # staged | approved | rejected | expired
    pipeline_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    payload_ref: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    impact_summary: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_pipeline_approvals_status", "status"),
        Index("ix_pipeline_approvals_gate_type", "gate_type"),
    )


class GovernanceEvent(Base):
    """Lightweight event log for autonomous system actions."""

    __tablename__ = "governance_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    source: Mapped[str] = mapped_column(String(50))
    detail: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class GovernanceConfig(Base):
    """Key-value configuration for governance thresholds."""

    __tablename__ = "governance_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    config_key: Mapped[str] = mapped_column(String(100), unique=True)
    config_value: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class UserProposal(Base):
    """Tracks system-generated proposals for end-user approval."""

    __tablename__ = "user_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    proposal_type: Mapped[str] = mapped_column(String(30))  # watchlist_add | watchlist_remove | alert_config | portfolio_suggestion
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | accepted | dismissed | expired
    payload: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_user_proposals_user_status", "user_id", "status"),
    )
```

Also add to **V4Score** class (after `detail` field, around line 327):

```python
    published: Mapped[bool] = mapped_column(default=False)
```

Also add to **MlModelRun** class (after `vae_model_checksum` field, around line 510):

```python
    deployment_status: Mapped[str] = mapped_column(String(20), default="candidate")  # candidate | active | retired
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_governance_models.py -v`
Expected: PASS — all 6 tests green

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_governance_models.py
git commit -m "feat(api): add governance data models for human oversight levels"
```

---

### Task 2: Create Alembic Migration

**Files:**
- Create: `api/alembic/versions/<auto>_add_governance_tables_and_columns.py`

**Step 1: Generate the migration**

Run: `cd api && uv run alembic revision --autogenerate -m "add governance tables and columns"`

**Step 2: Verify the migration**

Open the generated file and verify it contains:
- `create_table("pipeline_approvals", ...)` with all columns and indexes
- `create_table("governance_events", ...)` with columns and indexes
- `create_table("governance_configs", ...)` with unique constraint on config_key
- `create_table("user_proposals", ...)` with columns and indexes
- `add_column("v4_scores", Column("published", Boolean, default=False))`
- `add_column("ml_model_runs", Column("deployment_status", String(20), default="candidate"))`

Edit the migration to add idempotent checks (following project pattern from MEMORY.md):

```python
def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not inspector.has_table("pipeline_approvals"):
        op.create_table("pipeline_approvals", ...)

    if not inspector.has_table("governance_events"):
        op.create_table("governance_events", ...)

    if not inspector.has_table("governance_configs"):
        op.create_table("governance_configs", ...)

    if not inspector.has_table("user_proposals"):
        op.create_table("user_proposals", ...)

    # Add columns to existing tables
    existing_v4_cols = [c["name"] for c in inspector.get_columns("v4_scores")]
    if "published" not in existing_v4_cols:
        op.add_column("v4_scores", sa.Column("published", sa.Boolean(), server_default="false"))

    existing_ml_cols = [c["name"] for c in inspector.get_columns("ml_model_runs")]
    if "deployment_status" not in existing_ml_cols:
        op.add_column("ml_model_runs", sa.Column("deployment_status", sa.String(20), server_default="candidate"))
```

**Step 3: Check for multiple heads**

Run: `cd api && uv run alembic heads`
Expected: Single head. If multiple, create a merge migration.

**Step 4: Test the migration**

Run: `cd api && uv run alembic upgrade head`
Expected: Migration applies successfully

**Step 5: Commit**

```bash
git add api/alembic/versions/
git commit -m "feat(api): add alembic migration for governance tables and columns"
```

---

### Task 3: Add `stage_scores` Worker Job

**Files:**
- Modify: `api/src/margin_api/workers.py`
- Test: `api/tests/test_stage_scores.py`

**Step 1: Write the failing test**

```python
"""Tests for stage_scores worker job."""

import pytest
import pytest_asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import (
    Asset,
    PipelineApproval,
    V4Score,
)


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_stage_scores_creates_approval(async_session: AsyncSession):
    """stage_scores creates a PipelineApproval row with status=staged."""
    from margin_api.workers import _stage_scores_impl

    # Seed an asset and unpublished V4Score
    asset = Asset(ticker="AAPL", name="Apple Inc", sector="Technology")
    async_session.add(asset)
    await async_session.flush()

    score = V4Score(
        asset_id=asset.id,
        scored_at=datetime.now(UTC),
        opportunity_type="quality",
        conviction="high",
        rules_conviction="high",
        style="growth",
        timing_signal="neutral",
        regime="expansion",
        composite_score=82.0,
        published=False,
    )
    async_session.add(score)
    await async_session.commit()

    pipeline_id = "test-pipeline-123"
    result = await _stage_scores_impl(async_session, pipeline_id, score.scored_at)

    assert result["status"] == "staged"

    # Verify PipelineApproval was created
    approvals = (await async_session.execute(select(PipelineApproval))).scalars().all()
    assert len(approvals) == 1
    assert approvals[0].gate_type == "score_publish"
    assert approvals[0].status == "staged"
    assert approvals[0].pipeline_id == pipeline_id
    assert approvals[0].payload_ref["ticker_count"] == 1
    assert approvals[0].expires_at is not None


@pytest.mark.asyncio
async def test_stage_scores_computes_impact_summary(async_session: AsyncSession):
    """stage_scores includes conviction changes in impact_summary."""
    from margin_api.workers import _stage_scores_impl

    asset = Asset(ticker="AAPL", name="Apple Inc", sector="Technology")
    async_session.add(asset)
    await async_session.flush()

    # Previous published score
    old_score = V4Score(
        asset_id=asset.id,
        scored_at=datetime.now(UTC) - timedelta(days=1),
        opportunity_type="quality",
        conviction="medium",
        rules_conviction="medium",
        style="growth",
        timing_signal="neutral",
        regime="expansion",
        composite_score=55.0,
        published=True,
    )
    # New unpublished score
    new_score = V4Score(
        asset_id=asset.id,
        scored_at=datetime.now(UTC),
        opportunity_type="quality",
        conviction="high",
        rules_conviction="high",
        style="growth",
        timing_signal="neutral",
        regime="expansion",
        composite_score=82.0,
        published=False,
    )
    async_session.add_all([old_score, new_score])
    await async_session.commit()

    result = await _stage_scores_impl(async_session, "pipeline-456", new_score.scored_at)

    approvals = (await async_session.execute(select(PipelineApproval))).scalars().all()
    summary = approvals[0].impact_summary
    assert summary["conviction_changes"] == 1
    assert summary["ticker_count"] == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_stage_scores.py -v`
Expected: FAIL — `ImportError: cannot import name '_stage_scores_impl'`

**Step 3: Implement `_stage_scores_impl` and `stage_scores`**

Add to `api/src/margin_api/workers.py` after the `full_score_v4` function (around line 775):

```python
async def _stage_scores_impl(
    session: AsyncSession,
    pipeline_id: str,
    scored_at: datetime,
) -> dict:
    """Create a PipelineApproval for a batch of unpublished V4Scores.

    Computes impact summary by comparing new unpublished scores against
    the latest published scores for each asset.
    """
    from margin_api.db.models import PipelineApproval, V4Score, Asset

    # Count unpublished scores in this batch
    unpublished = (
        await session.execute(
            select(V4Score)
            .where(V4Score.scored_at == scored_at)
            .where(V4Score.published == False)  # noqa: E712
        )
    ).scalars().all()

    ticker_count = len(unpublished)
    conviction_changes = 0

    for score in unpublished:
        # Find latest published score for this asset
        prev = (
            await session.execute(
                select(V4Score)
                .where(V4Score.asset_id == score.asset_id)
                .where(V4Score.published == True)  # noqa: E712
                .order_by(V4Score.scored_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if prev and prev.conviction != score.conviction:
            conviction_changes += 1

    # Default expiry: 24 hours
    config_expiry_hours = 24
    expires_at = datetime.now(UTC) + timedelta(hours=config_expiry_hours)

    approval = PipelineApproval(
        gate_type="score_publish",
        status="staged",
        pipeline_id=pipeline_id,
        payload_ref={
            "scored_at": scored_at.isoformat(),
            "ticker_count": ticker_count,
        },
        impact_summary={
            "ticker_count": ticker_count,
            "conviction_changes": conviction_changes,
        },
        submitted_at=datetime.now(UTC),
        expires_at=expires_at,
    )
    session.add(approval)
    await session.commit()

    return {"status": "staged", "approval_id": approval.id, "ticker_count": ticker_count}


async def stage_scores(
    ctx: dict,
    pipeline_id: str | None = None,
    parent_job_id: int | None = None,
    scored_at_iso: str | None = None,
) -> dict:
    """Stage unpublished V4Scores for operator approval.

    Creates a PipelineApproval row and sends an operator notification.
    Chained after full_score_v4.
    """
    logger.info("[stage_scores] Staging scores for approval (pipeline=%s)", pipeline_id)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        job = JobRun(
            job_type="stage_scores",
            status="running",
            triggered_by="chained",
            parent_job_id=parent_job_id,
            pipeline_id=pipeline_id,
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    try:
        scored_at = datetime.fromisoformat(scored_at_iso) if scored_at_iso else datetime.now(UTC)

        async with session_factory() as session:
            result = await _stage_scores_impl(session, pipeline_id or "", scored_at)

        async with session_factory() as session:
            job_result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = job_result.scalar_one()
            job.status = "completed"
            job.progress = 1.0
            job.completed_at = datetime.now(UTC)
            await session.commit()

        logger.info(
            "[stage_scores] Staged %d scores for approval (approval_id=%s)",
            result["ticker_count"],
            result["approval_id"],
        )
        return {"status": "staged", "pipeline_id": pipeline_id, **result}

    except Exception as e:
        logger.exception("[stage_scores] Failed: %s", e)
        async with session_factory() as session:
            job_result = await session.execute(select(JobRun).where(JobRun.id == job_id))
            job = job_result.scalar_one()
            job.status = "failed"
            job.error_message = str(e)[:500]
            job.completed_at = datetime.now(UTC)
            await session.commit()
        return {"status": "failed", "pipeline_id": pipeline_id, "error": str(e)}
```

Then modify `full_score_v4` (around line 764–772) to remove the WebSocket event emission and chain to `stage_scores` instead:

```python
    # Replace the WebSocket emission block with:
    # Chain to stage_scores for operator approval
    try:
        redis: ArqRedis | None = ctx.get("redis")
        if redis:
            await redis.enqueue_job(
                "stage_scores",
                pipeline_id=pipeline_id,
                parent_job_id=job_id,
                scored_at_iso=datetime.now(UTC).isoformat(),
                _job_id=f"stage_scores:{uuid.uuid4().hex[:8]}",
            )
            logger.info("[score_v4] Enqueued stage_scores for approval")
    except Exception as e:
        logger.warning("[score_v4] Failed to enqueue stage_scores: %s", e)
```

Register `stage_scores` in `WorkerSettings.functions` list.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_stage_scores.py -v`
Expected: PASS

**Step 5: Run existing tests to verify no regressions**

Run: `uv run pytest api/tests/ -v --timeout=60`
Expected: All passing

**Step 6: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_stage_scores.py
git commit -m "feat(api): add stage_scores worker job for score approval gate"
```

---

### Task 4: Add `publish_scores` Worker Job

**Files:**
- Modify: `api/src/margin_api/workers.py`
- Test: `api/tests/test_publish_scores.py`

**Step 1: Write the failing test**

```python
"""Tests for publish_scores worker job."""

import pytest
import pytest_asyncio
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import Asset, PipelineApproval, V4Score


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_publish_scores_flips_published(async_session: AsyncSession):
    """publish_scores sets published=True on matching V4Scores."""
    from margin_api.workers import _publish_scores_impl

    asset = Asset(ticker="AAPL", name="Apple Inc", sector="Technology")
    async_session.add(asset)
    await async_session.flush()

    scored_at = datetime.now(UTC)
    score = V4Score(
        asset_id=asset.id,
        scored_at=scored_at,
        opportunity_type="quality",
        conviction="high",
        rules_conviction="high",
        style="growth",
        timing_signal="neutral",
        regime="expansion",
        composite_score=82.0,
        published=False,
    )
    async_session.add(score)

    approval = PipelineApproval(
        gate_type="score_publish",
        status="staged",
        payload_ref={"scored_at": scored_at.isoformat(), "ticker_count": 1},
    )
    async_session.add(approval)
    await async_session.commit()

    result = await _publish_scores_impl(async_session, approval.id)

    assert result["status"] == "published"
    assert result["published_count"] == 1

    # Verify score is now published
    updated = (await async_session.execute(select(V4Score))).scalar_one()
    assert updated.published is True

    # Verify approval is marked approved
    updated_approval = (await async_session.execute(select(PipelineApproval))).scalar_one()
    assert updated_approval.status == "approved"


@pytest.mark.asyncio
async def test_publish_scores_rejects_non_staged(async_session: AsyncSession):
    """publish_scores rejects approval that's not in staged status."""
    from margin_api.workers import _publish_scores_impl

    approval = PipelineApproval(
        gate_type="score_publish",
        status="approved",  # Already approved
        payload_ref={"scored_at": datetime.now(UTC).isoformat(), "ticker_count": 0},
    )
    async_session.add(approval)
    await async_session.commit()

    result = await _publish_scores_impl(async_session, approval.id)
    assert result["status"] == "error"
    assert "not in staged status" in result["message"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_publish_scores.py -v`
Expected: FAIL — `ImportError: cannot import name '_publish_scores_impl'`

**Step 3: Implement `_publish_scores_impl` and `publish_scores`**

Add to `api/src/margin_api/workers.py` after `stage_scores`:

```python
async def _publish_scores_impl(
    session: AsyncSession,
    approval_id: int,
    decided_by: int | None = None,
    decision_reason: str | None = None,
) -> dict:
    """Publish staged V4Scores by flipping published=True.

    Also updates the PipelineApproval status and emits score change events.
    """
    from margin_api.db.models import PipelineApproval, V4Score

    approval = (
        await session.execute(
            select(PipelineApproval).where(PipelineApproval.id == approval_id)
        )
    ).scalar_one_or_none()

    if not approval:
        return {"status": "error", "message": f"Approval {approval_id} not found"}

    if approval.status != "staged":
        return {"status": "error", "message": f"Approval {approval_id} not in staged status ({approval.status})"}

    scored_at = datetime.fromisoformat(approval.payload_ref["scored_at"])

    # Flip all matching unpublished scores to published
    scores = (
        await session.execute(
            select(V4Score)
            .where(V4Score.scored_at == scored_at)
            .where(V4Score.published == False)  # noqa: E712
        )
    ).scalars().all()

    for score in scores:
        score.published = True

    # Update approval status
    approval.status = "approved"
    approval.decided_at = datetime.now(UTC)
    approval.decided_by = decided_by
    approval.decision_reason = decision_reason

    await session.commit()

    return {"status": "published", "published_count": len(scores), "approval_id": approval_id}


async def publish_scores(
    ctx: dict,
    approval_id: int,
    decided_by: int | None = None,
    decision_reason: str | None = None,
) -> dict:
    """Publish approved scores and emit WebSocket events.

    Triggered by operator approval via admin API.
    """
    logger.info("[publish_scores] Publishing scores for approval_id=%d", approval_id)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    try:
        async with session_factory() as session:
            result = await _publish_scores_impl(session, approval_id, decided_by, decision_reason)

        if result["status"] == "published":
            # Emit score change events and broadcast via WebSocket
            async with session_factory() as session:
                n_events = await _emit_score_change_events(session)
                if n_events:
                    logger.info("[publish_scores] Emitted %d score change events", n_events)
                    await _broadcast_score_events(session)
                    logger.info("[publish_scores] Broadcast score change events via WebSocket")

        return result

    except Exception as e:
        logger.exception("[publish_scores] Failed: %s", e)
        return {"status": "failed", "error": str(e)}
```

Register `publish_scores` in `WorkerSettings.functions` list.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_publish_scores.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_publish_scores.py
git commit -m "feat(api): add publish_scores worker job for score publication gate"
```

---

### Task 5: Add ML Model Deployment Gate

**Files:**
- Modify: `api/src/margin_api/workers.py`
- Test: `api/tests/test_ml_deployment_gate.py`

**Step 1: Write the failing test**

```python
"""Tests for ML model deployment gate."""

import pytest
import pytest_asyncio
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import MlModelRun, PipelineApproval


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_stage_ml_model_creates_approval(async_session: AsyncSession):
    """stage_ml_model creates a PipelineApproval for candidate model."""
    from margin_api.workers import _stage_ml_model_impl

    model = MlModelRun(
        model_type="lightgbm_cluster",
        model_qualifies=True,
        overall_rank_ic=0.22,
        n_clusters=5,
        n_features=12,
        n_samples=200,
        deployment_status="candidate",
    )
    async_session.add(model)
    await async_session.commit()

    result = await _stage_ml_model_impl(async_session, model.id)

    assert result["status"] == "staged"
    approval = (await async_session.execute(select(PipelineApproval))).scalar_one()
    assert approval.gate_type == "ml_model_deploy"
    assert approval.impact_summary["rank_ic"] == 0.22
    assert approval.impact_summary["model_qualifies"] is True


@pytest.mark.asyncio
async def test_promote_ml_model_sets_active(async_session: AsyncSession):
    """promote_ml_model sets deployment_status=active and retires previous."""
    from margin_api.workers import _promote_ml_model_impl

    # Existing active model
    old_model = MlModelRun(
        model_type="lightgbm_cluster",
        model_qualifies=True,
        overall_rank_ic=0.18,
        deployment_status="active",
    )
    # New candidate model
    new_model = MlModelRun(
        model_type="lightgbm_cluster",
        model_qualifies=True,
        overall_rank_ic=0.25,
        deployment_status="candidate",
    )
    async_session.add_all([old_model, new_model])
    await async_session.commit()

    approval = PipelineApproval(
        gate_type="ml_model_deploy",
        status="staged",
        payload_ref={"ml_model_run_id": new_model.id},
    )
    async_session.add(approval)
    await async_session.commit()

    result = await _promote_ml_model_impl(async_session, approval.id)

    assert result["status"] == "promoted"

    # Verify new model is active
    refreshed_new = (
        await async_session.execute(
            select(MlModelRun).where(MlModelRun.id == new_model.id)
        )
    ).scalar_one()
    assert refreshed_new.deployment_status == "active"

    # Verify old model is retired
    refreshed_old = (
        await async_session.execute(
            select(MlModelRun).where(MlModelRun.id == old_model.id)
        )
    ).scalar_one()
    assert refreshed_old.deployment_status == "retired"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_ml_deployment_gate.py -v`
Expected: FAIL — `ImportError`

**Step 3: Implement `_stage_ml_model_impl` and `_promote_ml_model_impl`**

Add to `api/src/margin_api/workers.py` after `publish_scores`:

```python
async def _stage_ml_model_impl(
    session: AsyncSession,
    model_run_id: int,
) -> dict:
    """Create a PipelineApproval for a candidate ML model."""
    from margin_api.db.models import MlModelRun, PipelineApproval

    model = (
        await session.execute(select(MlModelRun).where(MlModelRun.id == model_run_id))
    ).scalar_one_or_none()

    if not model:
        return {"status": "error", "message": f"MlModelRun {model_run_id} not found"}

    # Find currently active model for comparison
    active = (
        await session.execute(
            select(MlModelRun)
            .where(MlModelRun.deployment_status == "active")
            .order_by(MlModelRun.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    impact = {
        "rank_ic": model.overall_rank_ic,
        "model_qualifies": model.model_qualifies,
        "n_clusters": model.n_clusters,
        "n_features": model.n_features,
        "n_samples": model.n_samples,
    }
    if active:
        impact["previous_rank_ic"] = active.overall_rank_ic
        impact["rank_ic_delta"] = round((model.overall_rank_ic or 0) - (active.overall_rank_ic or 0), 4)

    approval = PipelineApproval(
        gate_type="ml_model_deploy",
        status="staged",
        payload_ref={"ml_model_run_id": model.id},
        impact_summary=impact,
        submitted_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=48),  # ML models get 48h window
    )
    session.add(approval)
    await session.commit()

    return {"status": "staged", "approval_id": approval.id}


async def _promote_ml_model_impl(
    session: AsyncSession,
    approval_id: int,
    decided_by: int | None = None,
    decision_reason: str | None = None,
) -> dict:
    """Promote a candidate ML model to active, retire previous active."""
    from margin_api.db.models import MlModelRun, PipelineApproval

    approval = (
        await session.execute(select(PipelineApproval).where(PipelineApproval.id == approval_id))
    ).scalar_one_or_none()

    if not approval or approval.status != "staged":
        return {"status": "error", "message": f"Approval {approval_id} not in staged status"}

    model_id = approval.payload_ref["ml_model_run_id"]

    # Retire all currently active models
    active_models = (
        await session.execute(
            select(MlModelRun).where(MlModelRun.deployment_status == "active")
        )
    ).scalars().all()
    for m in active_models:
        m.deployment_status = "retired"

    # Promote candidate
    new_model = (
        await session.execute(select(MlModelRun).where(MlModelRun.id == model_id))
    ).scalar_one()
    new_model.deployment_status = "active"

    # Update approval
    approval.status = "approved"
    approval.decided_at = datetime.now(UTC)
    approval.decided_by = decided_by
    approval.decision_reason = decision_reason

    await session.commit()

    return {"status": "promoted", "model_id": model_id, "approval_id": approval_id}
```

Then modify `train_ml_models` to set `deployment_status="candidate"` and call `_stage_ml_model_impl` at the end instead of directly setting `model_qualifies` as the only gate. Find where `MlModelRun` is created (around line 1300–1340) and ensure `deployment_status="candidate"` is set. After the commit, add:

```python
    # Stage for operator approval
    async with session_factory() as session:
        await _stage_ml_model_impl(session, model_run.id)
    logger.info("[train_ml] Staged model %d for operator approval", model_run.id)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_ml_deployment_gate.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_ml_deployment_gate.py
git commit -m "feat(api): add ML model deployment gate with staging and promotion"
```

---

### Task 6: Add Universe Activation Gate

**Files:**
- Modify: `api/src/margin_api/routes/admin.py`
- Test: `api/tests/test_universe_gate.py`

**Step 1: Write the failing test**

```python
"""Tests for universe activation gate."""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from margin_api.app import create_app
from margin_api.config import get_settings


class TestUniverseActivationGate:
    def setup_method(self):
        get_settings.cache_clear()

    def teardown_method(self):
        get_settings.cache_clear()

    def _make_client(self, admin_key: str = "test-admin-key"):
        with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": admin_key}):
            app = create_app()
            return TestClient(app)

    def test_activate_creates_pending_approval(self):
        """POST /admin/universe/activate creates a pending approval instead of immediate activation."""
        client = self._make_client()

        with patch("margin_api.routes.admin.stage_universe_activation") as mock_stage:
            mock_stage.return_value = {
                "status": "staged",
                "approval_id": 1,
                "added_tickers": ["NVDA"],
                "removed_tickers": ["GE"],
            }

            response = client.post(
                "/api/v1/admin/universe/activate",
                headers={"X-Admin-Key": "test-admin-key"},
            )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "staged"
        assert body["approval_id"] == 1

    def test_activate_requires_admin_key(self):
        """POST /admin/universe/activate rejects without admin key."""
        client = self._make_client()
        response = client.post(
            "/api/v1/admin/universe/activate",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert response.status_code == 403
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_universe_gate.py -v`
Expected: FAIL — `stage_universe_activation` doesn't exist or endpoint still returns 200

**Step 3: Modify the `activate_universe_endpoint`**

In `api/src/margin_api/routes/admin.py`, change the endpoint to create a staging approval instead of immediate activation:

```python
@router.post("/universe/activate", status_code=202)
@limiter.limit("3/minute")
async def activate_universe_endpoint(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Stage a universe activation for operator approval.

    Computes the diff between current and proposed universe, creates a
    PipelineApproval, and returns 202 Accepted.
    """
    _verify_admin_key(x_admin_key)

    result = await stage_universe_activation(session)
    return result
```

Implement `stage_universe_activation` as a helper:

```python
async def stage_universe_activation(session: AsyncSession) -> dict:
    """Compare proposed universe against current and create approval."""
    from margin_api.db.models import PipelineApproval, UniverseSnapshot
    from margin_api.services.universe import load_universe_config

    # Load proposed config
    candidates = [
        Path("/app/engine/universe.yaml"),
        Path(__file__).resolve().parents[4] / "engine" / "universe.yaml",
    ]
    config_path = next((c for c in candidates if c.exists()), None)
    if not config_path:
        raise HTTPException(500, "universe.yaml not found")

    proposed_tickers = load_universe_config(config_path)

    # Get current active snapshot
    current = (
        await session.execute(
            select(UniverseSnapshot).where(UniverseSnapshot.is_active == True).limit(1)  # noqa: E712
        )
    ).scalar_one_or_none()

    current_tickers = set(current.tickers) if current and current.tickers else set()
    proposed_set = set(proposed_tickers)

    added = sorted(proposed_set - current_tickers)
    removed = sorted(current_tickers - proposed_set)

    approval = PipelineApproval(
        gate_type="universe_activate",
        status="staged",
        payload_ref={"config_path": str(config_path), "proposed_tickers": proposed_tickers},
        impact_summary={
            "current_count": len(current_tickers),
            "proposed_count": len(proposed_set),
            "added_tickers": added,
            "removed_tickers": removed,
        },
        submitted_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    session.add(approval)
    await session.commit()

    return {
        "status": "staged",
        "approval_id": approval.id,
        "added_tickers": added,
        "removed_tickers": removed,
    }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_universe_gate.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/admin.py api/tests/test_universe_gate.py
git commit -m "feat(api): add universe activation gate with staging approval"
```

---

### Task 7: Add Circuit Breaker Logic

**Files:**
- Create: `api/src/margin_api/services/circuit_breaker.py`
- Test: `api/tests/test_circuit_breaker.py`

**Step 1: Write the failing test**

```python
"""Tests for circuit breaker auto-escalation."""

import pytest
import pytest_asyncio
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score, GovernanceConfig


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_score_drift_triggers_when_threshold_exceeded(async_session: AsyncSession):
    """Circuit breaker triggers when >30% of universe changes conviction."""
    from margin_api.services.circuit_breaker import check_score_drift

    scored_at = datetime.now(UTC)

    # Create 10 assets, 4 with conviction changes (40% > 30% threshold)
    for i in range(10):
        asset = Asset(ticker=f"T{i:03d}", name=f"Test {i}", sector="Technology")
        async_session.add(asset)
        await async_session.flush()

        # Previous published score
        old_conviction = "medium"
        new_conviction = "high" if i < 4 else "medium"  # 4 out of 10 change

        old = V4Score(
            asset_id=asset.id,
            scored_at=datetime(2026, 2, 26, tzinfo=UTC),
            opportunity_type="quality",
            conviction=old_conviction,
            rules_conviction=old_conviction,
            style="growth",
            timing_signal="neutral",
            regime="expansion",
            composite_score=50.0,
            published=True,
        )
        new = V4Score(
            asset_id=asset.id,
            scored_at=scored_at,
            opportunity_type="quality",
            conviction=new_conviction,
            rules_conviction=new_conviction,
            style="growth",
            timing_signal="neutral",
            regime="expansion",
            composite_score=80.0 if i < 4 else 50.0,
            published=False,
        )
        async_session.add_all([old, new])

    await async_session.commit()

    result = await check_score_drift(async_session, scored_at, threshold_pct=0.30)
    assert result.triggered is True
    assert result.drift_pct == pytest.approx(0.4)


@pytest.mark.asyncio
async def test_score_drift_does_not_trigger_below_threshold(async_session: AsyncSession):
    """Circuit breaker does not trigger when conviction changes are below threshold."""
    from margin_api.services.circuit_breaker import check_score_drift

    scored_at = datetime.now(UTC)

    # Create 10 assets, only 2 with conviction changes (20% < 30% threshold)
    for i in range(10):
        asset = Asset(ticker=f"T{i:03d}", name=f"Test {i}", sector="Technology")
        async_session.add(asset)
        await async_session.flush()

        old_conviction = "medium"
        new_conviction = "high" if i < 2 else "medium"

        old = V4Score(
            asset_id=asset.id,
            scored_at=datetime(2026, 2, 26, tzinfo=UTC),
            opportunity_type="quality",
            conviction=old_conviction,
            rules_conviction=old_conviction,
            style="growth",
            timing_signal="neutral",
            regime="expansion",
            composite_score=50.0,
            published=True,
        )
        new = V4Score(
            asset_id=asset.id,
            scored_at=scored_at,
            opportunity_type="quality",
            conviction=new_conviction,
            rules_conviction=new_conviction,
            style="growth",
            timing_signal="neutral",
            regime="expansion",
            composite_score=80.0 if i < 2 else 50.0,
            published=False,
        )
        async_session.add_all([old, new])

    await async_session.commit()

    result = await check_score_drift(async_session, scored_at, threshold_pct=0.30)
    assert result.triggered is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_circuit_breaker.py -v`
Expected: FAIL — module not found

**Step 3: Implement circuit breaker service**

Create `api/src/margin_api/services/circuit_breaker.py`:

```python
"""Circuit breaker for auto-escalating on-the-loop actions to in-the-loop."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import V4Score


@dataclass
class CircuitBreakerResult:
    triggered: bool
    drift_pct: float
    detail: str


async def check_score_drift(
    session: AsyncSession,
    scored_at: datetime,
    threshold_pct: float = 0.30,
) -> CircuitBreakerResult:
    """Check if conviction drift exceeds threshold.

    Compares new unpublished scores against latest published scores.
    Returns triggered=True if % of universe with conviction changes > threshold.
    """
    # Get new unpublished scores
    new_scores = (
        await session.execute(
            select(V4Score)
            .where(V4Score.scored_at == scored_at)
            .where(V4Score.published == False)  # noqa: E712
        )
    ).scalars().all()

    if not new_scores:
        return CircuitBreakerResult(triggered=False, drift_pct=0.0, detail="No new scores")

    total = len(new_scores)
    conviction_changes = 0

    for score in new_scores:
        prev = (
            await session.execute(
                select(V4Score)
                .where(V4Score.asset_id == score.asset_id)
                .where(V4Score.published == True)  # noqa: E712
                .order_by(V4Score.scored_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if prev and prev.conviction != score.conviction:
            conviction_changes += 1

    drift_pct = conviction_changes / total if total > 0 else 0.0

    return CircuitBreakerResult(
        triggered=drift_pct > threshold_pct,
        drift_pct=drift_pct,
        detail=f"{conviction_changes}/{total} assets changed conviction ({drift_pct:.1%})",
    )


async def check_ingestion_failure_rate(
    failed_count: int,
    total_count: int,
    threshold_pct: float = 0.20,
) -> CircuitBreakerResult:
    """Check if ingestion failure rate exceeds threshold."""
    rate = failed_count / total_count if total_count > 0 else 0.0
    return CircuitBreakerResult(
        triggered=rate > threshold_pct,
        drift_pct=rate,
        detail=f"{failed_count}/{total_count} tickers failed ({rate:.1%})",
    )


async def check_ml_regression(
    new_rank_ic: float | None,
    active_rank_ic: float | None,
    threshold_pct: float = 0.50,
) -> CircuitBreakerResult:
    """Check if new model's rank IC regressed significantly vs active."""
    if not new_rank_ic or not active_rank_ic or active_rank_ic == 0:
        return CircuitBreakerResult(triggered=False, drift_pct=0.0, detail="Insufficient data")

    regression_pct = (active_rank_ic - new_rank_ic) / active_rank_ic
    return CircuitBreakerResult(
        triggered=regression_pct > threshold_pct,
        drift_pct=regression_pct,
        detail=f"Rank IC: {active_rank_ic:.3f} → {new_rank_ic:.3f} ({regression_pct:.1%} regression)",
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_circuit_breaker.py -v`
Expected: PASS

**Step 5: Wire circuit breaker into `stage_scores`**

In `_stage_scores_impl`, add after computing impact summary:

```python
    from margin_api.services.circuit_breaker import check_score_drift

    drift_result = await check_score_drift(session, scored_at)
    if drift_result.triggered:
        impact["circuit_breaker"] = {
            "triggered": True,
            "type": "score_drift",
            "detail": drift_result.detail,
        }
```

**Step 6: Commit**

```bash
git add api/src/margin_api/services/circuit_breaker.py api/tests/test_circuit_breaker.py api/src/margin_api/workers.py
git commit -m "feat(api): add circuit breaker auto-escalation for score drift and ingestion failures"
```

---

### Task 8: Add Governance Event Emission

**Files:**
- Create: `api/src/margin_api/services/governance_events.py`
- Test: `api/tests/test_governance_events.py`

**Step 1: Write the failing test**

```python
"""Tests for governance event emission."""

import pytest
from unittest.mock import AsyncMock, patch

from margin_api.services.governance_events import emit_governance_event, GovernanceEventEmitter


@pytest.mark.asyncio
async def test_emit_event_to_redis():
    """emit_governance_event writes to Redis stream."""
    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="1234-0")

    emitter = GovernanceEventEmitter(mock_redis)
    await emitter.emit("ingestion.ticker.success", "ingest_batch", {"ticker": "AAPL", "duration_ms": 500})

    mock_redis.xadd.assert_called_once()
    call_args = mock_redis.xadd.call_args
    assert call_args[0][0] == "governance:events"
    fields = call_args[0][1]
    assert fields["event_type"] == "ingestion.ticker.success"
    assert fields["source"] == "ingest_batch"


@pytest.mark.asyncio
async def test_emit_event_graceful_on_redis_failure():
    """emit_governance_event logs warning on Redis failure, doesn't raise."""
    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(side_effect=Exception("Redis down"))

    emitter = GovernanceEventEmitter(mock_redis)
    # Should not raise
    await emitter.emit("ingestion.ticker.failed", "ingest_batch", {"ticker": "AAPL"})
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_governance_events.py -v`
Expected: FAIL — module not found

**Step 3: Implement governance event service**

Create `api/src/margin_api/services/governance_events.py`:

```python
"""Governance event emission to Redis stream."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

STREAM_KEY = "governance:events"


class GovernanceEventEmitter:
    """Emit governance events to a Redis stream."""

    def __init__(self, redis) -> None:
        self._redis = redis

    async def emit(
        self,
        event_type: str,
        source: str,
        detail: dict | None = None,
    ) -> str | None:
        """Write an event to the governance Redis stream.

        Returns the stream entry ID, or None on failure.
        """
        try:
            fields = {
                "event_type": event_type,
                "source": source,
                "detail": json.dumps(detail or {}),
                "created_at": datetime.now(UTC).isoformat(),
            }
            entry_id = await self._redis.xadd(STREAM_KEY, fields)
            return entry_id
        except Exception:
            logger.warning(
                "Failed to emit governance event %s from %s",
                event_type,
                source,
                exc_info=True,
            )
            return None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_governance_events.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/governance_events.py api/tests/test_governance_events.py
git commit -m "feat(api): add governance event emitter for Redis stream"
```

---

### Task 9: Add Expiry Daemon Worker

**Files:**
- Modify: `api/src/margin_api/workers.py`
- Test: `api/tests/test_expiry_daemon.py`

**Step 1: Write the failing test**

```python
"""Tests for approval expiry daemon."""

import pytest
import pytest_asyncio
from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import PipelineApproval


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_expire_stale_approvals(async_session: AsyncSession):
    """Expiry daemon transitions staged approvals past their expires_at."""
    from margin_api.workers import _expire_stale_approvals_impl

    # Expired approval
    expired = PipelineApproval(
        gate_type="score_publish",
        status="staged",
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    # Still valid approval
    valid = PipelineApproval(
        gate_type="ml_model_deploy",
        status="staged",
        expires_at=datetime.now(UTC) + timedelta(hours=23),
    )
    # Already approved (should not be touched)
    approved = PipelineApproval(
        gate_type="score_publish",
        status="approved",
        expires_at=datetime.now(UTC) - timedelta(hours=2),
    )
    async_session.add_all([expired, valid, approved])
    await async_session.commit()

    count = await _expire_stale_approvals_impl(async_session)
    assert count == 1

    result = (await async_session.execute(select(PipelineApproval))).scalars().all()
    statuses = {a.gate_type + ":" + str(a.id): a.status for a in result}

    assert expired.status == "expired"
    assert valid.status == "staged"
    assert approved.status == "approved"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_expiry_daemon.py -v`
Expected: FAIL

**Step 3: Implement expiry daemon**

Add to `api/src/margin_api/workers.py`:

```python
async def _expire_stale_approvals_impl(session: AsyncSession) -> int:
    """Transition staged approvals past their expires_at to expired."""
    from margin_api.db.models import PipelineApproval

    now = datetime.now(UTC)
    stale = (
        await session.execute(
            select(PipelineApproval)
            .where(PipelineApproval.status == "staged")
            .where(PipelineApproval.expires_at < now)
        )
    ).scalars().all()

    for approval in stale:
        approval.status = "expired"
        approval.decided_at = now

    if stale:
        await session.commit()

    return len(stale)


async def expire_stale_approvals(ctx: dict) -> dict:
    """Hourly cron: expire staged approvals past their deadline."""
    logger.info("[expiry] Checking for stale approvals...")
    engine = get_engine()
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        count = await _expire_stale_approvals_impl(session)

    logger.info("[expiry] Expired %d stale approvals", count)
    return {"status": "completed", "expired_count": count}
```

Register in `WorkerSettings.functions` and add to `cron_jobs`:

```python
cron(expire_stale_approvals, hour={0, 6, 12, 18}, run_at_startup=False),  # Every 6 hours
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_expiry_daemon.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_expiry_daemon.py
git commit -m "feat(api): add approval expiry daemon with 6-hour cron"
```

---

### Task 10: Filter Score Serving to Published-Only

**Files:**
- Modify: `api/src/margin_api/routes/scores.py`
- Modify: `api/tests/routes/` (existing score route tests)
- Test: `api/tests/test_published_score_filter.py`

**Step 1: Write the failing test**

```python
"""Tests for published-only score serving."""

import pytest
import pytest_asyncio
from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from httpx import ASGITransport, AsyncClient

from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.db.session import get_db


@pytest_asyncio.fixture
async def setup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        asset = Asset(ticker="AAPL", name="Apple Inc", sector="Technology")
        session.add(asset)
        await session.flush()

        # Published (old) score
        published = V4Score(
            asset_id=asset.id,
            scored_at=datetime(2026, 2, 26, tzinfo=UTC),
            opportunity_type="quality",
            conviction="medium",
            rules_conviction="medium",
            style="growth",
            timing_signal="neutral",
            regime="expansion",
            composite_score=55.0,
            published=True,
            detail={},
        )
        # Unpublished (new, staged) score
        unpublished = V4Score(
            asset_id=asset.id,
            scored_at=datetime(2026, 2, 27, tzinfo=UTC),
            opportunity_type="quality",
            conviction="high",
            rules_conviction="high",
            style="growth",
            timing_signal="neutral",
            regime="expansion",
            composite_score=82.0,
            published=False,
            detail={},
        )
        session.add_all([published, unpublished])
        await session.commit()

    yield engine, factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_score_returns_published_only(setup_db):
    """GET /scores/AAPL returns the published score, not the staged one."""
    engine, factory = setup_db

    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/scores/AAPL")

    assert response.status_code == 200
    data = response.json()
    # Should return the published score (55.0) not the unpublished one (82.0)
    assert data["composite_score"] == pytest.approx(55.0)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_published_score_filter.py -v`
Expected: FAIL — returns 82.0 (unpublished) instead of 55.0

**Step 3: Add `.where(V4Score.published == True)` to the score query**

In `api/src/margin_api/routes/scores.py` around line 483-497, modify the V4Score query:

```python
    v4_query = (
        select(
            V4Score,
            Asset.ticker,
            Asset.name.label("asset_name"),
            Asset.sector.label("asset_sector"),
            Asset.market_cap.label("asset_market_cap"),
        )
        .join(Asset, V4Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .where(V4Score.published == True)  # noqa: E712  — Only serve published scores
        .order_by(V4Score.scored_at.desc())
        .limit(1)
    )
```

Also search for any other V4Score queries in the scores routes that serve data to users (history endpoint, dashboard endpoint) and add the same filter.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_published_score_filter.py -v`
Expected: PASS

**Step 5: Run existing score tests to verify no regressions**

Run: `uv run pytest api/tests/routes/ -v --timeout=60`
Expected: All passing (some tests may need `published=True` added to their fixtures)

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/scores.py api/tests/test_published_score_filter.py
git commit -m "feat(api): filter score serving to published-only V4Scores"
```

---

### Task 11: Add Governance Event Rollup Worker

**Files:**
- Modify: `api/src/margin_api/workers.py`
- Test: `api/tests/test_governance_rollup.py`

**Step 1: Write the failing test**

```python
"""Tests for governance event rollup worker."""

import json
import pytest
import pytest_asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.db.base import Base
from margin_api.db.models import GovernanceEvent


@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_rollup_reads_redis_stream_and_inserts(async_session: AsyncSession):
    """Rollup reads events from Redis stream and inserts into DB."""
    from margin_api.workers import _rollup_governance_events_impl

    mock_redis = AsyncMock()
    mock_redis.xrange = AsyncMock(return_value=[
        (b"1234-0", {
            b"event_type": b"ingestion.ticker.success",
            b"source": b"ingest_batch",
            b"detail": json.dumps({"ticker": "AAPL"}).encode(),
            b"created_at": datetime.now(UTC).isoformat().encode(),
        }),
        (b"1235-0", {
            b"event_type": b"pricing.cache.stale",
            b"source": b"live_price_poll",
            b"detail": json.dumps({"ticker": "MSFT"}).encode(),
            b"created_at": datetime.now(UTC).isoformat().encode(),
        }),
    ])
    mock_redis.xtrim = AsyncMock()

    count = await _rollup_governance_events_impl(async_session, mock_redis)
    assert count == 2

    events = (await async_session.execute(select(GovernanceEvent))).scalars().all()
    assert len(events) == 2
    assert events[0].event_type == "ingestion.ticker.success"
    assert events[1].event_type == "pricing.cache.stale"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_governance_rollup.py -v`
Expected: FAIL

**Step 3: Implement rollup**

Add to `api/src/margin_api/workers.py`:

```python
async def _rollup_governance_events_impl(
    session: AsyncSession,
    redis,
) -> int:
    """Read governance events from Redis stream and insert into DB."""
    from margin_api.db.models import GovernanceEvent

    entries = await redis.xrange("governance:events")
    if not entries:
        return 0

    for entry_id, fields in entries:
        event_type = fields.get(b"event_type", b"").decode()
        source = fields.get(b"source", b"").decode()
        detail_raw = fields.get(b"detail", b"{}").decode()
        created_at_raw = fields.get(b"created_at", b"").decode()

        detail = json.loads(detail_raw) if detail_raw else {}
        created_at = datetime.fromisoformat(created_at_raw) if created_at_raw else datetime.now(UTC)

        event = GovernanceEvent(
            event_type=event_type,
            source=source,
            detail=detail,
            created_at=created_at,
        )
        session.add(event)

    await session.commit()

    # Trim stream, keeping last 24h worth (approximate via maxlen)
    await redis.xtrim("governance:events", maxlen=10000)

    return len(entries)


async def rollup_governance_events(ctx: dict) -> dict:
    """Periodic cron: roll up Redis governance events to DB."""
    import aioredis
    from margin_api.config import get_settings

    logger.info("[rollup] Rolling up governance events from Redis...")
    settings = get_settings()

    engine = get_engine()
    session_factory = get_session_factory(engine)

    redis = aioredis.from_url(settings.redis_url, decode_responses=False)
    try:
        async with session_factory() as session:
            count = await _rollup_governance_events_impl(session, redis)
    finally:
        await redis.aclose()

    logger.info("[rollup] Rolled up %d governance events to DB", count)
    return {"status": "completed", "events_count": count}
```

Register in `WorkerSettings.functions` and add cron:

```python
cron(rollup_governance_events, hour={3, 9, 15, 21}, run_at_startup=False),  # Every 6 hours, offset from expiry
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_governance_rollup.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_governance_rollup.py
git commit -m "feat(api): add governance event rollup from Redis stream to DB"
```

---

### Task 12: Add Admin Approval API Endpoints

**Files:**
- Create: `api/src/margin_api/routes/governance.py`
- Create: `api/src/margin_api/schemas/governance.py`
- Modify: `api/src/margin_api/app.py` (register router)
- Test: `api/tests/routes/test_governance.py`

**Step 1: Write the failing test**

```python
"""Tests for governance admin API endpoints."""

import os
import pytest
import pytest_asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import patch, AsyncMock
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.base import Base
from margin_api.db.models import PipelineApproval
from margin_api.db.session import get_db


@pytest_asyncio.fixture
async def setup():
    get_settings.cache_clear()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    # Seed test approvals
    async with factory() as session:
        staged = PipelineApproval(
            gate_type="score_publish",
            status="staged",
            pipeline_id="pipe-1",
            payload_ref={"scored_at": "2026-02-27T00:00:00Z", "ticker_count": 47},
            impact_summary={"conviction_changes": 3, "ticker_count": 47},
            submitted_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        approved = PipelineApproval(
            gate_type="ml_model_deploy",
            status="approved",
            decided_at=datetime.now(UTC),
        )
        session.add_all([staged, approved])
        await session.commit()

    yield engine, factory
    await engine.dispose()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_list_approvals(setup):
    """GET /admin/approvals returns list of approvals."""
    engine, factory = setup

    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
        app = create_app()

        async def override_get_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/admin/approvals",
                headers={"X-Admin-Key": "test-key"},
            )

    assert response.status_code == 200
    data = response.json()
    assert len(data["approvals"]) == 2


@pytest.mark.asyncio
async def test_list_approvals_filter_by_status(setup):
    """GET /admin/approvals?status=staged returns only staged."""
    engine, factory = setup

    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
        app = create_app()

        async def override_get_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/admin/approvals?status=staged",
                headers={"X-Admin-Key": "test-key"},
            )

    assert response.status_code == 200
    data = response.json()
    assert len(data["approvals"]) == 1
    assert data["approvals"][0]["status"] == "staged"


@pytest.mark.asyncio
async def test_approve_approval(setup):
    """POST /admin/approvals/1/approve transitions to approved."""
    engine, factory = setup

    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
        app = create_app()

        async def override_get_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db

        # Mock the publish_scores job enqueue
        with patch("margin_api.routes.governance._enqueue_publish_job", new_callable=AsyncMock):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/admin/approvals/1/approve",
                    headers={"X-Admin-Key": "test-key"},
                    json={"reason": "Looks good"},
                )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"


@pytest.mark.asyncio
async def test_reject_approval(setup):
    """POST /admin/approvals/1/reject transitions to rejected."""
    engine, factory = setup

    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
        app = create_app()

        async def override_get_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/admin/approvals/1/reject",
                headers={"X-Admin-Key": "test-key"},
                json={"reason": "Score drift too high"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"


@pytest.mark.asyncio
async def test_approve_requires_admin_key(setup):
    """Approval endpoints require admin key."""
    engine, factory = setup

    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
        app = create_app()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/admin/approvals/1/approve",
                headers={"X-Admin-Key": "wrong-key"},
                json={"reason": "test"},
            )

    assert response.status_code == 403
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/routes/test_governance.py -v`
Expected: FAIL

**Step 3: Create schemas**

Create `api/src/margin_api/schemas/governance.py`:

```python
"""Governance API schemas."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class ApprovalSummary(BaseModel):
    id: int
    gate_type: str
    status: str
    pipeline_id: str | None = None
    payload_ref: dict | None = None
    impact_summary: dict | None = None
    submitted_at: datetime | None = None
    decided_at: datetime | None = None
    decided_by: int | None = None
    decision_reason: str | None = None
    expires_at: datetime | None = None


class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalSummary]


class ApprovalDecisionRequest(BaseModel):
    reason: str | None = None


class GovernanceEventResponse(BaseModel):
    id: int
    event_type: str
    source: str
    detail: dict | None = None
    created_at: datetime | None = None


class GovernanceEventListResponse(BaseModel):
    events: list[GovernanceEventResponse]
    total: int


class GovernanceDashboardResponse(BaseModel):
    pending_count: int
    avg_approval_latency_hours: float | None = None
    rejection_rate: float | None = None
    recent_anomalies: list[dict] = []


class TransparencyResponse(BaseModel):
    oversight_levels: dict
    last_approvals: dict
    pipeline_health: dict
```

**Step 4: Create routes**

Create `api/src/margin_api/routes/governance.py`:

```python
"""Governance admin API endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.models import GovernanceEvent, PipelineApproval
from margin_api.db.session import get_db
from margin_api.middleware.rate_limit import limiter
from margin_api.routes.admin import _verify_admin_key
from margin_api.schemas.governance import (
    ApprovalDecisionRequest,
    ApprovalListResponse,
    ApprovalSummary,
    GovernanceDashboardResponse,
    GovernanceEventListResponse,
    GovernanceEventResponse,
    TransparencyResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["governance"])


@router.get("/approvals", response_model=ApprovalListResponse)
@limiter.limit("30/minute")
async def list_approvals(
    request: Request,
    x_admin_key: str = Header(),
    status: str | None = Query(None),
    gate_type: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> ApprovalListResponse:
    """List pipeline approvals, optionally filtered."""
    _verify_admin_key(x_admin_key)

    query = select(PipelineApproval).order_by(PipelineApproval.submitted_at.desc())
    if status:
        query = query.where(PipelineApproval.status == status)
    if gate_type:
        query = query.where(PipelineApproval.gate_type == gate_type)

    result = await session.execute(query)
    rows = result.scalars().all()

    return ApprovalListResponse(
        approvals=[
            ApprovalSummary(
                id=r.id,
                gate_type=r.gate_type,
                status=r.status,
                pipeline_id=r.pipeline_id,
                payload_ref=r.payload_ref,
                impact_summary=r.impact_summary,
                submitted_at=r.submitted_at,
                decided_at=r.decided_at,
                decided_by=r.decided_by,
                decision_reason=r.decision_reason,
                expires_at=r.expires_at,
            )
            for r in rows
        ]
    )


@router.get("/approvals/{approval_id}", response_model=ApprovalSummary)
@limiter.limit("30/minute")
async def get_approval(
    request: Request,
    approval_id: int,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> ApprovalSummary:
    """Get a single approval by ID."""
    _verify_admin_key(x_admin_key)

    result = await session.execute(
        select(PipelineApproval).where(PipelineApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(404, f"Approval {approval_id} not found")

    return ApprovalSummary(
        id=approval.id,
        gate_type=approval.gate_type,
        status=approval.status,
        pipeline_id=approval.pipeline_id,
        payload_ref=approval.payload_ref,
        impact_summary=approval.impact_summary,
        submitted_at=approval.submitted_at,
        decided_at=approval.decided_at,
        decided_by=approval.decided_by,
        decision_reason=approval.decision_reason,
        expires_at=approval.expires_at,
    )


@router.post("/approvals/{approval_id}/approve")
@limiter.limit("10/minute")
async def approve_approval(
    request: Request,
    approval_id: int,
    body: ApprovalDecisionRequest,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Approve a staged pipeline approval."""
    _verify_admin_key(x_admin_key)

    result = await session.execute(
        select(PipelineApproval).where(PipelineApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(404, f"Approval {approval_id} not found")
    if approval.status != "staged":
        raise HTTPException(409, f"Approval {approval_id} is {approval.status}, not staged")

    approval.status = "approved"
    approval.decided_at = datetime.now(UTC)
    approval.decision_reason = body.reason
    await session.commit()

    # Trigger the appropriate publish job
    await _enqueue_publish_job(approval)

    return {"status": "approved", "approval_id": approval_id}


@router.post("/approvals/{approval_id}/reject")
@limiter.limit("10/minute")
async def reject_approval(
    request: Request,
    approval_id: int,
    body: ApprovalDecisionRequest,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Reject a staged pipeline approval."""
    _verify_admin_key(x_admin_key)

    result = await session.execute(
        select(PipelineApproval).where(PipelineApproval.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(404, f"Approval {approval_id} not found")
    if approval.status != "staged":
        raise HTTPException(409, f"Approval {approval_id} is {approval.status}, not staged")

    approval.status = "rejected"
    approval.decided_at = datetime.now(UTC)
    approval.decision_reason = body.reason
    await session.commit()

    return {"status": "rejected", "approval_id": approval_id}


async def _enqueue_publish_job(approval: PipelineApproval) -> None:
    """Enqueue the appropriate publish/promote job for an approved approval."""
    settings = get_settings()
    try:
        redis: ArqRedis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        if approval.gate_type == "score_publish":
            await redis.enqueue_job(
                "publish_scores",
                approval.id,
                _job_id=f"publish_scores:{uuid.uuid4().hex[:8]}",
            )
        elif approval.gate_type == "ml_model_deploy":
            await redis.enqueue_job(
                "promote_ml_model",
                approval.id,
                _job_id=f"promote_ml:{uuid.uuid4().hex[:8]}",
            )
        await redis.aclose()
    except Exception:
        logger.warning("Failed to enqueue publish job for approval %d", approval.id, exc_info=True)
```

Register in `api/src/margin_api/app.py`:

```python
from margin_api.routes.governance import router as governance_router
# ...
app.include_router(governance_router)
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest api/tests/routes/test_governance.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/governance.py api/src/margin_api/schemas/governance.py api/src/margin_api/app.py api/tests/routes/test_governance.py
git commit -m "feat(api): add admin approval API endpoints for governance"
```

---

### Task 13: Add Governance Dashboard and Events API

**Files:**
- Modify: `api/src/margin_api/routes/governance.py`
- Modify: `api/tests/routes/test_governance.py`

**Step 1: Write the failing test**

Add to `api/tests/routes/test_governance.py`:

```python
@pytest.mark.asyncio
async def test_governance_dashboard(setup):
    """GET /admin/governance/dashboard returns aggregate stats."""
    engine, factory = setup

    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
        app = create_app()

        async def override_get_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/admin/governance/dashboard",
                headers={"X-Admin-Key": "test-key"},
            )

    assert response.status_code == 200
    data = response.json()
    assert "pending_count" in data
    assert data["pending_count"] == 1  # One staged approval in fixture


@pytest.mark.asyncio
async def test_governance_events(setup):
    """GET /admin/governance/events returns event log."""
    engine, factory = setup

    # Seed a governance event
    async with factory() as session:
        from margin_api.db.models import GovernanceEvent
        event = GovernanceEvent(
            event_type="ingestion.ticker.success",
            source="ingest_batch",
            detail={"ticker": "AAPL"},
        )
        session.add(event)
        await session.commit()

    with patch.dict(os.environ, {"MARGIN_ADMIN_KEY": "test-key"}):
        app = create_app()

        async def override_get_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/admin/governance/events",
                headers={"X-Admin-Key": "test-key"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/routes/test_governance.py::test_governance_dashboard -v`
Expected: FAIL — endpoint not found

**Step 3: Add dashboard and events endpoints**

Add to `api/src/margin_api/routes/governance.py`:

```python
@router.get("/governance/dashboard", response_model=GovernanceDashboardResponse)
@limiter.limit("30/minute")
async def governance_dashboard(
    request: Request,
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> GovernanceDashboardResponse:
    """Aggregated governance stats."""
    _verify_admin_key(x_admin_key)

    # Pending count
    pending = await session.execute(
        select(func.count(PipelineApproval.id)).where(PipelineApproval.status == "staged")
    )
    pending_count = pending.scalar() or 0

    # Avg approval latency (for completed approvals in last 30 days)
    from datetime import timedelta
    cutoff = datetime.now(UTC) - timedelta(days=30)
    approved = (
        await session.execute(
            select(PipelineApproval)
            .where(PipelineApproval.status == "approved")
            .where(PipelineApproval.decided_at >= cutoff)
        )
    ).scalars().all()

    avg_latency = None
    if approved:
        latencies = [
            (a.decided_at - a.submitted_at).total_seconds() / 3600
            for a in approved
            if a.decided_at and a.submitted_at
        ]
        avg_latency = sum(latencies) / len(latencies) if latencies else None

    # Rejection rate
    total_decided = (
        await session.execute(
            select(func.count(PipelineApproval.id)).where(
                PipelineApproval.status.in_(["approved", "rejected"])
            )
        )
    ).scalar() or 0

    rejected_count = (
        await session.execute(
            select(func.count(PipelineApproval.id)).where(PipelineApproval.status == "rejected")
        )
    ).scalar() or 0

    rejection_rate = rejected_count / total_decided if total_decided > 0 else None

    return GovernanceDashboardResponse(
        pending_count=pending_count,
        avg_approval_latency_hours=avg_latency,
        rejection_rate=rejection_rate,
    )


@router.get("/governance/events", response_model=GovernanceEventListResponse)
@limiter.limit("30/minute")
async def list_governance_events(
    request: Request,
    x_admin_key: str = Header(),
    event_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    session: AsyncSession = Depends(get_db),
) -> GovernanceEventListResponse:
    """Query governance event log."""
    _verify_admin_key(x_admin_key)

    query = select(GovernanceEvent).order_by(GovernanceEvent.created_at.desc())
    count_query = select(func.count(GovernanceEvent.id))

    if event_type:
        query = query.where(GovernanceEvent.event_type.like(f"{event_type}%"))
        count_query = count_query.where(GovernanceEvent.event_type.like(f"{event_type}%"))

    total = (await session.execute(count_query)).scalar() or 0
    result = await session.execute(query.offset(offset).limit(limit))
    rows = result.scalars().all()

    return GovernanceEventListResponse(
        events=[
            GovernanceEventResponse(
                id=e.id,
                event_type=e.event_type,
                source=e.source,
                detail=e.detail,
                created_at=e.created_at,
            )
            for e in rows
        ],
        total=total,
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/routes/test_governance.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/governance.py api/tests/routes/test_governance.py
git commit -m "feat(api): add governance dashboard and event log API endpoints"
```

---

### Task 14: Add Public Transparency Endpoint

**Files:**
- Create: `api/src/margin_api/routes/transparency.py`
- Modify: `api/src/margin_api/app.py`
- Test: `api/tests/routes/test_transparency.py`

**Step 1: Write the failing test**

```python
"""Tests for public transparency endpoint."""

import pytest
import pytest_asyncio
from datetime import UTC, datetime
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import PipelineApproval
from margin_api.db.session import get_db


@pytest_asyncio.fixture
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield engine, factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_transparency_returns_oversight_levels(setup):
    """GET /governance/transparency returns component classification."""
    engine, factory = setup
    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/governance/transparency")

    assert response.status_code == 200
    data = response.json()
    assert "oversight_levels" in data
    assert "in_the_loop" in data["oversight_levels"]
    assert "score_publication" in data["oversight_levels"]["in_the_loop"]
    assert "pipeline_health" in data
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/routes/test_transparency.py -v`
Expected: FAIL

**Step 3: Implement transparency endpoint**

Create `api/src/margin_api/routes/transparency.py`:

```python
"""Public governance transparency endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import IngestionRun, PipelineApproval
from margin_api.db.session import get_db
from margin_api.middleware.rate_limit import limiter
from margin_api.schemas.governance import TransparencyResponse

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])

OVERSIGHT_LEVELS = {
    "in_the_loop": [
        "score_publication",
        "ml_model_deployment",
        "universe_activation",
        "filter_config",
    ],
    "on_the_loop": [
        "daily_scoring_pipeline",
        "13f_ingest",
        "backtest_replay",
    ],
    "out_of_the_loop": [
        "data_ingestion",
        "live_pricing",
        "data_quality",
        "accumulation_signals",
    ],
}


@router.get("/transparency", response_model=TransparencyResponse)
@limiter.limit("60/minute")
async def transparency(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TransparencyResponse:
    """Public transparency: oversight classification and pipeline health."""
    # Last approvals by gate type
    last_approvals = {}
    for gate_type in ["score_publish", "ml_model_deploy", "universe_activate"]:
        result = await session.execute(
            select(PipelineApproval)
            .where(PipelineApproval.gate_type == gate_type)
            .where(PipelineApproval.status.in_(["approved", "rejected"]))
            .order_by(PipelineApproval.decided_at.desc())
            .limit(1)
        )
        approval = result.scalar_one_or_none()
        if approval:
            last_approvals[gate_type] = {
                "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
                "status": approval.status,
            }

    # Pipeline health from latest IngestionRun
    latest_run = (
        await session.execute(
            select(IngestionRun)
            .where(IngestionRun.status == "completed")
            .order_by(IngestionRun.completed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    pipeline_health = {
        "status": "idle",
        "last_successful_run": latest_run.completed_at.isoformat() if latest_run else None,
    }

    return TransparencyResponse(
        oversight_levels=OVERSIGHT_LEVELS,
        last_approvals=last_approvals,
        pipeline_health=pipeline_health,
    )
```

Register in `app.py`:

```python
from margin_api.routes.transparency import router as transparency_router
# ...
app.include_router(transparency_router)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/routes/test_transparency.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/transparency.py api/src/margin_api/app.py api/tests/routes/test_transparency.py
git commit -m "feat(api): add public governance transparency endpoint"
```

---

### Task 15: Build Operator Approval Queue UI

**Files:**
- Create: `web/src/app/admin/approvals/page.tsx`
- Create: `web/src/app/admin/layout.tsx`
- Create: `web/src/components/admin/approval-card.tsx`
- Create: `web/src/lib/api/governance.ts`
- Test: `web/src/components/admin/__tests__/approval-card.test.tsx`

**Step 1: Write the failing test**

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { ApprovalCard } from "../approval-card"

const mockApproval = {
  id: 1,
  gate_type: "score_publish",
  status: "staged",
  pipeline_id: "pipe-123",
  payload_ref: { scored_at: "2026-02-27T00:00:00Z", ticker_count: 47 },
  impact_summary: { conviction_changes: 3, ticker_count: 47 },
  submitted_at: "2026-02-27T12:00:00Z",
  expires_at: "2026-02-28T12:00:00Z",
  decided_at: null,
  decided_by: null,
  decision_reason: null,
}

describe("ApprovalCard", () => {
  it("renders gate type badge", () => {
    render(<ApprovalCard approval={mockApproval} onApprove={vi.fn()} onReject={vi.fn()} />)
    expect(screen.getByText("score_publish")).toBeInTheDocument()
  })

  it("shows impact summary", () => {
    render(<ApprovalCard approval={mockApproval} onApprove={vi.fn()} onReject={vi.fn()} />)
    expect(screen.getByText(/47 tickers/)).toBeInTheDocument()
    expect(screen.getByText(/3 conviction changes/)).toBeInTheDocument()
  })

  it("shows approve and reject buttons for staged approvals", () => {
    render(<ApprovalCard approval={mockApproval} onApprove={vi.fn()} onReject={vi.fn()} />)
    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument()
  })

  it("calls onApprove when approve button clicked", () => {
    const onApprove = vi.fn()
    render(<ApprovalCard approval={mockApproval} onApprove={onApprove} onReject={vi.fn()} />)
    fireEvent.click(screen.getByRole("button", { name: /approve/i }))
    onApprove.toHaveBeenCalledWith(1)
  })

  it("hides action buttons for non-staged approvals", () => {
    const decided = { ...mockApproval, status: "approved" }
    render(<ApprovalCard approval={decided} onApprove={vi.fn()} onReject={vi.fn()} />)
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/admin/__tests__/approval-card.test.tsx`
Expected: FAIL

**Step 3: Create the API client**

Create `web/src/lib/api/governance.ts`:

```typescript
import { apiFetch } from "./client"

export interface Approval {
  id: number
  gate_type: string
  status: string
  pipeline_id: string | null
  payload_ref: Record<string, unknown> | null
  impact_summary: Record<string, unknown> | null
  submitted_at: string | null
  decided_at: string | null
  decided_by: number | null
  decision_reason: string | null
  expires_at: string | null
}

export interface ApprovalListResponse {
  approvals: Approval[]
}

export async function getApprovals(
  adminKey: string,
  status?: string,
): Promise<ApprovalListResponse> {
  const params = status ? `?status=${status}` : ""
  return apiFetch<ApprovalListResponse>(`/api/v1/admin/approvals${params}`, {
    headers: { "X-Admin-Key": adminKey },
  })
}

export async function approveApproval(
  adminKey: string,
  id: number,
  reason?: string,
): Promise<{ status: string }> {
  return apiFetch(`/api/v1/admin/approvals/${id}/approve`, {
    method: "POST",
    headers: { "X-Admin-Key": adminKey },
    body: JSON.stringify({ reason }),
  })
}

export async function rejectApproval(
  adminKey: string,
  id: number,
  reason?: string,
): Promise<{ status: string }> {
  return apiFetch(`/api/v1/admin/approvals/${id}/reject`, {
    method: "POST",
    headers: { "X-Admin-Key": adminKey },
    body: JSON.stringify({ reason }),
  })
}
```

**Step 4: Create ApprovalCard component**

Create `web/src/components/admin/approval-card.tsx`:

```tsx
"use client"

import type { Approval } from "@/lib/api/governance"

const GATE_LABELS: Record<string, string> = {
  score_publish: "Score Publication",
  ml_model_deploy: "ML Model Deploy",
  universe_activate: "Universe Activation",
  filter_config_change: "Filter Config",
}

interface ApprovalCardProps {
  approval: Approval
  onApprove: (id: number) => void
  onReject: (id: number) => void
}

export function ApprovalCard({ approval, onApprove, onReject }: ApprovalCardProps) {
  const isStaged = approval.status === "staged"
  const impact = approval.impact_summary || {}
  const payload = approval.payload_ref || {}

  const timeRemaining = approval.expires_at
    ? Math.max(0, Math.floor((new Date(approval.expires_at).getTime() - Date.now()) / 3600000))
    : null

  return (
    <div className="terminal-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono uppercase tracking-wider text-accent">
          {approval.gate_type}
        </span>
        <span className={`text-xs font-mono px-2 py-0.5 rounded ${
          isStaged ? "bg-warning/10 text-warning" :
          approval.status === "approved" ? "bg-bullish/10 text-bullish" :
          "bg-bearish/10 text-bearish"
        }`}>
          {approval.status}
        </span>
      </div>

      <div className="text-sm text-text-secondary space-y-1">
        {impact.ticker_count != null && (
          <p>{impact.ticker_count as number} tickers scored</p>
        )}
        {(impact.conviction_changes as number) > 0 && (
          <p>{impact.conviction_changes as number} conviction changes</p>
        )}
        {impact.rank_ic != null && (
          <p>Rank IC: {(impact.rank_ic as number).toFixed(3)}</p>
        )}
        {(impact.added_tickers as string[])?.length > 0 && (
          <p>+{(impact.added_tickers as string[]).length} tickers added</p>
        )}
        {(impact.removed_tickers as string[])?.length > 0 && (
          <p>-{(impact.removed_tickers as string[]).length} tickers removed</p>
        )}
      </div>

      {timeRemaining !== null && isStaged && (
        <p className="text-xs text-text-secondary">
          {timeRemaining}h remaining before expiry
        </p>
      )}

      {approval.decision_reason && (
        <p className="text-xs text-text-secondary italic">
          &ldquo;{approval.decision_reason}&rdquo;
        </p>
      )}

      {isStaged && (
        <div className="flex gap-2 pt-2">
          <button
            onClick={() => onApprove(approval.id)}
            className="px-3 py-1.5 text-xs font-medium bg-bullish/10 text-bullish border border-bullish/20 rounded hover:bg-bullish/20 transition-colors"
          >
            Approve
          </button>
          <button
            onClick={() => onReject(approval.id)}
            className="px-3 py-1.5 text-xs font-medium bg-bearish/10 text-bearish border border-bearish/20 rounded hover:bg-bearish/20 transition-colors"
          >
            Reject
          </button>
        </div>
      )}
    </div>
  )
}
```

**Step 5: Create admin layout and approvals page**

Create `web/src/app/admin/layout.tsx`:

```tsx
import { AppShell } from "@/components/layout"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>
}
```

Create `web/src/app/admin/approvals/page.tsx`:

```tsx
"use client"

import { useEffect, useState } from "react"
import { ApprovalCard } from "@/components/admin/approval-card"
import { getApprovals, approveApproval, rejectApproval, type Approval } from "@/lib/api/governance"

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [filter, setFilter] = useState<string>("staged")
  const [loading, setLoading] = useState(true)
  const adminKey = process.env.NEXT_PUBLIC_ADMIN_KEY || ""

  useEffect(() => {
    setLoading(true)
    getApprovals(adminKey, filter || undefined)
      .then((data) => setApprovals(data.approvals))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filter, adminKey])

  const handleApprove = async (id: number) => {
    const reason = window.prompt("Approval reason (optional):")
    await approveApproval(adminKey, id, reason || undefined)
    setApprovals((prev) => prev.map((a) => (a.id === id ? { ...a, status: "approved" } : a)))
  }

  const handleReject = async (id: number) => {
    const reason = window.prompt("Rejection reason:")
    if (!reason) return
    await rejectApproval(adminKey, id, reason)
    setApprovals((prev) => prev.map((a) => (a.id === id ? { ...a, status: "rejected" } : a)))
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <h1 className="text-2xl font-display text-text-primary">Approval Queue</h1>

      <div className="flex gap-2">
        {["staged", "approved", "rejected", "expired", ""].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1 text-xs font-mono rounded border ${
              filter === s
                ? "border-accent text-accent"
                : "border-border-primary text-text-secondary hover:text-text-primary"
            }`}
          >
            {s || "all"}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-text-secondary text-sm">Loading...</p>
      ) : approvals.length === 0 ? (
        <p className="text-text-secondary text-sm">No approvals found.</p>
      ) : (
        <div className="space-y-4">
          {approvals.map((a) => (
            <ApprovalCard
              key={a.id}
              approval={a}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          ))}
        </div>
      )}
    </div>
  )
}
```

**Step 6: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/admin/__tests__/approval-card.test.tsx`
Expected: PASS

**Step 7: Commit**

```bash
git add web/src/app/admin/ web/src/components/admin/ web/src/lib/api/governance.ts
git commit -m "feat(web): add operator approval queue UI at /admin/approvals"
```

---

### Task 16: Build Pipeline Monitor UI

**Files:**
- Create: `web/src/app/admin/approvals/monitor.tsx`
- Create: `web/src/components/admin/pipeline-status.tsx`
- Test: `web/src/components/admin/__tests__/pipeline-status.test.tsx`

This task adds a pipeline health section to the admin approvals page. The component fetches from `GET /admin/governance/dashboard` and displays: pending count, avg approval latency, rejection rate, and pipeline status.

Follow the same TDD pattern: write test → verify fail → implement component → verify pass → commit.

```bash
git commit -m "feat(web): add pipeline monitor section to admin dashboard"
```

---

### Task 17: Build Event Log UI

**Files:**
- Create: `web/src/app/admin/events/page.tsx`
- Create: `web/src/components/admin/event-table.tsx`
- Test: `web/src/components/admin/__tests__/event-table.test.tsx`

This task adds a paginated, filterable event log page at `/admin/events`. The EventTable component fetches from `GET /admin/governance/events` with event_type filter and offset/limit pagination. Each row shows: event_type, source, detail summary, created_at.

Follow the same TDD pattern: write test → verify fail → implement component → verify pass → commit.

```bash
git commit -m "feat(web): add governance event log UI at /admin/events"
```

---

### Task 18: Add User Proposals API

**Files:**
- Create: `api/src/margin_api/routes/proposals.py`
- Create: `api/src/margin_api/schemas/proposals.py`
- Modify: `api/src/margin_api/app.py`
- Test: `api/tests/routes/test_proposals.py`

Endpoints:
- `GET /api/v1/proposals` — list user's proposals (JWT auth, filter by user_id from token)
- `POST /api/v1/proposals/{id}/accept` — accept a proposal
- `POST /api/v1/proposals/{id}/dismiss` — dismiss a proposal

Follow the same TDD pattern as Task 12. Use the existing JWT auth pattern from other user-facing routes.

```bash
git commit -m "feat(api): add user proposals API endpoints"
```

---

### Task 19: Add User Proposal UI

**Files:**
- Create: `web/src/components/dashboard/proposal-banner.tsx`
- Modify: `web/src/app/dashboard/page.tsx` (add ProposalBanner)
- Test: `web/src/components/dashboard/__tests__/proposal-banner.test.tsx`

The ProposalBanner is a dismissible card shown on the dashboard when proposals are pending. It shows: proposal type badge, ticker, rationale text, Accept/Dismiss buttons.

Follow the same TDD pattern: write test → verify fail → implement component → wire into dashboard → verify pass → commit.

```bash
git commit -m "feat(web): add user proposal banner on dashboard"
```

---

## Final Verification

After all tasks are complete:

1. Run full test suites:
   ```bash
   uv run pytest api/tests/ -v
   uv run pytest engine/tests/ -v
   cd web && npx vitest run
   ```

2. Verify no regressions in existing functionality:
   - Score serving still works (returns published scores)
   - Dashboard loads
   - Admin endpoints still require HMAC auth

3. Manual smoke test:
   - Trigger scoring pipeline via `/admin/pipeline/trigger`
   - Verify scores are staged (not immediately visible)
   - Approve via `/admin/approvals/{id}/approve`
   - Verify scores now visible
