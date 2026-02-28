"""Tests for GET /api/v1/scores/{ticker}/valuation-audit endpoint."""

from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _score_detail_with_audit() -> dict:
    return {
        "ticker": "AAPL",
        "composite_percentile": 95.0,
        "composite_tier": "high",
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
        "valuation_audit": {
            "margin_invest_value": 195.50,
            "margin_of_safety": 0.2500,
            "buy_price": 146.63,
            "sell_price": 244.38,
            "actual_price": 180.0,
            "methods": [
                {
                    "method": "dcf",
                    "result_per_share": 200.0,
                    "weight": 0.35,
                    "renormalized_weight": 0.35,
                    "included": True,
                    "exclusion_reason": None,
                    "inputs": {
                        "fcf": 110e9,
                        "growth_rate": 0.05,
                        "discount_rate": 0.10,
                    },
                    "intermediates": {
                        "pv_stage1": 1.2e12,
                        "pv_terminal": 2.8e12,
                    },
                },
                {
                    "method": "ev_fcf",
                    "result_per_share": 185.0,
                    "weight": 0.25,
                    "renormalized_weight": 0.25,
                    "included": True,
                    "exclusion_reason": None,
                    "inputs": {
                        "fcf": 100e9,
                        "target_multiple": 15.0,
                    },
                    "intermediates": {
                        "implied_ev": 1.5e12,
                        "implied_equity": 1.4e12,
                    },
                },
            ],
            "mos_base": 0.25,
            "mos_cv": 0.045,
            "mos_adjustment": -0.0273,
            "was_clamped": False,
            "clamp_reason": None,
        },
    }


def _score_detail_without_audit() -> dict:
    return {
        "ticker": "MSFT",
        "composite_percentile": 80.0,
        "composite_tier": "medium",
        "signal": "hold",
        "quality": {
            "factor_name": "quality",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 75.0,
        },
        "value": {
            "factor_name": "value",
            "weight": 0.30,
            "sub_scores": [],
            "average_percentile": 70.0,
        },
        "momentum": {
            "factor_name": "momentum",
            "weight": 0.35,
            "sub_scores": [],
            "average_percentile": 72.0,
        },
        "filters_passed": [],
        "data_coverage": 0.9,
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
        # Asset with valuation audit data
        asset_aapl = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(asset_aapl)
        await session.flush()

        score_aapl = Score(
            asset_id=asset_aapl.id,
            composite_percentile=95.0,
            composite_raw_score=87.5,
            conviction_level="high",
            signal="buy",
            quality_percentile=90.0,
            value_percentile=85.0,
            momentum_percentile=88.0,
            data_coverage=1.0,
            score_detail=_score_detail_with_audit(),
            margin_invest_value=195.50,
            buy_price=146.63,
            sell_price=244.38,
            actual_price=180.0,
        )
        session.add(score_aapl)

        # Asset without valuation audit data
        asset_msft = Asset(
            ticker="MSFT",
            name="Microsoft Corp.",
            sector="Information Technology",
            market_cap=Decimal("2800000000000"),
        )
        session.add(asset_msft)
        await session.flush()

        score_msft = Score(
            asset_id=asset_msft.id,
            composite_percentile=80.0,
            composite_raw_score=72.0,
            conviction_level="medium",
            signal="hold",
            quality_percentile=75.0,
            value_percentile=70.0,
            momentum_percentile=72.0,
            data_coverage=0.9,
            score_detail=_score_detail_without_audit(),
        )
        session.add(score_msft)

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
async def test_valuation_audit_returns_methods(client):
    """Verify 200 response with methods, margin_invest_value, and margin_of_safety."""
    resp = await client.get("/api/v1/scores/AAPL/valuation-audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["margin_invest_value"] == pytest.approx(195.50)
    assert data["margin_of_safety"] == pytest.approx(0.2500)
    assert len(data["methods"]) == 2
    assert data["methods"][0]["method"] == "dcf"
    assert data["methods"][1]["method"] == "ev_fcf"


@pytest.mark.asyncio
async def test_valuation_audit_method_details(client):
    """Verify individual method has inputs and intermediates dicts."""
    resp = await client.get("/api/v1/scores/AAPL/valuation-audit")
    assert resp.status_code == 200
    data = resp.json()
    dcf = data["methods"][0]
    assert dcf["method"] == "dcf"
    assert dcf["result_per_share"] == pytest.approx(200.0)
    assert dcf["weight"] == pytest.approx(0.35)
    assert dcf["renormalized_weight"] == pytest.approx(0.35)
    assert dcf["included"] is True
    assert dcf["exclusion_reason"] is None
    # Inputs
    assert "fcf" in dcf["inputs"]
    assert "growth_rate" in dcf["inputs"]
    assert "discount_rate" in dcf["inputs"]
    assert dcf["inputs"]["growth_rate"] == pytest.approx(0.05)
    # Intermediates
    assert "pv_stage1" in dcf["intermediates"]
    assert "pv_terminal" in dcf["intermediates"]


@pytest.mark.asyncio
async def test_valuation_audit_unknown_ticker(client):
    """404 for unknown ticker."""
    resp = await client.get("/api/v1/scores/ZZZZZ/valuation-audit")
    assert resp.status_code == 404
    body = resp.json()
    detail = body.get("detail") or body.get("message", "")
    assert "No score found" in detail


@pytest.mark.asyncio
async def test_valuation_audit_no_audit_data(client):
    """404 when score_detail has no valuation_audit key."""
    resp = await client.get("/api/v1/scores/MSFT/valuation-audit")
    assert resp.status_code == 404
    body = resp.json()
    detail = body.get("detail") or body.get("message", "")
    assert "No valuation audit available" in detail


@pytest.mark.asyncio
async def test_valuation_audit_mos_components(client):
    """Verify mos_base, mos_cv, mos_adjustment are present and correct."""
    resp = await client.get("/api/v1/scores/AAPL/valuation-audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mos_base"] == pytest.approx(0.25)
    assert data["mos_cv"] == pytest.approx(0.045)
    assert data["mos_adjustment"] == pytest.approx(-0.0273)
    assert data["was_clamped"] is False
    assert data["clamp_reason"] is None


@pytest.mark.asyncio
async def test_valuation_audit_buy_sell_prices(client):
    """Verify buy_price, sell_price, and actual_price are present."""
    resp = await client.get("/api/v1/scores/AAPL/valuation-audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["buy_price"] == pytest.approx(146.63)
    assert data["sell_price"] == pytest.approx(244.38)
    assert data["actual_price"] == pytest.approx(180.0)


@pytest.mark.asyncio
async def test_valuation_audit_case_insensitive_ticker(client):
    """Ticker should be case insensitive."""
    resp = await client.get("/api/v1/scores/aapl/valuation-audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["margin_invest_value"] == pytest.approx(195.50)
