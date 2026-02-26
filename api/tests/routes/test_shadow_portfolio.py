"""Tests for shadow portfolio API endpoints."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
def client():
    """Client with an institutional-plan user for gated shadow-portfolio endpoint."""

    async def _setup():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            user = User(
                email="test@test.com",
                name="Test User",
                subscription_plan="institutional",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id
        return engine, factory, user_id

    engine, factory, user_id = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
        _setup()
    )

    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    tc = TestClient(app)
    yield tc
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(engine.dispose())


class TestShadowPortfolioEndpoint:
    def test_get_shadow_portfolio_returns_200(self, client):
        response = client.get("/api/v1/backtest/shadow-portfolio")
        assert response.status_code == 200

    def test_shadow_portfolio_has_required_fields(self, client):
        response = client.get("/api/v1/backtest/shadow-portfolio")
        data = response.json()
        assert "start_date" in data
        assert "snapshots" in data
        assert "total_return" in data
        assert "max_drawdown" in data
        assert "num_days" in data
        assert "cannot_be_backdated" in data

    def test_shadow_portfolio_cannot_be_backdated_true(self, client):
        response = client.get("/api/v1/backtest/shadow-portfolio")
        data = response.json()
        assert data["cannot_be_backdated"] is True

    def test_shadow_portfolio_empty_initially(self, client):
        response = client.get("/api/v1/backtest/shadow-portfolio")
        data = response.json()
        assert data["snapshots"] == []
        assert data["total_return"] == 0.0
        assert data["num_days"] == 0


class TestShadowPortfolioDBModel:
    def test_model_is_importable(self):
        from margin_api.db.models import ShadowPortfolioSnapshot

        assert ShadowPortfolioSnapshot.__tablename__ == "shadow_portfolio_snapshots"

    def test_model_has_required_columns(self):
        from margin_api.db.models import ShadowPortfolioSnapshot

        columns = {c.name for c in ShadowPortfolioSnapshot.__table__.columns}
        required = {
            "id",
            "as_of_date",
            "portfolio_value",
            "total_return",
            "num_positions",
            "positions_json",
            "recorded_at",
        }
        assert required.issubset(columns)
