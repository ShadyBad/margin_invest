# Tier E: Pre-Existing Known Gaps — Design Spec

Technical design for 7 items addressing known gaps from earlier feature work.
Organized into 4 parallel tracks by dependency.

---

## Track Structure

```
Track A (Governance Chain):  E3 → E1 → E2
Track B (Data Endpoints):    E5 + E7 (independent, parallel)
Track C (Quick Standalone):  E4
Track D (Coverage Campaign): E6 (runs last, covers all new code)
```

**Decisions applied across all items:**
- All admin actions require authenticated admin user (E3 establishes this)
- Governance events logged for all state-changing admin operations
- Published scores are the canonical data source for user-facing endpoints

---

## Track A: Governance Chain

### E3: Admin Auth & Role System

**Problem:** `NEXT_PUBLIC_ADMIN_KEY` is bundled into client JavaScript — anyone can extract
the admin key from browser DevTools. Three admin pages expose this key.

**Design Decision:** Replace shared key with proper user authentication using role-based
access. Role enum (`user`, `admin`, `superadmin`) provides tiered privileges.

#### DB Changes

Add `role` column to existing `User` model:

```python
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

# On User model:
role: Mapped[str] = mapped_column(String, default=UserRole.USER)
```

No new tables — reuses existing `User` model with `password_hash` and `mfa_enabled`.

#### Auth Flow

The existing auth flow uses a two-step challenge-token MFA flow: `verify-credentials` →
`mfa/complete` → session cookie. Admin login **must** follow the same MFA path — admin
accounts with elevated privileges must not have weaker auth than regular users.

1. **`POST /api/v1/auth/admin-login`** — validates credentials against `User.password_hash`,
   checks `role in ("admin", "superadmin")`. MFA is **mandatory** for admin/superadmin roles
   — returns challenge token requiring `mfa/complete` as with regular login. On successful
   MFA completion, issues a JWT with `role` claim signed with `settings.jwt_secret` (same
   key used by `mfa_complete` and `verify_mfa_token` in `routes/auth.py`). The JWT is set
   as an httpOnly cookie named `admin_session`.

   **Key distinction:** The existing `_verify_jwt_token()` in `deps.py` uses
   `settings.service_auth_secret` (for Next.js→API inter-service auth). Admin JWTs are
   signed with `settings.jwt_secret` (the user-facing JWT key). These are different keys.
   A new `_verify_admin_jwt(token, settings) -> tuple[int, str]` function is needed in
   `deps.py` that decodes with `jwt_secret` and returns `(user_id, role)`.

2. **`get_admin_user(request: Request, session) -> User`** — FastAPI dependency that reads
   `request.cookies.get("admin_session")`, calls `_verify_admin_jwt()` to extract user ID
   and role, loads the `User` from DB, and verifies `role in ("admin", "superadmin")`.
   Replaces `_verify_admin_key()` in all admin routes.
3. **`get_superadmin_user(request: Request, session) -> User`** — same but requires
   `superadmin` role. Used for governance config changes (E1).

#### Frontend Changes

- New `/admin/login` page (client component — needs form interactivity)
- All 3 admin pages (`approvals`, `model-validation`, `governance-events`) become server
  components using `serverFetch()` with session cookie
- Admin mutations (approve, reject) use server actions that pass cookie server-side
- Remove `NEXT_PUBLIC_ADMIN_KEY` from `.env` entirely

#### Middleware

The current `web/src/proxy.ts` re-exports the NextAuth `auth` handler and matches only
`/dashboard`, `/account`, `/settings`, `/backtesting`. It must be refactored from a
simple re-export into a custom middleware function that handles both:

1. **Regular session checks** — delegate to existing `auth` handler for existing routes
2. **Admin cookie checks** — for `/admin/*` routes, read the `admin_session` httpOnly
   cookie and redirect to `/admin/login` if missing or invalid

Add `/admin/:path*` to the matcher array. The admin login page itself (`/admin/login`)
must be excluded from the check to avoid redirect loops.

#### Files to Create/Modify

