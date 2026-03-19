# Tier E Governance Chain Plan

> Use superpowers:subagent-driven-development to implement.

**Goal:** Replace insecure admin key with proper auth, add config CRUD, build webhook notifications.

**Architecture:** E3 establishes admin authentication. E1 adds config CRUD. E2 adds webhooks.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, PyJWT, ARQ, Next.js 16, aiosqlite

**Spec:** See `docs/superpowers/specs/2026-03-18-tier-e-known-gaps-design.md` (Track A)

**IMPORTANT note on JWT keys:** The existing `_verify_jwt_token()` in `deps.py` uses `settings.service_auth_secret` for Next.js-to-API auth. Admin JWTs use `settings.jwt_secret` instead. These are DIFFERENT keys. A new `_verify_admin_jwt()` function is needed.

---

## File Map

### E3: Admin Auth

| File | Action | Responsibility |
|------|--------|----------------|
| `api/src/margin_api/db/models.py` | Modify | Add `UserRole` enum, `role` column to `User` |
| `api/alembic/versions/xxx_add_user_role.py` | Create | Migration for role column |
| `api/src/margin_api/deps.py` | Modify | Add `_verify_admin_jwt()`, `get_admin_user()`, `get_superadmin_user()` |
| `api/src/margin_api/routes/auth.py` | Modify | Add `admin-login` endpoint |
| `api/src/margin_api/schemas/auth.py` | Modify | Add login request/response schemas |
| `api/src/margin_api/routes/admin.py` | Modify | Replace old admin key check with new dependency |
| `api/src/margin_api/routes/governance.py` | Modify | Replace old admin key check with new dependency |
| `api/src/margin_api/app.py` | Modify | Remove `X-Admin-Key` from CORS headers |
| `web/src/proxy.ts` | Modify | Add admin cookie check for `/admin/*` routes |
| `web/src/app/admin/login/page.tsx` | Create | Admin login form (client component) |
| `web/src/app/admin/approvals/page.tsx` | Modify | Convert to server component |
| `web/src/app/admin/model-validation/page.tsx` | Modify | Convert to server component |
| `web/src/app/admin/events/page.tsx` | Modify | Convert to server component |

### E1: Governance Config CRUD

| File | Action | Responsibility |
|------|--------|----------------|
| `api/src/margin_api/services/governance_config.py` | Create | Config registry, validation, `get_threshold()` |
| `api/src/margin_api/schemas/governance.py` | Modify | Add config schemas |
| `api/src/margin_api/routes/admin_governance_config.py` | Create | CRUD endpoints |
| `api/src/margin_api/app.py` | Modify | Register new router |
| `api/src/margin_api/workers.py` | Modify | Replace hardcoded thresholds |

### E2: Webhook Notifications

| File | Action | Responsibility |
|------|--------|----------------|
| `api/src/margin_api/db/models.py` | Modify | Add `WebhookSubscription`, `WebhookDelivery` models |
| `api/alembic/versions/xxx_add_webhook_tables.py` | Create | Migration |
| `api/src/margin_api/schemas/webhooks.py` | Create | Pydantic schemas |
| `api/src/margin_api/services/webhook_dispatcher.py` | Create | Dispatch + delivery service |
| `api/src/margin_api/routes/admin_webhooks.py` | Create | Admin CRUD endpoints |
| `api/src/margin_api/app.py` | Modify | Register webhook router |
| `api/src/margin_api/workers.py` | Modify | Add `deliver_webhook` ARQ func, wire dispatch |

---

## E3: Admin Auth & Role System

### Task 1: Add UserRole enum and role column

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Create: `api/alembic/versions/xxx_add_user_role.py`

- [ ] **Step 1: Add UserRole enum and role column to User model**

Add `UserRole(str, PyEnum)` with values USER, ADMIN, SUPERADMIN. Add `role: Mapped[str] = mapped_column(String(20), default=UserRole.USER)` to User model after `subscription_plan`.

- [ ] **Step 2: Create Alembic migration**

Run: `uv run alembic revision --autogenerate -m "add_user_role_column"`
Verify: adds role column with `server_default="user"`. Add idempotent check.

- [ ] **Step 3: Apply and verify single head**

Run: `uv run alembic upgrade head && uv run alembic heads`

- [ ] **Step 4: Commit**

`git commit -m "feat(auth): add UserRole enum and role column to User model"`

