"""MFA enforcement for sensitive endpoints."""
from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC). SQLite stores naive datetimes."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


async def check_mfa_requirement(user) -> None:
    """Raise 403 if user has password but no MFA and grace period expired."""
    if not user.has_password:
        return
    if user.mfa_enabled:
        return
    if user.mfa_grace_deadline and _ensure_utc(user.mfa_grace_deadline) > datetime.now(UTC):
        return
    raise HTTPException(
        status_code=403,
        detail={
            "error": "mfa_required",
            "message": "Multi-factor authentication must be enabled to perform this action.",
        },
    )


async def require_mfa_dep(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: load user, enforce MFA requirement, return user.

    Use as a dependency on sensitive endpoints (change-password, API keys, billing).
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await check_mfa_requirement(user)
    return user
