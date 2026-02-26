# Security Remediation Design

**Date:** 2026-02-25
**Status:** Approved
**Audit:** `docs/2026-02-25-security-audit.md`
**Scope:** 2 critical, 5 high, 8 medium findings across FastAPI API, Next.js frontend, and Python engine

---

## 1. Remediation Sequencing Strategy

Four phases organized by blast radius and dependency, not arbitrary severity.

### Phase 1 — Stop the Bleeding (CRITICAL-001 + CRITICAL-002 + quick wins)

| # | Finding | Action | Risk | Parallelizable |
|---|---------|--------|------|----------------|
| 1a | CRITICAL-001 | HMAC signing as immediate auth patch | HIGH (touches all auth) | No |
| 1b | CRITICAL-001 | JWT forwarding as permanent solution | HIGH | After 1a |
| 2 | CRITICAL-002 | Rotate all secrets, add gitleaks pre-commit | LOW | Yes |
| 3 | MEDIUM-002 | `hmac.compare_digest` for admin key | ZERO | Yes |
| 4 | MEDIUM-001 | `defusedxml` drop-in replacement | ZERO | Yes |
| 5 | LOW-001 | Remove duplicate `thirteenf_router` | ZERO | Yes |
| 6 | LOW-002 | Restrict CORS methods/headers | ZERO | Yes |

Items 2-6 are independent and can ship as a single commit alongside 1a.

### Phase 2 — Harden Authentication (HIGH-001, HIGH-005, HIGH-002)

| # | Finding | Action | Risk | Parallelizable |
|---|---------|--------|------|----------------|
| 7 | HIGH-001 + HIGH-005 | MFA refactor: remove sessionStorage password, move challenge tokens out of URLs | HIGH | No |
| 8 | HIGH-002 | Rate limiting with slowapi + Redis | MEDIUM | Yes (independent of MFA) |

MFA refactor and rate limiting are independent and can be built in parallel, but each should be deployed and verified separately.

### Phase 3 — Defense in Depth (HIGH-003, HIGH-004, MEDIUM-003, MEDIUM-008, MEDIUM-006)

| # | Finding | Action | Risk | Parallelizable |
|---|---------|--------|------|----------------|
| 9 | HIGH-003 | DB SSL certificate verification | LOW | Yes |
| 10 | HIGH-004 | Security headers middleware (CSP report-only) | LOW | Yes |
| 11 | MEDIUM-003 | Server-side subscription plan gating | MEDIUM | Yes |
| 12 | MEDIUM-008 | Endpoint auth decisions (public vs authenticated) | MEDIUM | With 11 |
| 13 | MEDIUM-006 | Strip `password_changed_at` from session-check | LOW | Yes |

All items parallelizable. Plan gating (11) and endpoint auth decisions (12) should be designed together.

### Phase 4 — Audit Trail and Hardening (MEDIUM-004, MEDIUM-005, MEDIUM-007)

| # | Finding | Action | Risk | Parallelizable |
|---|---------|--------|------|----------------|
| 14 | MEDIUM-004 | Stripe webhook idempotency table | LOW | Yes |
| 15 | MEDIUM-007 | Structured audit logging | LOW | Yes |
| 16 | MEDIUM-005 | Pickle integrity checksums | LOW | Yes |

All additive. No changes to existing tables or contracts.

---

## 2. CRITICAL-001: Auth Model (HMAC then JWT Dual Validation)

### Problem

`deps.py:15-44` trusts `X-User-Id` and `X-User-Email` HTTP headers from any client. Any attacker can impersonate any user with `curl -H "X-User-Id: 1"`. This invalidates the entire authorization layer.

### Phase 1a: HMAC Signing (Immediate Patch)

**Next.js side** (`web/src/lib/api/server.ts`):

