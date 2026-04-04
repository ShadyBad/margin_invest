# External Spec Gap Analysis — Watchlist & Alert System

**Date**: 2026-04-04
**Context**: An external spec was provided describing Margin Invest's architecture, scoring engine, API, and frontend. This document reconciles that spec against the existing production system and identifies the genuine implementation gaps.

## Methodology

Every section of the external spec was audited against the live codebase. Items are classified as:
- **Covered**: Exists in equal or superior form
- **Covered (superior)**: Exists and exceeds the spec
- **Genuine gap**: Does not exist, needs implementation

---

## 1. Architecture & Infrastructure

| Spec Proposes | Existing | Decision |
|---|---|---|
| `apps/web`, `apps/api`, `packages/scoring` | `engine/`, `api/`, `web/` | **Keep** — same logical split |
| Supabase Postgres + Supabase Auth | PostgreSQL 16 + custom JWT/HMAC/MFA/WebAuthn | **Keep** — ripping out auth would be a regression |
| Vercel + Railway/Fly | Railway (API + worker) | **Keep** — defer Vercel migration |
| FMP API primary, yfinance fallback | EDGAR/XBRL + yfinance + PIT pipeline | **Keep** — far more robust |
| Stripe integration | Stripe integration exists | **Covered** |

**No gaps.** All infrastructure decisions favor the existing system.

---

## 2. Database Schema

| Spec Table | Existing Equivalent | Status |
|---|---|---|
| `equity_universe` | `assets` (ticker, name, exchange, sector, industry, is_active) | **Covered** |
| `scoring_cycles` | `ingestion_runs` + `job_runs` | **Covered** |
| `equity_scores` | `scores` + `v3_scores` + `v4_scores` (3 scoring generations) | **Covered (superior)** |
| `score_history` | `historical_scores` | **Covered** |
| `watchlists` | — | **Genuine gap** |
| `score_alerts` | — | **Genuine gap** |

### Gap G1: `watchlists` table

```sql
CREATE TABLE watchlists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, ticker)
);
CREATE INDEX ix_watchlists_user_id ON watchlists(user_id);
```

SQLAlchemy model in `api/src/margin_api/db/models.py`. Alembic migration.

### Gap G2: `score_alerts` table

```sql
CREATE TABLE score_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  alert_type TEXT NOT NULL CHECK (alert_type IN ('above', 'below', 'survivor')),
  threshold NUMERIC(5,2),  -- NULL for 'survivor' type
  is_active BOOLEAN NOT NULL DEFAULT true,
  last_triggered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, ticker, alert_type)
);
CREATE INDEX ix_score_alerts_user_id ON score_alerts(user_id);
CREATE INDEX ix_score_alerts_active ON score_alerts(is_active) WHERE is_active = true;
```

- `above`: fires when composite score crosses above threshold
- `below`: fires when composite score drops below threshold
- `survivor`: fires when a ticker enters or exits the survivor list
- `last_triggered_at`: prevents duplicate notifications within a cooldown window
- Unique constraint on (user_id, ticker, alert_type) prevents duplicate alerts

---

## 3. Scoring Engine

**No gaps.** The existing engine exceeds the spec in every dimension.

### Elimination Filters

| Spec Filter | Existing | Notes |
|---|---|---|
| Penny Stock (price < $1) | No explicit filter | Market cap minimums ($100M+) and dollar volume tiers are strictly more aggressive — any penny stock is eliminated by liquidity |
| Liquidity (30d vol < 50K) | `filters/liquidity.py` — market cap floors, dollar volume tiers, years of history | **Covered (superior)** — sector-adjusted thresholds |
| Delisting (inactive) | `is_active` filter + PIT delisting detection | **Covered** |
| Data Sufficiency (< 4 quarters) | `min_years_of_history` (default 5 years) | **Covered** — stricter than spec |
| Beneish M-Score (> -1.78) | `filters/beneish.py` — 8-variable model + v2 multi-period | **Covered** |
| Altman Z-Score (< 1.81) | `filters/altman.py` | **Covered** |

