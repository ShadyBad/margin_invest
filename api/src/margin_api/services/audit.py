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
    """Write an audit log entry. Does not commit -- caller controls the transaction."""
    entry = AuditLog(
        event_type=event_type,
        user_id=user_id,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        detail=detail,
    )
    db.add(entry)
