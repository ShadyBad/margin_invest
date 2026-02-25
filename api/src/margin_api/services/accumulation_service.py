"""DB-layer service for computing accumulation signals from holdings data."""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import (
    AccumulationSignal,
    Asset,
    InstitutionalHolding,
    Manager,
    SecurityMaster,
)
from margin_engine.services.accumulation import (
    HoldingSummary,
    compute_quarter_signals,
)

logger = logging.getLogger(__name__)


class AccumulationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def compute_signals(self, period_of_report: date) -> int:
        """Compute accumulation signals for all assets in a given quarter.

        Returns the number of signals upserted.
        """
        # Get all holdings for this quarter
        holdings_q = (
            select(
                InstitutionalHolding.cusip,
                InstitutionalHolding.shares_held,
                InstitutionalHolding.manager_id,
                Manager.tier,
                SecurityMaster.ticker,
            )
            .join(Manager, InstitutionalHolding.manager_id == Manager.id)
            .join(SecurityMaster, InstitutionalHolding.security_master_id == SecurityMaster.id)
            .where(InstitutionalHolding.period_of_report == period_of_report)
        )
        result = await self._session.execute(holdings_q)
        current_holdings = result.all()

        if not current_holdings:
            return 0

        # Get previous quarter's holdings for delta computation
        prev_period = _previous_quarter(period_of_report)
        prev_q = (
            select(
                InstitutionalHolding.cusip,
                InstitutionalHolding.shares_held,
                InstitutionalHolding.manager_id,
            )
            .where(InstitutionalHolding.period_of_report == prev_period)
        )
        prev_result = await self._session.execute(prev_q)
        prev_holdings = prev_result.all()

        # Build lookup: (cusip, manager_id) -> prev_shares
        prev_lookup: dict[tuple[str, int], int] = {}
        for row in prev_holdings:
            prev_lookup[(row.cusip, row.manager_id)] = row.shares_held

        # Resolve cusip -> asset_id
        cusips = list({h.cusip for h in current_holdings})
        asset_lookup = await self._resolve_asset_ids(cusips)

        # Build HoldingSummary list for the engine
        summaries: list[HoldingSummary] = []
        for h in current_holdings:
            asset_id = asset_lookup.get(h.cusip)
            if asset_id is None:
                continue  # can't link to an asset

            prev_shares = prev_lookup.get((h.cusip, h.manager_id))
            summaries.append(
                HoldingSummary(
                    cusip=h.cusip,
                    ticker=h.ticker,
                    asset_id=asset_id,
                    period_of_report=period_of_report,
                    manager_id=h.manager_id,
                    tier=h.tier,
                    shares_held=h.shares_held,
                    prev_shares=prev_shares,
                )
            )

        # Compute signals using the pure engine function
        signals = compute_quarter_signals(summaries)

        # Upsert into AccumulationSignal table
        count = 0
        for sig in signals:
            existing_q = select(AccumulationSignal).where(
                AccumulationSignal.asset_id == sig.asset_id,
                AccumulationSignal.period_of_report == sig.period_of_report,
            )
            existing_result = await self._session.execute(existing_q)
            existing = existing_result.scalar_one_or_none()

            if existing:
                existing.curated_holders = sig.curated_holders
                existing.total_holders = sig.total_holders
                existing.curated_new_positions = sig.curated_new_positions
                existing.total_new_positions = sig.total_new_positions
                existing.curated_net_shares = sig.curated_net_shares
                existing.total_net_shares = sig.total_net_shares
                existing.signal_score = sig.signal_score
                existing.computed_at = datetime.now(UTC)
            else:
                self._session.add(
                    AccumulationSignal(
                        asset_id=sig.asset_id,
                        period_of_report=sig.period_of_report,
                        curated_holders=sig.curated_holders,
                        total_holders=sig.total_holders,
                        curated_new_positions=sig.curated_new_positions,
                        total_new_positions=sig.total_new_positions,
                        curated_net_shares=sig.curated_net_shares,
                        total_net_shares=sig.total_net_shares,
                        signal_score=sig.signal_score,
                        computed_at=datetime.now(UTC),
                    )
                )
            count += 1

        await self._session.commit()
        return count

    async def _resolve_asset_ids(self, cusips: list[str]) -> dict[str, int]:
        """Map CUSIPs to asset IDs via SecurityMaster -> Asset ticker lookup."""
        # First try SecurityMaster.ticker -> Asset.ticker
        sec_q = select(SecurityMaster.cusip, SecurityMaster.ticker).where(
            SecurityMaster.cusip.in_(cusips)
        )
        sec_result = await self._session.execute(sec_q)
        cusip_to_ticker = {row.cusip: row.ticker for row in sec_result.all() if row.ticker}

        if not cusip_to_ticker:
            # Try Asset.cusip directly
            asset_q = select(Asset.cusip, Asset.id).where(Asset.cusip.in_(cusips))
            asset_result = await self._session.execute(asset_q)
            return {row.cusip: row.id for row in asset_result.all() if row.cusip}

        tickers = list(set(cusip_to_ticker.values()))
        asset_q = select(Asset.ticker, Asset.id).where(Asset.ticker.in_(tickers))
        asset_result = await self._session.execute(asset_q)
        ticker_to_id = {row.ticker: row.id for row in asset_result.all()}

        return {
            cusip: ticker_to_id[ticker]
            for cusip, ticker in cusip_to_ticker.items()
            if ticker in ticker_to_id
        }


def _previous_quarter(d: date) -> date:
    """Get the last day of the previous quarter."""
    quarter_ends = [
        date(d.year - 1, 12, 31),
        date(d.year, 3, 31),
        date(d.year, 6, 30),
        date(d.year, 9, 30),
        date(d.year, 12, 31),
    ]

    for qe in reversed(quarter_ends):
        if qe < d:
            return qe
    return date(d.year - 1, 12, 31)
