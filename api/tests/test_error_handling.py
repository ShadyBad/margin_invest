"""Tests for global error handling and request ID middleware."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
def app():
    """Create an app with an in-memory SQLite DB to avoid asyncpg loop issues."""
    application = create_app()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_db
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


class TestRequestIdMiddleware:
    def test_response_has_request_id_header(self, client):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers
        # UUID4 format: 8-4-4-4-12 hex chars
        rid = resp.headers["x-request-id"]
        assert len(rid) == 36
        assert rid.count("-") == 4


class TestStructuredErrorResponse:
    def test_404_returns_structured_error(self, client):
        resp = client.get("/api/v1/scores/NONEXISTENT_TICKER_XYZ")
        assert resp.status_code == 404
        body = resp.json()
        assert "error_code" in body
        assert "message" in body
        assert "request_id" in body
        assert "status_code" in body
        assert body["status_code"] == 404

    def test_404_has_request_id_header(self, client):
        resp = client.get("/api/v1/scores/NONEXISTENT_TICKER_XYZ")
        assert "x-request-id" in resp.headers
        body = resp.json()
        assert body["request_id"] == resp.headers["x-request-id"]
