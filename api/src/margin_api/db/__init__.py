"""Database layer — ORM models and session management."""

from margin_api.db.base import Base
from margin_api.db.models import (
    ApiKey,
    Asset,
    CredentialUser,
    LinkedProvider,
    MfaChallengeToken,
    RecoveryCode,
    Recommendation,
    Score,
    TotpSecret,
    User,
    WebAuthnCredential,
)
from margin_api.db.session import get_db, get_engine, get_session_factory

__all__ = [
    "ApiKey",
    "Asset",
    "Base",
    "CredentialUser",  # Backwards-compat alias; remove after migration
    "LinkedProvider",
    "MfaChallengeToken",
    "RecoveryCode",
    "Recommendation",
    "Score",
    "TotpSecret",
    "User",
    "WebAuthnCredential",
    "get_db",
    "get_engine",
    "get_session_factory",
]