| File | Change |
|------|--------|
| `api/src/margin_api/db/models.py` | Add `role` column to `User`, `UserRole` enum |
| `api/alembic/versions/xxx_add_user_role.py` | Migration: add role column with default "user" |
| `api/src/margin_api/routes/auth.py` | New `admin-login` endpoint |
| `api/src/margin_api/deps.py` | `get_admin_user`, `get_superadmin_user` dependencies; extend `_verify_jwt_token()` to extract `role` claim |
| `api/src/margin_api/routes/governance.py` | Replace `_verify_admin_key()` with `get_admin_user` |
| `web/src/app/admin/login/page.tsx` | New admin login page |
| `web/src/app/admin/approvals/page.tsx` | Convert to server component |
| `web/src/app/admin/model-validation/page.tsx` | Convert to server component |
| `web/src/app/admin/governance-events/page.tsx` | Convert to server component |
| `web/.env` | Remove `NEXT_PUBLIC_ADMIN_KEY` |
| `web/src/proxy.ts` | Add `/admin/:path*` to matcher; check admin session cookie, redirect to `/admin/login` if missing |

#### Test Strategy

- Auth tests: valid credentials + admin role → JWT issued
- Auth tests: valid credentials + user role → 403
- Auth tests: invalid credentials → 401
- Dependency tests: valid JWT → user returned; expired JWT → 401; wrong role → 403
- Frontend: admin pages redirect to `/admin/login` without session
- Frontend: `NEXT_PUBLIC_ADMIN_KEY` absent from JS bundle (build + inspect)

---

### E1: GovernanceConfig CRUD with Typed Validation

**Problem:** `GovernanceConfig` ORM model exists but has no CRUD endpoints. Circuit breaker
thresholds are hardcoded in worker code.

**Design Decisions:**
- Typed per-key validation via a config registry
- All config changes audited to `governance_events` with before/after values
- Requires `superadmin` role (via E3)

#### Config Key Registry

```python
@dataclass
class ConfigKeySpec:
    description: str
    schema: dict[str, tuple[type, Any, Any]]  # field_name -> (type, min, max)
    default: dict

CONFIG_REGISTRY: dict[str, ConfigKeySpec] = {
    "circuit_breaker.score_drift": ConfigKeySpec(
        description="Max allowed score drift percentage before blocking publish",
        schema={"threshold": (float, 0.0, 100.0)},
        default={"threshold": 30.0},
    ),
    "circuit_breaker.ingestion_failure": ConfigKeySpec(
        description="Max allowed ingestion failure rate",
        schema={"threshold": (float, 0.0, 100.0)},
        default={"threshold": 20.0},
    ),
    "circuit_breaker.ml_regression": ConfigKeySpec(
        description="Max allowed ML regression percentage",
        schema={"threshold": (float, 0.0, 100.0)},
        default={"threshold": 50.0},
    ),
}
```

Validation rejects unknown keys and validates value types/ranges against the spec.

#### Endpoints

All require `superadmin` role.

- **`GET /admin/governance-config`** — list all configs, merging DB values with registry
  defaults for unset keys
- **`GET /admin/governance-config/{key}`** — single key, returns DB value or registry default
- **`PUT /admin/governance-config/{key}`** — validate against registry, upsert, log
  `config.updated` to `governance_events` with before/after values and `user_id`
- **`DELETE /admin/governance-config/{key}`** — remove override (reverts to registry default),
  log `config.deleted` to `governance_events`

#### Schemas

```python
class GovernanceConfigResponse(BaseModel):
    config_key: str
    config_value: dict
    description: str
    is_default: bool  # True if no DB override exists
    updated_at: datetime | None

class GovernanceConfigUpdate(BaseModel):
    config_value: dict  # Validated against CONFIG_REGISTRY[key].schema

class GovernanceConfigListResponse(BaseModel):
    configs: list[GovernanceConfigResponse]
```

#### Worker Integration

The existing circuit breaker functions in `services/circuit_breaker.py` are a mix of
async (`check_score_drift` takes a `session`) and sync (`check_ingestion_failure_rate`,
`check_ml_regression` are pure functions taking primitive args). All accept a
`threshold_pct` parameter with hardcoded defaults.

**Wiring pattern:** Workers call async `get_threshold()` first, then pass the result
to the circuit breaker function. The circuit breaker functions themselves are NOT modified —
they remain pure and testable. Only the call sites in `workers.py` change.

