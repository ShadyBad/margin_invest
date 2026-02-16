"""FastAPI dependency helpers for auth and plan enforcement."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import User
from margin_api.db.session import get_db


def get_current_user_id(
    x_user_id: str | None = Header(None),
) -> int:
    """Extract the current user's ID from the X-User-Id header.

    The Next.js frontend injects this header via serverFetch after
    authenticating with NextAuth.
    """
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return int(x_user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID")


def require_plan(plan: str) -> Callable:
    """Return a FastAPI dependency that verifies the user's subscription plan."""

    async def _check(
        user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
    ) -> int:
        stmt = select(User.subscription_plan).where(User.id == user_id)
        result = await db.execute(stmt)
        current_plan = result.scalar_one_or_none()
        if current_plan != plan:
            raise HTTPException(
                status_code=403,
                detail=f"Upgrade to {plan} plan required",
            )
        return user_id

    return _check
