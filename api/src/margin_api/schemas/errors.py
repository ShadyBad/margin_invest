"""Structured error response schema."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Structured error returned for all API error responses."""

    error_code: str
    message: str
    request_id: str
    status_code: int
