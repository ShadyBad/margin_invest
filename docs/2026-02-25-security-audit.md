# Margin Invest — Comprehensive Security Audit

**Date:** 2026-02-25
**Auditors:** Claude (primary), Gemini (cross-review)
**Scope:** Full-stack static code review — frontend, backend, engine, infrastructure, CI/CD
**Method:** Manual source code analysis. No dynamic testing (OWASP ZAP, Burp Suite) was performed.

---

## 1. Executive Summary

Margin Invest has strong security fundamentals: Argon2id password hashing with OWASP parameters, mandatory MFA enforcement on sensitive endpoints, Fernet-encrypted API keys at rest, Stripe webhook signature verification, Pydantic input validation on all route handlers, and parameterized SQLAlchemy queries throughout.

However, the audit identified **2 critical, 5 high, and 8 medium** severity issues. The single most dangerous finding is the **trust-client-headers authentication model** (`deps.py:15-44`) — any HTTP client can impersonate any user by setting `X-User-Id: 1`. This alone invalidates the entire authorization layer for every authenticated endpoint.

### Positive Security Controls Already In Place

1. Password hashing: Argon2id with `time_cost=3, memory_cost=65536, parallelism=4`
2. Account lockout: 5 failed attempts triggers 15-minute lockout
3. MFA enforcement: Required on billing, API keys, password change, avatar, DNA
4. API key encryption: Fernet (AES-128-CBC + HMAC) at rest, masked on read
5. Challenge tokens: SHA-256 hashed before storage, 5-minute TTL, single-use
6. Stripe webhooks: Signature verification enforced
7. Input validation: Pydantic models on all route handlers
8. SQL injection prevention: SQLAlchemy ORM with parameterized queries throughout
9. File upload security: Magic byte validation, type allowlist (PNG/JPEG/WebP), 5MB limit
10. Error handling: Generic error messages in responses, no stack trace leakage
11. Request tracing: UUID request IDs on every response
12. API docs disabled in production: `docs_url=None` when `debug=False`
13. Production DB guard: Blocks startup if `MARGIN_DATABASE_URL` points to localhost in production

---

## 2. STRIDE Threat Model

| # | Threat | STRIDE Category | Component | Severity | Status |
|---|---|---|---|---|---|
| 1 | User impersonation via `X-User-Id` header spoofing | Spoofing | `deps.py:15-44` | **CRITICAL** | Open |
| 2 | Secrets in local env files (Stripe, OAuth, AUTH_SECRET) | Information Disclosure | `api/.env`, `web/.env.local` | **CRITICAL** | Open |
| 3 | Plaintext password in sessionStorage during MFA flow | Information Disclosure | `login-card.tsx:122-123` | **HIGH** | Open |
| 4 | No rate limiting on any endpoint | Denial of Service | System-wide | **HIGH** | Open |
| 5 | SSL certificate verification disabled for PostgreSQL | Tampering | `session.py:46-47` | **HIGH** | Open |
| 6 | No CSP or security headers on frontend | Tampering / XSS enablement | `next.config.ts` | **HIGH** | Open |
| 7 | MFA challenge token exposed in URL query params | Information Disclosure | `auth.ts:94,98` | **HIGH** | Open |
| 8 | XML bomb (Billion Laughs) via `xml.etree.ElementTree` | Denial of Service | `edgar_provider.py:312,539,620` | **MEDIUM** | Open |
| 9 | Admin key comparison vulnerable to timing attack | Spoofing | `admin.py:30` | **MEDIUM** | Open |
| 10 | Client-side-only subscription gating | Elevation of Privilege | `pro-gate.tsx` | **MEDIUM** | Open |
| 11 | Stripe webhook handler lacks idempotency | Repudiation | `billing.py:75-121` | **MEDIUM** | Open |
| 12 | Pickle deserialization of ML models | Tampering | `signal_model.py:96,109` | **MEDIUM** | Open |
| 13 | Session-check endpoint leaks `password_changed_at` | Information Disclosure | `auth.py:298` | **MEDIUM** | Open |
| 14 | No audit logging for auth, admin, or billing events | Repudiation | System-wide | **MEDIUM** | Open |
| 15 | Unauthenticated data endpoints (scores, 13F, backtest) | Information Disclosure | Multiple routes | **MEDIUM** | Needs decision |
| 16 | `thirteenf_router` registered twice | Misconfiguration | `app.py:117,120` | **LOW** | Open |
| 17 | Permissive CORS (`allow_methods=["*"]`, `allow_headers=["*"]`) | Tampering | `app.py:94-95` | **LOW** | Open |
| 18 | WebSocket endpoint authentication unknown | Spoofing | `ws/scores.py` | **UNKNOWN** | Needs investigation |

