"""TOTP (Time-based One-Time Password) service for MFA."""

from __future__ import annotations

import pyotp
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import TotpSecret, User

_ISSUER_NAME = "Margin Invest"


class TotpService:
    """Manages TOTP secret lifecycle: setup, confirmation, and verification."""

    def __init__(self, encryption_key: bytes) -> None:
        self._fernet = Fernet(encryption_key)

    def _encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def _decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()

    async def setup_totp(
        self,
        session: AsyncSession,
        user_id: int,
        user_email: str,
    ) -> dict:
        """Generate a new TOTP secret, encrypt and store it, return provisioning URI.

        Returns dict with ``provisioning_uri`` and ``secret_id``.
        """
        raw_secret = pyotp.random_base32()
        encrypted = self._encrypt(raw_secret)

        totp_row = TotpSecret(
            user_id=user_id,
            encrypted_secret=encrypted,
        )
        session.add(totp_row)
        await session.commit()
        await session.refresh(totp_row)

        totp = pyotp.TOTP(raw_secret)
        provisioning_uri = totp.provisioning_uri(name=user_email, issuer_name=_ISSUER_NAME)

        return {
            "provisioning_uri": provisioning_uri,
            "secret_id": totp_row.id,
        }

    async def confirm_totp(
        self,
        session: AsyncSession,
        secret_id: int,
        code: str,
    ) -> bool:
        """Verify the code against the unconfirmed secret. Confirm on success.

        Sets ``TotpSecret.confirmed = True`` and ``User.mfa_enabled = True``.
        """
        stmt = select(TotpSecret).where(TotpSecret.id == secret_id)
        secret_row = (await session.execute(stmt)).scalar_one_or_none()
        if secret_row is None:
            return False

        raw_secret = self._decrypt(secret_row.encrypted_secret)
        totp = pyotp.TOTP(raw_secret)
        if not totp.verify(code, valid_window=1):
            return False

        secret_row.confirmed = True

        user_stmt = select(User).where(User.id == secret_row.user_id)
        user = (await session.execute(user_stmt)).scalar_one()
        user.mfa_enabled = True
        await session.commit()
        return True

    async def verify_totp(
        self,
        session: AsyncSession,
        user_id: int,
        code: str,
    ) -> bool:
        """Verify code against the user's confirmed TOTP secret."""
        stmt = select(TotpSecret).where(
            TotpSecret.user_id == user_id,
            TotpSecret.confirmed.is_(True),
        )
        secret_row = (await session.execute(stmt)).scalar_one_or_none()
        if secret_row is None:
            return False

        raw_secret = self._decrypt(secret_row.encrypted_secret)
        totp = pyotp.TOTP(raw_secret)
        return totp.verify(code, valid_window=1)