Additional filters not in spec: `current_ratio`, `interest_coverage`, `fcf_distress`, `mediocrity_gate` (7 filters total vs spec's 6).

### Five-Factor Scoring

Spec describes simple 5-factor model with fixed subfactor weights. Existing engine has:
- Multi-track cascade system (Track A compounder, Track B mispricing, Track C efficient growth)
- Sector-neutral percentile ranking within GICS sectors
- Growth-stage-aware weight adjustments
- Cyclical asset 7-year median normalization

All 5 core factors (quality, value, momentum, sentiment, growth) exist with richer subfactor definitions.

### Composite Score

Spec: `geometric_mean(factors)` with floor at 1.0.
Existing: `v3_composite.py` — weighted geometric mean with configurable factor floor (0.05) and composite floor. Identical approach, better parameterized.

### Conviction Gate

Spec: composite >= 50, ROIC > 0, no factor below 20.
Existing: ROIC-conditional conviction gates with reinvestment tiers, trajectory overrides for turnarounds, capital-light bypass for high-ROIC companies. Strictly more nuanced.

---

## 4. API Endpoints

| Spec Endpoint | Existing | Status |
|---|---|---|
| `GET /api/health` | `routes/health.py` | **Covered** |
| `GET /api/cycle/latest` | `routes/dashboard.py` | **Covered** |
| `GET /api/survivors` | `routes/public_scores.py` + `routes/v3_scores.py` | **Covered** |
| `GET /api/score/{ticker}` | `routes/scores.py` + `routes/v3_scores.py` | **Covered** |
| `GET /api/score/{ticker}/history` | `routes/scores.py` | **Covered** |
| `GET /api/explore?sector=&sort=` | `routes/public_scores.py` | **Covered** |
| `GET /api/me/watchlist` + POST/DELETE | — | **Genuine gap (G3)** |
| `GET /api/me/alerts` + POST/DELETE | — | **Genuine gap (G4)** |
| `GET /api/report/{ticker}` | `routes/scores.py` (tier-gated) | **Covered** |
| `GET /api/correlation?tickers=` | `routes/correlations.py` | **Covered** |
| `GET /api/smart-money/{ticker}` | `routes/thirteenf.py` | **Covered** |
| `POST /api/internal/run-cycle` | ARQ cron: `orchestrate_ingest` (21:30 UTC) + 12 more crons | **Covered (superior)** — 13 cron jobs vs 1 HTTP trigger |
| Tier enforcement | `deps.py` `require_plan()` — analyst/portfolio/institutional/operator | **Covered** |

### Gap G3: Watchlist CRUD endpoints

New route file: `api/src/margin_api/routes/watchlist.py`

```
GET  /api/me/watchlist              — list user's watchlist with latest scores
POST /api/me/watchlist/{ticker}     — add ticker to watchlist
DELETE /api/me/watchlist/{ticker}   — remove ticker from watchlist
```

All routes require authentication. No tier gating (available to all users including free tier).

Response for GET includes latest score data for each watchlisted ticker (join with `v4_scores` or latest scoring table).

### Gap G4: Alert CRUD endpoints

New route file: `api/src/margin_api/routes/alerts.py`

```
GET    /api/me/alerts              — list user's alerts
POST   /api/me/alerts              — create alert (ticker, alert_type, threshold)
DELETE /api/me/alerts/{alert_id}   — delete alert
```

All routes require authentication. No tier gating.

Validation:
- `alert_type` must be one of: `above`, `below`, `survivor`
- `threshold` required for `above`/`below`, ignored for `survivor`
- Max 20 alerts per user (prevent abuse)

---

## 5. Alert Pipeline

### Gap G5: Alert trigger logic

After each scoring cycle completes (end of `orchestrate_ingest` chain), a new step checks all active alerts against fresh scores:

- `above`: fire if new composite >= threshold AND (previous composite < threshold OR first score)
- `below`: fire if new composite <= threshold AND (previous composite > threshold OR first score)
- `survivor`: fire if survived status changed (entered or exited survivor list)

Cooldown: skip if `last_triggered_at` is within 24 hours (prevents duplicate notifications from re-runs).

Wire into existing worker chain: after `stage_scores` (or `publish_scores`), enqueue `trigger_score_alerts`.

### Gap G6: Email notification delivery

New integration: Resend (simpler API, better developer experience than Postmark for transactional email).

- New worker function: `deliver_alert_email(user_id, alert_id, score_data)`
- Uses existing `deliver_webhook` pattern: ARQ task, retry with exponential backoff (3 attempts)
- Email template: minimal — ticker, alert type, current score, link to asset detail page
- Config: `RESEND_API_KEY` env var

---

## 6. Frontend

| Spec Page | Existing | Status |
|---|---|---|
| `/explore` | `web/src/app/explore/page.tsx` | **Covered** |
| `/dashboard` | `web/src/app/dashboard/page.tsx` — picks list, market context | **Partially covered** — missing watchlist + alerts UI |
| `/score/{ticker}` | `web/src/app/asset/[ticker]/` — full detail page | **Covered** |
| `/methodology` | `web/src/app/methodology/` | **Covered** |

### Gap G7: User-managed watchlist UI

Add to `/dashboard`:
- Watchlist section showing user's saved tickers with latest composite score, signal, and sector
- "Add to watchlist" button on asset detail page (`/asset/[ticker]`)
- "Remove" action on each watchlist row
- Empty state: prompt to explore and add tickers

Uses `apiFetch()` client-side calls to watchlist CRUD endpoints.

### Gap G8: Alert management UI

Add to `/dashboard`:
- Alerts section showing active alerts (ticker, type, threshold, last triggered)
- "Create alert" form: ticker autocomplete, alert type dropdown, threshold input
- "Delete" action on each alert row
- Visual indicator when an alert has fired recently (last 24h)

---

## Implementation Order

1. **DB**: Alembic migrations for `watchlists` and `score_alerts` tables (G1, G2)
2. **API**: Watchlist CRUD routes (G3)
3. **API**: Alert CRUD routes (G4)
4. **Worker**: Alert trigger logic wired into scoring pipeline (G5)
5. **Integration**: Resend email delivery (G6)
6. **Web**: Watchlist UI on dashboard + "add to watchlist" on asset detail (G7)
7. **Web**: Alert management UI on dashboard (G8)

Items 1-4 can be built and tested without the email integration. Item 5 can use a stub (log to console) during development. Items 6-7 (frontend) depend on items 2-4 (API endpoints) being complete.

---

## What This Spec Does NOT Cover (existing features beyond spec)

For completeness, major production features not mentioned in the external spec:
- ML pipeline (multi-seed validation, model training, promotion)
- PIT backtesting engine (17 months of historical data, 15 UI components)
- 13F institutional tracking (fund tracker, market signals, clone lab)
- EDGAR/XBRL pipeline (217K snapshots, 12.8M prices)
- Human oversight pipeline (staged/approved/published, governance, circuit breakers)
- NLP sentiment analysis on SEC filings
- Moat classification, Kelly sizing, inflection detection, drawdown re-screening
- Admin UI (approvals, model validation, governance config)
- MFA/WebAuthn authentication, rate limiting, audit logging
- Shadow portfolio tracking