---

## 3. Attack Surface Map

```
                              INTERNET
                                 │
                    ┌────────────┼────────────────┐
                    │            │                 │
              ┌─────▼─────┐  ┌──▼──────────┐  ┌──▼──────────────┐
              │  Attacker  │  │  Stripe     │  │  SEC EDGAR /    │
              │  (curl)    │  │  Webhooks   │  │  FMP / Polygon  │
              └─────┬──┬──┘  │  (verified)  │  │  (XML payloads) │
                    │  │     └──┬───────────┘  └──┬──────────────┘
                    │  │        │                  │
         ┌──────────┘  │     ┌──▼──────────────────▼───────────────┐
         │             │     │  Railway (FastAPI API)               │
         │ Direct API  │     │                                      │
         │ access      │     │  VULNERABILITIES:                    │
         │ (bypasses   │     │  • Trusts X-User-Id header blindly  │
         │  frontend)  │     │  • No rate limiting                  │
         │             │     │  • Admin key: string == (timing)     │
         │             │     │  • SSL CERT_NONE to PostgreSQL       │
         │             │     │  • No audit logging                  │
         │             │     │  • Pickle deserialization (ML)       │
         │             │     │  • xml.etree (no defusedxml)         │
         │             │     └──┬───────────┬──────────────────────┘
         │             │        │           │
         │   ┌─────────▼────┐ ┌▼────────┐ ┌▼────────────┐
         │   │  Vercel       │ │Railway  │ │ Railway      │
         │   │  (Next.js)    │ │PG       │ │ Redis / ARQ  │
         │   │               │ │(no TLS  │ │ (workers)    │
         │   │ VULNERABILITIES│ │ verify) │ └──────────────┘
         │   │ • No CSP       │ └─────────┘
         │   │ • No middleware │
         │   │ • sessionStorage│
         │   │   passwords     │
         │   │ • MFA token in  │
         │   │   URL params    │
         │   │ • Client-side   │
         │   │   plan gating   │
         └───┤               │
             │  serverFetch() │
             │  sets X-User-Id│──────► API trusts this header
             │  from session  │        from ANY source
             └────────────────┘
```

**Primary attack vector:** Direct API calls bypassing the Next.js frontend. An attacker sends `X-User-Id: <any_integer>` directly to the Railway-hosted API and gets full authenticated access to any user's account.

---

## 4. Detailed Findings

### CRITICAL-001: Unauthenticated User Impersonation via Header Trust

**File:** `api/src/margin_api/deps.py:15-44`

The API trusts `X-User-Id` and `X-User-Email` HTTP headers from any client. There is no JWT verification, no session token, no cryptographic proof of identity.

```python
async def get_current_user_id(
    x_user_id: str | None = Header(None),
    x_user_email: str | None = Header(None),
    ...
) -> int:
    if x_user_id is not None:
        return int(x_user_id)  # No verification
```

The design intent is that `serverFetch()` in `web/src/lib/api/server.ts:20-24` sets these headers server-side from the NextAuth session. But the API has no way to distinguish headers set by the Next.js server from headers set by a random attacker.

**Attack scenario:**
```bash
# Access any user's billing
curl -H "X-User-Id: 1" https://api.margininvest.com/api/v1/billing/status

# Change any user's password (combined with MFA bypass if MFA not set up)
curl -X POST -H "X-User-Id: 42" -H "Content-Type: application/json" \
  -d '{"current_password":"...","new_password":"..."}' \
  https://api.margininvest.com/api/v1/auth/change-password

# Access any user's DNA profile
curl -H "X-User-Id: 42" https://api.margininvest.com/api/v1/users/me/dna

# Create checkout session as another user
curl -X POST -H "X-User-Id: 1" -H "Content-Type: application/json" \
  -d '{"plan":"portfolio"}' https://api.margininvest.com/api/v1/billing/checkout
```

