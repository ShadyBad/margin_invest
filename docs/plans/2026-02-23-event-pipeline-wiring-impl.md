# Event Pipeline Wiring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the three existing event system layers (engine models, API routes, WebSocket) end-to-end so scoring results flow to users in real time.

**Architecture:** After V4 scoring completes, compare new scores against previous scores. For deltas exceeding 5 pts, create score_change events via the engine's ImpactClassifier, persist to DB, and broadcast to WebSocket clients. The frontend subscribes via a React hook and displays notification toasts.

**Tech Stack:** SQLAlchemy 2.0 (async), Alembic, FastAPI WebSocket, React hooks, existing engine event models.

---

### Task 1: Add Event and Notification DB Models

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Test: `api/tests/test_event_models_db.py`

**Step 1: Write the failing test**

```python
"""Tests for Event and Notification DB models."""

import pytest
from datetime import UTC, datetime
from sqlalchemy import select

from margin_api.db.models import Event, Notification


@pytest.mark.asyncio
async def test_event_roundtrip(async_session):
    """Event can be inserted and retrieved."""
    event = Event(
        event_id="evt-001",
        event_type="score_change",
        ticker="AAPL",
        severity="major",
        source="scoring_pipeline",
        payload={"old_score": 70.0, "new_score": 85.0, "delta": 15.0},
        timestamp=datetime.now(UTC),
    )
    async_session.add(event)
    await async_session.commit()

    result = await async_session.execute(select(Event).where(Event.event_id == "evt-001"))
    row = result.scalar_one()
    assert row.ticker == "AAPL"
    assert row.severity == "major"
    assert row.payload["delta"] == 15.0


@pytest.mark.asyncio
async def test_notification_links_event(async_session):
    """Notification references its parent event."""
    event = Event(
        event_id="evt-002",
        event_type="score_change",
        ticker="MSFT",
        severity="moderate",
        source="scoring_pipeline",
        payload={},
        timestamp=datetime.now(UTC),
    )
    async_session.add(event)
    await async_session.flush()

    notif = Notification(
        notification_id="ntf-001",
        event_id=event.id,
        read=False,
    )
    async_session.add(notif)
    await async_session.commit()

    result = await async_session.execute(
        select(Notification).where(Notification.notification_id == "ntf-001")
    )
    row = result.scalar_one()
    assert row.read is False
    assert row.event.ticker == "MSFT"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_event_models_db.py -v`
Expected: FAIL — `ImportError: cannot import name 'Event' from 'margin_api.db.models'`

**Step 3: Write minimal implementation**

Add to `api/src/margin_api/db/models.py` after the `ApiKeyEvent` class:

```python
class Event(Base):
    """Persisted event (score changes, earnings, etc.)."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(30))
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    severity: Mapped[str] = mapped_column(String(10))
    source: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    notifications: Mapped[list[Notification]] = relationship(back_populates="event")

    __table_args__ = (Index("ix_events_ticker_timestamp", "ticker", "timestamp"),)


class Notification(Base):
    """User-facing notification derived from an event."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    notification_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    event: Mapped[Event] = relationship(back_populates="notifications")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_event_models_db.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_event_models_db.py
git commit -m "feat(db): add Event and Notification tables"
```

---

### Task 2: Alembic Migration for Events Tables

**Files:**
- Create: `api/alembic/versions/<auto>_add_events_and_notifications_tables.py`

**Step 1: Generate migration**

```bash
cd api && uv run alembic revision --autogenerate -m "add events and notifications tables"
```

**Step 2: Review generated migration**

Verify it creates `events` and `notifications` tables with correct columns, indexes, and foreign key from `notifications.event_id` → `events.id`.

**Step 3: Test migration applies cleanly**

Run against a test database or verify via the test suite:

```bash
uv run pytest api/tests/test_event_models_db.py -v
```

Expected: PASS (SQLite auto-creates tables in test fixtures)

**Step 4: Commit**

```bash
git add api/alembic/versions/
git commit -m "feat(db): add migration for events and notifications tables"
```

---

