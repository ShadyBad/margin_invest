"""Tests for insider_service — is_first_purchase() query."""

from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import InsiderTransactionHistory
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


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
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


def _make_record(**overrides) -> InsiderTransactionHistory:
    """Create an InsiderTransactionHistory with sensible defaults."""
    defaults = {
        "ticker": "AAPL",
        "cik": "0000320193",
        "insider_cik": "0001234",
        "insider_name": "Test Insider",
        "title": "Director",
        "transaction_type": "P",
        "transaction_date": date(2024, 1, 15),
        "shares": 1000,
        "price_per_share": 150.0,
        "total_value": 150000.0,
        "accession_number": "0001234-24-000001",
        "filing_date": date(2024, 1, 16),
    }
    defaults.update(overrides)
    return InsiderTransactionHistory(**defaults)


class TestIsFirstPurchase:
    @pytest.mark.asyncio
    async def test_first_purchase_no_history(self, session):
        """No prior purchases = this is a first purchase."""
        from margin_api.services.insider_service import is_first_purchase

        result = await is_first_purchase(session, "AAPL", "0001234")
        assert result is True

    @pytest.mark.asyncio
    async def test_not_first_purchase_with_history(self, session):
        """Prior purchase exists = not a first purchase."""
        from margin_api.services.insider_service import is_first_purchase

        session.add(_make_record())
        await session.flush()

        result = await is_first_purchase(session, "AAPL", "0001234")
        assert result is False

    @pytest.mark.asyncio
    async def test_different_ticker_is_first(self, session):
        """Purchase in different ticker doesn't count."""
        from margin_api.services.insider_service import is_first_purchase

        session.add(
            _make_record(
                ticker="MSFT",
                cik="0000789019",
                accession_number="0001234-24-000002",
            )
        )
        await session.flush()

        result = await is_first_purchase(session, "AAPL", "0001234")
        assert result is True  # No AAPL purchases

    @pytest.mark.asyncio
    async def test_different_insider_is_first(self, session):
        """Purchase by different insider doesn't count."""
        from margin_api.services.insider_service import is_first_purchase

        session.add(
            _make_record(
                insider_cik="0009999",
                insider_name="Other Insider",
                accession_number="0009999-24-000001",
            )
        )
        await session.flush()

        result = await is_first_purchase(session, "AAPL", "0001234")
        assert result is True  # Different insider

    @pytest.mark.asyncio
    async def test_sale_does_not_count(self, session):
        """A sale ('S') transaction does not make it a prior purchase."""
        from margin_api.services.insider_service import is_first_purchase

        session.add(
            _make_record(
                transaction_type="S",
                accession_number="0001234-24-000003",
            )
        )
        await session.flush()

        result = await is_first_purchase(session, "AAPL", "0001234")
        assert result is True  # Sale, not purchase

    @pytest.mark.asyncio
    async def test_multiple_purchases_not_first(self, session):
        """Multiple prior purchases = still not first."""
        from margin_api.services.insider_service import is_first_purchase

        session.add(_make_record())
        session.add(
            _make_record(
                transaction_date=date(2024, 3, 15),
                accession_number="0001234-24-000004",
            )
        )
        await session.flush()

        result = await is_first_purchase(session, "AAPL", "0001234")
        assert result is False
