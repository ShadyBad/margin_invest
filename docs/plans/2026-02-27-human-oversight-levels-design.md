# Human Oversight Levels Design

Separate human oversight by decision stakes using the Agentic Autonomy Curve framework.

## Overview

Three oversight levels applied across two layers (operator + end-user):

- **Human-in-the-Loop**: Drives, reviews, approves. For high-stakes decisions.
- **Human-on-the-Loop**: Supervises, monitors trends. For routine operations.
- **Human-out-of-the-Loop**: Audits after the fact. For autonomous data processing.

Implementation uses a **state machine pipeline** — every gated output moves through `staged → approved → published` (or `rejected`/`expired`). A `pipeline_approvals` table tracks each gated output, doubling as an audit trail.

## Component Classification

### Human-in-the-Loop (Approval Required)

| Component | Current Behavior | Proposed Gate |
|-----------|-----------------|---------------|
| Score publication | V4Score rows written → immediately served | Scores staged with `published=False`; operator approves the batch |
| ML model deployment | `train_ml_models` writes MlModelRun, v4 scorer picks up if `model_qualifies=True` | New model held as `candidate`; operator reviews metrics, promotes to `active` |
| Universe activation | `/admin/universe/activate` immediately replaces active snapshot | Creates `pending` snapshot; operator reviews ticker diff and approves |
| Filter threshold changes | Code deploy | Config change creates pending entry; operator reviews impact before activation |
| User watchlist changes | Not yet implemented | System proposes; user explicitly accepts |
| User portfolio suggestions | Not yet implemented | Presented as proposals; never auto-executed |

### Human-on-the-Loop (Monitor + Override)

| Component | Monitoring |
|-----------|-----------|
| Daily scoring pipeline | Dashboard: pipeline health, score drift alerts, conviction swing alerts (>2 levels) |
| 13F ingest | Anomaly detection: sudden filing drops, large cross-manager position swings |
| Backtest replay | Flagged if metrics deviate significantly from historical norms |
| User alert thresholds | System proposes alerts; user monitors and adjusts sensitivity |

### Human-out-of-the-Loop (Autonomous + Audit)

| Component | Audit |
|-----------|-------|
| Data ingestion (yfinance batches) | Event stream: per-ticker success/fail/NaN-sanitized |
| Live price polling | Event stream: cache hit/miss rates, stale price warnings |
| Data quality flagging | Event stream: quarantine events, retry outcomes |
| Accumulation signal computation | Event stream: signal count, distribution shifts |
| Retry quarantined | Event stream: what was retried, outcomes |

## State Machine

Every gated output follows this lifecycle:

```
pending → staged → approved → published
                 ↘ rejected (terminal)
                 ↘ expired (auto, after configurable window)
```

- **pending**: Pipeline job running, output not yet written.
- **staged**: Output written to DB but NOT served to users. Awaiting operator review.
- **approved**: Operator approved. System publishes.
- **rejected**: Operator rejected. Output archived with reason. Previous live data continues.
- **expired**: Auto-transition if staged output sits unapproved for >24h (configurable).

## Data Model

### `pipeline_approvals`

| Column | Type | Purpose |
|--------|------|---------|
| id | UUID | PK |
| gate_type | Enum: `score_publish`, `ml_model_deploy`, `universe_activate`, `filter_config_change` | Decision type |
| status | Enum: `staged`, `approved`, `rejected`, `expired` | Current state |
| pipeline_id | UUID | Links to JobRun.pipeline_id |
| payload_ref | JSONB | Pointer to staged data |
| impact_summary | JSONB | Pre-computed impact analysis |
| submitted_at | DateTime(tz) | When staged |
| decided_at | DateTime(tz) | When approved/rejected |
| decided_by | FK → User | Who decided |
| decision_reason | Text | Optional operator note |
| expires_at | DateTime(tz) | Auto-expire deadline |

### `governance_events`

| Column | Type | Purpose |
|--------|------|---------|
| id | UUID | PK |
| event_type | String | e.g., `ingestion.ticker.success` |
| source | String | Worker/service that generated it |
| detail | JSONB | Event-specific payload |
| created_at | DateTime(tz) | Timestamp |

### `user_proposals`

| Column | Type | Purpose |
|--------|------|---------|
| id | UUID | PK |
| user_id | FK → User | Which user |
| proposal_type | Enum: `watchlist_add`, `watchlist_remove`, `alert_config`, `portfolio_suggestion` | Proposal type |
| status | Enum: `pending`, `accepted`, `dismissed`, `expired` | User's decision |
| payload | JSONB | Proposed change details |
| created_at | DateTime(tz) | When proposed |
| decided_at | DateTime(tz) | When user acted |

### Existing Table Modifications

**V4Score**: Add `published` boolean column (default `False`). Score-serving API changes query to `WHERE published=True`. Operator approval flips batch to `published=True`.

**MlModelRun**: Add `deployment_status` enum (`candidate`, `active`, `retired`). V4 scorer uses `WHERE deployment_status='active'`.

## Pipeline Integration

### Scoring Pipeline

Current chain adds an approval checkpoint after v4:

```
... → full_score_v4 → stage_scores → [OPERATOR APPROVAL] → publish_scores
```

