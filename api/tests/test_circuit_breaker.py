"""Tests for the circuit breaker service.

Verifies score drift detection, ingestion failure rate checks,
and ML regression detection with appropriate thresholds.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.services.circuit_breaker import (
    CircuitBreakerResult,
    check_ingestion_failure_rate,
    check_ml_regression,
    check_score_drift,
)
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
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


async def _create_asset(session: AsyncSession, ticker: str = "AAPL") -> Asset:
    """Create a test asset."""
    asset = Asset(
        ticker=ticker,
        name=f"{ticker} Inc.",
        sector="Technology",
        market_cap=Decimal("1000000000"),
    )
    session.add(asset)
    await session.flush()
    return asset


async def _create_v4_score(
    session: AsyncSession,
    asset: Asset,
    conviction: str = "high",
    scored_at: datetime | None = None,
    published: bool = False,
) -> V4Score:
    """Create a test V4Score."""
    score = V4Score(
        asset_id=asset.id,
        opportunity_type="value",
        conviction=conviction,
        rules_conviction=conviction,
        style="value",
        timing_signal="neutral",
        max_position_pct=5.0,
        regime="normal",
        composite_score=75.0,
        ml_override="none",
        published=published,
    )
    if scored_at is not None:
        score.scored_at = scored_at
    session.add(score)
    await session.flush()
    return score


# ---------------------------------------------------------------------------
# check_score_drift tests
# ---------------------------------------------------------------------------


class TestCheckScoreDrift:
    """Tests for check_score_drift circuit breaker."""

    @pytest.mark.asyncio
    async def test_triggers_when_above_threshold(self, db_session: AsyncSession):
        """Score drift triggers when >30% of universe changes conviction."""
        now = datetime.now(UTC)
        old_time = now - timedelta(days=1)

        # Create 10 assets, each with a published score and an unpublished new score.
        # 4 out of 10 change conviction (40% > 30% threshold) -> should trigger.
        for i in range(10):
            asset = await _create_asset(db_session, ticker=f"T{i:02d}")
            # Old published score: conviction "high"
            await _create_v4_score(
                db_session, asset, conviction="high", scored_at=old_time, published=True
            )
            # New unpublished score: 4 change to "medium", 6 stay "high"
            new_conviction = "medium" if i < 4 else "high"
            await _create_v4_score(
                db_session, asset, conviction=new_conviction, scored_at=now, published=False
            )

        await db_session.commit()

        result = await check_score_drift(db_session, scored_at=now, threshold_pct=0.30)

        assert result.triggered is True
        assert result.drift_pct == pytest.approx(0.4)
        assert "4" in result.detail or "40" in result.detail

    @pytest.mark.asyncio
    async def test_does_not_trigger_below_threshold(self, db_session: AsyncSession):
        """Score drift does NOT trigger when drift is below threshold."""
        now = datetime.now(UTC)
        old_time = now - timedelta(days=1)

        # Create 10 assets: only 2 change conviction (20% < 30% threshold).
        for i in range(10):
            asset = await _create_asset(db_session, ticker=f"T{i:02d}")
            await _create_v4_score(
                db_session, asset, conviction="high", scored_at=old_time, published=True
            )
            new_conviction = "medium" if i < 2 else "high"
            await _create_v4_score(
                db_session, asset, conviction=new_conviction, scored_at=now, published=False
            )

        await db_session.commit()

        result = await check_score_drift(db_session, scored_at=now, threshold_pct=0.30)

        assert result.triggered is False
        assert result.drift_pct == pytest.approx(0.2)

    @pytest.mark.asyncio
    async def test_no_new_scores_returns_not_triggered(self, db_session: AsyncSession):
        """Score drift with no new scores returns triggered=False."""
        now = datetime.now(UTC)

        result = await check_score_drift(db_session, scored_at=now, threshold_pct=0.30)

        assert result.triggered is False
        assert result.drift_pct == 0.0


# ---------------------------------------------------------------------------
# check_ingestion_failure_rate tests
# ---------------------------------------------------------------------------


class TestCheckIngestionFailureRate:
    """Tests for check_ingestion_failure_rate circuit breaker."""

    def test_triggers_above_threshold(self):
        """Ingestion failure rate triggers at >20%."""
        result = check_ingestion_failure_rate(
            failed_count=25, total_count=100, threshold_pct=0.20
        )

        assert result.triggered is True
        assert result.drift_pct == pytest.approx(0.25)

    def test_does_not_trigger_below_threshold(self):
        """Ingestion failure rate does not trigger below threshold."""
        result = check_ingestion_failure_rate(
            failed_count=15, total_count=100, threshold_pct=0.20
        )

        assert result.triggered is False
        assert result.drift_pct == pytest.approx(0.15)

    def test_zero_total_returns_not_triggered(self):
        """Zero total count returns triggered=False (avoid divide by zero)."""
        result = check_ingestion_failure_rate(
            failed_count=0, total_count=0, threshold_pct=0.20
        )

        assert result.triggered is False
        assert result.drift_pct == 0.0


# ---------------------------------------------------------------------------
# check_ml_regression tests
# ---------------------------------------------------------------------------


class TestCheckMlRegression:
    """Tests for check_ml_regression circuit breaker."""

    def test_triggers_when_above_threshold(self):
        """ML regression triggers when >50% regression."""
        # Active IC = 0.40, new IC = 0.15 -> regression = (0.40 - 0.15) / 0.40 = 0.625
        result = check_ml_regression(
            new_rank_ic=0.15, active_rank_ic=0.40, threshold_pct=0.50
        )

        assert result.triggered is True
        assert result.drift_pct == pytest.approx(0.625)

    def test_does_not_trigger_below_threshold(self):
        """ML regression does not trigger when regression is below threshold."""
        # Active IC = 0.40, new IC = 0.30 -> regression = (0.40 - 0.30) / 0.40 = 0.25
        result = check_ml_regression(
            new_rank_ic=0.30, active_rank_ic=0.40, threshold_pct=0.50
        )

        assert result.triggered is False
        assert result.drift_pct == pytest.approx(0.25)

    def test_handles_none_new_rank_ic(self):
        """ML regression handles None new_rank_ic gracefully."""
        result = check_ml_regression(
            new_rank_ic=None, active_rank_ic=0.40, threshold_pct=0.50
        )

        assert result.triggered is False
        assert result.drift_pct == 0.0

    def test_handles_none_active_rank_ic(self):
        """ML regression handles None active_rank_ic gracefully."""
        result = check_ml_regression(
            new_rank_ic=0.30, active_rank_ic=None, threshold_pct=0.50
        )

        assert result.triggered is False
        assert result.drift_pct == 0.0

    def test_handles_zero_active_rank_ic(self):
        """ML regression handles zero active_rank_ic gracefully."""
        result = check_ml_regression(
            new_rank_ic=0.30, active_rank_ic=0.0, threshold_pct=0.50
        )

        assert result.triggered is False
        assert result.drift_pct == 0.0

    def test_improvement_does_not_trigger(self):
        """ML regression does not trigger when new model is better."""
        # Active IC = 0.20, new IC = 0.40 -> regression = (0.20 - 0.40) / 0.20 = -1.0
        result = check_ml_regression(
            new_rank_ic=0.40, active_rank_ic=0.20, threshold_pct=0.50
        )

        assert result.triggered is False
        assert result.drift_pct == pytest.approx(-1.0)
