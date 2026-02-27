"""User-facing proposal endpoints."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import UserProposal
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.middleware.rate_limit import limiter
from margin_api.schemas.proposals import ProposalListResponse, ProposalResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/proposals", tags=["proposals"])


@router.get("")
@limiter.limit("30/minute")
async def list_proposals(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
) -> ProposalListResponse:
    """List the authenticated user's proposals, optionally filtered by status."""
    query = (
        select(UserProposal)
        .where(UserProposal.user_id == user_id)
        .order_by(UserProposal.created_at.desc())
    )

    if status is not None:
        query = query.where(UserProposal.status == status)

    result = await db.execute(query)
    proposals = result.scalars().all()

    return ProposalListResponse(
        proposals=[
            ProposalResponse(
                id=p.id,
                proposal_type=p.proposal_type,
                status=p.status,
                payload=p.payload,
                created_at=p.created_at,
                decided_at=p.decided_at,
            )
            for p in proposals
        ]
    )


@router.post("/{proposal_id}/accept")
@limiter.limit("30/minute")
async def accept_proposal(
    proposal_id: int,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Accept a pending proposal belonging to the authenticated user."""
    result = await db.execute(
        select(UserProposal).where(UserProposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()

    if proposal is None or proposal.user_id != user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.status != "pending":
        raise HTTPException(status_code=409, detail="Proposal is not pending")

    proposal.status = "accepted"
    proposal.decided_at = datetime.now(UTC)
    await db.commit()

    return {"status": "accepted", "proposal_id": proposal.id}


@router.post("/{proposal_id}/dismiss")
@limiter.limit("30/minute")
async def dismiss_proposal(
    proposal_id: int,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Dismiss a pending proposal belonging to the authenticated user."""
    result = await db.execute(
        select(UserProposal).where(UserProposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()

    if proposal is None or proposal.user_id != user_id:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.status != "pending":
        raise HTTPException(status_code=409, detail="Proposal is not pending")

    proposal.status = "dismissed"
    proposal.decided_at = datetime.now(UTC)
    await db.commit()

    return {"status": "dismissed", "proposal_id": proposal.id}
