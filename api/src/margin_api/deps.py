"""FastAPI dependency helpers for auth and plan enforcement."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import User
from margin_api.db.session import get_db


async def get_current_user_id(
    x_user_id: str | None = Header(None),
    x_user_email: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> int:
    """Resolve the current user's database ID.

    Accepts an integer DB ID (credential auth), or falls back to
    looking up the user by email (OAuth, where NextAuth generates
    unstable UUIDs).
    """
    if x_user_id is None and x_user_email is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fast path: integer DB ID from credential auth
    if x_user_id is not None:
        try:
            return int(x_user_id)
        except (ValueError, TypeError):
            pass

    # Fallback: look up by email
    if x_user_email:
        stmt = select(User.id).where(User.email == x_user_email)
        result = await db.execute(stmt)
        user_id = result.scalar_one_or_none()
        if user_id is not None:
            return user_id

    raise HTTPException(status_code=401, detail="Unknown user")


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
