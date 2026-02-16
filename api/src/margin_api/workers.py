"""ARQ worker configuration and job definitions."""
from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings


async def full_ingest(ctx: dict) -> dict:
    """Ingest full universe from active snapshot."""
    return {"status": "not_implemented"}


async def full_score(ctx: dict) -> dict:
    """Score all ingested assets."""
    return {"status": "not_implemented"}


async def backtest_validate(ctx: dict) -> dict:
    """Run automatic backtest validation."""
    return {"status": "not_implemented"}


async def live_price_poll(ctx: dict) -> dict:
    """Poll live prices for recommended candidates."""
    return {"status": "not_implemented"}


async def retry_quarantined(ctx: dict) -> dict:
    """Retry quarantined tickers weekly."""
    return {"status": "not_implemented"}


class WorkerSettings:
    redis_settings = RedisSettings(host="localhost", port=6379)
    functions = [full_ingest, full_score, backtest_validate, live_price_poll, retry_quarantined]
    cron_jobs = [
        cron(full_ingest, hour=16, minute=30),
        cron(
            live_price_poll,
            minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
            run_at_startup=False,
        ),
        cron(retry_quarantined, weekday=6, hour=0),
    ]
