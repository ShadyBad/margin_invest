"""Auth API routes — registration, credential verification, and MFA."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import Settings, get_settings
from margin_api.db.models import LinkedProvider, RecoveryCode, TotpSecret, User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.middleware.mfa_enforcement import _ensure_utc, require_mfa_dep
from margin_api.middleware.rate_limit import limiter
from margin_api.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    ConfirmTotpRequest,
    ConfirmTotpResponse,
    DisableMfaRequest,
    DisableMfaResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LinkProviderRequest,
    LinkProviderResponse,
    MfaCompleteRequest,
    MfaCompleteResponse,
    MfaVerifyResponse,
    OAuthSyncRequest,
    OAuthSyncResponse,
    ProviderInfo,
    RegenerateRecoveryCodesRequest,
    RegenerateRecoveryCodesResponse,
    RegisterRequest,
    RegisterResponse,
    RemovePasswordRequest,
    RemovePasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SecurityStatusResponse,
    SetPasswordRequest,
    SetPasswordResponse,
    SetupTotpRequest,
    SetupTotpResponse,
    UnlinkProviderResponse,
    VerifyCredentialsRequest,
    VerifyCredentialsResponse,
    VerifyMfaTokenRequest,
    VerifyMfaTokenResponse,
    VerifyRecoveryCodeRequest,
    VerifyTotpRequest,
    WebAuthnOptionsRequest,
    WebAuthnOptionsResponse,
)
from margin_api.services.analytics import track_event
from margin_api.services.audit import audit_log
from margin_api.services.auth import AuthService, _hasher
from margin_api.services.email import EmailService
from margin_api.services.recovery_codes import RecoveryCodeService
from margin_api.services.totp import TotpService
from margin_api.services.webauthn import WebAuthnService

logger = logging.getLogger(__name__)

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


def _get_recovery_code_service() -> RecoveryCodeService:
    return RecoveryCodeService()


def _get_email_service() -> EmailService:
    settings = get_settings()
    return EmailService(api_key=settings.resend_api_key)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
) -> RegisterResponse:
    """Register a new user with username/password credentials."""
    try:
        user = await auth.register_user(db, body.username, body.email, body.password)
    except ValueError as exc:
        track_event(
            body.email,
            "activation_failed",
            {
                "error_type": "validation",
                "error_message": str(exc),
                "username": body.username,
            },
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        logger.warning("Registration IntegrityError for %s: %s", body.username, exc)
        track_event(
            body.email,
            "activation_failed",
            {
                "error_type": "duplicate_account",
                "username": body.username,
            },
        )
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A user with this username or email already exists",
        ) from exc

    await audit_log(db, "register", request, user_id=user.id)
    await db.commit()
    return RegisterResponse(id=user.id, username=user.name, email=user.email)


@router.post("/verify-credentials", response_model=VerifyCredentialsResponse)
@limiter.limit("5/minute")
async def verify_credentials(
    request: Request,
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

    await audit_log(db, "login_success", request, user_id=result["id"])
    await db.commit()

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


@router.post("/mfa/confirm-totp", response_model=ConfirmTotpResponse)
async def confirm_totp(
    body: ConfirmTotpRequest,
    db: AsyncSession = Depends(get_db),
    totp: TotpService = Depends(_get_totp_service),
    recovery: RecoveryCodeService = Depends(_get_recovery_code_service),
) -> ConfirmTotpResponse:
    """Confirm a TOTP secret by verifying the first code. Returns recovery codes."""
    confirmed = await totp.confirm_totp(db, body.secret_id, body.code)
    recovery_codes: list[str] = []
    if confirmed:
        # Look up user_id from the totp secret
        secret_stmt = select(TotpSecret).where(TotpSecret.id == body.secret_id)
        secret_row = (await db.execute(secret_stmt)).scalar_one_or_none()
        if secret_row:
            recovery_codes = await recovery.generate_codes(db, secret_row.user_id)
    return ConfirmTotpResponse(confirmed=confirmed, recovery_codes=recovery_codes)


@router.post("/mfa/verify-totp", response_model=MfaVerifyResponse)
@limiter.limit("5/minute")
async def verify_totp(
    request: Request,
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
@limiter.limit("10/minute")
async def oauth_sync(
    request: Request,
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
    iat: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if a user's session should be invalidated.

    Accepts an optional `iat` query param (token issued-at timestamp).
    Returns whether the token is invalidated -- without leaking raw timestamps.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.password_changed_at:
        return {"session_valid": True, "token_invalidated": False}

    changed_at = int(user.password_changed_at.timestamp())
    token_invalidated = iat > 0 and changed_at > iat
    return {"session_valid": True, "token_invalidated": token_invalidated}


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: User = Depends(require_mfa_dep),
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
) -> ChangePasswordResponse:
    """Change the current user's password. Requires valid current password."""
    try:
        await auth.change_password(db, user.id, body.current_password, body.new_password)
    except LookupError:
        raise HTTPException(status_code=404, detail="User not found")
    except PermissionError:
        raise HTTPException(status_code=401, detail="Invalid current password")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await audit_log(db, "password_change", request, user_id=user.id)
    await db.commit()
    return ChangePasswordResponse(message="Password changed successfully")


