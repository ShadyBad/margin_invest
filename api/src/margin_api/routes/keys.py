"""API key management routes — CRUD for provider API keys."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import Settings, get_settings
from margin_api.db.session import get_db
from margin_api.deps import require_plan
from margin_api.middleware.mfa_enforcement import require_mfa_dep
from margin_api.schemas.keys import ApiKeyListResponse, ApiKeyResponse, SaveKeyRequest
from margin_api.services.api_keys import ApiKeyService

router = APIRouter(prefix="/api/v1/keys", tags=["keys"], dependencies=[Depends(require_mfa_dep)])


def _get_api_key_service(settings: Settings = Depends(get_settings)) -> ApiKeyService:
    return ApiKeyService(encryption_key=settings.api_key_encryption_key.encode())


def _mask_key(encrypted_key: str, service: ApiKeyService) -> str:
    """Decrypt a key and return a masked version showing only last 6 chars."""
    plaintext = service.decrypt(encrypted_key)
    if len(plaintext) <= 6:
        return "***"
    return f"{'*' * (len(plaintext) - 6)}{plaintext[-6:]}"


@router.get("/", response_model=ApiKeyListResponse)
async def list_keys(
    _user_id: int = Depends(require_plan("portfolio")),
    db: AsyncSession = Depends(get_db),
    service: ApiKeyService = Depends(_get_api_key_service),
) -> ApiKeyListResponse:
    """List all active API keys for the current user (masked)."""
    keys = await service.list_active_keys(db, _user_id)
    return ApiKeyListResponse(
        keys=[
            ApiKeyResponse(
                id=k.id,
                provider_name=k.provider_name,
                masked_key=_mask_key(k.encrypted_key, service),
                is_platform_managed=k.is_platform_managed,
                created_at=k.created_at,
            )
            for k in keys
        ]
    )


@router.post("/", response_model=ApiKeyResponse, status_code=201)
async def save_key(
    body: SaveKeyRequest,
    _user_id: int = Depends(require_plan("portfolio")),
    db: AsyncSession = Depends(get_db),
    service: ApiKeyService = Depends(_get_api_key_service),
) -> ApiKeyResponse:
    """Save (or replace) an API key for a provider."""
    key = await service.save_key(
        session=db,
        user_id=_user_id,
        provider_name=body.provider_name,
        plaintext_key=body.api_key,
        is_platform_managed=False,
    )
    return ApiKeyResponse(
        id=key.id,
        provider_name=key.provider_name,
        masked_key=_mask_key(key.encrypted_key, service),
        is_platform_managed=key.is_platform_managed,
        created_at=key.created_at,
    )


@router.delete("/{provider_name}")
async def delete_key(
    provider_name: str,
    _user_id: int = Depends(require_plan("portfolio")),
    db: AsyncSession = Depends(get_db),
    service: ApiKeyService = Depends(_get_api_key_service),
) -> dict:
    """Revoke the active key for a provider."""
    revoked = await service.revoke_key(db, _user_id, provider_name)
    if not revoked:
        raise HTTPException(status_code=404, detail="No active key found for this provider")
    return {"revoked": True}
