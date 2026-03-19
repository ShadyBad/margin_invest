"""Tests for governance config registry and validation service."""

from __future__ import annotations

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import GovernanceConfig
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Fixtures
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
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


# ---------------------------------------------------------------------------
# validate_config_value tests
# ---------------------------------------------------------------------------


class TestValidateConfigValue:
    def test_valid_value_returns_no_errors(self):
        from margin_api.services.governance_config import validate_config_value

        errors = validate_config_value("circuit_breaker.score_drift", {"threshold": 25.0})
        assert errors == []

    def test_valid_value_integer_accepted_for_float_field(self):
        from margin_api.services.governance_config import validate_config_value

        errors = validate_config_value("circuit_breaker.score_drift", {"threshold": 25})
        assert errors == []

    def test_out_of_range_high_returns_range_error(self):
        from margin_api.services.governance_config import validate_config_value

        errors = validate_config_value("circuit_breaker.score_drift", {"threshold": 150.0})
        assert any("range" in e.lower() for e in errors)

    def test_out_of_range_low_returns_range_error(self):
        from margin_api.services.governance_config import validate_config_value

        errors = validate_config_value("circuit_breaker.score_drift", {"threshold": -5.0})
        assert any("range" in e.lower() for e in errors)

    def test_wrong_type_returns_error(self):
        from margin_api.services.governance_config import validate_config_value

        errors = validate_config_value("circuit_breaker.score_drift", {"threshold": "not_a_number"})
        assert len(errors) > 0

    def test_unknown_key_returns_unknown_error(self):
        from margin_api.services.governance_config import validate_config_value

        errors = validate_config_value("circuit_breaker.nonexistent_key", {"threshold": 10.0})
        assert any("unknown" in e.lower() for e in errors)

    def test_missing_required_field_returns_error(self):
        from margin_api.services.governance_config import validate_config_value

        errors = validate_config_value("circuit_breaker.score_drift", {})
        assert len(errors) > 0

    def test_all_registry_keys_have_valid_defaults(self):
        from margin_api.services.governance_config import CONFIG_REGISTRY, validate_config_value

        for key, spec in CONFIG_REGISTRY.items():
            errors = validate_config_value(key, spec.default)
            assert errors == [], f"Default for {key!r} failed validation: {errors}"

    def test_all_three_circuit_breaker_keys_exist(self):
        from margin_api.services.governance_config import CONFIG_REGISTRY

        assert "circuit_breaker.score_drift" in CONFIG_REGISTRY
        assert "circuit_breaker.ingestion_failure" in CONFIG_REGISTRY
        assert "circuit_breaker.ml_regression" in CONFIG_REGISTRY

    def test_ingestion_failure_valid_value(self):
        from margin_api.services.governance_config import validate_config_value

        errors = validate_config_value("circuit_breaker.ingestion_failure", {"threshold": 20.0})
        assert errors == []

    def test_ml_regression_valid_value(self):
        from margin_api.services.governance_config import validate_config_value

        errors = validate_config_value("circuit_breaker.ml_regression", {"threshold": 50.0})
        assert errors == []


# ---------------------------------------------------------------------------
# get_threshold tests
# ---------------------------------------------------------------------------


class TestGetThreshold:
    @pytest.mark.asyncio
    async def test_returns_registry_default_when_no_db_row(self, session):
        from margin_api.services.governance_config import get_threshold

        result = await get_threshold(session, "circuit_breaker.score_drift")
        assert result == 30.0

    @pytest.mark.asyncio
    async def test_returns_registry_default_for_ingestion_failure(self, session):
        from margin_api.services.governance_config import get_threshold

        result = await get_threshold(session, "circuit_breaker.ingestion_failure")
        assert result == 20.0

    @pytest.mark.asyncio
    async def test_returns_registry_default_for_ml_regression(self, session):
        from margin_api.services.governance_config import get_threshold

        result = await get_threshold(session, "circuit_breaker.ml_regression")
        assert result == 50.0

    @pytest.mark.asyncio
    async def test_returns_db_value_when_row_exists(self, session):
        from margin_api.services.governance_config import get_threshold

        session.add(
            GovernanceConfig(
                config_key="circuit_breaker.score_drift",
                config_value={"threshold": 42.5},
            )
        )
        await session.commit()

        result = await get_threshold(session, "circuit_breaker.score_drift")
        assert result == 42.5

    @pytest.mark.asyncio
    async def test_db_value_overrides_default(self, session):
        from margin_api.services.governance_config import get_threshold

        session.add(
            GovernanceConfig(
                config_key="circuit_breaker.ingestion_failure",
                config_value={"threshold": 15.0},
            )
        )
        await session.commit()

        result = await get_threshold(session, "circuit_breaker.ingestion_failure")
        assert result == 15.0

    @pytest.mark.asyncio
    async def test_unknown_key_raises_key_error(self, session):
        from margin_api.services.governance_config import get_threshold

        with pytest.raises(KeyError):
            await get_threshold(session, "circuit_breaker.nonexistent")
