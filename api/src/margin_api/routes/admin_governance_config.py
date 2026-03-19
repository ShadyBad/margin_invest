"""Admin CRUD endpoints for governance config overrides."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import GovernanceConfig, GovernanceEvent, User
from margin_api.db.session import get_db
from margin_api.deps import get_superadmin_user
from margin_api.schemas.governance import (
    GovernanceConfigListResponse,
    GovernanceConfigResponse,
    GovernanceConfigUpdate,
)
from margin_api.services.governance_config import CONFIG_REGISTRY, validate_config_value

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/governance-config", tags=["governance-config"])


def _build_response(
    key: str,
    db_row: GovernanceConfig | None,
) -> GovernanceConfigResponse:
    """Build a GovernanceConfigResponse merging DB override with registry defaults."""
    spec = CONFIG_REGISTRY[key]
    if db_row is not None and db_row.config_value is not None:
        return GovernanceConfigResponse(
            config_key=key,
            config_value=db_row.config_value,
            description=spec.description,
            is_default=False,
            updated_at=db_row.updated_at,
        )
    return GovernanceConfigResponse(
        config_key=key,
        config_value=spec.default,
        description=spec.description,
        is_default=True,
        updated_at=None,
    )


@router.get("")
async def list_governance_configs(
    superadmin: User = Depends(get_superadmin_user),
    session: AsyncSession = Depends(get_db),
) -> GovernanceConfigListResponse:
    """List all governance config keys, merging DB overrides with registry defaults."""
    result = await session.execute(select(GovernanceConfig))
    rows: dict[str, GovernanceConfig] = {r.config_key: r for r in result.scalars().all()}

    configs = [_build_response(key, rows.get(key)) for key in sorted(CONFIG_REGISTRY)]
    return GovernanceConfigListResponse(configs=configs)


@router.get("/{key}")
async def get_governance_config(
    key: str,
    superadmin: User = Depends(get_superadmin_user),
    session: AsyncSession = Depends(get_db),
) -> GovernanceConfigResponse:
    """Get a single governance config key. 404 for unknown keys."""
    if key not in CONFIG_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown config key: {key!r}")

    result = await session.execute(
        select(GovernanceConfig).where(GovernanceConfig.config_key == key)
    )
    row = result.scalar_one_or_none()
    return _build_response(key, row)


@router.put("/{key}")
async def upsert_governance_config(
    key: str,
    body: GovernanceConfigUpdate,
    superadmin: User = Depends(get_superadmin_user),
    session: AsyncSession = Depends(get_db),
) -> GovernanceConfigResponse:
    """Upsert a governance config override. Validates value against registry schema."""
    errors = validate_config_value(key, body.config_value)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))

    result = await session.execute(
        select(GovernanceConfig).where(GovernanceConfig.config_key == key)
    )
    row = result.scalar_one_or_none()
    old_value = row.config_value if row is not None else None

    if row is None:
        row = GovernanceConfig(config_key=key, config_value=body.config_value)
        session.add(row)
    else:
        row.config_value = body.config_value

    event = GovernanceEvent(
        event_type="config.updated",
        source="admin_api",
        detail={
            "config_key": key,
            "old_value": old_value,
            "new_value": body.config_value,
            "admin_user_id": superadmin.id,
        },
    )
    session.add(event)
    await session.commit()
    await session.refresh(row)

    logger.info(
        "[governance-config] Updated key=%r old=%r new=%r by user=%d",
        key,
        old_value,
        body.config_value,
        superadmin.id,
    )
    return _build_response(key, row)


@router.delete("/{key}", status_code=204)
async def delete_governance_config(
    key: str,
    superadmin: User = Depends(get_superadmin_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Remove a governance config override (reverts to registry default)."""
    if key not in CONFIG_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown config key: {key!r}")

    result = await session.execute(
        select(GovernanceConfig).where(GovernanceConfig.config_key == key)
    )
    row = result.scalar_one_or_none()
    old_value = row.config_value if row is not None else None

    if row is not None:
        await session.delete(row)

    event = GovernanceEvent(
        event_type="config.deleted",
        source="admin_api",
        detail={
            "config_key": key,
            "old_value": old_value,
            "admin_user_id": superadmin.id,
        },
    )
    session.add(event)
    await session.commit()

    logger.info(
        "[governance-config] Deleted key=%r (was %r) by user=%d",
        key,
        old_value,
        superadmin.id,
    )