**Affected endpoints:** Every endpoint using `get_current_user_id` — billing (checkout, portal, status), API keys (CRUD), avatar (upload/delete), DNA, password change, MFA management, events, score history.

**Severity:** CRITICAL
**Business impact:** Complete account takeover for any user. Attacker can access billing, disable MFA, change passwords, exfiltrate all user data, manipulate subscriptions.

**Mitigation options (choose one):**

1. **JWT validation (recommended):** NextAuth already issues JWTs. Configure FastAPI to verify the JWT signature using the shared `AUTH_SECRET`. Extract user identity from the verified token claims. This is the standard approach.

2. **Shared HMAC signing (quick fix):** Next.js signs a timestamp + user ID with a shared secret. FastAPI verifies the signature before trusting the header. Reject if timestamp is > 60 seconds old (replay window).

3. **Network isolation (defense in depth, not standalone):** Place the API in Railway's private networking so only the Vercel deployment can reach it. This is a good layer but should not be the sole auth mechanism — it doesn't protect against Vercel-side vulnerabilities.

**Detection:** Log all `X-User-Id` header values with source IP. Alert on requests from IPs that don't match your Vercel deployment ranges. Alert on rapid user ID enumeration patterns.

---

### CRITICAL-002: Secrets in Local Environment Files

**Files:** `api/.env`, `web/.env.local`

These files are listed in `.gitignore` and were never committed to git history (verified via `git log`). However, they contain real credentials on disk:

**`web/.env.local`:**
- Google OAuth client secret
- GitHub OAuth client secret
- NextAuth `AUTH_SECRET`

**`api/.env`:**
- Stripe test-mode secret key (`sk_test_...`)
- Stripe webhook secret (`whsec_...`)
- Stripe price IDs

**Risk vectors:**
- Any tool with filesystem access (IDE extensions, MCP servers, AI coding assistants) can read these files
- If the repo is ever made public, even momentarily, secrets are exposed
- Unencrypted disk clones, backup tapes, or stolen laptops expose all secrets
- These exact secrets were visible to both AI auditors in this review

**Severity:** CRITICAL (if repo becomes public or disk is compromised) / HIGH (private repo, encrypted disk)
**Business impact:** Full Stripe account control (test mode), OAuth app impersonation, session forging via AUTH_SECRET.

**Mitigation:**
1. Rotate all secrets now (Stripe dashboard, Google Cloud Console, GitHub OAuth settings, generate new AUTH_SECRET)
2. Use `.env.local.example` with placeholder values only — never real credentials
3. Add a pre-commit hook with `detect-secrets` or `gitleaks` to prevent future leaks
4. For local development, consider `1Password CLI` or `direnv` with encrypted vaults

---

### HIGH-001: Plaintext Password in sessionStorage During MFA Flow

**Files:** `web/src/components/login/login-card.tsx:122-123`, `web/src/app/mfa/verify/page.tsx:47-48`

```typescript
// login-card.tsx:122-123 — stores password
sessionStorage.setItem("mfa_username", email)
sessionStorage.setItem("mfa_password", password)

// mfa/verify/page.tsx:47-48 — retrieves password
const username = sessionStorage.getItem("mfa_username") || ""
const password = sessionStorage.getItem("mfa_password") || ""
```

The MFA flow requires re-sending credentials after TOTP verification. The current implementation stores the plaintext password in `sessionStorage` to bridge the redirect between login and MFA verify pages.

**Attack scenario:** Any JavaScript running on the same origin — a browser extension, an XSS payload, a compromised third-party script — can call `sessionStorage.getItem("mfa_password")` and exfiltrate the user's plaintext password. `sessionStorage` persists for the tab's lifetime.

**Severity:** HIGH
**Business impact:** Credential theft if combined with any XSS vector or malicious browser extension.

**Mitigation:** Replace with a server-side approach:
1. Backend issues a short-lived challenge token on successful password verification (already exists — `challenge_token`)
2. Frontend stores only the opaque challenge token (never the password)
3. MFA verify page sends `challenge_token + TOTP code` to a backend endpoint that handles the full authentication, rather than re-sending username/password

This requires a new backend endpoint like `POST /api/v1/auth/mfa/complete` that accepts `{challenge_token, totp_code}` and returns a session — bypassing the need to re-send credentials.

---

### HIGH-002: No Rate Limiting on Any Endpoint

