"""MFA enforcement for sensitive endpoints."""
from datetime import UTC, datetime

from fastapi import HTTPException


async def check_mfa_requirement(user) -> None:
    """Raise 403 if user has password but no MFA and grace period expired."""
    if not user.has_password:
        return
    if user.mfa_enabled:
        return
    if user.mfa_grace_deadline and user.mfa_grace_deadline > datetime.now(UTC):
        return
    raise HTTPException(
        status_code=403,
        detail={
            "error": "mfa_required",
            "message": "Multi-factor authentication must be enabled to perform this action.",
        },
    )
