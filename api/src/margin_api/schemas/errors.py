"""Structured error response schema."""

from __future__ import annotations

from pydantic import BaseModel, model_validator


class ErrorResponse(BaseModel):
    """Structured error returned for all API error responses.

    Includes a ``detail`` field that mirrors ``message`` so that clients
    expecting the standard FastAPI ``{detail: ...}`` format continue to work.
    """

    error_code: str
    message: str
    detail: str = ""
    request_id: str
    status_code: int

    @model_validator(mode="after")
    def _sync_detail(self) -> "ErrorResponse":
        """Keep ``detail`` in sync with ``message`` when not set explicitly."""
        if not self.detail:
            self.detail = self.message
        return self