**Evidence:** No `slowapi`, no Redis-based throttle middleware, no rate limiting decorators found anywhere in the API codebase. The only rate limiting is on outbound EDGAR/FMP requests (ingestion-level, not security-relevant).

**Vulnerable endpoints:**

| Endpoint | Attack | Current Mitigation | Gap |
|---|---|---|---|
| `POST /auth/verify-credentials` | Password brute force | 5-attempt per-user lockout | No per-IP limiting — attacker distributes across users |
| `POST /auth/register` | Mass account creation | None | Unlimited fake accounts |
| `POST /auth/forgot-password` | Email flood | None | Reputation damage, email provider blocking |
| `POST /auth/mfa/verify-totp` | TOTP brute force (10^6 combinations) | Challenge token 5-min TTL | 200K attempts possible in 5 min without rate limit |
| `GET /scores/*` | Data scraping | None | All investment analysis exfiltrated |
| `GET /13f/*` | Institutional data scraping | None | Competitive intelligence leak |
| `POST /admin/*` | Admin key brute force | None | Full platform control |

**Severity:** HIGH
**Business impact:** Account takeover, data scraping, service disruption, email provider blacklisting.

**Mitigation:**
1. Add `slowapi` with Redis backend for per-IP rate limiting
2. Recommended limits:
   - Auth endpoints: 5 requests/minute per IP
   - Data endpoints (authenticated): 60 requests/minute per user
   - Data endpoints (unauthenticated): 20 requests/minute per IP
   - Admin endpoints: 3 requests/minute per IP
3. Return `429 Too Many Requests` with `Retry-After` header
4. Consider Cloudflare or AWS WAF as an additional layer in front of Railway

---

### HIGH-003: SSL Certificate Verification Disabled for PostgreSQL

**Files:** `api/src/margin_api/db/session.py:46-47`, `api/alembic/env.py:50` (same pattern)

```python
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE  # Accepts any certificate
```

**Attack scenario:** If an attacker gains network-level access (compromised Railway internal networking, BGP hijack, rogue DNS), they can present a fraudulent TLS certificate and intercept all SQL traffic between the API and PostgreSQL. This includes user credentials (password hashes), financial data, encryption keys stored in the database, and API key ciphertexts.

**Severity:** HIGH
**Business impact:** Complete database compromise via man-in-the-middle.

**Mitigation:**
1. **Preferred:** Download Railway's PostgreSQL CA certificate. Use `ssl_ctx.load_verify_locations(cafile="/path/to/ca.pem")` and set `ssl_ctx.verify_mode = ssl.CERT_REQUIRED`
2. **If Railway doesn't provide a CA cert:** Use `ssl_ctx.verify_mode = ssl.CERT_OPTIONAL` with certificate pinning (store and compare the server's certificate fingerprint)
3. Apply the same fix in `alembic/env.py` for migrations

---

### HIGH-004: No Security Headers on Frontend

**Evidence:** No `web/src/middleware.ts` file exists. `next.config.ts` contains only `transpilePackages: ["three"]` — no `headers()` configuration.

**Missing headers and their impact:**

| Header | Risk Without It |
|---|---|
| `Content-Security-Policy` | XSS payloads can load arbitrary external scripts |
| `X-Frame-Options: DENY` | Clickjacking attacks on financial operations |
| `Strict-Transport-Security` | SSL stripping / downgrade attacks |
| `X-Content-Type-Options: nosniff` | MIME sniffing attacks |
| `Referrer-Policy` | Sensitive URL params (challenge tokens) leaked in Referer headers |
| `Permissions-Policy` | Unnecessary browser API access (camera, mic, geolocation) |

**Severity:** HIGH
**Business impact:** XSS amplification, clickjacking of billing/account operations, MFA token leakage via Referer.

**Mitigation:** Create `web/src/middleware.ts`:
```typescript
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const response = NextResponse.next()
  response.headers.set('X-Frame-Options', 'DENY')
  response.headers.set('X-Content-Type-Options', 'nosniff')
  response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
  response.headers.set('Content-Security-Policy',
    "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; " +
    "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; " +
    "connect-src 'self' https://*.stripe.com wss:; " +
    "frame-src https://*.stripe.com;"
  )
  return response
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
```

Note: `unsafe-inline` and `unsafe-eval` may be needed for Next.js/React hydration. Tighten to nonce-based CSP when feasible.