---

### Task 2: Add admin JWT verification and dependencies

**Files:**
- Modify: `api/src/margin_api/deps.py`
- Create: `api/tests/test_admin_deps.py`

- [ ] **Step 1: Write failing tests for _verify_admin_jwt**

Create `api/tests/test_admin_deps.py`. Tests: valid admin JWT returns (user_id, role), valid superadmin returns correct role, expired JWT raises 401, wrong signing key raises 401, missing role claim raises 401. Use `pyjwt.encode()` with a fake test key to create JWTs.

- [ ] **Step 2: Verify tests fail**

Run: `uv run pytest api/tests/test_admin_deps.py -v` — FAIL expected

- [ ] **Step 3: Implement _verify_admin_jwt**

Add to `deps.py` after `_verify_jwt_token()`. Signature: `_verify_admin_jwt(token: str, settings: Settings) -> tuple[int, str]`. Reads `settings.jwt_secret` internally (NOT `service_auth_secret`). Requires JWT claims: sub, exp, iat, role. Tests should create a `Settings` instance with a known `jwt_secret` value.

- [ ] **Step 4: Verify tests pass**

Run: `uv run pytest api/tests/test_admin_deps.py -v`

- [ ] **Step 5: Add get_admin_user and get_superadmin_user**

Both read `request.cookies.get("admin_session")`, call `_verify_admin_jwt()`, load User from DB, verify role. Add `Request` to imports.

- [ ] **Step 6: Commit**

`git commit -m "feat(auth): add admin JWT verification and role-based dependencies"`

---

### Task 3: Add admin-login endpoint

**Files:**
- Modify: `api/src/margin_api/routes/auth.py`
- Modify: `api/src/margin_api/schemas/auth.py`
- Create: `api/tests/routes/test_admin_auth.py`

- [ ] **Step 1: Write failing tests**

Create `api/tests/routes/test_admin_auth.py`. Fixtures create admin and regular users. Tests: valid admin creds -> 200 with MFA challenge, wrong creds -> 401, regular user -> 403, nonexistent email -> 401.

- [ ] **Step 2: Verify tests fail**

Run: `uv run pytest api/tests/routes/test_admin_auth.py -v`

- [ ] **Step 3: Add schemas and implement endpoint**

Add `AdminLoginRequest` and `AdminLoginResponse` schemas. Implement `POST /api/v1/auth/admin-login`: lookup user by email, verify with argon2, check role is admin/superadmin (403 if not). MFA is **mandatory** for admin roles per spec — always return challenge JWT requiring MFA completion. No bypass path for non-MFA admins (enforce MFA enrollment at account setup). After MFA completion, set httpOnly cookie `admin_session`. Rate limit 5/min. Add test for full two-step flow: admin-login -> challenge -> mfa-complete -> cookie set.

- [ ] **Step 4: Verify tests pass**

- [ ] **Step 5: Commit**

`git commit -m "feat(auth): add admin-login endpoint with MFA requirement"`

---

### Task 4: Replace old admin key check with new dependency

**Files:**
- Modify: `api/src/margin_api/routes/governance.py`
- Modify: `api/src/margin_api/routes/admin.py`
- Modify: `api/src/margin_api/app.py`

- [ ] **Step 1: Update governance.py**

Replace import of `_verify_admin_key` with `get_admin_user` from deps. Replace all `Depends(_verify_admin_key)` with `admin_user: User = Depends(get_admin_user)`.

- [ ] **Step 2: Update admin.py**

Same replacement. Mark old function as DEPRECATED.

- [ ] **Step 3: Remove X-Admin-Key from CORS headers in app.py**

