"""Recovery code generation, storage, and verification."""

from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime

import bcrypt
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import RecoveryCode

_ALPHABET = "".join(c for c in string.ascii_lowercase + string.digits if c not in "0o1l")


class RecoveryCodeService:
    """Generates, stores (hashed), and verifies MFA recovery codes."""

    def _generate_raw_code(self) -> str:
        """Generate a single recovery code in xxxx-xxxx format."""
        chars = "".join(secrets.choice(_ALPHABET) for _ in range(8))
        return f"{chars[:4]}-{chars[4:]}"

    def _hash_code(self, code: str) -> str:
        """Hash a recovery code (normalized, without hyphen) using bcrypt."""
        normalized = code.replace("-", "")
        return bcrypt.hashpw(normalized.encode(), bcrypt.gensalt()).decode()

    def _check_code(self, code: str, hashed: str) -> bool:
        """Check a recovery code against a bcrypt hash."""
        normalized = code.replace("-", "")
        return bcrypt.checkpw(normalized.encode(), hashed.encode())

    async def generate_codes(self, session: AsyncSession, user_id: int) -> list[str]:
        """Generate 8 new recovery codes, replacing any existing ones.

        Returns the plaintext codes (shown once to the user).
        """
        await session.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user_id))

        codes: list[str] = []
        for _ in range(8):
            raw = self._generate_raw_code()
            codes.append(raw)
            session.add(RecoveryCode(user_id=user_id, code_hash=self._hash_code(raw)))

        await session.commit()
        return codes

    async def verify_code(self, session: AsyncSession, user_id: int, code: str) -> bool:
        """Verify a recovery code. On match, marks the code as used.

        Accepts codes with or without hyphen.
        """
        result = await session.execute(
            select(RecoveryCode).where(
                RecoveryCode.user_id == user_id,
                RecoveryCode.used == False,  # noqa: E712
            )
        )
        for rc in result.scalars().all():
            if self._check_code(code, rc.code_hash):
                rc.used = True
                rc.used_at = datetime.now(UTC)
                await session.commit()
                return True
        return False

    async def remaining_count(self, session: AsyncSession, user_id: int) -> int:
        """Return the number of unused recovery codes for a user."""
        result = await session.execute(
            select(func.count())
            .select_from(RecoveryCode)
            .where(
                RecoveryCode.user_id == user_id,
                RecoveryCode.used == False,  # noqa: E712
            )
        )
        return result.scalar() or 0
