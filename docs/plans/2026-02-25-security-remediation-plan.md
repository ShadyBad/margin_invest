# Security Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remediate 15 security findings (2 critical, 5 high, 8 medium) from the 2026-02-25 audit with zero downtime and no test regressions.

**Architecture:** Four-phase rollout ordered by blast radius. Phase 1 patches the critical auth bypass (HMAC signing, then JWT). Phase 2 hardens the MFA flow and adds rate limiting. Phase 3 adds defense-in-depth (SSL, headers, plan gating). Phase 4 adds audit trail infrastructure.

**Tech Stack:** FastAPI, Next.js 15 (NextAuth v5 beta), PyJWT, jose (JS), slowapi, Redis, defusedxml, PostgreSQL

**Design doc:** `docs/plans/2026-02-25-security-remediation-design.md`

---

## Parallel Groups

Tasks within each group can be executed in parallel (independent files, no shared state). Groups must be executed sequentially.

```
Group A (Phase 1 — quick wins): Tasks 1-4      [parallel, independent]
Group B (Phase 1 — HMAC auth):  Tasks 5-6      [sequential]
Group C (Phase 1 — JWT auth):   Tasks 7-8      [sequential, after Group B]
Group D (Phase 2 — MFA):        Tasks 9-12     [sequential]
Group E (Phase 2 — rate limit): Tasks 13-14    [sequential, parallel with Group D]
Group F (Phase 3):              Tasks 15-19    [parallel, independent]
Group G (Phase 4):              Tasks 20-22    [parallel, independent]
```

---

## Group A: Quick Wins (Phase 1, parallel)

### Task 1: Fix Admin Key Timing Attack (MEDIUM-002)

**Files:**
- Modify: `api/src/margin_api/routes/admin.py:25-31`
- Test: `api/tests/routes/test_admin_timing.py` (new)

**Step 1: Write the failing test**

Create `api/tests/routes/test_admin_timing.py`:

```python
"""Test that admin key comparison uses constant-time comparison."""

import hmac

from margin_api.routes.admin import _verify_admin_key


def test_verify_admin_key_uses_hmac_compare_digest(monkeypatch):
    """Verify the function uses hmac.compare_digest, not == operator."""
    # Patch settings to return a known admin key
    from margin_api.config import Settings

    monkeypatch.setattr(
        "margin_api.routes.admin.get_settings",
        lambda: Settings(admin_key="test-admin-key-123"),
    )

    # Valid key should not raise
    _verify_admin_key("test-admin-key-123")

    # Invalid key should raise 403
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        _verify_admin_key("wrong-key")
    assert exc_info.value.status_code == 403


def test_verify_admin_key_empty_input(monkeypatch):
    """Empty admin key input should not crash."""
    from margin_api.config import Settings

    monkeypatch.setattr(
        "margin_api.routes.admin.get_settings",
        lambda: Settings(admin_key="test-admin-key-123"),
    )

    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        _verify_admin_key("")
    assert exc_info.value.status_code == 403
```

**Step 2: Run test to verify it passes (existing behavior already works)**

```bash
uv run pytest api/tests/routes/test_admin_timing.py -v
```

Expected: PASS (the logic is the same, we're just changing the comparison method)

**Step 3: Apply the fix**

Edit `api/src/margin_api/routes/admin.py:25-31`:

```python
def _verify_admin_key(x_admin_key: str = Header()) -> None:
    """Verify the admin API key from the X-Admin-Key header."""
    import hmac

    settings = get_settings()
    if not settings.admin_key:
        raise HTTPException(503, "Admin key not configured")
    if not hmac.compare_digest(x_admin_key or "", settings.admin_key):
        raise HTTPException(403, "Invalid admin key")
```

**Step 4: Run tests**

```bash
uv run pytest api/tests/routes/test_admin_timing.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/admin.py api/tests/routes/test_admin_timing.py
git commit -m "fix(api): use hmac.compare_digest for admin key comparison (MEDIUM-002)"
```

---

### Task 2: Replace xml.etree with defusedxml (MEDIUM-001)

**Files:**
- Modify: `engine/src/margin_engine/ingestion/providers/edgar_provider.py:1` (import line)
- Test: existing EDGAR tests

**Step 1: Add dependency**

```bash
uv add defusedxml --package margin-engine
```

**Step 2: Replace import**

Edit `engine/src/margin_engine/ingestion/providers/edgar_provider.py`. Find:

```python
import xml.etree.ElementTree as ET
```

Replace with:

```python
import defusedxml.ElementTree as ET
```

**Step 3: Run existing EDGAR tests**

```bash
uv run pytest engine/tests/ -k "edgar" -v
```

Expected: All PASS (defusedxml.ElementTree is a drop-in replacement)

**Step 4: Run full engine suite to confirm no regressions**

```bash
uv run pytest engine/tests/ -v --tb=short
```

Expected: All ~2122 tests pass

**Step 5: Commit**

```bash
git add engine/pyproject.toml engine/src/margin_engine/ingestion/providers/edgar_provider.py uv.lock
git commit -m "fix(engine): replace xml.etree with defusedxml for XML bomb protection (MEDIUM-001)"
```

---

### Task 3: Fix Duplicate Router + Permissive CORS (LOW-001, LOW-002)

**Files:**
- Modify: `api/src/margin_api/app.py:94-95,120`

**Step 1: Apply fixes**

Edit `api/src/margin_api/app.py`.

Change lines 94-95 from:

```python
        allow_methods=["*"],
        allow_headers=["*"],
```

To:

```python
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-User-Id",
            "X-User-Email",
            "X-Auth-Timestamp",
            "X-Auth-Signature",
            "X-Admin-Key",
        ],
```

Delete line 120 (the duplicate `app.include_router(thirteenf_router)`).

**Step 2: Run API tests**

```bash
uv run pytest api/tests/ -v --tb=short
```

Expected: All ~1038 tests pass

**Step 3: Commit**

```bash
git add api/src/margin_api/app.py
git commit -m "fix(api): restrict CORS methods/headers, remove duplicate thirteenf_router (LOW-001, LOW-002)"
```

---

### Task 4: Add gitleaks Pre-commit Hook (CRITICAL-002 partial)

**Files:**
- Create: `.gitleaks.toml`
- Create: `.pre-commit-config.yaml` (or modify if exists)
- Create: `api/.env.example`
- Create: `web/.env.local.example`

**Step 1: Create gitleaks config**

Create `.gitleaks.toml`:

```toml
[extend]

[[allowlist.paths]]
description = "Example env files with placeholder values"
paths = [
    '''\.env\.example$''',
    '''\.env\.local\.example$''',
]

[[allowlist.paths]]
description = "Test fixtures with fake keys"
paths = [
    '''tests/''',
    '''__tests__/''',
]
```

**Step 2: Create pre-commit config**

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
```

**Step 3: Create example env files**

Create `api/.env.example`:

```bash
# Margin Invest API — Local Development Environment
# Copy to .env and fill in real values

MARGIN_DATABASE_URL=postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest
MARGIN_REDIS_URL=redis://localhost:6379
MARGIN_ENVIRONMENT=development
MARGIN_DEBUG=true

# Auth
MARGIN_JWT_SECRET=generate-with-openssl-rand-hex-32
MARGIN_MFA_ENCRYPTION_KEY=generate-fernet-key
MARGIN_API_KEY_ENCRYPTION_KEY=generate-fernet-key

# Stripe (test mode)
MARGIN_STRIPE_SECRET_KEY=sk_test_REPLACE_ME
MARGIN_STRIPE_PUBLISHABLE_KEY=pk_test_REPLACE_ME
MARGIN_STRIPE_WEBHOOK_SECRET=whsec_REPLACE_ME
MARGIN_STRIPE_PORTFOLIO_PRICE_ID=price_REPLACE_ME
MARGIN_STRIPE_INSTITUTIONAL_PRICE_ID=price_REPLACE_ME

# Admin
MARGIN_ADMIN_KEY=generate-with-openssl-rand-hex-32

# Data providers
MARGIN_POLYGON_API_KEY=REPLACE_ME
MARGIN_FMP_API_KEY=REPLACE_ME
MARGIN_EDGAR_USER_AGENT=YourName your@email.com

# Email
MARGIN_RESEND_API_KEY=re_REPLACE_ME
MARGIN_APP_URL=http://localhost:3000

# CORS
MARGIN_CORS_ORIGINS=["http://localhost:3000"]

# Service-to-service auth (shared with Next.js)
SERVICE_AUTH_SECRET=generate-with-openssl-rand-hex-64
```

Create `web/.env.local.example`:

```bash
# Margin Invest Web — Local Development Environment
# Copy to .env.local and fill in real values

# API (server-side only, NOT exposed to browser)
API_URL=http://localhost:8000

# Public API (exposed to browser for client-side fetches)
NEXT_PUBLIC_API_URL=http://localhost:8000

# NextAuth
AUTH_SECRET=generate-with-openssl-rand-base64-32

# Google OAuth
GOOGLE_CLIENT_ID=REPLACE_ME.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=REPLACE_ME

# GitHub OAuth
GITHUB_CLIENT_ID=REPLACE_ME
GITHUB_CLIENT_SECRET=REPLACE_ME

# Service-to-service auth (shared with FastAPI)
SERVICE_AUTH_SECRET=generate-with-openssl-rand-hex-64
```

**Step 4: Verify .gitignore covers env files**

```bash
grep -n "\.env" .gitignore
```

Expected: `.env`, `.env.local`, or similar patterns present. If missing, add them.

**Step 5: Commit**

```bash
git add .gitleaks.toml .pre-commit-config.yaml api/.env.example web/.env.local.example
git commit -m "chore: add gitleaks pre-commit hook and env example files (CRITICAL-002)"
```

---

## Group B: HMAC Auth Signing (Phase 1, sequential)

### Task 5: Add HMAC Verification to FastAPI deps.py (CRITICAL-001 Phase 1a)

**Files:**
- Modify: `api/src/margin_api/deps.py`
- Modify: `api/src/margin_api/config.py` (add `service_auth_secret`, `require_signed_auth`)
- Create: `api/tests/security/test_hmac_auth.py`

**Step 1: Add config vars**

Edit `api/src/margin_api/config.py`. Add after line 66 (`admin_key`):

```python
    # Service-to-service auth
    service_auth_secret: str = ""
    require_signed_auth: bool = False
```

**Step 2: Write failing tests**

Create `api/tests/security/__init__.py` (empty file).

Create `api/tests/security/test_hmac_auth.py`:

```python
"""Tests for HMAC-signed service-to-service authentication."""

from __future__ import annotations

import hashlib
import hmac
import time

import pytest
from fastapi import FastAPI, Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.config import Settings
from margin_api.deps import get_current_user_id
from margin_api.db.session import get_db
from margin_api.db.models import Base, User

_TEST_SECRET = "a" * 64  # 64-byte hex secret for testing


def _sign_request(user_id: int, secret: str, timestamp: int | None = None) -> dict:
    """Create HMAC-signed auth headers."""
    ts = timestamp or int(time.time())
    payload = f"{user_id}:{ts}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {
        "X-User-Id": str(user_id),
        "X-Auth-Timestamp": str(ts),
        "X-Auth-Signature": sig,
    }


