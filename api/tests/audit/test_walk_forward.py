from __future__ import annotations

from datetime import date

import pytest
from margin_api.audit.walk_forward import RegeneratingUniverseProvider
from sqlalchemy.ext.asyncio import AsyncSession


def test_regenerating_provider_implements_get_scores_signature(
    synthetic_audit_db: AsyncSession,
) -> None:
    provider = RegeneratingUniverseProvider(session=synthetic_audit_db)
    assert callable(getattr(provider, "get_scores", None))


@pytest.mark.asyncio
async def test_regenerating_provider_returns_scored_stocks_at_cohort_date(
    synthetic_audit_db: AsyncSession,
) -> None:
    provider = RegeneratingUniverseProvider(session=synthetic_audit_db)
    scored = await provider.get_scores_async(date(2026, 2, 28))
    assert isinstance(scored, list)
    for item in scored:
        assert hasattr(item, "ticker")
        assert hasattr(item, "composite_score")
