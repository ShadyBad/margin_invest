"""Final route coverage push.

Targets:
  routes/dashboard.py   — get_dashboard, audit_dashboard, get_dashboard_status
  routes/auth.py        — register, verify_credentials, oauth_sync, session_check,
                          setup_totp, confirm_totp, verify_totp, verify_recovery_code,
                          mfa_complete, verify_mfa_token, admin_login, change_password,
                          forgot_password, reset_password, link_provider, unlink_provider,
                          set_password, remove_password, security_status,
                          regenerate_recovery_codes, disable_mfa
  routes/thirteenf.py   — get_holdings, get_holdings_history, list_managers,
                          get_manager_portfolio, get_overlap, get_new_positions,
                          get_clone_portfolio
  routes/scores.py      — list_scores, get_score, get_score_history,
                          get_valuation_audit
  routes/metrics.py     — get_metrics
  routes/admin.py       — trigger_pipeline, trigger_scoring, redis_health,
                          flush_redis_jobs, trigger_ml_training, pit_stats,
                          pit_data_quality, historical_stats, update_job_status,
                          cancel_zombie_jobs, backtest_latest, ingestion_quarantined
  routes/public_scores.py — get_public_score (all three code paths)
  routes/rarity.py      — get_rarity_picks (empty + data), get_rarity
  routes/proposals.py   — list_proposals, accept_proposal, dismiss_proposal
"""

# Model construction notes from schema inspection:
# - V4Score: opportunity_type NOT NULL, ml_override NOT NULL (String)
# - FinancialData: filing_date NOT NULL (String "YYYY-MM-DD")
# - JobRun: triggered_by NOT NULL (String "schedule"|"cli"|"chained")
# - BacktestRun: universe_snapshot_id FK NOT NULL, config NOT NULL, config_hash NOT NULL
# - RegisterRequest.password: min_length=12 (not 8 as assumed)
# - Duplicate register returns 400 (ValueError from auth service, not IntegrityError path)
# - resolve_quarter raises 404 when no data — overlap/new-positions return 404 not 200

from __future__ import annotations

import json
import os
import time
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.config import get_settings
from margin_api.db.base import Base
from margin_api.db.models import (
    Asset,
    BacktestRun,
    FinancialData,
    JobRun,
    LinkedProvider,
    Manager,
    Score,
    User,
    UserProposal,
    UserRole,
    V4Score,
)
from margin_api.db.session import get_db
from margin_api.deps import get_admin_user, get_current_user_id
from margin_api.services.auth import AuthService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


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


def _db_override(session_factory):
    async def override():
        async with session_factory() as s:
            yield s

    return override


def _make_admin_user() -> User:
    user = MagicMock(spec=User)
    user.id = 1
    user.role = UserRole.ADMIN
    return user


_DEFAULT_V4_DETAIL = {
    # ScoreResponse requires factor_name + weight on factor dicts.
    # Do NOT include "ticker" or "name" here — the route fills these via
    # detail.setdefault("ticker", ticker) and detail.setdefault("name", asset_name)
    # using values from the DB query. Including them here would override those.
    "quality": {
        "factor_name": "quality",
        "weight": 0.35,
        "average_percentile": 70.0,
        "sub_scores": [],
    },
    "value": {"factor_name": "value", "weight": 0.30, "average_percentile": 65.0, "sub_scores": []},
    "momentum": {
        "factor_name": "momentum",
        "weight": 0.35,
        "average_percentile": 60.0,
        "sub_scores": [],
    },
    "filters_passed": [],
    "composite_raw_score": 75.0,
    "composite_percentile": 72.0,
    "signal": "stable",
    "data_coverage": 0.95,
}


def _make_v4_score(
    asset_id: int,
    *,
    conviction: str = "high",
    composite_score: float = 75.0,
    published: bool = True,
    detail: dict | None = None,
) -> V4Score:
    """Create a V4Score with all required fields populated."""
    if detail is None:
        d = dict(_DEFAULT_V4_DETAIL)
        d["composite_raw_score"] = composite_score
        d["composite_percentile"] = composite_score
    else:
        d = detail
    return V4Score(
        asset_id=asset_id,
        scored_at=datetime.now(UTC),
        opportunity_type="value_compounder",  # NOT NULL
        conviction=conviction,
        rules_conviction=conviction,
        style="value",
        timing_signal="accumulate",
        max_position_pct=5.0,
        regime="expansion",
        composite_score=composite_score,
        ml_override="none",
        detail=d,
        published=published,
    )


def _make_app_with_db(session_factory, user_id: int | None = None, admin: bool = False):
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_db] = _db_override(session_factory)
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    if admin:
        app.dependency_overrides[get_admin_user] = lambda: _make_admin_user()
    return app


# ===========================================================================
# DASHBOARD tests
# ===========================================================================


