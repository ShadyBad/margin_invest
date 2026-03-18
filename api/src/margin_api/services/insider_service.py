"""Insider transaction service — queries Form 4 history for first-buy detection.

Architecture boundary: this DB query runs in the API/worker layer. The boolean
result is populated on InsiderTransaction.is_first_purchase before the model
reaches the engine. The engine package remains pure Python with zero web/DB deps.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import InsiderTransactionHistory


async def is_first_purchase(
    session: AsyncSession,
    ticker: str,
    insider_cik: str,
) -> bool:
    """Check if this insider has ever purchased this stock before.

    Returns True if no prior purchase exists (this IS a first purchase).
    Returns False if prior purchases exist.

    Queries insider_transaction_history for any prior 'P' (purchase) transaction
    matching this ticker + insider_cik combination.
    """
    result = await session.execute(
        select(InsiderTransactionHistory.id)
        .where(InsiderTransactionHistory.ticker == ticker)
        .where(InsiderTransactionHistory.insider_cik == insider_cik)
        .where(InsiderTransactionHistory.transaction_type == "P")
        .limit(1)
    )
    return result.scalar_one_or_none() is None