# ---------------------------------------------------------------------------
# Password reset endpoints
# ---------------------------------------------------------------------------


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
    email_svc: EmailService = Depends(_get_email_service),
) -> ForgotPasswordResponse:
    """Initiate password reset. Always returns 200 to prevent email enumeration."""
    stmt = select(User).where(
        User.email == body.email,
        User.password_hash.isnot(None),
    )
    user = (await db.execute(stmt)).scalar_one_or_none()

    if user is not None:
        settings = get_settings()
        raw_token = await auth.create_challenge_token(db, user.id, ttl_minutes=60)
        reset_url = f"{settings.app_url}/reset-password?token={raw_token}&userId={user.id}"
        email_svc.send_password_reset(to_email=user.email, reset_url=reset_url)

    return ForgotPasswordResponse(
        message="If an account exists with that email, a reset link has been sent."
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
) -> ResetPasswordResponse:
    """Complete password reset using a valid token."""
    try:
        await auth.reset_password(db, body.user_id, body.token, body.new_password)
    except LookupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ResetPasswordResponse(message="Password has been reset.")


# ---------------------------------------------------------------------------
# Task 10: Recovery code endpoints
# ---------------------------------------------------------------------------


@router.post("/mfa/verify-recovery", response_model=MfaVerifyResponse)
@limiter.limit("5/minute")
async def verify_recovery_code(
    request: Request,
    body: VerifyRecoveryCodeRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
    recovery: RecoveryCodeService = Depends(_get_recovery_code_service),
) -> MfaVerifyResponse:
    """Verify an MFA recovery code during login."""
    valid = await auth.verify_challenge_token(db, body.user_id, body.challenge_token)
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid or expired challenge token")

    verified = await recovery.verify_code(db, body.user_id, body.code)
    if not verified:
        raise HTTPException(status_code=401, detail="Invalid recovery code")

    mfa_token = await auth.create_challenge_token(db, body.user_id)
    return MfaVerifyResponse(verified=True, mfa_token=mfa_token)


