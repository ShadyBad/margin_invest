"""WebAuthn/passkey service for MFA registration and authentication."""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import CredentialUser, WebAuthnCredential


class WebAuthnService:
    """Manages WebAuthn credential lifecycle: registration, authentication, and storage."""

    def __init__(self, rp_id: str, rp_name: str, rp_origin: str) -> None:
        self._rp_id = rp_id
        self._rp_name = rp_name
        self._rp_origin = rp_origin

    async def _get_existing_credentials(
        self, session: AsyncSession, user_id: int
    ) -> list[WebAuthnCredential]:
        stmt = select(WebAuthnCredential).where(WebAuthnCredential.user_id == user_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def generate_registration_options(
        self,
        session: AsyncSession,
        user_id: int,
        username: str,
        email: str,
    ) -> dict:
        """Generate WebAuthn registration options for a user.

        Returns a dict with rp, user, challenge, excludeCredentials, etc.
        """
        challenge = secrets.token_urlsafe(32)
        existing = await self._get_existing_credentials(session, user_id)
        exclude_credentials = [
            {"id": cred.credential_id, "type": "public-key"}
            for cred in existing
        ]

        return {
            "rp": {
                "name": self._rp_name,
                "id": self._rp_id,
            },
            "user": {
                "id": str(user_id),
                "name": username,
                "displayName": email,
            },
            "challenge": challenge,
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},   # ES256
                {"type": "public-key", "alg": -257},  # RS256
            ],
            "excludeCredentials": exclude_credentials,
            "authenticatorSelection": {
                "authenticatorAttachment": "platform",
                "requireResidentKey": False,
                "userVerification": "preferred",
            },
            "timeout": 60000,
            "attestation": "none",
        }

    async def generate_authentication_options(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> dict:
        """Generate WebAuthn authentication options for a user.

        Returns a dict with challenge, allowCredentials, rpId, etc.
        """
        challenge = secrets.token_urlsafe(32)
        existing = await self._get_existing_credentials(session, user_id)
        allow_credentials = [
            {"id": cred.credential_id, "type": "public-key"}
            for cred in existing
        ]

        return {
            "challenge": challenge,
            "rpId": self._rp_id,
            "allowCredentials": allow_credentials,
            "userVerification": "preferred",
            "timeout": 60000,
        }

    async def store_credential(
        self,
        session: AsyncSession,
        user_id: int,
        credential_id: str,
        public_key: str,
    ) -> WebAuthnCredential:
        """Store a verified WebAuthn credential and enable MFA for the user."""
        cred = WebAuthnCredential(
            user_id=user_id,
            credential_id=credential_id,
            public_key=public_key,
        )
        session.add(cred)

        user_stmt = select(CredentialUser).where(CredentialUser.id == user_id)
        user = (await session.execute(user_stmt)).scalar_one()
        user.mfa_enabled = True

        await session.commit()
        await session.refresh(cred)
        return cred
