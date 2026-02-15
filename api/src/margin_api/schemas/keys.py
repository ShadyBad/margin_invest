"""API key management request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SaveKeyRequest(BaseModel):
    """Request body for saving an API key."""

    provider_name: str = Field(min_length=1, max_length=50)
    api_key: str = Field(min_length=1)


class ApiKeyResponse(BaseModel):
    """Response for a single API key (masked, never plaintext)."""

    id: int
    provider_name: str
    masked_key: str  # e.g., "sk_live_...abc"
    is_platform_managed: bool
    created_at: datetime


class ApiKeyListResponse(BaseModel):
    """Response for listing API keys."""

    keys: list[ApiKeyResponse]