After extracting session via `auth()`:
1. Compute `timestamp = Math.floor(Date.now() / 1000)`
2. Compute `payload = "${userId}:${timestamp}"`
3. Compute `signature = HMAC-SHA256(payload, SERVICE_AUTH_SECRET)` using Node.js `crypto`
4. Set headers: `X-User-Id`, `X-Auth-Timestamp`, `X-Auth-Signature`
5. Remove `X-User-Email` header entirely (never needed again)

**FastAPI side** (`api/src/margin_api/deps.py`):

Modified `get_current_user_id()`:
1. Read `X-Auth-Signature` and `X-Auth-Timestamp` headers
2. If signature present: recompute HMAC, compare with `hmac.compare_digest()`, reject if `abs(now - timestamp) > 60` seconds
3. If signature absent and `MARGIN_REQUIRE_SIGNED_AUTH=false`: log WARNING, fall through to current `X-User-Id` trust (temporary)
4. If signature absent and `MARGIN_REQUIRE_SIGNED_AUTH=true`: reject with 401

**Feature flag:** `MARGIN_REQUIRE_SIGNED_AUTH` (default `false`). Deploy with flag off, monitor logs for unsigned requests, flip to `true` once clean, then remove flag.

**New secret:** `SERVICE_AUTH_SECRET` — 64-byte hex random, shared between Next.js and FastAPI. Distinct from `AUTH_SECRET` (NextAuth encryption key).

**No nonce tracking needed.** The 60-second timestamp window is sufficient because requests travel over Railway's internal network. JWT phase replaces this within days.

### Phase 1b: JWT Forwarding (Permanent Solution)

**Critical finding from verification:** NextAuth v5 beta uses JWE (encrypted tokens), not JWS (signed tokens). The raw session cookie cannot be decoded by PyJWT. Instead of forwarding the encrypted session cookie, `serverFetch()` creates a new short-lived JWS token.

**Next.js side** (`web/src/lib/api/server.ts`):

```
1. const session = await auth()          // already works today
2. if (session?.userId) {
     const token = await signServiceToken({
       sub: session.userId,
       email: session.user?.email,
     })
     headers["Authorization"] = `Bearer ${token}`
   }
3. Remove X-User-Id, X-Auth-Timestamp, X-Auth-Signature headers
```

**New helper** (`web/src/lib/api/service-token.ts`):

Uses the `jose` library (already installed as NextAuth dependency):
- `new SignJWT({sub, email}).setProtectedHeader({alg: "HS256"}).setIssuedAt().setExpirationTime("60s").sign(encodedSecret)`
- Secret: `SERVICE_AUTH_SECRET` (same as HMAC phase)
- TTL: 60 seconds (created fresh per-request, not cached)

**FastAPI side** (`api/src/margin_api/deps.py`):

New dependency: `pyjwt` (`uv add pyjwt --package margin-api`).

```
1. Read Authorization: Bearer <token>
2. jwt.decode(token, SERVICE_AUTH_SECRET, algorithms=["HS256"])
3. Verify exp, iat (PyJWT does this automatically)
4. Clock skew: leeway=30 seconds
5. Extract userId from "sub" claim
6. Return int(userId)
```

Accepts JWT OR HMAC during transition. After 1 week: remove HMAC code path.

### Migration Rollout

```
Day 1: Deploy HMAC signing (flag off — dual accept, log warnings for unsigned)
Day 2: Flip MARGIN_REQUIRE_SIGNED_AUTH=true (reject unsigned requests)
Day 3-5: Implement JWT signing in serverFetch + JWT verification in deps.py
Day 5: Deploy JWT support (accept JWT OR HMAC, prefer JWT)
Day 6: Update serverFetch to send JWT only (remove HMAC headers)
Day 7: Remove HMAC code path from deps.py
Day 8: Remove X-User-Id header support entirely
```

### Test Strategy

Existing API tests use `app.dependency_overrides[get_current_user_id] = lambda: user_id` — they bypass header parsing entirely and pass unchanged.

