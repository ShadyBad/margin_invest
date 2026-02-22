"""Tests for universe service functions."""

from __future__ import annotations

from datetime import UTC, datetime
from textwrap import dedent

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import UniverseSnapshot
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


class TestActivateUniverse:
    @pytest.mark.asyncio
    async def test_activate_creates_snapshot(self, session, tmp_path):
        from margin_api.services.universe import activate_universe

        config_file = tmp_path / "universe.yaml"
        config_file.write_text(
            dedent("""\
            version: "2026.02.15"
            description: "Test"
            tickers:
              - AAPL
              - MSFT
        """)
        )
        snapshot = await activate_universe(session, config_file)
        assert snapshot.version == "2026.02.15"
        assert snapshot.ticker_count == 2
        assert snapshot.is_active is True

    @pytest.mark.asyncio
    async def test_activate_deactivates_previous(self, session, tmp_path):
        from margin_api.services.universe import activate_universe

        config_file = tmp_path / "universe.yaml"
        config_file.write_text("version: 'v1'\ntickers:\n  - AAPL\n")
        s1 = await activate_universe(session, config_file)

        config_file.write_text("version: 'v2'\ntickers:\n  - MSFT\n")
        s2 = await activate_universe(session, config_file)

        await session.refresh(s1)
        assert s1.is_active is False
        assert s2.is_active is True


class TestGetActiveSnapshot:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_snapshot(self, session):
        from margin_api.services.universe import get_active_snapshot

        result = await get_active_snapshot(session)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_active_snapshot(self, session):
        from margin_api.services.universe import get_active_snapshot

        snapshot = UniverseSnapshot(
            version="v1",
            config_hash="a" * 64,
            ticker_count=1,
            tickers=["AAPL"],
            exclusion_rules={},
            is_active=True,
            activated_at=datetime.now(UTC),
        )
        session.add(snapshot)
        await session.commit()

        result = await get_active_snapshot(session)
        assert result is not None
        assert result.version == "v1"
