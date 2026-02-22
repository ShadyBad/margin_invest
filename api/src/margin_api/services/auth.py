"""Authentication service — registration, credential verification, and challenge tokens."""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import MfaChallengeToken, User
from margin_api.middleware.mfa_enforcement import _ensure_utc

# Argon2id hasher with OWASP-recommended parameters
_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

# Password policy constants
_MIN_LENGTH = 12
_PASSWORD_RULES: list[tuple[str, str]] = [
    (r"[A-Z]", "Password must contain at least one uppercase letter"),
    (r"[a-z]", "Password must contain at least one lowercase letter"),
    (r"[0-9]", "Password must contain at least one digit"),
    (r"[^A-Za-z0-9]", "Password must contain at least one special character"),
]

# Lockout policy
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_MINUTES = 15


def _validate_password(password: str) -> None:
    """Raise ValueError if password does not meet complexity requirements."""
    if len(password) < _MIN_LENGTH:
        raise ValueError(f"Password must be at least {_MIN_LENGTH} characters")
    for pattern, message in _PASSWORD_RULES:
        if not re.search(pattern, password):
            raise ValueError(message)


class AuthService:
    """Handles user registration, credential verification, and MFA challenge tokens."""

    async def register_user(
        self,
        session: AsyncSession,
        username: str,
        email: str,
        password: str,
    ) -> User:
        """Register a new credential user after validating password strength and uniqueness."""
        _validate_password(password)

        # Check email uniqueness
        existing = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            raise ValueError(f"A user with this email already exists: {email}")

        password_hash = _hasher.hash(password)
        user = User(
            email=email,
            name=username,
            password_hash=password_hash,
            mfa_grace_deadline=datetime.now(UTC) + timedelta(hours=72),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def verify_credentials(
        self,
        session: AsyncSession,
        username: str,
        password: str,
    ) -> dict | None:
        """Verify username/password. Returns user info dict or None on failure.

        Tracks failed attempts and locks the account after 5 consecutive failures
        for 15 minutes.
        """
        stmt = select(User).where(
            User.email == username,
            User.password_hash.isnot(None),
        )
        user = (await session.execute(stmt)).scalar_one_or_none()
        if user is None:
            return None

        # Check lockout
        if user.locked_until is not None:
            if datetime.now(UTC) < _ensure_utc(user.locked_until):
                return None
            # Lockout expired — reset
            user.locked_until = None
            user.failed_login_attempts = 0

        try:
            _hasher.verify(user.password_hash, password)
        except VerifyMismatchError:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= _MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.now(UTC) + timedelta(minutes=_LOCKOUT_MINUTES)
            await session.commit()
            return None

        # Rehash if needed (argon2-cffi handles parameter upgrades)
        if _hasher.check_needs_rehash(user.password_hash):
            user.password_hash = _hasher.hash(password)

        # Reset failed attempts on success
        user.failed_login_attempts = 0
        user.locked_until = None
        await session.commit()

        return {
            "id": user.id,
            "username": user.email,
            "email": user.email,
            "mfa_enabled": user.mfa_enabled,
            "avatar_url": user.avatar_url,
        }

    async def create_challenge_token(
        self,
        session: AsyncSession,
        user_id: int,
        ttl_minutes: int = 5,
    ) -> str:
        """Create a short-lived challenge token for the MFA step. Returns raw token hex."""
        raw_token = secrets.token_hex(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        challenge = MfaChallengeToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
        )
        session.add(challenge)
        await session.commit()
        return raw_token

    async def change_password(
        self,
        session: AsyncSession,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change a credential user's password.

        Validates current password, enforces strength rules, updates hash,
        sets password_changed_at, and resets failed attempts.
        """
        stmt = select(User).where(User.id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if user is None:
            raise LookupError("User not found")

        try:
            _hasher.verify(user.password_hash, current_password)
        except VerifyMismatchError:
            raise PermissionError("Invalid current password")

        _validate_password(new_password)

        user.password_hash = _hasher.hash(new_password)
        user.password_changed_at = datetime.now(UTC)
        user.failed_login_attempts = 0
        await session.commit()

    async def verify_challenge_token(
        self,
        session: AsyncSession,
        user_id: int,
        raw_token: str,
    ) -> bool:
        """Verify and consume a challenge token (single-use). Returns True if valid."""
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        stmt = select(MfaChallengeToken).where(
            MfaChallengeToken.user_id == user_id,
            MfaChallengeToken.token_hash == token_hash,
            MfaChallengeToken.used.is_(False),
        )
        token_row = (await session.execute(stmt)).scalar_one_or_none()
        if token_row is None:
            return False
        if datetime.now(UTC) >= _ensure_utc(token_row.expires_at):
            return False
        token_row.used = True
        await session.commit()
        return True

    async def reset_password(
        self,
        session: AsyncSession,
        user_id: int,
        raw_token: str,
        new_password: str,
    ) -> None:
        """Reset a user's password using a valid challenge token."""
        valid = await self.verify_challenge_token(session, user_id, raw_token)
        if not valid:
            raise LookupError("Invalid or expired reset token")

        _validate_password(new_password)

        stmt = select(User).where(User.id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if user is None:
            raise LookupError("User not found")

        user.password_hash = _hasher.hash(new_password)
        user.password_changed_at = datetime.now(UTC)
        user.failed_login_attempts = 0
        user.locked_until = None
        await session.commit()
