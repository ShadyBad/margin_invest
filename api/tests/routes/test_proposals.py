"""Tests for user proposal endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import UserProposal
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_USER_A = 1
_USER_B = 2


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client_a(session_factory):
    """AsyncClient authenticated as USER_A."""
    app = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: _USER_A

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def client_b(session_factory):
    """AsyncClient authenticated as USER_B."""
    app = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: _USER_B

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_proposal(
    session: AsyncSession,
    user_id: int = _USER_A,
    proposal_type: str = "rebalance",
    status: str = "pending",
    payload: dict | None = None,
) -> UserProposal:
    """Insert a UserProposal into the test database."""
    proposal = UserProposal(
        user_id=user_id,
        proposal_type=proposal_type,
        status=status,
        payload=payload or {"ticker": "AAPL"},
        created_at=datetime.now(UTC),
    )
    session.add(proposal)
    await session.commit()
    await session.refresh(proposal)
    return proposal


# ---------------------------------------------------------------------------
# Tests: List proposals
# ---------------------------------------------------------------------------


class TestListProposals:
    @pytest.mark.asyncio
    async def test_list_returns_user_proposals_only(
        self, db_session, session_factory, client_a
    ):
        """GET /proposals returns only the authenticated user's proposals."""
        await _create_proposal(db_session, user_id=_USER_A, proposal_type="rebalance")
        await _create_proposal(db_session, user_id=_USER_A, proposal_type="allocation")
        await _create_proposal(db_session, user_id=_USER_B, proposal_type="rebalance")

        resp = await client_a.get("/api/v1/proposals")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["proposals"]) == 2
        for p in data["proposals"]:
            assert p["proposal_type"] in ("rebalance", "allocation")

    @pytest.mark.asyncio
    async def test_list_filters_by_status(self, db_session, session_factory, client_a):
        """GET /proposals?status=pending returns only pending proposals."""
        await _create_proposal(db_session, user_id=_USER_A, status="pending")
        await _create_proposal(db_session, user_id=_USER_A, status="accepted")

        resp = await client_a.get("/api/v1/proposals?status=pending")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["proposals"]) == 1
        assert data["proposals"][0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_empty(self, db_session, session_factory, client_a):
        """GET /proposals returns empty list when no proposals exist."""
        resp = await client_a.get("/api/v1/proposals")

        assert resp.status_code == 200
        data = resp.json()
        assert data["proposals"] == []


# ---------------------------------------------------------------------------
# Tests: Accept proposal
# ---------------------------------------------------------------------------


class TestAcceptProposal:
    @pytest.mark.asyncio
    async def test_accept_transitions_pending_to_accepted(
        self, db_session, session_factory, client_a
    ):
        """POST /proposals/{id}/accept transitions pending to accepted."""
        proposal = await _create_proposal(db_session, user_id=_USER_A, status="pending")

        resp = await client_a.post(f"/api/v1/proposals/{proposal.id}/accept")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["proposal_id"] == proposal.id

        # Verify in DB
        async with session_factory() as verify_session:
            result = await verify_session.execute(
                select(UserProposal).where(UserProposal.id == proposal.id)
            )
            updated = result.scalar_one()
            assert updated.status == "accepted"
            assert updated.decided_at is not None

    @pytest.mark.asyncio
    async def test_accept_404_on_missing_proposal(
        self, db_session, session_factory, client_a
    ):
        """POST /proposals/999/accept returns 404 for non-existent proposal."""
        resp = await client_a.post("/api/v1/proposals/999/accept")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_accept_409_on_non_pending(
        self, db_session, session_factory, client_a
    ):
        """POST /proposals/{id}/accept returns 409 if already accepted."""
        proposal = await _create_proposal(
            db_session, user_id=_USER_A, status="accepted"
        )

        resp = await client_a.post(f"/api/v1/proposals/{proposal.id}/accept")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_cannot_accept_another_users_proposal(
        self, db_session, session_factory, client_a
    ):
        """POST /proposals/{id}/accept returns 404 for another user's proposal."""
        proposal = await _create_proposal(
            db_session, user_id=_USER_B, status="pending"
        )

        resp = await client_a.post(f"/api/v1/proposals/{proposal.id}/accept")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Dismiss proposal
# ---------------------------------------------------------------------------


class TestDismissProposal:
    @pytest.mark.asyncio
    async def test_dismiss_transitions_pending_to_dismissed(
        self, db_session, session_factory, client_a
    ):
        """POST /proposals/{id}/dismiss transitions pending to dismissed."""
        proposal = await _create_proposal(db_session, user_id=_USER_A, status="pending")

        resp = await client_a.post(f"/api/v1/proposals/{proposal.id}/dismiss")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "dismissed"
        assert data["proposal_id"] == proposal.id

        # Verify in DB
        async with session_factory() as verify_session:
            result = await verify_session.execute(
                select(UserProposal).where(UserProposal.id == proposal.id)
            )
            updated = result.scalar_one()
            assert updated.status == "dismissed"
            assert updated.decided_at is not None

    @pytest.mark.asyncio
    async def test_dismiss_404_on_missing_proposal(
        self, db_session, session_factory, client_a
    ):
        """POST /proposals/999/dismiss returns 404 for non-existent proposal."""
        resp = await client_a.post("/api/v1/proposals/999/dismiss")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_dismiss_409_on_non_pending(
        self, db_session, session_factory, client_a
    ):
        """POST /proposals/{id}/dismiss returns 409 if already dismissed."""
        proposal = await _create_proposal(
            db_session, user_id=_USER_A, status="dismissed"
        )

        resp = await client_a.post(f"/api/v1/proposals/{proposal.id}/dismiss")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_cannot_dismiss_another_users_proposal(
        self, db_session, session_factory
    ):
        """POST /proposals/{id}/dismiss returns 404 for another user's proposal."""
        # Create a proposal belonging to USER_A
        proposal = await _create_proposal(
            db_session, user_id=_USER_A, status="pending"
        )

        # Create a client authenticated as USER_B
        app = create_app()

        async def override_get_db():
            async with session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = lambda: _USER_B

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/api/v1/proposals/{proposal.id}/dismiss")

        assert resp.status_code == 404