```python
# In services/governance_config.py:
async def get_threshold(session: AsyncSession, key: str) -> float:
    config = await session.execute(
        select(GovernanceConfig).where(GovernanceConfig.config_key == key)
    )
    row = config.scalar_one_or_none()
    if row and row.config_value:
        return row.config_value.get("threshold", CONFIG_REGISTRY[key].default["threshold"])
    return CONFIG_REGISTRY[key].default["threshold"]

# In workers.py (call site):
drift_threshold = await get_threshold(session, "circuit_breaker.score_drift")
result = await check_score_drift(session, scored_at, threshold_pct=drift_threshold)

# For sync functions:
ingest_threshold = await get_threshold(session, "circuit_breaker.ingestion_failure")
result = check_ingestion_failure_rate(failed, total, threshold_pct=ingest_threshold)
```

#### Files to Create/Modify

| File | Change |
|------|--------|
| `api/src/margin_api/routes/admin_governance.py` | New CRUD endpoints |
| `api/src/margin_api/schemas/governance.py` | New Pydantic schemas |
| `api/src/margin_api/services/governance_config.py` | Config registry, validation, `get_threshold()` |
| `api/src/margin_api/app.py` | Register new router |
| `api/src/margin_api/workers.py` (circuit breaker sections) | Replace hardcoded thresholds |

#### Test Strategy

- CRUD: create, read, update, delete config entries
- Upsert semantics: PUT to existing key updates, PUT to new key creates
- Validation: reject unknown keys, reject out-of-range values, reject wrong types
- Audit: config change → `governance_events` row with before/after
- Worker integration: mock config row → verify threshold used; missing config → fallback default
- Auth: `admin` role → 403 on config endpoints; `superadmin` → 200

---

### E2: Webhook Notifications with Delivery Tracking

**Problem:** No notification system for governance events. External systems cannot subscribe
to score staging, model promotions, or circuit breaker trips.

**Design Decisions:**
- Internal consumers first, extensible for external later
- Full delivery tracking: `webhook_deliveries` table, ARQ-based retries, dead letter
- HMAC-SHA256 signing per subscription

#### New DB Tables

ORM models following codebase conventions (SQLAlchemy 2.0 `Mapped` style, `DateTime(timezone=True)`):

```python
class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"
    __table_args__ = (UniqueConstraint("event_type", "url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    url: Mapped[str] = mapped_column(String)
    hmac_secret_encrypted: Mapped[str] = mapped_column(String)  # Encrypted at rest
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("webhook_subscriptions.id"), index=True)
    event_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSONVariant)  # JSON/JSONB
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, delivered, failed, dead_letter
    attempts: Mapped[int] = mapped_column(default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status_code: Mapped[int | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

**hmac_secret encryption:** The codebase already encrypts TOTP secrets via `TotpService`
with `settings.encryption_key`. Webhook HMAC secrets use the same encryption pattern —
stored as `hmac_secret_encrypted` and decrypted at dispatch time. The secret is returned
in plaintext only once (on creation) so the subscriber can configure their receiver.

#### Event Types

- `score.staged` — new scores ready for review
- `score.approved` — scores approved by admin
- `score.published` — scores published to users
- `model.promoted` — ML model promoted to production
- `circuit_breaker.tripped` — circuit breaker activated
- `config.updated` — governance config changed (from E1)

#### Dispatcher Service

`api/src/margin_api/services/webhook_dispatcher.py`:

```python
class WebhookDispatcher:
    async def dispatch(self, session: AsyncSession, event_type: str, payload: dict):
        """Create webhook_deliveries rows for all active subscribers matching
        event_type, then enqueue ARQ deliver_webhook jobs for each."""

    async def deliver(self, session: AsyncSession, delivery_id: int):
        """Execute a single delivery attempt:
        - Sign payload with HMAC-SHA256 using subscription's hmac_secret
        - POST to subscription URL with X-Margin-Signature header, 10s timeout
        - On 2xx: status='delivered', delivered_at=now
        - On failure: increment attempts, schedule retry via ARQ with backoff
        - After 5 failed attempts: status='dead_letter', log to governance_events
        """

    def _sign_payload(self, payload: bytes, secret: str) -> str:
        """HMAC-SHA256 hex digest."""
