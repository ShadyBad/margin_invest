"""Compute institutional accumulation signals from 13F holdings."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date


@dataclass
class HoldingSummary:
    """Input: one manager's holding of one asset for one quarter."""

    cusip: str
    ticker: str | None
    asset_id: int
    period_of_report: date
    manager_id: int
    tier: str  # 'curated' or 'top_aum'
    shares_held: int
    prev_shares: int | None  # None = new position


@dataclass
class QuarterSignal:
    """Output: aggregated signal for one asset for one quarter."""

    asset_id: int
    period_of_report: date
    curated_holders: int
    total_holders: int
    curated_new_positions: int
    total_new_positions: int
    curated_net_shares: int
    total_net_shares: int
    signal_score: float = 0.0  # populated later by percentile ranking


def compute_quarter_signals(summaries: list[HoldingSummary]) -> list[QuarterSignal]:
    """Aggregate holdings into per-asset accumulation signals."""
    if not summaries:
        return []

    by_asset: dict[int, list[HoldingSummary]] = defaultdict(list)
    for s in summaries:
        by_asset[s.asset_id].append(s)

    signals: list[QuarterSignal] = []
    for asset_id, holdings in by_asset.items():
        curated_holders = 0
        total_holders = 0
        curated_new = 0
        total_new = 0
        curated_net = 0
        total_net = 0

        for h in holdings:
            total_holders += 1
            is_new = h.prev_shares is None
            net = h.shares_held if is_new else h.shares_held - h.prev_shares

            if is_new:
                total_new += 1
            total_net += net

            if h.tier == "curated":
                curated_holders += 1
                curated_net += net
                if is_new:
                    curated_new += 1

        signals.append(
            QuarterSignal(
                asset_id=asset_id,
                period_of_report=holdings[0].period_of_report,
                curated_holders=curated_holders,
                total_holders=total_holders,
                curated_new_positions=curated_new,
                total_new_positions=total_new,
                curated_net_shares=curated_net,
                total_net_shares=total_net,
            )
        )
    return signals