- [ ] **Step 4: Run existing tests, fix broken fixtures**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py -x`

- [ ] **Step 5: Commit**

`git commit -m "refactor(auth): replace _verify_admin_key with get_admin_user"`

---

### Task 5: Refactor proxy.ts for admin route protection

**Files:**
- Modify: `web/src/proxy.ts`

- [ ] **Step 1: Refactor from re-export to custom middleware**

Current file re-exports NextAuth `auth`. Refactor to handle both: regular sessions (delegate to auth) for existing routes, and admin cookie check for `/admin/*` (except `/admin/login`). Add `/admin/:path*` to matcher. See spec E3 Middleware section.

- [ ] **Step 2: Verify build**

Run: `cd web && npx next build`

- [ ] **Step 3: Commit**

`git commit -m "feat(auth): add admin route protection to proxy.ts"`

---

### Task 6: Create admin login page

**Files:**
- Create: `web/src/app/admin/login/page.tsx`
- Create: `web/src/app/admin/login/__tests__/page.test.tsx`

- [ ] **Step 1: Create login page**

Client component with two-step form: email/creds -> API call, then TOTP if MFA required. Use zinc design tokens matching admin aesthetic.

- [ ] **Step 2: Write and run component test**

Run: `cd web && npx vitest run src/app/admin/login`

- [ ] **Step 3: Commit**

`git commit -m "feat(auth): add admin login page with MFA flow"`

---

### Task 7: Convert admin pages to server components

**Files:**
- Modify: `web/src/app/admin/approvals/page.tsx`
- Modify: `web/src/app/admin/model-validation/page.tsx`
- Modify: `web/src/app/admin/governance-events/page.tsx`

- [ ] **Step 1: Read current admin pages**

- [ ] **Step 2: Convert to server components**

Remove client directive, replace admin key header usage with `serverFetch()` + forwarded cookie. Extract interactive parts to client sub-components.

- [ ] **Step 3: Remove NEXT_PUBLIC_ADMIN_KEY from .env**

- [ ] **Step 4: Run web tests**

Run: `cd web && npx vitest run`

- [ ] **Step 5: Commit**

`git commit -m "refactor(auth): convert admin pages to server components, remove NEXT_PUBLIC_ADMIN_KEY"`

---

## E1: GovernanceConfig CRUD

### Task 8: Implement config registry and validation service

**Files:**
- Create: `api/src/margin_api/services/governance_config.py`
- Create: `api/tests/services/test_governance_config.py`

- [ ] **Step 1: Write failing tests**

Tests for `validate_config_value()`: known key + valid value -> no errors, out-of-range -> error, wrong type -> error, unknown key -> error, missing field -> error, all registry defaults pass validation.

- [ ] **Step 2: Verify tests fail**

- [ ] **Step 3: Implement service**

`CONFIG_REGISTRY` with 3 circuit breaker keys and their thresholds/ranges. `validate_config_value()` rejects unknowns, validates types and ranges. `get_threshold(session, key)` reads DB with fallback.

- [ ] **Step 4: Verify tests pass**

- [ ] **Step 5: Commit**

`git commit -m "feat(governance): add config registry with typed validation"`

---

### Task 9: Add governance config CRUD endpoints

**Files:**
- Modify: `api/src/margin_api/schemas/governance.py`
- Create: `api/src/margin_api/routes/admin_governance_config.py`
- Modify: `api/src/margin_api/app.py`
- Create: `api/tests/routes/test_admin_governance_config.py`

- [ ] **Step 1: Write failing tests**

CRUD tests: list returns defaults, get shows `is_default=True`, upsert creates audit event, invalid value -> 422, unknown key -> 422, delete reverts to default.

- [ ] **Step 2: Add schemas**

`GovernanceConfigResponse`, `GovernanceConfigUpdate`, `GovernanceConfigListResponse`.

- [ ] **Step 3: Implement CRUD route**

Prefix `/api/v1/admin/governance-config`. All use `Depends(get_superadmin_user)`. GET list merges DB with registry. PUT validates then upserts + logs `config.updated` governance event. DELETE removes override + logs `config.deleted`.

**Note:** This creates `admin_governance_config.py` which is a SEPARATE router from the existing `governance.py` (which handles approvals/events). When registering in `app.py`, import as `governance_config_router` to avoid collision with existing `governance_router`.

- [ ] **Step 4: Register router in app.py**

- [ ] **Step 5: Verify tests pass**

- [ ] **Step 6: Commit**

`git commit -m "feat(governance): add governance config CRUD with audit trail"`

---

### Task 10: Wire get_threshold into workers

**Files:**
- Modify: `api/src/margin_api/workers.py`

- [ ] **Step 1: Find circuit breaker call sites**

Search for `check_score_drift`, `check_ingestion_failure_rate`, `check_ml_regression`.

- [ ] **Step 2: Replace hardcoded thresholds**

Import `get_threshold`. At each call site, fetch threshold first:

For async `check_score_drift`: `drift_threshold = await get_threshold(session, "circuit_breaker.score_drift")` then pass as `threshold_pct`.

For sync functions: same pattern, `await get_threshold()` first, pass float to sync function.

- [ ] **Step 3: Run worker tests**

- [ ] **Step 4: Commit**

`git commit -m "feat(governance): wire dynamic config thresholds into workers"`

---

## E2: Webhook Notifications

### Task 11: Add webhook ORM models and migration

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Create: `api/alembic/versions/xxx_add_webhook_tables.py`

- [ ] **Step 1: Add models**

`WebhookSubscription` and `WebhookDelivery`. Follow existing patterns: Mapped annotations, DateTime(timezone=True), JSONVariant, lambda defaults. HMAC key stored encrypted (`hmac_secret_encrypted`). UniqueConstraint on (event_type, url). See spec E2 for complete definitions.

- [ ] **Step 2: Generate and apply migration**

- [ ] **Step 3: Commit**

`git commit -m "feat(webhooks): add WebhookSubscription and WebhookDelivery models"`

---

### Task 12: Implement webhook dispatcher service

**Files:**
- Create: `api/src/margin_api/services/webhook_dispatcher.py`
- Create: `api/tests/services/test_webhook_dispatcher.py`

- [ ] **Step 1: Write failing tests for HMAC signing**

Tests: sign produces 64-char hex, deterministic, different keys differ.

- [ ] **Step 2: Implement dispatcher**

`WebhookDispatcher` class: `_sign_payload()` (HMAC-SHA256), `dispatch()` (create delivery rows), `deliver()` (attempt delivery with httpx, 10s timeout, retry logic, dead_letter after 5 failures). Constants: MAX_ATTEMPTS=5, BACKOFF_SECONDS=[0,1,10,60,300].

- [ ] **Step 3: Verify tests pass**

- [ ] **Step 4: Commit**

`git commit -m "feat(webhooks): implement dispatcher with HMAC signing and delivery tracking"`

---

### Task 13: Add webhook admin CRUD endpoints

**Files:**
- Create: `api/src/margin_api/schemas/webhooks.py`
- Create: `api/src/margin_api/routes/admin_webhooks.py`
- Modify: `api/src/margin_api/app.py`
- Create: `api/tests/routes/test_admin_webhooks.py`

- [ ] **Step 1: Write failing tests**

Create, list, delete, duplicate rejection (409), unauthorized (401), delivery history.

- [ ] **Step 2: Create schemas**

Request/response models for subscription CRUD and delivery listing.

- [ ] **Step 3: Implement routes**

Prefix `/api/v1/admin/webhooks`. All require `get_admin_user`. POST generates HMAC key, encrypts with TotpService pattern, returns plaintext once. Validates event_type against allowed set.

- [ ] **Step 4: Register router, run tests**

- [ ] **Step 5: Commit**

`git commit -m "feat(webhooks): add webhook subscription admin CRUD endpoints"`

---

### Task 14: Add deliver_webhook ARQ function and wire dispatch

**Files:**
- Modify: `api/src/margin_api/workers.py`

- [ ] **Step 1: Add deliver_webhook ARQ function**

Calls `dispatcher.deliver()`, on failure enqueues retry with backoff.

- [ ] **Step 2: Register in WorkerSettings.functions**

- [ ] **Step 3: Wire dispatch into governance workers**

In `_stage_scores_impl`: dispatch `"score.staged"` after approval creation. In `publish_scores`: dispatch `"score.published"`. In `promote_ml_model`: dispatch `"model.promoted"`. At each circuit breaker trip point (where `check_score_drift`, `check_ingestion_failure_rate`, or `check_ml_regression` returns `triggered=True`): dispatch `"circuit_breaker.tripped"`. Pattern: create dispatcher, call dispatch(), enqueue deliver jobs via redis.

- [ ] **Step 4: Run worker tests**

- [ ] **Step 5: Commit**

`git commit -m "feat(webhooks): wire webhook dispatch into governance workers"`

---

### Task 15: Final validation

- [ ] **Step 1: Run full API tests**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`

- [ ] **Step 2: Run linter**

Run: `uv run ruff check --fix api/ && uv run ruff format api/`

- [ ] **Step 3: Run web tests**

Run: `cd web && npx vitest run`

- [ ] **Step 4: Commit any fixes**

`git commit -m "style: lint fixes for governance chain"`
