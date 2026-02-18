"""Auth API request and response schemas."""

from __future__ import annotations

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
