"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from margin_api import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Return service health status."""
    return {"status": "ok", "version": __version__}