```

#### Retry Strategy

ARQ-based async retries with exponential backoff:
- Attempt 1: immediate
- Attempt 2: +1s
- Attempt 3: +10s
- Attempt 4: +60s
- Attempt 5: +300s

After 5 failures → `dead_letter` status, governance event logged.

New ARQ function: `deliver_webhook(ctx, delivery_id: int)`.

#### Admin Endpoints

All require `admin` role:

- **`GET /admin/webhooks`** — list all subscriptions
- **`POST /admin/webhooks`** — create subscription (server generates `hmac_secret`, returns it once)
- **`DELETE /admin/webhooks/{id}`** — remove subscription
- **`POST /admin/webhooks/{id}/test`** — send test payload, return delivery result
- **`GET /admin/webhooks/{id}/deliveries`** — paginated delivery history

#### Integration Points

One-liner additions to existing workers:

```python
# In stage_scores worker:
await webhook_dispatcher.dispatch(session, "score.staged", {"tickers": [...], "count": n})

# In publish_scores worker:
await webhook_dispatcher.dispatch(session, "score.published", {"tickers": [...], "count": n})

# In promote_ml_model worker:
await webhook_dispatcher.dispatch(session, "model.promoted", {"model_id": ..., "ic": ...})

# In circuit breaker checks:
await webhook_dispatcher.dispatch(session, "circuit_breaker.tripped", {"breaker": key, "value": v})
```

#### Files to Create/Modify

| File | Change |
|------|--------|
| `api/src/margin_api/db/models.py` | `WebhookSubscription`, `WebhookDelivery` models |
| `api/alembic/versions/xxx_add_webhook_tables.py` | Migration |
| `api/src/margin_api/services/webhook_dispatcher.py` | Dispatch + delivery service |
| `api/src/margin_api/routes/admin_webhooks.py` | Admin CRUD endpoints |
| `api/src/margin_api/schemas/webhooks.py` | Pydantic schemas |
| `api/src/margin_api/app.py` | Register webhook router |
| `api/src/margin_api/workers.py` | Add `deliver_webhook` ARQ function, wire dispatch calls |

#### Test Strategy

- HMAC: signature generation and verification round-trip
- Retry: mock HTTP failures → verify backoff schedule and attempt counting
- Dead letter: 5 failures → status transitions to dead_letter
- Integration: `stage_scores` → delivery row created for active subscriber
- Inactive subscription: `is_active=False` → skipped during dispatch
- Test endpoint: `POST /admin/webhooks/{id}/test` → delivery attempted and result returned
- Auth: `admin` role can manage subscriptions; `user` role → 403

---

## Track B: Data Endpoints

### E5: 13F Analytics — New Positions & Crowded Trades

**Problem:** Two analytics endpoints return empty arrays. Quarter-over-quarter comparison
logic was deferred during 13F pipeline implementation.

**Design Decision:** Auto-detect quarters by default, optional `?quarter=` override.

#### Existing Schema Conflicts

The existing `schemas/thirteenf.py` defines schemas that will be **replaced** by this work:

- `NewPositionEntry` (ticker, managers, total_new_funds, curated_new_funds, total_value_millions)
  → fields updated to reflect quarter-comparison semantics
- `NewPositionResponse` (period_of_report, new_positions)
  → adds `previous_quarter: date` field
- `CrowdedTrade` (ticker, new_position_count, pct_funds_adding)
  → replaced with holder-based fields (holder_count, concentration_pct, total_value_millions)
- `OverlapEntry` (ticker, holder_count, curated_count) → field definitions unchanged
- `OverlapResponse` (period_of_report, most_held, crowded_trades)
  → adds `total_managers: int` field; `crowded_trades` element type changes to match new `CrowdedTrade`

**This is a breaking API change** affecting 5 schemas. The Smart Money page frontend
(`/smart-money`) must be updated to consume the new response shapes. Since these endpoints
currently return empty arrays, no real data flows through them — the frontend is already
handling the empty case. The breaking change is safe because the old schemas never carried
real data.

#### Data Source

All queries target the `institutional_holdings` table (ORM: `InstitutionalHolding`), NOT
`thirteen_f_holdings` (which does not exist). The table is joined to `Manager` for names
and `SecurityMaster` for ticker resolution.

#### Plan Gating

Both endpoints use `Depends(require_plan("institutional"))` which returns the authenticated
`user_id`. This dependency **must be preserved** — it gates these endpoints to users on
paid plans. The new `quarter` query parameter is added alongside the existing dependency.

#### Quarter Resolution

New service file `api/src/margin_api/services/thirteenf_analytics.py` (NOT in
`accumulation_service.py` which uses a class-based `AccumulationService` pattern for a
different concern):

```python
async def get_available_quarters(session: AsyncSession) -> list[date]:
    """Return distinct period_of_report dates from institutional_holdings,
    ordered most recent first."""

