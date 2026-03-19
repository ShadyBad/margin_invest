"""FastAPI dependency helpers for auth and plan enforcement."""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import logging
import time
from collections.abc import Callable

import jwt as pyjwt
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import Settings, get_settings
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
    settings: Settings = Depends(get_settings),
) -> int:
    """Resolve the current user's database ID.

    Authentication priority:
    1. Authorization: Bearer <JWT> (service token from Next.js)
    2. HMAC-signed X-User-Id + X-Auth-Signature + X-Auth-Timestamp
    3. Unsigned X-User-Id (only when require_signed_auth=False, logs warning)
    """

    # --- Path 1: JWT Bearer token ---
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


def _verify_hmac(user_id_str: str, timestamp_str: str, signature: str, settings: Settings) -> int:
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


async def _verify_jwt_token(token: str, settings: Settings) -> int:
    """Verify a JWT service token signed by the Next.js server."""
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


def _verify_admin_jwt(token_str: str, settings: Settings) -> tuple[int, str]:
    """Verify an admin session JWT signed with the user-facing jwt_secret.

    Returns (user_id, role) on success.
    Raises HTTPException(401) for any invalid/expired/missing-claim token.
    """
    try:
        payload = pyjwt.decode(
            token_str,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat"]},
        )
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Admin token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    sub = payload.get("sub")
    role = payload.get("role")

    if not sub:
        raise HTTPException(status_code=401, detail="Missing sub claim")
    if not role:
        raise HTTPException(status_code=401, detail="Missing role claim")

    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID in token")

    return user_id, role


async def get_admin_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Dependency that requires a valid admin or superadmin session cookie."""
    cookie = request.cookies.get("admin_session")
    if not cookie:
        raise HTTPException(status_code=401, detail="Admin session required")

    user_id, _role = _verify_admin_jwt(cookie, settings)

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    if user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    return user


async def get_superadmin_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Dependency that requires a valid superadmin session cookie."""
    cookie = request.cookies.get("admin_session")
    if not cookie:
        raise HTTPException(status_code=401, detail="Admin session required")

    user_id, _role = _verify_admin_jwt(cookie, settings)

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")

    return user


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