New tests:
- `test_hmac_auth.py`: valid signature, expired timestamp, wrong secret, missing headers
- `test_jwt_auth.py`: valid token, expired token, wrong secret, malformed, missing sub claim
- `test_deps.py` updates: existing X-User-Id header tests become negative tests (expect 401 when flag is on)
- Integration test: real serverFetch + FastAPI with JWT

### Why not forward the raw NextAuth cookie?

NextAuth v5 beta encrypts JWTs by default (JWE with A256CBC-HS512). Decrypting in Python requires `jwcrypto` and matching the exact NextAuth encryption format, which is fragile across NextAuth versions. Creating a fresh service-to-service JWS token is simpler, more standard, and decouples the API auth from NextAuth's internal format.

---

## 3. CRITICAL-002: Secret Rotation Plan

### Scope

Secrets in `api/.env` and `web/.env.local` were never committed to git history (verified). Risk is local filesystem exposure.

### Rotation Order (dependency-safe)

**a) AUTH_SECRET (NextAuth)**
- Generate: `openssl rand -base64 32`
- Update: Railway env var for web service + local `web/.env.local`
- Effect: All existing sessions invalidated (users must re-login)
- Timing: Deploy during low-traffic window

**b) SERVICE_AUTH_SECRET (new, from CRITICAL-001)**
- Generate: `openssl rand -hex 64`
- Set in both Railway services (web + api)
- No existing sessions to invalidate (new secret)

**c) Stripe keys (sk_test_\*, whsec_\*)**
- Stripe Dashboard: Developers > API Keys > Roll key
- Old key valid for 24 hours (overlap window, no downtime)
- Update Railway env var for api service + local `api/.env`
- Test: trigger a webhook event from Stripe dashboard after rotation

**d) Google OAuth client secret**
- Google Cloud Console: Credentials > Edit OAuth client > Reset Secret
- Old secret invalidated immediately — ~60s window of breakage during deploy
- Rotate during lowest traffic

**e) GitHub OAuth client secret**
- GitHub: Settings > Developer settings > OAuth Apps > Generate new client secret
- Old secret remains valid until explicitly deleted (safe overlap)
- Update Railway env var, then delete old secret

**f) MFA_ENCRYPTION_KEY, API_KEY_ENCRYPTION_KEY**
- DO NOT rotate now. These encrypt data at rest (Fernet). Rotating requires re-encrypting all existing MFA secrets and API keys with decrypt-old/encrypt-new migration logic.
- Schedule as a separate task. Risk is lower: only useful with DB access.

### Pre-commit Secret Scanning

Tool: gitleaks (faster and more accurate than detect-secrets for git repos).

Setup:
1. Add `.gitleaks.toml` config (allowlist `.env.example` files and test fixtures)
2. Add to `.pre-commit-config.yaml`: repo `https://github.com/gitleaks/gitleaks`, hook `gitleaks`
3. CI: Add gitleaks GitHub Action on every PR

### Local Dev Cleanup

1. Create `api/.env.example` and `web/.env.local.example` with placeholder values only
2. Verify `.gitignore` covers `.env`, `.env.local`, `.env*.local`

---

## 4. MFA Refactor (HIGH-001 + HIGH-005)

### Problem

Two related issues in the MFA flow:
- **HIGH-001**: Plaintext password stored in `sessionStorage` during MFA (accessible to any JS on the origin)
- **HIGH-005**: Challenge token passed in URL query parameters (visible in browser history, server logs, Referer headers)

### Current Flow (Broken)

```
1. User submits email + password on /login
2. login-card.tsx stores password in sessionStorage          ← HIGH-001
3. NextAuth authorize() calls POST /auth/verify-credentials
4. API returns {id, mfa_status, challenge_token}
5. signIn callback redirects to /mfa/verify?challengeToken=x ← HIGH-005
6. MFA page reads password from sessionStorage
7. After TOTP verification, re-calls signIn() with password + mfaToken
```

### New Flow (Secure)