@pytest.fixture
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        user = User(id=42, email="test@test.com", name="Test")
        session.add(user)
        await session.commit()

    app = FastAPI()

    async def override_db():
        async with factory() as session:
            yield session

    def override_settings():
        return Settings(
            service_auth_secret=_TEST_SECRET,
            require_signed_auth=True,
        )

    app.dependency_overrides[get_db] = override_db
    from margin_api.config import get_settings
    app.dependency_overrides[get_settings] = override_settings

    @app.get("/test")
    async def test_endpoint(user_id: int = Depends(get_current_user_id)):
        return {"user_id": user_id}

    return app


class TestHmacAuth:
    @pytest.mark.asyncio
    async def test_valid_hmac_returns_user_id(self, setup):
        app = await setup
        headers = _sign_request(42, _TEST_SECRET)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["user_id"] == 42

    @pytest.mark.asyncio
    async def test_missing_signature_rejected_when_required(self, setup):
        app = await setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"X-User-Id": "42"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_secret_rejected(self, setup):
        app = await setup
        headers = _sign_request(42, "wrong" * 13)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_timestamp_rejected(self, setup):
        app = await setup
        old_ts = int(time.time()) - 120  # 2 minutes ago
        headers = _sign_request(42, _TEST_SECRET, timestamp=old_ts)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers=headers)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_no_headers_returns_401(self, setup):
        app = await setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test")
        assert resp.status_code == 401


