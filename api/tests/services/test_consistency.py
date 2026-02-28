"""Tests for the post-ingestion consistency validation service."""

from __future__ import annotations

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, FinancialData
from margin_api.services.consistency import (
    validate_ticker_consistency,
    validate_universe_consistency,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


# ---------------------------------------------------------------------------
# Financial data helpers — realistic, stable by default
# ---------------------------------------------------------------------------


def _income(revenue: int = 100_000, ebit: int = 20_000, shares: int = 1_000_000) -> dict:
    return {
        "revenue": str(revenue),
        "costOfRevenue": str(revenue // 2),
        "grossProfit": str(revenue // 2),
        "ebit": str(ebit),
        "netIncome": str(ebit),
        "interestExpense": "0",
        "incomeTaxExpense": "0",
        "sharesOutstanding": shares,
    }


def _balance(total_assets: int = 500_000, shares: int = 1_000_000) -> dict:
    return {
        "totalAssets": str(total_assets),
        "totalCurrentAssets": str(total_assets // 3),
        "cashAndCashEquivalents": str(total_assets // 10),
        "netReceivables": str(total_assets // 10),
        "totalLiabilities": str(total_assets // 2),
        "totalCurrentLiabilities": str(total_assets // 4),
        "longTermDebt": str(total_assets // 4),
        "totalStockholdersEquity": str(total_assets // 2),
        "retainedEarnings": str(total_assets // 10),
        "propertyPlantEquipmentNet": str(total_assets // 5),
        "sharesOutstanding": shares,
    }


def _cashflow(operating_cf: int = 25_000, capex: int = -5_000) -> dict:
    return {
        "operatingCashFlow": str(operating_cf),
        "capitalExpenditure": str(capex),
        "dividendsPaid": "0",
        "commonStockRepurchased": "0",
        "commonStockIssued": "0",
    }


async def _create_asset(session: AsyncSession, ticker: str = "AAPL") -> Asset:
    asset = Asset(ticker=ticker, name=f"{ticker} Inc", sector="Information Technology")
    session.add(asset)
    await session.commit()
    return asset


async def _add_period(
    session: AsyncSession,
    asset: Asset,
    period_end: str,
    revenue: int = 100_000,
    shares: int = 1_000_000,
) -> FinancialData:
    fd = FinancialData(
        asset_id=asset.id,
        period_end=period_end,
        filing_date=period_end,
        income_statement=_income(revenue=revenue, shares=shares),
        balance_sheet=_balance(shares=shares),
        cash_flow=_cashflow(),
        source="yfinance",
    )
    session.add(fd)
    await session.commit()
    return fd


class TestValidateTickerConsistency:
    @pytest.mark.asyncio
    async def test_stable_ticker_no_anomalies(self, session):
        """Stable data across 5 periods should produce no anomaly flags."""
        asset = await _create_asset(session, "STABLE")
        for i, year in enumerate(range(2020, 2025)):
            # Slight revenue variation — all within normal bounds
            await _add_period(session, asset, f"{year}-12-31", revenue=100_000 + i * 2_000)

        result = await validate_ticker_consistency(session, "STABLE")
        assert result is not None
        assert result["has_anomalies"] is False
        assert result["anomalies"] == []
        assert len(result["all_flags"]) > 0  # flags exist, just none are anomalous

    @pytest.mark.asyncio
    async def test_anomalous_ticker_detected(self, session):
        """A 4x shares_outstanding jump should be flagged as an anomaly."""
        asset = await _create_asset(session, "SPLIT")
        for year in range(2020, 2024):
            await _add_period(session, asset, f"{year}-12-31", shares=1_000_000)
        # Last period: 4x spike in shares outstanding
        await _add_period(session, asset, "2024-12-31", shares=4_000_000)

        result = await validate_ticker_consistency(session, "SPLIT")
        assert result is not None
        assert result["has_anomalies"] is True
        anomaly_fields = {a["field_name"] for a in result["anomalies"]}
        assert "shares_outstanding" in anomaly_fields

    @pytest.mark.asyncio
    async def test_unknown_ticker_returns_none(self, session):
        """Non-existent ticker should return None."""
        result = await validate_ticker_consistency(session, "DOESNOTEXIST")
        assert result is None

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_none(self, session):
        """Less than 3 financial data rows should return None."""
        asset = await _create_asset(session, "SHORT")
        await _add_period(session, asset, "2023-12-31")
        await _add_period(session, asset, "2024-12-31")

        result = await validate_ticker_consistency(session, "SHORT")
        assert result is None

    @pytest.mark.asyncio
    async def test_flags_persisted_to_db(self, session):
        """After validation, the latest FinancialData row should have consistency_flags."""
        asset = await _create_asset(session, "PERSIST")
        for year in range(2020, 2024):
            await _add_period(session, asset, f"{year}-12-31", shares=1_000_000)
        # Anomalous period
        await _add_period(session, asset, "2024-12-31", shares=4_000_000)

        await validate_ticker_consistency(session, "PERSIST")

        # Reload the latest row from DB
        from sqlalchemy import select

        stmt = (
            select(FinancialData)
            .where(FinancialData.asset_id == asset.id)
            .order_by(FinancialData.period_end.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        latest = result.scalar_one()
        assert latest.consistency_flags is not None
        assert latest.consistency_flags["has_anomalies"] is True
        assert len(latest.consistency_flags["anomalies"]) >= 1


class TestValidateUniverseConsistency:
    @pytest.mark.asyncio
    async def test_universe_validates_all_active_tickers(self, session):
        """validate_universe_consistency should process all tickers when none specified."""
        # Create two assets with data
        for ticker in ("AAA", "BBB"):
            asset = await _create_asset(session, ticker)
            for year in range(2020, 2025):
                await _add_period(session, asset, f"{year}-12-31")

        results = await validate_universe_consistency(session)
        assert "AAA" in results
        assert "BBB" in results
        assert results["AAA"]["has_anomalies"] is False
        assert results["BBB"]["has_anomalies"] is False

    @pytest.mark.asyncio
    async def test_universe_with_explicit_tickers(self, session):
        """When tickers are passed, only those should be validated."""
        for ticker in ("AAA", "BBB", "CCC"):
            asset = await _create_asset(session, ticker)
            for year in range(2020, 2025):
                await _add_period(session, asset, f"{year}-12-31")

        results = await validate_universe_consistency(session, tickers=["AAA", "CCC"])
        assert "AAA" in results
        assert "CCC" in results
        assert "BBB" not in results
