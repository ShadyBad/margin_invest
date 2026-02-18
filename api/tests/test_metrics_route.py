"""Tests for GET /api/v1/scores/{ticker}/metrics endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, FinancialData, Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _score_detail() -> dict:
    return {
        "ticker": "AAPL",
        "composite_percentile": 95.0,
        "conviction_level": "high",
        "signal": "buy",
        "quality": {"factor_name": "quality", "weight": 0.35, "sub_scores": [], "average_percentile": 90.0},
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": 85.0},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": 88.0},
        "filters_passed": [],
        "data_coverage": 1.0,
    }


def _make_price_bars(closes: list[float]) -> dict:
    bars = []
    for i, close in enumerate(closes):
        bars.append({
            "date": f"2025-01-{i + 1:02d}",
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1000000,
        })
    return {"bars": bars}


def _make_income_data() -> dict:
    return {
        "net_income": 25000000000,
        "total_revenue": 100000000000,
    }


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
async def seeded_session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        asset = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(asset)
        await session.flush()

        score = Score(
            asset_id=asset.id,
            composite_percentile=95.0,
            composite_raw_score=87.5,
            conviction_level="high",
            signal="buy",
            quality_percentile=90.0,
            value_percentile=85.0,
            momentum_percentile=88.0,
            data_coverage=1.0,
            score_detail=_score_detail(),
            intrinsic_value=200.0,
            buy_price=200.0,
            sell_price=250.0,
            actual_price=180.0,
            max_position_pct=8.0,
        )
        session.add(score)
        await session.flush()

        closes = [100.0, 101.0, 100.5, 102.0, 101.5, 103.0, 102.5, 104.0, 103.5, 105.0]
        fin_data = FinancialData(
            asset_id=asset.id,
            period_end="2025-01-10",
            filing_date="2025-01-15",
            price_history=_make_price_bars(closes),
            income_statement=_make_income_data(),
        )
        session.add(fin_data)
        await session.commit()
    return factory


@pytest_asyncio.fixture
async def client(seeded_session):
    app = create_app()

    async def override_get_db():
        async with seeded_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_metrics_returns_all_fields(client):
    resp = await client.get("/api/v1/scores/AAPL/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sharpe_ratio"] is not None
    assert data["max_drawdown"] is not None
    assert data["volatility"] is not None
    assert data["avg_profit_margin"] is not None
    assert data["risk_classification"] in ("Conservative", "Moderate", "Moderate-High", "Aggressive")
    assert data["allocation_weight"] == 8.0
    assert data["margin_of_safety"] is not None


@pytest.mark.asyncio
async def test_metrics_sharpe_positive(client):
    resp = await client.get("/api/v1/scores/AAPL/metrics")
    data = resp.json()
    assert data["sharpe_ratio"] > 0


@pytest.mark.asyncio
async def test_metrics_margin_of_safety(client):
    resp = await client.get("/api/v1/scores/AAPL/metrics")
    data = resp.json()
    assert data["margin_of_safety"] == pytest.approx(0.1, abs=0.01)


@pytest.mark.asyncio
async def test_metrics_avg_profit_margin(client):
    resp = await client.get("/api/v1/scores/AAPL/metrics")
    data = resp.json()
    assert data["avg_profit_margin"] == pytest.approx(25.0, abs=0.5)


@pytest.mark.asyncio
async def test_metrics_unknown_ticker(client):
    resp = await client.get("/api/v1/scores/ZZZZZ/metrics")
    assert resp.status_code == 404
