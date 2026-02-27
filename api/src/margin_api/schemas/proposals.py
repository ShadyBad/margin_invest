"""Pydantic schemas for user proposals."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProposalResponse(BaseModel):
    id: int
    proposal_type: str
    status: str
    payload: dict | None = None
    created_at: datetime | None = None
    decided_at: datetime | None = None


class ProposalListResponse(BaseModel):
    proposals: list[ProposalResponse]