class TestDashboardEndpoints:
    @pytest.mark.asyncio
    async def test_get_dashboard_empty_db(self, session_factory):
        """GET /api/v1/dashboard returns 200 with empty picks when DB is empty."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "picks" in data
        assert "watchlist" in data
        assert "total_scored" in data

    @pytest.mark.asyncio
    async def test_get_dashboard_status(self, session_factory):
        """GET /api/v1/dashboard/status returns diagnostic info."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "scores" in data
        assert "assets" in data

    @pytest.mark.asyncio
    async def test_audit_dashboard_empty(self, session_factory):
        """GET /api/v1/dashboard/audit returns entries list."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_dashboard_with_scores(self, db_session, session_factory):
        """GET /api/v1/dashboard returns picks when scores exist with high conviction."""
        asset = Asset(ticker="AAPL", name="Apple Inc", sector="Technology")
        db_session.add(asset)
        await db_session.flush()

        score = Score(
            asset_id=asset.id,
            scored_at=datetime.now(UTC),
            composite_raw_score=80.0,
            composite_percentile=90.0,
            quality_percentile=85.0,
            value_percentile=80.0,
            momentum_percentile=75.0,
            conviction_level="exceptional",
            signal="strong",
            data_coverage=0.95,
        )
        db_session.add(score)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["picks"]) >= 1
        assert data["picks"][0]["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_get_dashboard_watchlist_conviction(self, db_session, session_factory):
        """GET /api/v1/dashboard returns watchlist items for medium conviction."""
        asset = Asset(ticker="MSFT", name="Microsoft", sector="Technology")
        db_session.add(asset)
        await db_session.flush()

        score = Score(
            asset_id=asset.id,
            scored_at=datetime.now(UTC),
            composite_raw_score=67.0,
            composite_percentile=65.0,
            quality_percentile=60.0,
            value_percentile=55.0,
            momentum_percentile=50.0,
            conviction_level="medium",
            signal="stable",
            data_coverage=0.90,
        )
        db_session.add(score)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["watchlist"]) >= 1

    @pytest.mark.asyncio
    async def test_audit_dashboard_with_data(self, db_session, session_factory):
        """GET /api/v1/dashboard/audit populates entries with mismatch detection."""
        asset = Asset(ticker="TSLA", name="Tesla", sector="Automotive")
        db_session.add(asset)
        await db_session.flush()

        score = Score(
            asset_id=asset.id,
            scored_at=datetime.now(UTC),
            composite_raw_score=77.0,
            composite_percentile=85.0,
            quality_percentile=80.0,
            value_percentile=70.0,
            momentum_percentile=65.0,
            conviction_level="high",
            signal="strong",
            data_coverage=0.90,
        )
        db_session.add(score)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        entry = data["entries"][0]
        assert "ticker" in entry
        assert "db_values" in entry
        assert "derived_values" in entry

    @pytest.mark.asyncio
    async def test_dashboard_status_with_data(self, db_session, session_factory):
        """GET /api/v1/dashboard/status shows scores count when data exists."""
        asset = Asset(ticker="GOOG", name="Alphabet", sector="Technology")
        db_session.add(asset)
        await db_session.flush()

        score = Score(
            asset_id=asset.id,
            scored_at=datetime.now(UTC),
            composite_raw_score=72.0,
            composite_percentile=75.0,
            quality_percentile=70.0,
            value_percentile=65.0,
            momentum_percentile=60.0,
            conviction_level="high",
            signal="stable",
            data_coverage=0.92,
        )
        db_session.add(score)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scores"]["total_rows"] >= 1


# ===========================================================================
# AUTH tests
# ===========================================================================


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_register_success(self, session_factory):
        """POST /api/v1/auth/register creates a new user."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "Str0ng!Pass9923",  # min_length=12
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "testuser"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_weak_password_returns_422(self, session_factory):
        """POST /api/v1/auth/register returns 422 for too-short password (min_length=12)."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": "user2",
                    "email": "user2@example.com",
                    "password": "weak",
                },
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_duplicate_returns_400_or_409(self, session_factory):
        """POST /api/v1/auth/register returns 4xx for duplicate user."""
        app = _make_app_with_db(session_factory)
        payload = {
            "username": "dupuser",
            "email": "dup@example.com",
            "password": "Str0ng!Pass9923",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post("/api/v1/auth/register", json=payload)
            assert first.status_code == 201
            resp = await client.post("/api/v1/auth/register", json=payload)
        # Auth service raises ValueError for duplicate (-> 400) or IntegrityError (-> 409)
        assert resp.status_code in (400, 409)

    @pytest.mark.asyncio
    async def test_verify_credentials_invalid_returns_401(self, session_factory):
        """POST /api/v1/auth/verify-credentials returns 401 for bad creds."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-credentials",
                json={"username": "nobody", "password": "badpass"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_credentials_success(self, db_session, session_factory):
        """POST /api/v1/auth/verify-credentials succeeds with correct creds.

        Note: verify_credentials looks up users by User.email (not username),
        so the 'username' field in the request body must be the user's email address.
        """
        # Seed user via AuthService so password_hash is set correctly
        auth_svc = AuthService()
        await auth_svc.register_user(db_session, "creduser", "cred@example.com", "Str0ng!Pass9923")
        # register_user already commits, but we flush to ensure visibility
        await db_session.flush()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # The endpoint uses email as the username lookup (User.email == username)
            resp = await client.post(
                "/api/v1/auth/verify-credentials",
                json={"username": "cred@example.com", "password": "Str0ng!Pass9923"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "challenge_token" in data
        assert data["mfa_status"] in ("enabled", "disabled")

    @pytest.mark.asyncio
    async def test_oauth_sync_creates_new_user(self, session_factory):
        """POST /api/v1/auth/oauth-sync creates user when not exists."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/oauth-sync",
                json={
                    "email": "oauth@example.com",
                    "name": "OAuth User",
                    "provider": "google",
                    "oauth_id": "google-123",
                    "avatar_url": None,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    @pytest.mark.asyncio
    async def test_oauth_sync_updates_existing_user(self, db_session, session_factory):
        """POST /api/v1/auth/oauth-sync updates existing user."""
        user = User(email="existing@example.com", name="Old Name")
        db_session.add(user)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/oauth-sync",
                json={
                    "email": "existing@example.com",
                    "name": "New Name",
                    "provider": "github",
                    "oauth_id": "gh-456",
                    "avatar_url": None,
                },
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_session_check_unknown_user(self, session_factory):
        """GET /api/v1/auth/session-check/{user_id} returns valid for unknown user."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/auth/session-check/99999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_valid"] is True
        assert data["token_invalidated"] is False

    @pytest.mark.asyncio
    async def test_session_check_with_iat(self, db_session, session_factory):
        """GET /api/v1/auth/session-check detects invalidated token when iat < password change."""
        auth_svc = AuthService()
        user = await auth_svc.register_user(
            db_session, "passuser", "passuser@example.com", "Str0ng!Pass99"
        )
        # Set password_changed_at to now (so iat=0 would be < changed_at)
        user.password_changed_at = datetime.now(UTC)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        old_iat = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/auth/session-check/{user.id}",
                params={"iat": old_iat},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["token_invalidated"] is True

    @pytest.mark.asyncio
    async def test_forgot_password_always_returns_200(self, session_factory):
        """POST /api/v1/auth/forgot-password always returns 200."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "noone@example.com"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_forgot_password_for_real_user(self, db_session, session_factory):
        """POST /api/v1/auth/forgot-password triggers email for real user."""
        auth_svc = AuthService()
        await auth_svc.register_user(db_session, "resetuser", "reset@example.com", "Str0ng!Pass99")
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        with patch("margin_api.services.email.EmailService.send_password_reset"):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/forgot-password",
                    json={"email": "reset@example.com"},
                )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, db_session, session_factory):
        """POST /api/v1/auth/reset-password returns 400 for invalid token."""
        auth_svc = AuthService()
        user = await auth_svc.register_user(
            db_session, "resetuser2", "reset2@example.com", "Str0ng!Pass99"
        )
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/reset-password",
                json={
                    "user_id": user.id,
                    "token": "invalidtoken",
                    "new_password": "NewStr0ng!Pass",
                },
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_setup_totp_invalid_challenge(self, db_session, session_factory):
        """POST /api/v1/auth/mfa/setup-totp returns 403 for invalid challenge token."""
        from cryptography.fernet import Fernet

        auth_svc = AuthService()
        user = await auth_svc.register_user(
            db_session, "totpuser", "totp@example.com", "Str0ng!Pass9923"
        )
        await db_session.commit()

        # Patch settings to have a valid Fernet key
        fernet_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"MARGIN_MFA_ENCRYPTION_KEY": fernet_key}):
            get_settings.cache_clear()
            app = _make_app_with_db(session_factory)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/mfa/setup-totp",
                    json={"user_id": user.id, "challenge_token": "badtoken"},
                )
        get_settings.cache_clear()
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_setup_totp_user_not_found(self, session_factory):
        """POST /api/v1/auth/mfa/setup-totp returns 404 when user not found."""
        from cryptography.fernet import Fernet

        fernet_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"MARGIN_MFA_ENCRYPTION_KEY": fernet_key}):
            get_settings.cache_clear()
            app = _make_app_with_db(session_factory)
            # Mock auth service to return valid challenge but user doesn't exist
            with patch(
                "margin_api.services.auth.AuthService.verify_challenge_token",
                return_value=True,
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(
                        "/api/v1/auth/mfa/setup-totp",
                        json={"user_id": 99999, "challenge_token": "any"},
                    )
        get_settings.cache_clear()
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_verify_totp_invalid_challenge(self, db_session, session_factory):
        """POST /api/v1/auth/mfa/verify-totp returns 403 for invalid challenge."""
        from cryptography.fernet import Fernet

        auth_svc = AuthService()
        user = await auth_svc.register_user(
            db_session, "vtotp", "vtotp@example.com", "Str0ng!Pass9923"
        )
        await db_session.commit()

        fernet_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"MARGIN_MFA_ENCRYPTION_KEY": fernet_key}):
            get_settings.cache_clear()
            app = _make_app_with_db(session_factory)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/mfa/verify-totp",
                    json={"user_id": user.id, "challenge_token": "bad", "code": "123456"},
                )
        get_settings.cache_clear()
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_verify_recovery_code_invalid_challenge(self, db_session, session_factory):
        """POST /api/v1/auth/mfa/verify-recovery returns 403 for invalid challenge."""
        auth_svc = AuthService()
        user = await auth_svc.register_user(
            db_session, "recov", "recov@example.com", "Str0ng!Pass99"
        )
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/mfa/verify-recovery",
                json={"user_id": user.id, "challenge_token": "bad", "code": "ABCD-1234"},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_mfa_complete_missing_cookie_returns_401(self, session_factory):
        """POST /api/v1/auth/mfa/complete returns 401 when no cookie present."""
        from cryptography.fernet import Fernet

        fernet_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"MARGIN_MFA_ENCRYPTION_KEY": fernet_key}):
            get_settings.cache_clear()
            app = _make_app_with_db(session_factory)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/mfa/complete",
                    json={"totp_code": "123456"},
                )
        get_settings.cache_clear()
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_mfa_complete_invalid_cookie(self, session_factory):
        """POST /api/v1/auth/mfa/complete returns 401 with malformed cookie."""
        from cryptography.fernet import Fernet

        fernet_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"MARGIN_MFA_ENCRYPTION_KEY": fernet_key}):
            get_settings.cache_clear()
            app = _make_app_with_db(session_factory)
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                cookies={"__mfa_challenge": "notjson"},
            ) as client:
                resp = await client.post(
                    "/api/v1/auth/mfa/complete",
                    json={"totp_code": "123456"},
                )
        get_settings.cache_clear()
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_mfa_complete_no_code_provided(self, session_factory):
        """POST /api/v1/auth/mfa/complete returns 400 when no code field given."""
        from cryptography.fernet import Fernet

        fernet_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"MARGIN_MFA_ENCRYPTION_KEY": fernet_key}):
            get_settings.cache_clear()
            app = _make_app_with_db(session_factory)
            cookie_val = json.dumps({"userId": 1, "challengeToken": "tok"})
            with patch(
                "margin_api.services.auth.AuthService.verify_challenge_token",
                return_value=True,
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                    cookies={"__mfa_challenge": cookie_val},
                ) as client:
                    resp = await client.post(
                        "/api/v1/auth/mfa/complete",
                        json={},
                    )
        get_settings.cache_clear()
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_mfa_token_invalid_returns_401(self, session_factory):
        """POST /api/v1/auth/verify-mfa-token returns 401 for invalid token."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": "invalidsignature"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_mfa_token_wrong_purpose(self, session_factory):
        """POST /api/v1/auth/verify-mfa-token returns 401 when purpose != mfa_complete."""
        get_settings.cache_clear()
        settings = get_settings()
        token = pyjwt.encode(
            {
                "sub": "1",
                "purpose": "wrong_purpose",
                "iat": int(time.time()),
                "exp": int(time.time()) + 60,
            },
            settings.jwt_secret,
            algorithm="HS256",
        )

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/verify-mfa-token",
                json={"token": token},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_login_invalid_creds(self, session_factory):
        """POST /api/v1/auth/admin-login returns 401 for unknown user."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "nobody@example.com", "pw": "badpass"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_login_non_admin_returns_403(self, db_session, session_factory):
        """POST /api/v1/auth/admin-login returns 403 for non-admin user."""
        auth_svc = AuthService()
        await auth_svc.register_user(
            db_session, "regularuser", "regular@example.com", "Str0ng!Pass9923"
        )
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "regular@example.com", "pw": "Str0ng!Pass9923"},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_login_success(self, db_session, session_factory):
        """POST /api/v1/auth/admin-login issues MFA challenge for admin user."""
        auth_svc = AuthService()
        user = await auth_svc.register_user(
            db_session, "adminuser", "admin@example.com", "Str0ng!Pass9923"
        )
        user.role = UserRole.ADMIN
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/admin-login",
                json={"email": "admin@example.com", "pw": "Str0ng!Pass9923"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mfa_required"] is True
        assert "challenge_str" in data

    @pytest.mark.asyncio
    async def test_link_provider_success(self, db_session, session_factory):
        """POST /api/v1/auth/link-provider links a provider to current user."""
        user = User(email="link@example.com", name="Link User")
        db_session.add(user)
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/link-provider",
                json={
                    "provider": "github",
                    "oauth_id": "gh-777",
                    "provider_email": "link@github.com",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["linked"] is True

    @pytest.mark.asyncio
    async def test_link_provider_duplicate_returns_409(self, db_session, session_factory):
        """POST /api/v1/auth/link-provider returns 409 for duplicate link."""
        user = User(email="link2@example.com", name="Link2 User")
        db_session.add(user)
        await db_session.flush()
        lp = LinkedProvider(
            user_id=user.id,
            provider="github",
            oauth_id="gh-999",
            provider_email="link2@github.com",
        )
        db_session.add(lp)
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/link-provider",
                json={
                    "provider": "github",
                    "oauth_id": "gh-999",
                    "provider_email": "link2@github.com",
                },
            )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_unlink_provider_not_found(self, db_session, session_factory):
        """DELETE /api/v1/auth/unlink-provider/{provider} returns 404 for unlinked."""
        user = User(email="unlink@example.com", name="Unlink User")
        db_session.add(user)
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/v1/auth/unlink-provider/github")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_set_password_success(self, db_session, session_factory):
        """POST /api/v1/auth/set-password sets password for OAuth user."""
        user = User(email="setpass@example.com", name="SetPass User")
        db_session.add(user)
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/set-password",
                json={"new_password": "Str0ng!Pass9923"},  # min 12 chars
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["password_set"] is True

    @pytest.mark.asyncio
    async def test_set_password_already_set_returns_409(self, db_session, session_factory):
        """POST /api/v1/auth/set-password returns 409 when password already set."""
        auth_svc = AuthService()
        user = await auth_svc.register_user(
            db_session, "haspass", "haspass@example.com", "Str0ng!Pass9923"
        )
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/set-password",
                json={"new_password": "NewStr0ng!Pass99"},
            )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_security_status_no_user_returns_404(self, session_factory):
        """GET /api/v1/auth/security-status returns 404 for nonexistent user."""
        app = _make_app_with_db(session_factory, user_id=99999)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/auth/security-status")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_security_status_success(self, db_session, session_factory):
        """GET /api/v1/auth/security-status returns security info for user."""
        user = User(email="secstatus@example.com", name="SecStatus User")
        db_session.add(user)
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/auth/security-status")
        assert resp.status_code == 200
        data = resp.json()
        assert "has_password" in data
        assert "mfa_enabled" in data
        assert "linked_providers" in data


# ===========================================================================
# 13F tests
# ===========================================================================


class TestThirteenfEndpoints:
    @pytest.mark.asyncio
    async def test_get_holdings_empty(self, session_factory):
        """GET /api/v1/13f/holdings/{ticker} returns empty holders when no data."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/holdings/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["curated_holders"] == []
        assert data["other_holders"] == []
        assert data["summary"]["total_holders"] == 0

    @pytest.mark.asyncio
    async def test_get_holdings_history_empty(self, session_factory):
        """GET /api/v1/13f/holdings/{ticker}/history returns empty quarters."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/holdings/MSFT/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "MSFT"
        assert data["quarters"] == []

    @pytest.mark.asyncio
    async def test_list_managers_empty(self, session_factory):
        """GET /api/v1/13f/managers returns empty list when no managers."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/managers")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_managers_with_data(self, db_session, session_factory):
        """GET /api/v1/13f/managers returns managers when data exists."""
        mgr = Manager(
            cik="0001234567",
            name="Test Fund LP",
            short_name="Test Fund",
            tier="curated",
        )
        db_session.add(mgr)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/managers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Fund"

    @pytest.mark.asyncio
    async def test_list_managers_filter_by_tier(self, db_session, session_factory):
        """GET /api/v1/13f/managers?tier=curated filters by tier."""
        mgr1 = Manager(cik="0001", name="Fund A", short_name="FA", tier="curated")
        mgr2 = Manager(cik="0002", name="Fund B", short_name="FB", tier="top_aum")
        db_session.add_all([mgr1, mgr2])
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/managers?tier=curated")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "FA"

    @pytest.mark.asyncio
    async def test_get_manager_portfolio_not_found(self, db_session, session_factory):
        """GET /api/v1/13f/managers/{id}/portfolio returns 404 when manager missing."""
        user = User(email="inst@test.com", name="Inst User", subscription_plan="institutional")
        db_session.add(user)
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/managers/99999/portfolio")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_manager_portfolio_no_filing(self, db_session, session_factory):
        """GET /api/v1/13f/managers/{id}/portfolio returns 404 when no filings."""
        user = User(email="inst2@test.com", name="Inst User 2", subscription_plan="institutional")
        mgr = Manager(cik="0009999", name="Empty Fund", short_name="EF", tier="curated")
        db_session.add_all([user, mgr])
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/13f/managers/{mgr.id}/portfolio")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_overlap_empty_db_returns_404(self, db_session, session_factory):
        """GET /api/v1/13f/analytics/overlap returns 404 when no quarterly data."""
        user = User(email="inst3@test.com", name="Inst User 3", subscription_plan="institutional")
        db_session.add(user)
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/analytics/overlap")
        # resolve_quarter raises 404 when no holdings data exists
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_new_positions_empty_db_returns_404(self, db_session, session_factory):
        """GET /api/v1/13f/analytics/new-positions returns 404 when no quarterly data."""
        user = User(email="inst4@test.com", name="Inst User 4", subscription_plan="institutional")
        db_session.add(user)
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/analytics/new-positions")
        # resolve_quarter raises 404 when no holdings data exists
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_clone_portfolio_not_found(self, db_session, session_factory):
        """GET /api/v1/13f/analytics/clone/{id} returns 404 when manager missing."""
        user = User(email="inst5@test.com", name="Inst User 5", subscription_plan="institutional")
        db_session.add(user)
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/analytics/clone/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_clone_portfolio_no_filing(self, db_session, session_factory):
        """GET /api/v1/13f/analytics/clone/{id} returns 404 when no filing."""
        user = User(email="inst6@test.com", name="Inst User 6", subscription_plan="institutional")
        mgr = Manager(cik="0000001", name="Clone Fund", short_name="CF", tier="curated")
        db_session.add_all([user, mgr])
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/13f/analytics/clone/{mgr.id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_holdings_with_asset_cusip_fallback(self, db_session, session_factory):
        """GET /api/v1/13f/holdings uses asset CUSIP fallback when no SecurityMaster match."""
        asset = Asset(ticker="CUSIPTEST", name="Cusip Test Co", sector="Technology")
        db_session.add(asset)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/13f/holdings/CUSIPTEST")
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "CUSIPTEST"


# ===========================================================================
# SCORES tests
# ===========================================================================


class TestScoresEndpoints:
    @pytest.mark.asyncio
    async def test_list_scores_empty(self, session_factory):
        """GET /api/v1/scores returns empty list when no V4 scores."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scores"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_scores_with_data(self, db_session, session_factory):
        """GET /api/v1/scores returns V4 scores."""
        asset = Asset(ticker="AMZN", name="Amazon", sector="Consumer Discretionary")
        db_session.add(asset)
        await db_session.flush()

        v4 = _make_v4_score(asset.id, conviction="high", composite_score=79.0)
        db_session.add(v4)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_scores_filter_conviction(self, db_session, session_factory):
        """GET /api/v1/scores?conviction=high filters by conviction."""
        asset = Asset(ticker="META", name="Meta", sector="Technology")
        db_session.add(asset)
        await db_session.flush()

        v4 = _make_v4_score(asset.id, conviction="high", composite_score=78.0)
        db_session.add(v4)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores?conviction=high")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_score_not_found(self, session_factory):
        """GET /api/v1/scores/{ticker} returns 404 for unknown ticker."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/ZZZZ")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_score_returns_v4(self, db_session, session_factory):
        """GET /api/v1/scores/{ticker} returns V4 score when available."""
        asset = Asset(ticker="NVDA", name="Nvidia", sector="Technology")
        db_session.add(asset)
        await db_session.flush()

        v4 = _make_v4_score(asset.id, conviction="exceptional", composite_score=85.0)
        db_session.add(v4)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/NVDA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "NVDA"

    @pytest.mark.asyncio
    async def test_get_score_unpublished_fallback(self, db_session, session_factory):
        """GET /api/v1/scores/{ticker} falls back to unpublished V4 score."""
        asset = Asset(ticker="STAGED", name="Staged Corp", sector="Technology")
        db_session.add(asset)
        await db_session.flush()

        v4 = _make_v4_score(asset.id, conviction="high", composite_score=75.0, published=False)
        db_session.add(v4)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/STAGED")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_score_history_not_found(self, session_factory):
        """GET /api/v1/scores/{ticker}/history returns 404 for unknown ticker."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/ZZZZ/history")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_score_history_returns_points(self, db_session, session_factory):
        """GET /api/v1/scores/{ticker}/history returns history points."""
        asset = Asset(ticker="HIST", name="History Co", sector="Technology")
        db_session.add(asset)
        await db_session.flush()

        for i in range(3):
            score = Score(
                asset_id=asset.id,
                scored_at=datetime.now(UTC) - timedelta(days=i),
                composite_raw_score=70.0 + i,
                composite_percentile=75.0 + i,
                quality_percentile=70.0,
                value_percentile=65.0,
                momentum_percentile=60.0,
                conviction_level="high",
                signal="stable",
                data_coverage=0.90,
            )
            db_session.add(score)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/HIST/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "HIST"
        assert len(data["points"]) == 3

    @pytest.mark.asyncio
    async def test_get_valuation_audit_not_found(self, session_factory):
        """GET /api/v1/scores/{ticker}/valuation-audit returns 404 for unknown ticker."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/ZZZZ/valuation-audit")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_valuation_audit_no_audit_data(self, db_session, session_factory):
        """GET /api/v1/scores/{ticker}/valuation-audit returns 404 when no audit data."""
        asset = Asset(ticker="NOAUDIT", name="No Audit Co", sector="Technology")
        db_session.add(asset)
        await db_session.flush()

        score = Score(
            asset_id=asset.id,
            scored_at=datetime.now(UTC),
            composite_raw_score=70.0,
            composite_percentile=72.0,
            quality_percentile=65.0,
            value_percentile=60.0,
            momentum_percentile=55.0,
            conviction_level="high",
            signal="stable",
            data_coverage=0.85,
            score_detail={"quality": {}, "value": {}, "momentum": {}},
        )
        db_session.add(score)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/NOAUDIT/valuation-audit")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_score_with_price_history_include(self, db_session, session_factory):
        """GET /api/v1/scores/{ticker}?include=price_history returns price_history list."""
        asset = Asset(ticker="PRICEHIST", name="PriceHist Co", sector="Technology")
        db_session.add(asset)
        await db_session.flush()

        v4 = _make_v4_score(asset.id, conviction="high", composite_score=75.0)
        db_session.add(v4)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/PRICEHIST?include=price_history")
        assert resp.status_code == 200
        data = resp.json()
        assert "price_history" in data


