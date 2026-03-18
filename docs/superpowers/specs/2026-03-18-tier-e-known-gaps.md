# Tier E: Pre-Existing Known Gaps

Technical design doc for 7 items addressing known gaps from earlier feature work.
These are not part of the Engine v2 spec — they are deferred items from previous
implementation cycles documented in MEMORY.md.

---

## E1: GovernanceConfig CRUD

**Effort: Small**

### Problem

The `GovernanceConfig` ORM model exists (`api/src/margin_api/db/models.py:968`) with a
`governance_configs` table, but no admin CRUD endpoints exist. Circuit breaker thresholds
and approval gates are hardcoded instead of reading from the database.

### Current State

**Model** (`db/models.py`):
```python
class GovernanceConfig(Base):
    __tablename__ = "governance_configs"
    id: Mapped[int]
    config_key: Mapped[str]           # Unique key (e.g., "circuit_breaker.score_drift")
    config_value: Mapped[dict | None]  # JSONB payload
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

**No endpoints:** No GET/PUT/POST/DELETE for governance config.

**Hardcoded thresholds:** Circuit breaker checks (score drift >30%, ingestion failure
>20%, ML regression >50%) are hardcoded in worker code rather than reading from this
table.

### Design

New route file `api/src/margin_api/routes/admin_governance.py`:

```python
# GET /admin/governance-config
async def list_configs(session: AsyncSession) -> list[GovernanceConfigResponse]:
    """List all governance config entries."""

# GET /admin/governance-config/{key}
async def get_config(key: str, session: AsyncSession) -> GovernanceConfigResponse:
    """Get a specific config by key."""

# PUT /admin/governance-config/{key}
async def upsert_config(
    key: str, body: GovernanceConfigUpdate, session: AsyncSession
) -> GovernanceConfigResponse:
    """Create or update a governance config entry."""

# DELETE /admin/governance-config/{key}
async def delete_config(key: str, session: AsyncSession) -> None:
    """Delete a governance config entry."""
```

**Schema:**
```python
class GovernanceConfigResponse(BaseModel):
    config_key: str
    config_value: dict | None
    updated_at: datetime

class GovernanceConfigUpdate(BaseModel):
    config_value: dict
```

**Integration:** Update circuit breaker workers to read thresholds from
`GovernanceConfig` with hardcoded fallbacks:
```python
async def get_threshold(session, key: str, default: float) -> float:
    config = await session.get(GovernanceConfig, key)
    if config and config.config_value:
        return config.config_value.get("threshold", default)
    return default
```

### Files to Create/Modify

| File | Change |
|------|--------|
| `api/src/margin_api/routes/admin_governance.py` | New CRUD endpoints |
| `api/src/margin_api/schemas/governance.py` | New Pydantic schemas |
| `api/src/margin_api/app.py` | Register new router |
| Worker files using circuit breaker thresholds | Read from config with fallback |

### Test Strategy

- CRUD tests: create, read, update, delete config entries
- Test upsert semantics: PUT to existing key updates, PUT to new key creates
- Test workers read from config: mock config row, verify threshold used
- Test fallback: missing config → hardcoded default

---

## E2: Webhook Notifications

**Effort: Medium**

### Problem

No notification system for governance events. When scores are staged for approval,
a model is promoted, or a circuit breaker trips, there's no way to alert external
systems or administrators. Only Stripe webhooks exist (billing, unrelated).

### Current State

- Stripe webhook handler at `routes/billing.py:75`
- Idempotency table: `processed_webhook_events` (exists for Stripe)
- HMAC pattern: model integrity checksums exist in `ml/signal_model.py`
- No governance event dispatch mechanism

### Design

**New DB table:**
```sql
CREATE TABLE webhook_subscriptions (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,           -- 'score.staged', 'model.promoted', etc.
    url TEXT NOT NULL,
    hmac_secret TEXT NOT NULL,          -- Per-subscription signing key
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (event_type, url)
);
```

**Event types:**
- `score.staged` — new scores ready for review
- `score.approved` — scores approved by admin
- `score.published` — scores published to users
- `model.promoted` — ML model promoted to production
- `circuit_breaker.tripped` — circuit breaker activated

**Dispatcher service** `api/src/margin_api/services/webhook_dispatcher.py`:
```python
class WebhookDispatcher:
    async def dispatch(self, event_type: str, payload: dict):
        """Send webhook to all active subscribers for this event type.

        - Sign payload with HMAC-SHA256 using subscriber's secret
        - Set X-Margin-Signature header
        - Retry 3 times with exponential backoff (1s, 4s, 16s)
        - Log failures to governance_events table
        """

    def _sign_payload(self, payload: bytes, secret: str) -> str:
        return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
