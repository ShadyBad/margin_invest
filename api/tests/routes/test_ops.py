"""Tests for ops API routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import JobRun, User
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_TEST_FERNET_KEY = Fernet.generate_key().decode()
_TEST_ADMIN_KEY = "test-admin-key-secret"


@pytest_asyncio.fixture()
async def setup():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed users
    async with factory() as session:
        now = datetime.now(UTC)

        # Active portfolio subscriber, logged in recently
        u1 = User(
            email="active@test.com",
            name="Active",
            subscription_plan="portfolio",
            subscription_status="active",
            last_login_at=now - timedelta(days=1),
            created_at=now - timedelta(days=30),
        )
        # Active institutional subscriber, no login in 20 days (churn risk)
        u2 = User(
            email="churn@test.com",
            name="Churner",
            subscription_plan="institutional",
            subscription_status="active",
            last_login_at=now - timedelta(days=20),
            created_at=now - timedelta(days=60),
        )
        # Trialing user, trial ends in 2 days
        u3 = User(
            email="trial@test.com",
            name="Trialer",
            subscription_plan="portfolio",
            subscription_status="trialing",
            current_period_end=now + timedelta(days=2),
            created_at=now - timedelta(days=12),
        )
        # Payment failed user
        u4 = User(
            email="failed@test.com",
            name="FailedPay",
            subscription_plan="operator",
            subscription_status="past_due",
            created_at=now - timedelta(days=90),
        )
        # Free user, signed up within 24h
        u5 = User(
            email="new@test.com",
            name="Newbie",
            subscription_plan="analyst",
            created_at=now - timedelta(hours=5),
        )
        # Active subscriber who has never logged in (NULL last_login_at) — churn risk
        u6 = User(
            email="nologin@test.com",
            name="NoLogin",
            subscription_plan="portfolio",
            subscription_status="active",
            last_login_at=None,
            created_at=now - timedelta(days=20),
        )
        session.add_all([u1, u2, u3, u4, u5, u6])

        # Active pipeline job
        j1 = JobRun(
            job_type="ingestion",
            status="running",
            triggered_by="schedule",
        )
        session.add(j1)
        await session.commit()

    app = create_app()

    async def override_db():
        async with factory() as session:
            yield session

    def override_settings():
        from margin_api.config import Settings

        return Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            mfa_encryption_key=_TEST_FERNET_KEY,
            api_key_encryption_key=_TEST_FERNET_KEY,
            stripe_secret_key="sk_test_fake",
            stripe_portfolio_price_id="price_portfolio_123",
            stripe_institutional_price_id="price_institutional_456",
            stripe_webhook_secret="whsec_fake",
            admin_key=_TEST_ADMIN_KEY,
        )

    from margin_api.config import get_settings

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings

    yield app
    await engine.dispose()


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


class TestOpsAuth:
    @pytest.mark.asyncio
    async def test_403_without_admin_key(self, setup):
        app = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/ops/daily-summary")
        assert resp.status_code in (403, 422)

    @pytest.mark.asyncio
    async def test_403_with_wrong_key(self, setup):
        app = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/ops/daily-summary",
                headers={"x-admin-key": "wrong-key"},
            )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Daily summary
# ---------------------------------------------------------------------------


class TestDailySummary:
    @pytest.mark.asyncio
    async def test_daily_summary_shape(self, setup):
        app = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch("margin_api.routes.ops._fetch_sentry_error_count", return_value=42):
                resp = await client.get(
                    "/api/v1/ops/daily-summary",
                    headers={"x-admin-key": _TEST_ADMIN_KEY},
                )
        assert resp.status_code == 200
        data = resp.json()
        assert "mrr_by_plan" in data
        assert "total_users" in data
        assert "active_subscribers" in data
        assert "signups_24h" in data
        assert "active_pipeline_jobs" in data
        assert "sentry_error_count" in data
        assert data["total_users"] == 6
        # u1 (portfolio active) + u2 (institutional active) + u6 (portfolio active) = 3 active subs
        assert data["active_subscribers"] == 3
        # u5 signed up within 24h
        assert data["signups_24h"] == 1
        # 1 running job
        assert data["active_pipeline_jobs"] == 1
        assert data["sentry_error_count"] == 42
        # MRR: portfolio=29 * 2 active (u1 + u6) + institutional=99 * 1 active (u2)
        assert data["mrr_by_plan"]["portfolio"] == 58.0
        assert data["mrr_by_plan"]["institutional"] == 99.0


# ---------------------------------------------------------------------------
# Churn risk users
# ---------------------------------------------------------------------------


class TestChurnRisk:
    @pytest.mark.asyncio
    async def test_churn_risk_users(self, setup):
        app = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/ops/churn-risk-users",
                headers={"x-admin-key": _TEST_ADMIN_KEY},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "total" in data
        # u2 (active, 20d ago) + u3 (trialing, NULL login)
        # + u6 (active, NULL login) = 3 churn-risk
        assert data["total"] == 3
        emails = {u["email"] for u in data["users"]}
        assert "churn@test.com" in emails

    @pytest.mark.asyncio
    async def test_churn_risk_includes_null_last_login(self, setup):
        """Users with NULL last_login_at and active sub appear in churn-risk."""
        app = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/ops/churn-risk-users",
                headers={"x-admin-key": _TEST_ADMIN_KEY},
            )
        assert resp.status_code == 200
        data = resp.json()
        emails = {u["email"] for u in data["users"]}
        assert "nologin@test.com" in emails, (
            "User with NULL last_login_at must be included in churn-risk results"
        )


# ---------------------------------------------------------------------------
# Revenue metrics
# ---------------------------------------------------------------------------


class TestRevenueMetrics:
    @pytest.mark.asyncio
    async def test_revenue_metrics_shape(self, setup):
        app = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/ops/revenue-metrics",
                headers={"x-admin-key": _TEST_ADMIN_KEY},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "mrr_total" in data
        assert "mrr_by_plan" in data
        assert "trials_expiring_3d" in data
        assert "payment_failed_users" in data
        # MRR: portfolio=29 * 2 (u1 + u6) + institutional=99 * 1 (u2) = 157
        assert data["mrr_total"] == 157.0
        # u3 trial expires within 3 days
        assert data["trials_expiring_3d"] == 1
        # u4 is past_due
        assert data["payment_failed_users"] == 1


# ---------------------------------------------------------------------------
# Send email
# ---------------------------------------------------------------------------


class TestSendEmail:
    @pytest.mark.asyncio
    async def test_send_valid_email_type(self, setup):
        app = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/ops/send-email",
                headers={"x-admin-key": _TEST_ADMIN_KEY},
                json={
                    "type": "welcome",
                    "to_email": "user@example.com",
                    "data": {"name": "Test User"},
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sent"] is True

    @pytest.mark.asyncio
    async def test_send_unknown_email_type(self, setup):
        app = setup
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/ops/send-email",
                headers={"x-admin-key": _TEST_ADMIN_KEY},
                json={
                    "type": "nonexistent_type",
                    "to_email": "user@example.com",
                    "data": {},
                },
            )
        assert resp.status_code == 400
