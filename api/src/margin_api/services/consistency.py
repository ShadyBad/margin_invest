"""Post-ingestion consistency validation service.

Bridges the engine's validate_data_consistency() function with the database.
Loads a ticker's financial history, runs the engine validation, and persists
flags to the FinancialData.consistency_flags JSONB column.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, FinancialData
from margin_api.services.scoring import build_financial_history_from_rows
from margin_engine.scoring.data_consistency import validate_data_consistency

logger = logging.getLogger(__name__)


async def validate_ticker_consistency(
    session: AsyncSession,
    ticker: str,
) -> dict | None:
    """Validate data consistency for a single ticker.

    Loads the asset's financial history from the DB, runs the engine's
    cross-period deviation detection, and persists results to the latest
    FinancialData row's consistency_flags column.

    Args:
        session: Async SQLAlchemy session.
        ticker: Stock ticker symbol.

    Returns:
        Result dict with has_anomalies, anomalies, and all_flags keys,
        or None if the ticker is unknown or has < 3 periods of data.
    """
    # Load the asset
    stmt = select(Asset).where(Asset.ticker == ticker)
    result = await session.execute(stmt)
    asset = result.scalar_one_or_none()
    if asset is None:
        return None

    # Load all FinancialData rows, ordered by period_end ascending
    fd_stmt = (
        select(FinancialData)
        .where(FinancialData.asset_id == asset.id)
        .order_by(FinancialData.period_end.asc())
    )
    fd_result = await session.execute(fd_stmt)
    rows = fd_result.scalars().all()

    if len(rows) < 3:
        return None

    # Convert ORM rows to dicts for build_financial_history_from_rows
    row_dicts = [
        {
            "period_end": row.period_end,
            "filing_date": row.filing_date,
            "income_statement": row.income_statement,
            "balance_sheet": row.balance_sheet,
            "cash_flow": row.cash_flow,
        }
        for row in rows
    ]

    # Build FinancialHistory and run engine validation
    history = build_financial_history_from_rows(ticker, row_dicts)
    flags = validate_data_consistency(history)

    # Separate anomalies from all flags
    anomalies = [f for f in flags if f.is_anomaly]

    result_dict = {
        "has_anomalies": len(anomalies) > 0,
        "anomalies": [f.model_dump() for f in anomalies],
        "all_flags": [f.model_dump() for f in flags],
    }

    # Persist to the latest row's consistency_flags column
    latest_row = rows[-1]
    latest_row.consistency_flags = result_dict
    session.add(latest_row)
    await session.commit()

    if anomalies:
        logger.warning(
            "Consistency anomalies detected for %s: %s",
            ticker,
            [f.field_name for f in anomalies],
        )

    return result_dict


async def validate_universe_consistency(
    session: AsyncSession,
    tickers: list[str] | None = None,
) -> dict[str, dict]:
    """Validate data consistency for multiple tickers.

    Args:
        session: Async SQLAlchemy session.
        tickers: Optional list of tickers to validate. If None,
                 validates all active tickers in the database.

    Returns:
        Dict mapping ticker -> result dict (same shape as validate_ticker_consistency).
        Tickers with None results (unknown or insufficient data) are omitted.
    """
    if tickers is None:
        # Load all active tickers
        stmt = select(Asset.ticker).where(Asset.ingestion_status == "active")
        result = await session.execute(stmt)
        tickers = [row[0] for row in result.all()]

    results: dict[str, dict] = {}
    anomaly_count = 0

    for ticker in tickers:
        ticker_result = await validate_ticker_consistency(session, ticker)
        if ticker_result is not None:
            results[ticker] = ticker_result
            if ticker_result["has_anomalies"]:
                anomaly_count += 1

    logger.info(
        "Universe consistency validation complete: %d/%d tickers have anomalies",
        anomaly_count,
        len(results),
    )

    return results
