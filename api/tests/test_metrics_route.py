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
            margin_invest_value=200.0,
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
    assert data["sharpe_ratio"]["value"] is not None
    assert data["max_drawdown"]["value"] is not None
    assert data["volatility"]["value"] is not None
    assert data["avg_profit_margin"]["value"] is not None
    assert data["risk_classification"] in ("Conservative", "Moderate", "Moderate-High", "Aggressive")
    assert data["allocation_weight"]["value"] == 8.0
    assert data["margin_of_safety"]["value"] is not None


@pytest.mark.asyncio
async def test_metrics_sharpe_positive(client):
    resp = await client.get("/api/v1/scores/AAPL/metrics")
    data = resp.json()
    assert data["sharpe_ratio"]["value"] > 0


@pytest.mark.asyncio
async def test_metrics_margin_of_safety(client):
    resp = await client.get("/api/v1/scores/AAPL/metrics")
    data = resp.json()
    assert data["margin_of_safety"]["value"] == pytest.approx(0.1, abs=0.01)


@pytest.mark.asyncio
async def test_metrics_avg_profit_margin(client):
    resp = await client.get("/api/v1/scores/AAPL/metrics")
    data = resp.json()
    assert data["avg_profit_margin"]["value"] == pytest.approx(25.0, abs=0.5)


@pytest.mark.asyncio
async def test_metrics_unknown_ticker(client):
    resp = await client.get("/api/v1/scores/ZZZZZ/metrics")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Defensive tests: ensure graceful degradation when data is missing/malformed
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client_no_financial_data(async_engine):
    """Client where the ticker has a score but NO FinancialData rows."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        asset = Asset(
            ticker="EMPTY",
            name="Empty Corp.",
            sector="Information Technology",
            market_cap=Decimal("1000000000"),
        )
        session.add(asset)
        await session.flush()

        score = Score(
            asset_id=asset.id,
            composite_percentile=50.0,
            composite_raw_score=50.0,
            conviction_level="medium",
            signal="hold",
            quality_percentile=50.0,
            value_percentile=50.0,
            momentum_percentile=50.0,
            data_coverage=0.5,
            score_detail=_score_detail(),
        )
        session.add(score)
        await session.commit()

    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_metrics_with_missing_financial_data_returns_nulls(client_no_financial_data):
    """Metrics endpoint returns null metrics with reasons when data is missing."""
    resp = await client_no_financial_data.get("/api/v1/scores/EMPTY/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sharpe_ratio"]["value"] is None
    assert data["sharpe_ratio"]["unavailable_reason"] is not None
    assert data["max_drawdown"]["value"] is None
    assert data["volatility"]["value"] is None


@pytest_asyncio.fixture
async def client_malformed_prices(async_engine):
    """Client where FinancialData has malformed price_history (non-numeric closes)."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        asset = Asset(
            ticker="BAD",
            name="Bad Data Corp.",
            sector="Information Technology",
            market_cap=Decimal("1000000000"),
        )
        session.add(asset)
        await session.flush()

        score = Score(
            asset_id=asset.id,
            composite_percentile=50.0,
            composite_raw_score=50.0,
            conviction_level="medium",
            signal="hold",
            quality_percentile=50.0,
            value_percentile=50.0,
            momentum_percentile=50.0,
            data_coverage=0.5,
            score_detail=_score_detail(),
        )
        session.add(score)
        await session.flush()

        # Malformed price data: close values are strings, not floats
        fin_data = FinancialData(
            asset_id=asset.id,
            period_end="2025-01-10",
            filing_date="2025-01-15",
            price_history={
                "bars": [
                    {"close": "not_a_number"},
                    {"close": "also_bad"},
                    {"close": "still_bad"},
                    {"close": "very_bad"},
                    {"close": "worst"},
                    {"close": "terrible"},
                ]
            },
            income_statement={"net_income": "garbage", "total_revenue": "trash"},
        )
        session.add(fin_data)
        await session.commit()

    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_metrics_with_malformed_prices_returns_nulls(client_malformed_prices):
    """Metrics endpoint returns null metrics with reasons when data is malformed."""
    resp = await client_malformed_prices.get("/api/v1/scores/BAD/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sharpe_ratio"]["value"] is None
    assert data["max_drawdown"]["value"] is None
    assert data["volatility"]["value"] is None
    assert data["avg_profit_margin"]["value"] is None


@pytest.mark.asyncio
async def test_metrics_allocation_fallback_when_null(client_no_financial_data):
    """When max_position_pct is NULL, allocation_weight is computed from conviction + volatility."""
    resp = await client_no_financial_data.get("/api/v1/scores/EMPTY/metrics")
    assert resp.status_code == 200
    data = resp.json()
    # Should have a computed value, not None
    assert data["allocation_weight"]["value"] is not None
    assert data["allocation_weight"]["unavailable_reason"] is None