```
1. User submits email + password on /login
2. login-card.tsx calls signIn("credentials", {username, password})
   (NO sessionStorage writes)
3. NextAuth authorize() calls POST /auth/verify-credentials
4. API returns {id, mfa_status, challenge_token}
5. signIn callback returns redirect to /api/mfa-redirect
   (server-to-server, challenge token never in browser URL)
6. /api/mfa-redirect route handler:
   a. Sets __mfa_challenge httpOnly cookie (userId + challengeToken)
   b. Redirects to /mfa/verify (clean URL, no query params)
7. User enters TOTP code
8. Page calls POST /api/v1/auth/mfa/complete
   Body: {totp_code: "123456"}
   Cookie: __mfa_challenge sent automatically
9. NEW backend endpoint processes:
   a. Read cookie -> extract userId, challengeToken
   b. Verify challenge token (existing logic)
   c. Verify TOTP code (existing logic)
   d. Sign a JWT completion token: {sub: userId, purpose: "mfa_complete", exp: +60s}
   e. Return {mfa_completion_token: "<jwt>"}
10. Page calls signIn("credentials", {mfaCompletionToken: "<jwt>"})
11. NextAuth authorize() sees mfaCompletionToken:
    a. Calls POST /auth/verify-mfa-token
    b. API verifies JWT signature + expiry + purpose claim
    c. Returns user data (no password needed)
12. Session created — password was NEVER stored client-side
```

### Backend Changes

**New endpoint: `POST /api/v1/auth/mfa/complete`**
- Input: `{totp_code: str}` + `__mfa_challenge` cookie
- Parses cookie for userId and challengeToken
- Verifies challenge token (existing `verify_challenge_token()` logic)
- Verifies TOTP code (existing `verify_totp_code()` logic)
- Signs JWT: `{sub: str(userId), purpose: "mfa_complete", exp: now+60s}` with `jwt_secret` from config
- Clears `__mfa_challenge` cookie in response
- Returns `{mfa_completion_token: str}`

**New endpoint: `POST /api/v1/auth/verify-mfa-token`**
- Input: `{token: str}`
- Decodes JWT with `jwt_secret`, verifies `purpose == "mfa_complete"`, verifies not expired
- Looks up user by ID
- Returns user data `{id, email, username, avatar_url}`

**Modified: NextAuth `authorize()` in `auth.ts`**
- If `credentials.mfaCompletionToken` is present: call `/auth/verify-mfa-token`, return user data (skip password verification)
- Else: existing flow (email + password)

### Frontend Changes

**`web/src/lib/auth.ts` signIn callback:**
- Remove `challengeToken` from redirect URL
- Return redirect to `/api/mfa-redirect?userId=X&challengeToken=Y` (server-to-server, never in browser URL bar)

**New route handler: `web/src/app/api/mfa-redirect/route.ts`**
- Reads userId + challengeToken from query params (server-side only)
- Sets `__mfa_challenge` httpOnly cookie (secure, sameSite: lax, maxAge: 300, path: /mfa)
- Redirects to `/mfa/verify` (302, clean URL)

**`web/src/components/login/login-card.tsx`:**
- Remove `sessionStorage.setItem("mfa_username", ...)` and `sessionStorage.setItem("mfa_password", ...)`

**`web/src/app/mfa/verify/page.tsx`:**
- Remove `useSearchParams()` for userId/challengeToken
- Remove `sessionStorage.getItem()` calls
- TOTP verify: call `POST /api/v1/auth/mfa/complete` (cookie sent automatically)
- On success: call `signIn("credentials", {mfaCompletionToken: token})`
- Recovery code: same pattern

**`web/src/app/mfa/setup/page.tsx`:**
- Same cookie-based approach (also uses searchParams for challengeToken today)

### Backward Compatibility

- Old clients hitting `/mfa/verify?challengeToken=...` still work for 1 week (page checks URL params as fallback, logs deprecation warning, prefers cookie)
- Password removal from sessionStorage is immediate (no backward compat needed)
- Users mid-MFA-flow at deploy time must restart login (~30s flow vs ~60s deploy)

