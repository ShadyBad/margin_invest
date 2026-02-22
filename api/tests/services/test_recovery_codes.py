"""Tests for RecoveryCodeService."""

from __future__ import annotations

import re

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import RecoveryCode, User
from margin_api.services.recovery_codes import RecoveryCodeService
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture()
def service():
    return RecoveryCodeService()


@pytest_asyncio.fixture()
async def credential_user(db_session) -> User:
    u = User(
        email="recovery@example.com",
        name="recoverytest",
        password_hash="hashed_password",
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


class TestGenerateCodes:
    @pytest.mark.asyncio
    async def test_generates_eight_codes(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        assert len(codes) == 8

    @pytest.mark.asyncio
    async def test_codes_match_format(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        for code in codes:
            assert re.match(r"^[a-z2-9]{4}-[a-z2-9]{4}$", code)

    @pytest.mark.asyncio
    async def test_no_ambiguous_characters(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        ambiguous = set("0oO1lI")
        for code in codes:
            assert not ambiguous.intersection(code.replace("-", ""))

    @pytest.mark.asyncio
    async def test_codes_stored_hashed(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        result = await db_session.execute(
            select(RecoveryCode).where(RecoveryCode.user_id == credential_user.id)
        )
        stored = result.scalars().all()
        assert len(stored) == 8
        for rc in stored:
            assert rc.code_hash not in codes

    @pytest.mark.asyncio
    async def test_regenerate_deletes_old_codes(self, service, db_session, credential_user):
        await service.generate_codes(db_session, credential_user.id)
        await service.generate_codes(db_session, credential_user.id)
        result = await db_session.execute(
            select(func.count())
            .select_from(RecoveryCode)
            .where(RecoveryCode.user_id == credential_user.id)
        )
        assert result.scalar() == 8


class TestVerifyCode:
    @pytest.mark.asyncio
    async def test_valid_code_returns_true(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        assert await service.verify_code(db_session, credential_user.id, codes[0]) is True

    @pytest.mark.asyncio
    async def test_used_code_returns_false(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        await service.verify_code(db_session, credential_user.id, codes[0])
        assert await service.verify_code(db_session, credential_user.id, codes[0]) is False

    @pytest.mark.asyncio
    async def test_code_works_without_hyphen(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        no_hyphen = codes[0].replace("-", "")
        assert await service.verify_code(db_session, credential_user.id, no_hyphen) is True

    @pytest.mark.asyncio
    async def test_invalid_code_returns_false(self, service, db_session, credential_user):
        await service.generate_codes(db_session, credential_user.id)
        assert (
            await service.verify_code(db_session, credential_user.id, "zzzz-zzzz") is False
        )


class TestRemainingCount:
    @pytest.mark.asyncio
    async def test_returns_count_of_unused(self, service, db_session, credential_user):
        codes = await service.generate_codes(db_session, credential_user.id)
        assert await service.remaining_count(db_session, credential_user.id) == 8
        await service.verify_code(db_session, credential_user.id, codes[0])
        assert await service.remaining_count(db_session, credential_user.id) == 7
