"""ARQ background worker for scoring tickers.

Loads financial data from the database, runs the scoring pipeline,
and persists Score rows. Designed to be run via:

    arq margin_api.worker.WorkerSettings
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.models import ApiKey, ApiKeyEvent, Asset, FinancialData, Score
from margin_api.db.session import get_engine, get_session_factory
from margin_api.services.api_keys import ApiKeyService
from margin_api.services.scoring import (
    build_asset_profile,
    build_financial_period,
    run_scoring_pipeline,
)

logger = logging.getLogger(__name__)


async def score_ticker(*, ticker: str, session: AsyncSession) -> bool:
    """Score a single ticker using data already stored in the database.

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL").
        session: An active async database session.

    Returns:
        True if scoring succeeded and a Score row was persisted, False otherwise.
    """
    try:
        # 1. Load Asset
        result = await session.execute(select(Asset).where(Asset.ticker == ticker))
        asset = result.scalar_one_or_none()
        if asset is None:
            logger.warning("Asset not found for ticker: %s", ticker)
            return False

        # 2. Load most recent FinancialData
        result = await session.execute(
            select(FinancialData)
            .where(FinancialData.asset_id == asset.id)
            .order_by(FinancialData.fetched_at.desc())
            .limit(1)
        )
        fin_data = result.scalar_one_or_none()
        if fin_data is None:
            logger.warning("No financial data found for ticker: %s", ticker)
            return False

        # 3. Build engine models
        period = build_financial_period(
            income_raw=fin_data.income_statement or {},
            balance_raw=fin_data.balance_sheet or {},
            cashflow_raw=fin_data.cash_flow or {},
            period_end=fin_data.period_end,
            filing_date=fin_data.filing_date,
        )

        # 4. Extract price bars and earnings from JSONB
        # price_history is stored as {"bars": [...]}
        price_data = fin_data.price_history or {}
        price_bars_raw: list[dict] = (
            price_data.get("bars", []) if isinstance(price_data, dict) else []
        )

        # Compute volume and history from price bars for liquidity filter
        avg_daily_volume = Decimal("0")
        years_of_history = 0
        if price_bars_raw:
            volumes = [
                float(b.get("volume") or b.get("Volume") or 0)
                * float(
                    b.get("close")
                    or b.get("Close")
                    or b.get("adj_close")
                    or b.get("Adj Close")
                    or 0
                )
                for b in price_bars_raw
            ]
            if volumes:
                avg_daily_volume = Decimal(str(sum(volumes) / len(volumes)))
            dates = [b.get("date") or b.get("Date") for b in price_bars_raw]
            valid_dates = [d for d in dates if d]
            if len(valid_dates) >= 2:
                try:
                    first = datetime.fromisoformat(str(valid_dates[0]))
                    last = datetime.fromisoformat(str(valid_dates[-1]))
                    years_of_history = max(1, int(abs((last - first).days) / 365))
                except (ValueError, TypeError):
                    pass

        profile = build_asset_profile(
            ticker=asset.ticker,
            name=asset.name,
            sector=asset.sector,
            market_cap=asset.market_cap,
            avg_daily_volume=avg_daily_volume,
            years_of_history=years_of_history,
            shares_outstanding=asset.shares_outstanding,
        )
        earnings_raw: list[dict] = fin_data.earnings_data or []

        # 5. Run scoring pipeline
        composite = run_scoring_pipeline(
            ticker=ticker,
            period=period,
            profile=profile,
            price_bars_raw=price_bars_raw,
            earnings_raw=earnings_raw,
        )

        # 6. Create Score row
        score = Score(
            asset_id=asset.id,
            composite_percentile=composite.composite_percentile,
            composite_raw_score=composite.composite_raw_score,
            conviction_level=composite.conviction_level.value,
            signal=composite.signal.value,
            quality_percentile=composite.quality.average_percentile,
            value_percentile=composite.value.average_percentile,
            momentum_percentile=composite.momentum.average_percentile,
            data_coverage=composite.data_coverage,
            growth_stage=composite.growth_stage.value if composite.growth_stage else None,
            score_detail=composite.model_dump(mode="json"),
            scored_at=datetime.now(UTC),
            margin_invest_value=composite.intrinsic_value,
            buy_price=composite.buy_price,
            sell_price=composite.sell_price,
            actual_price=composite.actual_price,
            price_target_invalid_reason=composite.price_target_invalid_reason,
            opportunity_type=(
                composite.opportunity_type.value if composite.opportunity_type else None
            ),
            winning_track=composite.winning_track,
            asymmetry_ratio=composite.asymmetry_ratio,
            max_position_pct=composite.max_position_pct,
            timing_signal=composite.timing_signal,
        )
        session.add(score)
        await session.commit()

        logger.info(
            "Scored %s: composite=%.1f conviction=%s signal=%s",
            ticker,
            composite.composite_percentile,
            composite.conviction_level.value,
            composite.signal.value,
        )
        return True

    except Exception:
        logger.exception("Error scoring ticker %s", ticker)
        await session.rollback()
        return False


async def score_all_tickers(ctx: dict) -> None:
    """ARQ task: load all tickers from the assets table and score each one."""
    engine = get_engine()
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        result = await session.execute(select(Asset.ticker))
        tickers = list(result.scalars().all())

    logger.info("Scoring %d tickers", len(tickers))

    for ticker in tickers:
        async with session_factory() as session:
            await score_ticker(ticker=ticker, session=session)


async def score_single_ticker(ctx: dict, ticker: str) -> bool:
    """ARQ task: score a single ticker."""
    engine = get_engine()
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        return await score_ticker(ticker=ticker, session=session)


_ROTATION_AGE_DAYS = 90
_OVERLAP_HOURS = 24


async def rotate_platform_keys(
    *,
    session: AsyncSession,
    service: ApiKeyService,
) -> int:
    """Rotate platform-managed API keys older than 90 days.

    Sets expires_at on the old key (24-hour overlap window) and creates
    a new key with the same plaintext value. Returns count of rotated keys.
    """
    cutoff = datetime.now(UTC) - timedelta(days=_ROTATION_AGE_DAYS)
    stmt = select(ApiKey).where(
        ApiKey.is_platform_managed.is_(True),
        ApiKey.revoked_at.is_(None),
        ApiKey.expires_at.is_(None),
        ApiKey.created_at < cutoff,
    )
    result = await session.execute(stmt)
    old_keys = list(result.scalars().all())

    rotated = 0
    for old_key in old_keys:
        # Set overlap window on old key
        old_key.expires_at = datetime.now(UTC) + timedelta(hours=_OVERLAP_HOURS)
        session.add(ApiKeyEvent(api_key_id=old_key.id, event_type="rotated"))

        # Create new key with same plaintext
        plaintext = service.decrypt(old_key.encrypted_key)
        new_key = ApiKey(
            user_id=old_key.user_id,
            provider_name=old_key.provider_name,
            encrypted_key=service.encrypt(plaintext),
            is_platform_managed=True,
        )
        session.add(new_key)
        rotated += 1

    if rotated:
        await session.commit()

    return rotated


def _parse_redis_settings() -> RedisSettings:
    """Parse the Redis URL from app settings into ARQ RedisSettings."""
    settings = get_settings()
    return RedisSettings.from_dsn(settings.redis_url)


class WorkerSettings:
    """ARQ worker settings.

    Run the worker with:
        arq margin_api.worker.WorkerSettings
    """

    functions = [score_all_tickers, score_single_ticker]
    redis_settings = _parse_redis_settings()


def get_worker_settings() -> type:
    """Return the WorkerSettings class with Redis connection from app config.

    This function re-reads the settings so that it picks up any environment
    variable changes (useful for tests).
    """
    WorkerSettings.redis_settings = _parse_redis_settings()
    return WorkerSettings