### Test Strategy

New API tests (`test_mfa_complete.py`, ~15 tests):
- Valid TOTP + valid cookie -> 200 + JWT
- Invalid TOTP -> 401
- Expired challenge -> 401
- Missing cookie -> 401
- verify-mfa-token: valid JWT -> user data
- verify-mfa-token: expired JWT -> 401
- verify-mfa-token: wrong purpose claim -> 401

Updated web tests:
- MFA verify page: mock `/auth/mfa/complete`, verify no sessionStorage access
- Login card: verify `sessionStorage.setItem` never called

Existing verify-totp tests unchanged (endpoint still exists for MFA setup flow).

---

## 5. Rate Limiting Architecture (HIGH-002)

### Library

slowapi with Redis backend. Redis connection reuses `MARGIN_REDIS_URL` (already configured for ARQ). Separate connection pool, separate key namespace, no conflict with workers.

New dependency: `uv add slowapi --package margin-api`

### Tiered Limits

**Tier 1 — Auth endpoints (5/min per IP):**
- `POST /auth/verify-credentials`
- `POST /auth/register`
- `POST /auth/forgot-password`
- `POST /auth/mfa/verify-totp`
- `POST /auth/mfa/complete`
- `POST /auth/reset-password`

Per-IP because attacker has no session yet. Existing per-user lockout (5 attempts, 15-min window) remains as second layer.

**Tier 2 — Admin endpoints (3/min per IP):**
- `POST /admin/*`

Combined with `hmac.compare_digest` fix, makes timing attacks infeasible.

**Tier 3 — Authenticated data endpoints (60/min free, 120/min paid per user):**
- `GET /scores/history/*`
- `GET /backtest/default`, `/backtest/replay`
- `POST /backtest/shadow-portfolio`
- `GET /13f/*` (authenticated routes)
- `GET /correlations/*`

Keyed by verified user_id (post CRITICAL-001 fix). Plan-aware: check subscription to pick limit.

**Tier 4 — Public data endpoints (20/min per IP):**
- `GET /scores/{ticker}`
- `GET /dashboard`
- `GET /backtest/teaser`

**Tier 5 — Global fallback (200/min per IP):**
- All endpoints not explicitly tiered.

### Response Format

```
HTTP/1.1 429 Too Many Requests
Retry-After: 45
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1708905660

{"detail": "Rate limit exceeded. Try again in 45 seconds."}
```

### Redis Failure Mode

slowapi fails open by default (allows requests through). Redis outage does not take down the API. Log WARNING when Redis connection fails.

### Implementation

```python
# api/src/margin_api/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    strategy="fixed-window",
)

# Applied per-route via @limiter.limit("5/minute") decorators
# Integrated into app via SlowAPIMiddleware + exception handler
```

### Test Strategy

- `MARGIN_RATE_LIMIT_ENABLED=false` in test environment (limiter returns no-op)
- Existing tests never see rate limits
- New `test_rate_limit.py` (~12 tests): explicitly enables limiting, tests 429 responses, Retry-After headers, tier behavior, Redis-unavailable fallback

---

## 6. Database SSL Fix (HIGH-003)

### Problem

`session.py:44-47` and `alembic/env.py` disable certificate verification (`ssl.CERT_NONE`). Railway PostgreSQL uses self-signed certificates with an auto-generated CA that is not downloadable via dashboard.

### Solution: Extract and Trust the CA Cert

Extract Railway PG's CA certificate using `openssl s_client`, store as an environment variable, verify on every connection.

**New shared utility** (`api/src/margin_api/db/ssl.py`):

```python
def create_pg_ssl_context() -> ssl.SSLContext:
    ssl_ctx = ssl.create_default_context()
    ca_cert = os.environ.get("MARGIN_DB_CA_CERT")
    if ca_cert:
        # Write PEM to temp file, load as CA
        ssl_ctx.load_verify_locations(cafile=ca_path)
        ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        ssl_ctx.check_hostname = False  # self-signed won't match hostname
    else:
        # Fallback: encrypted but unverified
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        logger.warning("DB SSL: CERT_NONE - set MARGIN_DB_CA_CERT for verification")
    return ssl_ctx
```

