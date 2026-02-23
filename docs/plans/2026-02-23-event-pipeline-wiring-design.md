# Event Pipeline Wiring Design

**Goal:** Connect the three existing event system layers (engine models, API routes, WebSocket endpoint) end-to-end so scoring results flow to users in real time.

**Constraint:** No new features. Only wire what's already built.

## Architecture

```
full_score workers
    │
    ▼
compare old vs new scores
    │
    ▼
engine EventPipeline (filter → ImpactClassifier → NotificationThrottle)
    │
    ▼
persist Event + Notification to DB
    │
    ▼
ConnectionManager.broadcast() via WebSocket
    │
    ▼
Frontend WebSocket hook → notification toast / dashboard update
```

## Scope

### 1. DB Persistence (Event + Notification tables)

Add SQLAlchemy models for Event and Notification. Create alembic migration. Replace the in-memory dicts in `api/routes/events.py` with async DB queries.

### 2. Scoring → Event Creation

After `full_score` / `full_score_v3` / `full_score_v4` complete in `workers.py`, compare new scores against previous scores. For any score change exceeding the delta threshold (5 pts), create a score_change event using the existing `add_event()` helper.

### 3. Event Pipeline Integration

When events are created via the API, run them through the engine's `ImpactClassifier` for severity classification and `NotificationThrottle` for rate limiting before storing.

### 4. WebSocket Broadcast

After an event is persisted, call `manager.broadcast()` with a `ScoreChangeMessage` to push to all connected WebSocket clients.

### 5. Frontend WebSocket Client

Add a React hook (`useScoreUpdates`) that connects to `/ws/scores`, parses incoming messages, and surfaces them as notification toasts and/or updates the dashboard score display.

## What's NOT in Scope

- Event detection (Finnhub, EDGAR, FRED polling) — new feature
- Re-score triggering (IMMEDIATE/DEFERRED) — new feature
- Notification preferences / user settings — separate item (#3 on the list)
- Email notifications via Resend — new feature
