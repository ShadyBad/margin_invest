"""Additional metrics route tests — helper functions and edge cases."""

from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, FinancialData, Score
from margin_api.db.session import get_db
from margin_api.routes.metrics import _build_price_bars, _metric
from margin_api.schemas.metrics import MetricStatus
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class TestMetricHelper:
    def test_metric_with_value(self):
        result = _metric(42.5, "not used")
        assert result.value == 42.5
        assert result.unavailable_reason is None

    def test_metric_without_value(self):
        result = _metric(None, "insufficient data")
        assert result.value is None
        assert result.unavailable_reason == "insufficient data"


class TestBuildPriceBars:
    def test_capitalized_keys(self):
        bars = _build_price_bars([
            {
                "Close": 150.0,
                "Date": "2025-01-01",
                "Open": 149.0,
                "High": 151.0,
                "Low": 148.0,
                "Volume": 1000000,
            },
            {
                "Close": 152.0,
                "Date": "2025-01-02",
                "Open": 150.0,
                "High": 153.0,
                "Low": 149.5,
                "Volume": 2000000,
            },
        ])
        assert len(bars) == 2
        assert float(bars[0].close) == 150.0
        assert float(bars[1].close) == 152.0

    def test_lowercase_keys(self):
        bars = _build_price_bars([
            {"close": 100.0, "date": "2025-01-01", "open": 99.0, "high": 101.0, "low": 98.0, "volume": 500},
        ])
        assert len(bars) == 1

    def test_missing_close_skips_bar(self):
        bars = _build_price_bars([
            {"date": "2025-01-01", "open": 99.0},  # No close
        ])
        assert len(bars) == 0

    def test_missing_date_skips_bar(self):
        bars = _build_price_bars([
            {"close": 100.0, "open": 99.0},  # No date
        ])
        assert len(bars) == 0

    def test_long_datetime_trimmed(self):
        """yfinance datetime format '2025-02-14T00:00:00-05:00' is trimmed to date."""
        bars = _build_price_bars([
            {"close": 100.0, "date": "2025-02-14T00:00:00-05:00", "open": 99.0, "high": 101.0, "low": 98.0},
        ])
        assert len(bars) == 1
        assert str(bars[0].date) == "2025-02-14"

    def test_invalid_close_value_skips_bar(self):
        """Non-numeric close values skip the bar."""
        bars = _build_price_bars([
            {"close": "not_a_number", "date": "2025-01-01"},
        ])
        assert len(bars) == 0

    def test_empty_list(self):
        bars = _build_price_bars([])
        assert len(bars) == 0


def _score_detail() -> dict:
    return {
        "ticker": "TEST",
        "composite_percentile": 50.0,
        "conviction_level": "medium",
        "signal": "hold",
        "quality": {"factor_name": "quality", "weight": 0.35, "sub_scores": [], "average_percentile": 50.0},
        "value": {"factor_name": "value", "weight": 0.30, "sub_scores": [], "average_percentile": 50.0},
        "momentum": {"factor_name": "momentum", "weight": 0.35, "sub_scores": [], "average_percentile": 50.0},
        "filters_passed": [],
        "data_coverage": 1.0,
    }


class TestMetricsIncomeStatementFormats:
    """Test metrics endpoint with income_statement as list vs dict."""

    @pytest_asyncio.fixture
    async def engine(self):
        eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield eng
        await eng.dispose()

    @pytest.mark.asyncio
    async def test_income_statement_as_single_dict(self, engine):
        """income_statement as a single dict (not list) is handled."""
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            asset = Asset(
                ticker="DICT",
                name="Dict Corp.",
                sector="Technology",
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
                margin_invest_value=100.0,
                actual_price=100.0,
            )
            session.add(score)
            await session.flush()

            fin_data = FinancialData(
                asset_id=asset.id,
                period_end="2025-01-10",
                filing_date="2025-01-15",
                price_history={"bars": []},
                income_statement={"net_income": 5000000, "total_revenue": 20000000},
            )
            session.add(fin_data)
            await session.commit()

        app = create_app()

        async def override_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/DICT/metrics")

        assert resp.status_code == 200
        data = resp.json()
        # income_statement as dict should be converted to single-element list
        assert data["avg_profit_margin"]["value"] == pytest.approx(25.0, abs=0.5)

    @pytest.mark.asyncio
    async def test_income_statement_as_list(self, engine):
        """income_statement as a list of periods."""
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            asset = Asset(
                ticker="LIST",
                name="List Corp.",
                sector="Technology",
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

            fin_data = FinancialData(
                asset_id=asset.id,
                period_end="2025-01-10",
                filing_date="2025-01-15",
                price_history={"bars": []},
                income_statement=[
                    {"net_income": 10000000, "total_revenue": 50000000},
                    {"net_income": 15000000, "total_revenue": 50000000},
                ],
            )
            session.add(fin_data)
            await session.commit()

        app = create_app()

        async def override_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/LIST/metrics")

        assert resp.status_code == 200
        data = resp.json()
        # Average of 20% and 30% = 25%
        assert data["avg_profit_margin"]["value"] == pytest.approx(25.0, abs=0.5)

    @pytest.mark.asyncio
    async def test_metrics_with_few_price_bars(self, engine):
        """Metrics with < 5 bars reports insufficient data."""
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            asset = Asset(
                ticker="FEW",
                name="Few Bars Corp.",
                sector="Technology",
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

            fin_data = FinancialData(
                asset_id=asset.id,
                period_end="2025-01-10",
                filing_date="2025-01-15",
                price_history={"bars": [
                    {"close": 100.0, "date": "2025-01-01"},
                    {"close": 101.0, "date": "2025-01-02"},
                    {"close": 102.0, "date": "2025-01-03"},
                ]},
            )
            session.add(fin_data)
            await session.commit()

        app = create_app()

        async def override_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/FEW/metrics")

        assert resp.status_code == 200
        data = resp.json()
        assert data["sharpe_ratio"]["value"] is None
        assert "Insufficient" in data["sharpe_ratio"]["unavailable_reason"]
