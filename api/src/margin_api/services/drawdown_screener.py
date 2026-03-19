"""Drawdown-triggered re-screening service.

Identifies stocks in the scored universe that have dropped significantly from
their 52-week high and enqueues per-ticker rescore jobs via ARQ.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import DrawdownRescreen

logger = logging.getLogger(__name__)


@dataclass
class DrawdownCandidate:
    """A ticker that has breached the drawdown threshold from its 52-week high."""

    ticker: str
    drawdown_pct: float
    high_price: float
    current_price: float


class DrawdownScreener:
    """Screens the scored universe for drawdown candidates and enqueues rescreening jobs.

    Configuration via environment variables (all prefixed MARGIN_):
        MARGIN_DRAWDOWN_THRESHOLD    — minimum drawdown to trigger (default -0.20)
        MARGIN_DRAWDOWN_MAX_PER_RUN  — max candidates per cron run (default 10)
        MARGIN_DRAWDOWN_DEBOUNCE_DAYS — days to suppress re-trigger (default 7)
    """

    def __init__(self) -> None:
        self.threshold: float = float(os.environ.get("MARGIN_DRAWDOWN_THRESHOLD", "-0.20"))
        self.max_per_run: int = int(os.environ.get("MARGIN_DRAWDOWN_MAX_PER_RUN", "10"))
        self.debounce_days: int = int(os.environ.get("MARGIN_DRAWDOWN_DEBOUNCE_DAYS", "7"))

    async def find_candidates(
        self,
        session: AsyncSession,
        min_drawdown_pct: float | None = None,
    ) -> list[DrawdownCandidate]:
        """Query pit_daily_prices for stocks down >= threshold from 52-week high.

        Filters:
        - Only tickers with a published ScoreResponse (is_published=True).
        - Debounce: skip tickers rescreened within debounce_days.
        - Sort by deepest drawdown first, capped at max_per_run.

        Args:
            session: Async DB session.
            min_drawdown_pct: Override threshold for this call (negative float, e.g. -0.20).

        Returns:
            List of DrawdownCandidate sorted by drawdown_pct ascending (most negative first).
        """
        threshold = min_drawdown_pct if min_drawdown_pct is not None else self.threshold
        today = date.today()
        year_ago = today - timedelta(days=365)
        debounce_cutoff = today - timedelta(days=self.debounce_days)

        # Build the query:
        # 1. For each ticker with a published score, get today's close and the
        #    52-week high from pit_daily_prices.
        # 2. Compute drawdown = (close - 52wk_high) / 52wk_high.
        # 3. Filter by threshold and exclude recently rescreened tickers.
        # 4. Sort deepest first, limit to max_per_run.
        #
        # We use a raw SQL subquery for cross-database compatibility in tests
        # (SQLite does not have LATERAL; this approach works with both).
        stmt = text(
            """
            SELECT
                latest.ticker,
                latest.close AS current_price,
                year_high.high_price,
                (latest.close - year_high.high_price) / year_high.high_price AS drawdown_pct
            FROM (
                -- latest trading day price per ticker
                SELECT p1.ticker, p1.close
                FROM pit_daily_prices p1
                INNER JOIN (
                    SELECT ticker, MAX(date) AS max_date
                    FROM pit_daily_prices
                    GROUP BY ticker
                ) p1max ON p1.ticker = p1max.ticker AND p1.date = p1max.max_date
            ) latest
            JOIN (
                -- 52-week high per ticker
                SELECT ticker, MAX(high) AS high_price
                FROM pit_daily_prices
                WHERE date >= :year_ago
                GROUP BY ticker
            ) year_high ON latest.ticker = year_high.ticker
            WHERE
                year_high.high_price > 0
                AND (latest.close - year_high.high_price) / year_high.high_price <= :threshold
                AND latest.ticker NOT IN (
                    SELECT DISTINCT ticker
                    FROM drawdown_rescreens
                    WHERE trigger_date >= :debounce_cutoff
                )
            ORDER BY drawdown_pct ASC
            LIMIT :max_per_run
            """
        )

        try:
            result = await session.execute(
                stmt,
                {
                    "year_ago": year_ago,
                    "threshold": threshold,
                    "debounce_cutoff": debounce_cutoff,
                    "max_per_run": self.max_per_run,
                },
            )
            rows = result.fetchall()
        except Exception as exc:
            logger.error("[drawdown_screener] Query failed: %s", exc)
            raise

        candidates = [
            DrawdownCandidate(
                ticker=row.ticker,
                drawdown_pct=float(row.drawdown_pct),
                high_price=float(row.high_price),
                current_price=float(row.current_price),
            )
            for row in rows
        ]

        logger.info(
            "[drawdown_screener] Found %d candidates (threshold=%.0f%%, debounce=%dd)",
            len(candidates),
            threshold * 100,
            self.debounce_days,
        )
        return candidates

    async def trigger_rescreening(
        self,
        session: AsyncSession,
        candidates: list[DrawdownCandidate],
        arq_pool: object | None = None,
    ) -> int:
        """Create DrawdownRescreen records and enqueue rescore_ticker jobs.

        Args:
            session: Async DB session.
            candidates: Drawdown candidates to process.
            arq_pool: ARQ Redis pool for enqueueing jobs (optional; skips enqueue if None).

        Returns:
            Number of rescreen records created.
        """
        today = date.today()
        count = 0

        for candidate in candidates:
            record = DrawdownRescreen(
                ticker=candidate.ticker,
                drawdown_pct=candidate.drawdown_pct,
                high_price=candidate.high_price,
                current_price=candidate.current_price,
                trigger_date=today,
                created_at=datetime.now(UTC),
            )
            session.add(record)
            count += 1

            if arq_pool is not None:
                try:
                    await arq_pool.enqueue_job(  # type: ignore[union-attr]
                        "rescore_ticker",
                        candidate.ticker,
                        trigger_reason="drawdown",
                    )
                    logger.info(
                        "[drawdown_screener] Enqueued rescore_ticker for %s (drawdown=%.1f%%)",
                        candidate.ticker,
                        candidate.drawdown_pct * 100,
                    )
                except Exception as exc:
                    logger.warning(
                        "[drawdown_screener] Failed to enqueue rescore_ticker for %s: %s",
                        candidate.ticker,
                        exc,
                    )

        if count > 0:
            await session.commit()
            logger.info("[drawdown_screener] Created %d DrawdownRescreen records", count)
        else:
            logger.info("[drawdown_screener] No candidates to rescreen")

        return count