---

### HIGH-005: MFA Challenge Token Exposed in URL Query Parameters

**File:** `web/src/lib/auth.ts:94,98`

```typescript
return `/mfa/setup?userId=${user.id}&challengeToken=${challengeToken}`
return `/mfa/verify?userId=${user.id}&challengeToken=${challengeToken}`
```

**Attack scenario:** Challenge tokens in URLs are visible in:
- Browser history (persists after tab close)
- Server access logs (Vercel, CDN, reverse proxy)
- `Referer` headers sent to any external resource loaded on the MFA page
- Shoulder surfing / screen recording
- Browser sync (Chrome history synced to Google account)

Combined with the 5-minute token TTL, an attacker who obtains a challenge token from any of these sources can complete MFA setup/verification for the victim's account.

**Severity:** HIGH
**Business impact:** MFA bypass leading to account takeover.

**Mitigation:**
1. Store challenge token in a server-side session (NextAuth session) or httpOnly cookie
2. Use `POST` redirect pattern instead of `GET` with query params
3. At minimum, add `Referrer-Policy: no-referrer` on MFA pages (but this doesn't fix history/logs)

---

### MEDIUM-001: XML Bomb (Billion Laughs) via `xml.etree.ElementTree`

**File:** `engine/src/margin_engine/ingestion/providers/edgar_provider.py:312,539,620`

```python
import xml.etree.ElementTree as ET
# ...
root = ET.fromstring(xml_text)  # 3 call sites parsing external SEC XML
```

**Important nuance:** CPython's `xml.etree.ElementTree` does **not** process external entities (unlike Java/PHP XML parsers). The XXE risk (SSRF, local file read) is **not present**. However, the **Billion Laughs attack** (exponential entity expansion causing OOM) **is** possible with `xml.etree.ElementTree`.

**Attack scenario:** If an attacker can MITM the EDGAR connection or if SEC infrastructure is compromised, they inject a Billion Laughs XML payload:
```xml
<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!-- ... exponential expansion ... -->
]>
<ownershipDocument>&lol9;</ownershipDocument>
```
This causes exponential memory consumption and crashes the worker container via OOM kill.

**Severity:** MEDIUM (requires MITM or compromised trusted source — SEC EDGAR is fetched over HTTPS)
**Business impact:** Worker denial of service, disrupted data pipeline.

**Mitigation:**
```bash
uv add defusedxml --package margin-engine
```
Then replace the import — `defusedxml.ElementTree` is a drop-in replacement:
```python
import defusedxml.ElementTree as ET  # was: import xml.etree.ElementTree as ET
```

---

### MEDIUM-002: Admin Key Comparison Vulnerable to Timing Attack

**File:** `api/src/margin_api/routes/admin.py:30`

```python
if x_admin_key != settings.admin_key:
    raise HTTPException(403, "Invalid admin key")
```

Python's `!=` for strings uses early-exit comparison — it returns as soon as the first mismatching byte is found. By measuring response time differences across many requests, an attacker can progressively discover the admin key character by character.

**Severity:** MEDIUM (requires many requests and microsecond-level timing, but no rate limiting exists)
**Business impact:** Admin key disclosure leading to full pipeline control.

**Mitigation:**
```python
import hmac

if not hmac.compare_digest(x_admin_key, settings.admin_key):
    raise HTTPException(403, "Invalid admin key")
```

---

### MEDIUM-003: Client-Side-Only Subscription Gating

**Files:** `web/src/components/dashboard/pro-gate.tsx`, `web/src/lib/hooks/use-subscription-tier.ts`

The `ProGate` component checks subscription tier via a client-side hook and applies a CSS blur overlay. The underlying premium data is rendered in the DOM beneath the blur — a user can inspect elements and read the content, or modify React state to bypass the gate.

More critically, backend endpoints serving premium data (`/api/v1/13f/analytics`, institutional holdings, etc.) do **not** check subscription tier — many require no authentication at all.

**Severity:** MEDIUM
**Business impact:** Free users access paid content; revenue loss; undermines subscription model.

**Mitigation:**
1. Add `require_plan("institutional")` or `require_plan("portfolio")` FastAPI dependency to all premium endpoints
2. Return `403 Upgrade required` from the API when a free user requests premium data
3. Client-side gating remains for UX polish but is never the access control mechanism

---

### MEDIUM-004: Stripe Webhook Handler Lacks Idempotency

**File:** `api/src/margin_api/routes/billing.py:75-121`

Stripe retries webhook deliveries for up to 72 hours if a `200` response is not received. The handler processes `customer.subscription.created/updated/deleted` events but does not track which `event.id` values have already been processed.

**Severity:** MEDIUM
**Business impact:** Duplicate subscription state changes; a retry during a race condition could toggle a user between free and pro.

**Mitigation:**
1. Create a `processed_webhook_events` table with `event_id` (unique) and `processed_at` columns
2. Before processing, check if `event.id` already exists
3. Insert the event ID in the same transaction as the subscription update (atomic)
4. Return `200` for already-processed events (Stripe considers this success)

---

### MEDIUM-005: Pickle Deserialization in ML Pipeline

**File:** `engine/src/margin_engine/ml/signal_model.py:96,109`

```python
model = pickle.loads(model_bytes)  # noqa: S301
```

`pickle.loads()` can execute arbitrary Python code during deserialization. Model bytes are stored in the `ml_model_runs.cluster_model_data` database column. If an attacker gains database write access (SQL injection elsewhere, compromised DB credentials, admin access), they can inject a malicious pickle payload that achieves remote code execution when the model is next loaded.

**Severity:** MEDIUM (requires prior database write access)
**Business impact:** Remote code execution on the worker container.

**Mitigation:**
1. **Short term:** Add integrity checksums (SHA-256 hash stored alongside model bytes, verified before `pickle.loads`)
2. **Long term:** Migrate to `safetensors` (for neural network weights) or `joblib` with restricted unpickler, or export to ONNX format

---

### MEDIUM-006: Session-Check Endpoint Leaks Password Timestamps

**File:** `api/src/margin_api/routes/auth.py:298`

`GET /api/v1/auth/session-check/{user_id}` is unauthenticated and returns `password_changed_at` timestamps. An attacker can enumerate user IDs (sequential integers) and determine when each user last changed their password.

**Severity:** MEDIUM
**Business impact:** User enumeration; password change timing information aids targeted attacks.

**Mitigation:** Either require authentication, or return only a boolean `session_valid` flag without raw timestamps.

---

### MEDIUM-007: No Audit Logging

No admin action, authentication event, or subscription change produces an audit trail. If an attacker gains access, there is no forensic evidence of what they accessed or modified.

**Missing audit events:**
- Login success/failure (IP, user agent, timestamp)
- MFA verification success/failure
- Password changes
- Admin API calls (who triggered what pipeline)
- Subscription changes (plan upgrades/downgrades)
- API key creation/revocation
- Avatar uploads

**Severity:** MEDIUM
**Business impact:** No incident response capability; no compliance evidence; no breach investigation trail.

**Mitigation:** Implement structured, append-only audit logging. Log to a separate table or external service (not the application log). Each entry: `{event_type, user_id, ip_address, user_agent, timestamp, details}`.

---

### MEDIUM-008: Unauthenticated Data Endpoints

These endpoints require no authentication:

| Endpoint | Data Exposed |
|---|---|
| `GET /api/v1/scores/{ticker}` | Investment analysis scores |
| `GET /api/v1/dashboard` | Full dashboard with scored universe |
| `GET /api/v1/13f/holdings/{ticker}` | Institutional 13F holdings |
| `GET /api/v1/13f/managers/*` | Manager portfolios |
| `GET /api/v1/backtest/*` | Backtesting results |
| `GET /api/v1/correlations/*` | Correlation matrices |
| `GET /api/v1/ingestion/runs` | Operational/ingestion data |
| `GET /api/v1/jobs/latest` | Job execution history |

**Severity:** MEDIUM (depends on business intent)
**Business impact:** If this data is proprietary, it can be scraped by competitors or data brokers with zero authentication. Combined with no rate limiting (HIGH-002), the entire dataset can be exfiltrated in minutes.

**Decision required:** If intentionally public (free tier), document this decision. If premium, add `get_current_user_id` dependency with appropriate plan gating.

---

### LOW-001: `thirteenf_router` Registered Twice

**File:** `api/src/margin_api/app.py:117,120`

```python
app.include_router(thirteenf_router)  # line 117
# ...
app.include_router(thirteenf_router)  # line 120 (duplicate)
```

Every 13F route is registered twice. FastAPI handles duplicates gracefully, but it doubles OpenAPI spec entries and could cause confusion.

**Severity:** LOW
**Mitigation:** Remove the duplicate line at line 120.

---

### LOW-002: Permissive CORS Configuration

**File:** `api/src/margin_api/app.py:94-95`

```python
allow_methods=["*"],
allow_headers=["*"],
```

While origins are properly restricted (`cors_origins` is configurable per environment), the wildcard methods and headers are unnecessarily permissive.

**Severity:** LOW (origins are restricted, which is the primary CORS control)
**Mitigation:**
```python
allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
allow_headers=["Content-Type", "Authorization", "X-User-Id", "X-User-Email", "X-Admin-Key"],
```

---

### INVESTIGATE-001: WebSocket Authentication

**File:** `api/src/margin_api/ws/scores.py`

The WebSocket endpoint at `/ws/scores` was not deeply audited by either review. It needs investigation:
- Is the WebSocket connection authenticated?
- Can an unauthenticated client connect and receive real-time score data?
- Is there rate limiting on WebSocket message frequency?

**Action:** Audit `ws/scores.py` and confirm authentication is enforced on WebSocket upgrade.

---

## 5. Most Likely to Be Exploited

These findings will be found and exploited by unsophisticated attackers or automated scanners:

1. **CRITICAL-001 — Header spoofing:** The API URL is discoverable. An attacker will fuzz headers and find `X-User-Id` works within minutes. Zero sophistication required. Complete account takeover.

2. **HIGH-002 — No rate limiting + unauthenticated endpoints:** Bot networks routinely scrape unauthenticated APIs. Your entire scored universe, 13F data, and backtest results can be exfiltrated programmatically.

3. **HIGH-001 — sessionStorage passwords:** Any browser extension (even legitimate ones that have been compromised via supply chain attack) can read `sessionStorage`. This is a known attack vector — Chrome extension compromises happen regularly.

## 6. Catastrophic but Rare

These require significant attacker capability but have devastating impact:

1. **HIGH-003 — Database MITM:** Requires network-level access to Railway infrastructure (BGP hijack, compromised internal routing). If achieved, attacker reads every SQL query and response including password hashes, encryption keys, and all financial data.

2. **MEDIUM-005 — Pickle RCE:** Requires prior database write access. If achieved, attacker gets arbitrary code execution on worker containers, which have access to all API secrets via environment variables.

3. **Supply chain attack via unpinned Docker base image:** Attacker compromises `python:3.13-slim` on DockerHub. Affects all deployments. Mitigated by pinning to SHA digest.

---

## 7. Prioritized Remediation Roadmap

### Phase 1 — Emergency (This Week)

| # | Finding | Action | Effort |
|---|---|---|---|
| 1 | CRITICAL-001 | Implement JWT validation in FastAPI (verify NextAuth token) or signed HMAC service-to-service auth | 1-2 days |
| 2 | CRITICAL-002 | Rotate all secrets (Stripe, OAuth, AUTH_SECRET). Add `detect-secrets` pre-commit hook | 2 hours |
| 3 | HIGH-001 | Remove password from sessionStorage; implement `POST /auth/mfa/complete` endpoint | 4 hours |
| 4 | HIGH-002 | Add `slowapi` with Redis backend. Tiered rate limits on auth, data, and admin endpoints | 4 hours |

### Phase 2 — This Sprint (1-2 Weeks)

| # | Finding | Action | Effort |
|---|---|---|---|
| 5 | HIGH-003 | Fix SSL cert verification for Railway PostgreSQL (both `session.py` and `alembic/env.py`) | 2 hours |
| 6 | HIGH-004 | Create `middleware.ts` with security headers (CSP, HSTS, X-Frame-Options, Referrer-Policy) | 2 hours |
| 7 | HIGH-005 | Move MFA challenge token from URL params to httpOnly cookie or server session | 3 hours |
| 8 | MEDIUM-001 | Replace `xml.etree.ElementTree` with `defusedxml.ElementTree` in edgar_provider.py | 30 min |
| 9 | MEDIUM-002 | Replace `!=` with `hmac.compare_digest` for admin key in admin.py | 15 min |
| 10 | MEDIUM-003 | Add `require_plan()` dependency to all premium API endpoints | 2 hours |
| 11 | MEDIUM-008 | Decide and enforce public vs. authenticated access for data endpoints | 2 hours |

### Phase 3 — Next Sprint

| # | Finding | Action | Effort |
|---|---|---|---|
| 12 | MEDIUM-004 | Add Stripe webhook idempotency table and check | 2 hours |
| 13 | MEDIUM-007 | Implement structured audit logging (auth, admin, billing events) | 4 hours |
| 14 | MEDIUM-005 | Add integrity checksums to ML model blobs; plan migration from pickle | 4 hours |
| 15 | MEDIUM-006 | Protect session-check endpoint or reduce response to boolean | 30 min |
| 16 | LOW-001 | Remove duplicate `thirteenf_router` registration | 5 min |
| 17 | LOW-002 | Restrict CORS to explicit methods and headers | 15 min |
| 18 | INVESTIGATE-001 | Audit WebSocket authentication in `ws/scores.py` | 1 hour |

### Phase 4 — Hardening (Ongoing)

| # | Action |
|---|---|
| 19 | Add `pip-audit` and `npm audit` to CI pipeline |
| 20 | Pin Docker base images to SHA digests |
| 21 | Pin GitHub Actions to SHA digests |
| 22 | Add Sentry or equivalent error monitoring / APM |
| 23 | Add `productionBrowserSourceMaps: false` to next.config.ts |
| 24 | Implement dynamic testing (OWASP ZAP against staging) |
| 25 | Add Cloudflare or AWS WAF in front of Railway |

---

## 8. Security Code Review Checklist

Use this for every pull request:

### Authentication & Authorization
- [ ] Every new endpoint uses `get_current_user_id` or explicitly documents why it's public
- [ ] Subscription tier checked server-side for premium features (not just client-side gating)
- [ ] Admin endpoints use `_verify_admin_key` with `hmac.compare_digest`
- [ ] No new secrets hardcoded in source code
- [ ] Authentication verified via cryptographic signatures (JWT), not unverified headers

### Input Validation
- [ ] All user inputs validated via Pydantic models
- [ ] Path parameters constrained with regex patterns
- [ ] No raw SQL or string interpolation in queries
- [ ] File uploads validated (type, size, magic bytes)
- [ ] External data formats (XML, JSON) parsed via defused/safe libraries

### Data Exposure
- [ ] API responses don't leak internal IDs, stack traces, or DB schema details
- [ ] Error messages are generic for auth failures (no user enumeration)
- [ ] Sensitive fields (passwords, tokens, keys) never appear in logs
- [ ] No PII or secrets in URL parameters
- [ ] No sensitive data stored in `localStorage` or `sessionStorage`

### Session & Token Security
- [ ] Tokens have expiration (TTL)
- [ ] Tokens are single-use where appropriate
- [ ] No passwords stored in browser storage
- [ ] Cookies use httpOnly, Secure, SameSite flags
- [ ] Challenge tokens not exposed in URLs

### Infrastructure
- [ ] No new ports exposed in Docker/compose
- [ ] Dependencies version-constrained
- [ ] CI/CD secrets not echoed in logs
- [ ] Database migrations are idempotent
- [ ] SSL/TLS connections verify certificates

### Business Logic
- [ ] Subscription gating enforced server-side
- [ ] Webhook handlers are idempotent (event ID tracked)
- [ ] Financial calculations are deterministic (no race conditions)
- [ ] Stripe operations use idempotency keys
- [ ] All string comparisons for secrets use `hmac.compare_digest`

### Serialization
- [ ] No `pickle.loads` on untrusted data without integrity checks
- [ ] XML parsing uses `defusedxml`, not `xml.etree.ElementTree`
- [ ] JSON responses sanitize NaN/Infinity values

---

## 9. Recommended Dynamic Testing (Not Covered by This Audit)

This was a static code review only. The following dynamic tests are recommended:

1. **OWASP ZAP automated scan** against a staging deployment
2. **Burp Suite manual testing** of the authentication flow and MFA bypass scenarios
3. **Nuclei templates** for common FastAPI/Next.js misconfigurations
4. **`pip-audit`** and **`npm audit --audit-level=high`** for dependency CVEs
5. **Load testing** auth endpoints to validate rate limiting once implemented
6. **Penetration test** of the header spoofing fix to confirm JWT validation cannot be bypassed