Used by both `session.py` and `alembic/env.py`.

### Config

New env var: `MARGIN_DB_CA_CERT` (optional, PEM string). When present: `CERT_REQUIRED`. When absent: `CERT_NONE` with logged warning (graceful degradation).

### Rollout

1. Extract CA cert from Railway PG (one-time: `openssl s_client -connect $PGHOST:$PGPORT`)
2. Store as `MARGIN_DB_CA_CERT` in Railway env vars
3. Deploy — if cert is wrong, connection fails, startup fails
4. Rollback: unset `MARGIN_DB_CA_CERT` -> falls back to `CERT_NONE`
5. When Railway rotates cert (~every 2 years): extract new cert, update env var

### Test Strategy

Existing tests unaffected (use SQLite, no SSL). New unit tests for `create_pg_ssl_context()` with and without env var.

---

## 7. Security Headers (HIGH-004)

### Implementation

New file: `web/src/middleware.ts`

**Immediate enforcement:**
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`
- `X-DNS-Prefetch-Control: off`

**Report-only (weeks 1-2), then enforcing:**
- `Content-Security-Policy-Report-Only` -> `Content-Security-Policy`

### CSP Policy

```
default-src 'self';
script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com;
style-src 'self' 'unsafe-inline';
img-src 'self' data: blob: https://lh3.googleusercontent.com https://avatars.githubusercontent.com;
font-src 'self';
connect-src 'self' https://api.stripe.com wss:;
frame-src https://js.stripe.com https://hooks.stripe.com;
worker-src 'self' blob:;
object-src 'none';
base-uri 'self';
form-action 'self';
frame-ancestors 'none';
```

`unsafe-inline` required for Next.js hydration scripts. `unsafe-eval` required for Three.js GLSL shader compilation. Both can be tightened later with nonce-based CSP (Next.js 15 experimental support) and pre-compiled shaders.

### HSTS Note

Not adding `preload` yet. That submits the domain to browser preload lists permanently and requires separate consideration. Save for Phase 4.

### Rollout

1. Deploy with `Content-Security-Policy-Report-Only` + all other headers enforcing
2. Monitor browser console for CSP violations across all critical flows (login, MFA, Stripe checkout, dashboard, Three.js homepage, Smart Money)
3. Adjust policy if violations found
4. After 1-2 weeks: switch to enforcing `Content-Security-Policy`

### Test Strategy

New `middleware.test.ts` (~8 tests): mock NextResponse, verify all headers set, verify matcher excludes static files. Existing tests unaffected (Vitest doesn't run middleware).

Manual QA during report-only window: homepage, login, MFA, Stripe checkout, dashboard charts, asset detail, WebSocket connection.

---

## 8. Medium-Severity Batch Strategy

### Quick Wins (< 30 min total, ship in Phase 1)

**MEDIUM-002: Admin key timing attack** (`admin.py:30`)
```python
# Before:
if x_admin_key != settings.admin_key:
# After:
if not hmac.compare_digest(x_admin_key or "", settings.admin_key):
```

**MEDIUM-006: Session-check info leak** (`auth.py:298`)
- Strip `password_changed_at` from response
- Return `{session_valid: bool, token_invalidated: bool}` instead
- Accept `iat` query param, do the comparison server-side
- Update NextAuth jwt callback to read the boolean

**MEDIUM-001: XML bomb** (`edgar_provider.py`)
```bash
uv add defusedxml --package margin-engine
```
Replace `import xml.etree.ElementTree as ET` with `import defusedxml.ElementTree as ET` at 3 call sites. Drop-in replacement.

**LOW-001: Duplicate router** (`app.py:120`) — delete the line.

**LOW-002: Permissive CORS** (`app.py:94-95`)
```python
allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
allow_headers=["Content-Type", "Authorization", "X-Auth-Timestamp", "X-Auth-Signature"],
```

### Moderate Fixes (Phase 3, 1-2 hours each)

**MEDIUM-003: Server-side subscription gating**

Fix `require_plan()` tier hierarchy (current implementation uses exact match):
```python
PLAN_TIERS = {"analyst": 0, "portfolio": 1, "institutional": 2, "operator": 3}
```
Higher tiers can access lower-tier endpoints. Fix `keys.py` from `require_plan("margin_invest")` to `require_plan("portfolio")` (legacy bug — no user has plan `"margin_invest"`).

Apply gating:
- `require_plan("portfolio")`: score history, backtest default/replay, correlations
- `require_plan("institutional")`: 13F analytics, curated managers, clone, shadow-portfolio

**MEDIUM-008: Endpoint auth decisions**

Per business decision — free tier gets public read:
- Public (rate-limited by IP): `GET /scores/{ticker}`, `GET /dashboard`, `GET /backtest/teaser`
- Auth required (any plan): score history, backtest default/replay
- Auth + plan gating: 13F analytics, curated managers, clone, shadow-portfolio

**MEDIUM-005: Pickle integrity checksums** (`signal_model.py`)

Add `cluster_model_checksum` and `vae_model_checksum` columns to `ml_model_runs` (Alembic migration, nullable). On save: `sha256(model_bytes)`. On load: verify checksum before `pickle.loads()`. Old rows without checksums load with a logged warning.

### Structural Additions (Phase 4, half-day each)

**MEDIUM-004: Stripe webhook idempotency**

New table: `processed_webhook_events` with `event_id` (PK), `event_type`, `processed_at`. Before processing: check if event_id exists. Insert event_id in same transaction as subscription update. Return 200 for already-processed events. Weekly cleanup of rows older than 72 hours.

**MEDIUM-007: Audit logging**

New table: `audit_log` with `id`, `event_type`, `user_id`, `ip_address`, `user_agent`, `detail` (JSONB), `created_at`. Append-only, no UPDATE or DELETE. New service `audit.py` with `audit_log()` function. Instrumented at: login success/failure, MFA verify, password change, admin actions, subscription changes. 90-day retention.

---

## 9. Regression Prevention Plan

### Pre-Work: Establish Green Baseline

Before any security changes:
1. Run full test suite, record results
2. Fix any existing failures (batched ingest test updates)
3. Tag: `git tag pre-security-remediation`

This tag is the rollback point.

### Existing Test Safety

All ~1038 API tests use `app.dependency_overrides[get_current_user_id] = lambda: user_id`. They bypass header parsing entirely. Changes to `deps.py` auth logic do not affect them.

Only `test_deps.py` (11 tests) and `test_dna.py` (3 tests) send `X-User-Id` headers directly to test the real parsing. These become negative tests (expect 401) after CRITICAL-001 migration.

### Per-Phase Risk

**Phase 1** (auth + quick wins): Existing tests pass unchanged. Quick wins are drop-in replacements. New tests cover HMAC/JWT verification.

**Phase 2** (MFA + rate limiting): MFA refactor is highest-risk change. New endpoint tests cover the new flow. Rate limiting disabled in test env via `MARGIN_RATE_LIMIT_ENABLED=false`.

**Phase 3** (SSL + headers + plan gating): SSL tests use SQLite (no SSL path). Headers tested in isolation. Plan gating is the risk: tests hitting newly-gated endpoints with default `plan=None` fixtures will get 403. Must update test user fixtures to set appropriate plans.

**Phase 4** (webhook idempotency + audit): Additive. No existing behavior changes.

### New Security Test Suite

```
api/tests/security/
  test_hmac_auth.py         ~10 tests
  test_jwt_auth.py          ~10 tests
  test_rate_limit.py        ~12 tests
  test_plan_gating.py       ~8 tests
  test_mfa_complete.py      ~15 tests
  test_webhook_idempotency.py ~6 tests
  test_audit_log.py         ~8 tests

