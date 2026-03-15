"""Tests for SIC->GICS sector mapping."""

from __future__ import annotations

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import SICSectorMap
from margin_engine.models.financial import GICSSector
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
        # Seed test data
        sess.add_all(
            [
                SICSectorMap(
                    sic_code=3571,
                    gics_sector="Information Technology",
                    sic_description="Computers",
                ),
                SICSectorMap(
                    sic_code=2830,
                    gics_sector="Health Care",
                    sic_description="Pharmaceuticals",
                ),
                SICSectorMap(
                    sic_code=6020,
                    gics_sector="Financials",
                    sic_description="Banking",
                ),
            ]
        )
        await sess.commit()
        yield sess


class TestSICMapper:
    @pytest.mark.asyncio
    async def test_known_sic_code(self, session):
        from margin_api.services.sic_mapper import SICMapper

        mapper = await SICMapper.load(session)
        assert mapper.to_gics(3571) == GICSSector.TECHNOLOGY

    @pytest.mark.asyncio
    async def test_unknown_sic_falls_back_to_industrials(self, session):
        from margin_api.services.sic_mapper import SICMapper

        mapper = await SICMapper.load(session)
        assert mapper.to_gics(9999) == GICSSector.INDUSTRIALS

    @pytest.mark.asyncio
    async def test_none_sic_falls_back_to_industrials(self, session):
        from margin_api.services.sic_mapper import SICMapper

        mapper = await SICMapper.load(session)
        assert mapper.to_gics(None) == GICSSector.INDUSTRIALS

    @pytest.mark.asyncio
    async def test_pharma_maps_to_healthcare(self, session):
        from margin_api.services.sic_mapper import SICMapper

        mapper = await SICMapper.load(session)
        assert mapper.to_gics(2830) == GICSSector.HEALTHCARE

    @pytest.mark.asyncio
    async def test_financials(self, session):
        from margin_api.services.sic_mapper import SICMapper

        mapper = await SICMapper.load(session)
        assert mapper.to_gics(6020) == GICSSector.FINANCIALS
