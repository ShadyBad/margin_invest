"""Tests for score alert trigger logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, ScoreAlert, User
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
async def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def seeded_db(session_factory):
    async with session_factory() as session:
        user = User(id=1, email="test@example.com", name="Test User")
        asset = Asset(
            id=1,
            ticker="AAPL",
            name="Apple Inc.",
            sector="TECHNOLOGY",
        )
        session.add_all([user, asset])
        await session.commit()
    return session_factory


@pytest.mark.asyncio
async def test_above_alert_fires_when_threshold_crossed(seeded_db):
    from margin_api.workers import _evaluate_alerts

    async with seeded_db() as session:
        alert = ScoreAlert(user_id=1, ticker="AAPL", alert_type="above", threshold=70.0)
        session.add(alert)
        await session.commit()

    triggered = await _evaluate_alerts(
        seeded_db,
        score_map={"AAPL": {"composite": 75.0, "survived": True}},
        prev_score_map={},
    )
    assert len(triggered) == 1
    assert triggered[0]["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_above_alert_does_not_fire_when_already_above(seeded_db):
    from margin_api.workers import _evaluate_alerts

    async with seeded_db() as session:
        alert = ScoreAlert(user_id=1, ticker="AAPL", alert_type="above", threshold=70.0)
        session.add(alert)
        await session.commit()

    triggered = await _evaluate_alerts(
        seeded_db,
        score_map={"AAPL": {"composite": 80.0, "survived": True}},
        prev_score_map={"AAPL": {"composite": 75.0, "survived": True}},
    )
    assert len(triggered) == 0


@pytest.mark.asyncio
async def test_below_alert_fires_when_threshold_crossed(seeded_db):
    from margin_api.workers import _evaluate_alerts

    async with seeded_db() as session:
        alert = ScoreAlert(user_id=1, ticker="AAPL", alert_type="below", threshold=40.0)
        session.add(alert)
        await session.commit()

    triggered = await _evaluate_alerts(
        seeded_db,
        score_map={"AAPL": {"composite": 35.0, "survived": False}},
        prev_score_map={"AAPL": {"composite": 50.0, "survived": True}},
    )
    assert len(triggered) == 1


@pytest.mark.asyncio
async def test_survivor_alert_fires_on_status_change(seeded_db):
    from margin_api.workers import _evaluate_alerts

    async with seeded_db() as session:
        alert = ScoreAlert(user_id=1, ticker="AAPL", alert_type="survivor")
        session.add(alert)
        await session.commit()

    triggered = await _evaluate_alerts(
        seeded_db,
        score_map={"AAPL": {"composite": 60.0, "survived": True}},
        prev_score_map={"AAPL": {"composite": 55.0, "survived": False}},
    )
    assert len(triggered) == 1


@pytest.mark.asyncio
async def test_cooldown_prevents_duplicate_notifications(seeded_db):
    from margin_api.workers import _evaluate_alerts

    async with seeded_db() as session:
        alert = ScoreAlert(
            user_id=1,
            ticker="AAPL",
            alert_type="above",
            threshold=70.0,
            last_triggered_at=datetime.now(UTC) - timedelta(hours=12),
        )
        session.add(alert)
        await session.commit()

    triggered = await _evaluate_alerts(
        seeded_db,
        score_map={"AAPL": {"composite": 75.0, "survived": True}},
        prev_score_map={},
    )
    assert len(triggered) == 0
