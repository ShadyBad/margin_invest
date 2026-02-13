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