### Task 3: Replace In-Memory Event Store with DB Operations

**Files:**
- Modify: `api/src/margin_api/routes/events.py`
- Modify: `api/tests/test_events.py`
- Modify: `api/tests/test_events_integration.py`

**Step 1: Update the events route to use DB**

Replace the in-memory `_event_store` and `_notification_store` dicts with async DB operations. The `add_event()` and `add_notification()` functions become async and accept a `session` parameter. Route handlers use `Depends(get_db)` for their session.

Key changes:
- `add_event()` → `async def add_event(session, ...)` — creates `Event` ORM object, commits, returns `EventResponse`
- `add_notification()` → `async def add_notification(session, event_db)` — creates `Notification` ORM object
- `create_event` route → injects `session: AsyncSession = Depends(get_db)`, calls `add_event(session, ...)`
- `list_events` route → queries `Event` table filtered by ticker, ordered by timestamp desc
- `list_recent_events` route → queries `Event` table with timestamp >= cutoff
- `list_notifications` route → queries `Notification` table joined with `Event`, ordered by created_at desc
- `mark_notification_read` route → updates `Notification.read = True` by notification_id
- `delete_notification` route → deletes `Notification` by notification_id

**Step 2: Update tests to use async DB session fixture**

The existing test files (`test_events.py`, `test_events_integration.py`) use `httpx.AsyncClient` with the app. Since the routes now depend on `get_db`, tests need the async DB fixture (same pattern as other API tests).

**Step 3: Run tests to verify they pass**

```bash
uv run pytest api/tests/test_events.py api/tests/test_events_integration.py -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add api/src/margin_api/routes/events.py api/tests/test_events.py api/tests/test_events_integration.py
git commit -m "feat(events): replace in-memory store with DB persistence"
```

---

### Task 4: Integrate ImpactClassifier into Event Creation

**Files:**
- Modify: `api/src/margin_api/routes/events.py`
- Test: `api/tests/test_events_integration.py`

**Step 1: Write the failing test**

Add to `test_events_integration.py`:

```python
@pytest.mark.asyncio
async def test_score_change_event_auto_classified(client):
    """Score change events get severity auto-classified by ImpactClassifier."""
    resp = await client.post("/api/v1/events", json={
        "event_type": "score_change",
        "ticker": "AAPL",
        "severity": "minor",  # will be overridden
        "source": "test",
        "payload": {"delta": 15.0},
    })
    assert resp.status_code == 201
    data = resp.json()
    # delta > 10 → MAJOR per ImpactClassifier rules
    assert data["severity"] == "major"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_events_integration.py::test_score_change_event_auto_classified -v`
Expected: FAIL — severity is "minor" (passed through unchanged)

**Step 3: Implement**

In `add_event()`, after creating the `EventRecord`, run it through `ImpactClassifier().classify()` to determine the real severity, then use that as the stored severity:

```python
from margin_engine.events.models import EventRecord, EventType, EventSeverity
from margin_engine.events.pipeline import ImpactClassifier

_classifier = ImpactClassifier()

async def add_event(session, event_type, ticker, severity, source, payload=None, ...):
    # Build engine EventRecord to classify
    engine_event = EventRecord(
        event_type=event_type,
        ticker=ticker,
        timestamp=timestamp or datetime.now(UTC),
        severity=severity,  # initial, will be overridden for score_change
        source=source,
        payload=payload or {},
    )
    classified_severity = _classifier.classify(engine_event)

    event = Event(
        event_id=event_id or str(uuid4()),
        event_type=event_type,
        ticker=ticker.upper(),
        timestamp=timestamp or datetime.now(UTC),
        severity=classified_severity.value,
        source=source,
        payload=payload or {},
    )
    session.add(event)
    await session.flush()
    return event
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_events_integration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/events.py api/tests/test_events_integration.py
git commit -m "feat(events): auto-classify severity via ImpactClassifier"
```

---

### Task 5: Wire Score Change Events from V4 Scoring Worker

**Files:**
- Modify: `api/src/margin_api/workers.py`
- Test: `api/tests/test_score_change_events.py`

