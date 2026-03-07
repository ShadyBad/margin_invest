"""Tests for backtest API wiring -- real PIT provider with synthetic fallback."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import BacktestRun, ShadowPortfolioSnapshot, UniverseSnapshot, User
from margin_api.db.session import get_db
from margin_api.deps import get_current_user_id
from margin_api.services.backtest import (
    get_best_available_result,
    get_default_replay_result,
    get_precomputed_default,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine_and_factory():
    """Create an async engine + session factory with all tables."""

    async def _setup():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        return engine, factory

    engine, factory = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_setup())
    yield engine, factory
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(engine.dispose())


@pytest.fixture
def client(engine_and_factory):
    """Client with an institutional-plan user for gated endpoints."""
    engine, factory = engine_and_factory

    async def _create_user():
        async with factory() as session:
            user = User(
                email="test@test.com",
                name="Test User",
                subscription_plan="institutional",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user.id

    user_id = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_create_user())

    app = create_app()

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: user_id

    return TestClient(app)


# ---------------------------------------------------------------------------
# Unit tests for service functions
# ---------------------------------------------------------------------------


class TestGetPrecomputedDefault:
    """Tests for get_precomputed_default()."""

    def test_returns_none_when_no_backtest_runs(self, engine_and_factory):
        """Should return None when no backtest_runs exist."""
        _, factory = engine_and_factory

        async def _test():
            async with factory() as session:
                result = await get_precomputed_default(session)
                assert result is None

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_test())

    def test_returns_none_when_only_pending_runs(self, engine_and_factory):
        """Should return None when runs exist but none are complete."""
        _, factory = engine_and_factory

        async def _test():
            async with factory() as session:
                # Need a universe snapshot for the FK
                snap = UniverseSnapshot(
                    version="test-v1",
                    config_hash="testhash",
                    ticker_count=100,
                    is_active=True,
                    activated_at=datetime.now(UTC),
                )
                session.add(snap)
                await session.commit()
                await session.refresh(snap)

                run = BacktestRun(
                    name="default",
                    universe_snapshot_id=snap.id,
                    start_date="2006-01-01",
                    end_date="2025-12-31",
                    rebalance_frequency="monthly",
                    config={"test": True},
                    config_hash="abc123",
                    status="pending",
                )
                session.add(run)
                await session.commit()

                result = await get_precomputed_default(session)
                assert result is None

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_test())

    def test_returns_result_when_complete_run_exists(self, engine_and_factory):
        """Should deserialize and return ReplayResult from summary_stats."""
        _, factory = engine_and_factory

        # Build a synthetic result and serialize it
        synthetic = get_default_replay_result()
        summary = synthetic.model_dump(mode="json")

        async def _test():
            async with factory() as session:
                snap = UniverseSnapshot(
                    version="test-v1",
                    config_hash="testhash",
                    ticker_count=100,
                    is_active=True,
                    activated_at=datetime.now(UTC),
                )
                session.add(snap)
                await session.commit()
                await session.refresh(snap)

                run = BacktestRun(
                    name="default",
                    universe_snapshot_id=snap.id,
                    start_date="2006-01-01",
                    end_date="2025-12-31",
                    rebalance_frequency="monthly",
                    config={"test": True},
                    config_hash="abc123",
                    status="complete",
                    summary_stats=summary,
                )
                session.add(run)
                await session.commit()

                result = await get_precomputed_default(session)
                assert result is not None
                assert result.metrics.cagr == synthetic.metrics.cagr
                assert result.metrics.num_months == synthetic.metrics.num_months

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_test())


class TestGetBestAvailableResult:
    """Tests for get_best_available_result()."""

    def test_returns_synthetic_when_no_precomputed(self, engine_and_factory):
        """Should fall back to synthetic when no precomputed exists."""
        _, factory = engine_and_factory

        async def _test():
            async with factory() as session:
                result = await get_best_available_result(session)
                # Should be the synthetic result
                assert result.metrics.cagr == 0.104
                assert result.metrics.num_months == 240

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_test())

    def test_returns_precomputed_when_available(self, engine_and_factory):
        """Should return precomputed result when it exists."""
        _, factory = engine_and_factory

        # Build a modified synthetic with distinct metrics
        from margin_engine.backtesting.models import PerformanceMetrics
        from margin_engine.backtesting.replay_orchestrator import ReplayConfig, ReplayResult

        custom_result = ReplayResult(
            config=ReplayConfig(
                start_date=date(2010, 1, 1),
                end_date=date(2025, 12, 31),
            ),
            metrics=PerformanceMetrics(
                cagr=0.12,
                excess_cagr=0.05,
                sharpe_ratio=0.95,
                sortino_ratio=1.3,
                max_drawdown=0.22,
                win_rate=0.60,
                information_ratio=0.70,
                total_return=4.0,
                benchmark_total_return=2.5,
                num_months=192,
                avg_turnover=0.15,
            ),
            snapshots=[],
            audit_log=[],
            regime_segments={},
            factor_timeline=[],
            duration_seconds=1.5,
        )
        summary = custom_result.model_dump(mode="json")

        async def _test():
            async with factory() as session:
                snap = UniverseSnapshot(
                    version="test-v1",
                    config_hash="testhash",
                    ticker_count=100,
                    is_active=True,
                    activated_at=datetime.now(UTC),
                )
                session.add(snap)
                await session.commit()
                await session.refresh(snap)

                run = BacktestRun(
                    name="default",
                    universe_snapshot_id=snap.id,
                    start_date="2010-01-01",
                    end_date="2025-12-31",
                    rebalance_frequency="monthly",
                    config={"test": True},
                    config_hash="def456",
                    status="complete",
                    summary_stats=summary,
                )
                session.add(run)
                await session.commit()

                result = await get_best_available_result(session)
                # Should return the precomputed result
                assert result.metrics.cagr == 0.12
                assert result.metrics.num_months == 192

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_test())


# ---------------------------------------------------------------------------
# Route integration tests
# ---------------------------------------------------------------------------


class TestTeaserEndpointWiring:
    """Test that teaser endpoints work with DB session."""

    def test_teaser_returns_200(self, client):
        response = client.get("/api/v1/backtest/teaser/AAPL")
        assert response.status_code == 200

    def test_teaser_has_required_fields(self, client):
        response = client.get("/api/v1/backtest/teaser/AAPL")
        data = response.json()
        assert "model_return" in data
        assert "benchmark_return" in data
        assert "max_drawdown" in data
        assert data["ticker"] == "AAPL"

    def test_teaser_uses_synthetic_fallback(self, client):
        """When no precomputed backtest exists, should use synthetic values."""
        response = client.get("/api/v1/backtest/teaser/MSFT")
        data = response.json()
        # Synthetic result has total_return=5.42
        assert data["model_return"] == 5.42


class TestPortfolioTeaserEndpointWiring:
    """Test portfolio teaser endpoint with DB session."""

    def test_portfolio_teaser_returns_200(self, client):
        response = client.get("/api/v1/backtest/portfolio-teaser")
        assert response.status_code == 200

    def test_portfolio_teaser_has_equity_curve(self, client):
        response = client.get("/api/v1/backtest/portfolio-teaser")
        data = response.json()
        assert "equity_curve" in data
        assert len(data["equity_curve"]) > 0


class TestDefaultBacktestEndpointWiring:
    """Test default backtest endpoint with DB session."""

    def test_default_returns_200(self, client):
        response = client.get("/api/v1/backtest/default")
        assert response.status_code == 200

    def test_default_has_full_fields(self, client):
        response = client.get("/api/v1/backtest/default")
        data = response.json()
        assert "metrics" in data
        assert "config" in data
        assert "equity_curve" in data
        assert "walk_forward_note" in data


class TestReplayEndpointWiring:
    """Test replay endpoint with DB session and real backtest fallback."""

    def test_replay_accepts_empty_config(self, client):
        response = client.post("/api/v1/backtest/replay", json={})
        assert response.status_code in (200, 201, 202)

    def test_replay_returns_full_response(self, client):
        response = client.post("/api/v1/backtest/replay", json={})
        data = response.json()
        assert "metrics" in data
        assert "config" in data

    def test_replay_with_custom_config(self, client):
        response = client.post(
            "/api/v1/backtest/replay",
            json={
                "rebalance_frequency": "quarterly",
                "conviction_threshold": 0.20,
            },
        )
        assert response.status_code in (200, 201, 202)
        data = response.json()
        assert data["config"]["rebalance_frequency"] == "quarterly"


class TestShadowPortfolioEndpointWiring:
    """Test shadow portfolio endpoint with DB session."""

    def test_shadow_portfolio_returns_200(self, client):
        response = client.get("/api/v1/backtest/shadow-portfolio")
        assert response.status_code == 200

    def test_shadow_portfolio_empty_initially(self, client):
        response = client.get("/api/v1/backtest/shadow-portfolio")
        data = response.json()
        assert data["snapshots"] == []
        assert data["total_return"] == 0.0
        assert data["num_days"] == 0

    def test_shadow_portfolio_with_snapshots(self, engine_and_factory):
        """When snapshots exist, should return them."""
        engine, factory = engine_and_factory

        async def _create_data():
            async with factory() as session:
                user = User(
                    email="test2@test.com",
                    name="Test User 2",
                    subscription_plan="institutional",
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)

                # Add shadow portfolio snapshots
                snap1 = ShadowPortfolioSnapshot(
                    as_of_date="2026-02-25",
                    portfolio_value=1000000.0,
                    total_return=0.0,
                    num_positions=10,
                    positions_json=[{"ticker": "AAPL", "weight": 0.1}],
                )
                snap2 = ShadowPortfolioSnapshot(
                    as_of_date="2026-02-26",
                    portfolio_value=1010000.0,
                    total_return=0.01,
                    num_positions=10,
                    positions_json=[{"ticker": "AAPL", "weight": 0.1}],
                )
                session.add_all([snap1, snap2])
                await session.commit()
                return user.id

        user_id = (
            asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_create_data())
        )

        app = create_app()

        async def override_get_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = lambda: user_id

        tc = TestClient(app)
        response = tc.get("/api/v1/backtest/shadow-portfolio")
        assert response.status_code == 200
        data = response.json()
        assert len(data["snapshots"]) == 2
        assert data["snapshots"][0]["portfolio_value"] == 1000000.0
        assert data["snapshots"][1]["portfolio_value"] == 1010000.0
        assert data["total_return"] == 0.01
        assert data["num_days"] == 2
        assert data["cannot_be_backdated"] is True


class TestBackwardCompatibility:
    """Ensure existing legacy endpoints still work after wiring changes."""

    def test_old_run_endpoint_still_works(self, client):
        response = client.post("/api/v1/backtest/run", json={})
        assert response.status_code == 201

    def test_old_results_endpoint_still_works(self, client):
        response = client.get("/api/v1/backtest/results")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Real scoring flag tests
# ---------------------------------------------------------------------------


class TestRunRealBacktestUsesRealScoring:
    """Verify that run_real_backtest passes use_real_scoring=True."""

    @pytest.mark.asyncio
    async def test_run_real_backtest_uses_real_scoring(self):
        """run_real_backtest must pass use_real_scoring=True to ReplayOrchestrator."""
        from unittest.mock import AsyncMock, patch

        from margin_engine.backtesting.models import PerformanceMetrics
        from margin_engine.backtesting.replay_orchestrator import ReplayConfig, ReplayResult

        captured_kwargs: dict = {}

        class MockOrchestrator:
            def __init__(self, **kwargs):
                captured_kwargs.update(kwargs)

            async def run_async(self):
                return ReplayResult(
                    config=ReplayConfig(),
                    metrics=PerformanceMetrics(
                        cagr=0,
                        excess_cagr=0,
                        sharpe_ratio=0,
                        sortino_ratio=0,
                        max_drawdown=0,
                        win_rate=0,
                        information_ratio=0,
                        total_return=0,
                        benchmark_total_return=0,
                        num_months=0,
                        avg_turnover=0,
                    ),
                    snapshots=[],
                    audit_log=[],
                    regime_segments={},
                    factor_timeline=[],
                    duration_seconds=0.0,
                )

        mock_session = AsyncMock()

        with patch(
            "margin_engine.backtesting.replay_orchestrator.ReplayOrchestrator",
            MockOrchestrator,
        ):
            with patch("margin_api.services.backtest.DatabasePITProvider"):
                with patch("margin_api.services.backtest.FactorRegistry"):
                    from margin_api.services.backtest import run_real_backtest

                    await run_real_backtest(mock_session, ReplayConfig())

        assert captured_kwargs.get("use_real_scoring") is True

    @pytest.mark.asyncio
    async def test_run_real_backtest_uses_backtest_filter_config(self):
        """run_real_backtest must pass backtest_filter_config to ReplayOrchestrator."""
        from unittest.mock import AsyncMock, patch

        from margin_engine.backtesting.models import PerformanceMetrics
        from margin_engine.backtesting.replay_orchestrator import ReplayConfig, ReplayResult
        from margin_engine.config.filter_config import FilterConfig

        captured_kwargs: dict = {}

        class MockOrchestrator:
            def __init__(self, **kwargs):
                captured_kwargs.update(kwargs)

            async def run_async(self):
                return ReplayResult(
                    config=ReplayConfig(),
                    metrics=PerformanceMetrics(
                        cagr=0,
                        excess_cagr=0,
                        sharpe_ratio=0,
                        sortino_ratio=0,
                        max_drawdown=0,
                        win_rate=0,
                        information_ratio=0,
                        total_return=0,
                        benchmark_total_return=0,
                        num_months=0,
                        avg_turnover=0,
                    ),
                    snapshots=[],
                    audit_log=[],
                    regime_segments={},
                    factor_timeline=[],
                    duration_seconds=0.0,
                )

        mock_session = AsyncMock()

        with patch(
            "margin_engine.backtesting.replay_orchestrator.ReplayOrchestrator",
            MockOrchestrator,
        ):
            with patch("margin_api.services.backtest.DatabasePITProvider"):
                with patch("margin_api.services.backtest.FactorRegistry"):
                    from margin_api.services.backtest import run_real_backtest

                    await run_real_backtest(mock_session, ReplayConfig())

        fc = captured_kwargs.get("filter_config")
        assert fc is not None, "filter_config must be passed to orchestrator"
        assert isinstance(fc, FilterConfig)
        assert fc.liquidity.min_years_of_history == 1
        assert fc.liquidity.market_cap_minimum.default == 100_000_000
