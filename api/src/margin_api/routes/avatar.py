"""Avatar upload and delete routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.schemas.avatar import AvatarResponse
from margin_api.services.image_processing import (
    InvalidImageError,
    process_avatar,
    validate_image,
)
from margin_api.services.storage import AvatarStorageService

router = APIRouter(prefix="/api/v1/users/me", tags=["avatar"])


def _get_storage() -> AvatarStorageService:
    return AvatarStorageService()


@router.post("/avatar", response_model=AvatarResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    storage: AvatarStorageService = Depends(_get_storage),
) -> AvatarResponse:
    """Upload or replace a user's avatar image."""
    data = await file.read()
    try:
        validate_image(data, file.content_type or "")
    except InvalidImageError as e:
        raise HTTPException(status_code=400, detail=str(e))

    processed = process_avatar(data)
    url = storage.upload(user_id, processed)

    await db.execute(update(User).where(User.id == user_id).values(avatar_url=url))
    await db.commit()
    return AvatarResponse(avatar_url=url)


@router.delete("/avatar", response_model=AvatarResponse)
async def delete_avatar(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    storage: AvatarStorageService = Depends(_get_storage),
) -> AvatarResponse:
    """Remove a user's custom avatar."""
    storage.delete(user_id)
    await db.execute(update(User).where(User.id == user_id).values(avatar_url=None))
    await db.commit()
    return AvatarResponse(avatar_url=None)