async def resolve_quarter(
    session: AsyncSession, quarter: str | None
) -> tuple[date, date]:
    """If quarter param provided (e.g., '2026-Q1'), parse to period_of_report date
    and find the preceding quarter. If None, auto-detect from the two most recent
    period_of_report dates. Raises 404 if fewer than 2 quarters available."""
```

Quarter string format: `YYYY-QN` (e.g., `2026-Q1` → `2026-03-31`).

#### New Positions Endpoint

`GET /analytics/new-positions?quarter=2026-Q1` (quarter optional, plan-gated):

```python
async def compute_new_positions(
    session: AsyncSession, current_q: date, prev_q: date
) -> list[NewPositionEntry]:
    """
    1. Query all (manager_id, security_master_id) pairs from institutional_holdings for current quarter
    2. Query same for previous quarter
    3. For each ticker: find managers present in current but absent in previous
    4. Aggregate: new manager count, total new shares, total new value
    5. Return sorted by manager count descending, limit 50
    """
```

**Updated schemas** (replace existing in `schemas/thirteenf.py`):

```python
class NewPositionEntry(BaseModel):
    """A ticker with new institutional positions this quarter."""
    ticker: str
    managers: list[str]           # Up to 10 manager names (renamed from top_managers for consistency)
    total_new_funds: int          # Count of managers initiating new positions
    curated_new_funds: int        # Count among curated managers only
    total_value_millions: float   # Total new position value in $M

class NewPositionResponse(BaseModel):
    period_of_report: date        # Current quarter (keep existing field name)
    previous_quarter: date        # Comparison quarter (new field)
    new_positions: list[NewPositionEntry]
```

#### Crowded Trades Endpoint

`GET /analytics/overlap?quarter=2026-Q1` (quarter optional, plan-gated):

```python
async def compute_crowded_trades(
    session: AsyncSession, quarter: date
) -> tuple[list[OverlapEntry], list[CrowdedTrade]]:
    """
    1. Count distinct managers per ticker for the quarter
    2. most_held: top 20 by raw holder_count (OverlapEntry)
    3. crowded_trades: top 20 by concentration metrics (CrowdedTrade)
    """
```

**Updated schemas** (replace existing in `schemas/thirteenf.py`):

```python
class OverlapEntry(BaseModel):
    """A ticker held by many institutional managers."""
    ticker: str
    holder_count: int             # Total managers holding this ticker
    curated_count: int            # Among curated managers only

class CrowdedTrade(BaseModel):
    """A ticker with high concentration risk."""
    ticker: str
    holder_count: int             # Total managers holding
    concentration_pct: float      # holder_count / total_managers in universe
    total_value_millions: float   # Total held value in $M

class OverlapResponse(BaseModel):
    period_of_report: date
    total_managers: int           # New field: total managers in universe for concentration calc
    most_held: list[OverlapEntry]
    crowded_trades: list[CrowdedTrade]