```

**Integration points:**
- `stage_scores` worker → dispatch `score.staged`
- `publish_scores` worker → dispatch `score.published`
- `promote_ml_model` worker → dispatch `model.promoted`
- Circuit breaker checks → dispatch `circuit_breaker.tripped`

**Admin endpoints for managing subscriptions:**
```python
# GET /admin/webhooks — list all subscriptions
# POST /admin/webhooks — create subscription (generates hmac_secret)
# DELETE /admin/webhooks/{id} — remove subscription
# POST /admin/webhooks/{id}/test — send test payload
```

### Files to Create/Modify

| File | Change |
|------|--------|
| `api/src/margin_api/services/webhook_dispatcher.py` | New dispatch service |
| `api/src/margin_api/db/models.py` | New webhook_subscriptions table |
| `api/alembic/versions/xxx_add_webhook_subscriptions.py` | Migration |
| `api/src/margin_api/routes/admin_webhooks.py` | New admin endpoints |
| `api/src/margin_api/workers.py` | Wire dispatch into existing workers |

### Test Strategy

- Unit test: HMAC signature generation and verification
- Unit test: retry logic with mock HTTP failures
- Integration test: stage_scores → webhook dispatched to mock endpoint
- Test idempotency: same event not dispatched twice
- Test inactive subscription: is_active=False → skipped

---

## E3: NEXT_PUBLIC_ADMIN_KEY Security

**Effort: Small**

### Problem

Three admin pages read `NEXT_PUBLIC_ADMIN_KEY` from environment:
- `web/src/app/admin/approvals/page.tsx:13`
- `web/src/app/admin/model-validation/page.tsx:13`
- `web/src/app/admin/events/page.tsx:6`

`NEXT_PUBLIC_*` variables are **bundled into client JavaScript** — anyone can extract
the admin key from browser DevTools or the JS bundle. This is a security vulnerability.

### Current State

```typescript
// All 3 admin pages
const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_KEY ?? ""
// Used in fetch headers: Authorization: Bearer ${ADMIN_KEY}
```

The API validates this key on admin routes. But the key is exposed in the browser.

### Design

**Option A: Server Components (recommended for Next.js 16)**

Convert admin pages to server components. Read `ADMIN_KEY` (without `NEXT_PUBLIC_`
prefix) on the server side. Use server actions for mutations.

```typescript
// app/admin/approvals/page.tsx (server component)
import { cookies } from "next/headers"