@router.post(
    "/mfa/regenerate-recovery-codes",
    response_model=RegenerateRecoveryCodesResponse,
)
async def regenerate_recovery_codes(
    body: RegenerateRecoveryCodesRequest,
    user: User = Depends(require_mfa_dep),
    db: AsyncSession = Depends(get_db),
    recovery: RecoveryCodeService = Depends(_get_recovery_code_service),
) -> RegenerateRecoveryCodesResponse:
    """Regenerate MFA recovery codes. Requires current password verification."""
    if not user.password_hash:
        raise HTTPException(status_code=400, detail="User has no password set")

    try:
        _hasher.verify(user.password_hash, body.current_password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Invalid password")

    codes = await recovery.generate_codes(db, user.id)
    return RegenerateRecoveryCodesResponse(codes=codes)


# ---------------------------------------------------------------------------
# Task 11: MFA disable endpoint
# ---------------------------------------------------------------------------


@router.post("/mfa/disable", response_model=DisableMfaResponse)
async def disable_mfa(
    body: DisableMfaRequest,
    user: User = Depends(require_mfa_dep),
    db: AsyncSession = Depends(get_db),
    totp: TotpService = Depends(_get_totp_service),
) -> DisableMfaResponse:
    """Disable MFA. Requires both current password and a valid TOTP code."""
    if not user.password_hash:
        raise HTTPException(status_code=400, detail="User has no password set")

    # Verify password
    try:
        _hasher.verify(user.password_hash, body.current_password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Invalid password")

    # Verify TOTP code
    verified = await totp.verify_totp(db, user.id, body.totp_code)
    if not verified:
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    # Disable MFA
    user.mfa_enabled = False
    user.mfa_grace_deadline = datetime.now(UTC) + timedelta(hours=72)

    # Delete TOTP secrets
    await db.execute(delete(TotpSecret).where(TotpSecret.user_id == user.id))

    # Delete recovery codes
    await db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))

    await db.commit()
    return DisableMfaResponse(mfa_disabled=True)


# ---------------------------------------------------------------------------
# Task 12: Provider linking and password management
# ---------------------------------------------------------------------------


@router.post("/link-provider", response_model=LinkProviderResponse)
async def link_provider(
    body: LinkProviderRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> LinkProviderResponse:
    """Link an OAuth provider to the current user account."""
    lp = LinkedProvider(
        user_id=user_id,
        provider=body.provider,
        oauth_id=body.oauth_id,
        provider_email=body.provider_email,
    )
    db.add(lp)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This provider account is already linked",
        )
    return LinkProviderResponse(linked=True, provider=body.provider)