**Step 1: Write the failing test**

```python
"""Test that score changes create events after V4 scoring."""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select

from margin_api.db.models import Event, Score, Asset


@pytest.mark.asyncio
async def test_emit_score_change_events(async_session):
    """Score changes > 5 pts delta should create score_change events."""
    from margin_api.workers import _emit_score_change_events

    # Setup: create asset with old score
    asset = Asset(
        ticker="AAPL", name="Apple", sector="Technology", market_cap=3000000000000
    )
    async_session.add(asset)
    await async_session.flush()

    old_score = Score(
        asset_id=asset.id,
        composite_percentile=70.0,
        composite_raw_score=70.0,
        conviction_level="high",
        signal="BUY",
        scored_at=datetime(2026, 2, 22, tzinfo=UTC),
    )
    new_score = Score(
        asset_id=asset.id,
        composite_percentile=85.0,
        composite_raw_score=85.0,
        conviction_level="exceptional",
        signal="BUY",
        scored_at=datetime(2026, 2, 23, tzinfo=UTC),
    )
    async_session.add_all([old_score, new_score])
    await async_session.commit()

    count = await _emit_score_change_events(async_session)
    assert count >= 1

    result = await async_session.execute(
        select(Event).where(Event.ticker == "AAPL", Event.event_type == "score_change")
    )
    event = result.scalar_one()
    assert event.payload["delta"] == 15.0
    assert event.payload["old_score"] == 70.0
    assert event.payload["new_score"] == 85.0
    assert event.severity == "major"  # delta > 10
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_score_change_events.py -v`
Expected: FAIL — `ImportError: cannot import name '_emit_score_change_events'`

**Step 3: Implement `_emit_score_change_events` in workers.py**

Add a helper function that:
1. Queries the two most recent scores per asset (today vs previous)
2. Computes delta = new_composite - old_composite
3. If `abs(delta) > 5.0`, creates a score_change event via the DB `Event` model
4. Runs `ImpactClassifier` to set severity
5. Returns the count of events created

```python
from margin_engine.events.pipeline import ImpactClassifier
from margin_engine.events.models import EventRecord, EventType as EngineEventType

_classifier = ImpactClassifier()

async def _emit_score_change_events(session: AsyncSession) -> int:
    """Compare latest scores to previous scores and emit events for significant changes."""
    from margin_api.db.models import Asset, Event, Notification, Score
    from sqlalchemy import func
    from uuid import uuid4

    # Get the most recent scored_at per asset
    latest_subq = (
        select(Score.asset_id, func.max(Score.scored_at).label("max_scored"))
        .group_by(Score.asset_id)
        .subquery()
    )

    # Get new scores (most recent)
    new_scores_result = await session.execute(
        select(Score, Asset.ticker)
        .join(Asset, Score.asset_id == Asset.id)
        .join(latest_subq, (Score.asset_id == latest_subq.c.asset_id) & (Score.scored_at == latest_subq.c.max_scored))
    )
    new_scores = {row.ticker: row.Score for row in new_scores_result}

    # Get previous scores (second most recent)
    prev_subq = (
        select(Score.asset_id, func.max(Score.scored_at).label("prev_scored"))
        .where(Score.scored_at < latest_subq.c.max_scored)  # noqa: this needs a join
        .group_by(Score.asset_id)
        .subquery()
    )
    # Simplified: for each asset with a new score, get the score just before it
    count = 0
    for ticker, new_score in new_scores.items():
        prev_result = await session.execute(
            select(Score)
            .where(Score.asset_id == new_score.asset_id, Score.scored_at < new_score.scored_at)
            .order_by(Score.scored_at.desc())
            .limit(1)
        )
        prev_score = prev_result.scalar_one_or_none()
        if prev_score is None:
            continue

        delta = new_score.composite_percentile - prev_score.composite_percentile
        if abs(delta) <= 5.0:
            continue

        # Classify via engine
        engine_event = EventRecord(
            event_type=EngineEventType.SCORE_CHANGE,
            ticker=ticker,
            timestamp=new_score.scored_at,
            severity="minor",  # placeholder, will be classified
            source="scoring_pipeline",
            payload={"old_score": prev_score.composite_percentile, "new_score": new_score.composite_percentile, "delta": round(delta, 2)},
        )
        severity = _classifier.classify(engine_event)

        event = Event(
            event_id=str(uuid4()),
            event_type="score_change",
            ticker=ticker,
            timestamp=new_score.scored_at,
            severity=severity.value,
            source="scoring_pipeline",
            payload={"old_score": prev_score.composite_percentile, "new_score": new_score.composite_percentile, "delta": round(delta, 2)},
        )
        session.add(event)
        await session.flush()

        notification = Notification(
            notification_id=str(uuid4()),
            event_id=event.id,
        )
        session.add(notification)
        count += 1

    await session.commit()
    return count
```

