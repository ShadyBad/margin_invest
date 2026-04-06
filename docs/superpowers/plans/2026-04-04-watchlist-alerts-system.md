# Watchlist and Alert System Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development
> or superpowers:executing-plans to implement this plan.

**Goal:** Add user-managed watchlists and score alerts with email notifications.

**Architecture:** Two new DB tables, two new route files, one new worker function,
Resend email integration, and dashboard UI additions.

**Spec:** `docs/superpowers/specs/2026-04-04-external-spec-gap-analysis-design.md`

---

## Tasks (14 total, TDD throughout)

### Task 1: ORM Models
- [ ] Add `Watchlist` model to `api/src/margin_api/db/models.py`
- [ ] Add `ScoreAlert` model to `api/src/margin_api/db/models.py`
- [ ] Verify import works
- [ ] Commit

### Task 2: Alembic Migration
- [ ] Generate: `cd api && uv run alembic revision --autogenerate -m "add_watchlists_and_score_alerts_tables"`
- [ ] Add idempotent guards (inspector.has_table checks)
- [ ] Verify single head: `cd api && uv run alembic heads`
- [ ] Apply: `cd api && uv run alembic upgrade head`
- [ ] Verify tables exist
- [ ] Commit

### Task 3: Pydantic Schemas
- [ ] Create `api/src/margin_api/schemas/watchlist.py`
  - WatchlistItemResponse, WatchlistResponse
  - AlertCreateRequest (with threshold validator), AlertResponse, AlertListResponse
- [ ] Verify import
- [ ] Commit

### Task 4: Watchlist CRUD Tests (TDD)
- [ ] Create `api/tests/routes/test_watchlist.py` with 7 tests
- [ ] Run to verify failures
- [ ] Commit failing tests

### Task 5: Watchlist + Alert CRUD Routes
- [ ] Create `api/src/margin_api/routes/watchlist.py`
  - GET/POST/DELETE /api/v1/me/watchlist
  - GET/POST/DELETE /api/v1/me/alerts
- [ ] Register router in `api/src/margin_api/app.py`
- [ ] Run watchlist tests, verify pass
- [ ] Commit

### Task 6: Alert CRUD Tests
- [ ] Create `api/tests/routes/test_alerts.py` with 9 tests
- [ ] Run to verify pass
- [ ] Commit

### Task 7: Alert Trigger Worker
- [ ] Create `api/tests/workers/test_trigger_alerts.py` with 5 tests
- [ ] Run to verify failures
- [ ] Add `_evaluate_alerts` and `trigger_score_alerts` to `workers.py`
- [ ] Register in ARQ functions list
- [ ] Run tests, verify pass
- [ ] Run full API suite for regressions
- [ ] Commit

### Task 8: Next.js Proxy Routes
- [ ] Create `web/src/app/api/v1/me/watchlist/route.ts` (GET)
- [ ] Create `web/src/app/api/v1/me/watchlist/[ticker]/route.ts` (POST/DELETE)
- [ ] Create `web/src/app/api/v1/me/alerts/route.ts` (GET/POST)
- [ ] Create `web/src/app/api/v1/me/alerts/[id]/route.ts` (DELETE)
- [ ] Commit

### Task 9: TypeScript Types + API Client
- [ ] Add types to `web/src/lib/api/types.ts`
  - UserWatchlistItem, UserWatchlistResponse
  - ScoreAlertItem, AlertListResponse, AlertCreateRequest
- [ ] Create `web/src/lib/api/watchlist.ts` with 6 functions
- [ ] Commit

### Task 10: Watchlist UI Component
- [ ] Write failing test in `web/src/components/dashboard/__tests__/user-watchlist.test.tsx`
- [ ] Implement `web/src/components/dashboard/user-watchlist.tsx`
- [ ] Run test, verify pass
- [ ] Commit

### Task 11: Alert Manager UI
- [ ] Write failing test in `web/src/components/dashboard/__tests__/alert-manager.test.tsx`
- [ ] Implement `web/src/components/dashboard/alert-manager.tsx`
- [ ] Run test, verify pass
- [ ] Commit

### Task 12: Watchlist Button on Asset Detail
- [ ] Write failing test in `web/src/components/asset-detail/__tests__/watchlist-button.test.tsx`
- [ ] Implement `web/src/components/asset-detail/watchlist-button.tsx`
- [ ] Run test, verify pass
- [ ] Commit

### Task 13: Wire Into Dashboard
- [ ] Add exports to `web/src/components/dashboard/index.ts`
- [ ] Add UserWatchlist + AlertManager sections to `web/src/app/dashboard/page.tsx`
- [ ] Run web tests
- [ ] Commit

### Task 14: Full Regression Suite
- [ ] Engine tests: `uv run pytest engine/tests/ -q`
- [ ] API tests: `uv run pytest api/tests/ --ignore=api/tests/services/test_xbrl_parser.py -q`
- [ ] Web tests: `cd web && npx vitest run`
- [ ] Linters: `uv run ruff check --fix . && uv run ruff format .`
- [ ] Commit lint fixes if any

---

**Complete code for all tasks** (models, schemas, routes, workers, proxy routes,
components, and tests) is documented in the conversation history with full code blocks.
Refer to the conversation for exact file contents.