export default async function ApprovalsPage() {
    const session = await getAdminSession()  // Read httpOnly cookie
    if (!session) redirect("/admin/login")

    const data = await serverFetch("/admin/approvals")  // Server-side fetch
    return <ApprovalsClient data={data} />
}
```

**Option B: Admin Login Flow**

Add admin authentication:
1. `POST /api/auth/admin-login` — validates credentials, sets httpOnly session cookie
2. Admin middleware in `web/src/middleware.ts` — checks cookie on `/admin/*` routes
3. Remove `NEXT_PUBLIC_ADMIN_KEY` entirely

The User model already has `password_hash` and `mfa_enabled` — infrastructure exists.

**Recommended: Option A** — simpler, leverages Next.js 16 server components, no new
login UI needed. Admin key stays server-side.

### Files to Modify

| File | Change |
|------|--------|
| `web/src/app/admin/approvals/page.tsx` | Convert to server component |
| `web/src/app/admin/model-validation/page.tsx` | Convert to server component |
| `web/src/app/admin/events/page.tsx` | Convert to server component |
| `web/.env` | Rename NEXT_PUBLIC_ADMIN_KEY → ADMIN_KEY |

### Test Strategy

- Verify admin key NOT present in browser JS bundle (build and inspect)
- Verify admin pages still render with server-side fetch
- Verify unauthenticated access returns 401/redirect

---

## E4: Backtesting Mock Data

**Effort: Small**

### Problem

Some backtesting frontend components may use placeholder or mock data as fallbacks when
API data is unavailable. Test fixtures use mock data (expected), but runtime components
should always show real data from the API or proper loading/error states.

### Current State

- Test files have mock data in `__tests__/*.test.tsx` (expected for unit tests)
- Runtime page `web/src/app/backtesting/page.tsx` fetches from `/api/backtest`
- 15 components in `web/src/components/backtesting/`
- Mock data may exist in component default props or storybook stories

### Design

**Audit phase:**
1. Grep all backtesting components for hardcoded data, `mockData`, `PLACEHOLDER`, etc.
2. Check for default prop values that look like real data (not loading states)
3. Identify any components that render before API data arrives without showing loading state

**Fix phase:**
1. Replace any hardcoded fallback data with proper loading states (`<Skeleton />`)
2. Add error boundaries: if API returns 500, show error message (not mock data)
3. Ensure all chart components receive data exclusively from API responses

**Optional: Storybook stories**
Add stories with realistic fixture data for visual QA of each backtesting component.
This replaces inline mock data with explicit test fixtures.

### Files to Modify

| File | Change |
|------|--------|
| `web/src/components/backtesting/*.tsx` | Audit and fix mock data usage |
| `web/src/app/backtesting/page.tsx` | Add loading/error states if missing |

### Test Strategy

- Grep audit: no `mockData` or hardcoded numbers in non-test files
- Test loading state: API slow → skeleton shown
- Test error state: API 500 → error message shown
- Visual QA: Storybook stories render correctly with fixture data

---

## E5: 13F Analytics Stubs

**Effort: Medium**

### Problem

Two analytics endpoints return empty arrays:
- `GET /analytics/new-positions` — returns `NewPositionResponse(new_positions=[])`
- `GET /analytics/overlap` — returns `OverlapResponse(crowded_trades=[])`

These stubs exist because quarter-over-quarter comparison logic was deferred during
the 13F pipeline implementation.

### Current State

**`routes/thirteenf.py:399`:**
```python
async def get_new_positions(...) -> NewPositionResponse:
    return NewPositionResponse(period_of_report=date.today(), new_positions=[])
```

**`routes/thirteenf.py:343`:**
```python
return OverlapResponse(period_of_report=date.today(), most_held=[], crowded_trades=[])
```

**Available data:**
- `thirteen_f_holdings` table with manager/ticker/shares/value per quarter
- `accumulation_signals` table with aggregated flow data
- `curated_new_positions` count exists in model but not the actual position list

### Design

**New-Positions Logic:**

```python
async def compute_new_positions(
    session: AsyncSession,
    current_quarter: date,
    prev_quarter: date,
) -> list[NewPosition]:
    """Find tickers held in current quarter but not in previous quarter.

    For each ticker:
    - Count how many managers initiated new positions
    - Sum total new shares added
    - Return sorted by new_manager_count descending
    """
    current_holders = await get_holders_for_quarter(session, current_quarter)
    prev_holders = await get_holders_for_quarter(session, prev_quarter)

    new_positions = []
    for ticker, managers in current_holders.items():
        prev_managers = prev_holders.get(ticker, set())
        new_managers = managers - prev_managers
        if new_managers:
            new_positions.append(NewPosition(
                ticker=ticker,
                new_manager_count=len(new_managers),
                total_new_shares=sum(...),
                managers=list(new_managers)[:10],
            ))
    return sorted(new_positions, key=lambda x: -x.new_manager_count)
```

**Crowded-Trades Logic:**

```python
async def compute_crowded_trades(
    session: AsyncSession,
    current_quarter: date,
) -> list[CrowdedTrade]:
    """Find tickers held by the most managers in current quarter.

    Returns top N tickers by total holder count, with concentration metrics.
    """
    holder_counts = await count_holders_per_ticker(session, current_quarter)
    return [
        CrowdedTrade(ticker=t, holder_count=c, concentration_pct=c/total)
        for t, c in sorted(holder_counts.items(), key=lambda x: -x[1])[:20]
    ]
```

**Quarter detection:** Determine current and previous quarters from the most recent
`period_of_report` dates in `thirteen_f_holdings`.

### Files to Modify

| File | Change |
|------|--------|
| `api/src/margin_api/routes/thirteenf.py` | Implement new_positions and overlap logic |
| `api/src/margin_api/services/accumulation_service.py` | Add quarter-over-quarter helpers |

### Test Strategy

- Unit test: 3 managers hold AAPL in Q2 but only 1 in Q1 → 2 new positions
- Unit test: crowded trade ranking by holder count
- Edge case: first quarter with no previous → return empty (no comparison possible)
- Integration test: seed test data for 2 quarters, verify endpoint returns

---

## E6: API Test Coverage

**Effort: Small**

### Problem

API test coverage is ~67%, target is 70%. The rarity worker has only 3 tests. Gaps
exist in governance flows, new worker functions, and edge cases.

### Current State

- `api/tests/workers/test_rarity_worker.py`: 3 tests (no_scores, creates_job_run,
  handles_exception)
- Missing: percentile ranking, multi-ticker, regime classification, edge cases
- Missing: governance worker integration tests (stage→approve→publish flow)
- Missing: webhook dispatch tests (depends on E2)

### Design

**Rarity worker tests** (add 10-12 tests):
```python
class TestRarityPercentileRanking:
    """Test percentile computation with known distributions."""
    def test_single_ticker_rarity(self): ...
    def test_multi_ticker_ranking(self): ...
    def test_ties_in_rarity_score(self): ...
    def test_empty_universe(self): ...

class TestRarityRegimeClassification:
    """Test regime affects rarity thresholds."""
    def test_bull_regime_thresholds(self): ...
    def test_bear_regime_thresholds(self): ...

class TestRarityDimensionScores:
    """Test individual dimension score population."""
    def test_all_dimensions_populated(self): ...
    def test_missing_factor_graceful(self): ...
```

**Governance worker tests** (add 5-8 tests):
```python
class TestGovernanceWorkflow:
    def test_stage_scores_creates_approval(self): ...
    def test_publish_scores_requires_approval(self): ...
    def test_expire_stale_approvals(self): ...
    def test_circuit_breaker_blocks_publish(self): ...
```

### Files to Create/Modify

| File | Change |
|------|--------|
| `api/tests/workers/test_rarity_worker.py` | Add 10-12 tests |
| `api/tests/workers/test_governance_workers.py` | New test file, 5-8 tests |

### Test Strategy

- Run coverage after adding tests: `uv run pytest api/tests/ --cov=margin_api --cov-report=term-missing`
- Target: 70%+ overall, 80%+ for workers/
- Focus on branches not covered (regime conditional logic, error paths)

---

## E7: Deferred API Enhancements

**Effort: Small**

### Problem

Several API enhancements were deferred during the dashboard visualization work:
- Sector champion endpoint (top scorer per sector)
- Dedicated sector listing endpoint
- `market_cap` field on ScoreResponse

Note: `sector_pass_rate` and P10/P50/P90 distribution are **already implemented** —
they were wired in during the dashboard work.

### Current State

- `sector_pass_rate`: computed in CLI (`cli.py:1611`) and injected into responses
  (`routes/scores.py:241`). **Done.**
- P10/P50/P90 distribution: computed in CLI (`cli.py:1613`), wired into sub-factor
  scores. **Done.**
- `market_cap`: available in `AssetProfile.market_cap`, not on `ScoreResponse`
- No `/sectors` or `/sectors/{sector}/champion` endpoints

### Design

**1. Sector champion endpoint:**

New `api/src/margin_api/routes/sectors.py`:
```python
# GET /sectors
async def list_sectors(session: AsyncSession) -> list[SectorSummary]:
    """List all sectors with summary stats.
    Returns: sector name, asset count, avg composite score, top ticker."""

# GET /sectors/{sector}/champion
async def get_sector_champion(sector: str, session: AsyncSession) -> ChampionResponse:
    """Return the highest-scored ticker in the given sector.
    Returns: ticker, composite_score, conviction, track."""
```

Implementation: query latest published scores grouped by sector, take max composite_score.

**2. market_cap on ScoreResponse:**

Add `market_cap: float | None = None` to `schemas/scores.py`:
```python
class ScoreResponse(BaseModel):
    ticker: str
    composite_score: float
    conviction: str
    # ... existing fields ...
    market_cap: float | None = None  # New
```

Populate from `AssetProfile.market_cap` when constructing response.

### Files to Create/Modify

| File | Change |
|------|--------|
| `api/src/margin_api/routes/sectors.py` | New sector endpoints |
| `api/src/margin_api/schemas/scores.py` | Add market_cap field |
| `api/src/margin_api/routes/scores.py` | Populate market_cap from profile |
| `api/src/margin_api/app.py` | Register sectors router |

### Test Strategy

- Test `/sectors` returns all 11 GICS sectors
- Test `/sectors/Technology/champion` returns highest-scored tech stock
- Test `market_cap` present on ScoreResponse
- Test empty sector (no scored assets) → 404 or empty response