# ===========================================================================
# METRICS tests
# ===========================================================================


class TestMetricsEndpoints:
    @pytest.mark.asyncio
    async def test_get_metrics_not_found(self, session_factory):
        """GET /api/v1/scores/{ticker}/metrics returns 404 for unknown ticker."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/ZZZZ/metrics")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_metrics_no_price_data(self, db_session, session_factory):
        """GET /api/v1/scores/{ticker}/metrics returns unavailable metrics without price data."""
        asset = Asset(ticker="METRICS", name="Metrics Co", sector="Technology")
        db_session.add(asset)
        await db_session.flush()

        score = Score(
            asset_id=asset.id,
            scored_at=datetime.now(UTC),
            composite_raw_score=70.0,
            composite_percentile=72.0,
            quality_percentile=65.0,
            value_percentile=60.0,
            momentum_percentile=55.0,
            conviction_level="high",
            signal="stable",
            data_coverage=0.85,
        )
        db_session.add(score)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/METRICS/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "sharpe_ratio" in data
        assert data["sharpe_ratio"]["value"] is None or "unavailable_reason" in data["sharpe_ratio"]

    @pytest.mark.asyncio
    async def test_get_metrics_with_price_data(self, db_session, session_factory):
        """GET /api/v1/scores/{ticker}/metrics computes metrics from price data."""
        asset = Asset(ticker="RICHMETRIC", name="Rich Metric Co", sector="Technology")
        db_session.add(asset)
        await db_session.flush()

        score = Score(
            asset_id=asset.id,
            scored_at=datetime.now(UTC),
            composite_raw_score=75.0,
            composite_percentile=78.0,
            quality_percentile=72.0,
            value_percentile=68.0,
            momentum_percentile=65.0,
            conviction_level="high",
            signal="stable",
            data_coverage=0.92,
            actual_price=150.0,
            margin_invest_value=180.0,
        )
        db_session.add(score)
        await db_session.flush()

        # Seed financial data with price history (252+ bars for 1Y Sharpe)
        import math

        bars = []
        for i in range(260):
            price = 100.0 + 50.0 * math.sin(i * 0.05)
            bars.append(
                {
                    "date": (date(2024, 1, 1) + timedelta(days=i)).isoformat(),
                    "open": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "close": price,
                    "volume": 1000000,
                }
            )

        fin = FinancialData(
            asset_id=asset.id,
            period_end=date.today(),
            filing_date="2024-12-31",  # NOT NULL
            price_history={"bars": bars},
            income_statement=[
                {
                    "totalRevenue": 100_000_000,
                    "netIncome": 20_000_000,
                    "period": "2024-12-31",
                }
            ],
        )
        db_session.add(fin)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/RICHMETRIC/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "sharpe_ratio" in data
        assert "max_drawdown" in data
        assert "volatility" in data


# ===========================================================================
# ADMIN tests
# ===========================================================================


class TestAdminEndpoints:
    @pytest.mark.asyncio
    async def test_trigger_pipeline_redis_failure(self, session_factory):
        """POST /api/v1/admin/pipeline/trigger returns 503 when Redis unreachable."""
        app = _make_app_with_db(session_factory, admin=True)
        with patch("margin_api.routes.admin.create_pool", side_effect=Exception("no redis")):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/v1/admin/pipeline/trigger")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_trigger_scoring_redis_failure(self, session_factory):
        """POST /api/v1/admin/scoring/trigger returns 503 when Redis unreachable."""
        app = _make_app_with_db(session_factory, admin=True)
        with patch("margin_api.routes.admin.create_pool", side_effect=Exception("no redis")):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/v1/admin/scoring/trigger")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_trigger_ml_training_redis_failure(self, session_factory):
        """POST /api/v1/admin/ml/train returns 503 when Redis unreachable."""
        app = _make_app_with_db(session_factory, admin=True)
        with patch("margin_api.routes.admin.create_pool", side_effect=Exception("no redis")):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post("/api/v1/admin/ml/train")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_pit_stats_empty(self, session_factory):
        """GET /api/v1/admin/pit/stats returns zero counts for empty DB."""
        app = _make_app_with_db(session_factory, admin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/pit/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pit_financial_snapshots"] == 0
        assert data["pit_daily_prices"] == 0
        assert data["pit_universe_memberships"] == 0

    @pytest.mark.asyncio
    async def test_pit_data_quality_empty(self, session_factory):
        """GET /api/v1/admin/pit/data-quality returns zero counts for empty DB."""
        app = _make_app_with_db(session_factory, admin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/pit/data-quality")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_snapshots"] == 0

    @pytest.mark.asyncio
    async def test_historical_stats_empty(self, session_factory):
        """GET /api/v1/admin/historical/stats returns zero count for empty DB."""
        app = _make_app_with_db(session_factory, admin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/historical/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["historical_scores"] == 0

    @pytest.mark.asyncio
    async def test_update_job_status_not_found(self, session_factory):
        """PATCH /api/v1/admin/jobs/{id}/status returns 404 for unknown job."""
        app = _make_app_with_db(session_factory, admin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(
                "/api/v1/admin/jobs/99999/status",
                json={"status": "cancelled"},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_job_status_invalid_status(self, session_factory):
        """PATCH /api/v1/admin/jobs/{id}/status returns 400 for invalid status."""
        app = _make_app_with_db(session_factory, admin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(
                "/api/v1/admin/jobs/1/status",
                json={"status": "bogus"},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_job_status_success(self, db_session, session_factory):
        """PATCH /api/v1/admin/jobs/{id}/status updates job status."""
        job = JobRun(
            job_type="train_ml_models",
            status="running",
            triggered_by="cli",  # NOT NULL
            started_at=datetime.now(UTC),
        )
        db_session.add(job)
        await db_session.commit()

        app = _make_app_with_db(session_factory, admin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(
                f"/api/v1/admin/jobs/{job.id}/status",
                json={"status": "cancelled"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_zombie_jobs(self, db_session, session_factory):
        """POST /api/v1/admin/jobs/cancel-zombies cancels old running jobs."""
        old_job = JobRun(
            job_type="train_ml_models",
            status="running",
            triggered_by="schedule",  # NOT NULL
            started_at=datetime.now(UTC) - timedelta(hours=3),
        )
        db_session.add(old_job)
        await db_session.commit()

        app = _make_app_with_db(session_factory, admin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/admin/jobs/cancel-zombies",
                json={"job_type": "train_ml_models"},
                headers={"content-type": "application/json"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cancelled"] >= 1

    @pytest.mark.asyncio
    async def test_backtest_latest_not_found(self, session_factory):
        """GET /api/v1/admin/backtest/latest returns 404 when no backtests."""
        app = _make_app_with_db(session_factory, admin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/backtest/latest")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_backtest_latest_returns_run(self, db_session, session_factory):
        """GET /api/v1/admin/backtest/latest returns the latest backtest run."""
        from margin_api.db.models import UniverseSnapshot

        # BacktestRun.universe_snapshot_id FK is NOT NULL
        # UniverseSnapshot.activated_at is also NOT NULL (Mapped[datetime] with no default)
        snap = UniverseSnapshot(
            version="v1",
            config_hash="testhash123",  # NOT NULL
            tickers=["AAPL", "MSFT"],
            ticker_count=2,
            is_active=False,
            activated_at=datetime.now(UTC),  # NOT NULL, no server default
        )
        db_session.add(snap)
        await db_session.flush()

        run = BacktestRun(
            name="Test Backtest",
            universe_snapshot_id=snap.id,
            start_date="2020-01-01",
            end_date="2024-12-31",
            rebalance_frequency="quarterly",
            config={"universe": "SP500"},
            config_hash="abc123",
            status="complete",
            total_return=0.15,
            annualized_return=0.12,
            sharpe_ratio=1.2,
            max_drawdown=-0.18,
        )
        db_session.add(run)
        await db_session.commit()

        app = _make_app_with_db(session_factory, admin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/backtest/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Backtest"
        assert data["status"] == "complete"

    @pytest.mark.asyncio
    async def test_ingestion_quarantined_empty(self, session_factory):
        """GET /api/v1/admin/ingestion/quarantined returns empty list when none."""
        app = _make_app_with_db(session_factory, admin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/ingestion/quarantined")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_ingestion_quarantined_with_data(self, db_session, session_factory):
        """GET /api/v1/admin/ingestion/quarantined lists quarantined assets."""
        asset = Asset(
            ticker="QUAR",
            name="Quarantine Corp",
            sector="Technology",
            ingestion_status="quarantined",
            consecutive_failures=5,
            last_failure_reason="timeout",
        )
        db_session.add(asset)
        await db_session.commit()

        app = _make_app_with_db(session_factory, admin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/ingestion/quarantined")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["ticker"] == "QUAR"

    @pytest.mark.asyncio
    async def test_redis_health_unreachable(self, session_factory):
        """GET /api/v1/admin/redis/health returns error status when Redis is down."""
        app = _make_app_with_db(session_factory, admin=True)
        with patch(
            "redis.asyncio.from_url",
            return_value=AsyncMock(ping=AsyncMock(side_effect=Exception("refused"))),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/admin/redis/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_ml_training_dry_run(self, session_factory):
        """GET /api/v1/admin/ml/training-dry-run returns dry run report."""
        app = _make_app_with_db(session_factory, admin=True)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/ml/training-dry-run")
        assert resp.status_code == 200
        data = resp.json()
        assert "v4score_rows" in data or "error" in data


# ===========================================================================
# PUBLIC SCORES tests (complementary to existing tests)
# ===========================================================================


class TestPublicScoresAdditional:
    @pytest.mark.asyncio
    async def test_score_with_signal_history_include(self, db_session, session_factory):
        """GET /api/v1/scores/{ticker}?include=signal_history includes signal history."""
        asset = Asset(ticker="SIGH", name="Signal History Co", sector="Technology")
        db_session.add(asset)
        await db_session.flush()

        v4 = _make_v4_score(asset.id, conviction="high", composite_score=75.0)
        db_session.add(v4)
        await db_session.commit()

        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/scores/SIGH?include=signal_history")
        assert resp.status_code == 200
        data = resp.json()
        assert "signal_history" in data


# ===========================================================================
# RARITY tests (complementary to existing tests)
# ===========================================================================


class TestRarityAdditional:
    @pytest.mark.asyncio
    async def test_get_rarity_picks_empty_async(self, session_factory):
        """GET /api/v1/rarity/picks returns 200 with empty list."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/rarity/picks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["picks"] == []

    @pytest.mark.asyncio
    async def test_get_rarity_404_async(self, session_factory):
        """GET /api/v1/rarity/{ticker} returns 404 for unknown ticker."""
        app = _make_app_with_db(session_factory)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/rarity/ZZZMISSING")
        assert resp.status_code == 404


