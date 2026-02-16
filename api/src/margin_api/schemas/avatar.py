"""Schemas for avatar endpoints."""

from pydantic import BaseModel


class AvatarResponse(BaseModel):
    avatar_url: str | None