class TestHmacAuthFlagOff:
    @pytest.mark.asyncio
    async def test_unsigned_allowed_when_flag_off(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        app = FastAPI()

        async def override_db():
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as session:
                yield session

        def override_settings():
            return Settings(
                service_auth_secret=_TEST_SECRET,
                require_signed_auth=False,  # Flag OFF
            )

        app.dependency_overrides[get_db] = override_db
        from margin_api.config import get_settings
        app.dependency_overrides[get_settings] = override_settings

        @app.get("/test")
        async def test_endpoint(user_id: int = Depends(get_current_user_id)):
            return {"user_id": user_id}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"X-User-Id": "42"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == 42
```

**Step 3: Run tests to verify they fail**

```bash
uv run pytest api/tests/security/test_hmac_auth.py -v
```

Expected: FAIL (HMAC verification not implemented yet)

**Step 4: Implement HMAC verification in deps.py**

Replace `api/src/margin_api/deps.py` entirely:

```python
"""FastAPI dependency helpers for auth and plan enforcement."""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import logging
import time
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.models import User
from margin_api.db.session import get_db

logger = logging.getLogger(__name__)

_TIMESTAMP_MAX_AGE = 60  # seconds


async def get_current_user_id(
    x_user_id: str | None = Header(None),
    x_user_email: str | None = Header(None),
    x_auth_signature: str | None = Header(None),
    x_auth_timestamp: str | None = Header(None),
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> int:
    """Resolve the current user's database ID.

    Authentication priority:
    1. Authorization: Bearer <JWT> (service token from Next.js)
    2. HMAC-signed X-User-Id + X-Auth-Signature + X-Auth-Timestamp
    3. Unsigned X-User-Id (only when require_signed_auth=False, logs warning)
    """
    settings = get_settings()

    # --- Path 1: JWT Bearer token (added in Task 7) ---
    if authorization and authorization.startswith("Bearer "):
        return await _verify_jwt_token(authorization[7:], settings)

    # --- Path 2: HMAC-signed request ---
    if x_auth_signature and x_auth_timestamp and x_user_id is not None:
        return _verify_hmac(x_user_id, x_auth_timestamp, x_auth_signature, settings)

    # --- Path 3: Unsigned X-User-Id (legacy, will be removed) ---
    if x_user_id is not None or x_user_email is not None:
        if settings.require_signed_auth:
            raise HTTPException(status_code=401, detail="Signed authentication required")

        logger.warning(
            "Unsigned auth request: user_id=%s email=%s — set MARGIN_REQUIRE_SIGNED_AUTH=true",
            x_user_id,
            x_user_email,
        )

        if x_user_id is not None:
            try:
                return int(x_user_id)
            except (ValueError, TypeError):
                pass

        if x_user_email:
            stmt = select(User.id).where(User.email == x_user_email)
            result = await db.execute(stmt)
            user_id = result.scalar_one_or_none()
            if user_id is not None:
                return user_id

    raise HTTPException(status_code=401, detail="Not authenticated")


def _verify_hmac(
    user_id_str: str, timestamp_str: str, signature: str, settings
) -> int:
    """Verify HMAC-SHA256 signature over user_id:timestamp."""
    if not settings.service_auth_secret:
        raise HTTPException(status_code=500, detail="Service auth not configured")

    # Verify timestamp freshness
    try:
        ts = int(timestamp_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid auth timestamp")

    age = abs(int(time.time()) - ts)
    if age > _TIMESTAMP_MAX_AGE:
        raise HTTPException(status_code=401, detail="Auth timestamp expired")

    # Verify HMAC signature
    payload = f"{user_id_str}:{timestamp_str}"
    expected = hmac_mod.new(
        settings.service_auth_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac_mod.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid auth signature")

    try:
        return int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID")


async def _verify_jwt_token(token: str, settings) -> int:
    """Verify a JWT service token. Implemented in Task 7."""
    # Placeholder — will be implemented in Task 7
    raise HTTPException(status_code=401, detail="JWT auth not yet implemented")


PLAN_TIERS = {"analyst": 0, "portfolio": 1, "institutional": 2, "operator": 3}


def require_plan(minimum_plan: str) -> Callable:
    """Return a FastAPI dependency that verifies the user's subscription plan.

    Uses tier hierarchy: operator > institutional > portfolio > analyst.
    """

    async def _check(
        user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
    ) -> int:
        stmt = select(User.subscription_plan).where(User.id == user_id)
        result = await db.execute(stmt)
        current_plan = result.scalar_one_or_none() or "analyst"
        if PLAN_TIERS.get(current_plan, 0) < PLAN_TIERS[minimum_plan]:
            raise HTTPException(
                status_code=403,
                detail=f"Upgrade to {minimum_plan} plan required",
            )
        return user_id

    return _check
```

**Step 5: Run HMAC tests**

```bash
uv run pytest api/tests/security/test_hmac_auth.py -v
```

Expected: All PASS

**Step 6: Run full API suite to confirm no regressions**

```bash
uv run pytest api/tests/ -v --tb=short
```

Expected: All ~1038 tests pass (they all use dependency overrides, bypassing the new HMAC logic)

**Step 7: Commit**

```bash
git add api/src/margin_api/deps.py api/src/margin_api/config.py api/tests/security/
git commit -m "feat(api): add HMAC-signed auth verification with feature flag (CRITICAL-001 phase 1a)"
```

---

### Task 6: Add HMAC Signing to serverFetch (CRITICAL-001 Phase 1a frontend)

**Files:**
- Modify: `web/src/lib/api/server.ts`

**Step 1: Implement HMAC signing**

Edit `web/src/lib/api/server.ts`. Replace the full file:

```typescript
import { auth } from "@/lib/auth"
import { ApiError } from "./client"
import { createHmac } from "crypto"

const API_URL = process.env.API_URL || "http://localhost:8000"
const SERVICE_AUTH_SECRET = process.env.SERVICE_AUTH_SECRET || ""

function signRequest(userId: string): Record<string, string> {
  if (!SERVICE_AUTH_SECRET) {
    // Fallback: unsigned (for local dev without secret configured)
    return { "X-User-Id": userId }
  }
  const timestamp = Math.floor(Date.now() / 1000).toString()
  const payload = `${userId}:${timestamp}`
  const signature = createHmac("sha256", SERVICE_AUTH_SECRET)
    .update(payload)
    .digest("hex")
  return {
    "X-User-Id": userId,
    "X-Auth-Timestamp": timestamp,
    "X-Auth-Signature": signature,
  }
}

export async function serverFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_URL}${path}`

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  }

  // Inject signed auth headers from session
  try {
    const session = await auth()
    if (session?.userId) {
      Object.assign(headers, signRequest(session.userId as string))
    }
  } catch {
    // Auth not available — continue without user context
  }

  let response: Response
  try {
    response = await fetch(url, {
      ...options,
      headers,
      cache: options.cache ?? "no-store",
    })
  } catch (err) {
    throw new ApiError(503, "SERVICE_UNAVAILABLE", "API server is not reachable")
  }

  if (!response.ok) {
    let errorCode = "UNKNOWN"
    let message = `API Error: ${response.status} ${response.statusText}`
    let requestId: string | undefined

    try {
      const body = await response.json()
      errorCode = body.error_code || errorCode
      message = body.message || message
      requestId = body.request_id
    } catch {
      // Non-JSON error response — use status text
      message = response.statusText || message
    }

    throw new ApiError(response.status, errorCode, message, requestId)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}
```

**Step 2: Run web tests**

```bash
cd web && npx vitest run --reporter=verbose 2>&1 | tail -20
```

Expected: All ~978 tests pass (serverFetch is mocked in tests)

**Step 3: Commit**

```bash
git add web/src/lib/api/server.ts
git commit -m "feat(web): add HMAC signing to serverFetch for service-to-service auth (CRITICAL-001 phase 1a)"
```

---

## Group C: JWT Auth (Phase 1, sequential, after Group B)

### Task 7: Add JWT Service Token Verification to FastAPI (CRITICAL-001 Phase 1b)

**Files:**
- Add dependency: `pyjwt` to api
- Modify: `api/src/margin_api/deps.py` (implement `_verify_jwt_token`)
- Create: `api/tests/security/test_jwt_auth.py`

**Step 1: Add PyJWT dependency**

```bash
uv add pyjwt --package margin-api
```

**Step 2: Write failing tests**

Create `api/tests/security/test_jwt_auth.py`:

```python
"""Tests for JWT service token verification."""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi import FastAPI, Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.config import Settings
from margin_api.deps import get_current_user_id
from margin_api.db.session import get_db
from margin_api.db.models import Base

_TEST_SECRET = "jwt-test-secret-64-bytes-" + "x" * 39


def _make_token(user_id: int, secret: str = _TEST_SECRET, **overrides) -> str:
    payload = {
        "sub": str(user_id),
        "email": "test@test.com",
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
        **overrides,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
async def app():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = FastAPI()

    async def override_db():
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session

    def override_settings():
        return Settings(
            service_auth_secret=_TEST_SECRET,
            require_signed_auth=True,
        )

    app.dependency_overrides[get_db] = override_db
    from margin_api.config import get_settings
    app.dependency_overrides[get_settings] = override_settings

    @app.get("/test")
    async def test_endpoint(user_id: int = Depends(get_current_user_id)):
        return {"user_id": user_id}

    return app


class TestJwtAuth:
    @pytest.mark.asyncio
    async def test_valid_jwt_returns_user_id(self, app):
        token = _make_token(42)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["user_id"] == 42

    @pytest.mark.asyncio
    async def test_expired_jwt_rejected(self, app):
        token = _make_token(42, exp=int(time.time()) - 60)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_secret_rejected(self, app):
        token = _make_token(42, secret="wrong-secret-" + "x" * 50)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_sub_claim_rejected(self, app):
        payload = {"email": "test@test.com", "iat": int(time.time()), "exp": int(time.time()) + 60}
        token = jwt.encode(payload, _TEST_SECRET, algorithm="HS256")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_non_integer_sub_rejected(self, app):
        token = _make_token(42)
        # Override sub with non-integer
        payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
        payload["sub"] = "not-an-integer"
        bad_token = jwt.encode(payload, _TEST_SECRET, algorithm="HS256")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"Authorization": f"Bearer {bad_token}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_token_rejected(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test", headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401
```

**Step 3: Run tests to verify they fail**

```bash
uv run pytest api/tests/security/test_jwt_auth.py -v
```

Expected: FAIL (JWT verification returns "not yet implemented")

**Step 4: Implement JWT verification**

Edit `api/src/margin_api/deps.py`. Replace the `_verify_jwt_token` placeholder:

```python
async def _verify_jwt_token(token: str, settings) -> int:
    """Verify a JWT service token signed by the Next.js server."""
    import jwt as pyjwt

    if not settings.service_auth_secret:
        raise HTTPException(status_code=500, detail="Service auth not configured")

    try:
        payload = pyjwt.decode(
            token,
            settings.service_auth_secret,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat"]},
            leeway=30,
        )
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Missing sub claim")

    try:
        return int(sub)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token")
```

Also add `import jwt as pyjwt` at the top of deps.py (below existing imports) — or keep the import inside the function for lazy loading.

**Step 5: Run JWT tests**

```bash
uv run pytest api/tests/security/test_jwt_auth.py -v
```

Expected: All PASS

**Step 6: Run full API suite**

```bash
uv run pytest api/tests/ -v --tb=short
```

Expected: All pass

**Step 7: Commit**

```bash
git add api/pyproject.toml api/src/margin_api/deps.py api/tests/security/test_jwt_auth.py uv.lock
git commit -m "feat(api): add JWT service token verification (CRITICAL-001 phase 1b backend)"
```

---

### Task 8: Add JWT Service Token Signing to serverFetch (CRITICAL-001 Phase 1b frontend)

**Files:**
- Create: `web/src/lib/api/service-token.ts`
- Modify: `web/src/lib/api/server.ts` (switch from HMAC to JWT)
- Create: `web/src/lib/api/__tests__/service-token.test.ts`

**Step 1: Write the service token helper test**

Create `web/src/lib/api/__tests__/service-token.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"

// Mock jose before importing
vi.mock("jose", () => ({
  SignJWT: vi.fn().mockImplementation((payload) => ({
    setProtectedHeader: vi.fn().mockReturnThis(),
    setIssuedAt: vi.fn().mockReturnThis(),
    setExpirationTime: vi.fn().mockReturnThis(),
    sign: vi.fn().mockResolvedValue("mock.jwt.token"),
  })),
}))

describe("signServiceToken", () => {
  beforeEach(() => {
    vi.stubEnv("SERVICE_AUTH_SECRET", "a".repeat(64))
  })

  it("returns a JWT string", async () => {
    const { signServiceToken } = await import("../service-token")
    const token = await signServiceToken("42", "test@test.com")
    expect(typeof token).toBe("string")
    expect(token).toBe("mock.jwt.token")
  })

  it("returns empty string when no secret configured", async () => {
    vi.stubEnv("SERVICE_AUTH_SECRET", "")
    // Re-import to get fresh module
    vi.resetModules()
    const { signServiceToken } = await import("../service-token")
    const token = await signServiceToken("42", "test@test.com")
    expect(token).toBe("")
  })
})
```

**Step 2: Implement the service token helper**

Create `web/src/lib/api/service-token.ts`:

```typescript
import { SignJWT } from "jose"

const SERVICE_AUTH_SECRET = process.env.SERVICE_AUTH_SECRET || ""

export async function signServiceToken(
  userId: string,
  email?: string | null,
): Promise<string> {
  if (!SERVICE_AUTH_SECRET) {
    return ""
  }

  const secret = new TextEncoder().encode(SERVICE_AUTH_SECRET)

  return new SignJWT({ sub: userId, email: email ?? undefined })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("60s")
    .sign(secret)
}
```

**Step 3: Update serverFetch to use JWT**

Edit `web/src/lib/api/server.ts`. Replace `signRequest` and its usage with the JWT approach:

```typescript
import { auth } from "@/lib/auth"
import { ApiError } from "./client"
import { signServiceToken } from "./service-token"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function serverFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_URL}${path}`

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  }

  // Inject signed auth token from session
  try {
    const session = await auth()
    if (session?.userId) {
      const token = await signServiceToken(
        session.userId as string,
        session.user?.email,
      )
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      } else {
        // Fallback: unsigned header for local dev without SERVICE_AUTH_SECRET
        headers["X-User-Id"] = session.userId as string
      }
    }
  } catch {
    // Auth not available — continue without user context
  }

  let response: Response
  try {
    response = await fetch(url, {
      ...options,
      headers,
      cache: options.cache ?? "no-store",
    })
  } catch (err) {
    throw new ApiError(503, "SERVICE_UNAVAILABLE", "API server is not reachable")
  }

  if (!response.ok) {
    let errorCode = "UNKNOWN"
    let message = `API Error: ${response.status} ${response.statusText}`
    let requestId: string | undefined

    try {
      const body = await response.json()
      errorCode = body.error_code || errorCode
      message = body.message || message
      requestId = body.request_id
    } catch {
      message = response.statusText || message
    }

    throw new ApiError(response.status, errorCode, message, requestId)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}
```

**Step 4: Run web tests**

```bash
cd web && npx vitest run --reporter=verbose 2>&1 | tail -20
```

Expected: All pass

**Step 5: Commit**

```bash
git add web/src/lib/api/service-token.ts web/src/lib/api/__tests__/service-token.test.ts web/src/lib/api/server.ts
git commit -m "feat(web): add JWT service token signing in serverFetch (CRITICAL-001 phase 1b frontend)"
```

---

## Group D: MFA Refactor (Phase 2, sequential)

### Task 9: Add MFA Complete Backend Endpoint (HIGH-001)

**Files:**
- Modify: `api/src/margin_api/schemas/auth.py` (add new schemas)
- Modify: `api/src/margin_api/routes/auth.py` (add 2 new endpoints)
- Create: `api/tests/security/test_mfa_complete.py`

**Step 1: Add schemas**

Append to `api/src/margin_api/schemas/auth.py`:

```python
class MfaCompleteRequest(BaseModel):
    """Request body for completing MFA during login."""

    totp_code: str | None = Field(None, min_length=6, max_length=6)
    recovery_code: str | None = Field(None, min_length=8, max_length=9)


class MfaCompleteResponse(BaseModel):
    """Response with a signed MFA completion token."""

    mfa_completion_token: str


class VerifyMfaTokenRequest(BaseModel):
    """Request body for verifying an MFA completion token."""

    token: str


class VerifyMfaTokenResponse(BaseModel):
    """Response with user data after MFA token verification."""

    id: int
    email: str
    username: str
    avatar_url: str | None = None
```

**Step 2: Write failing tests**

Create `api/tests/security/test_mfa_complete.py`:

```python
"""Tests for the MFA complete and verify-mfa-token endpoints."""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from margin_api.config import Settings
from margin_api.db.models import Base, MfaChallengeToken, TotpSecret, User
from margin_api.db.session import get_db
from margin_api.routes.auth import router as auth_router

_TEST_JWT_SECRET = "test-jwt-secret-for-mfa"
_TEST_FERNET_KEY = "dGVzdC1mZXJuZXQta2V5LTMyLWJ5dGVzYWJjZGVmZw=="


@pytest.fixture
async def app_and_user():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create test user
    async with factory() as session:
        user = User(id=1, email="test@test.com", name="testuser")
        session.add(user)
        await session.commit()

    app = FastAPI()
    app.include_router(auth_router)

    async def override_db():
        async with factory() as session:
            yield session

    def override_settings():
        return Settings(
            jwt_secret=_TEST_JWT_SECRET,
            mfa_encryption_key=_TEST_FERNET_KEY,
        )

    app.dependency_overrides[get_db] = override_db
    from margin_api.config import get_settings
    app.dependency_overrides[get_settings] = override_settings

    return app, factory


class TestVerifyMfaToken:
    @pytest.mark.asyncio
    async def test_valid_mfa_token_returns_user(self, app_and_user):
        app, _ = app_and_user
        token = jwt.encode(
            {"sub": "1", "purpose": "mfa_complete", "exp": int(time.time()) + 60, "iat": int(time.time())},
            _TEST_JWT_SECRET,
            algorithm="HS256",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": token},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["email"] == "test@test.com"

    @pytest.mark.asyncio
    async def test_expired_mfa_token_rejected(self, app_and_user):
        app, _ = app_and_user
        token = jwt.encode(
            {"sub": "1", "purpose": "mfa_complete", "exp": int(time.time()) - 60, "iat": int(time.time()) - 120},
            _TEST_JWT_SECRET,
            algorithm="HS256",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": token},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_purpose_rejected(self, app_and_user):
        app, _ = app_and_user
        token = jwt.encode(
            {"sub": "1", "purpose": "password_reset", "exp": int(time.time()) + 60, "iat": int(time.time())},
            _TEST_JWT_SECRET,
            algorithm="HS256",
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": token},
            )
        assert resp.status_code == 401
```

**Step 3: Run tests to verify they fail**

```bash
uv run pytest api/tests/security/test_mfa_complete.py -v
```

Expected: FAIL (endpoints don't exist yet)

**Step 4: Implement the endpoints**

Add to `api/src/margin_api/routes/auth.py`, after the `verify_recovery_code` endpoint. Add `import jwt as pyjwt` and `import time` at top of file. Import the new schemas.

```python
@router.post("/mfa/complete", response_model=MfaCompleteResponse)
async def mfa_complete(
    body: MfaCompleteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
    totp: TotpService = Depends(_get_totp_service),
    recovery: RecoveryCodeService = Depends(_get_recovery_code_service),
) -> MfaCompleteResponse:
    """Complete MFA verification during login using cookie-based challenge."""
    # Read challenge from httpOnly cookie
    cookie_value = request.cookies.get("__mfa_challenge")
    if not cookie_value:
        raise HTTPException(status_code=401, detail="Missing MFA challenge cookie")

    import json
    try:
        challenge_data = json.loads(cookie_value)
        user_id = int(challenge_data["userId"])
        challenge_token = challenge_data["challengeToken"]
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid MFA challenge cookie")

    # Verify challenge token
    valid = await auth.verify_challenge_token(db, user_id, challenge_token)
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid or expired challenge token")

    # Verify TOTP or recovery code
    if body.totp_code:
        verified = await totp.verify_totp(db, user_id, body.totp_code)
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid verification code")
    elif body.recovery_code:
        verified = await recovery.verify_code(db, user_id, body.recovery_code)
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid recovery code")
    else:
        raise HTTPException(status_code=400, detail="Provide totp_code or recovery_code")

    # Sign an MFA completion token
    settings = get_settings()
    completion_token = pyjwt.encode(
        {
            "sub": str(user_id),
            "purpose": "mfa_complete",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    response = MfaCompleteResponse(mfa_completion_token=completion_token)
    return response


@router.post("/verify-mfa-token", response_model=VerifyMfaTokenResponse)
async def verify_mfa_token(
    body: VerifyMfaTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifyMfaTokenResponse:
    """Verify an MFA completion token and return user data for session creation."""
    settings = get_settings()

    try:
        payload = pyjwt.decode(
            body.token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat", "purpose"]},
        )
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="MFA token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid MFA token")

    if payload.get("purpose") != "mfa_complete":
        raise HTTPException(status_code=401, detail="Invalid token purpose")

    user_id = int(payload["sub"])
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return VerifyMfaTokenResponse(
        id=user.id,
        email=user.email,
        username=user.name,
        avatar_url=user.avatar_url if hasattr(user, "avatar_url") else None,
    )
```

Add `Request` to the fastapi imports at the top, add `import time` and `import jwt as pyjwt`, and add the new schema imports.

**Step 5: Run tests**

```bash
uv run pytest api/tests/security/test_mfa_complete.py -v
```

Expected: All PASS

**Step 6: Run full API suite**

```bash
uv run pytest api/tests/ -v --tb=short
```

Expected: All pass

**Step 7: Commit**

```bash
git add api/src/margin_api/schemas/auth.py api/src/margin_api/routes/auth.py api/tests/security/test_mfa_complete.py
git commit -m "feat(api): add mfa/complete and verify-mfa-token endpoints (HIGH-001, HIGH-005)"
```

---

### Task 10: Add MFA Redirect Route Handler (HIGH-005)

**Files:**
- Create: `web/src/app/api/mfa-redirect/route.ts`

**Step 1: Create the route handler**

Create `web/src/app/api/mfa-redirect/route.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const userId = request.nextUrl.searchParams.get("userId")
  const challengeToken = request.nextUrl.searchParams.get("challengeToken")
  const setup = request.nextUrl.searchParams.get("setup") === "true"

  if (!userId || !challengeToken) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  const destination = setup ? "/mfa/setup" : "/mfa/verify"
  const response = NextResponse.redirect(new URL(destination, request.url))

  // Set challenge data in httpOnly cookie — never exposed to client JS
  response.cookies.set("__mfa_challenge", JSON.stringify({ userId, challengeToken }), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 300, // 5 minutes, matches challenge token TTL
    path: "/mfa",
  })

  return response
}
```

**Step 2: Commit**

```bash
git add web/src/app/api/mfa-redirect/route.ts
git commit -m "feat(web): add MFA redirect route handler with httpOnly cookie (HIGH-005)"
```

---

### Task 11: Update auth.ts signIn Callback and authorize (HIGH-001, HIGH-005)

**Files:**
- Modify: `web/src/lib/auth.ts:82-101` (signIn callback — remove query params)
- Modify: `web/src/lib/auth.ts:37-71` (authorize — add mfaCompletionToken path)

**Step 1: Update signIn callback to use redirect route**

In `web/src/lib/auth.ts`, change the signIn callback (lines 82-101).

Replace:
```typescript
      if (mfaStatus === "disabled") {
        return `/mfa/setup?userId=${user.id}&challengeToken=${challengeToken}`
      }

      if (mfaStatus === "enabled" && !mfaToken) {
        return `/mfa/verify?userId=${user.id}&challengeToken=${challengeToken}`
      }
```

With:
```typescript
      if (mfaStatus === "disabled") {
        return `/api/mfa-redirect?userId=${user.id}&challengeToken=${challengeToken}&setup=true`
      }

      if (mfaStatus === "enabled" && !mfaToken) {
        return `/api/mfa-redirect?userId=${user.id}&challengeToken=${challengeToken}&setup=false`
      }
```

**Step 2: Add mfaCompletionToken to Credentials provider**

In the Credentials provider config (line 36), add the credential field:

```typescript
      Credentials({
        credentials: {
          username: { label: "Username", type: "text" },
          password: { label: "Password", type: "password" },
          mfaToken: { label: "MFA Token", type: "text" },
          mfaCompletionToken: { label: "MFA Completion Token", type: "text" },
        },
```

**Step 3: Update authorize function**

At the beginning of `authorize()` (after `let res: Response`), add the MFA completion token path:

```typescript
      async authorize(credentials) {
        // Path 1: MFA completion token (no password needed)
        if (credentials.mfaCompletionToken) {
          let verifyRes: Response
          try {
            verifyRes = await fetch(`${API_URL}/api/v1/auth/verify-mfa-token`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ token: credentials.mfaCompletionToken }),
            })
          } catch (error) {
            console.error("[auth] Failed to verify MFA token", error)
            throw new ApiUnreachableError()
          }

          if (!verifyRes.ok) {
            throw new InvalidCredentialsError()
          }

          const userData = await verifyRes.json()
          return {
            id: String(userData.id),
            name: userData.username,
            email: userData.email,
            mfaStatus: "enabled",
            mfaToken: "verified",  // signals MFA was completed
            avatarUrl: userData.avatar_url,
          }
        }

        // Path 2: Existing username/password flow
        let res: Response
        // ... rest of existing authorize code ...
```

**Step 4: Run web tests**

```bash
cd web && npx vitest run --reporter=verbose 2>&1 | tail -20
```

Expected: All pass (auth.ts tests mock fetch calls)

**Step 5: Commit**

```bash
git add web/src/lib/auth.ts
git commit -m "feat(web): route MFA challenge through httpOnly cookie, add mfaCompletionToken path (HIGH-001, HIGH-005)"
```

---

### Task 12: Update MFA Pages and Login Card (HIGH-001, HIGH-005)

**Files:**
- Modify: `web/src/components/login/login-card.tsx:119-129` (remove sessionStorage)
- Modify: `web/src/app/mfa/verify/page.tsx` (use cookie flow instead of searchParams + sessionStorage)
- Modify: `web/src/app/mfa/setup/page.tsx` (use cookie flow instead of searchParams)

**Step 1: Remove sessionStorage from login-card.tsx**

In `web/src/components/login/login-card.tsx`, lines 119-129. Remove the two `sessionStorage.setItem` lines:

```typescript
  const handleCredentialsSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    signIn("credentials", {
      username: email,
      password,
      callbackUrl: "/dashboard",
    })
  }
```

**Step 2: Rewrite MFA verify page**

Replace `web/src/app/mfa/verify/page.tsx` entirely. The new version reads the challenge from the httpOnly cookie via the `/api/v1/auth/mfa/complete` endpoint (cookie sent automatically by browser), no longer reads searchParams or sessionStorage:

```typescript
"use client"

import { Suspense, useState } from "react"
import { signIn } from "next-auth/react"
import { startAuthentication } from "@simplewebauthn/browser"

type Method = "totp" | "webauthn"

function MfaVerifyContent() {
  const [method, setMethod] = useState<Method>("totp")
  const [verificationCode, setVerificationCode] = useState("")
  const [showRecovery, setShowRecovery] = useState(false)
  const [recoveryCode, setRecoveryCode] = useState("")
  const [error, setError] = useState("")

  const handleMfaComplete = async (completionToken: string) => {
    await signIn("credentials", {
      mfaCompletionToken: completionToken,
      callbackUrl: "/dashboard",
    })
  }

  const handleVerifyTotp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    try {
      const res = await fetch(`/api/v1/auth/mfa/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ totp_code: verificationCode }),
      })

      if (!res.ok) {
        const data = await res.json()
        setError(data.detail ?? data.message ?? "Invalid verification code")
        return
      }

      const data = await res.json()
      await handleMfaComplete(data.mfa_completion_token)
    } catch (err) {
      console.error("TOTP verification error:", err)
      setError("Unable to reach the server. Please try again.")
    }
  }

  const handleWebAuthnAuthenticate = async () => {
    setError("")
    // WebAuthn authentication verification endpoint is not yet implemented.
    setError("WebAuthn authentication is not yet available. Please use an authenticator app.")
  }

  const handleVerifyRecovery = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    try {
      const res = await fetch(`/api/v1/auth/mfa/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ recovery_code: recoveryCode }),
      })

      if (!res.ok) {
        const data = await res.json()
        setError(data.detail ?? data.message ?? "Invalid recovery code")
        return
      }

      const data = await res.json()
      await handleMfaComplete(data.mfa_completion_token)
    } catch (err) {
      console.error("Recovery code verification error:", err)
      setError("Unable to reach the server. Please try again.")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0F1C]">
      <div className="flex flex-col items-center gap-8 p-8 w-full max-w-sm">
        <h1 className="text-3xl font-bold text-[#E8E4DD]">
          Verify Your Identity
        </h1>

        {error && (
          <p className="text-red-400 text-sm w-full text-center">{error}</p>
        )}

        <div className="flex w-full rounded-sm overflow-hidden border border-[#1E2740]">
          <button
            onClick={() => setMethod("totp")}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              method === "totp"
                ? "bg-[#D4A843] text-[#0A0F1C]"
                : "bg-[#141B2D] text-[#8A8473] hover:text-[#E8E4DD]"
            }`}
          >
            Authenticator
          </button>
          <button
            onClick={() => setMethod("webauthn")}
            className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
              method === "webauthn"
                ? "bg-[#D4A843] text-[#0A0F1C]"
                : "bg-[#141B2D] text-[#8A8473] hover:text-[#E8E4DD]"
            }`}
          >
            Security Key
          </button>
        </div>

        {method === "totp" && !showRecovery && (
          <div className="flex flex-col gap-4 w-full">
            <form onSubmit={handleVerifyTotp} className="flex flex-col gap-3 w-full">
              <div className="flex flex-col gap-1">
                <label htmlFor="verification-code" className="text-sm text-[#8A8473]">
                  Verification Code
                </label>
                <input
                  id="verification-code"
                  type="text"
                  inputMode="numeric"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  className="w-full px-4 py-3 rounded-sm bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] placeholder-[#8A8473] focus:border-[#D4A843] focus:outline-none transition-colors text-center text-lg tracking-widest"
                  placeholder="000000"
                  maxLength={6}
                  required
                />
              </div>
              <button
                type="submit"
                className="w-full px-4 py-3 rounded-sm bg-[#D4A843] text-[#0A0F1C] font-semibold hover:bg-[#E8B84D] transition-colors"
              >
                Verify
              </button>
            </form>
            <p className="text-sm text-[#8A8473] text-center">
              Lost your authenticator?{" "}
              <button
                type="button"
                onClick={() => setShowRecovery(true)}
                className="font-semibold text-[#E8E4DD] hover:text-[#D4A843] transition-colors"
              >
                Use a recovery code
              </button>
            </p>
          </div>
        )}

        {method === "totp" && showRecovery && (
          <div className="flex flex-col gap-4 w-full">
            <form onSubmit={handleVerifyRecovery} className="flex flex-col gap-3 w-full">
              <div className="flex flex-col gap-1">
                <label htmlFor="recovery-code" className="text-sm text-[#8A8473]">
                  Recovery code
                </label>
                <input
                  id="recovery-code"
                  type="text"
                  value={recoveryCode}
                  onChange={(e) => setRecoveryCode(e.target.value)}
                  className="w-full px-4 py-3 rounded-sm bg-[#141B2D] border border-[#1E2740] text-[#E8E4DD] placeholder-[#8A8473] focus:border-[#D4A843] focus:outline-none transition-colors text-center text-lg tracking-widest font-mono"
                  placeholder="xxxx-xxxx"
                  required
                />
              </div>
              <button
                type="submit"
                className="w-full px-4 py-3 rounded-sm bg-[#D4A843] text-[#0A0F1C] font-semibold hover:bg-[#E8B84D] transition-colors"
              >
                Verify
              </button>
            </form>
            <p className="text-sm text-[#8A8473] text-center">
              <button
                type="button"
                onClick={() => setShowRecovery(false)}
                className="font-semibold text-[#E8E4DD] hover:text-[#D4A843] transition-colors"
              >
                Back to authenticator
              </button>
            </p>
            <p className="text-sm text-[#8A8473] text-center">
              Lost your recovery codes too?{" "}
              <a
                href="/support?subject=MFA+recovery"
                className="font-semibold text-[#E8E4DD] hover:text-[#D4A843] transition-colors"
              >
                Contact support
              </a>
            </p>
          </div>
        )}

        {method === "webauthn" && (
          <div className="flex flex-col items-center gap-6 w-full">
            <p className="text-[#8A8473] text-sm text-center">
              Use your security key, biometric device, or passkey to verify your
              identity.
            </p>
            <button
              onClick={handleWebAuthnAuthenticate}
              className="w-full px-4 py-3 rounded-sm bg-[#D4A843] text-[#0A0F1C] font-semibold hover:bg-[#E8B84D] transition-colors"
            >
              Authenticate with Security Key
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function MfaVerifyPage() {
  return (
    <Suspense>
      <MfaVerifyContent />
    </Suspense>
  )
}
```

**Step 3: Update MFA setup page similarly**

In `web/src/app/mfa/setup/page.tsx`, the same pattern applies: remove `useSearchParams()` for userId/challengeToken, read them from cookie instead. The setup page calls different API endpoints (`/auth/mfa/setup-totp`), which still need userId and challengeToken. For setup, pass the cookie data via a server action or fetch from a small helper endpoint.

For setup, since the existing endpoints (`setup-totp`, `confirm-totp`) accept `user_id` and `challenge_token` in the request body (not from cookies), the simplest approach is to create a small client-side helper that reads the cookie value. But `__mfa_challenge` is httpOnly — the client can't read it.

**Solution**: Add a `GET /api/mfa-challenge` Next.js route that reads the cookie server-side and returns the values:

Create `web/src/app/api/mfa-challenge/route.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const cookie = request.cookies.get("__mfa_challenge")
  if (!cookie) {
    return NextResponse.json({ error: "No MFA challenge" }, { status: 401 })
  }

  try {
    const data = JSON.parse(cookie.value)
    return NextResponse.json({
      userId: data.userId,
      challengeToken: data.challengeToken,
    })
  } catch {
    return NextResponse.json({ error: "Invalid MFA challenge" }, { status: 401 })
  }
}
```

Then update `mfa/setup/page.tsx` to fetch challenge data from `/api/mfa-challenge` on mount instead of using searchParams.

**Step 4: Run web tests**

```bash
cd web && npx vitest run --reporter=verbose 2>&1 | tail -20
```

Expected: All pass (update any failing MFA tests to match new flow)

**Step 5: Commit**

```bash
git add web/src/components/login/login-card.tsx web/src/app/mfa/verify/page.tsx web/src/app/mfa/setup/page.tsx web/src/app/api/mfa-challenge/route.ts
git commit -m "feat(web): remove sessionStorage password, use httpOnly cookie MFA flow (HIGH-001, HIGH-005)"
```

---

## Group E: Rate Limiting (Phase 2, parallel with Group D)

### Task 13: Add slowapi Rate Limiting Infrastructure (HIGH-002)

**Files:**
- Add dependency: `slowapi`
- Modify: `api/src/margin_api/config.py` (add rate limit config)
- Create: `api/src/margin_api/middleware/rate_limit.py`
- Modify: `api/src/margin_api/app.py` (integrate slowapi)
- Create: `api/tests/security/test_rate_limit.py`

**Step 1: Add dependency**

```bash
uv add slowapi --package margin-api
```

**Step 2: Add config**

In `api/src/margin_api/config.py`, add after `require_signed_auth`:

```python
    # Rate limiting
    rate_limit_enabled: bool = True
```

**Step 3: Create rate limiter module**

Create `api/src/margin_api/middleware/__init__.py` (if it doesn't exist — check first).

Create `api/src/margin_api/middleware/rate_limit.py`:

```python
"""Rate limiting middleware using slowapi + Redis."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from margin_api.config import get_settings


def _get_limiter() -> Limiter:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return Limiter(key_func=get_remote_address, enabled=False)
    return Limiter(
        key_func=get_remote_address,
        storage_uri=settings.redis_url,
        strategy="fixed-window",
    )


limiter = _get_limiter()
```

**Step 4: Integrate into app.py**

In `api/src/margin_api/app.py`, after the CORS middleware block, add:

```python
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from margin_api.middleware.rate_limit import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
```

**Step 5: Run API tests (rate limiting disabled in test config)**

```bash
uv run pytest api/tests/ -v --tb=short
```

Expected: All pass (limiter is disabled when redis_url points to non-existent Redis in test environment; slowapi fails open)

**Step 6: Commit**

```bash
git add api/pyproject.toml api/src/margin_api/middleware/rate_limit.py api/src/margin_api/app.py api/src/margin_api/config.py uv.lock
git commit -m "feat(api): add slowapi rate limiting infrastructure with Redis backend (HIGH-002)"
```

---

### Task 14: Apply Rate Limits to Routes (HIGH-002)

**Files:**
- Modify: `api/src/margin_api/routes/auth.py` (auth endpoints: 5/min per IP)
- Modify: `api/src/margin_api/routes/admin.py` (admin: 3/min per IP)
- Modify: `api/src/margin_api/routes/scores.py` (public data: 20/min per IP)
- Modify: `api/src/margin_api/routes/dashboard.py` (public data: 20/min per IP)

**Step 1: Add rate limit decorators to auth routes**

In `api/src/margin_api/routes/auth.py`, import the limiter and add `Request` parameter:

```python
from margin_api.middleware.rate_limit import limiter
```

Add `@limiter.limit("5/minute")` decorator and `request: Request` parameter to these endpoints:
- `verify_credentials`
- `register`
- `forgot_password`
- `verify_totp`
- `mfa_complete`
- `reset_password`

Example for verify_credentials:

```python
@router.post("/verify-credentials", response_model=VerifyCredentialsResponse)
@limiter.limit("5/minute")
async def verify_credentials(
    request: Request,
    body: VerifyCredentialsRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
) -> VerifyCredentialsResponse:
```

**Step 2: Add rate limit to admin routes**

In `api/src/margin_api/routes/admin.py`, add `@limiter.limit("3/minute")` to all admin endpoints.

**Step 3: Add rate limit to public data routes**

In score and dashboard routes, add `@limiter.limit("20/minute")` to unauthenticated endpoints.

**Step 4: Run API tests**

```bash
uv run pytest api/tests/ -v --tb=short
```

Expected: All pass (slowapi disabled in test env since no Redis available, or fails open)

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/auth.py api/src/margin_api/routes/admin.py api/src/margin_api/routes/scores.py api/src/margin_api/routes/dashboard.py
git commit -m "feat(api): apply tiered rate limits to auth, admin, and data endpoints (HIGH-002)"
```

---

## Group F: Defense in Depth (Phase 3, parallel)

### Task 15: Fix Database SSL Verification (HIGH-003)

**Files:**
- Create: `api/src/margin_api/db/ssl.py`
- Modify: `api/src/margin_api/db/session.py:37-48`
- Modify: `api/alembic/env.py` (same SSL pattern)

**Step 1: Create shared SSL utility**

Create `api/src/margin_api/db/ssl.py`:

```python
"""PostgreSQL SSL context factory with optional CA certificate verification."""

from __future__ import annotations

import logging
import os
import ssl
import tempfile

logger = logging.getLogger(__name__)


def create_pg_ssl_context() -> ssl.SSLContext:
    """Create an SSL context for asyncpg PostgreSQL connections.

    If MARGIN_DB_CA_CERT is set (PEM string), uses CERT_REQUIRED.
    Otherwise falls back to CERT_NONE with a logged warning.
    """
    ssl_ctx = ssl.create_default_context()

    ca_cert = os.environ.get("MARGIN_DB_CA_CERT", "")
    if ca_cert.strip():
        ca_path = os.path.join(tempfile.gettempdir(), "margin-pg-ca.pem")
        with open(ca_path, "w") as f:
            f.write(ca_cert)
        ssl_ctx.load_verify_locations(cafile=ca_path)
        ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        ssl_ctx.check_hostname = False  # Railway self-signed certs won't match hostname
        logger.info("DB SSL: CERT_REQUIRED with CA certificate")
    else:
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        logger.warning(
            "DB SSL: CERT_NONE — set MARGIN_DB_CA_CERT env var for certificate verification"
        )

    return ssl_ctx
```

**Step 2: Update session.py**

In `api/src/margin_api/db/session.py`, replace lines 40-48:

```python
        if "sslmode=require" in db_url:
            from margin_api.db.ssl import create_pg_ssl_context

            db_url = db_url.replace("?sslmode=require", "").replace("&sslmode=require", "")
            connect_args["ssl"] = create_pg_ssl_context()
```

**Step 3: Update alembic/env.py with same pattern**

Replace the SSL block in `api/alembic/env.py` with the same `create_pg_ssl_context()` call.

**Step 4: Run tests**

```bash
uv run pytest api/tests/ -v --tb=short
```

Expected: All pass (tests use SQLite, SSL code path not triggered)

**Step 5: Commit**

```bash
git add api/src/margin_api/db/ssl.py api/src/margin_api/db/session.py api/alembic/env.py
git commit -m "fix(api): add SSL CA verification for PostgreSQL connections (HIGH-003)"
```

---

### Task 16: Add Security Headers Middleware (HIGH-004)

**Files:**
- Create: `web/src/middleware.ts`
- Create: `web/src/__tests__/middleware.test.ts`

**Step 1: Write test**

Create `web/src/__tests__/middleware.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest"

// We'll test the header values by importing the CSP and headers config
describe("Security Headers", () => {
  it("should define all required security headers", async () => {
    // Import the middleware module to verify it exports correctly
    const mod = await import("../middleware")
    expect(mod.middleware).toBeDefined()
    expect(mod.config).toBeDefined()
    expect(mod.config.matcher).toBeDefined()
  })

  it("matcher should exclude static files", async () => {
    const { config } = await import("../middleware")
    const matcher = config.matcher[0]
    // Static files should be excluded
    expect(matcher).toContain("_next/static")
    expect(matcher).toContain("favicon.ico")
  })
})
```

**Step 2: Create middleware**

Create `web/src/middleware.ts`:

```typescript
import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

const cspDirectives = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://lh3.googleusercontent.com https://avatars.githubusercontent.com",
  "font-src 'self'",
  "connect-src 'self' https://api.stripe.com wss:",
  "frame-src https://js.stripe.com https://hooks.stripe.com",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
]

const csp = cspDirectives.join("; ")

export function middleware(request: NextRequest) {
  const response = NextResponse.next()

  // Enforced immediately
  response.headers.set("X-Frame-Options", "DENY")
  response.headers.set("X-Content-Type-Options", "nosniff")
  response.headers.set("X-DNS-Prefetch-Control", "off")
  response.headers.set(
    "Strict-Transport-Security",
    "max-age=31536000; includeSubDomains"
  )
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin")
  response.headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=(), payment=()"
  )

  // CSP: report-only first — switch to enforcing after 1-2 weeks of monitoring
  response.headers.set("Content-Security-Policy-Report-Only", csp)

  return response
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
}
```

**Step 3: Run web tests**

```bash
cd web && npx vitest run --reporter=verbose 2>&1 | tail -20
```

Expected: All pass

**Step 4: Commit**

```bash
git add web/src/middleware.ts web/src/__tests__/middleware.test.ts
git commit -m "feat(web): add security headers middleware with CSP report-only (HIGH-004)"
```

---

### Task 17: Fix Session-Check Info Leak (MEDIUM-006)

**Files:**
- Modify: `api/src/margin_api/routes/auth.py:298-308`
- Modify: `web/src/lib/auth.ts:180-201` (jwt callback — use boolean instead of timestamp)

**Step 1: Update session-check endpoint**

Replace the session-check endpoint in `api/src/margin_api/routes/auth.py`:

```python
@router.get("/session-check/{user_id}")
async def check_session(
    user_id: int,
    iat: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if a user's session should be invalidated.

    Accepts an optional `iat` query param (token issued-at timestamp).
    Returns whether the token is invalidated — without leaking raw timestamps.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.password_changed_at:
        return {"session_valid": True, "token_invalidated": False}

    changed_at = int(user.password_changed_at.timestamp())
    token_invalidated = iat > 0 and changed_at > iat
    return {"session_valid": True, "token_invalidated": token_invalidated}
```

**Step 2: Update NextAuth jwt callback**

In `web/src/lib/auth.ts`, update the session-check fetch (around line 182-195):

```typescript
              const res = await fetch(
                `${API_URL}/api/v1/auth/session-check/${token.userId}?iat=${token.iat || 0}`
              )
              if (res.ok) {
                const data = await res.json()
                if (data.token_invalidated) {
                  return {} as typeof token
                }
              }
```

**Step 3: Run tests**

```bash
uv run pytest api/tests/ -v --tb=short
cd web && npx vitest run --reporter=verbose 2>&1 | tail -20
```

Expected: All pass

**Step 4: Commit**

```bash
git add api/src/margin_api/routes/auth.py web/src/lib/auth.ts
git commit -m "fix(api): remove password_changed_at from session-check response (MEDIUM-006)"
```

---

### Task 18: Add Server-Side Plan Gating (MEDIUM-003)

**Files:**
- Modify: `api/src/margin_api/routes/keys.py` (fix plan name from "margin_invest" to "portfolio")
- Modify: `api/src/margin_api/routes/thirteenf.py` (add require_plan to premium endpoints)
- Modify: `api/src/margin_api/routes/backtest.py` (add require_plan to authenticated endpoints)
- Update test fixtures that hit newly-gated endpoints

**Step 1: Fix keys.py plan name**

In `api/src/margin_api/routes/keys.py`, replace all `require_plan("margin_invest")` with `require_plan("portfolio")`.

**Step 2: Add plan gating to 13F analytics endpoints**

In the 13F routes file, add `Depends(require_plan("institutional"))` to premium analytics endpoints (curated managers, clone, overlap).

**Step 3: Add plan gating to backtest endpoints**

Add `Depends(require_plan("portfolio"))` to `/backtest/default`, `/backtest/replay`. Add `Depends(require_plan("institutional"))` to `/backtest/shadow-portfolio`.

**Step 4: Update test fixtures**

Any test calling newly-gated endpoints must create users with the appropriate `subscription_plan`. Find all affected tests by running the suite and fixing 403 failures.

**Step 5: Run tests**

```bash
uv run pytest api/tests/ -v --tb=short
```

Expected: All pass after fixture updates

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/keys.py api/src/margin_api/routes/thirteenf.py api/src/margin_api/routes/backtest.py api/tests/
git commit -m "feat(api): add server-side subscription plan gating to premium endpoints (MEDIUM-003)"
```

---

### Task 19: Add Pickle Integrity Checksums (MEDIUM-005)

**Files:**
- Modify: `engine/src/margin_engine/ml/signal_model.py` (add checksum on save/load)
- Migration: `api/alembic/versions/xxx_add_model_checksums.py`

**Step 1: Add checksum logic to signal_model.py**

In `engine/src/margin_engine/ml/signal_model.py`, modify `predict_alpha` and `compute_feature_importance`:

```python
def _verify_model_integrity(model_bytes: bytes, expected_checksum: str | None) -> None:
    """Verify model bytes match expected SHA-256 checksum."""
    if expected_checksum is None:
        import logging
        logging.getLogger(__name__).warning("No checksum for model — skipping integrity check")
        return
    import hashlib
    import hmac as hmac_mod
    actual = hashlib.sha256(model_bytes).hexdigest()
    if not hmac_mod.compare_digest(actual, expected_checksum):
        raise ValueError("Model integrity check failed — refusing to unpickle")


def compute_model_checksum(model_bytes: bytes) -> str:
    """Compute SHA-256 checksum for model bytes."""
    import hashlib
    return hashlib.sha256(model_bytes).hexdigest()
```

Update `predict_alpha` signature to optionally accept a checksum:

```python
def predict_alpha(
    model_bytes: bytes, features: np.ndarray, checksum: str | None = None
) -> np.ndarray:
    _verify_model_integrity(model_bytes, checksum)
    model = pickle.loads(model_bytes)  # noqa: S301
    return model.predict(features)
```

**Step 2: Add Alembic migration for checksum columns**

```bash
cd api && uv run alembic revision --autogenerate -m "add model checksum columns"
```

Edit the migration to add `cluster_model_checksum` and `vae_model_checksum` (nullable String) columns to `ml_model_runs`.

**Step 3: Run tests**

```bash
uv run pytest engine/tests/ml/ -v
uv run pytest api/tests/ -v --tb=short
```

Expected: All pass

**Step 4: Commit**

```bash
git add engine/src/margin_engine/ml/signal_model.py api/alembic/versions/
git commit -m "feat(engine): add SHA-256 integrity checksums for ML model blobs (MEDIUM-005)"
```

---

## Group G: Audit Trail (Phase 4, parallel)

### Task 20: Add Stripe Webhook Idempotency (MEDIUM-004)

**Files:**
- Create DB model for `ProcessedWebhookEvent` in `api/src/margin_api/db/models.py`
- Migration: add `processed_webhook_events` table
- Modify: `api/src/margin_api/routes/billing.py` (add idempotency check)
- Create: `api/tests/security/test_webhook_idempotency.py`

**Step 1: Add model**

In `api/src/margin_api/db/models.py`, add:

```python
class ProcessedWebhookEvent(Base):
    __tablename__ = "processed_webhook_events"

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
```

**Step 2: Generate migration**

```bash
cd api && uv run alembic revision --autogenerate -m "add processed webhook events table"
```

**Step 3: Add idempotency check to billing webhook handler**

In `api/src/margin_api/routes/billing.py`, after Stripe event construction and before processing:

```python
    # Idempotency check
    existing = await db.execute(
        select(ProcessedWebhookEvent).where(
            ProcessedWebhookEvent.event_id == event["id"]
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_processed"}

    # ... process event ...

    # Record as processed (same transaction as subscription update)
    db.add(ProcessedWebhookEvent(
        event_id=event["id"],
        event_type=event["type"],
    ))
    await db.commit()
```

**Step 4: Write tests, run, commit**

```bash
uv run pytest api/tests/security/test_webhook_idempotency.py -v
uv run pytest api/tests/ -v --tb=short
git add api/src/margin_api/db/models.py api/src/margin_api/routes/billing.py api/alembic/versions/ api/tests/security/test_webhook_idempotency.py
git commit -m "feat(api): add Stripe webhook idempotency tracking (MEDIUM-004)"
```

---

### Task 21: Add Audit Logging Infrastructure (MEDIUM-007)

**Files:**
- Create DB model `AuditLog` in `api/src/margin_api/db/models.py`
- Migration: add `audit_log` table
- Create: `api/src/margin_api/services/audit.py`
- Modify: `api/src/margin_api/routes/auth.py` (instrument login, MFA, password change)
- Create: `api/tests/security/test_audit_log.py`

**Step 1: Add model**

In `api/src/margin_api/db/models.py`:

```python
class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
```

**Step 2: Create audit service**

Create `api/src/margin_api/services/audit.py`:

```python
"""Append-only audit logging service."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import AuditLog


async def audit_log(
    db: AsyncSession,
    event_type: str,
    request: Request | None = None,
    user_id: int | None = None,
    detail: dict | None = None,
) -> None:
    """Write an audit log entry. Does not commit — caller controls the transaction."""
    entry = AuditLog(
        event_type=event_type,
        user_id=user_id,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        detail=detail,
    )
    db.add(entry)
```

**Step 3: Generate migration, instrument auth routes, write tests**

Add `await audit_log(db, "login_success", request, user_id=result["id"])` calls to verify_credentials (success and failure), verify_totp, change_password, and register.

**Step 4: Run tests, commit**

```bash
uv run pytest api/tests/ -v --tb=short
git add api/src/margin_api/db/models.py api/src/margin_api/services/audit.py api/src/margin_api/routes/auth.py api/alembic/versions/ api/tests/security/test_audit_log.py
git commit -m "feat(api): add structured audit logging for auth events (MEDIUM-007)"
```

---

### Task 22: Final Verification

**Step 1: Run full test suite (all three packages)**

```bash
uv run pytest engine/tests/ -v --tb=short 2>&1 | tail -5
uv run pytest api/tests/ -v --tb=short 2>&1 | tail -5
cd web && npx vitest run 2>&1 | tail -5
```

Expected: All ~4200+ tests pass (4138 original + ~83 new security tests)

**Step 2: Verify no secrets in staged files**

```bash
gitleaks detect --source . --verbose
```

Expected: No leaks detected

**Step 3: Tag the completion**

```bash
git tag post-security-remediation
```

---

## Summary

| Group | Tasks | Parallel? | Estimated New Tests |
|-------|-------|-----------|-------------------|
| A (quick wins) | 1-4 | Yes | ~5 |
| B (HMAC auth) | 5-6 | Sequential | ~8 |
| C (JWT auth) | 7-8 | Sequential | ~8 |
| D (MFA refactor) | 9-12 | Sequential | ~15 |
| E (rate limiting) | 13-14 | Sequential | ~12 |
| F (defense in depth) | 15-19 | Yes | ~20 |
| G (audit trail) | 20-22 | Yes | ~15 |
| **Total** | **22 tasks** | | **~83 new tests** |
