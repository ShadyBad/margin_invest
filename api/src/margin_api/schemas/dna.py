"""Pydantic schemas for the DNA visual parameters endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DNAResponse(BaseModel):
    """Visual DNA parameters derived from user portfolio composition."""

    base: str = Field(description="Deepest background hex color")
    mid: str = Field(description="Mid-layer gradient hex color")
    accent: str = Field(description="Highlight/caustic tint hex color")
    density: float = Field(ge=0, le=1, description="Visual density 0-1")
    tempo: float = Field(ge=0.5, le=1.5, description="Animation speed multiplier")