@router.delete("/unlink-provider/{provider}", response_model=UnlinkProviderResponse)
async def unlink_provider(
    provider: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UnlinkProviderResponse:
    """Unlink an OAuth provider from the current user account."""
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Find the linked provider row
    lp_stmt = select(LinkedProvider).where(
        LinkedProvider.user_id == user_id,
        LinkedProvider.provider == provider,
    )
    lp = (await db.execute(lp_stmt)).scalar_one_or_none()
    if lp is None:
        raise HTTPException(status_code=404, detail="Provider not linked")

    # Count remaining auth methods
    all_providers_stmt = select(LinkedProvider).where(LinkedProvider.user_id == user_id)
    all_providers = (await db.execute(all_providers_stmt)).scalars().all()

    if not user.has_password and len(all_providers) <= 1:
        raise HTTPException(
            status_code=403,
            detail="Can't disconnect only sign-in method",
        )

    if user.has_password and not user.mfa_enabled:
        # Check grace period
        if not user.mfa_grace_deadline or _ensure_utc(user.mfa_grace_deadline) <= datetime.now(UTC):
            raise HTTPException(
                status_code=403,
                detail="Set up MFA first",
            )

    await db.delete(lp)
    await db.commit()
    return UnlinkProviderResponse(unlinked=True)


@router.post("/set-password", response_model=SetPasswordResponse)
async def set_password(
    body: SetPasswordRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SetPasswordResponse:
    """Set a password for an OAuth-only user account."""
    from margin_api.services.auth import _validate_password

    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.has_password:
        raise HTTPException(
            status_code=409, detail="Password already set. Use change-password instead."
        )

    try:
        _validate_password(body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    user.password_hash = _hasher.hash(body.new_password)
    user.mfa_grace_deadline = datetime.now(UTC) + timedelta(hours=72)
    await db.commit()
    return SetPasswordResponse(password_set=True)


@router.post("/remove-password", response_model=RemovePasswordResponse)
async def remove_password(
    body: RemovePasswordRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> RemovePasswordResponse:
    """Remove password authentication. User must have at least one linked provider."""
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    if not user.password_hash:
        raise HTTPException(status_code=400, detail="User has no password set")

    try:
        _hasher.verify(user.password_hash, body.current_password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Invalid password")

    # Must have at least one linked provider
    lp_stmt = select(LinkedProvider).where(LinkedProvider.user_id == user_id)
    providers = (await db.execute(lp_stmt)).scalars().all()
    if not providers:
        raise HTTPException(
            status_code=403,
            detail="Must have at least one linked provider before removing password",
        )

    # Clear password and MFA
    user.password_hash = None
    user.password_changed_at = None
    user.mfa_enabled = False
    user.mfa_grace_deadline = None

    # Delete TOTP secrets and recovery codes
    await db.execute(delete(TotpSecret).where(TotpSecret.user_id == user_id))
    await db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user_id))

    await db.commit()
    return RemovePasswordResponse(password_removed=True)


# ---------------------------------------------------------------------------
# Task 13: Security status endpoint
# ---------------------------------------------------------------------------


@router.get("/security-status", response_model=SecurityStatusResponse)
async def security_status(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    recovery: RecoveryCodeService = Depends(_get_recovery_code_service),
) -> SecurityStatusResponse:
    """Return the full security status for the current user."""
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Determine MFA method
    mfa_method: str | None = None
    if user.mfa_enabled:
        mfa_method = "totp"

    # Get remaining recovery codes
    remaining = await recovery.remaining_count(db, user_id)

    # Get linked providers
    lp_stmt = select(LinkedProvider).where(LinkedProvider.user_id == user_id)
    providers = (await db.execute(lp_stmt)).scalars().all()
    provider_info = [
        ProviderInfo(
            provider=lp.provider,
            provider_email=lp.provider_email,
            linked_at=lp.linked_at,
        )
        for lp in providers
    ]

    return SecurityStatusResponse(
        has_password=user.has_password,
        mfa_enabled=user.mfa_enabled,
        mfa_method=mfa_method,
        mfa_grace_deadline=user.mfa_grace_deadline,
        recovery_codes_remaining=remaining,
        linked_providers=provider_info,
    )


# ---------------------------------------------------------------------------
# MFA complete endpoints (cookie-based challenge flow)
# ---------------------------------------------------------------------------


@router.post("/mfa/complete", response_model=MfaCompleteResponse)
async def mfa_complete(
    body: MfaCompleteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth: AuthService = Depends(_get_auth_service),
    totp: TotpService = Depends(_get_totp_service),
    recovery: RecoveryCodeService = Depends(_get_recovery_code_service),
) -> MfaCompleteResponse:
    """Complete MFA verification during login using cookie-based challenge."""
    cookie_value = request.cookies.get("__mfa_challenge")
    if not cookie_value:
        raise HTTPException(status_code=401, detail="Missing MFA challenge cookie")

    try:
        challenge_data = json.loads(cookie_value)
        user_id = int(challenge_data["userId"])
        challenge_token = challenge_data["challengeToken"]
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid MFA challenge cookie")

    valid = await auth.verify_challenge_token(db, user_id, challenge_token)
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid or expired challenge token")

    if body.totp_code:
        verified = await totp.verify_totp(db, user_id, body.totp_code)
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid verification code")
    elif body.recovery_code:
        verified = await recovery.verify_code(db, user_id, body.recovery_code)
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid recovery code")
    else:
        raise HTTPException(status_code=400, detail="Provide totp_code or recovery_code")

    settings = get_settings()
    completion_token = pyjwt.encode(
        {
            "sub": str(user_id),
            "purpose": "mfa_complete",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    return MfaCompleteResponse(mfa_completion_token=completion_token)


@router.post("/verify-mfa-token", response_model=VerifyMfaTokenResponse)
async def verify_mfa_token(
    body: VerifyMfaTokenRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> VerifyMfaTokenResponse:
    """Verify an MFA completion token and return user data for session creation."""
    try:
        payload = pyjwt.decode(
            body.token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat", "purpose"]},
        )
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="MFA token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid MFA token")

    if payload.get("purpose") != "mfa_complete":
        raise HTTPException(status_code=401, detail="Invalid token purpose")

    user_id = int(payload["sub"])
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return VerifyMfaTokenResponse(
        id=user.id,
        email=user.email,
        username=user.name or "",
        avatar_url=user.avatar_url,
    )