web/src/__tests__/security/
  middleware.test.ts         ~8 tests
  mfa-flow.test.ts          ~6 tests

Estimated new tests: ~83
```

### Smoke Test Checklist (Per Deploy)

```
Auth:
  [ ] Credentials login (non-MFA) -> dashboard
  [ ] Credentials login (MFA) -> MFA page -> dashboard
  [ ] Google OAuth -> dashboard
  [ ] GitHub OAuth -> dashboard
  [ ] Logout -> /login
  [ ] Direct API call with X-User-Id (no signature) -> 401

Data access:
  [ ] GET /scores/AAPL (unauthenticated) -> 200
  [ ] GET /13f/analytics (unauthenticated) -> 401
  [ ] GET /13f/analytics (free user) -> 403
  [ ] GET /13f/analytics (institutional user) -> 200

Rate limiting:
  [ ] 6th auth request in 1 minute -> 429
  [ ] 21st public data request in 1 minute -> 429

Headers:
  [ ] curl -I returns all security headers
  [ ] No CSP violations in browser console
```

---

## 10. What Could Go Wrong

### Most Likely Regressions

**1. MFA cookie flow fails in production (HIGH probability)**

The `__mfa_challenge` httpOnly cookie may be blocked by SameSite policy on redirect, stripped by Vercel edge functions, or set after the redirect fires. Mitigation: keep URL-param fallback for 1 week, monitor which path is used, remove fallback once cookie path is confirmed.

**2. NextAuth JWE format incompatible with service token approach (MEDIUM probability)**

If NextAuth changes its internal token format or `auth()` stops returning the expected session shape, `serverFetch()` can't sign service tokens. Mitigation: the HMAC phase (1a) doesn't depend on NextAuth internals at all — it reads session data, not tokens. HMAC can remain as long-term fallback.

**3. Rate limiting blocks corporate NAT users (MEDIUM probability)**

Many users behind one IP exhaust per-IP limits collectively. Mitigation: start with 2x the design limits, monitor 429 rates, add `X-Forwarded-For` trust for known proxies if needed. Limits are configurable via env vars.

**4. Plan gating breaks API tests (HIGH probability, LOW impact)**

Tests using default user fixtures (`plan=None`) that call newly-gated endpoints get 403. Mitigation: update fixtures before adding `require_plan()`. Run full suite after each endpoint is gated.

### Hidden Coupling Risks

**5. serverFetch cookie access triggers dynamic rendering**

Reading `cookies()` in serverFetch may force Next.js pages from static to dynamic rendering. Mitigation: only read cookies when auth is needed; unauthenticated calls skip it. `try/catch` already wraps the `auth()` call.

**6. AUTH_SECRET rotation during in-flight Stripe checkout**

User mid-checkout when sessions invalidate. Stripe iframe survives (client-side), but the redirect back to /dashboard after payment requires re-login. Acceptable one-time cost for security rotation.

**7. CSP breaks Stripe 3D Secure**

`frame-src` may miss domains needed for bank verification iframes. Mitigation: CSP is report-only for 2 weeks. Test with Stripe 3DS test card (`4000 0025 0000 3155`) during report-only period. Add missing domains before enforcing.

### The Nightmare Scenario

Deploy HMAC auth, flip `MARGIN_REQUIRE_SIGNED_AUTH=true` before verifying HMAC path works in production. Every authenticated request returns 401. Complete API lockout.

Prevention:
1. Deploy with flag `false` (dual accept)
2. Monitor logs: verify signed requests arriving and succeeding
3. Verify unsigned requests generate WARNING logs
4. Only then flip to `true`

Recovery: Set `MARGIN_REQUIRE_SIGNED_AUTH=false` via Railway env var (~60 seconds) or use Railway instant rollback (~30 seconds). No data loss.