```

#### Performance

Queries scan `institutional_holdings` (217K+ rows). Both queries use GROUP BY with
aggregate counts — straightforward indexed queries on `(period_of_report, security_master_id)`.
No materialized views needed unless performance becomes an issue.

#### Files to Modify

| File | Change |
|------|--------|
| `api/src/margin_api/routes/thirteenf.py` | Replace stubs with real logic, add `quarter` query param, preserve `require_plan` |
| `api/src/margin_api/services/thirteenf_analytics.py` | **New file**: `resolve_quarter`, `compute_new_positions`, `compute_crowded_trades` |
| `api/src/margin_api/schemas/thirteenf.py` | Update `NewPositionEntry`, `CrowdedTrade`, `OverlapEntry`, `OverlapResponse`, `NewPositionResponse` |
| `web/src/components/smart-money/` | Update any components consuming the changed response shapes |

#### Test Strategy

- 3 managers hold AAPL in Q2, only 1 in Q1 → 2 new positions reported
- Crowded trade ranking: ticker with most holders appears first
- Edge case: first quarter with no previous → 404 with clear message
- Edge case: explicit `?quarter=2025-Q3` → compares Q3 vs Q2
- Plan gating: unauthenticated user → 403; user without institutional plan → 403
- Integration: seed 2 quarters of test data in `institutional_holdings`, verify endpoint returns populated response
- Schema backward compat: verify `period_of_report` field still present on both responses

---

### E7: Sector Endpoints & market_cap Wiring

**Problem:** No sector listing or champion endpoints. `market_cap` field exists on
`ScoreResponse` schema but may not be populated in route handlers.

**Design Decision:** Published scores only for all sector endpoints.

#### Existing Code to Reuse

- **`services/sector_stats.py`** already exists with `compute_sector_filter_pass_rates()`
  and `compute_sector_distribution()` (P10/P50/P90). These handle per-sector statistics
  injected into V4Score detail JSONB. The new sector endpoints are a different concern
  (listing sectors with aggregate stats, identifying champions) but should live alongside
  this service or extend it.
- **`SectorChampionResponse`** already exists in `schemas/scores.py` (line 82) with fields
  `ticker: str` and `filter_values: dict[str, float | None]`. This is used inline in the
  per-ticker score response for the FailedComparison component. The new standalone champion
  endpoint needs a **different schema** — named `SectorChampionDetail` to avoid collision.
- **`routes/scores.py` line 701-733** already implements sector champion lookup inline
  (top 10 by composite_score). The new endpoint extracts and formalizes this pattern.

#### market_cap Wiring

- Audit `routes/scores.py` response construction
- If `market_cap` is not populated from `AssetProfile.market_cap`, add the lookup
- Single line change in the response builder

#### Sector Endpoints

New route file `routes/sectors.py`:

**`GET /sectors`** — list all sectors with summary stats:

```python
async def list_sectors(session: AsyncSession) -> list[SectorSummary]:
    """Query latest published scores grouped by GICS sector.
    For each sector: count assets, avg composite score, top ticker."""

class SectorSummary(BaseModel):
    sector: str
    asset_count: int
    avg_composite_score: float
    top_ticker: str
    top_score: float
```

**`GET /sectors/{sector}/champion`** — highest-scored ticker in a sector:

```python
async def get_sector_champion(sector: str, session: AsyncSession) -> SectorChampionDetail:
    """Query published scores where sector matches, order by composite_score desc,
    limit 1. Returns 404 if sector has no published scores.
    Reuses the query pattern from routes/scores.py:701-733."""

class SectorChampionDetail(BaseModel):
    """Standalone sector champion response. Distinct from SectorChampionResponse
    in schemas/scores.py which is embedded in per-ticker score responses."""
    ticker: str
    sector: str
    composite_score: float
    composite_tier: str
    signal: str
    market_cap: float | None
