"""API key management service with Fernet encryption."""

from __future__ import annotations

from datetime import UTC, datetime

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import ApiKey, ApiKeyEvent


class ApiKeyService:
    """Manages encrypted API key lifecycle: save, retrieve, revoke."""

    def __init__(self, encryption_key: bytes) -> None:
        self._fernet = Fernet(encryption_key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()

    async def save_key(
        self,
        session: AsyncSession,
        user_id: int,
        provider_name: str,
        plaintext_key: str,
        is_platform_managed: bool,
        ip_address: str | None = None,
    ) -> ApiKey:
        """Encrypt and save a key. Revokes any existing active key for the same provider."""
        # Revoke existing active key for this provider
        existing = await self.get_active_key(session, user_id, provider_name)
        if existing is not None:
            existing.revoked_at = datetime.now(UTC)
            session.add(
                ApiKeyEvent(
                    api_key_id=existing.id,
                    event_type="revoked",
                    ip_address=ip_address,
                )
            )

        encrypted = self.encrypt(plaintext_key)
        key = ApiKey(
            user_id=user_id,
            provider_name=provider_name,
            encrypted_key=encrypted,
            is_platform_managed=is_platform_managed,
        )
        session.add(key)
        await session.commit()
        await session.refresh(key)

        session.add(
            ApiKeyEvent(
                api_key_id=key.id,
                event_type="created",
                ip_address=ip_address,
            )
        )
        await session.commit()
        return key

    async def get_active_key(
        self,
        session: AsyncSession,
        user_id: int,
        provider_name: str,
    ) -> ApiKey | None:
        """Get the currently active (non-revoked, non-expired) key for a provider."""
        now = datetime.now(UTC)
        stmt = (
            select(ApiKey)
            .where(
                ApiKey.user_id == user_id,
                ApiKey.provider_name == provider_name,
                ApiKey.revoked_at.is_(None),
            )
            .where((ApiKey.expires_at.is_(None)) | (ApiKey.expires_at > now))
            .order_by(ApiKey.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_keys(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> list[ApiKey]:
        """List all active (non-revoked, non-expired) keys for a user."""
        now = datetime.now(UTC)
        stmt = (
            select(ApiKey)
            .where(
                ApiKey.user_id == user_id,
                ApiKey.revoked_at.is_(None),
            )
            .where((ApiKey.expires_at.is_(None)) | (ApiKey.expires_at > now))
            .order_by(ApiKey.provider_name)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def revoke_key(
        self,
        session: AsyncSession,
        user_id: int,
        provider_name: str,
        ip_address: str | None = None,
    ) -> bool:
        """Revoke the active key for a provider. Returns True if a key was revoked."""
        key = await self.get_active_key(session, user_id, provider_name)
        if key is None:
            return False
        key.revoked_at = datetime.now(UTC)
        session.add(
            ApiKeyEvent(
                api_key_id=key.id,
                event_type="revoked",
                ip_address=ip_address,
            )
        )
        await session.commit()
        return True
