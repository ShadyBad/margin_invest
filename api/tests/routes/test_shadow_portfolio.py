"""Tests for shadow portfolio API endpoints."""

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


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