Then call `_emit_score_change_events` at the end of `full_score_v4` after scoring completes successfully (before the return):

```python
# In full_score_v4, after job.status = "completed":
async with session_factory() as session:
    n_events = await _emit_score_change_events(session)
    if n_events:
        logger.info("[score_v4] Emitted %d score change events", n_events)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_score_change_events.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_score_change_events.py
git commit -m "feat(events): emit score_change events after V4 scoring"
```

---

### Task 6: Broadcast Score Change Events via WebSocket

**Files:**
- Modify: `api/src/margin_api/workers.py`
- Modify: `api/tests/test_ws_scores.py`

**Step 1: Write the failing test**

Add to `test_ws_scores.py`:

```python
@pytest.mark.asyncio
async def test_broadcast_called_after_score_events(async_session):
    """After score change events are emitted, broadcast should be called."""
    from margin_api.workers import _broadcast_score_events
    from margin_api.db.models import Event
    from margin_api.ws.scores import manager, ScoreChangeMessage
    from unittest.mock import AsyncMock, patch
    from datetime import UTC, datetime

    event = Event(
        event_id="evt-broadcast-001",
        event_type="score_change",
        ticker="AAPL",
        timestamp=datetime.now(UTC),
        severity="major",
        source="scoring_pipeline",
        payload={"old_score": 70.0, "new_score": 85.0, "delta": 15.0},
    )
    async_session.add(event)
    await async_session.commit()

    with patch.object(manager, "broadcast", new_callable=AsyncMock) as mock_broadcast:
        await _broadcast_score_events(async_session)
        assert mock_broadcast.call_count == 1
        msg = mock_broadcast.call_args[0][0]
        assert isinstance(msg, ScoreChangeMessage)
        assert msg.ticker == "AAPL"
        assert msg.delta == 15.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_ws_scores.py::test_broadcast_called_after_score_events -v`
Expected: FAIL — `ImportError: cannot import name '_broadcast_score_events'`

**Step 3: Implement `_broadcast_score_events` in workers.py**

```python
from margin_api.ws.scores import manager, ScoreChangeMessage

async def _broadcast_score_events(session: AsyncSession) -> int:
    """Broadcast recent unbroadcast score_change events via WebSocket."""
    from margin_api.db.models import Event

    # Get score_change events from the last 5 minutes (covers current scoring run)
    cutoff = datetime.now(UTC) - timedelta(minutes=5)
    result = await session.execute(
        select(Event)
        .where(Event.event_type == "score_change", Event.created_at >= cutoff)
        .order_by(Event.created_at)
    )
    events = result.scalars().all()

    for event in events:
        msg = ScoreChangeMessage(
            ticker=event.ticker,
            old_score=event.payload.get("old_score", 0.0),
            new_score=event.payload.get("new_score", 0.0),
            delta=event.payload.get("delta", 0.0),
            severity=event.severity,
            timestamp=event.timestamp,
            event_id=event.event_id,
        )
        await manager.broadcast(msg)

    return len(events)
```

Call after `_emit_score_change_events` in `full_score_v4`:

