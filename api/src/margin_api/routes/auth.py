"""Auth API routes — registration, credential verification, and MFA."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings

logger = logging.getLogger(__name__)
from margin_api.db.models import LinkedProvider, User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    ConfirmTotpRequest,
    MfaVerifyResponse,
    OAuthSyncRequest,
    OAuthSyncResponse,
    RegisterRequest,
    RegisterResponse,
    SetupTotpRequest,
    SetupTotpResponse,
    VerifyCredentialsRequest,
    VerifyCredentialsResponse,
    VerifyTotpRequest,
    WebAuthnOptionsRequest,
    WebAuthnOptionsResponse,
)
from margin_api.services.auth import AuthService
from margin_api.services.totp import TotpService
from margin_api.services.webauthn import WebAuthnService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Service dependency factories
# ---------------------------------------------------------------------------


def _get_auth_service() -> AuthService:
    return AuthService()


def _get_totp_service() -> TotpService:
    settings = get_settings()
    return TotpService(encryption_key=settings.mfa_encryption_key.encode())


def _get_webauthn_service() -> WebAuthnService:
    settings = get_settings()
    return WebAuthnService(
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.webauthn_rp_name,
        rp_origin=settings.webauthn_rp_origin,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
) -> RegisterResponse:
    """Register a new user with username/password credentials."""
    try:
        user = await auth.register_user(db, body.username, body.email, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        logger.warning("Registration IntegrityError for %s: %s", body.username, exc)
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A user with this username or email already exists",
        ) from exc
    return RegisterResponse(id=user.id, username=user.name, email=user.email)


@router.post("/verify-credentials", response_model=VerifyCredentialsResponse)
async def verify_credentials(
    body: VerifyCredentialsRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
) -> VerifyCredentialsResponse:
    """Verify username/password and return a challenge token for MFA."""
    result = await auth.verify_credentials(db, body.username, body.password)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    challenge_token = await auth.create_challenge_token(db, result["id"])
    mfa_status = "enabled" if result["mfa_enabled"] else "disabled"

    return VerifyCredentialsResponse(
        id=result["id"],
        username=result["username"],
        email=result["email"],
        mfa_status=mfa_status,
        challenge_token=challenge_token,
        avatar_url=result.get("avatar_url"),
    )


@router.post("/mfa/setup-totp", response_model=SetupTotpResponse)
async def setup_totp(
    body: SetupTotpRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
    totp: TotpService = Depends(_get_totp_service),
) -> SetupTotpResponse:
    """Initiate TOTP setup — returns a provisioning URI for authenticator apps."""
    valid = await auth.verify_challenge_token(db, body.user_id, body.challenge_token)
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid or expired challenge token")

    # Look up user to get their email
    stmt = select(User).where(User.id == body.user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    result = await totp.setup_totp(db, user.id, user.email)
    return SetupTotpResponse(
        provisioning_uri=result["provisioning_uri"],
        secret_id=result["secret_id"],
    )


@router.post("/mfa/confirm-totp", response_model=MfaVerifyResponse)
async def confirm_totp(
    body: ConfirmTotpRequest,
    db: AsyncSession = Depends(get_db),
    totp: TotpService = Depends(_get_totp_service),
) -> MfaVerifyResponse:
    """Confirm a TOTP secret by verifying the first code."""
    confirmed = await totp.confirm_totp(db, body.secret_id, body.code)
    return MfaVerifyResponse(verified=confirmed)


@router.post("/mfa/verify-totp", response_model=MfaVerifyResponse)
async def verify_totp(
    body: VerifyTotpRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
    totp: TotpService = Depends(_get_totp_service),
) -> MfaVerifyResponse:
    """Verify a TOTP code during login (after credential verification)."""
    valid = await auth.verify_challenge_token(db, body.user_id, body.challenge_token)
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid or expired challenge token")

    verified = await totp.verify_totp(db, body.user_id, body.code)
    mfa_token = None
    if verified:
        # Issue a new challenge token that serves as the MFA proof
        mfa_token = await auth.create_challenge_token(db, body.user_id)

    return MfaVerifyResponse(verified=verified, mfa_token=mfa_token)


@router.post("/mfa/register-webauthn", response_model=WebAuthnOptionsResponse)
async def register_webauthn(
    body: WebAuthnOptionsRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
    webauthn: WebAuthnService = Depends(_get_webauthn_service),
) -> WebAuthnOptionsResponse:
    """Generate WebAuthn registration options."""
    valid = await auth.verify_challenge_token(db, body.user_id, body.challenge_token)
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid or expired challenge token")

    stmt = select(User).where(User.id == body.user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    options = await webauthn.generate_registration_options(
        db, user.id, user.name or user.email, user.email
    )
    return WebAuthnOptionsResponse(options=options)


@router.post("/mfa/authenticate-webauthn", response_model=WebAuthnOptionsResponse)
async def authenticate_webauthn(
    body: WebAuthnOptionsRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
    webauthn: WebAuthnService = Depends(_get_webauthn_service),
) -> WebAuthnOptionsResponse:
    """Generate WebAuthn authentication options."""
    valid = await auth.verify_challenge_token(db, body.user_id, body.challenge_token)
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid or expired challenge token")

    options = await webauthn.generate_authentication_options(db, body.user_id)
    return WebAuthnOptionsResponse(options=options)


@router.post("/oauth-sync", response_model=OAuthSyncResponse)
async def oauth_sync(
    body: OAuthSyncRequest,
    db: AsyncSession = Depends(get_db),
) -> OAuthSyncResponse:
    """Upsert an OAuth user and return the database integer ID.

    Called by the NextAuth jwt callback on sign-in so the frontend
    can store the real DB id instead of the provider's opaque id.
    """
    stmt = select(User).where(User.email == body.email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if user is None:
        user = User(
            email=body.email,
            name=body.name,
            oauth_avatar_url=body.avatar_url,
        )
        db.add(user)
        await db.flush()
    else:
        user.name = body.name
        user.oauth_avatar_url = body.avatar_url

    # Upsert LinkedProvider for this OAuth provider
    lp_stmt = select(LinkedProvider).where(
        LinkedProvider.user_id == user.id,
        LinkedProvider.provider == body.provider,
    )
    lp = (await db.execute(lp_stmt)).scalar_one_or_none()
    if lp is None:
        lp = LinkedProvider(
            user_id=user.id,
            provider=body.provider,
            oauth_id=body.oauth_id,
            provider_email=body.email,
        )
        db.add(lp)

    await db.commit()
    await db.refresh(user)

    return OAuthSyncResponse(id=user.id, subscription_plan=user.subscription_plan)


@router.get("/session-check/{user_id}")
async def check_session(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Internal endpoint called by NextAuth JWT callback to check if password was changed."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.password_changed_at:
        return {"password_changed_at": None}
    return {"password_changed_at": user.password_changed_at.isoformat()}


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    body: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
) -> ChangePasswordResponse:
    """Change the current user's password. Requires valid current password."""
    try:
        await auth.change_password(db, user_id, body.current_password, body.new_password)
    except LookupError:
        raise HTTPException(status_code=404, detail="User not found")
    except PermissionError:
        raise HTTPException(status_code=401, detail="Invalid current password")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChangePasswordResponse(message="Password changed successfully")
