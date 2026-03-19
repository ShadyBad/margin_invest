"""Auth API request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    username: str = Field(min_length=3, max_length=150)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=12)


class RegisterResponse(BaseModel):
    """Response after successful registration."""

    id: int
    username: str
    email: str


class VerifyCredentialsRequest(BaseModel):
    """Request body for credential verification (login step 1)."""

    username: str
    password: str


class VerifyCredentialsResponse(BaseModel):
    """Response after successful credential verification."""

    id: int
    username: str
    email: str
    mfa_status: str
    challenge_token: str
    avatar_url: str | None = None


class SetupTotpRequest(BaseModel):
    """Request body for initiating TOTP setup."""

    user_id: int
    challenge_token: str


class SetupTotpResponse(BaseModel):
    """Response with TOTP provisioning URI and secret ID."""

    provisioning_uri: str
    secret_id: int


class ConfirmTotpRequest(BaseModel):
    """Request body for confirming a TOTP secret."""

    secret_id: int
    code: str = Field(min_length=6, max_length=6)


class VerifyTotpRequest(BaseModel):
    """Request body for verifying a TOTP code during login."""

    user_id: int
    code: str = Field(min_length=6, max_length=6)
    challenge_token: str


class MfaVerifyResponse(BaseModel):
    """Response after MFA verification attempt."""

    verified: bool
    mfa_token: str | None = None


class WebAuthnOptionsRequest(BaseModel):
    """Request body for WebAuthn registration/authentication options."""

    user_id: int
    challenge_token: str


class WebAuthnOptionsResponse(BaseModel):
    """Response containing WebAuthn options."""

    options: dict


class OAuthSyncRequest(BaseModel):
    """Request body for syncing an OAuth user to the database."""

    email: str = Field(max_length=320)
    name: str = Field(max_length=255)
    provider: str = Field(max_length=50)
    oauth_id: str = Field(max_length=255)
    avatar_url: str | None = None


class OAuthSyncResponse(BaseModel):
    """Response after syncing an OAuth user."""

    id: int
    subscription_plan: str


class ChangePasswordRequest(BaseModel):
    """Request body for changing a credential user's password."""

    current_password: str
    new_password: str = Field(min_length=12)


class ChangePasswordResponse(BaseModel):
    """Response after successful password change."""

    message: str


# ---------------------------------------------------------------------------
# MFA confirm TOTP response (with recovery codes)
# ---------------------------------------------------------------------------


class ConfirmTotpResponse(BaseModel):
    """Response after confirming TOTP setup (includes recovery codes)."""

    confirmed: bool
    recovery_codes: list[str] = []


# ---------------------------------------------------------------------------
# Recovery code schemas
# ---------------------------------------------------------------------------


class VerifyRecoveryCodeRequest(BaseModel):
    """Request body for verifying an MFA recovery code."""

    user_id: int
    code: str = Field(min_length=8, max_length=9)
    challenge_token: str


class RegenerateRecoveryCodesRequest(BaseModel):
    """Request body for regenerating recovery codes."""

    current_password: str


class RegenerateRecoveryCodesResponse(BaseModel):
    """Response with newly generated recovery codes."""

    codes: list[str]


# ---------------------------------------------------------------------------
# MFA disable schemas
# ---------------------------------------------------------------------------


class DisableMfaRequest(BaseModel):
    """Request body for disabling MFA."""

    current_password: str
    totp_code: str = Field(min_length=6, max_length=6)


class DisableMfaResponse(BaseModel):
    """Response after disabling MFA."""

    mfa_disabled: bool


# ---------------------------------------------------------------------------
# Provider linking schemas
# ---------------------------------------------------------------------------


class LinkProviderRequest(BaseModel):
    """Request body for linking an OAuth provider."""

    provider: str = Field(max_length=50)
    oauth_id: str = Field(max_length=255)
    provider_email: str | None = None


class LinkProviderResponse(BaseModel):
    """Response after linking a provider."""

    linked: bool
    provider: str


class UnlinkProviderResponse(BaseModel):
    """Response after unlinking a provider."""

    unlinked: bool


# ---------------------------------------------------------------------------
# Password management schemas
# ---------------------------------------------------------------------------


class SetPasswordRequest(BaseModel):
    """Request body for setting a password (for OAuth-only users)."""

    new_password: str = Field(min_length=12)


class SetPasswordResponse(BaseModel):
    """Response after setting a password."""

    password_set: bool


class RemovePasswordRequest(BaseModel):
    """Request body for removing password authentication."""

    current_password: str


class RemovePasswordResponse(BaseModel):
    """Response after removing password."""

    password_removed: bool


# ---------------------------------------------------------------------------
# Security status schemas
# ---------------------------------------------------------------------------


class ProviderInfo(BaseModel):
    """Info about a linked OAuth provider."""

    provider: str
    provider_email: str | None
    linked_at: datetime


class SecurityStatusResponse(BaseModel):
    """Full security status for a user account."""

    has_password: bool
    mfa_enabled: bool
    mfa_method: str | None
    mfa_grace_deadline: datetime | None
    recovery_codes_remaining: int
    linked_providers: list[ProviderInfo]


# ---------------------------------------------------------------------------
# Password reset schemas
# ---------------------------------------------------------------------------


class ForgotPasswordRequest(BaseModel):
    """Request body for initiating password reset."""

    email: str = Field(min_length=5, max_length=320)


class ForgotPasswordResponse(BaseModel):
    """Response after initiating password reset."""

    message: str


class ResetPasswordRequest(BaseModel):
    """Request body for completing password reset."""

    user_id: int
    token: str
    new_password: str = Field(min_length=12)


class ResetPasswordResponse(BaseModel):
    """Response after successful password reset."""

    message: str


# ---------------------------------------------------------------------------
# MFA complete schemas (cookie-based challenge flow)
# ---------------------------------------------------------------------------


class MfaCompleteRequest(BaseModel):
    """Request body for completing MFA during login."""

    totp_code: str | None = Field(None, min_length=6, max_length=6)
    recovery_code: str | None = Field(None, min_length=8, max_length=9)


class MfaCompleteResponse(BaseModel):
    """Response with a signed MFA completion token."""

    mfa_completion_token: str


class VerifyMfaTokenRequest(BaseModel):
    """Request body for verifying an MFA completion token."""

    token: str


class VerifyMfaTokenResponse(BaseModel):
    """Response with user data after MFA token verification."""

    id: int
    email: str
    username: str
    avatar_url: str | None = None


# ---------------------------------------------------------------------------
# Admin login schemas
# ---------------------------------------------------------------------------


class AdminLoginRequest(BaseModel):
    """Request body for admin login (step 1 of admin auth flow)."""

    email: str = Field(min_length=5, max_length=320)
    pw: str


class AdminLoginResponse(BaseModel):
    """Response from admin login — always issues an MFA challenge."""

    mfa_required: bool
    challenge_str: str | None = None
    message: str