```

Data source: published scores joined to asset profile for sector and market_cap.

#### Files to Create/Modify

| File | Change |
|------|--------|
| `api/src/margin_api/routes/sectors.py` | New sector endpoints |
| `api/src/margin_api/schemas/sectors.py` | `SectorSummary`, `SectorChampionDetail` schemas |
| `api/src/margin_api/services/sector_stats.py` | Add sector listing/champion query functions alongside existing stats functions |
| `api/src/margin_api/routes/scores.py` | Wire `market_cap` if not already populated |
| `api/src/margin_api/app.py` | Register sectors router |

#### Test Strategy

- `/sectors` returns all GICS sectors that have published scores
- `/sectors/Technology/champion` returns highest-scored tech ticker
- `market_cap` present and non-null on ScoreResponse when AssetProfile has it
- Empty sector (no published scores) → 404
- Case handling: sector name matching (exact match vs case-insensitive)

---

## Track C: Quick Standalone

### E4: Backtesting Mock Data Audit

**Problem:** Backtesting components may use placeholder data as fallbacks. Initial
exploration found no hardcoded mock data in runtime code, but a formal audit is needed.

**Design Decision:** Lightweight audit-and-fix pass. Confirm no mock data, patch missing
loading/error states.

#### Audit Steps

1. Grep all 16 backtesting components for: `mockData`, `placeholder`, `PLACEHOLDER`, `TODO`,
   `hardcoded`, `sample`, `dummy`, `fake`, and inline array/object literals that look like
   test data
2. For each component, verify:
   - Loading state exists (skeleton or spinner) when data is undefined/null
   - Error state exists when API returns non-200
   - No default prop values that silently mask missing data
3. Fix any gaps — add `<Skeleton />` or error message components where missing
4. Document findings (even if clean) to formally close this gap

#### Files to Audit

All files in `web/src/components/backtesting/`:
- `stats-summary.tsx`, `knobs-panel.tsx`, `performance-chart.tsx`, `equity-curve.tsx`
- `validation-badges.tsx`, `returns-heatmap.tsx`, `snapshot-table.tsx`, `regime-cards.tsx`
- `factor-timeline.tsx`, `audit-log.tsx`, `failure-audit.tsx`, `shadow-section.tsx`
- `metrics-summary.tsx`, `cost-sensitivity.tsx`, `cost-disclosure.tsx`, `capacity-chart.tsx`

Plus `web/src/app/backtesting/page.tsx`.

#### Expected Outcome

0-3 small patches. Primary deliverable is the audit record confirming the gap is closed.

---

## Track D: Coverage Campaign

### E6: API Test Coverage — 90% Target

**Problem:** API test coverage was ~67% as of the original gap filing. CLAUDE.md target is
90%. Rarity worker has only 3 tests. No governance worker tests exist.

**Design Decision:** Full 90% coverage campaign — audit all uncovered code, systematic
test addition across the entire API module.

#### Phase 1: Coverage Audit

**Re-measure current baseline first** — the 67% figure may be stale. Tests have been added
since the original measurement. Run:

```bash
uv run pytest api/tests/ --cov=margin_api --cov-report=term-missing \
    --ignore=api/tests/services/test_xbrl_parser.py
```

Record the actual starting coverage percentage. Parse output to build a gap map: which
modules are below 90%, which lines are uncovered. This determines the true scope of work.

#### Phase 2: Prioritized Test Writing

| Priority | Module Area | Rationale |
|----------|------------|-----------|
| P0 | Governance workers (`stage_scores`, `publish_scores`, `promote_ml_model`, `expire_stale_approvals`) | Zero coverage, high-stakes pipeline |
| P0 | Circuit breaker logic | Thresholds moving to dynamic config (E1) — must be tested |
| P1 | Rarity worker (expand from 3 tests) | Percentile ranking, multi-ticker, regime classification |
| P1 | New code from E1-E5, E7 | All new endpoints and services need tests |
| P2 | Route handlers with low coverage | Score routes, admin routes, 13F routes |
| P2 | Services with uncovered branches | Accumulation service, ingest pipeline edge cases |
| P3 | Utility functions, schema validation | Lower risk but needed for 90% |

Test patterns follow existing conventions:
- `pytest-asyncio` + `aiosqlite` for async DB tests
- `fakeredis` for ARQ worker tests
- Factory fixtures from `conftest.py`
- Golden-value tests for scoring logic

#### Phase 3: Validation

Re-run coverage. Acceptance criteria:
- Overall API coverage ≥ 90%
- No individual module below 80%
- All P0 and P1 areas at 90%+

#### Scope Boundary

E6 runs last because it covers new code from E1-E5 and E7. Depends on all other tracks
being complete.

---

## Execution Order

```
Phase 1 (parallel):
  Track A: E3 (admin auth)
  Track B: E5 (13F analytics) + E7 (sector endpoints) — parallel within track
  Track C: E4 (backtesting audit)

Phase 2 (after E3):
  Track A: E1 (governance config CRUD)

Phase 3 (after E1):
  Track A: E2 (webhook notifications)

Phase 4 (after all above):
  Track D: E6 (coverage campaign)
```

## Effort Estimates

| Item | Original Estimate | Revised Estimate | Change Reason |
|------|------------------|-----------------|---------------|
| E1 | Small | Small | Added typed validation + audit, still contained |
| E2 | Medium | Medium-Large | Full delivery tracking, ARQ retries, dead letter |
| E3 | Small | Medium | Full auth flow replaces simple server component fix |
| E4 | Small | Small | Confirmed likely minimal patches |
| E5 | Medium | Medium | No change |
| E6 | Small | Large | Expanded from targeted tests to full 90% campaign |
| E7 | Small | Small | market_cap may already be wired |
