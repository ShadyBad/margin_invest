"""Tests for GET /api/v1/scores/{ticker}/metrics endpoint."""

from __future__ import annotations

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
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 90.0,
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [],
            "average_percentile": 85.0,
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 88.0,
        },
        "filters_passed": [],
        "data_coverage": 1.0,
    }


def _make_price_bars(closes: list[float]) -> dict:
    """Build price bar dicts with sequential dates.

    Supports up to ~365 bars by spanning multiple months.
    """
    from datetime import date, timedelta

    start = date(2024, 1, 2)
    bars = []
    for i, close in enumerate(closes):
        d = start + timedelta(days=i)
        bars.append(
            {
                "date": d.isoformat(),
                "open": close,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": 1000000,
            }
        )
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

        # Generate 260 bars (need >= 253 for engine 1Y Sharpe/volatility)
        import random

        rng = random.Random(42)
        closes = [100.0]
        for _ in range(259):
            closes.append(round(closes[-1] * (1 + rng.gauss(0.0004, 0.01)), 4))
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
    # 1Y metrics should be computed from 10 bars
    assert data["sharpe_ratio"]["value"] is not None
    assert data["max_drawdown"]["value"] is not None
    assert data["volatility"]["value"] is not None
    assert data["avg_profit_margin"]["value"] is not None
    assert data["risk_classification"] in (
        "Conservative",
        "Moderate",
        "Moderate-High",
        "Aggressive",
    )
    assert data["margin_of_safety"]["value"] is not None

    # 3Y Sharpe and volatility should be None with only 260 bars (need >= 757)
    assert data["sharpe_ratio_3y"]["value"] is None
    assert data["sharpe_ratio_3y"]["unavailable_reason"] is not None
    # 3Y max_drawdown still computes (uses all available bars when < window)
    assert data["max_drawdown_3y"]["value"] is not None
    assert data["volatility_3y"]["value"] is None
    assert data["volatility_3y"]["unavailable_reason"] is not None

    # Delta should be computed from MIV=200 and actual=180
    assert data["delta"]["value"] is not None
    assert "allocation_weight" not in data


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


@pytest.mark.asyncio
async def test_metrics_delta_computed_correctly(client):
    """Delta = (margin_invest_value - actual_price) / actual_price."""
    resp = await client.get("/api/v1/scores/AAPL/metrics")
    assert resp.status_code == 200
    data = resp.json()
    # MIV=200.0, actual=180.0 -> delta = (200-180)/180 = 0.1111
    assert data["delta"]["value"] == pytest.approx(0.1111, abs=0.001)
    assert data["delta"]["unavailable_reason"] is None


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
    # 3Y also null
    assert data["sharpe_ratio_3y"]["value"] is None
    assert data["max_drawdown_3y"]["value"] is None
    assert data["volatility_3y"]["value"] is None
    # Delta null when no MIV/price
    assert data["delta"]["value"] is None
    assert data["delta"]["unavailable_reason"] is not None


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
                    {"close": "not_a_number", "date": "2025-01-01"},
                    {"close": "also_bad", "date": "2025-01-02"},
                    {"close": "still_bad", "date": "2025-01-03"},
                    {"close": "very_bad", "date": "2025-01-04"},
                    {"close": "worst", "date": "2025-01-05"},
                    {"close": "terrible", "date": "2025-01-06"},
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
async def test_metrics_no_allocation_weight_field(client_no_financial_data):
    """allocation_weight field has been removed from the response."""
    resp = await client_no_financial_data.get("/api/v1/scores/EMPTY/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "allocation_weight" not in data
