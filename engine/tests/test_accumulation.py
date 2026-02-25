"""Tests for institutional accumulation signal computation."""
from datetime import date

from margin_engine.services.accumulation import (
    HoldingSummary,
    QuarterSignal,
    compute_quarter_signals,
)


def _make(
    asset_id: int = 1,
    cusip: str = "037833100",
    ticker: str = "AAPL",
    period: date = date(2025, 12, 31),
    manager_id: int = 1,
    tier: str = "curated",
    shares: int = 1000,
    prev_shares: int | None = None,
) -> HoldingSummary:
    return HoldingSummary(
        cusip=cusip,
        ticker=ticker,
        asset_id=asset_id,
        period_of_report=period,
        manager_id=manager_id,
        tier=tier,
        shares_held=shares,
        prev_shares=prev_shares,
    )


def test_single_curated_new_position():
    signals = compute_quarter_signals([_make(prev_shares=None)])
    assert len(signals) == 1
    s = signals[0]
    assert s.asset_id == 1
    assert s.curated_holders == 1
    assert s.total_holders == 1
    assert s.curated_new_positions == 1
    assert s.total_new_positions == 1
    assert s.curated_net_shares == 1000
    assert s.total_net_shares == 1000


def test_existing_position_increased():
    signals = compute_quarter_signals([_make(shares=1500, prev_shares=1000)])
    s = signals[0]
    assert s.curated_new_positions == 0
    assert s.total_new_positions == 0
    assert s.curated_net_shares == 500
    assert s.total_net_shares == 500


def test_mixed_tiers():
    summaries = [
        _make(manager_id=1, tier="curated", shares=1000, prev_shares=None),
        _make(manager_id=2, tier="top_aum", shares=2000, prev_shares=1000),
        _make(manager_id=3, tier="top_aum", shares=500, prev_shares=None),
    ]
    signals = compute_quarter_signals(summaries)
    s = signals[0]
    assert s.curated_holders == 1
    assert s.total_holders == 3
    assert s.curated_new_positions == 1
    assert s.total_new_positions == 2
    assert s.curated_net_shares == 1000
    assert s.total_net_shares == 2500


def test_multiple_assets():
    summaries = [
        _make(asset_id=1, cusip="037833100"),
        _make(asset_id=2, cusip="594918104"),
    ]
    signals = compute_quarter_signals(summaries)
    assert len(signals) == 2
    assert {s.asset_id for s in signals} == {1, 2}


def test_position_decreased():
    signals = compute_quarter_signals([_make(shares=500, prev_shares=1000)])
    s = signals[0]
    assert s.curated_net_shares == -500
    assert s.total_net_shares == -500


def test_empty_input():
    assert compute_quarter_signals([]) == []