- **`full_score_v4`** (modified): Writes V4Score rows with `published=False`. No longer emits WebSocket events.
- **`stage_scores`** (new): Creates `pipeline_approvals` row, computes impact summary, sends operator notification, sets expiry.
- **`publish_scores`** (new, triggered by approval): Flips `published=True`, emits WebSocket events, updates approval status.

### ML Model Deployment

- `train_ml_models` writes MlModelRun with `deployment_status=candidate`
- Creates `pipeline_approvals` row with impact summary (rank IC, comparison to active model)
- Operator approves → `candidate` promoted to `active`, previous `active` set to `retired`

### Universe Activation

- `/admin/universe/activate` creates snapshot in `pending` state + approval row
- Impact summary: diff of added/removed tickers vs. current active snapshot
- Operator approves → snapshot activated

### Expiry Daemon

Hourly job: finds `staged` approvals past `expires_at`, transitions to `expired`, logs governance event, optionally notifies operator.

### Circuit Breakers (Auto-Escalation)

On-the-loop components auto-escalate to in-the-loop when anomalies detected:

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Score drift | >30% of universe changes conviction level in single run | Auto-stage batch for approval |
| Ingestion failure rate | >20% of tickers fail in a batch | Pause pipeline, create approval for partial-data scoring |
| ML model regression | New model rank IC >50% lower than active model | Flag even if technically qualifying |

Thresholds stored in `governance_config` table (key-value, tunable without code deploys).

## API Endpoints

### Admin Endpoints (X-Admin-Key HMAC auth)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/admin/approvals` | GET | List approvals, filterable by gate_type/status |
| `/api/v1/admin/approvals/{id}` | GET | Full detail with impact summary and staged data preview |
| `/api/v1/admin/approvals/{id}/approve` | POST | Approve, triggers publish job |
| `/api/v1/admin/approvals/{id}/reject` | POST | Reject with required reason |
| `/api/v1/admin/governance/events` | GET | Query event stream, filterable/paginated |
| `/api/v1/admin/governance/config` | GET/PUT | Read/update governance thresholds |
| `/api/v1/admin/governance/dashboard` | GET | Aggregated stats: pending count, approval latency, rejection rate |

### User Endpoints (JWT auth)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/proposals` | GET | List user's pending/recent proposals |
| `/api/v1/proposals/{id}/accept` | POST | Accept a proposal |
| `/api/v1/proposals/{id}/dismiss` | POST | Dismiss a proposal |

### Public Endpoint

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/governance/transparency` | GET | Oversight classification, last approval timestamps, pipeline health |

## Operator Admin UI (`/admin/approvals`)

Three sections:

**Approval Queue**: Cards per pending approval — gate type badge, impact summary, time remaining. Expand for full detail (score diffs, model comparisons, universe diffs). Approve/Reject with reason field.

**Pipeline Monitor**: Current pipeline status, score drift chart, ingestion health trend, ML model timeline.

**Event Log**: Filterable, paginated governance events table. Event volume sparklines per category.

## User-Facing Proposal UI

Integrated into existing surfaces, not a separate page:

- **Dashboard**: Notification badge for pending proposals. Small proposal card in sidebar.
- **Asset detail**: Inline prompt in hero section if system proposes adding ticker to watchlist.
- **Passive**: Proposals appear, user acts when ready. No modal interrupts.

## Governance Event Stream

### Redis Stream

Components emit to `governance:events`:

| Category | Event Types |
|----------|------------|
| `ingestion.*` | `ticker.success`, `ticker.failed`, `ticker.quarantined`, `batch.complete` |
| `pricing.*` | `cache.refreshed`, `cache.stale`, `cache.miss` |
| `quality.*` | `nan_sanitized`, `data_gap_detected`, `retry.success`, `retry.failed` |
| `scoring.*` | `batch.staged`, `batch.published`, `batch.expired`, `drift.alert` |
| `ml.*` | `model.trained`, `model.promoted`, `model.retired`, `model.regression_alert` |
| `thirteenf.*` | `filing.ingested`, `accumulation.computed`, `anomaly.detected` |
| `circuit_breaker.*` | `score_drift.triggered`, `failure_rate.triggered`, `ml_regression.triggered` |

### DB Rollup

`rollup_governance_events` runs every 6 hours: reads Redis stream, batch inserts to `governance_events` table, trims consumed entries (retains 24h in Redis for real-time queries).

### Transparency Endpoint Response

```json
{
  "oversight_levels": {
    "in_the_loop": ["score_publication", "ml_model_deployment", "universe_activation", "filter_config"],
    "on_the_loop": ["daily_scoring_pipeline", "13f_ingest", "backtest_replay"],
    "out_of_the_loop": ["data_ingestion", "live_pricing", "data_quality", "accumulation_signals"]
  },
  "last_approvals": {
    "score_publish": {"decided_at": "...", "status": "approved"},
    "ml_model_deploy": {"decided_at": "...", "status": "approved"}
  },
  "pipeline_health": {
    "status": "idle",
    "last_successful_run": "...",
    "ingestion_success_rate_7d": 0.97
  }
}
```

## Notification Delivery

Operator notifications for pending approvals:

- **Webhook**: POST to configurable URL when new approval staged
- **Reminder**: If still pending after 50% of expiry window
- **Escalation**: If expired without action, notify secondary contact

Configuration in `governance_config`:
```
notification.webhook_url = "https://hooks.slack.com/..."
notification.reminder_pct = 0.5
notification.escalation_email = "ops@margin.invest"
```
