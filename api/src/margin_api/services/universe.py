"""Universe management service."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from margin_engine.universe.config import load_universe_config
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import UniverseSnapshot


async def activate_universe(session: AsyncSession, config_path: Path) -> UniverseSnapshot:
    """Load universe config from YAML, deactivate previous, create active snapshot."""
    config = load_universe_config(config_path)

    # Deactivate all existing snapshots
    await session.execute(
        update(UniverseSnapshot).where(UniverseSnapshot.is_active.is_(True)).values(is_active=False)
    )

    snapshot = UniverseSnapshot(
        version=config.version,
        config_hash=config.config_hash,
        ticker_count=config.ticker_count,
        tickers=config.tickers,
        exclusion_rules={
            "sectors": config.exclusions.sectors,
            "min_market_cap": config.exclusions.min_market_cap,
            "min_avg_volume": config.exclusions.min_avg_volume,
        },
        is_active=True,
        activated_at=datetime.now(UTC),
    )
    session.add(snapshot)
    await session.commit()
    await session.refresh(snapshot)
    return snapshot


async def get_active_snapshot(session: AsyncSession) -> UniverseSnapshot | None:
    """Return the currently active universe snapshot, or None."""
    result = await session.execute(
        select(UniverseSnapshot).where(UniverseSnapshot.is_active.is_(True))
    )
    return result.scalar_one_or_none()