```python
if n_events:
    logger.info("[score_v4] Emitted %d score change events", n_events)
    async with session_factory() as session:
        await _broadcast_score_events(session)
    logger.info("[score_v4] Broadcast %d events via WebSocket", n_events)
```

**Step 4: Run tests**

```bash
uv run pytest api/tests/test_ws_scores.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_ws_scores.py
git commit -m "feat(events): broadcast score changes via WebSocket after scoring"
```

---

### Task 7: Frontend WebSocket Hook

**Files:**
- Create: `web/src/hooks/useScoreUpdates.ts`
- Test: `web/src/__tests__/hooks/useScoreUpdates.test.ts`

**Step 1: Write the failing test**

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useScoreUpdates } from '@/hooks/useScoreUpdates'

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = []
  onopen: (() => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  readyState = 0

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
    setTimeout(() => {
      this.readyState = 1
      this.onopen?.()
    }, 0)
  }

  send = vi.fn()
  close = vi.fn()
}

describe('useScoreUpdates', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('connects to ws/scores endpoint', async () => {
    renderHook(() => useScoreUpdates())
    await vi.waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1)
      expect(MockWebSocket.instances[0].url).toContain('/ws/scores')
    })
  })

  it('returns score update messages', async () => {
    const { result } = renderHook(() => useScoreUpdates())

    await vi.waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1)
    })

    const ws = MockWebSocket.instances[0]
    act(() => {
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({
          ticker: 'AAPL',
          old_score: 70,
          new_score: 85,
          delta: 15,
          severity: 'major',
        }),
      }))
    })

    expect(result.current.updates).toHaveLength(1)
    expect(result.current.updates[0].ticker).toBe('AAPL')
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/__tests__/hooks/useScoreUpdates.test.ts`
Expected: FAIL — module not found

**Step 3: Implement the hook**

```typescript
'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

export interface ScoreUpdate {
  ticker: string
  old_score: number
  new_score: number
  delta: number
  severity: 'minor' | 'moderate' | 'major'
  timestamp: string
  event_id: string
}

const WS_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, 'ws') + '/ws/scores'
const HEARTBEAT_INTERVAL = 30_000
const RECONNECT_DELAY = 5_000