# ===========================================================================
# PROPOSALS tests (complementary)
# ===========================================================================


class TestProposalsAdditional:
    @pytest.mark.asyncio
    async def test_list_proposals_async(self, db_session, session_factory):
        """GET /api/v1/proposals returns proposals for current user."""
        user = User(email="propuser@example.com", name="Prop User")
        db_session.add(user)
        await db_session.flush()

        proposal = UserProposal(
            user_id=user.id,
            proposal_type="rebalance",
            status="pending",
            payload={"ticker": "AAPL"},
            created_at=datetime.now(UTC),
        )
        db_session.add(proposal)
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/proposals")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["proposals"]) == 1

    @pytest.mark.asyncio
    async def test_accept_proposal_async(self, db_session, session_factory):
        """POST /api/v1/proposals/{id}/accept transitions proposal to accepted."""
        user = User(email="propuser2@example.com", name="Prop User 2")
        db_session.add(user)
        await db_session.flush()

        proposal = UserProposal(
            user_id=user.id,
            proposal_type="allocation",
            status="pending",
            payload={"amount": 1000},
            created_at=datetime.now(UTC),
        )
        db_session.add(proposal)
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/proposals/{proposal.id}/accept")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_dismiss_proposal_async(self, db_session, session_factory):
        """POST /api/v1/proposals/{id}/dismiss transitions proposal to dismissed."""
        user = User(email="propuser3@example.com", name="Prop User 3")
        db_session.add(user)
        await db_session.flush()

        proposal = UserProposal(
            user_id=user.id,
            proposal_type="rebalance",
            status="pending",
            payload={},
            created_at=datetime.now(UTC),
        )
        db_session.add(proposal)
        await db_session.commit()

        app = _make_app_with_db(session_factory, user_id=user.id)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/proposals/{proposal.id}/dismiss")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "dismissed"