export function useScoreUpdates() {
  const [updates, setUpdates] = useState<ScoreUpdate[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const clearUpdate = useCallback((eventId: string) => {
    setUpdates(prev => prev.filter(u => u.event_id !== eventId))
  }, [])

  useEffect(() => {
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

    function connect() {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        heartbeatRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, HEARTBEAT_INTERVAL)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as ScoreUpdate
          if (data.ticker) {
            setUpdates(prev => [data, ...prev].slice(0, 50))
          }
        } catch {
          // Ignore non-JSON messages (pong, etc.)
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (heartbeatRef.current) clearInterval(heartbeatRef.current)
        reconnectTimeout = setTimeout(connect, RECONNECT_DELAY)
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      if (heartbeatRef.current) clearInterval(heartbeatRef.current)
      wsRef.current?.close()
    }
  }, [])

  return { updates, connected, clearUpdate }
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/__tests__/hooks/useScoreUpdates.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/hooks/useScoreUpdates.ts web/src/__tests__/hooks/useScoreUpdates.test.ts
git commit -m "feat(web): add useScoreUpdates WebSocket hook"
```

---

### Task 8: Frontend Notification Toast Component

**Files:**
- Create: `web/src/components/ScoreNotification.tsx`
- Test: `web/src/__tests__/components/ScoreNotification.test.tsx`

**Step 1: Write the failing test**

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ScoreNotification } from '@/components/ScoreNotification'
import type { ScoreUpdate } from '@/hooks/useScoreUpdates'

describe('ScoreNotification', () => {
  const update: ScoreUpdate = {
    ticker: 'AAPL',
    old_score: 70,
    new_score: 85,
    delta: 15,
    severity: 'major',
    timestamp: '2026-02-23T12:00:00Z',
    event_id: 'evt-001',
  }

  it('renders ticker and delta', () => {
    render(<ScoreNotification update={update} onDismiss={vi.fn()} />)
    expect(screen.getByText('AAPL')).toBeDefined()
    expect(screen.getByText(/\+15/)).toBeDefined()
  })

  it('calls onDismiss when close button clicked', () => {
    const onDismiss = vi.fn()
    render(<ScoreNotification update={update} onDismiss={onDismiss} />)
    fireEvent.click(screen.getByRole('button'))
    expect(onDismiss).toHaveBeenCalledWith('evt-001')
  })

  it('shows severity indicator', () => {
    render(<ScoreNotification update={update} onDismiss={vi.fn()} />)
    // major severity should have a visual indicator
    expect(screen.getByText(/major/i)).toBeDefined()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/__tests__/components/ScoreNotification.test.tsx`
Expected: FAIL — module not found

**Step 3: Implement the component**

```tsx
'use client'

import type { ScoreUpdate } from '@/hooks/useScoreUpdates'

const SEVERITY_STYLES = {
  major: 'border-l-red-500 bg-red-500/10',
  moderate: 'border-l-amber-500 bg-amber-500/10',
  minor: 'border-l-blue-500 bg-blue-500/10',
} as const

export function ScoreNotification({
  update,
  onDismiss,
}: {
  update: ScoreUpdate
  onDismiss: (eventId: string) => void
}) {
  const sign = update.delta > 0 ? '+' : ''

  return (
    <div
      className={`border-l-4 rounded-r-lg p-3 flex items-center justify-between gap-3 ${SEVERITY_STYLES[update.severity]}`}
      role="alert"
    >
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm">{update.ticker}</span>
          <span className="text-xs uppercase opacity-70">{update.severity}</span>
        </div>
        <div className="text-xs opacity-80">
          Score: {update.old_score.toFixed(1)} → {update.new_score.toFixed(1)} ({sign}{update.delta.toFixed(1)})
        </div>
      </div>
      <button
        onClick={() => onDismiss(update.event_id)}
        className="text-xs opacity-50 hover:opacity-100"
        aria-label="Dismiss notification"
      >
        ✕
      </button>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/__tests__/components/ScoreNotification.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add web/src/components/ScoreNotification.tsx web/src/__tests__/components/ScoreNotification.test.tsx
git commit -m "feat(web): add ScoreNotification toast component"
```

---

### Task 9: Wire Notifications into Dashboard Layout

**Files:**
- Modify: `web/src/app/(dashboard)/layout.tsx` (or equivalent dashboard layout)
- Test: Verify visually + existing tests still pass

**Step 1: Add notification container to dashboard layout**

Import `useScoreUpdates` and `ScoreNotification`, render a fixed-position notification stack in the layout:

```tsx
'use client'

import { useScoreUpdates } from '@/hooks/useScoreUpdates'
import { ScoreNotification } from '@/components/ScoreNotification'

// Inside layout component:
const { updates, clearUpdate } = useScoreUpdates()

// In JSX, add a fixed notification area:
<div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80">
  {updates.slice(0, 5).map((update) => (
    <ScoreNotification
      key={update.event_id}
      update={update}
      onDismiss={clearUpdate}
    />
  ))}
</div>
```

**Step 2: Run all web tests**

```bash
cd web && npx vitest run
```

Expected: All tests pass

**Step 3: Commit**

```bash
git add web/src/
git commit -m "feat(web): wire score notifications into dashboard layout"
```

---

### Task 10: Run Full Test Suite and Verify

**Step 1: Run all engine tests**

```bash
uv run pytest engine/tests/ -v
```

Expected: All pass (no engine changes)

**Step 2: Run all API tests**

```bash
uv run pytest api/tests/ -v
```

Expected: All pass including new event DB, score change emission, and broadcast tests

**Step 3: Run all web tests**

```bash
cd web && npx vitest run
```

Expected: All pass including new hook and component tests

**Step 4: Run linting**

```bash
uv run ruff check engine/src engine/tests api/src api/tests
cd web && npx next lint
```

Expected: Clean

**Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: address any lint/test issues from event pipeline wiring"
```
